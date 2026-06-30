# core/task_planner.py
# Implementa ADR-004: mapeo por keywords a Workflows con nombre.
# Traduce un Intent en texto libre a un ExecutionPlan concreto.

import yaml
from pathlib import Path
from core.interfaces.task import Task
from core.interfaces.execution_plan import ExecutionPlan, PlanStatus


class TaskPlanner:
    """
    Traduce un Intent del usuario en un ExecutionPlan.

    v1.0 (ADR-004): mapeo por keywords contra Workflows registrados en
    config/workflows/. Si ningun Workflow matchea, retorna un plan INVALID.

    Uso:
        planner = TaskPlanner()
        plan, tasks_by_id = planner.plan("Crea un proyecto nuevo llamado client-api")
    """

    def __init__(self, workflows_dir: str = "config/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self._workflows: dict = self._load_workflows()

    def _load_workflows(self) -> dict:
        """Carga todos los Workflows YAML del directorio."""
        workflows = {}
        if not self.workflows_dir.exists():
            return workflows
        for file in self.workflows_dir.glob("*.yaml"):
            with open(file, "r") as f:
                wf = yaml.safe_load(f)
                workflows[wf["name"]] = wf
        return workflows

    def _match_workflow(self, intent: str) -> dict:
        """Busca el primer Workflow cuyas keywords aparezcan en el Intent."""
        intent_lower = intent.lower()
        for wf in self._workflows.values():
            for keyword in wf.get("keywords", []):
                if keyword in intent_lower:
                    return wf
        return None

    def plan(self, intent: str, params: dict = None) -> tuple:
        """
        Genera un ExecutionPlan a partir de un Intent.

        Retorna (ExecutionPlan, tasks_by_id) — tasks_by_id es necesario
        para que WorkflowEngine.execute() pueda resolver cada Task del
        task_graph (mismo patron usado en las pruebas de WorkflowEngine).

        Si no hay Workflow que matchee, retorna un plan INVALID.
        """
        params = params or {}
        workflow = self._match_workflow(intent)

        if workflow is None:
            plan = ExecutionPlan(intent=intent, tasks=[], task_graph={})
            plan.transition(PlanStatus.INVALID, reason="no_matching_workflow")
            return plan, {}

        tasks_by_id = {}
        type_to_id = {}

        # Primera pasada: instanciar cada Task con un id real
        for task_def in workflow["tasks"]:
            task = Task(
                type=task_def["type"],
                params=params,
                assigned_to=task_def["assigned_to"],
                capability=task_def["capability"],
            )
            tasks_by_id[task.id] = task
            type_to_id[task_def["type"]] = task.id

        # Segunda pasada: construir el task_graph traduciendo depends_on
        # (declarado por 'type' en el YAML) a ids reales
        task_graph = {}
        for task_def in workflow["tasks"]:
            task_id = type_to_id[task_def["type"]]
            depends_on_types = task_def.get("depends_on", [])
            task_graph[task_id] = [type_to_id[t] for t in depends_on_types]

        plan = ExecutionPlan(
            intent=intent,
            tasks=list(tasks_by_id.keys()),
            task_graph=task_graph,
        )

        return plan, tasks_by_id

    def list_workflows(self) -> list:
        """Retorna los nombres de los Workflows disponibles."""
        return list(self._workflows.keys())

    def __repr__(self):
        return f"TaskPlanner(workflows={self.list_workflows()})"