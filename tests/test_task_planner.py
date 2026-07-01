# tests/test_task_planner.py
# Tests para el TaskPlanner — extracción de nombre e intent matching.

import pytest
from core.task_planner import TaskPlanner


@pytest.fixture
def planner():
    return TaskPlanner()


class TestExtractName:
    def test_extract_llamado(self, planner):
        name = planner._extract_name("Crea un proyecto llamado client-api")
        assert name == "client-api"

    def test_extract_named(self, planner):
        name = planner._extract_name("Create a new project named my-service")
        assert name == "my-service"

    def test_extract_called(self, planner):
        name = planner._extract_name("Create a project called lra-platform")
        assert name == "lra-platform"

    def test_extract_with_underscore(self, planner):
        name = planner._extract_name("nuevo proyecto llamado lra_test")
        assert name == "lra_test"

    def test_no_name_returns_none(self, planner):
        name = planner._extract_name("Crea un proyecto nuevo")
        assert name is None


class TestPlan:
    def test_create_project_workflow_matches(self, planner):
        plan, tasks = planner.plan("Crea un proyecto nuevo llamado test-proj")
        assert len(tasks) > 0

    def test_name_extracted_from_intent(self, planner):
        plan, tasks = planner.plan("Crea un proyecto llamado my-api")
        for task in tasks.values():
            assert task.params.get("name") == "my-api"

    def test_params_passed_to_tasks(self, planner):
        plan, tasks = planner.plan(
            "Crea un proyecto llamado test",
            {"org": "lra-cloud-ops"}
        )
        for task in tasks.values():
            assert task.params.get("org") == "lra-cloud-ops"

    def test_no_matching_workflow_returns_empty(self, planner):
        plan, tasks = planner.plan("algo que no matchea ningun workflow xyz123")
        assert len(tasks) == 0

    def test_security_review_workflow_matches(self, planner):
        plan, tasks = planner.plan("escanea seguridad del repositorio")
        assert len(tasks) > 0

    def test_infrastructure_review_matches(self, planner):
        plan, tasks = planner.plan("revisa la infraestructura")
        assert len(tasks) > 0

    def test_deploy_eks_matches(self, planner):
        plan, tasks = planner.plan("deploy eks en eu-west-1")
        assert len(tasks) > 0

    def test_task_graph_has_dependencies(self, planner):
        plan, tasks = planner.plan("Crea un proyecto llamado test")
        assert plan.task_graph is not None
        assert len(plan.task_graph) == len(tasks)