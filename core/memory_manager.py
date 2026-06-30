# core/memory_manager.py
# Facade que gestiona los 4 tipos de memoria de la plataforma.
# Ver MEMORY.md para el diseño completo.

import shutil
from pathlib import Path
from core.memory.organization_memory import OrganizationMemory
from core.memory.project_memory import ProjectMemory
from core.memory.workflow_memory import WorkflowMemory
from core.memory.conversation_memory import ConversationMemory
from core.memory.memory_resolver import MemoryResolver


class MemoryManager:
    """
    Gestiona los 4 tipos de memoria de LRA AI Platform.

    Uso:
        mm = MemoryManager()

        # Organization (estándares de la org)
        org = mm.get_organization_memory()
        org.load("naming_convention")   # → "kebab-case"

        # Project (contexto de un proyecto)
        proj = mm.get_project_memory("lracloudops")
        proj.save("stack", ["Astro", "Tailwind"])

        # Workflow (estado de un Execution Plan)
        wf = mm.get_workflow_memory("exec-2026-06-30-001")
        wf.save("vpc_id", "vpc-0a1b2c3d")

        # Conversation (sesión actual)
        conv = mm.get_conversation_memory("session-xyz")
        conv.add_message("user", "Crea un proyecto nuevo")

        # Resolver (jerarquía completa)
        resolver = mm.get_resolver("lracloudops", "exec-001", "session-xyz")
        resolver.resolve("default_region")  # gana el más específico
    """

    def __init__(self, base_dir: str = "memory"):
        self.base_dir = base_dir
        self._org_memory: OrganizationMemory = None
        self._projects: dict = {}
        self._workflows: dict = {}
        self._conversations: dict = {}

    def get_organization_memory(self) -> OrganizationMemory:
        """Retorna la memoria de organización (singleton)."""
        if self._org_memory is None:
            self._org_memory = OrganizationMemory(self.base_dir)
        return self._org_memory

    def get_project_memory(self, project: str) -> ProjectMemory:
        """Retorna la memoria de un proyecto (crea si no existe)."""
        if project not in self._projects:
            self._projects[project] = ProjectMemory(project, self.base_dir)
        return self._projects[project]

    # Alias para compatibilidad con código existente (v1.0)
    def get_memory(self, project: str) -> ProjectMemory:
        return self.get_project_memory(project)

    def get_workflow_memory(self, plan_id: str) -> WorkflowMemory:
        """Retorna la memoria de un Execution Plan en curso."""
        if plan_id not in self._workflows:
            self._workflows[plan_id] = WorkflowMemory(plan_id, self.base_dir)
        return self._workflows[plan_id]

    def get_conversation_memory(self, session_id: str) -> ConversationMemory:
        """Retorna la memoria de una sesión de conversación."""
        if session_id not in self._conversations:
            self._conversations[session_id] = ConversationMemory(session_id)
        return self._conversations[session_id]

    def get_resolver(
        self,
        project: str = None,
        plan_id: str = None,
        session_id: str = None,
    ) -> MemoryResolver:
        """
        Retorna un MemoryResolver con los tipos de memoria relevantes.
        Siempre incluye OrganizationMemory como base.
        """
        return MemoryResolver(
            organization=self.get_organization_memory(),
            project=self.get_project_memory(project) if project else None,
            workflow=self.get_workflow_memory(plan_id) if plan_id else None,
            conversation=self.get_conversation_memory(session_id) if session_id else None,
        )

    def promote_workflow_to_project(
        self, plan_id: str, project: str, keys: list = None
    ) -> None:
        """
        Promueve valores de WorkflowMemory a ProjectMemory al completarse
        el plan. Ver MEMORY.md §8.

        Si keys=None, promueve todos los valores del workflow.
        """
        wf_memory = self.get_workflow_memory(plan_id)
        proj_memory = self.get_project_memory(project)
        snapshot = wf_memory.archive()

        to_promote = {k: v for k, v in snapshot.items()
                      if keys is None or k in keys}

        for key, value in to_promote.items():
            proj_memory.save(key, value)

    def list_projects(self) -> list:
        """Retorna todos los proyectos que tienen memoria en disco."""
        base = Path(self.base_dir)
        if not base.exists():
            return []
        return [
            d.name for d in base.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]

    def delete_project(self, project: str) -> None:
        """Elimina la memoria de un proyecto."""
        project_dir = Path(self.base_dir) / project
        if project_dir.exists():
            shutil.rmtree(project_dir)
        self._projects.pop(project, None)

    def summary(self) -> dict:
        """Resumen del estado del MemoryManager."""
        return {
            "projects": self.list_projects(),
            "loaded_projects": list(self._projects.keys()),
            "loaded_workflows": list(self._workflows.keys()),
            "loaded_conversations": list(self._conversations.keys()),
            "org_memory_keys": self.get_organization_memory().list_keys(),
        }

    def __repr__(self):
        return f"MemoryManager(projects={self.list_projects()})"