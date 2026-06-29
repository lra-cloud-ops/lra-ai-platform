# core/interfaces/memory.py
# Contrato base para el sistema de memoria de la plataforma.
# Cada proyecto tiene su propia memoria independiente.

from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """
    Interfaz base para el sistema de memoria de LRA AI Platform.

    La memoria permite que los agentes recuerden el contexto
    de cada proyecto entre sesiones de trabajo.

    Cada proyecto tiene su propia memoria independiente:
        memory/lracloudops/
        memory/aws-terraform-devops/
        memory/k8s-devops-platform/

    La memoria almacena:
        - Stack tecnológico del proyecto
        - Decisiones de arquitectura tomadas
        - Historial de tareas ejecutadas
        - Estado actual del proyecto
        - Errores conocidos y sus soluciones
        - Contactos y responsables
    """

    def __init__(self, project: str):
        self.project = project

    @abstractmethod
    def save(self, key: str, value: Any) -> None:
        """
        Guarda un dato en la memoria del proyecto.

        Ejemplo:
            memory.save("stack", ["Astro", "Tailwind", "Cloudflare"])
            memory.save("last_deploy", "2026-06-29")
            memory.save("cluster_name", "lra-prod-eks")
        """
        pass

    @abstractmethod
    def load(self, key: str) -> Any:
        """
        Recupera un dato de la memoria del proyecto.

        Retorna None si la clave no existe.

        Ejemplo:
            stack = memory.load("stack")
            → ["Astro", "Tailwind", "Cloudflare"]
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Elimina un dato de la memoria del proyecto.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Limpia toda la memoria del proyecto.
        Útil cuando se reinicia o re-registra un proyecto.
        """
        pass

    @abstractmethod
    def list_keys(self) -> list[str]:
        """
        Retorna todas las claves almacenadas en la memoria del proyecto.
        Útil para debugging y para el dashboard.

        Ejemplo:
            memory.list_keys()
            → ["stack", "last_deploy", "cluster_name", "team"]
        """
        pass

    def __repr__(self):
        return f"Memory(project={self.project})"