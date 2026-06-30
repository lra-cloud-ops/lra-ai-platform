# tools/cloud/base_cloud_tool.py
# Contrato base para todas las Cloud Tools de LRA AI Platform.
# Cualquier cloud nueva (AWS, Azure, GCP, VMware, Cloudflare...)
# hereda de esta clase y sigue el mismo patrón.

from abc import abstractmethod
from core.interfaces.tool import Tool


class BaseCloudTool(Tool):
    """
    Contrato base para todas las Cloud Tools.

    Garantiza que cualquier cloud tool implementa las mismas
    operaciones fundamentales, independientemente del proveedor.
    Esto permite que el CloudArchitectAgent trabaje con cualquier
    cloud sin conocer los detalles internos de cada una.

    Operaciones que toda cloud tool debe implementar:
        validate()              → verifica credenciales
        get_capabilities()      → lista acciones disponibles
        execute(action, params) → ejecuta una acción

    Operaciones cloud-específicas que se recomienda implementar:
        list_compute()     → lista instancias/VMs
        list_storage()     → lista buckets/blobs/discos
        list_networks()    → lista VPCs/VNets
        list_kubernetes()  → lista clusters K8s gestionados
        list_registries()  → lista registros de contenedores
        get_identity()     → retorna la identidad autenticada
        generate_report()  → genera informe de infraestructura
    """

    def __init__(self, name: str, provider: str, version: str = "1.0.0"):
        super().__init__(name=name, version=version)
        self.provider = provider   # "aws" | "azure" | "gcp" | "vmware" | ...

    @abstractmethod
    def get_identity(self) -> dict:
        """
        Retorna la identidad autenticada en este proveedor.
        Equivalente a:
            AWS   → sts.get_caller_identity()
            Azure → az account show
            GCP   → gcloud auth list
        """
        pass

    @abstractmethod
    def list_compute(self, params: dict = None) -> dict:
        """Lista instancias de cómputo (EC2, VMs, GCE instances)."""
        pass

    @abstractmethod
    def list_storage(self, params: dict = None) -> dict:
        """Lista almacenamiento (S3 buckets, Storage Accounts, GCS buckets)."""
        pass

    @abstractmethod
    def list_networks(self, params: dict = None) -> dict:
        """Lista redes virtuales (VPC, VNet, GCP VPC)."""
        pass

    @abstractmethod
    def list_kubernetes(self, params: dict = None) -> dict:
        """Lista clusters Kubernetes gestionados (EKS, AKS, GKE)."""
        pass

    @abstractmethod
    def list_registries(self, params: dict = None) -> dict:
        """Lista registros de contenedores (ECR, ACR, Artifact Registry)."""
        pass

    def generate_report(self, params: dict = None) -> dict:
        """
        Genera un informe de infraestructura recopilando todos
        los recursos del proveedor. Implementación por defecto
        que llama a los métodos abstractos — puede ser sobreescrita.
        """
        params = params or {}
        print(f"[{self.__class__.__name__}] Generating infrastructure report...")

        identity  = self.get_identity()
        compute   = self.list_compute(params)
        storage   = self.list_storage(params)
        networks  = self.list_networks(params)
        k8s       = self.list_kubernetes(params)
        registries = self.list_registries(params)

        return {
            "provider": self.provider,
            "identity": identity,
            "compute": compute,
            "storage": storage,
            "networks": networks,
            "kubernetes": k8s,
            "registries": registries,
            "summary": {
                "compute_count":    compute.get("total", 0),
                "storage_count":    storage.get("total", 0),
                "network_count":    networks.get("total", 0),
                "kubernetes_count": k8s.get("total", 0),
                "registry_count":   registries.get("total", 0),
            }
        }

    def __repr__(self):
        return f"{self.__class__.__name__}(provider={self.provider}, version={self.version})"