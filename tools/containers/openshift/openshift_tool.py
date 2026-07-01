# tools/containers/openshift/openshift_tool.py
# Implementación de la OpenShift Tool para LRA AI Platform.
# Ejecuta comandos oc reales via subprocess.

import os
import subprocess
import json
from core.interfaces.tool import Tool


class OpenshiftTool(Tool):
    """
    Tool para interactuar con OpenShift via oc CLI.

    Ejecuta comandos oc reales contra el cluster configurado
    en el kubeconfig del sistema.

    Uso:
        oc = OpenshiftTool()
        oc.execute("get_projects", {})
        oc.execute("get_pods", {"namespace": "my-project"})
        oc.execute("deploy_app", {"name": "my-app", "image": "nginx:latest"})
    """

    def __init__(self):
        super().__init__(name="openshift", version="1.0.0")
        self._oc = self._find_oc()

    def _find_oc(self) -> str:
        import shutil
        return shutil.which("oc") or "oc"

    def _run(self, args: list, output_json: bool = True) -> dict:
        """Ejecuta un comando oc."""
        cmd = [self._oc] + args
        if output_json:
            cmd += ["-o", "json"]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True
            )
            output = result.stdout.strip()

            if output_json and output:
                try:
                    return {
                        "success": result.returncode == 0,
                        "data": json.loads(output),
                        "stderr": result.stderr.strip(),
                        "returncode": result.returncode,
                    }
                except json.JSONDecodeError:
                    pass

            return {
                "success": result.returncode == 0,
                "stdout": output,
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "stderr": "oc binary not found",
                "returncode": -1,
            }

    def validate(self) -> bool:
        """Verifica que oc está instalado."""
        result = self._run(["version", "--client"], output_json=False)
        if result["success"]:
            print(f"[OpenshiftTool] {result['stdout'].split(chr(10))[0]}")
            return True
        print(f"[OpenshiftTool] Validation failed: {result['stderr']}")
        return False

    def get_capabilities(self) -> list:
        return [
            "get_projects",
            "create_project",
            "delete_project",
            "get_pods",
            "get_deployments",
            "get_services",
            "get_routes",
            "get_builds",
            "get_build_configs",
            "get_image_streams",
            "deploy_app",
            "new_app",
            "expose_service",
            "scale_deployment",
            "rollout_latest",
            "get_operators",
            "install_operator",
            "apply_manifest",
            "get_events",
            "whoami",
            "get_cluster_version",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(f"Action '{action}' not supported.")

        actions = {
            "get_projects":      self._get_projects,
            "create_project":    self._create_project,
            "delete_project":    self._delete_project,
            "get_pods":          self._get_pods,
            "get_deployments":   self._get_deployments,
            "get_services":      self._get_services,
            "get_routes":        self._get_routes,
            "get_builds":        self._get_builds,
            "get_build_configs": self._get_build_configs,
            "get_image_streams": self._get_image_streams,
            "deploy_app":        self._deploy_app,
            "new_app":           self._new_app,
            "expose_service":    self._expose_service,
            "scale_deployment":  self._scale_deployment,
            "rollout_latest":    self._rollout_latest,
            "get_operators":     self._get_operators,
            "install_operator":  self._install_operator,
            "apply_manifest":    self._apply_manifest,
            "get_events":        self._get_events,
            "whoami":            self._whoami,
            "get_cluster_version": self._get_cluster_version,
        }
        return actions[action](params)

    # --- Implementaciones ---

    def _ns(self, params: dict) -> list:
        ns = params.get("namespace") or params.get("project")
        return ["-n", ns] if ns else []

    def _get_projects(self, params: dict) -> dict:
        result = self._run(["get", "projects"])
        if result.get("success") and "data" in result:
            projects = [
                {
                    "name": p["metadata"]["name"],
                    "status": p["status"].get("phase", "Unknown"),
                    "display_name": p["metadata"].get("annotations", {})
                        .get("openshift.io/display-name", ""),
                }
                for p in result["data"].get("items", [])
            ]
            return {"projects": projects, "total": len(projects)}
        return result

    def _create_project(self, params: dict) -> dict:
        name = params.get("name")
        display = params.get("display_name", name)
        description = params.get("description", "")
        args = ["new-project", name, f"--display-name={display}"]
        if description:
            args.append(f"--description={description}")
        result = self._run(args, output_json=False)
        print(f"[OpenshiftTool] Project '{name}': {'created' if result['success'] else 'failed'}")
        return result

    def _delete_project(self, params: dict) -> dict:
        name = params.get("name")
        result = self._run(["delete", "project", name], output_json=False)
        return result

    def _get_pods(self, params: dict) -> dict:
        result = self._run(["get", "pods"] + self._ns(params))
        if result.get("success") and "data" in result:
            pods = [
                {
                    "name": p["metadata"]["name"],
                    "namespace": p["metadata"]["namespace"],
                    "status": p["status"].get("phase", "Unknown"),
                }
                for p in result["data"].get("items", [])
            ]
            return {"pods": pods, "total": len(pods)}
        return result

    def _get_deployments(self, params: dict) -> dict:
        result = self._run(["get", "deploymentconfigs"] + self._ns(params))
        if result.get("success") and "data" in result:
            dcs = [
                {
                    "name": d["metadata"]["name"],
                    "namespace": d["metadata"]["namespace"],
                    "replicas": d["spec"].get("replicas", 0),
                    "ready": d["status"].get("readyReplicas", 0),
                }
                for d in result["data"].get("items", [])
            ]
            return {"deployments": dcs, "total": len(dcs)}
        return result

    def _get_services(self, params: dict) -> dict:
        result = self._run(["get", "services"] + self._ns(params))
        if result.get("success") and "data" in result:
            services = [
                {
                    "name": s["metadata"]["name"],
                    "namespace": s["metadata"]["namespace"],
                    "type": s["spec"].get("type"),
                    "cluster_ip": s["spec"].get("clusterIP"),
                }
                for s in result["data"].get("items", [])
            ]
            return {"services": services, "total": len(services)}
        return result

    def _get_routes(self, params: dict) -> dict:
        result = self._run(["get", "routes"] + self._ns(params))
        if result.get("success") and "data" in result:
            routes = [
                {
                    "name": r["metadata"]["name"],
                    "namespace": r["metadata"]["namespace"],
                    "host": r["spec"].get("host", ""),
                    "tls": bool(r["spec"].get("tls")),
                }
                for r in result["data"].get("items", [])
            ]
            return {"routes": routes, "total": len(routes)}
        return result

    def _get_builds(self, params: dict) -> dict:
        result = self._run(["get", "builds"] + self._ns(params))
        if result.get("success") and "data" in result:
            builds = [
                {
                    "name": b["metadata"]["name"],
                    "status": b["status"].get("phase", "Unknown"),
                }
                for b in result["data"].get("items", [])
            ]
            return {"builds": builds, "total": len(builds)}
        return result

    def _get_build_configs(self, params: dict) -> dict:
        result = self._run(["get", "buildconfigs"] + self._ns(params))
        if result.get("success") and "data" in result:
            bcs = [
                {"name": b["metadata"]["name"], "namespace": b["metadata"]["namespace"]}
                for b in result["data"].get("items", [])
            ]
            return {"build_configs": bcs, "total": len(bcs)}
        return result

    def _get_image_streams(self, params: dict) -> dict:
        result = self._run(["get", "imagestreams"] + self._ns(params))
        if result.get("success") and "data" in result:
            streams = [
                {"name": i["metadata"]["name"], "namespace": i["metadata"]["namespace"]}
                for i in result["data"].get("items", [])
            ]
            return {"image_streams": streams, "total": len(streams)}
        return result

    def _deploy_app(self, params: dict) -> dict:
        """Despliega una aplicación en OpenShift."""
        name = params.get("name")
        image = params.get("image")
        ns_args = self._ns(params)
        result = self._run(
            ["new-app", f"--name={name}", image] + ns_args,
            output_json=False
        )
        print(f"[OpenshiftTool] Deploy '{name}': {'OK' if result['success'] else 'FAILED'}")
        return result

    def _new_app(self, params: dict) -> dict:
        """Crea una nueva app desde template o imagen."""
        template = params.get("template") or params.get("image")
        ns_args = self._ns(params)
        args = ["new-app", template] + ns_args
        if params.get("name"):
            args.append(f"--name={params['name']}")
        return self._run(args, output_json=False)

    def _expose_service(self, params: dict) -> dict:
        """Expone un servicio creando una Route."""
        name = params.get("name")
        ns_args = self._ns(params)
        result = self._run(["expose", "service", name] + ns_args, output_json=False)
        print(f"[OpenshiftTool] Route for '{name}': {'created' if result['success'] else 'failed'}")
        return result

    def _scale_deployment(self, params: dict) -> dict:
        name = params.get("name")
        replicas = params.get("replicas", 1)
        ns_args = self._ns(params)
        result = self._run(
            ["scale", "dc", name, f"--replicas={replicas}"] + ns_args,
            output_json=False
        )
        print(f"[OpenshiftTool] Scaled '{name}' to {replicas} replicas")
        return result

    def _rollout_latest(self, params: dict) -> dict:
        name = params.get("name")
        ns_args = self._ns(params)
        return self._run(["rollout", "latest", name] + ns_args, output_json=False)

    def _get_operators(self, params: dict) -> dict:
        result = self._run(["get", "csv", "--all-namespaces"])
        if result.get("success") and "data" in result:
            operators = [
                {
                    "name": o["metadata"]["name"],
                    "namespace": o["metadata"]["namespace"],
                    "phase": o["status"].get("phase", "Unknown"),
                    "display": o["spec"].get("displayName", ""),
                }
                for o in result["data"].get("items", [])
            ]
            return {"operators": operators, "total": len(operators)}
        return result

    def _install_operator(self, params: dict) -> dict:
        """Instala un operador via subscription."""
        name = params.get("name")
        source = params.get("source", "redhat-operators")
        channel = params.get("channel", "stable")
        namespace = params.get("namespace", "openshift-operators")

        subscription = f"""
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: {name}
  namespace: {namespace}
spec:
  channel: {channel}
  name: {name}
  source: {source}
  sourceNamespace: openshift-marketplace
"""
        import tempfile, os
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            f.write(subscription)
            tmp_path = f.name

        result = self._run(["apply", "-f", tmp_path], output_json=False)
        os.unlink(tmp_path)
        print(f"[OpenshiftTool] Operator '{name}': {'installed' if result['success'] else 'failed'}")
        return result

    def _apply_manifest(self, params: dict) -> dict:
        file_path = params.get("file")
        return self._run(["apply", "-f", file_path], output_json=False)

    def _get_events(self, params: dict) -> dict:
        return self._run(["get", "events"] + self._ns(params))

    def _whoami(self, params: dict) -> dict:
        result = self._run(["whoami"], output_json=False)
        return {"user": result.get("stdout", "").strip(), "success": result["success"]}

    def _get_cluster_version(self, params: dict) -> dict:
        result = self._run(["get", "clusterversion"])
        if result.get("success") and "data" in result:
            items = result["data"].get("items", [])
            if items:
                cv = items[0]
                return {
                    "version": cv["status"].get("desired", {}).get("version"),
                    "channel": cv["spec"].get("channel"),
                    "available_updates": len(cv["status"].get("availableUpdates", [])),
                }
        return result