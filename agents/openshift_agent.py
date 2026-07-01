# agents/openshift_agent.py
# OpenShift Agent — gestiona clusters OpenShift, Operators y Pipelines.
# v2.0 Task-centric: ejecuta Tasks individuales asignadas por WorkflowEngine.

from core.interfaces.agent import Agent
from core.interfaces.task import Task


class OpenShiftAgent(Agent):
    """
    OpenShift Agent de LRA AI Platform.

    Especialidad: gestión de clusters Red Hat OpenShift,
    Operators, Pipelines y GitOps.

    Tasks que sabe ejecutar:
        get_projects          → lista proyectos del cluster
        create_project        → crea un proyecto nuevo
        get_pods              → lista pods de un proyecto
        get_routes            → lista routes (URLs) de un proyecto
        get_operators         → lista operadores instalados
        deploy_app            → despliega una aplicación
        expose_service        → crea una route para exponer un servicio
        install_operator      → instala un operador via subscription
        get_cluster_version   → versión del cluster OpenShift
        whoami                → usuario autenticado en el cluster
        generate_cluster_report → informe completo del cluster

    Tools que usa:
        - openshift → oc CLI para gestión del cluster
        - github    → acceso a repositorios y manifests
    """

    _TASK_HANDLERS = [
        "get_projects",
        "create_project",
        "get_pods",
        "get_routes",
        "get_operators",
        "deploy_app",
        "expose_service",
        "install_operator",
        "get_cluster_version",
        "whoami",
        "generate_cluster_report",
    ]

    def execute_task(self, task: Task) -> dict:
        handlers = {
            "get_projects":          self._get_projects,
            "create_project":        self._create_project,
            "get_pods":              self._get_pods,
            "get_routes":            self._get_routes,
            "get_operators":         self._get_operators,
            "deploy_app":            self._deploy_app,
            "expose_service":        self._expose_service,
            "install_operator":      self._install_operator,
            "get_cluster_version":   self._get_cluster_version,
            "whoami":                self._whoami,
            "generate_cluster_report": self._generate_cluster_report,
        }

        handler = handlers.get(task.type)
        if handler is None:
            raise ValueError(
                f"OpenShiftAgent does not handle task type '{task.type}'. "
                f"Supported: {list(handlers.keys())}"
            )
        return handler(task.params)

    def run(self, task: str, context: dict = {}) -> dict:
        """Compatibilidad v1.0."""
        t = Task(type=task.replace(" ", "_"), params=context, assigned_to="openshift")
        return self.execute_task(t)

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tools": list(self.tools.keys()),
            "supported_tasks": self._TASK_HANDLERS,
        }

    # --- Implementaciones ---

    def _get_projects(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        print(f"[OpenShiftAgent] Getting projects...")
        result = oc.execute("get_projects", params)
        print(f"[OpenShiftAgent] Projects: {result.get('total', 0)}")
        return result

    def _create_project(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        name = params.get("name")
        print(f"[OpenShiftAgent] Creating project: {name}")
        return oc.execute("create_project", params)

    def _get_pods(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        ns = params.get("namespace", "default")
        print(f"[OpenShiftAgent] Getting pods in {ns}...")
        return oc.execute("get_pods", params)

    def _get_routes(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        print(f"[OpenShiftAgent] Getting routes...")
        return oc.execute("get_routes", params)

    def _get_operators(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        print(f"[OpenShiftAgent] Getting installed operators...")
        return oc.execute("get_operators", params)

    def _deploy_app(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        name  = params.get("name")
        image = params.get("image")
        print(f"[OpenShiftAgent] Deploying {name} from {image}...")
        return oc.execute("deploy_app", params)

    def _expose_service(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        name = params.get("name")
        print(f"[OpenShiftAgent] Exposing service {name}...")
        return oc.execute("expose_service", params)

    def _install_operator(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        name = params.get("name")
        print(f"[OpenShiftAgent] Installing operator: {name}")
        return oc.execute("install_operator", params)

    def _get_cluster_version(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        print(f"[OpenShiftAgent] Getting cluster version...")
        return oc.execute("get_cluster_version", params)

    def _whoami(self, params: dict) -> dict:
        oc = self.get_tool("openshift")
        return oc.execute("whoami", params)

    def _generate_cluster_report(self, params: dict) -> dict:
        """
        Genera un informe completo del estado del cluster OpenShift.
        Recoge proyectos, operadores, routes y versión del cluster.
        """
        oc = self.get_tool("openshift")
        print(f"[OpenShiftAgent] Generating cluster report...")

        report = {}

        whoami = oc.execute("whoami", {})
        report["user"] = whoami.get("user", "unknown")

        version = oc.execute("get_cluster_version", {})
        report["cluster_version"] = version

        projects = oc.execute("get_projects", {})
        report["projects"] = projects

        operators = oc.execute("get_operators", {})
        report["operators"] = operators

        report["summary"] = {
            "user": report["user"],
            "cluster_version": version.get("version", "unknown"),
            "total_projects": projects.get("total", 0),
            "total_operators": operators.get("total", 0),
        }

        print(f"[OpenShiftAgent] Cluster report complete.")
        return report