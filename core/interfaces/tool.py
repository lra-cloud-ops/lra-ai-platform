# core/interfaces/tool.py
# Contrato base para todas las herramientas de la plataforma.
# Cualquier Tool (GitHub, AWS, kubectl...) debe heredar de esta clase.

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    Interfaz base para todas las herramientas de LRA AI Platform.

    Una Tool es cualquier módulo que ejecuta acciones reales:
    - Llamar a la API de GitHub
    - Ejecutar comandos de AWS CLI
    - Correr kubectl contra un cluster
    - Aplicar un plan de Terraform

    Toda Tool debe implementar estos métodos obligatoriamente.
    """

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = True

    @abstractmethod
    def execute(self, action: str, params: dict) -> Any:
        """
        Ejecuta una acción con los parámetros dados.

        Ejemplo:
            github_tool.execute("create_repo", {"name": "mi-repo"})
            aws_tool.execute("create_eks_cluster", {"name": "prod", "region": "eu-west-1"})
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Valida que la herramienta está correctamente configurada.
        Comprueba credenciales, conectividad, permisos, etc.

        Retorna True si está lista, False si hay algún problema.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """
        Retorna la lista de acciones que esta herramienta puede ejecutar.

        Ejemplo GitHub Tool:
            ["create_repo", "clone_repo", "create_pr", "merge_pr"]

        Ejemplo AWS Tool:
            ["create_eks", "create_vpc", "deploy_lambda", "create_s3"]
        """
        pass

    def __repr__(self):
        return f"Tool(name={self.name}, version={self.version}, enabled={self.enabled})"