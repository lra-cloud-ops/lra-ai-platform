# tools/security/trivy/trivy_tool.py
# Implementación de la Trivy Tool para LRA AI Platform.
# Ejecuta escaneos de seguridad reales via Trivy CLI.

import os
import subprocess
import json
from core.interfaces.tool import Tool


class TrivyTool(Tool):
    """
    Tool para ejecutar escaneos de seguridad con Trivy.

    Trivy detecta vulnerabilidades en:
    - Imágenes Docker
    - Repositorios de código (filesystem)
    - Manifests de Kubernetes
    - Configuraciones de Terraform (IaC)

    Uso:
        trivy = TrivyTool()
        trivy.execute("scan_image", {"image": "nginx:latest"})
        trivy.execute("scan_filesystem", {"path": "."})
        trivy.execute("scan_kubernetes", {"path": "k8s/"})
    """

    def __init__(self):
        super().__init__(name="trivy", version="1.0.0")
        self._trivy_bin = self._find_trivy()

    def _find_trivy(self) -> str:
        import shutil
        return shutil.which("trivy") or "trivy"

    def _run(self, args: list) -> dict:
        """Ejecuta trivy y retorna el resultado."""
        cmd = [self._trivy_bin] + args + ["--format", "json", "--quiet"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True
            )
            output = result.stdout.strip()
            try:
                return {
                    "success": result.returncode in (0, 1),
                    "data": json.loads(output) if output else {},
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
                "stderr": "trivy binary not found",
                "returncode": -1,
            }

    def validate(self) -> bool:
        try:
            result = subprocess.run(
                [self._trivy_bin, "--version"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0]
                print(f"[TrivyTool] {version}")
                return True
        except Exception as e:
            print(f"[TrivyTool] Validation failed: {e}")
        return False

    def get_capabilities(self) -> list:
        return [
            "scan_image",
            "scan_filesystem",
            "scan_kubernetes",
            "scan_terraform",
            "scan_repo",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(f"Action '{action}' not supported.")

        actions = {
            "scan_image":      self._scan_image,
            "scan_filesystem": self._scan_filesystem,
            "scan_kubernetes": self._scan_kubernetes,
            "scan_terraform":  self._scan_terraform,
            "scan_repo":       self._scan_filesystem,
        }
        return actions[action](params)

    def _scan_image(self, params: dict) -> dict:
        """Escanea una imagen Docker en busca de vulnerabilidades."""
        image = params.get("image", "nginx:latest")
        severity = params.get("severity", "HIGH,CRITICAL")
        print(f"[TrivyTool] Scanning image: {image}...")
        result = self._run(["image", f"--severity={severity}", image])
        return self._parse_result(result, "image", image)

    def _scan_filesystem(self, params: dict) -> dict:
        """Escanea un directorio en busca de vulnerabilidades."""
        path = params.get("path", ".")
        severity = params.get("severity", "HIGH,CRITICAL")
        print(f"[TrivyTool] Scanning filesystem: {path}...")
        result = self._run(["fs", f"--severity={severity}", path])
        return self._parse_result(result, "filesystem", path)

    def _scan_kubernetes(self, params: dict) -> dict:
        """Escanea manifests de Kubernetes."""
        path = params.get("path", ".")
        print(f"[TrivyTool] Scanning Kubernetes manifests: {path}...")
        result = self._run(["config", path])
        return self._parse_result(result, "kubernetes", path)

    def _scan_terraform(self, params: dict) -> dict:
        """Escanea configuraciones de Terraform."""
        path = params.get("path", ".")
        print(f"[TrivyTool] Scanning Terraform: {path}...")
        result = self._run(["config", path])
        return self._parse_result(result, "terraform", path)

    def _parse_result(self, result: dict, scan_type: str, target: str) -> dict:
        """Parsea el resultado de Trivy en un formato limpio."""
        if not result.get("success"):
            return {
                "scan_type": scan_type,
                "target": target,
                "error": result.get("stderr", "Unknown error"),
                "vulnerabilities": [],
                "total": 0,
            }

        data = result.get("data", {})
        results = data.get("Results", []) if isinstance(data, dict) else []

        vulns = []
        for r in results:
            for v in r.get("Vulnerabilities", []) or []:
                vulns.append({
                    "id": v.get("VulnerabilityID"),
                    "severity": v.get("Severity"),
                    "package": v.get("PkgName"),
                    "version": v.get("InstalledVersion"),
                    "fixed_version": v.get("FixedVersion"),
                    "title": v.get("Title", ""),
                })

        misconfigs = []
        for r in results:
            for m in r.get("Misconfigurations", []) or []:
                misconfigs.append({
                    "id": m.get("ID"),
                    "severity": m.get("Severity"),
                    "title": m.get("Title"),
                    "description": m.get("Description", "")[:100],
                    "resolution": m.get("Resolution", ""),
                })

        critical = sum(1 for v in vulns if v["severity"] == "CRITICAL")
        high     = sum(1 for v in vulns if v["severity"] == "HIGH")

        return {
            "scan_type": scan_type,
            "target": target,
            "vulnerabilities": vulns,
            "misconfigurations": misconfigs,
            "total_vulnerabilities": len(vulns),
            "total_misconfigurations": len(misconfigs),
            "critical": critical,
            "high": high,
            "summary": f"{critical} CRITICAL, {high} HIGH vulnerabilities found",
        }