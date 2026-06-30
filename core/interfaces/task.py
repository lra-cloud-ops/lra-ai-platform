# core/interfaces/task.py
# Contrato de Task — la unidad atómica de trabajo de LRA AI Platform.
# Implementa exactamente lo definido en docs/TASK_ENGINE.md

import uuid
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    """
    Ciclo de vida de una Task. Ver TASK_ENGINE.md §3.

    PENDING -> APPROVED -> RUNNING -> COMPLETED
                  |            |
                  |            +-> FAILED -> RETRYING -> RUNNING
                  |                   |
                  |                   +-> CANCELLED
                  +-> REJECTED
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RetryPolicy:
    """Ver TASK_ENGINE.md §6."""
    max_attempts: int = 1
    backoff_seconds: int = 5
    backoff_multiplier: float = 1.0
    attempts_made: int = 0

    def can_retry(self) -> bool:
        return self.attempts_made < self.max_attempts

    def next_backoff(self) -> float:
        return self.backoff_seconds * (self.backoff_multiplier ** self.attempts_made)


@dataclass
class Task:
    """
    Unidad atómica de trabajo de LRA AI Platform.

    Todo lo que la plataforma hace —crear un repo, escanear seguridad,
    desplegar una app, generar documentación— es una Task.

    Contrato completo: docs/TASK_ENGINE.md

    Uso:
        task = Task(
            type="create_repository",
            params={"name": "client-api", "org": "lra-cloud-ops"},
            assigned_to="founder",
            capability="create_repository",
        )
    """

    type: str
    params: dict = field(default_factory=dict)
    assigned_to: str = ""
    capability: str = ""

    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL

    depends_on: list = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    timeout_seconds: int = 60

    rollback_type: str = ""
    rollback_params: dict = field(default_factory=dict)

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str = None
    completed_at: str = None

    result: dict = None
    error: dict = None

    governance: dict = field(default_factory=dict)
    audit_trail: list = field(default_factory=list)

    @property
    def idempotency_key(self) -> str:
        """
        Ver TASK_ENGINE.md §8.
        Deriva una key estable a partir del type y los params relevantes,
        para detectar reintentos duplicados del mismo efecto.
        """
        relevant = sorted(self.params.items())
        return f"{self.type}:{relevant}"

    def transition(self, new_status: TaskStatus, reason: str = "") -> None:
        """
        Cambia el estado de la Task y registra el cambio en audit_trail.
        No valida transiciones inválidas en esta versión — el Workflow
        Engine es responsable de invocar transiciones válidas según el
        ciclo de vida definido en TASK_ENGINE.md §3.
        """
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now().isoformat()

        if new_status == TaskStatus.RUNNING and self.started_at is None:
            self.started_at = self.updated_at
        if new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.completed_at = self.updated_at

        self.audit_trail.append({
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason,
            "timestamp": self.updated_at,
        })

    def is_terminal(self) -> bool:
        """True si la Task ya no puede cambiar de estado (TASK_ENGINE.md §3)."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    def has_rollback(self) -> bool:
        """Ver TASK_ENGINE.md §5."""
        return bool(self.rollback_type)

    def __repr__(self):
        return f"Task(id={self.id}, type={self.type}, status={self.status.value})"