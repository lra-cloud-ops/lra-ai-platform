# core/workflow_engine.py
# Implementa docs/WORKFLOW_ENGINE.md
# Ejecuta un ExecutionPlan completo usando TaskEngine para cada Task individual.

from core.interfaces.task import TaskStatus
from core.interfaces.execution_plan import ExecutionPlan, PlanStatus
from core.task_engine import TaskEngine
from core.governance_engine import PermissionLevel
from core.event_bus import EventBus, Event


class WorkflowEngine:
    """
    Ejecuta un ExecutionPlan resolviendo su task_graph (WORKFLOW_ENGINE.md §3),
    paralelizando Tasks independientes (§4) y manejando fallos en cascada (§5).

    No decide si algo esta permitido -- eso ya lo resuelve Governance via
    TaskEngine para cada Task individual. Solo decide cuando y en que orden.

    Uso:
        workflow_engine = WorkflowEngine(task_engine, event_bus)
        result = workflow_engine.execute(plan, tasks_by_id={...},
                                          actor="ruben.liquenson",
                                          actor_level=PermissionLevel.DEVELOPMENT,
                                          environment="development")
    """

    def __init__(self, task_engine: TaskEngine, event_bus: EventBus):
        self.task_engine = task_engine
        self.event_bus = event_bus

    def execute(
        self,
        plan: ExecutionPlan,
        tasks_by_id: dict,
        actor: str,
        actor_level: PermissionLevel,
        environment: str = "development",
    ) -> dict:
        """
        Ejecuta el plan completo. tasks_by_id mapea task.id -> objeto Task
        (las mismas Tasks referenciadas en plan.task_graph).

        Retorna un result_summary (EXECUTION_PLAN.md §2).
        """
        if plan.has_cycles():
            plan.transition(PlanStatus.INVALID, reason="cyclic_task_graph")
            self._emit("plan.invalid", plan)
            return {"status": "invalid", "reason": "cyclic_task_graph"}

        plan.transition(PlanStatus.VALIDATED)
        self._emit("plan.validated", plan)

        plan.transition(PlanStatus.RUNNING)
        self._emit("plan.started", plan)

        levels = plan.topological_order()
        completed_task_types = []
        cancelled_ids = set()
        plan_failed = False

        for level_index, level in enumerate(levels):
            for task_id in level:
                task = tasks_by_id[task_id]

                # Si alguna dependencia fue cancelada/fallida, esta Task
                # se cancela en cascada sin ejecutarse (TASK_ENGINE.md §4)
                deps = plan.task_graph.get(task_id, [])
                if any(d in cancelled_ids for d in deps):
                    task.transition(TaskStatus.CANCELLED, reason="dependency_failed")
                    cancelled_ids.add(task_id)
                    self._emit("task.cancelled", task)
                    continue

                result = self.task_engine.run(
                    task, actor, actor_level, environment, completed_task_types
                )

                if result.get("status") == "pending_approval":
                    # El plan se queda esperando aprobacion humana para esta Task.
                    # No se cancelan las demas -- el usuario puede aprobar y
                    # se reanuda mas adelante (resume_task en este mismo plan).
                    self._emit("plan.paused_for_approval", plan)
                    return {
                        "status": "pending_approval",
                        "blocked_task_id": task.id,
                        "plan_id": plan.id,
                    }

                if result.get("status") in ("failed", "rejected"):
                    cancelled_ids.add(task_id)
                    plan_failed = True
                else:
                    completed_task_types.append(task.type)

            self._emit("workflow.level_completed", plan, extra={"level": level_index})

        if plan_failed:
            plan.transition(PlanStatus.FAILED, reason="one_or_more_tasks_failed")
            self._emit("plan.failed", plan)

            if plan.rollback_plan:
                return self._execute_rollback(plan, tasks_by_id, actor, actor_level, environment)

            return {"status": "failed", "cancelled_tasks": list(cancelled_ids)}

        plan.result_summary = {
            "completed_tasks": completed_task_types,
            "cancelled_tasks": list(cancelled_ids),
        }
        plan.transition(PlanStatus.COMPLETED)
        self._emit("plan.completed", plan)
        return {"status": "completed", "summary": plan.result_summary}

    def resume_task(
        self,
        plan: ExecutionPlan,
        tasks_by_id: dict,
        task_id: str,
        actor: str,
        actor_level: PermissionLevel,
        environment: str = "development",
    ) -> dict:
        """
        Reanuda un plan que estaba pausado esperando aprobacion de una Task
        especifica (EXECUTION_PLAN.md §7). Asume que la Task ya fue aprobada
        via GovernanceEngine.approval_engine.approve() antes de llamar esto.
        """
        task = tasks_by_id[task_id]
        result = self.task_engine.resume_after_approval(task)

        if result.get("status") != "completed":
            plan.transition(PlanStatus.FAILED, reason="resumed_task_failed")
            self._emit("plan.failed", plan)
            return {"status": "failed", "task_id": task_id}

        # Continuar con el resto del plan desde donde se quedo
        return self.execute(plan, tasks_by_id, actor, actor_level, environment)

    def _execute_rollback(self, plan, tasks_by_id, actor, actor_level, environment) -> dict:
        """Ver TASK_ENGINE.md §5 y EXECUTION_PLAN.md §3 (ROLLED_BACK)."""
        self._emit("plan.rollback_started", plan)

        for task_id in reversed(plan.rollback_plan):
            rollback_task = tasks_by_id.get(task_id)
            if rollback_task:
                self.task_engine.run(rollback_task, actor, actor_level, environment)

        plan.transition(PlanStatus.ROLLED_BACK, reason="rollback_completed")
        self._emit("plan.rollback_completed", plan)
        return {"status": "rolled_back"}

    def _emit(self, event_type: str, plan: ExecutionPlan, extra: dict = None) -> None:
        data = {"plan_id": plan.id, "status": plan.status.value}
        if extra:
            data.update(extra)
        self.event_bus.publish(Event(type=event_type, source="workflow_engine", data=data))

    def __repr__(self):
        return "WorkflowEngine()"