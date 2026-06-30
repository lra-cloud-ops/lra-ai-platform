# core/memory/memory_resolver.py
# Implementa la jerarquía de resolución de MEMORY.md §3.
# El valor más específico siempre gana.

from core.memory.organization_memory import OrganizationMemory
from core.memory.project_memory import ProjectMemory
from core.memory.workflow_memory import WorkflowMemory
from core.memory.conversation_memory import ConversationMemory


class MemoryResolver:
    """
    Resuelve el valor de una clave consultando los 4 tipos de memoria
    en orden de especificidad, de más general a más específico.

    Jerarquía (MEMORY.md §3):
        Organization → Project → Workflow → Conversation
        (base)                              (máxima prioridad)

    Uso:
        resolver = MemoryResolver(org_memory, project_memory,
                                   workflow_memory, conv_memory)
        region = resolver.resolve("default_region")
        # Busca en Conversation primero, luego Workflow, Project, Organization
    """

    def __init__(
        self,
        organization: OrganizationMemory,
        project: ProjectMemory = None,
        workflow: WorkflowMemory = None,
        conversation: ConversationMemory = None,
    ):
        self.organization = organization
        self.project = project
        self.workflow = workflow
        self.conversation = conversation

    def resolve(self, key: str, default=None):
        """
        Retorna el valor más específico disponible para la clave.
        Orden de búsqueda: Conversation > Workflow > Project > Organization

        Ejemplo (MEMORY.md §3):
            Organization: default_region = "eu-west-1"
            Conversation: default_region = "eu-south-2"  (usuario lo pidió)
            → resolve("default_region") retorna "eu-south-2"
        """
        sources = [
            self.conversation,
            self.workflow,
            self.project,
            self.organization,
        ]

        for source in sources:
            if source is None:
                continue
            value = source.load(key)
            if value is not None:
                return value

        return default

    def resolve_all(self, key: str) -> dict:
        """
        Retorna el valor de la clave en cada tipo de memoria disponible.
        Útil para debugging — muestra de dónde viene cada valor.

        Ejemplo:
            resolver.resolve_all("default_region")
            → {
                "organization": "eu-west-1",
                "project": None,
                "workflow": None,
                "conversation": "eu-south-2",
                "resolved": "eu-south-2"
              }
        """
        result = {
            "organization": self.organization.load(key),
            "project": self.project.load(key) if self.project else None,
            "workflow": self.workflow.load(key) if self.workflow else None,
            "conversation": self.conversation.load(key) if self.conversation else None,
        }
        result["resolved"] = self.resolve(key)
        return result

    def snapshot(self) -> dict:
        """
        Retorna el contexto efectivo resolviendo todas las claves
        conocidas en todos los tipos activos.
        """
        all_keys = set()
        for source in [self.organization, self.project, self.workflow, self.conversation]:
            if source:
                all_keys.update(source.list_keys())

        return {key: self.resolve(key) for key in all_keys}

    def __repr__(self):
        active = sum(1 for s in [self.organization, self.project,
                                   self.workflow, self.conversation] if s)
        return f"MemoryResolver(active_sources={active})"