# tests/test_agents.py
# Tests de importación y contrato básico de todos los agentes.

import pytest
from core.interfaces.task import Task


class TestAgentImports:
    def test_founder_agent_imports(self):
        from agents.founder_agent import FounderAgent
        assert FounderAgent is not None

    def test_cloud_architect_imports(self):
        from agents.cloud_architect_agent import CloudArchitectAgent
        assert CloudArchitectAgent is not None

    def test_devops_agent_imports(self):
        from agents.devops_agent import DevOpsAgent
        assert DevOpsAgent is not None

    def test_security_agent_imports(self):
        from agents.security_agent import SecurityAgent
        assert SecurityAgent is not None

    def test_sre_agent_imports(self):
        from agents.sre_agent import SREAgent
        assert SREAgent is not None

    def test_openshift_agent_imports(self):
        from agents.openshift_agent import OpenShiftAgent
        assert OpenShiftAgent is not None

    def test_documentation_agent_imports(self):
        from agents.documentation_agent import DocumentationAgent
        assert DocumentationAgent is not None

    def test_reviewer_agent_imports(self):
        from agents.reviewer_agent import ReviewerAgent
        assert ReviewerAgent is not None


class TestAgentContract:
    def test_founder_has_execute_task(self):
        from agents.founder_agent import FounderAgent
        agent = FounderAgent(name="test", role="test", description="test")
        assert hasattr(agent, "execute_task")

    def test_security_has_execute_task(self):
        from agents.security_agent import SecurityAgent
        agent = SecurityAgent(name="test", role="test", description="test")
        assert hasattr(agent, "execute_task")

    def test_devops_has_run(self):
        from agents.devops_agent import DevOpsAgent
        agent = DevOpsAgent(name="test", role="test", description="test")
        assert hasattr(agent, "run")

    def test_agents_have_task_handlers(self):
        from agents.security_agent import SecurityAgent
        agent = SecurityAgent(name="test", role="test", description="test")
        assert hasattr(agent, "_TASK_HANDLERS")
        assert len(agent._TASK_HANDLERS) > 0

    def test_unsupported_task_raises_error(self):
        from agents.founder_agent import FounderAgent
        agent = FounderAgent(name="test", role="test", description="test")
        task = Task(type="nonexistent_task", params={}, assigned_to="founder")
        with pytest.raises(ValueError):
            agent.execute_task(task)