# core/interfaces/execution_plan.py
# Contrato de ExecutionPlan — el objeto más visible para el usuario.
# Implementa exactamente lo definido en docs/EXECUTION_PLAN.md

import uuid
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class PlanStatus(str, Enum):
    """
    Ciclo de vida de un Execution Plan. Ver EXECUTION_PLAN.md §3.

    CREATED -> VALIDATED -> PENDING_APPROVAL -> APPROVED -> RUNNING -> COMPLETED
       |            |              |                            |
       |            |              +-> REJECTED                 +-> FAILED -> ROLLED_BACK
       |            +-> INVALID
       +-> CANCELLED (en cualquier punto antes de RUNNING)

    PAUSED es alcanzable solo desde RUNNING (EXECUTION_PLAN.md §7).
    """
    CREATED = "created"
    VALIDATED = "validated"
    INVALID = "invalid"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExecutionPlan:
    """
    Traducción de un Intent del usuario en una secuencia concreta de Tasks,
    antes de ejecutarse. Es lo que el usuario revisa y aprueba.

    Contrato completo: docs/EXECUTION_PLAN.md

    Uso:
        plan = ExecutionPlan(
            intent="Crea una plataforma SaaS en AWS con EKS y CI/CD",
            tasks=["task-001", "task-002", "task-003"],
            task_graph={"task-001": [], "task-002": ["task-001"], "task-003": ["task-002"]},
        )
    """

    intent: str
    tasks: list = field(default_factory=list)
    task_graph: dict = field(default_factory=dict)

    id: str = field(default_factory=lambda: f"exec-{datetime.now().strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:6]}")
    status: PlanStatus = PlanStatus.CREATED

    requires_approval: bool = False
    approved_by: str = None
    estimated_impact: ImpactLevel = ImpactLevel.LOW

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str = None
    completed_at: str = None

    rollback_plan: list = field(default_factory=list)
    result_summary: dict = None
    audit_trail: list = field(default_factory=list)

    def transition(self, new_status: PlanStatus, reason: str = "") -> None:
        """
        Cambia el estado del plan y registra el cambio en audit_trail.
        Ver EXECUTION_PLAN.md §3 para las transiciones válidas.
        """
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now().isoformat()

        if new_status == PlanStatus.RUNNING and self.started_at is None:
            self.started_at = self.updated_at
        if new_status in (PlanStatus.COMPLETED, PlanStatus.FAILED,
                          PlanStatus.ROLLED_BACK, PlanStatus.CANCELLED):
            self.completed_at = self.updated_at

        self.audit_trail.append({
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason,
            "timestamp": self.updated_at,
        })

    def has_cycles(self) -> bool:
        """
        Detecta dependencias circulares en task_graph antes de validar.
        Ver EXECUTION_PLAN.md §4.
        """
        visited, stack = set(), set()

        def visit(node):
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for dep in self.task_graph.get(node, []):
                if visit(dep):
                    return True
            stack.remove(node)
            return False

        return any(visit(node) for node in self.task_graph)

    def topological_order(self) -> list:
        """
        Resuelve el orden de ejecución por niveles, respetando dependencias.
        Ver WORKFLOW_ENGINE.md §3. Tasks del mismo nivel pueden paralelizarse.

        Retorna: lista de niveles, cada nivel es una lista de task ids.
        """
        remaining = dict(self.task_graph)
        levels = []

        while remaining:
            level = [
                task_id for task_id, deps in remaining.items()
                if all(d not in remaining for d in deps)
            ]
            if not level:
                raise ValueError("Cycle detected — cannot resolve topological order")
            levels.append(level)
            for task_id in level:
                remaining.pop(task_id)

        return levels

    def is_terminal(self) -> bool:
        """True si el plan ya no puede cambiar de estado."""
        return self.status in (
            PlanStatus.COMPLETED,
            PlanStatus.FAILED,
            PlanStatus.ROLLED_BACK,
            PlanStatus.CANCELLED,
        )

    def summary(self) -> dict:
        """Resumen legible para mostrar al usuario antes de aprobar."""
        return {
            "id": self.id,
            "intent": self.intent,
            "status": self.status.value,
            "total_tasks": len(self.tasks),
            "requires_approval": self.requires_approval,
            "estimated_impact": self.estimated_impact.value,
            "approved_by": self.approved_by,
        }

    def __repr__(self):
        return f"ExecutionPlan(id={self.id}, status={self.status.value}, tasks={len(self.tasks)})"