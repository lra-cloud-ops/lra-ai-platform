# tools/local/local_tool.py
# Local Tool para LRA AI Platform.
# Lee y analiza proyectos en el sistema de archivos local.

import os
import json
from pathlib import Path
from core.interfaces.tool import Tool


class LocalTool(Tool):
    """
    Tool para leer y analizar proyectos locales.

    Permite que los agentes trabajen con proyectos en el
    sistema de archivos local sin necesidad de GitHub.

    Uso:
        local = LocalTool()
        local.execute("analyze_project", {"path": "C:/proyectos/mi-app"})
        local.execute("read_file", {"path": "C:/proyectos/mi-app/README.md"})
        local.execute("list_files", {"path": "C:/proyectos/mi-app"})
    """

    def __init__(self):
        super().__init__(name="local", version="1.0.0")

    def validate(self) -> bool:
        print("[LocalTool] Local filesystem available")
        return True

    def get_capabilities(self) -> list:
        return [
            "analyze_project",
            "read_file",
            "list_files",
            "detect_stack",
            "get_project_info",
            "save_file",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(f"Action '{action}' not supported.")

        actions = {
            "analyze_project":  self._analyze_project,
            "read_file":        self._read_file,
            "list_files":       self._list_files,
            "detect_stack":     self._detect_stack,
            "get_project_info": self._get_project_info,
            "save_file":        self._save_file,
        }
        return actions[action](params)

    # --- Implementaciones ---

    def _analyze_project(self, params: dict) -> dict:
        """
        Analiza un proyecto local completo.
        Detecta stack, lee README existente, lista estructura.
        """
        path = Path(params.get("path", ".")).resolve()
        if not path.exists():
            return {"error": f"Path not found: {path}"}

        print(f"[LocalTool] Analyzing project at {path}...")

        info      = self._get_project_info({"path": str(path)})
        stack     = self._detect_stack({"path": str(path)})
        structure = self._list_files({"path": str(path), "depth": 2})

        # Leer README existente si hay uno
        existing_readme = ""
        for readme_name in ["README.md", "readme.md", "Readme.md"]:
            readme_path = path / readme_name
            if readme_path.exists():
                existing_readme = readme_path.read_text(encoding="utf-8", errors="ignore")
                break

        return {
            "path": str(path),
            "name": path.name,
            "info": info,
            "stack": stack,
            "structure": structure,
            "existing_readme": existing_readme[:2000] if existing_readme else "",
            "has_readme": bool(existing_readme),
        }

    def _get_project_info(self, params: dict) -> dict:
        """Obtiene información básica del proyecto."""
        path = Path(params.get("path", ".")).resolve()

        # Detectar nombre y descripción
        name = path.name

        # Leer descripción de package.json, pyproject.toml, etc.
        description = ""
        for config_file in ["package.json", "pyproject.toml", "setup.py", "Cargo.toml"]:
            config_path = path / config_file
            if config_path.exists():
                content = config_path.read_text(encoding="utf-8", errors="ignore")
                if config_file == "package.json":
                    try:
                        data = json.loads(content)
                        description = data.get("description", "")
                        name = data.get("name", name)
                    except Exception:
                        pass
                break

        # Contar archivos por extensión
        file_counts = {}
        try:
            for f in path.rglob("*"):
                if f.is_file() and not any(
                    part.startswith(".") or part in ["node_modules", "__pycache__", ".git"]
                    for part in f.parts
                ):
                    ext = f.suffix.lower() or "no_ext"
                    file_counts[ext] = file_counts.get(ext, 0) + 1
        except Exception:
            pass

        return {
            "name": name,
            "description": description,
            "path": str(path),
            "file_counts": dict(sorted(
                file_counts.items(), key=lambda x: -x[1]
            )[:10]),
            "total_files": sum(file_counts.values()),
        }

    def _detect_stack(self, params: dict) -> dict:
        """
        Detecta el stack tecnológico del proyecto
        basándose en archivos de configuración.
        """
        path = Path(params.get("path", ".")).resolve()

        indicators = {
            # Lenguajes
            "Python":      ["requirements.txt", "setup.py", "pyproject.toml", "*.py"],
            "JavaScript":  ["package.json", "*.js", "*.jsx"],
            "TypeScript":  ["tsconfig.json", "*.ts", "*.tsx"],
            "Go":          ["go.mod", "go.sum", "*.go"],
            "Java":        ["pom.xml", "build.gradle", "*.java"],
            "Rust":        ["Cargo.toml", "*.rs"],
            # Frameworks
            "FastAPI":     ["requirements.txt"],
            "React":       ["package.json"],
            "Django":      ["manage.py"],
            "Spring":      ["pom.xml"],
            # Infrastructure
            "Terraform":   ["*.tf", "*.tfvars"],
            "Kubernetes":  ["*.yaml", "*.yml"],
            "Docker":      ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
            "Ansible":     ["playbook.yml", "inventory", "*.yml"],
            "Helm":        ["Chart.yaml", "values.yaml"],
            # CI/CD
            "GitHub Actions": [".github/workflows"],
            "Jenkins":     ["Jenkinsfile"],
            "ArgoCD":      ["argocd-app.yaml"],
        }

        detected = []
        for tech, patterns in indicators.items():
            for pattern in patterns:
                if "*" in pattern:
                    ext = pattern.replace("*", "")
                    matches = list(path.rglob(f"*{ext}"))
                    if matches and not any(
                        "node_modules" in str(m) or "__pycache__" in str(m)
                        for m in matches
                    ):
                        detected.append(tech)
                        break
                else:
                    if (path / pattern).exists():
                        detected.append(tech)
                        break

        return {
            "technologies": list(dict.fromkeys(detected)),  # deduplicate
            "total": len(detected),
        }

    def _list_files(self, params: dict) -> dict:
        """Lista la estructura de archivos del proyecto."""
        path  = Path(params.get("path", ".")).resolve()
        depth = params.get("depth", 2)

        IGNORE = {
            "node_modules", "__pycache__", ".git", ".venv", "venv",
            ".env", "dist", "build", ".next", ".nuxt", "target",
            ".terraform", ".pytest_cache",
        }

        def tree(p: Path, current_depth: int) -> list:
            if current_depth > depth:
                return []
            items = []
            try:
                for child in sorted(p.iterdir()):
                    if child.name in IGNORE or child.name.startswith("."):
                        continue
                    indent = "  " * (current_depth - 1)
                    if child.is_dir():
                        items.append(f"{indent}{child.name}/")
                        items.extend(tree(child, current_depth + 1))
                    else:
                        items.append(f"{indent}{child.name}")
            except PermissionError:
                pass
            return items

        structure = tree(path, 1)
        return {
            "path": str(path),
            "structure": structure[:50],  # máx 50 líneas
            "total_shown": len(structure),
        }

    def _read_file(self, params: dict) -> dict:
        """Lee el contenido de un archivo."""
        file_path = Path(params.get("path", ""))
        max_chars = params.get("max_chars", 5000)

        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return {
                "path": str(file_path),
                "content": content[:max_chars],
                "total_chars": len(content),
                "truncated": len(content) > max_chars,
            }
        except Exception as e:
            return {"error": str(e)}

    def _save_file(self, params: dict) -> dict:
        """Guarda un archivo en el sistema local."""
        file_path = Path(params.get("path", ""))
        content   = params.get("content", "")

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            print(f"[LocalTool] Saved: {file_path}")
            return {"path": str(file_path), "saved": True}
        except Exception as e:
            return {"error": str(e), "saved": False}