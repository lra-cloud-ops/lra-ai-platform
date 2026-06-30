# tools/iac/terraform/terraform_tool.py
# Implementación de la Terraform Tool para LRA AI Platform.
# Ejecuta comandos terraform reales via subprocess.

import os
import subprocess
import json
from pathlib import Path
from core.interfaces.tool import Tool


class TerraformTool(Tool):
    """
    Tool para ejecutar Terraform via subprocess.

    Ejecuta comandos terraform reales contra el directorio
    de trabajo especificado en los params de cada acción.

    Uso:
        tf = TerraformTool()
        tf.execute("init", {"working_dir": "terraform/"})
        tf.execute("plan", {"working_dir": "terraform/", "var_file": "prod.tfvars"})
        tf.execute("validate", {"working_dir": "terraform/"})
    """

    def __init__(self):
        super().__init__(name="terraform", version="1.0.0")
        self._terraform_bin = self._find_terraform()

    def _find_terraform(self) -> str:
        """Encuentra el binario de terraform en el PATH."""
        import shutil
        path = shutil.which("terraform")
        return path or "terraform"

    def _run(self, args: list, working_dir: str = ".", env: dict = None) -> dict:
        """Ejecuta un comando terraform y retorna stdout/stderr."""
        cmd = [self._terraform_bin] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                env={**os.environ, **(env or {})}
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "success": result.returncode == 0,
            }
        except FileNotFoundError:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "terraform binary not found",
                "success": False,
            }

    def validate(self) -> bool:
        """Verifica que terraform está instalado."""
        result = self._run(["version", "-json"])
        if result["success"]:
            try:
                data = json.loads(result["stdout"])
                print(f"[TerraformTool] Version: {data.get('terraform_version')}")
                return True
            except Exception:
                print(f"[TerraformTool] Available: {result['stdout'][:50]}")
                return True
        print(f"[TerraformTool] Validation failed: {result['stderr']}")
        return False

    def get_capabilities(self) -> list:
        return [
            "version",
            "init",
            "validate",
            "format",
            "plan",
            "apply",
            "destroy",
            "output",
            "show",
            "state_list",
            "workspace_list",
            "workspace_new",
            "workspace_select",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        """
        Ejecuta una acción de Terraform.

        Ejemplo:
            tf.execute("init", {"working_dir": "terraform/"})
            tf.execute("plan", {"working_dir": "terraform/", "var_file": "prod.tfvars"})
            tf.execute("apply", {"working_dir": "terraform/", "auto_approve": True})
        """
        if action not in self.get_capabilities():
            raise ValueError(
                f"Action '{action}' not supported. "
                f"Available: {self.get_capabilities()}"
            )

        actions = {
            "version":         self._version,
            "init":            self._init,
            "validate":        self._validate,
            "format":          self._format,
            "plan":            self._plan,
            "apply":           self._apply,
            "destroy":         self._destroy,
            "output":          self._output,
            "show":            self._show,
            "state_list":      self._state_list,
            "workspace_list":  self._workspace_list,
            "workspace_new":   self._workspace_new,
            "workspace_select": self._workspace_select,
        }

        return actions[action](params)

    # --- Implementaciones ---

    def _version(self, params: dict) -> dict:
        return self._run(["version", "-json"])

    def _init(self, params: dict) -> dict:
        """Inicializa un directorio de Terraform."""
        working_dir = params.get("working_dir", ".")
        args = ["init"]
        if params.get("upgrade"):
            args.append("-upgrade")
        if params.get("backend_config"):
            args += [f"-backend-config={params['backend_config']}"]
        result = self._run(args, working_dir)
        print(f"[TerraformTool] init in {working_dir}: {'OK' if result['success'] else 'FAILED'}")
        return result

    def _validate(self, params: dict) -> dict:
        """Valida la configuración de Terraform."""
        working_dir = params.get("working_dir", ".")
        result = self._run(["validate", "-json"], working_dir)
        print(f"[TerraformTool] validate: {'OK' if result['success'] else 'FAILED'}")
        return result

    def _format(self, params: dict) -> dict:
        """Formatea los archivos Terraform."""
        working_dir = params.get("working_dir", ".")
        check_only = params.get("check", False)
        args = ["fmt", "-recursive"]
        if check_only:
            args.append("-check")
        return self._run(args, working_dir)

    def _plan(self, params: dict) -> dict:
        """
        Genera un plan de Terraform.
        IMPORTANTE: nunca ejecuta cambios, solo planifica.
        """
        working_dir = params.get("working_dir", ".")
        args = ["plan", "-no-color"]
        if params.get("var_file"):
            args += [f"-var-file={params['var_file']}"]
        if params.get("out"):
            args += [f"-out={params['out']}"]
        for k, v in params.get("vars", {}).items():
            args += [f"-var={k}={v}"]
        result = self._run(args, working_dir)
        print(f"[TerraformTool] plan: {'OK' if result['success'] else 'FAILED'}")
        return result

    def _apply(self, params: dict) -> dict:
        """
        Aplica un plan de Terraform.
        Requiere auto_approve=True o un plan file explícito.
        Sin auto_approve ni plan_file — deniega por seguridad.
        """
        working_dir = params.get("working_dir", ".")
        auto_approve = params.get("auto_approve", False)
        plan_file = params.get("plan_file")

        if not auto_approve and not plan_file:
            return {
                "success": False,
                "stderr": "apply requires auto_approve=True or a plan_file. "
                          "This is a safety measure — never apply without a plan.",
                "stdout": "",
                "returncode": -1,
            }

        args = ["apply", "-no-color"]
        if auto_approve:
            args.append("-auto-approve")
        if plan_file:
            args.append(plan_file)
        if params.get("var_file"):
            args += [f"-var-file={params['var_file']}"]

        result = self._run(args, working_dir)
        print(f"[TerraformTool] apply: {'OK' if result['success'] else 'FAILED'}")
        return result

    def _destroy(self, params: dict) -> dict:
        """
        Destruye infraestructura Terraform.
        Requiere auto_approve=True explícito — medida de seguridad.
        """
        working_dir = params.get("working_dir", ".")
        auto_approve = params.get("auto_approve", False)

        if not auto_approve:
            return {
                "success": False,
                "stderr": "destroy requires auto_approve=True explicitly. "
                          "This is a safety measure.",
                "stdout": "",
                "returncode": -1,
            }

        args = ["destroy", "-auto-approve", "-no-color"]
        if params.get("var_file"):
            args += [f"-var-file={params['var_file']}"]

        result = self._run(args, working_dir)
        print(f"[TerraformTool] destroy: {'OK' if result['success'] else 'FAILED'}")
        return result

    def _output(self, params: dict) -> dict:
        """Retorna los outputs de Terraform en JSON."""
        working_dir = params.get("working_dir", ".")
        args = ["output", "-json"]
        if params.get("name"):
            args.append(params["name"])
        return self._run(args, working_dir)

    def _show(self, params: dict) -> dict:
        """Muestra el estado actual de Terraform."""
        working_dir = params.get("working_dir", ".")
        return self._run(["show", "-json"], working_dir)

    def _state_list(self, params: dict) -> dict:
        """Lista los recursos en el estado de Terraform."""
        working_dir = params.get("working_dir", ".")
        return self._run(["state", "list"], working_dir)

    def _workspace_list(self, params: dict) -> dict:
        """Lista los workspaces de Terraform."""
        working_dir = params.get("working_dir", ".")
        return self._run(["workspace", "list"], working_dir)

    def _workspace_new(self, params: dict) -> dict:
        """Crea un workspace nuevo."""
        working_dir = params.get("working_dir", ".")
        name = params.get("name")
        return self._run(["workspace", "new", name], working_dir)

    def _workspace_select(self, params: dict) -> dict:
        """Selecciona un workspace."""
        working_dir = params.get("working_dir", ".")
        name = params.get("name")
        return self._run(["workspace", "select", name], working_dir)