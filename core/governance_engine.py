# core/governance_engine.py
# Implementa docs/GOVERNANCE.md
# Ninguna Task pasa de PENDING a RUNNING sin pasar por aquí (ADR-002).
# Regla de oro: ante cualquier error interno, se DENIEGA. Nunca se aprueba por omisión.

from enum import IntEnum
from datetime import datetime
from core.interfaces.task import Task, TaskStatus


class PermissionLevel(IntEnum):
    """Ver GOVERNANCE.md §3."""
    READ_ONLY = 1
    PROPOSE = 2
    DEVELOPMENT = 3
    PRODUCTION = 4
    ADMIN = 5


# Nivel mínimo requerido por tipo de Task — el resto de tipos no listados
# usan PROPOSE (2) como default seguro.
DEFAULT_TASK_PERMISSION_LEVELS = {
    "get_repo": PermissionLevel.READ_ONLY,
    "list_repos": PermissionLevel.READ_ONLY,
    "list_pods": PermissionLevel.READ_ONLY,
    "get_metrics": PermissionLevel.READ_ONLY,
    "create_pull_request": PermissionLevel.PROPOSE,
    "generate_documentation": PermissionLevel.PROPOSE,
    "create_repository": PermissionLevel.PROPOSE,
    "create_branch": PermissionLevel.DEVELOPMENT,
    "deploy_to_dev": PermissionLevel.DEVELOPMENT,
    "run_tests": PermissionLevel.DEVELOPMENT,
    "deploy_to_production": PermissionLevel.PRODUCTION,
    "terraform_apply_prod": PermissionLevel.PRODUCTION,
    "update_agent_config": PermissionLevel.ADMIN,
    "modify_policy": PermissionLevel.ADMIN,
}


class AuditEngine:
    """
    Registro inmutable de eventos. Ver GOVERNANCE.md §6.
    Solo escritura — nunca se edita ni se borra una entrada existente.
    """

    def __init__(self):
        self._log: list = []

    def record(self, actor: str, event_type: str, target: str, detail: dict = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "actor": actor,
            "event_type": event_type,
            "target": target,
            "detail": detail or {},
        }
        self._log.append(entry)

    def history(self, target: str = None) -> list:
        if target:
            return [e for e in self._log if e["target"] == target]
        return list(self._log)

    def __repr__(self):
        return f"AuditEngine(entries={len(self._log)})"


class PolicyEngine:
    """
    Evalua reglas declarativas por entorno. Ver GOVERNANCE.md §4.

    Ejemplo de uso:
        policies = {
            "production": {"requires": ["security_scan", "approval"]},
            "development": {"requires": []},
        }
        policy_engine = PolicyEngine(policies)
    """

    def __init__(self, policies: dict = None):
        self.policies = policies or {
            "production": {"requires": ["security_scan", "approval"]},
            "development": {"requires": []},
        }

    def evaluate(self, task: Task, environment: str, completed_task_types: list) -> dict:
        """
        Retorna {"allowed": bool, "missing": [...], "reason": str}

        completed_task_types: tipos de Task ya COMPLETED en el mismo
        Execution Plan, para verificar requisitos como "security_scan
        debe haberse completado antes de deploy_to_production".
        """
        policy = self.policies.get(environment, {"requires": []})
        required = policy.get("requires", [])

        missing = [
            req for req in required
            if req != "approval" and req not in completed_task_types
        ]

        if missing:
            return {
                "allowed": False,
                "missing": missing,
                "reason": f"Missing required steps for '{environment}': {missing}",
            }

        return {"allowed": True, "missing": [], "reason": "Policy satisfied"}

    def estimate_impact(self, task: Task, environment: str) -> str:
        """Calcula estimated_impact según GOVERNANCE.md §4."""
        if environment == "production":
            return "high" if "deploy" in task.type or "apply" in task.type else "medium"
        return "low"


class ApprovalEngine:
    """
    Gestiona Tasks/Plans que requieren aprobación humana. Ver GOVERNANCE.md §5.
    """

    def __init__(self):
        self._pending: dict = {}   # task_id -> Task
        self._decisions: dict = {} # task_id -> {"approved": bool, "by": str, "at": str}

    def request_approval(self, task: Task) -> None:
        self._pending[task.id] = task

    def approve(self, task_id: str, approved_by: str, comment: str = "") -> dict:
        decision = {
            "approved": True,
            "by": approved_by,
            "at": datetime.now().isoformat(),
            "comment": comment,
        }
        self._decisions[task_id] = decision
        self._pending.pop(task_id, None)
        return decision

    def reject(self, task_id: str, rejected_by: str, comment: str = "") -> dict:
        decision = {
            "approved": False,
            "by": rejected_by,
            "at": datetime.now().isoformat(),
            "comment": comment,
        }
        self._decisions[task_id] = decision
        self._pending.pop(task_id, None)
        return decision

    def get_decision(self, task_id: str) -> dict:
        return self._decisions.get(task_id)

    def list_pending(self) -> list:
        return list(self._pending.keys())


class GovernanceEngine:
    """
    Punto único de decisión: ¿puede ejecutarse esta Task?
    Ver GOVERNANCE.md §2 y §7 para el flujo completo.

    Uso:
        governance = GovernanceEngine()
        decision = governance.evaluate(task, actor_level=PermissionLevel.DEVELOPMENT,
                                        environment="development", completed_task_types=[])
    """

    def __init__(self, policies: dict = None):
        self.policy_engine = PolicyEngine(policies)
        self.approval_engine = ApprovalEngine()
        self.audit_engine = AuditEngine()

    def evaluate(
        self,
        task: Task,
        actor: str,
        actor_level: PermissionLevel,
        environment: str = "development",
        completed_task_types: list = None,
    ) -> dict:
        """
        Evalua una Task y retorna una decision. Nunca deja una Task sin
        decision: APPROVED, REJECTED o PENDING_APPROVAL.

        Ver GOVERNANCE.md §8: ante cualquier excepcion interna, se DENIEGA.
        """
        completed_task_types = completed_task_types or []

        try:
            required_level = DEFAULT_TASK_PERMISSION_LEVELS.get(
                task.type, PermissionLevel.PROPOSE
            )

            # 1. RBAC: el actor tiene nivel suficiente?
            if actor_level < required_level:
                task.transition(TaskStatus.REJECTED, reason="insufficient_permission_level")
                task.governance = {
                    "requires_approval": False,
                    "permission_level": required_level.value,
                    "decision": "rejected",
                    "reason": "insufficient_permission_level",
                }
                self.audit_engine.record(actor, "task.rejected", task.id, task.governance)
                return task.governance

            # 2. PolicyEngine: la Task cumple los requisitos del entorno?
            policy_result = self.policy_engine.evaluate(task, environment, completed_task_types)
            if not policy_result["allowed"]:
                task.transition(TaskStatus.REJECTED, reason=policy_result["reason"])
                task.governance = {
                    "requires_approval": False,
                    "permission_level": required_level.value,
                    "decision": "rejected",
                    "reason": policy_result["reason"],
                }
                self.audit_engine.record(actor, "task.rejected", task.id, task.governance)
                return task.governance

            estimated_impact = self.policy_engine.estimate_impact(task, environment)

            # 3. Requiere aprobacion humana?
            requires_approval = required_level >= PermissionLevel.PRODUCTION
            if requires_approval:
                task.transition(TaskStatus.PENDING, reason="awaiting_human_approval")
                self.approval_engine.request_approval(task)
                task.governance = {
                    "requires_approval": True,
                    "permission_level": required_level.value,
                    "decision": "pending_approval",
                    "estimated_impact": estimated_impact,
                }
                self.audit_engine.record(actor, "task.pending_approval", task.id, task.governance)
                return task.governance

            # 4. Aprobacion automatica
            task.transition(TaskStatus.APPROVED, reason="auto_approved")
            task.governance = {
                "requires_approval": False,
                "permission_level": required_level.value,
                "decision": "approved",
                "estimated_impact": estimated_impact,
            }
            self.audit_engine.record(actor, "task.approved", task.id, task.governance)
            return task.governance

        except Exception as e:
            # GOVERNANCE.md §8: denegar por defecto ante error interno
            task.transition(TaskStatus.REJECTED, reason="governance_unavailable")
            task.governance = {
                "requires_approval": False,
                "decision": "rejected",
                "reason": "governance_unavailable",
                "error": str(e),
            }
            self.audit_engine.record("system", "task.rejected", task.id, task.governance)
            return task.governance

    def __repr__(self):
        return f"GovernanceEngine(pending_approvals={len(self.approval_engine.list_pending())})"