# core/agent_manager.py
# Registro central de todos los agentes de LRA AI Platform.
# Coordina qué agentes están activos y qué tools tienen asignadas.

import importlib
from core.interfaces.agent import Agent
from core.config_manager import ConfigManager
from core.tool_manager import ToolManager


class AgentManager:
    """
    Gestor central de agentes de LRA AI Platform.

    Responsabilidades:
        1. Registrar todos los agentes activos al arrancar
        2. Asignar las tools correctas a cada agente
        3. Proporcionar agentes al Supervisor cuando los solicita
        4. Reportar el estado de todos los agentes al dashboard
    """

    # Overrides para nombres que no siguen PascalCase estándar
    _CLASS_NAME_OVERRIDES = {
        "devops":    "DevOpsAgent",
        "sre":       "SREAgent",
        "openshift": "OpenShiftAgent",
    }

    def __init__(self, config: ConfigManager, tool_manager: ToolManager):
        self.config = config
        self.tool_manager = tool_manager
        self._registry: dict[str, Agent] = {}
        self._catalog: dict[str, dict] = {}
        self._load_catalog()

    def _load_catalog(self):
        self._catalog = self.config.get_active_agents()

    def get_agent(self, name: str) -> Agent:
        if name in self._registry:
            return self._registry[name]

        if name not in self._catalog:
            raise ValueError(
                f"Agent '{name}' not found or not active. "
                f"Available agents: {list(self._catalog.keys())}"
            )

        agent = self._load_agent(name)
        self._assign_tools(agent, name)
        self._registry[name] = agent
        return agent

    def _load_agent(self, name: str) -> Agent:
        class_name = self._to_class_name(name)
        try:
            module = importlib.import_module(f"agents.{name}_agent")
            agent_class = getattr(module, class_name)
            agent_config = self._catalog[name]
            return agent_class(
                name=agent_config["name"],
                role=agent_config["role"],
                description=agent_config["description"],
            )
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Could not load agent '{name}' from 'agents/{name}_agent.py'. "
                f"Make sure the file exists and defines '{class_name}'. "
                f"Error: {e}"
            )

    def _assign_tools(self, agent: Agent, name: str) -> None:
        agent_config = self._catalog[name]
        required_tools = agent_config.get("tools", [])

        for tool_name in required_tools:
            if self.tool_manager.is_available(tool_name):
                tool = self.tool_manager.get_tool(tool_name)
                agent.register_tool(tool)
            else:
                print(
                    f"[WARNING] Tool '{tool_name}' required by agent "
                    f"'{name}' is not available or inactive."
                )

    def _to_class_name(self, name: str) -> str:
        if name in self._CLASS_NAME_OVERRIDES:
            return self._CLASS_NAME_OVERRIDES[name]
        return "".join(word.capitalize() for word in name.split("_")) + "Agent"

    def register_agent(self, name: str, agent: Agent) -> None:
        self._registry[name] = agent

    def list_available(self) -> list[str]:
        return list(self._catalog.keys())

    def list_loaded(self) -> list[str]:
        return list(self._registry.keys())

    def is_available(self, name: str) -> bool:
        return name in self._catalog

    def summary(self) -> dict:
        return {
            "available_agents": len(self._catalog),
            "loaded_agents": len(self._registry),
            "agents": {
                name: {
                    "role": config["role"],
                    "tools": config.get("tools", []),
                    "loaded": name in self._registry,
                }
                for name, config in self._catalog.items()
            },
        }

    def __repr__(self):
        return (
            f"AgentManager("
            f"available={len(self._catalog)}, "
            f"loaded={len(self._registry)})"
        )