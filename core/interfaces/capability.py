# core/interfaces/capability.py
# Contrato base para todas las capabilities de la plataforma.
# Una Capability es una habilidad concreta que un agente puede ejecutar.

from abc import ABC, abstractmethod
from typing import Any


class Capability(ABC):
    """
    Interfaz base para todas las capabilities de LRA AI Platform.

    Una Capability representa una habilidad de alto nivel:
    - provision_infrastructure  → crea VPCs, clusters, bases de datos
    - deploy_application        → despliega en Kubernetes, ECS, OpenShift
    - review_pull_request       → analiza código, seguridad, calidad
    - generate_documentation    → crea README, ADR, Runbooks
    - scan_security             → detecta vulnerabilidades y misconfiguraciones

    Cada Capability usa internamente las Tools necesarias para completar
    su trabajo. El agente no necesita saber qué Tools usa cada Capability.
    """

    def __init__(self, name: str, description: str, required_tools: list[str]):
        self.name = name
        self.description = description
        self.required_tools = required_tools  # Tools que esta capability necesita

    @abstractmethod
    def execute(self, params: dict, tools: dict) -> Any:
        """
        Ejecuta la capability con los parámetros y herramientas dados.

        Args:
            params: Parámetros específicos de la tarea.
            tools:  Diccionario de Tools disponibles del agente.

        Ejemplo:
            deploy_capability.execute(
                params={"app": "lracloudops", "env": "prod", "replicas": 3},
                tools={"kubernetes": k8s_tool, "helm": helm_tool}
            )
        """
        pass

    @abstractmethod
    def validate_params(self, params: dict) -> bool:
        """
        Valida que los parámetros son correctos antes de ejecutar.
        Evita errores a mitad de una operación crítica.

        Ejemplo:
            Si deploy_application necesita 'app' y 'env',
            este método verifica que ambos estén presentes y sean válidos.
        """
        pass

    def get_required_tools(self) -> list[str]:
        """
        Retorna las Tools que esta Capability necesita para funcionar.
        El Agent Manager usa esto para verificar que el agente
        tiene todas las herramientas necesarias antes de ejecutar.
        """
        return self.required_tools

    def __repr__(self):
        return f"Capability(name={self.name}, required_tools={self.required_tools})"