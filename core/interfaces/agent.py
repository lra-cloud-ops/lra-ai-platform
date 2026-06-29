# core/interfaces/agent.py
# Contrato base para todos los agentes de la plataforma.
# Cualquier Agent (DevOps, Security, Architect...) debe heredar de esta clase.

from abc import ABC, abstractmethod
from typing import Any
from core.interfaces.tool import Tool


class Agent(ABC):
    """
    Interfaz base para todos los agentes de LRA AI Platform.

    Un Agent es un ingeniero virtual especializado que:
    - Tiene un rol definido (DevOps, Security, Architect...)
    - Usa un conjunto de Tools para ejecutar acciones reales
    - Recibe tareas, las procesa y retorna resultados
    - Mantiene contexto y memoria de su trabajo

    Ejemplos:
        DevOpsAgent  → usa: github, docker, kubernetes, helm, argocd
        SecurityAgent → usa: trivy, checkov, vault, snyk
        CloudArchitect → usa: aws, azure, gcp, terraform
    """

    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description
        self.tools: dict[str, Tool] = {}
        self.active = True

    def register_tool(self, tool: Tool) -> None:
        """
        Registra una herramienta en el agente.
        Solo puede usar herramientas que hayan sido registradas.

        Ejemplo:
            devops_agent.register_tool(github_tool)
            devops_agent.register_tool(kubernetes_tool)
        """
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        """
        Retorna una herramienta por nombre.
        Lanza error si el agente no tiene acceso a esa herramienta.
        """
        if name not in self.tools:
            raise ValueError(f"Agent '{self.name}' does not have access to tool '{name}'")
        return self.tools[name]

    @abstractmethod
    def run(self, task: str, context: dict = {}) -> Any:
        """
        Ejecuta una tarea.

        Ejemplo:
            devops_agent.run("deploy application", {"repo": "lracloudops", "env": "prod"})
            security_agent.run("scan repository", {"repo": "aws-terraform-devops"})
        """
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """
        Retorna el estado actual del agente.
        Útil para el dashboard y el supervisor.
        """
        pass

    def __repr__(self):
        tools_list = list(self.tools.keys())
        return f"Agent(name={self.name}, role={self.role}, tools={tools_list})"