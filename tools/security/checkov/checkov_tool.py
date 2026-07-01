# tools/security/checkov/checkov_tool.py
# Implementación de la Checkov Tool para LRA AI Platform.
# Escanea IaC (Terraform, Kubernetes, Dockerfile) en busca de misconfiguraciones.

import os
import subprocess
import json
from core.interfaces.tool import Tool


class CheckovTool(Tool):
    """
    Tool para ejecutar escaneos de seguridad con Checkov.

    Checkov detecta misconfiguraciones en:
    - Terraform (HCL)
    - Kubernetes (YAML)
    - Dockerfiles
    - GitHub Actions workflows
    - CloudFormation, ARM templates

    Uso:
        checkov = CheckovTool()
        checkov.execute("scan_terraform", {"path": "terraform/"})
        checkov.execute("scan_kubernetes", {"path": "k8s/"})
        checkov.execute("scan_dockerfile", {"path": "."})
    """

    def __init__(self):
        super().__init__(name="checkov", version="1.0.0")

    def _run(self, args: list) -> dict:
        """Ejecuta checkov via python -m checkov.main."""
        cmd = ["python", "-m", "checkov.main"] + args + ["--output", "json", "--quiet"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True
            )
            output = result.stdout.strip()
            try:
                data = json.loads(output) if output else {}
                return {
                    "success": True,
                    "data": data,
                    "stderr": result.stderr.strip(),
                    "returncode": result.returncode,
                }
            except json.JSONDecodeError:
                return {
                    "success": result.returncode == 0,
                    "stdout": output,
                    "stderr": result.stderr.strip(),
                    "returncode": result.returncode,
                }
        except FileNotFoundError:
            return {
                "success": False,
                "stderr": "checkov not found",
                "returncode": -1,
            }

    def validate(self) -> bool:
        result = subprocess.run(
            ["python", "-m", "checkov.main", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"[CheckovTool] Checkov {result.stdout.strip()}")
            return True
        print(f"[CheckovTool] Validation failed: {result.stderr}")
        return False

    def get_capabilities(self) -> list:
        return [
            "scan_terraform",
            "scan_kubernetes",
            "scan_dockerfile",
            "scan_github_actions",
            "scan_directory",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(f"Action '{action}' not supported.")

        actions = {
            "scan_terraform":      self._scan_terraform,
            "scan_kubernetes":     self._scan_kubernetes,
            "scan_dockerfile":     self._scan_dockerfile,
            "scan_github_actions": self._scan_github_actions,
            "scan_directory":      self._scan_directory,
        }
        return actions[action](params)

    def _scan_terraform(self, params: dict) -> dict:
        """Escanea código Terraform."""
        path = params.get("path", ".")
        print(f"[CheckovTool] Scanning Terraform: {path}...")
        result = self._run(["-d", path, "--framework", "terraform"])
        return self._parse_result(result, "terraform", path)

    def _scan_kubernetes(self, params: dict) -> dict:
        """Escanea manifests de Kubernetes."""
        path = params.get("path", ".")
        print(f"[CheckovTool] Scanning Kubernetes: {path}...")
        result = self._run(["-d", path, "--framework", "kubernetes"])
        return self._parse_result(result, "kubernetes", path)

    def _scan_dockerfile(self, params: dict) -> dict:
        """Escanea Dockerfiles."""
        path = params.get("path", ".")
        print(f"[CheckovTool] Scanning Dockerfile: {path}...")
        result = self._run(["-d", path, "--framework", "dockerfile"])
        return self._parse_result(result, "dockerfile", path)

    def _scan_github_actions(self, params: dict) -> dict:
        """Escanea GitHub Actions workflows."""
        path = params.get("path", ".github/workflows")
        print(f"[CheckovTool] Scanning GitHub Actions: {path}...")
        result = self._run(["-d", path, "--framework", "github_actions"])
        return self._parse_result(result, "github_actions", path)

    def _scan_directory(self, params: dict) -> dict:
        """Escanea un directorio completo con todos los frameworks."""
        path = params.get("path", ".")
        print(f"[CheckovTool] Scanning directory: {path}...")
        result = self._run(["-d", path])
        return self._parse_result(result, "directory", path)

    def _parse_result(self, result: dict, scan_type: str, target: str) -> dict:
        """Parsea el resultado de Checkov."""
        if not result.get("success") and "data" not in result:
            return {
                "scan_type": scan_type,
                "target": target,
                "error": result.get("stderr", "Unknown error")[:200],
                "passed": 0,
                "failed": 0,
                "checks": [],
            }

        data = result.get("data", {})
        if isinstance(data, list):
            data = data[0] if data else {}

        summary = data.get("summary", {})
        passed  = summary.get("passed", 0)
        failed  = summary.get("failed", 0)

        failed_checks = []
        for check in data.get("results", {}).get("failed_checks", []) or []:
            failed_checks.append({
                "check_id":   check.get("check_id"),
                "check_name": check.get("check",{}).get("name", ""),
                "file":       check.get("repo_file_path", ""),
                "severity":   check.get("check", {}).get("severity", "UNKNOWN"),
                "guideline":  check.get("check", {}).get("guideline", ""),
            })

        return {
            "scan_type": scan_type,
            "target": target,
            "passed": passed,
            "failed": failed,
            "total_checks": passed + failed,
            "failed_checks": failed_checks[:20],
            "summary": f"{passed} passed, {failed} failed",
        }