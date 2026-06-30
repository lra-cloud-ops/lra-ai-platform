# core/tool_manager.py
# Registro central de todas las tools de LRA AI Platform.
# Los agentes solicitan tools aquí — nunca las instancian directamente.

import importlib
from core.interfaces.tool import Tool
from core.config_manager import ConfigManager


class ToolManager:
    """
    Gestor central de tools de LRA AI Platform.

    Responsabilidades:
        1. Registrar todas las tools disponibles al arrancar
        2. Proporcionar tools a los agentes cuando las solicitan
        3. Verificar que una tool está activa y configurada
        4. Cargar dinámicamente la implementación de cada tool

    Uso:
        tool_manager = ToolManager(config)
        github = tool_manager.get_tool("github")
        github.execute("create_repo", {"name": "mi-repo"})
    """

    def __init__(self, config: ConfigManager):
        self.config = config
        self._registry: dict[str, Tool] = {}
        self._catalog: dict[str, dict] = {}
        self._load_catalog()

    def _load_catalog(self):
        """
        Carga el catálogo de tools desde tools.yaml.
        No instancia las tools — solo registra su configuración.
        Las tools se instancian solo cuando se solicitan (lazy loading).
        """
        self._catalog = self.config.get_active_tools()

    def get_tool(self, name: str) -> Tool:
        """
        Retorna una tool por nombre.
        Si ya fue instanciada antes la reutiliza (singleton por tool).
        Si no, la carga dinámicamente desde su módulo.

        Ejemplo:
            github = tool_manager.get_tool("github")
            aws    = tool_manager.get_tool("aws")
            k8s    = tool_manager.get_tool("kubernetes")
        """
        if name in self._registry:
            return self._registry[name]

        if name not in self._catalog:
            raise ValueError(
                f"Tool '{name}' not found or not active. "
                f"Available tools: {list(self._catalog.keys())}"
            )

        tool = self._load_tool(name)
        self._registry[name] = tool
        return tool

    def _load_tool(self, name: str) -> Tool:
        """
        Carga dinámicamente la implementación de una tool.

        Convierte el path del YAML en un módulo Python importable.

        Ejemplo:
            tools/vcs/github  →  tools.vcs.github.GitHubTool
            tools/cloud/aws   →  tools.cloud.aws.AWSTool
            tools/iac/terraform → tools.iac.terraform.TerraformTool
        """
        tool_config = self._catalog[name]
        module_path = tool_config["path"].replace("/", ".")
        class_name  = self._to_class_name(name)

        try:
            module = importlib.import_module(f"{module_path}.{name}_tool")
            tool_class = getattr(module, class_name)
            return tool_class()
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Could not load tool '{name}' from '{module_path}'. "
                f"Make sure '{name}_tool.py' exists and defines '{class_name}'. "
                f"Error: {e}"
            )

    # Overrides para siglas que no siguen PascalCase estándar
    # Ver PLUGIN_SYSTEM.md §7 — excepción conocida documentada
    _CLASS_NAME_OVERRIDES = {
        "github": "GitHubTool",
        "aws": "AWSTool",
        "gcp": "GCPTool",
    }

    def _to_class_name(self, name: str) -> str:
        """
        Convierte el nombre de una tool a nombre de clase Python.
        Usa overrides para siglas que no siguen PascalCase estándar.
        Ver PLUGIN_SYSTEM.md §7.

        Ejemplos:
            github              → GitHubTool  (override)
            aws                 → AWSTool     (override)
            kubernetes          → KubernetesTool
            ansible_automation_platform → AnsibleAutomationPlatformTool
        """
        if name in self._CLASS_NAME_OVERRIDES:
            return self._CLASS_NAME_OVERRIDES[name]
        return "".join(word.capitalize() for word in name.split("_")) + "Tool"

    def register_tool(self, name: str, tool: Tool) -> None:
        """
        Registra manualmente una tool en el manager.
        Útil para testing o para tools creadas dinámicamente.

        Ejemplo:
            mock_github = MockGitHubTool()
            tool_manager.register_tool("github", mock_github)
        """
        self._registry[name] = tool

    def list_available(self) -> list[str]:
        """
        Retorna los nombres de todas las tools activas disponibles.

        Ejemplo:
            tool_manager.list_available()
            → ["github", "aws", "kubernetes", "terraform", "ansible", ...]
        """
        return list(self._catalog.keys())

    def list_loaded(self) -> list[str]:
        """
        Retorna las tools que ya han sido instanciadas.
        Útil para el dashboard y para debugging.
        """
        return list(self._registry.keys())

    def is_available(self, name: str) -> bool:
        """
        Verifica si una tool está disponible sin instanciarla.
        Los agentes usan esto para verificar sus dependencias al arrancar.

        Ejemplo:
            if tool_manager.is_available("github"):
                agent.register_tool(tool_manager.get_tool("github"))
        """
        return name in self._catalog

    def summary(self) -> dict:
        """
        Retorna un resumen del estado del ToolManager.
        Útil para el dashboard.
        """
        return {
            "available_tools": len(self._catalog),
            "loaded_tools": len(self._registry),
            "tools": self.list_available(),
        }

    def __repr__(self):
        return (
            f"ToolManager("
            f"available={len(self._catalog)}, "
            f"loaded={len(self._registry)})"
        )