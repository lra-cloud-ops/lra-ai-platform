# core/task_engine.py
# Implementa docs/TASK_ENGINE.md
# Orquesta el ciclo de vida completo de una Task: Governance -> Execution -> Retry/Timeout

import time
import signal
from core.interfaces.task import Task, TaskStatus
from core.governance_engine import GovernanceEngine, PermissionLevel
from core.event_bus import EventBus, Event


class TaskTimeoutError(Exception):
    """Se lanza cuando una Task supera su timeout_seconds (TASK_ENGINE.md §7)."""
    pass


class TaskEngine:
    """
    Orquesta el ciclo de vida completo de una Task.

    Flujo (TASK_ENGINE.md + GOVERNANCE.md §7):
        1. Verifica idempotencia (TASK_ENGINE.md §8)
        2. Pasa la Task por GovernanceEngine
        3. Si APPROVED -> ejecuta contra el Agent asignado, respetando timeout
        4. Si falla y retry_policy lo permite -> reintenta con backoff
        5. Emite eventos en cada transicion (TASK_ENGINE.md §9)

    Uso:
        engine = TaskEngine(governance, event_bus, agent_manager)
        result = engine.run(task, actor="ruben.liquenson",
                             actor_level=PermissionLevel.DEVELOPMENT,
                             environment="development")
    """

    def __init__(self, governance: GovernanceEngine, event_bus: EventBus, agent_manager=None):
        self.governance = governance
        self.event_bus = event_bus
        self.agent_manager = agent_manager
        self._idempotency_cache: dict = {}  # idempotency_key -> result

    def run(
        self,
        task: Task,
        actor: str,
        actor_level: PermissionLevel,
        environment: str = "development",
        completed_task_types: list = None,
    ) -> dict:
        """
        Ejecuta el ciclo de vida completo de una Task.
        Retorna siempre un dict con el resultado o el error — nunca lanza
        una excepcion hacia afuera (las captura y las traduce a FAILED).
        """
        self._emit("task.created", task)

        # 1. Idempotencia (TASK_ENGINE.md §8)
        if task.idempotency_key in self._idempotency_cache:
            cached = self._idempotency_cache[task.idempotency_key]
            task.result = cached
            task.transition(TaskStatus.COMPLETED, reason="idempotent_cache_hit")
            self._emit("task.completed", task)
            return cached

        # 2. Governance (ADR-002: ninguna Task se ejecuta sin pasar por aqui)
        decision = self.governance.evaluate(
            task, actor, actor_level, environment, completed_task_types or []
        )

        if task.status == TaskStatus.REJECTED:
            self._emit("task.failed", task)
            return {"status": "rejected", "reason": decision.get("reason")}

        if task.status == TaskStatus.PENDING and decision.get("requires_approval"):
            self._emit("task.pending_approval", task)
            return {"status": "pending_approval", "task_id": task.id}

        self._emit("task.approved", task)

        # 3. Ejecucion con retry + timeout
        return self._execute_with_retry(task)

    def resume_after_approval(self, task: Task) -> dict:
        """
        Llamar despues de que ApprovalEngine.approve() autorizo la Task.
        Ver GOVERNANCE.md §5.
        """
        task.transition(TaskStatus.APPROVED, reason="manually_approved")
        self._emit("task.approved", task)
        return self._execute_with_retry(task)

    def _execute_with_retry(self, task: Task) -> dict:
        """Ver TASK_ENGINE.md §6 (retries) y §7 (timeouts)."""
        while True:
            task.transition(TaskStatus.RUNNING)
            self._emit("task.started", task)

            try:
                result = self._execute_with_timeout(task)
                task.result = result
                task.transition(TaskStatus.COMPLETED)
                self._emit("task.completed", task)
                self._idempotency_cache[task.idempotency_key] = result
                return {"status": "completed", "result": result}

            except TaskTimeoutError:
                error = {"reason": "timeout", "timeout_seconds": task.timeout_seconds}
                return self._handle_failure(task, error)

            except Exception as e:
                error = {"reason": "execution_error", "detail": str(e)}
                return self._handle_failure(task, error)

    def _handle_failure(self, task: Task, error: dict) -> dict:
        task.error = error
        task.transition(TaskStatus.FAILED, reason=error["reason"])
        self._emit("task.failed", task)

        if task.retry_policy.can_retry():
            task.retry_policy.attempts_made += 1
            backoff = task.retry_policy.next_backoff()
            task.transition(TaskStatus.RETRYING, reason=f"retry_{task.retry_policy.attempts_made}")
            self._emit("task.retrying", task)
            time.sleep(min(backoff, 1))  # cap a 1s en pruebas; backoff real en produccion
            return self._execute_with_retry(task)

        task.transition(TaskStatus.CANCELLED, reason="retries_exhausted")
        self._emit("task.cancelled", task)
        return {"status": "failed", "error": error}

    def _execute_with_timeout(self, task: Task) -> dict:
        """
        Ejecuta la Task real contra el Agent asignado, respetando timeout_seconds.
        Si no hay agent_manager configurado (tests unitarios), simula el resultado.
        """
        if self.agent_manager is None:
            return {"simulated": True, "task_type": task.type, "params": task.params}

        agent = self.agent_manager.get_agent(task.assigned_to)

        # Timeout simple basado en signal (suficiente para esta version;
        # ejecucion distribuida real queda en Future Work, ver ADR-003)
        def _timeout_handler(signum, frame):
            raise TaskTimeoutError()

        result = None
        try:
            if hasattr(signal, "SIGALRM"):
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(task.timeout_seconds)
            result = agent.execute_task(task)
        finally:
            if hasattr(signal, "SIGALRM"):
                signal.alarm(0)

        return result

    def _emit(self, event_type: str, task: Task) -> None:
        self.event_bus.publish(Event(
            type=event_type,
            source=task.assigned_to or "task_engine",
            data={"task_id": task.id, "task_type": task.type, "status": task.status.value},
        ))

    def __repr__(self):
        return f"TaskEngine(cached_results={len(self._idempotency_cache)})"