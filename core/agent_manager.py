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

    Relación con otros componentes:
        AgentManager usa ConfigManager → sabe qué agentes existen
        AgentManager usa ToolManager   → asigna tools a cada agente

    Uso:
        agent_manager = AgentManager(config, tool_manager)
        devops = agent_manager.get_agent("devops")
        devops.run("deploy application", {"repo": "lracloudops"})
    """

    def __init__(self, config: ConfigManager, tool_manager: ToolManager):
        self.config = config
        self.tool_manager = tool_manager
        self._registry: dict[str, Agent] = {}
        self._catalog: dict[str, dict] = {}
        self._load_catalog()

    def _load_catalog(self):
        """
        Carga el catálogo de agentes desde agents.yaml.
        No instancia los agentes — solo registra su configuración.
        """
        self._catalog = self.config.get_active_agents()

    def get_agent(self, name: str) -> Agent:
        """
        Retorna un agente por nombre.
        Si ya fue instanciado antes lo reutiliza.
        Si no, lo carga dinámicamente y le asigna sus tools.

        Ejemplo:
            devops   = agent_manager.get_agent("devops")
            security = agent_manager.get_agent("security")
            founder  = agent_manager.get_agent("founder")
        """
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
        """
        Carga dinámicamente la implementación de un agente.

        Ejemplo:
            agents/devops_agent.py   → DevOpsAgent
            agents/security_agent.py → SecurityAgent
            agents/founder_agent.py  → FounderAgent
        """
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
        """
        Asigna las tools configuradas en agents.yaml al agente.
        Solo asigna tools que estén activas en el ToolManager.

        Ejemplo agents.yaml:
            devops:
              tools:
                - github
                - kubernetes
                - helm

        El agente recibirá GitHubTool, KubernetesTool y HelmTool.
        Tools inactivas o no disponibles se omiten con un warning.
        """
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
        """
        Convierte el nombre de un agente a nombre de clase Python.

        Ejemplos:
            devops          → DevOpsAgent
            cloud_architect → CloudArchitectAgent
            founder         → FounderAgent
        """
        return "".join(word.capitalize() for word in name.split("_")) + "Agent"

    def register_agent(self, name: str, agent: Agent) -> None:
        """
        Registra manualmente un agente en el manager.
        Útil para testing o para agentes creados dinámicamente.
        """
        self._registry[name] = agent

    def list_available(self) -> list[str]:
        """Retorna los nombres de todos los agentes activos."""
        return list(self._catalog.keys())

    def list_loaded(self) -> list[str]:
        """Retorna los agentes que ya han sido instanciados."""
        return list(self._registry.keys())

    def is_available(self, name: str) -> bool:
        """Verifica si un agente está disponible sin instanciarlo."""
        return name in self._catalog

    def summary(self) -> dict:
        """
        Retorna un resumen del estado del AgentManager.
        Útil para el dashboard y el Supervisor.
        """
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