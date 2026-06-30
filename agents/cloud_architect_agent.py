# agents/cloud_architect_agent.py
# Cloud Architect Agent — diseña y revisa arquitecturas cloud multi-proveedor.
# v2.0 Task-centric: ejecuta Tasks individuales asignadas por WorkflowEngine.

from core.interfaces.agent import Agent
from core.interfaces.task import Task


class CloudArchitectAgent(Agent):
    """
    Cloud Architect Agent de LRA AI Platform.

    Especialidad: diseño y revisión de arquitecturas cloud multi-proveedor.
    Soporta AWS, Azure y GCP via BaseCloudTool.generate_report().

    Tasks que sabe ejecutar:
        review_aws_architecture    → informe completo de infraestructura AWS
        review_azure_architecture  → informe completo de infraestructura Azure
        review_gcp_architecture    → informe completo de infraestructura GCP
        review_multicloud          → informe combinado de las 3 clouds
        list_vpcs                  → lista VPCs en AWS
        list_eks_clusters          → lista clusters EKS en AWS
        list_s3_buckets            → lista buckets S3 en AWS
        list_ec2_instances         → lista instancias EC2 en AWS
        list_ecr_repos             → lista repositorios ECR en AWS
        generate_architecture_report → genera informe en Markdown y lo guarda en GitHub

    Tools que usa:
        - aws    → infraestructura AWS real
        - azure  → infraestructura Azure real
        - gcp    → infraestructura GCP real
        - github → guardar informes en repositorios
    """

    _TASK_HANDLERS = [
        "review_aws_architecture",
        "review_azure_architecture",
        "review_gcp_architecture",
        "review_multicloud",
        "list_vpcs",
        "list_eks_clusters",
        "list_s3_buckets",
        "list_ec2_instances",
        "list_ecr_repos",
        "generate_architecture_report",
    ]

    def execute_task(self, task: Task) -> dict:
        """Ejecuta una Task individual asignada por el WorkflowEngine."""
        handlers = {
            "review_aws_architecture":   self._review_aws,
            "review_azure_architecture": self._review_azure,
            "review_gcp_architecture":   self._review_gcp,
            "review_multicloud":         self._review_multicloud,
            "list_vpcs":                 self._list_vpcs,
            "list_eks_clusters":         self._list_eks_clusters,
            "list_s3_buckets":           self._list_s3_buckets,
            "list_ec2_instances":        self._list_ec2_instances,
            "list_ecr_repos":            self._list_ecr_repos,
            "generate_architecture_report": self._generate_architecture_report,
        }

        handler = handlers.get(task.type)
        if handler is None:
            raise ValueError(
                f"CloudArchitectAgent does not handle task type '{task.type}'. "
                f"Supported: {list(handlers.keys())}"
            )
        return handler(task.params)

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tools": list(self.tools.keys()),
            "supported_tasks": self._TASK_HANDLERS,
        }

    def run(self, task: str, context: dict = {}) -> dict:
        """Compatibilidad v1.0 — delega a execute_task()."""
        t = Task(type=task.replace(" ", "_"), params=context, assigned_to="cloud_architect")
        return self.execute_task(t)

    # --- Implementaciones ---

    def _review_aws(self, params: dict) -> dict:
        """Genera informe completo de infraestructura AWS."""
        aws = self.get_tool("aws")
        print(f"[CloudArchitectAgent] Reviewing AWS infrastructure...")
        report = aws.generate_report(params)
        print(f"[CloudArchitectAgent] AWS review complete.")
        return report

    def _review_azure(self, params: dict) -> dict:
        """Genera informe completo de infraestructura Azure."""
        azure = self.get_tool("azure")
        print(f"[CloudArchitectAgent] Reviewing Azure infrastructure...")
        report = azure.generate_report(params)
        print(f"[CloudArchitectAgent] Azure review complete.")
        return report

    def _review_gcp(self, params: dict) -> dict:
        """Genera informe completo de infraestructura GCP."""
        gcp = self.get_tool("gcp")
        print(f"[CloudArchitectAgent] Reviewing GCP infrastructure...")
        report = gcp.generate_report(params)
        print(f"[CloudArchitectAgent] GCP review complete.")
        return report

    def _review_multicloud(self, params: dict) -> dict:
        """
        Genera un informe combinado de las 3 clouds.
        Cada cloud se revisa de forma independiente y se consolida.
        """
        print(f"[CloudArchitectAgent] Starting multi-cloud review...")
        results = {}

        for cloud in ["aws", "azure", "gcp"]:
            try:
                tool = self.get_tool(cloud)
                results[cloud] = tool.generate_report(params)
                print(f"[CloudArchitectAgent] {cloud.upper()} review complete.")
            except ValueError:
                results[cloud] = {"error": f"Tool '{cloud}' not available"}
                print(f"[CloudArchitectAgent] {cloud.upper()} not available, skipping.")

        total_summary = {
            "aws":   results.get("aws", {}).get("summary", {}),
            "azure": results.get("azure", {}).get("summary", {}),
            "gcp":   results.get("gcp", {}).get("summary", {}),
        }

        return {
            "type": "multicloud_report",
            "clouds": results,
            "total_summary": total_summary,
        }

    def _list_vpcs(self, params: dict) -> dict:
        aws = self.get_tool("aws")
        return aws.execute("list_vpcs", params)

    def _list_eks_clusters(self, params: dict) -> dict:
        aws = self.get_tool("aws")
        return aws.execute("list_eks_clusters", params)

    def _list_s3_buckets(self, params: dict) -> dict:
        aws = self.get_tool("aws")
        return aws.execute("list_s3_buckets", params)

    def _list_ec2_instances(self, params: dict) -> dict:
        aws = self.get_tool("aws")
        return aws.execute("list_ec2_instances", params)

    def _list_ecr_repos(self, params: dict) -> dict:
        aws = self.get_tool("aws")
        return aws.execute("list_ecr_repos", params)

    def _generate_architecture_report(self, params: dict) -> dict:
        """
        Genera un informe de arquitectura multi-cloud en Markdown
        y lo guarda en el repositorio indicado via GitHub Tool.
        """
        repo   = params.get("repo")
        org    = params.get("org", "lra-cloud-ops")
        clouds = params.get("clouds", ["aws"])

        sections = []
        total_summary = {}

        for cloud in clouds:
            try:
                tool = self.get_tool(cloud)
                report = tool.generate_report(params)
                total_summary[cloud] = report.get("summary", {})

                identity = report.get("identity", {})
                summary  = report.get("summary", {})

                sections.append(f"""
## {cloud.upper()} Infrastructure

**Account/Project:** {identity}

| Resource | Count |
|---|---|
| Compute | {summary.get('compute_count', 0)} |
| Storage | {summary.get('storage_count', 0)} |
| Networks | {summary.get('network_count', 0)} |
| Kubernetes | {summary.get('kubernetes_count', 0)} |
| Registries | {summary.get('registry_count', 0)} |
""")
            except ValueError:
                sections.append(f"\n## {cloud.upper()}\n\n_Tool not available._\n")

        report_md = f"""# Multi-Cloud Architecture Report

**Generated by:** LRA AI Platform — Cloud Architect Agent
**Organization:** {org}
**Clouds reviewed:** {', '.join(c.upper() for c in clouds)}

{"".join(sections)}

---
*Generated by LRA AI Platform — Cloud Architect Agent v2.0*
"""

        result = {"report": report_md, "summary": total_summary}

        if repo:
            github = self.get_tool("github")
            github.execute("create_file", {
                "repo": repo,
                "org": org,
                "path": "docs/MULTICLOUD_REPORT.md",
                "content": report_md,
                "message": "docs: add multi-cloud architecture report",
            })
            print(f"[CloudArchitectAgent] Report saved to {org}/{repo}")
            result["saved_to"] = f"{org}/{repo}/docs/MULTICLOUD_REPORT.md"

        return result