# tools/cloud/gcp/gcp_tool.py
# Implementación de la GCP Tool para LRA AI Platform.
# Conecta la plataforma con Google Cloud via google-cloud SDK.

import os
import subprocess
import json
from tools.cloud.base_cloud_tool import BaseCloudTool


class GCPTool(BaseCloudTool):
    """
    Tool para interactuar con Google Cloud via google-cloud SDK.

    Credenciales: usa Application Default Credentials (ADC).
    Detecta automáticamente gcloud CLI, variables de entorno o
    service account. Nunca hardcodeadas.

    Uso:
        gcp = GCPTool()
        gcp.execute("list_gcs_buckets", {})
        gcp.execute("list_gke_clusters", {"zone": "europe-west1"})
        gcp.execute("list_compute_instances", {"zone": "europe-west1-b"})
    """

    def __init__(self):
        super().__init__(name="gcp", provider="gcp", version="1.0.0")
        self._project = os.getenv("GOOGLE_CLOUD_PROJECT") or self._get_project_from_cli()
        self._region = os.getenv("GOOGLE_CLOUD_REGION", "europe-west1")

    def _get_project_from_cli(self) -> str:
        """Obtiene el project ID desde gcloud CLI."""
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, shell=True
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _run_gcloud(self, *args) -> dict:
        """Ejecuta un comando gcloud y retorna el resultado como dict."""
        cmd = ["gcloud"] + list(args) + ["--format=json"]
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        try:
            return json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            return {"raw": result.stdout.strip()}

    def validate(self) -> bool:
        try:
            identity = self.get_identity()
            print(f"[GCPTool] Authenticated: {identity.get('account')} | Project: {self._project}")
            return True
        except Exception as e:
            print(f"[GCPTool] Validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        return [
            "get_identity",
            "list_projects",
            "list_compute_instances",
            "list_gcs_buckets",
            "list_vpc_networks",
            "list_gke_clusters",
            "describe_gke_cluster",
            "list_artifact_registries",
            "list_cloud_sql",
            "list_cloud_run_services",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(
                f"Action '{action}' not supported. "
                f"Available: {self.get_capabilities()}"
            )

        actions = {
            "get_identity":            self._get_identity_action,
            "list_projects":           self._list_projects,
            "list_compute_instances":  self._list_compute_instances,
            "list_gcs_buckets":        self._list_gcs_buckets,
            "list_vpc_networks":       self._list_vpc_networks,
            "list_gke_clusters":       self._list_gke_clusters,
            "describe_gke_cluster":    self._describe_gke_cluster,
            "list_artifact_registries": self._list_artifact_registries,
            "list_cloud_sql":          self._list_cloud_sql,
            "list_cloud_run_services": self._list_cloud_run_services,
        }

        try:
            return actions[action](params)
        except Exception as e:
            return {"error": str(e), "action": action}

    # --- BaseCloudTool interface ---

    def get_identity(self) -> dict:
        return self._get_identity_action({})

    def list_compute(self, params: dict = None) -> dict:
        return self._list_compute_instances(params or {})

    def list_storage(self, params: dict = None) -> dict:
        return self._list_gcs_buckets(params or {})

    def list_networks(self, params: dict = None) -> dict:
        return self._list_vpc_networks(params or {})

    def list_kubernetes(self, params: dict = None) -> dict:
        return self._list_gke_clusters(params or {})

    def list_registries(self, params: dict = None) -> dict:
        return self._list_artifact_registries(params or {})

    # --- Implementaciones ---

    def _get_identity_action(self, params: dict) -> dict:
        result = self._run_gcloud("auth", "list", "--filter=status:ACTIVE")
        if isinstance(result, list) and result:
            return {
                "account": result[0].get("account", ""),
                "project": self._project,
                "status": result[0].get("status", ""),
            }
        return {"account": "unknown", "project": self._project}

    def _list_projects(self, params: dict) -> dict:
        result = self._run_gcloud("projects", "list")
        if isinstance(result, list):
            projects = [{"id": p.get("projectId"), "name": p.get("name"),
                         "number": p.get("projectNumber")}
                        for p in result]
            return {"projects": projects, "total": len(projects)}
        return {"projects": [], "total": 0, "error": result.get("error")}

    def _list_compute_instances(self, params: dict) -> dict:
        zone = params.get("zone", "--zones")
        if zone == "--zones":
            result = self._run_gcloud("compute", "instances", "list",
                                       "--project", self._project)
        else:
            result = self._run_gcloud("compute", "instances", "list",
                                       "--project", self._project,
                                       "--zones", zone)
        if isinstance(result, list):
            instances = [{"name": i.get("name"), "zone": i.get("zone", "").split("/")[-1],
                          "machine_type": i.get("machineType", "").split("/")[-1],
                          "status": i.get("status")}
                         for i in result]
            return {"instances": instances, "total": len(instances)}
        return {"instances": [], "total": 0}

    def _list_gcs_buckets(self, params: dict) -> dict:
        result = self._run_gcloud("storage", "buckets", "list",
                                   "--project", self._project)
        if isinstance(result, list):
            buckets = [{"name": b.get("name"), "location": b.get("location"),
                        "storage_class": b.get("storageClass")}
                       for b in result]
            return {"buckets": buckets, "total": len(buckets)}
        return {"buckets": [], "total": 0}

    def _list_vpc_networks(self, params: dict) -> dict:
        result = self._run_gcloud("compute", "networks", "list",
                                   "--project", self._project)
        if isinstance(result, list):
            networks = [{"name": n.get("name"), "mode": n.get("autoCreateSubnetworks"),
                         "mtu": n.get("mtu")}
                        for n in result]
            return {"networks": networks, "total": len(networks)}
        return {"networks": [], "total": 0}

    def _list_gke_clusters(self, params: dict) -> dict:
        result = self._run_gcloud("container", "clusters", "list",
                                   "--project", self._project)
        if isinstance(result, list):
            clusters = [{"name": c.get("name"), "location": c.get("location"),
                         "status": c.get("status"),
                         "k8s_version": c.get("currentMasterVersion"),
                         "node_count": c.get("currentNodeCount")}
                        for c in result]
            return {"clusters": clusters, "total": len(clusters)}
        return {"clusters": [], "total": 0}

    def _describe_gke_cluster(self, params: dict) -> dict:
        name = params.get("name")
        zone = params.get("zone", self._region)
        result = self._run_gcloud("container", "clusters", "describe", name,
                                   "--project", self._project,
                                   "--zone", zone)
        if isinstance(result, dict) and "name" in result:
            return {
                "name": result.get("name"),
                "location": result.get("location"),
                "status": result.get("status"),
                "k8s_version": result.get("currentMasterVersion"),
                "node_count": result.get("currentNodeCount"),
                "endpoint": result.get("endpoint"),
            }
        return result

    def _list_artifact_registries(self, params: dict) -> dict:
        result = self._run_gcloud("artifacts", "repositories", "list",
                                   "--project", self._project,
                                   "--location", self._region)
        if isinstance(result, list):
            repos = [{"name": r.get("name", "").split("/")[-1],
                      "format": r.get("format"),
                      "location": r.get("name", "").split("/")[3] if "/" in r.get("name","") else ""}
                     for r in result]
            return {"repositories": repos, "total": len(repos)}
        return {"repositories": [], "total": 0}

    def _list_cloud_sql(self, params: dict) -> dict:
        result = self._run_gcloud("sql", "instances", "list",
                                   "--project", self._project)
        if isinstance(result, list):
            instances = [{"name": i.get("name"), "database_version": i.get("databaseVersion"),
                          "region": i.get("region"), "state": i.get("state")}
                         for i in result]
            return {"instances": instances, "total": len(instances)}
        return {"instances": [], "total": 0}

    def _list_cloud_run_services(self, params: dict) -> dict:
        region = params.get("region", self._region)
        result = self._run_gcloud("run", "services", "list",
                                   "--project", self._project,
                                   "--region", region)
        if isinstance(result, list):
            services = [{"name": s.get("metadata", {}).get("name"),
                         "region": region,
                         "url": s.get("status", {}).get("url")}
                        for s in result]
            return {"services": services, "total": len(services)}
        return {"services": [], "total": 0}