# agents/security_agent.py
# Security Agent — escanea vulnerabilidades y misconfiguraciones.
# v2.0 Task-centric: ejecuta Tasks individuales asignadas por WorkflowEngine.

from core.interfaces.agent import Agent
from core.interfaces.task import Task


class SecurityAgent(Agent):
    """
    Security Agent de LRA AI Platform.

    Especialidad: detección de vulnerabilidades y misconfiguraciones
    en código, imágenes Docker, Terraform y Kubernetes.

    Tasks que sabe ejecutar:
        scan_image              → escanea imagen Docker (Trivy)
        scan_filesystem         → escanea directorio (Trivy)
        scan_terraform          → escanea IaC Terraform (Checkov)
        scan_kubernetes         → escanea manifests K8s (Checkov + Trivy)
        scan_dockerfile         → escanea Dockerfile (Checkov)
        scan_github_actions     → escanea workflows (Checkov)
        scan_repository         → escaneo completo de un repo
        generate_security_report → genera informe consolidado

    Tools que usa:
        - trivy   → vulnerabilidades en imágenes y filesystem
        - checkov → misconfiguraciones en IaC
        - github  → leer archivos del repositorio
    """

    _TASK_HANDLERS = [
        "scan_image",
        "scan_filesystem",
        "scan_terraform",
        "scan_kubernetes",
        "scan_dockerfile",
        "scan_github_actions",
        "scan_repository",
        "generate_security_report",
    ]

    def execute_task(self, task: Task) -> dict:
        handlers = {
            "scan_image":              self._scan_image,
            "scan_filesystem":         self._scan_filesystem,
            "scan_terraform":          self._scan_terraform,
            "scan_kubernetes":         self._scan_kubernetes,
            "scan_dockerfile":         self._scan_dockerfile,
            "scan_github_actions":     self._scan_github_actions,
            "scan_repository":         self._scan_repository,
            "generate_security_report": self._generate_security_report,
        }

        handler = handlers.get(task.type)
        if handler is None:
            raise ValueError(
                f"SecurityAgent does not handle task type '{task.type}'. "
                f"Supported: {list(handlers.keys())}"
            )
        return handler(task.params)

    def run(self, task: str, context: dict = {}) -> dict:
        """Compatibilidad v1.0."""
        t = Task(type=task.replace(" ", "_"), params=context, assigned_to="security")
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

    def _scan_image(self, params: dict) -> dict:
        """Escanea una imagen Docker con Trivy."""
        trivy = self.get_tool("trivy")
        image = params.get("image", "nginx:latest")
        print(f"[SecurityAgent] Scanning image: {image}")
        return trivy.execute("scan_image", params)

    def _scan_filesystem(self, params: dict) -> dict:
        """Escanea un directorio con Trivy."""
        trivy = self.get_tool("trivy")
        path = params.get("path", ".")
        print(f"[SecurityAgent] Scanning filesystem: {path}")
        return trivy.execute("scan_filesystem", params)

    def _scan_terraform(self, params: dict) -> dict:
        """Escanea Terraform con Checkov."""
        checkov = self.get_tool("checkov")
        path = params.get("path", ".")
        print(f"[SecurityAgent] Scanning Terraform: {path}")
        return checkov.execute("scan_terraform", params)

    def _scan_kubernetes(self, params: dict) -> dict:
        """Escanea manifests de Kubernetes con Checkov y Trivy."""
        checkov = self.get_tool("checkov")
        path = params.get("path", ".")
        print(f"[SecurityAgent] Scanning Kubernetes manifests: {path}")
        checkov_result = checkov.execute("scan_kubernetes", params)

        try:
            trivy = self.get_tool("trivy")
            trivy_result = trivy.execute("scan_kubernetes", params)
        except ValueError:
            trivy_result = {"note": "trivy not available"}

        return {
            "checkov": checkov_result,
            "trivy": trivy_result,
            "summary": f"Checkov: {checkov_result.get('summary')} | "
                       f"Trivy misconfigs: {trivy_result.get('total_misconfigurations', 0)}"
        }

    def _scan_dockerfile(self, params: dict) -> dict:
        """Escanea Dockerfile con Checkov."""
        checkov = self.get_tool("checkov")
        print(f"[SecurityAgent] Scanning Dockerfile")
        return checkov.execute("scan_dockerfile", params)

    def _scan_github_actions(self, params: dict) -> dict:
        """Escanea GitHub Actions workflows con Checkov."""
        checkov = self.get_tool("checkov")
        print(f"[SecurityAgent] Scanning GitHub Actions workflows")
        return checkov.execute("scan_github_actions", params)

    def _scan_repository(self, params: dict) -> dict:
        """
        Escaneo completo de un repositorio:
        filesystem (Trivy) + Terraform (Checkov) + Dockerfile (Checkov)
        """
        path = params.get("path", ".")
        print(f"[SecurityAgent] Full repository scan: {path}")

        results = {}
        trivy   = self.get_tool("trivy")
        checkov = self.get_tool("checkov")

        results["filesystem"] = trivy.execute("scan_filesystem", {"path": path})
        results["terraform"]  = checkov.execute("scan_terraform", {"path": path})
        results["dockerfile"] = checkov.execute("scan_dockerfile", {"path": path})
        results["kubernetes"] = checkov.execute("scan_kubernetes", {"path": path})

        total_vulns   = results["filesystem"].get("total_vulnerabilities", 0)
        total_critical = results["filesystem"].get("critical", 0)
        total_high    = results["filesystem"].get("high", 0)
        total_misconfigs = (
            results["terraform"].get("failed", 0) +
            results["dockerfile"].get("failed", 0) +
            results["kubernetes"].get("failed", 0)
        )

        return {
            "path": path,
            "results": results,
            "summary": {
                "total_vulnerabilities": total_vulns,
                "critical": total_critical,
                "high": total_high,
                "total_misconfigurations": total_misconfigs,
                "status": "PASS" if total_critical == 0 and total_misconfigs == 0 else "FAIL",
            }
        }

    def _generate_security_report(self, params: dict) -> dict:
        """
        Genera un informe de seguridad completo en Markdown
        y opcionalmente lo guarda en GitHub.
        """
        path = params.get("path", ".")
        repo = params.get("repo")
        org  = params.get("org", "lra-cloud-ops")

        scan_result = self._scan_repository({"path": path})
        summary = scan_result.get("summary", {})
        results = scan_result.get("results", {})

        status_icon = "✅" if summary.get("status") == "PASS" else "❌"

        report_md = f"""# Security Report

**Generated by:** LRA AI Platform — Security Agent
**Target:** {path}
**Status:** {status_icon} {summary.get('status', 'UNKNOWN')}

## Summary

| Check | Result |
|---|---|
| Critical Vulnerabilities | {summary.get('critical', 0)} |
| High Vulnerabilities | {summary.get('high', 0)} |
| Total Vulnerabilities | {summary.get('total_vulnerabilities', 0)} |
| Misconfigurations | {summary.get('total_misconfigurations', 0)} |

## Filesystem Scan (Trivy)

{results.get('filesystem', {}).get('summary', 'N/A')}

## Terraform Scan (Checkov)

{results.get('terraform', {}).get('summary', 'N/A')}

## Dockerfile Scan (Checkov)

{results.get('dockerfile', {}).get('summary', 'N/A')}

## Kubernetes Scan (Checkov)

{results.get('kubernetes', {}).get('summary', 'N/A')}

---
*Generated by LRA AI Platform — Security Agent v1.0*
"""

        result = {"report": report_md, "summary": summary}

        if repo:
            try:
                github = self.get_tool("github")
                github.execute("create_file", {
                    "repo": repo,
                    "org": org,
                    "path": "docs/SECURITY_REPORT.md",
                    "content": report_md,
                    "message": "docs: add security report (Security Agent)",
                })
                print(f"[SecurityAgent] Report saved to {org}/{repo}")
                result["saved_to"] = f"{org}/{repo}/docs/SECURITY_REPORT.md"
            except Exception as e:
                result["github_error"] = str(e)

        return result