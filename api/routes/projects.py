# api/routes/projects.py
# Rutas para gestión de proyectos via Supervisor.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class PlanRequest(BaseModel):
    intent: str
    params: Optional[dict] = {}


class ExecuteRequest(BaseModel):
    intent: str
    params: Optional[dict] = {}
    actor: Optional[str] = "api.user"
    environment: Optional[str] = "development"


@router.post("/plan")
def create_plan(request: PlanRequest):
    """
    Genera un Execution Plan a partir de un Intent.
    No ejecuta nada — solo planifica.
    """
    from core.supervisor import Supervisor
    supervisor = Supervisor.build()

    plan, tasks = supervisor.plan(request.intent, request.params)

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail=f"No matching workflow for intent: '{request.intent}'"
        )

    levels = plan.topological_order()
    execution_order = []
    for i, level in enumerate(levels):
        for task_id in level:
            task = tasks[task_id]
            execution_order.append({
                "level": i + 1,
                "type": task.type,
                "assigned_to": task.assigned_to,
                "parallel": len(level) > 1,
            })

    return {
        "plan_id": plan.id,
        "intent": plan.intent,
        "status": plan.status.value,
        "total_tasks": len(tasks),
        "requires_approval": plan.requires_approval,
        "execution_order": execution_order,
    }


@router.post("/execute")
def execute_plan(request: ExecuteRequest):
    """
    Genera y ejecuta un Execution Plan a partir de un Intent.
    """
    from core.supervisor import Supervisor
    from core.governance_engine import PermissionLevel

    supervisor = Supervisor.build()

    plan, tasks = supervisor.plan(request.intent, request.params)

    if not tasks:
        raise HTTPException(
            status_code=404,
            detail=f"No matching workflow for intent: '{request.intent}'"
        )

    result = supervisor.execute(
        plan, tasks,
        actor=request.actor,
        actor_level=PermissionLevel.DEVELOPMENT,
        environment=request.environment,
    )

    return {
        "plan_id": plan.id,
        "intent": request.intent,
        "status": result.get("status"),
        "summary": result.get("summary", {}),
    }


@router.get("/memory")
def list_projects_with_memory():
    """Lista todos los proyectos que tienen memoria."""
    from core.memory_manager import MemoryManager
    mm = MemoryManager()
    return {"projects": mm.list_projects()}