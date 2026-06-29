# core/config_manager.py
# Lee y gestiona la configuración global de LRA AI Platform.
# Es el primer componente que arranca — todos los demás dependen de él.

import os
import yaml
from pathlib import Path


class ConfigManager:
    """
    Gestor de configuración global de LRA AI Platform.

    Lee los archivos YAML de config/ y los pone disponibles
    para todos los componentes de la plataforma.

    Archivos que gestiona:
        config/config.yaml   → configuración general
        config/agents.yaml   → registro de agentes
        config/tools.yaml    → catálogo de tools
        .env                 → credenciales (nunca en Git)

    Uso:
        config = ConfigManager()
        platform_name = config.get("platform.name")
        agents = config.get_agents()
        tools = config.get_tools()
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config = {}
        self._agents = {}
        self._tools = {}
        self._load()

    def _load(self):
        """Carga todos los archivos de configuración al iniciar."""
        self._config = self._load_yaml("config.yaml")
        self._agents = self._load_yaml("agents.yaml")
        self._tools  = self._load_yaml("tools.yaml")

    def _load_yaml(self, filename: str) -> dict:
        """Lee un archivo YAML y retorna su contenido como diccionario."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        with open(filepath, "r") as f:
            return yaml.safe_load(f) or {}

    def get(self, key: str, default=None):
        """
        Retorna un valor de config.yaml usando notación de punto.

        Ejemplo:
            config.get("platform.name")     → "LRA AI Platform"
            config.get("api.port")          → 8000
            config.get("logging.level")     → "INFO"
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_agents(self) -> dict:
        """
        Retorna todos los agentes definidos en agents.yaml.

        Ejemplo:
            agents = config.get_agents()
            → {"founder": {...}, "devops": {...}, "security": {...}}
        """
        return self._agents.get("agents", {})

    def get_active_agents(self) -> dict:
        """Retorna solo los agentes con active: true."""
        return {
            name: agent
            for name, agent in self.get_agents().items()
            if agent.get("active", False)
        }

    def get_tools(self) -> dict:
        """
        Retorna todas las tools definidas en tools.yaml.

        Ejemplo:
            tools = config.get_tools()
            → {"github": {...}, "aws": {...}, "kubernetes": {...}}
        """
        return self._tools.get("tools", {})

    def get_active_tools(self) -> dict:
        """Retorna solo las tools con active: true."""
        return {
            name: tool
            for name, tool in self.get_tools().items()
            if tool.get("active", False)
        }

    def get_tool(self, name: str) -> dict:
        """
        Retorna la configuración de una tool específica.

        Ejemplo:
            github_config = config.get_tool("github")
            → {"name": "GitHub Tool", "category": "vcs", ...}
        """
        tools = self.get_tools()
        if name not in tools:
            raise ValueError(f"Tool '{name}' not found in tools.yaml")
        return tools[name]

    def get_agent(self, name: str) -> dict:
        """
        Retorna la configuración de un agente específico.

        Ejemplo:
            devops_config = config.get_agent("devops")
            → {"name": "DevOps Engineer", "role": "...", "tools": [...]}
        """
        agents = self.get_agents()
        if name not in agents:
            raise ValueError(f"Agent '{name}' not found in agents.yaml")
        return agents[name]

    def reload(self):
        """
        Recarga la configuración desde disco.
        Útil cuando se modifican los archivos YAML en caliente.
        """
        self._load()

    def summary(self) -> dict:
        """
        Retorna un resumen del estado de la configuración.
        Útil para el dashboard y para debugging.
        """
        return {
            "platform": self.get("platform.name"),
            "version": self.get("platform.version"),
            "environment": self.get("platform.environment"),
            "total_agents": len(self.get_agents()),
            "active_agents": len(self.get_active_agents()),
            "total_tools": len(self.get_tools()),
            "active_tools": len(self.get_active_tools()),
        }

    def __repr__(self):
        return f"ConfigManager(config_dir={self.config_dir})"