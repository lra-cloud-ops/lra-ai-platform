# tests/test_governance_engine.py
# Tests para el GovernanceEngine — RBAC y políticas.

import pytest
from core.governance_engine import GovernanceEngine, PermissionLevel
from core.interfaces.task import Task


@pytest.fixture
def governance():
    return GovernanceEngine()


@pytest.fixture
def task():
    return Task(
        type="create_repository",
        params={"name": "test-repo"},
        assigned_to="founder",
        capability="create_repository",
    )


class TestPermissionLevels:
    def test_development_level_value(self):
        assert PermissionLevel.DEVELOPMENT.value == 3

    def test_production_level_value(self):
        assert PermissionLevel.PRODUCTION.value == 4

    def test_admin_level_value(self):
        assert PermissionLevel.ADMIN.value == 5

    def test_read_only_is_lowest(self):
        assert PermissionLevel.READ_ONLY.value < PermissionLevel.DEVELOPMENT.value


class TestGovernance:
    def test_governance_initializes(self, governance):
        assert governance is not None

    def test_task_can_be_evaluated(self, governance, task):
        decision = governance.evaluate(
            task=task,
            actor="ruben.liquenson",
            actor_level=PermissionLevel.DEVELOPMENT,
            environment="development",
        )
        assert decision is not None
        assert "decision" in decision  # es un dict

    def test_development_task_approved(self, governance, task):
        decision = governance.evaluate(
            task=task,
            actor="ruben.liquenson",
            actor_level=PermissionLevel.DEVELOPMENT,
            environment="development",
        )
        assert decision["decision"] == "approved"