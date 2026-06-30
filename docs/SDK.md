# SDK.md

## LRA AI Platform — SDK

**Versión:** 1.0
**Estado:** Congelado — este documento es el contrato de la plataforma
**Depende de:** ARCHITECTURE.md, TASK_ENGINE.md, EXECUTION_PLAN.md,
GOVERNANCE.md, WORKFLOW_ENGINE.md, MEMORY.md, PLUGIN_SYSTEM.md
**Consumido por:** futuros colaboradores, CLI, API REST, Dashboard

---

## 1. Para quién es este documento

Hasta ahora cada documento definió una pieza interna de la plataforma.
Este es distinto: es la cara visible para alguien que **no** va a tocar
`core/`, solo quiere construir sobre la plataforma — añadir un Agent,
invocar un Execution Plan desde un script, o integrar LRA AI Platform en
otra herramienta. Ese "alguien" puede perfectamente ser Ruben dentro de 6
meses, sin memoria fresca de las decisiones tomadas hoy — por eso este
documento prioriza ejemplos ejecutables sobre prosa.

---

## 2. Las dos formas de usar la plataforma

```
1. Como consumidor          → usas el Supervisor, le das un Intent,
                                recibes un Execution Plan, lo apruebas
                                o no, ves el resultado.

2. Como extensor (plugin)   → escribes un Agent/Tool/Capability nuevo
                                siguiendo PLUGIN_SYSTEM.md, y la
                                plataforma lo descubre sola.
```

Este documento cubre ambas, en ese orden.

---

## 3. Uso como consumidor — flujo mínimo

```python
from dotenv import load_dotenv
load_dotenv()

from core.config_manager import ConfigManager
from core.tool_manager import ToolManager
from core.agent_manager import AgentManager
from core.supervisor import Supervisor          # pendiente de implementar

config = ConfigManager()
tools  = ToolManager(config)
agents = AgentManager(config, tools)

supervisor = Supervisor(config, tools, agents)

# 1. Expresar un Intent
plan = supervisor.plan("Crea un proyecto nuevo llamado client-api con stack FastAPI + EKS")

# 2. Revisar el Execution Plan antes de ejecutar (EXECUTION_PLAN.md)
print(plan.summary())
#  Plan exec-2026-06-30-002
#  Tasks: create_repository, generate_documentation, provision_vpc, provision_eks
#  Requires approval: True (nivel 4 — producción incluida)

# 3. Aprobar (o rechazar) — esto pasa por Governance (GOVERNANCE.md §5)
supervisor.approve(plan.id, approved_by="ruben.liquenson")

# 4. Ejecutar — esto lo dispara el Workflow Engine (WORKFLOW_ENGINE.md)
result = supervisor.execute(plan.id)
print(result.status)   # "completed"
```

Nota: `core/supervisor.py` está documentado en `ROADMAP.md §Fase 1` como
pendiente de implementación. Este ejemplo define el contrato que debe
cumplir cuando se construya — sirve como especificación ejecutable.

---

## 4. Uso directo de un Agent (sin pasar por el Supervisor)

Útil para testing o scripts puntuales — exactamente como ya se hizo al
probar `FounderAgent` durante la construcción de esta plataforma:

```python
from agents.founder_agent import FounderAgent
from tools.vcs.github.github_tool import GitHubTool

founder = FounderAgent(
    name="Founder Agent",
    role="Project Initializer",
    description="Initializes new projects for LRA CloudOps"
)
founder.register_tool(GitHubTool())

# v1.0 (orquesta su propio flujo — comportamiento actual)
result = founder.run("init project", {"name": "test-project", "org": "lra-cloud-ops"})

# v2.0, post-refactor (ejecuta una Task individual — TASK_ENGINE.md §11)
from core.interfaces.task import Task
task = Task(type="create_repository", params={"name": "test-project", "org": "lra-cloud-ops"})
result = founder.execute_task(task)
```

Importante: este camino **se salta Governance**. Es válido para
desarrollo y pruebas locales, nunca para flujos contra producción — ese
es exactamente el motivo por el que existe el Supervisor como camino
recomendado en producción (§3).

---

## 5. Construir un Agent nuevo — receta completa

Combina lo ya definido en `PLUGIN_SYSTEM.md §4` en una receta ejecutable
de principio a fin.

```python
# agents/azure_specialist_agent.py

from core.interfaces.agent import Agent

class AzureSpecialistAgent(Agent):
    def execute_task(self, task) -> dict:
        capability_name = task.capability
        capability = self._resolve_capability(capability_name)
        tool = self.get_tool("azure")
        return capability.execute(task.params, {"azure": tool})

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tools": list(self.tools.keys()),
        }

    def _resolve_capability(self, name: str):
        # resolución de capability — detalle de implementación del Agent
        ...
```

```yaml
# config/agents.yaml — añadir entrada
azure_specialist:
  name: "Azure Specialist"
  role: "Azure Cloud Engineer"
  description: "Maneja recursos en Azure: AKS, VNet, Storage, Key Vault"
  active: true
  tools:
    - azure
```

```bash
# Verificación — el mismo patrón de prueba usado en cada componente
# construido hasta ahora en este proyecto
python -c "
from core.config_manager import ConfigManager
from core.tool_manager import ToolManager
from core.agent_manager import AgentManager

config = ConfigManager()
tools  = ToolManager(config)
agents = AgentManager(config, tools)

print(agents.is_available('azure_specialist'))
"
```

No se requiere ningún cambio en `core/agent_manager.py`, `core/supervisor.py`
ni en ningún otro Agent existente — exactamente la garantía que
`PLUGIN_SYSTEM.md §4` formaliza.

---

## 6. Garantías de estabilidad por componente

Para que alguien que construye sobre la plataforma sepa qué puede asumir
estable y qué puede cambiar:

| Componente | Estabilidad | Notas |
|---|---|---|
| `core/interfaces/*.py` | Alta — contrato congelado | Cambios requieren ADR y versionado (`TASK_ENGINE.md`, nota de versionado) |
| `ToolManager`, `AgentManager`, `ConfigManager`, `EventBus` | Alta — ya implementados y probados | API pública estable; internals pueden refactorizarse |
| `Task`, `ExecutionPlan` (estructura de datos) | Alta — documentos congelados | Cualquier campo nuevo se añade de forma retrocompatible |
| Estructura de `tools.yaml` / `agents.yaml` | Alta | Añadir campos opcionales es seguro; renombrar campos existentes no |
| Implementación interna de un Agent/Tool concreto | Baja — libre de cambiar | Mientras cumpla la interfaz, el contenido interno es responsabilidad del autor del plugin |
| `GovernanceEngine`, `WorkflowEngine` (implementación) | Media — recién diseñados, no implementados aún | Estable una vez implementados y probados con el segundo Agent real |

---

## 7. Errores comunes a evitar (ya identificados en este proyecto)

- **No saltarse Governance en flujos contra producción.** El atajo de §4
  es válido solo para desarrollo local.
- **No declarar tools fijas dentro del código de un Agent.** Las tools se
  declaran en `agents.yaml`, nunca hardcodeadas en el `__init__` del
  Agent (`ARCHITECTURE.md §3.7`).
- **No asumir que `__pycache__`, `.env` o `memory/*/` deben subirse a
  Git** — ya cubierto por `.gitignore`, pero es un error real que ya
  ocurrió durante la construcción de este proyecto.
- **No mezclar CRLF/LF sin preocupación** — los warnings de Git en
  Windows son inofensivos pero indican que el repo no tiene `.gitattributes`
  configurado; aceptable por ahora, revisar si causa fricción real en
  colaboración futura.

---

## 8. Lo que NO incluye este documento

- Empaquetado para distribución externa (publicar en PyPI, instalación
  vía `pip install lra-ai-platform-sdk`) → Future Work, no hay necesidad
  real todavía con un solo desarrollador activo
- Documentación de la API REST (`api/`) — se escribirá cuando esa fase se
  implemente (`ROADMAP.md §Fase 4`)
- Versionado semántico formal de releases de la plataforma → se adopta
  cuando exista el primer consumidor externo real
