# agents/reviewer_agent.py
# Reviewer Agent — revisa PRs, calidad de código y seguridad.
# v2.0 Task-centric: ejecuta Tasks individuales asignadas por WorkflowEngine.

from core.interfaces.agent import Agent
from core.interfaces.task import Task


class ReviewerAgent(Agent):
    """
    Reviewer Agent de LRA AI Platform.

    Especialidad: revisión de Pull Requests, análisis de calidad
    de código y escaneos de seguridad antes de merge.

    Tasks que sabe ejecutar:
        review_pr               → revisa un PR completo
        list_open_prs           → lista PRs abiertos en un repo
        approve_pr              → aprueba un PR
        request_changes         → solicita cambios en un PR
        add_pr_comment          → añade comentario a un PR
        check_pr_security       → escanea seguridad del código del PR
        check_pr_quality        → verifica calidad del código
        generate_review_report  → genera informe completo de revisión

    Tools que usa:
        - github  → leer PRs, archivos, añadir comentarios
        - trivy   → escaneos de seguridad en el código
        - checkov → análisis de misconfiguraciones IaC
    """

    _TASK_HANDLERS = [
        "review_pr",
        "list_open_prs",
        "approve_pr",
        "request_changes",
        "add_pr_comment",
        "check_pr_security",
        "check_pr_quality",
        "generate_review_report",
    ]

    def execute_task(self, task: Task) -> dict:
        handlers = {
            "review_pr":             self._review_pr,
            "list_open_prs":         self._list_open_prs,
            "approve_pr":            self._approve_pr,
            "request_changes":       self._request_changes,
            "add_pr_comment":        self._add_pr_comment,
            "check_pr_security":     self._check_pr_security,
            "check_pr_quality":      self._check_pr_quality,
            "generate_review_report": self._generate_review_report,
        }

        handler = handlers.get(task.type)
        if handler is None:
            raise ValueError(
                f"ReviewerAgent does not handle task type '{task.type}'. "
                f"Supported: {list(handlers.keys())}"
            )
        return handler(task.params)

    def run(self, task: str, context: dict = {}) -> dict:
        """Compatibilidad v1.0."""
        t = Task(type=task.replace(" ", "_"), params=context, assigned_to="reviewer")
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

    def _list_open_prs(self, params: dict) -> dict:
        """Lista todos los PRs abiertos en un repositorio."""
        github = self.get_tool("github")
        repo   = params.get("repo")
        org    = params.get("org", "lra-cloud-ops")
        print(f"[ReviewerAgent] Listing open PRs in {org}/{repo}...")
        result = github.execute("list_prs", {"repo": repo, "org": org, "state": "open"})
        prs = result.get("prs", [])
        print(f"[ReviewerAgent] Found {len(prs)} open PRs")
        return result

    def _review_pr(self, params: dict) -> dict:
        """
        Revisa un PR completo:
        - Lee los archivos cambiados
        - Analiza el contenido
        - Genera un resumen de la revisión
        """
        github = self.get_tool("github")
        repo   = params.get("repo")
        org    = params.get("org", "lra-cloud-ops")
        pr_number = params.get("pr_number")

        print(f"[ReviewerAgent] Reviewing PR #{pr_number} in {org}/{repo}...")

        pr_info = github.execute("get_pr", {
            "repo": repo, "org": org, "pr_number": pr_number
        })

        files = github.execute("get_pr_files", {
            "repo": repo, "org": org, "pr_number": pr_number
        })

        changed_files = files.get("files", [])
        total_additions = sum(f.get("additions", 0) for f in changed_files)
        total_deletions = sum(f.get("deletions", 0) for f in changed_files)

        # Clasificar archivos por tipo
        terraform_files = [f for f in changed_files if f.get("filename", "").endswith(".tf")]
        k8s_files       = [f for f in changed_files if f.get("filename", "").endswith(".yaml")
                          or f.get("filename", "").endswith(".yml")]
        python_files    = [f for f in changed_files if f.get("filename", "").endswith(".py")]
        docker_files    = [f for f in changed_files if "Dockerfile" in f.get("filename", "")]

        review = {
            "pr_number": pr_number,
            "repo": f"{org}/{repo}",
            "title": pr_info.get("title", ""),
            "author": pr_info.get("user", {}).get("login", ""),
            "base": pr_info.get("base", {}).get("ref", ""),
            "head": pr_info.get("head", {}).get("ref", ""),
            "total_files": len(changed_files),
            "additions": total_additions,
            "deletions": total_deletions,
            "file_types": {
                "terraform": len(terraform_files),
                "kubernetes": len(k8s_files),
                "python": len(python_files),
                "dockerfile": len(docker_files),
                "other": len(changed_files) - len(terraform_files) - len(k8s_files)
                         - len(python_files) - len(docker_files),
            },
            "changed_files": [f.get("filename") for f in changed_files],
        }

        print(f"[ReviewerAgent] PR #{pr_number}: {len(changed_files)} files, "
              f"+{total_additions}/-{total_deletions}")
        return review

    def _approve_pr(self, params: dict) -> dict:
        """Aprueba un PR con un comentario."""
        github    = self.get_tool("github")
        repo      = params.get("repo")
        org       = params.get("org", "lra-cloud-ops")
        pr_number = params.get("pr_number")
        comment   = params.get("comment", "✅ Approved by LRA AI Platform — Reviewer Agent")

        print(f"[ReviewerAgent] Approving PR #{pr_number}...")
        result = github.execute("review_pr", {
            "repo": repo, "org": org,
            "pr_number": pr_number,
            "event": "APPROVE",
            "body": comment,
        })
        return {"approved": True, "pr_number": pr_number, "comment": comment}

    def _request_changes(self, params: dict) -> dict:
        """Solicita cambios en un PR."""
        github    = self.get_tool("github")
        repo      = params.get("repo")
        org       = params.get("org", "lra-cloud-ops")
        pr_number = params.get("pr_number")
        comment   = params.get("comment", "❌ Changes requested by LRA AI Platform — Reviewer Agent")
        reasons   = params.get("reasons", [])

        full_comment = comment
        if reasons:
            full_comment += "\n\n**Issues found:**\n"
            full_comment += "\n".join(f"- {r}" for r in reasons)

        print(f"[ReviewerAgent] Requesting changes on PR #{pr_number}...")
        result = github.execute("review_pr", {
            "repo": repo, "org": org,
            "pr_number": pr_number,
            "event": "REQUEST_CHANGES",
            "body": full_comment,
        })
        return {
            "changes_requested": True,
            "pr_number": pr_number,
            "reasons": reasons,
        }

    def _add_pr_comment(self, params: dict) -> dict:
        """Añade un comentario a un PR."""
        github    = self.get_tool("github")
        repo      = params.get("repo")
        org       = params.get("org", "lra-cloud-ops")
        pr_number = params.get("pr_number")
        comment   = params.get("comment", "")

        print(f"[ReviewerAgent] Adding comment to PR #{pr_number}...")
        return github.execute("create_issue_comment", {
            "repo": repo, "org": org,
            "issue_number": pr_number,
            "body": comment,
        })

    def _check_pr_security(self, params: dict) -> dict:
        """
        Escanea seguridad del código en el PR.
        Usa Trivy y Checkov si están disponibles.
        """
        path = params.get("path", ".")
        print(f"[ReviewerAgent] Running security scan on {path}...")

        results = {}

        try:
            trivy = self.get_tool("trivy")
            results["trivy"] = trivy.execute("scan_filesystem", {"path": path})
        except ValueError:
            results["trivy"] = {"available": False}

        try:
            checkov = self.get_tool("checkov")
            results["checkov_terraform"]  = checkov.execute("scan_terraform",  {"path": path})
            results["checkov_kubernetes"] = checkov.execute("scan_kubernetes", {"path": path})
            results["checkov_dockerfile"] = checkov.execute("scan_dockerfile", {"path": path})
        except ValueError:
            results["checkov"] = {"available": False}

        critical = results.get("trivy", {}).get("critical", 0)
        high     = results.get("trivy", {}).get("high", 0)
        tf_failed = results.get("checkov_terraform", {}).get("failed", 0)

        status = "PASS" if critical == 0 and tf_failed == 0 else "FAIL"

        return {
            "scan_results": results,
            "summary": {
                "critical_vulns": critical,
                "high_vulns": high,
                "terraform_failed": tf_failed,
                "status": status,
            }
        }

    def _check_pr_quality(self, params: dict) -> dict:
        """
        Verifica calidad básica del PR:
        - Tiene descripción
        - Tiene tests
        - Tiene documentación actualizada
        """
        github    = self.get_tool("github")
        repo      = params.get("repo")
        org       = params.get("org", "lra-cloud-ops")
        pr_number = params.get("pr_number")

        pr_info = github.execute("get_pr", {
            "repo": repo, "org": org, "pr_number": pr_number
        })

        files = github.execute("get_pr_files", {
            "repo": repo, "org": org, "pr_number": pr_number
        })

        changed_files = [f.get("filename", "") for f in files.get("files", [])]

        has_description = bool(pr_info.get("body", "").strip())
        has_tests       = any("test" in f.lower() for f in changed_files)
        has_docs        = any(f.endswith(".md") for f in changed_files)
        has_changelog   = any("CHANGELOG" in f for f in changed_files)

        issues = []
        if not has_description:
            issues.append("PR has no description")
        if not has_tests:
            issues.append("No test files found in changes")
        if not has_docs:
            issues.append("No documentation updates found")

        score = sum([has_description, has_tests, has_docs, has_changelog])
        quality = "GOOD" if score >= 3 else "NEEDS_IMPROVEMENT" if score >= 1 else "POOR"

        return {
            "pr_number": pr_number,
            "has_description": has_description,
            "has_tests": has_tests,
            "has_docs": has_docs,
            "has_changelog": has_changelog,
            "issues": issues,
            "score": f"{score}/4",
            "quality": quality,
        }

    def _generate_review_report(self, params: dict) -> dict:
        """
        Genera un informe completo de revisión combinando:
        revisión del PR + seguridad + calidad.
        """
        repo      = params.get("repo")
        org       = params.get("org", "lra-cloud-ops")
        pr_number = params.get("pr_number")
        path      = params.get("path", ".")

        print(f"[ReviewerAgent] Generating full review report for PR #{pr_number}...")

        pr_review   = self._review_pr(params)
        pr_quality  = self._check_pr_quality(params)
        pr_security = self._check_pr_security({"path": path})

        security_status = pr_security.get("summary", {}).get("status", "UNKNOWN")
        quality_status  = pr_quality.get("quality", "UNKNOWN")

        overall = "APPROVE" if (
            security_status == "PASS" and quality_status in ("GOOD", "NEEDS_IMPROVEMENT")
        ) else "REQUEST_CHANGES"

        report = {
            "pr_number": pr_number,
            "repo": f"{org}/{repo}",
            "review": pr_review,
            "quality": pr_quality,
            "security": pr_security,
            "recommendation": overall,
            "summary": {
                "files_changed": pr_review.get("total_files", 0),
                "additions": pr_review.get("additions", 0),
                "deletions": pr_review.get("deletions", 0),
                "security_status": security_status,
                "quality_score": pr_quality.get("score", "0/4"),
                "recommendation": overall,
            }
        }

        print(f"[ReviewerAgent] Review complete. Recommendation: {overall}")
        return report