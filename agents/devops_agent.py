# agents/devops_agent.py
# DevOps Agent — automatización de infraestructura, CI/CD y configuración.
# v2.0 Task-centric: ejecuta Tasks individuales asignadas por WorkflowEngine.

from core.interfaces.agent import Agent
from core.interfaces.task import Task


class DevOpsAgent(Agent):
    """
    DevOps Agent de LRA AI Platform.

    Especialidad: automatización de infraestructura, despliegues
    y configuración de servidores.

    Tasks que sabe ejecutar:
        terraform_init          → inicializa directorio Terraform
        terraform_plan          → genera plan de infraestructura
        terraform_apply         → aplica infraestructura (requiere aprobación)
        terraform_validate      → valida configuración Terraform
        kubernetes_get_pods     → lista pods del cluster
        kubernetes_get_nodes    → lista nodos del cluster
        kubernetes_get_deployments → lista deployments
        kubernetes_scale        → escala un deployment
        kubernetes_apply        → aplica un manifest YAML
        kubernetes_rollout      → reinicia un deployment
        ansible_ping            → verifica conectividad con hosts
        ansible_run_playbook    → ejecuta un playbook
        ansible_adhoc           → ejecuta comando ad-hoc

    Tools que usa:
        - terraform  → gestión de infraestructura como código
        - kubernetes → gestión de clusters Kubernetes
        - ansible    → configuración y automatización de servidores
        - github     → acceso a repos y archivos
    """

    _TASK_HANDLERS = [
        "terraform_init",
        "terraform_plan",
        "terraform_apply",
        "terraform_validate",
        "kubernetes_get_pods",
        "kubernetes_get_nodes",
        "kubernetes_get_deployments",
        "kubernetes_scale",
        "kubernetes_apply",
        "kubernetes_rollout",
        "ansible_ping",
        "ansible_run_playbook",
        "ansible_adhoc",
    ]

    def execute_task(self, task: Task) -> dict:
        """Ejecuta una Task individual asignada por el WorkflowEngine."""
        handlers = {
            "terraform_init":              self._terraform_init,
            "terraform_plan":              self._terraform_plan,
            "terraform_apply":             self._terraform_apply,
            "terraform_validate":          self._terraform_validate,
            "kubernetes_get_pods":         self._k8s_get_pods,
            "kubernetes_get_nodes":        self._k8s_get_nodes,
            "kubernetes_get_deployments":  self._k8s_get_deployments,
            "kubernetes_scale":            self._k8s_scale,
            "kubernetes_apply":            self._k8s_apply,
            "kubernetes_rollout":          self._k8s_rollout,
            "ansible_ping":                self._ansible_ping,
            "ansible_run_playbook":        self._ansible_run_playbook,
            "ansible_adhoc":               self._ansible_adhoc,
        }

        handler = handlers.get(task.type)
        if handler is None:
            raise ValueError(
                f"DevOpsAgent does not handle task type '{task.type}'. "
                f"Supported: {list(handlers.keys())}"
            )
        return handler(task.params)

    def run(self, task: str, context: dict = {}) -> dict:
        """Compatibilidad v1.0 — delega a execute_task()."""
        t = Task(type=task.replace(" ", "_"), params=context,
                 assigned_to="devops")
        return self.execute_task(t)

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tools": list(self.tools.keys()),
            "supported_tasks": self._TASK_HANDLERS,
        }

    # --- Terraform ---

    def _terraform_init(self, params: dict) -> dict:
        tf = self.get_tool("terraform")
        print(f"[DevOpsAgent] Running terraform init...")
        return tf.execute("init", params)

    def _terraform_plan(self, params: dict) -> dict:
        tf = self.get_tool("terraform")
        print(f"[DevOpsAgent] Running terraform plan...")
        return tf.execute("plan", params)

    def _terraform_apply(self, params: dict) -> dict:
        """
        Aplica infraestructura Terraform.
        Requiere auto_approve=True en params — medida de seguridad.
        En producción, Governance Engine exige aprobación nivel 4.
        """
        tf = self.get_tool("terraform")
        print(f"[DevOpsAgent] Running terraform apply...")
        return tf.execute("apply", params)

    def _terraform_validate(self, params: dict) -> dict:
        tf = self.get_tool("terraform")
        print(f"[DevOpsAgent] Running terraform validate...")
        return tf.execute("validate", params)

    # --- Kubernetes ---

    def _k8s_get_pods(self, params: dict) -> dict:
        k8s = self.get_tool("kubernetes")
        result = k8s.execute("get_pods", params)
        print(f"[DevOpsAgent] Pods: {result.get('total', 0)}")
        return result

    def _k8s_get_nodes(self, params: dict) -> dict:
        k8s = self.get_tool("kubernetes")
        result = k8s.execute("get_nodes", params)
        print(f"[DevOpsAgent] Nodes: {result.get('total', 0)}")
        return result

    def _k8s_get_deployments(self, params: dict) -> dict:
        k8s = self.get_tool("kubernetes")
        result = k8s.execute("get_deployments", params)
        print(f"[DevOpsAgent] Deployments: {result.get('total', 0)}")
        return result

    def _k8s_scale(self, params: dict) -> dict:
        k8s = self.get_tool("kubernetes")
        name     = params.get("name")
        replicas = params.get("replicas", 1)
        print(f"[DevOpsAgent] Scaling {name} to {replicas} replicas...")
        return k8s.execute("scale_deployment", params)

    def _k8s_apply(self, params: dict) -> dict:
        k8s = self.get_tool("kubernetes")
        file = params.get("file")
        print(f"[DevOpsAgent] Applying manifest {file}...")
        return k8s.execute("apply_manifest", params)

    def _k8s_rollout(self, params: dict) -> dict:
        k8s = self.get_tool("kubernetes")
        name = params.get("name")
        print(f"[DevOpsAgent] Restarting deployment {name}...")
        return k8s.execute("rollout_restart", params)

    # --- Ansible ---

    def _ansible_ping(self, params: dict) -> dict:
        ansible = self.get_tool("ansible")
        print(f"[DevOpsAgent] Pinging hosts...")
        return ansible.execute("ping_hosts", params)

    def _ansible_run_playbook(self, params: dict) -> dict:
        ansible  = self.get_tool("ansible")
        playbook = params.get("playbook")
        print(f"[DevOpsAgent] Running playbook {playbook}...")
        return ansible.execute("run_playbook", params)

    def _ansible_adhoc(self, params: dict) -> dict:
        ansible = self.get_tool("ansible")
        module  = params.get("module", "ping")
        hosts   = params.get("hosts", "all")
        print(f"[DevOpsAgent] Running ad-hoc '{module}' on '{hosts}'...")
        return ansible.execute("run_adhoc", params)