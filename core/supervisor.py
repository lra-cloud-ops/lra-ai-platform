# core/supervisor.py
# Punto de entrada único de LRA AI Platform. Ver SDK.md §3.
# Usuario -> Supervisor -> TaskPlanner -> WorkflowEngine -> resultado.

from core.config_manager import ConfigManager
from core.tool_manager import ToolManager
from core.agent_manager import AgentManager
from core.governance_engine import GovernanceEngine, PermissionLevel
from core.event_bus import EventBus
from core.task_engine import TaskEngine
from core.workflow_engine import WorkflowEngine
from core.task_planner import TaskPlanner
from core.interfaces.execution_plan import ExecutionPlan, PlanStatus


class Supervisor:
    """
    Punto de entrada único de LRA AI Platform.

    Recibe un Intent del usuario, genera un Execution Plan via
    TaskPlanner, lo presenta para aprobacion si es necesario, y lo
    ejecuta via WorkflowEngine. Ver SDK.md §3 para el flujo completo.

    Uso:
        supervisor = Supervisor.build()

        plan, tasks = supervisor.plan("Crea un proyecto nuevo llamado client-api")
        print(supervisor.describe(plan, tasks))

        result = supervisor.execute(plan, tasks,
                                     actor="ruben.liquenson",
                                     actor_level=PermissionLevel.DEVELOPMENT)
    """

    def __init__(
        self,
        config: ConfigManager,
        tool_manager: ToolManager,
        agent_manager: AgentManager,
        governance: GovernanceEngine,
        event_bus: EventBus,
        task_engine: TaskEngine,
        workflow_engine: WorkflowEngine,
        task_planner: TaskPlanner,
    ):
        self.config = config
        self.tool_manager = tool_manager
        self.agent_manager = agent_manager
        self.governance = governance
        self.event_bus = event_bus
        self.task_engine = task_engine
        self.workflow_engine = workflow_engine
        self.task_planner = task_planner

    @classmethod
    def build(cls, workflows_dir: str = "config/workflows") -> "Supervisor":
        """
        Factory method: construye e inyecta todos los componentes
        del nucleo en el orden correcto. Ver ARCHITECTURE.md §4.
        """
        config         = ConfigManager()
        tool_manager   = ToolManager(config)
        agent_manager  = AgentManager(config, tool_manager)
        governance     = GovernanceEngine()
        event_bus      = EventBus()
        task_engine    = TaskEngine(governance, event_bus, agent_manager)
        workflow_engine = WorkflowEngine(task_engine, event_bus)
        task_planner   = TaskPlanner(workflows_dir)

        return cls(
            config, tool_manager, agent_manager,
            governance, event_bus, task_engine,
            workflow_engine, task_planner,
        )

    def plan(self, intent: str, params: dict = None) -> tuple:
        """
        Traduce un Intent en un ExecutionPlan.
        Retorna (plan, tasks_by_id) — ver SDK.md §3.

        Si el planner no encuentra un Workflow, el plan queda INVALID.
        """
        print(f"\n[Supervisor] Received intent: '{intent}'")
        plan, tasks_by_id = self.task_planner.plan(intent, params or {})

        if plan.status == PlanStatus.INVALID:
            print(f"[Supervisor] No matching workflow for this intent.")
        else:
            print(f"[Supervisor] Plan generated: {plan.id} ({len(tasks_by_id)} tasks)")

        return plan, tasks_by_id

    def describe(self, plan: ExecutionPlan, tasks_by_id: dict) -> str:
        """
        Retorna una descripcion legible del plan para presentar al usuario
        antes de ejecutarlo. Ver ARCHITECTURE.md §4 paso 4.
        """
        if plan.status == PlanStatus.INVALID:
            return f"[Plan INVALID] No se encontro un workflow para este intent."

        levels = plan.topological_order()
        lines = [
            f"\nExecution Plan: {plan.id}",
            f"Intent: {plan.intent}",
            f"Requires approval: {plan.requires_approval}",
            f"Tasks:",
        ]
        for i, level in enumerate(levels):
            for task_id in level:
                task = tasks_by_id[task_id]
                parallel = " (parallel)" if len(level) > 1 else ""
                lines.append(f"  {i+1}. {task.type} → {task.assigned_to}{parallel}")

        lines.append(f"\n¿Deseas ejecutarlo? (yes/no)")
        return "\n".join(lines)

    def execute(
        self,
        plan: ExecutionPlan,
        tasks_by_id: dict,
        actor: str,
        actor_level: PermissionLevel,
        environment: str = "development",
    ) -> dict:
        """
        Ejecuta el plan via WorkflowEngine.
        El plan debe estar en estado CREATED o APPROVED.
        """
        if plan.status == PlanStatus.INVALID:
            return {"status": "error", "reason": "cannot execute an INVALID plan"}

        print(f"\n[Supervisor] Executing plan {plan.id}...")
        result = self.workflow_engine.execute(
            plan, tasks_by_id, actor, actor_level, environment
        )
        print(f"[Supervisor] Plan {plan.id} finished: {result['status']}")
        return result

    def approve_task(self, task_id: str, approved_by: str, comment: str = "") -> dict:
        """
        Aprueba una Task pendiente de aprobacion humana.
        Ver GOVERNANCE.md §5 y SDK.md §3.
        """
        return self.governance.approval_engine.approve(task_id, approved_by, comment)

    def status(self) -> dict:
        """Retorna el estado actual de la plataforma."""
        return {
            "platform": self.config.get("platform.name"),
            "version": self.config.get("platform.version"),
            "environment": self.config.get("platform.environment"),
            "agents": self.agent_manager.summary(),
            "tools": self.tool_manager.summary(),
            "workflows": self.task_planner.list_workflows(),
            "pending_approvals": self.governance.approval_engine.list_pending(),
        }

    def __repr__(self):
        return f"Supervisor(platform={self.config.get('platform.name')})"