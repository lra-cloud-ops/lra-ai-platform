# tools/iac/ansible/ansible_tool.py
# Implementación de la Ansible Tool para LRA AI Platform.
# Ejecuta comandos ansible reales via WSL2 (subprocess).

import os
import subprocess
from core.interfaces.tool import Tool


class AnsibleTool(Tool):
    """
    Tool para ejecutar Ansible via WSL2 subprocess.

    Ansible no corre en Windows nativamente — se ejecuta
    via 'wsl ansible' y 'wsl ansible-playbook'.

    Uso:
        ansible = AnsibleTool()
        ansible.execute("run_adhoc", {
            "hosts": "all",
            "module": "ping",
            "inventory": "inventory/hosts"
        })
        ansible.execute("run_playbook", {
            "playbook": "playbooks/deploy.yml",
            "inventory": "inventory/hosts"
        })
    """

    def __init__(self):
        super().__init__(name="ansible", version="1.0.0")
        self._use_wsl = self._detect_wsl()

    def _detect_wsl(self) -> bool:
        """Detecta si ansible debe ejecutarse via WSL2."""
        import shutil
        if shutil.which("ansible"):
            return False  # Ansible disponible nativamente
        try:
            result = subprocess.run(
                ["wsl", "ansible", "--version"],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _build_cmd(self, base_cmd: list) -> list:
        """Construye el comando con o sin wsl prefix."""
        if self._use_wsl:
            return ["wsl"] + base_cmd
        return base_cmd

    def _to_wsl_path(self, path: str) -> str:
        """Convierte rutas Windows a rutas WSL2 si es necesario."""
        if self._use_wsl and path and ":" in path:
            # C:\Users\... -> /mnt/c/Users/...
            drive = path[0].lower()
            rest = path[2:].replace("\\", "/")
            return f"/mnt/{drive}{rest}"
        return path

    def _run(self, args: list, working_dir: str = ".") -> dict:
        """Ejecuta un comando ansible."""
        cmd = self._build_cmd(args)
        wsl_dir = self._to_wsl_path(str(working_dir))

        if self._use_wsl:
            cmd = ["wsl", "bash", "-c",
                   f"cd '{wsl_dir}' && " + " ".join(args)]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=None if self._use_wsl else working_dir
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
                "stderr": "ansible not found. Install ansible or enable WSL2.",
                "success": False,
            }

    def validate(self) -> bool:
        """Verifica que ansible está disponible."""
        cmd = self._build_cmd(["ansible", "--version"])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split("\n")[0]
                print(f"[AnsibleTool] Available via {'WSL2' if self._use_wsl else 'native'}: {version_line}")
                return True
        except Exception as e:
            print(f"[AnsibleTool] Validation failed: {e}")
        return False

    def get_capabilities(self) -> list:
        return [
            "run_adhoc",
            "run_playbook",
            "check_syntax",
            "list_hosts",
            "list_tasks",
            "ping_hosts",
            "gather_facts",
            "encrypt_vault",
            "decrypt_vault",
            "view_vault",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        """
        Ejecuta una acción de Ansible.

        Ejemplo:
            ansible.execute("ping_hosts", {"inventory": "inventory/hosts"})
            ansible.execute("run_playbook", {
                "playbook": "playbooks/deploy.yml",
                "inventory": "inventory/hosts",
                "extra_vars": {"env": "production"}
            })
        """
        if action not in self.get_capabilities():
            raise ValueError(
                f"Action '{action}' not supported. "
                f"Available: {self.get_capabilities()}"
            )

        actions = {
            "run_adhoc":    self._run_adhoc,
            "run_playbook": self._run_playbook,
            "check_syntax": self._check_syntax,
            "list_hosts":   self._list_hosts,
            "list_tasks":   self._list_tasks,
            "ping_hosts":   self._ping_hosts,
            "gather_facts": self._gather_facts,
            "encrypt_vault": self._encrypt_vault,
            "decrypt_vault": self._decrypt_vault,
            "view_vault":   self._view_vault,
        }

        return actions[action](params)

    # --- Implementaciones ---

    def _run_adhoc(self, params: dict) -> dict:
        """Ejecuta un comando ad-hoc de Ansible."""
        hosts     = params.get("hosts", "all")
        module    = params.get("module", "ping")
        args      = params.get("args", "")
        inventory = params.get("inventory", "localhost,")
        become    = params.get("become", False)

        cmd = ["ansible", hosts, "-m", module, "-i", inventory]
        if args:
            cmd += ["-a", args]
        if become:
            cmd.append("--become")

        result = self._run(cmd)
        print(f"[AnsibleTool] ad-hoc '{module}' on '{hosts}': "
              f"{'OK' if result['success'] else 'FAILED'}")
        return result

    def _run_playbook(self, params: dict) -> dict:
        """Ejecuta un playbook de Ansible."""
        playbook  = params.get("playbook")
        inventory = params.get("inventory", "localhost,")
        extra_vars = params.get("extra_vars", {})
        tags      = params.get("tags", "")
        check     = params.get("check", False)  # dry-run
        become    = params.get("become", False)
        limit     = params.get("limit", "")

        cmd = ["ansible-playbook", playbook, "-i", inventory]
        if extra_vars:
            import json
            cmd += ["-e", json.dumps(extra_vars)]
        if tags:
            cmd += ["--tags", tags]
        if check:
            cmd.append("--check")
        if become:
            cmd.append("--become")
        if limit:
            cmd += ["--limit", limit]

        result = self._run(cmd)
        print(f"[AnsibleTool] playbook '{playbook}': "
              f"{'OK' if result['success'] else 'FAILED'}")
        return result

    def _check_syntax(self, params: dict) -> dict:
        """Verifica la sintaxis de un playbook."""
        playbook  = params.get("playbook")
        inventory = params.get("inventory", "localhost,")
        return self._run(["ansible-playbook", playbook,
                          "-i", inventory, "--syntax-check"])

    def _list_hosts(self, params: dict) -> dict:
        """Lista los hosts del inventario."""
        inventory = params.get("inventory", "localhost,")
        hosts     = params.get("hosts", "all")
        return self._run(["ansible", hosts, "-i", inventory, "--list-hosts"])

    def _list_tasks(self, params: dict) -> dict:
        """Lista las tasks de un playbook."""
        playbook  = params.get("playbook")
        inventory = params.get("inventory", "localhost,")
        return self._run(["ansible-playbook", playbook,
                          "-i", inventory, "--list-tasks"])

    def _ping_hosts(self, params: dict) -> dict:
        """Hace ping a todos los hosts del inventario."""
        return self._run_adhoc({
            "hosts":     params.get("hosts", "all"),
            "module":    "ping",
            "inventory": params.get("inventory", "localhost,"),
        })

    def _gather_facts(self, params: dict) -> dict:
        """Recopila facts de los hosts."""
        return self._run_adhoc({
            "hosts":     params.get("hosts", "all"),
            "module":    "setup",
            "inventory": params.get("inventory", "localhost,"),
        })

    def _encrypt_vault(self, params: dict) -> dict:
        """Encripta un archivo con Ansible Vault."""
        file_path = params.get("file")
        return self._run(["ansible-vault", "encrypt", file_path])

    def _decrypt_vault(self, params: dict) -> dict:
        """Desencripta un archivo con Ansible Vault."""
        file_path = params.get("file")
        return self._run(["ansible-vault", "decrypt", file_path])

    def _view_vault(self, params: dict) -> dict:
        """Visualiza el contenido de un archivo Vault."""
        file_path = params.get("file")
        return self._run(["ansible-vault", "view", file_path])