# tools/cloud/azure/azure_tool.py
# Implementación de la Azure Tool para LRA AI Platform.
# Conecta la plataforma con Azure real via azure-sdk-for-python.

import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from tools.cloud.base_cloud_tool import BaseCloudTool


class AzureTool(BaseCloudTool):
    """
    Tool para interactuar con Azure via azure-sdk-for-python.

    Credenciales: usa DefaultAzureCredential — detecta automáticamente
    az CLI, variables de entorno, managed identity, etc.
    Nunca hardcodeadas.

    Uso:
        azure = AzureTool()
        azure.execute("list_resource_groups", {})
        azure.execute("list_aks_clusters", {})
        azure.execute("list_storage_accounts", {})
    """

    def __init__(self):
        super().__init__(name="azure", provider="azure", version="1.0.0")
        self._subscription_id = os.getenv(
            "AZURE_SUBSCRIPTION_ID",
            self._get_subscription_id_from_cli()
        )
        self._credential = None
        self._clients: dict = {}

    def _get_subscription_id_from_cli(self) -> str:
        try:
            import subprocess
            import shutil
            az_path = shutil.which("az") or r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
            result = subprocess.run(
                [az_path, "account", "show", "--query", "id", "-o", "tsv"],
                capture_output=True, text=True, shell=True
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _get_credential(self) -> DefaultAzureCredential:
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential

    def _get_client(self, client_class, **kwargs):
        key = client_class.__name__
        if key not in self._clients:
            self._clients[key] = client_class(
                self._get_credential(),
                self._subscription_id,
                **kwargs
            )
        return self._clients[key]

    def validate(self) -> bool:
        try:
            identity = self.get_identity()
            print(f"[AzureTool] Authenticated: {identity.get('subscription')}")
            return True
        except Exception as e:
            print(f"[AzureTool] Validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        return [
            "get_identity",
            "list_resource_groups",
            "list_virtual_machines",
            "list_storage_accounts",
            "list_virtual_networks",
            "list_aks_clusters",
            "describe_aks_cluster",
            "list_acr_registries",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(
                f"Action '{action}' not supported. "
                f"Available: {self.get_capabilities()}"
            )

        actions = {
            "get_identity":           self._get_identity_action,
            "list_resource_groups":   self._list_resource_groups,
            "list_virtual_machines":  self._list_virtual_machines,
            "list_storage_accounts":  self._list_storage_accounts,
            "list_virtual_networks":  self._list_virtual_networks,
            "list_aks_clusters":      self._list_aks_clusters,
            "describe_aks_cluster":   self._describe_aks_cluster,
            "list_acr_registries":    self._list_acr_registries,
        }

        try:
            return actions[action](params)
        except Exception as e:
            return {"error": str(e), "action": action}

    # --- BaseCloudTool interface ---

    def get_identity(self) -> dict:
        return self._get_identity_action({})

    def list_compute(self, params: dict = None) -> dict:
        return self._list_virtual_machines(params or {})

    def list_storage(self, params: dict = None) -> dict:
        return self._list_storage_accounts(params or {})

    def list_networks(self, params: dict = None) -> dict:
        return self._list_virtual_networks(params or {})

    def list_kubernetes(self, params: dict = None) -> dict:
        return self._list_aks_clusters(params or {})

    def list_registries(self, params: dict = None) -> dict:
        return self._list_acr_registries(params or {})

    # --- Implementaciones ---

    def _get_identity_action(self, params: dict) -> dict:
        import subprocess
        import json
        import shutil

        # Busca az en el PATH o en la ubicación estándar de Windows
        az_path = shutil.which("az") or r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

        result = subprocess.run(
            [az_path, "account", "show", "--query",
             "{subscription:name, id:id, user:user.name}", "-o", "json"],
            capture_output=True, text=True, shell=True
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        return json.loads(result.stdout)

    def _list_resource_groups(self, params: dict) -> dict:
        client = ResourceManagementClient(
            self._get_credential(), self._subscription_id
        )
        groups = [{"name": rg.name, "location": rg.location}
                  for rg in client.resource_groups.list()]
        return {"resource_groups": groups, "total": len(groups)}

    def _list_virtual_machines(self, params: dict) -> dict:
        client = self._get_client(ComputeManagementClient)
        vms = []
        for vm in client.virtual_machines.list_all():
            vms.append({
                "name": vm.name,
                "location": vm.location,
                "size": vm.hardware_profile.vm_size if vm.hardware_profile else "unknown",
            })
        return {"virtual_machines": vms, "total": len(vms)}

    def _list_storage_accounts(self, params: dict) -> dict:
        client = self._get_client(StorageManagementClient)
        accounts = [{"name": sa.name, "location": sa.location,
                     "kind": sa.kind}
                    for sa in client.storage_accounts.list()]
        return {"storage_accounts": accounts, "total": len(accounts)}

    def _list_virtual_networks(self, params: dict) -> dict:
        client = self._get_client(NetworkManagementClient)
        vnets = [{"name": vn.name, "location": vn.location,
                  "address_space": vn.address_space.address_prefixes
                  if vn.address_space else []}
                 for vn in client.virtual_networks.list_all()]
        return {"virtual_networks": vnets, "total": len(vnets)}

    def _list_aks_clusters(self, params: dict) -> dict:
        client = self._get_client(ContainerServiceClient)
        clusters = [{"name": c.name, "location": c.location,
                     "k8s_version": c.kubernetes_version,
                     "status": c.provisioning_state}
                    for c in client.managed_clusters.list()]
        return {"clusters": clusters, "total": len(clusters)}

    def _describe_aks_cluster(self, params: dict) -> dict:
        name = params.get("name")
        resource_group = params.get("resource_group")
        client = self._get_client(ContainerServiceClient)
        cluster = client.managed_clusters.get(resource_group, name)
        return {
            "name": cluster.name,
            "location": cluster.location,
            "k8s_version": cluster.kubernetes_version,
            "status": cluster.provisioning_state,
            "node_count": sum(
                p.count for p in cluster.agent_pool_profiles or []
            ),
        }

    def _list_acr_registries(self, params: dict) -> dict:
        try:
            from azure.mgmt.containerregistry import ContainerRegistryManagementClient
            client = ContainerRegistryManagementClient(
                self._get_credential(), self._subscription_id
            )
            registries = [{"name": r.name, "location": r.location,
                           "login_server": r.login_server}
                          for r in client.registries.list()]
            return {"registries": registries, "total": len(registries)}
        except Exception as e:
            return {"registries": [], "total": 0, "note": str(e)}