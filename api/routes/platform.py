# api/routes/platform.py
# Rutas de estado y configuración de la plataforma.

from fastapi import APIRouter
from core.supervisor import Supervisor

router = APIRouter()

def get_supervisor():
    return Supervisor.build()


@router.get("/status")
def platform_status():
    """Estado general de la plataforma."""
    supervisor = get_supervisor()
    return supervisor.status()


@router.get("/agents")
def list_agents():
    """Lista todos los agentes disponibles."""
    supervisor = get_supervisor()
    return supervisor.agent_manager.summary()


@router.get("/tools")
def list_tools():
    """Lista todas las tools disponibles."""
    supervisor = get_supervisor()
    return supervisor.tool_manager.summary()


@router.get("/workflows")
def list_workflows():
    """Lista todos los workflows registrados."""
    supervisor = get_supervisor()
    return {"workflows": supervisor.task_planner.list_workflows()}


@router.get("/memory/{project}")
def get_memory(project: str):
    """Retorna la memoria de un proyecto."""
    from core.memory_manager import MemoryManager
    mm = MemoryManager()
    proj = mm.get_project_memory(project)
    org  = mm.get_organization_memory()
    return {
        "project": project,
        "project_memory": proj.snapshot(),
        "organization_defaults": org.snapshot(),
    }


@router.get("/audit")
def get_audit_log():
    """Retorna el audit log de la sesión actual."""
    supervisor = get_supervisor()
    return {
        "audit_log": supervisor.governance.audit_engine.history()
    }