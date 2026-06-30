# PLUGIN_SYSTEM.md

## LRA AI Platform — Plugin System

**Versión:** 1.0
**Estado:** Congelado — este documento es el contrato de la plataforma
**Depende de:** ARCHITECTURE.md, TASK_ENGINE.md
**Consumido por:** ToolManager, AgentManager (ya construidos), SDK.md

---

## 1. Por qué este documento existe

`core/tool_manager.py` y `core/agent_manager.py` (ya implementados y
probados en este proyecto) ya hacen carga dinámica y lazy loading de
Tools y Agents a partir de `tools.yaml` y `agents.yaml`. Este documento no
reemplaza eso — lo formaliza como un contrato explícito de "qué necesita
cumplir un plugin nuevo para que la plataforma lo reconozca", de forma
que añadir el agente número 9 o la tool número 25 sea un procedimiento
mecánico y no una excavación arqueológica del código existente.

> Referencia directa a la decisión original que motivó este sistema: "hoy
> tienes DevOps Agent, mañana aparece Azure Specialist. No cambias el
> Supervisor. Solo registras un nuevo agente."

---

## 2. Qué es un plugin en esta plataforma

Tres tipos de plugin, cada uno con su propio contrato ya definido en
`core/interfaces/`:

```
Plugin
   │
   ├── Tool         → implementa core/interfaces/tool.py
   ├── Agent        → implementa core/interfaces/agent.py
   └── Capability   → implementa core/interfaces/capability.py
```

Un plugin nunca modifica código del core. Solo añade: un archivo Python
nuevo bajo la carpeta correspondiente, y una entrada en el YAML de
configuración correspondiente.

---

## 3. Registrar una Tool nueva

Procedimiento mecánico, ya validado con `GitHubTool` (Hito de
implementación anterior, `tools/vcs/github/github_tool.py`):

```
1. Elegir categoría y crear carpeta:
   tools/<categoria>/<nombre>/<nombre>_tool.py

2. La clase debe:
   - heredar de core.interfaces.tool.Tool
   - implementar execute(), validate(), get_capabilities()
   - nombrarse <Nombre>Tool (PascalCase), según la convención que ya
     usa ToolManager._to_class_name()

3. Añadir entrada en config/tools.yaml:
   nueva_tool:
     name: "Nueva Tool"
     category: "<categoria>"
     path: "tools/<categoria>/<nombre>"
     active: true
     actions: [...]

4. No se toca core/tool_manager.py. El lazy loading ya construido
   la descubre automáticamente la primera vez que un Agent la solicita.
```

### Ejemplo: registrar Azure Tool

```
tools/cloud/azure/azure_tool.py   → class AzureTool(Tool)

config/tools.yaml:
  azure:
    name: "Azure Tool"
    category: "cloud"
    path: "tools/cloud/azure"
    active: true   # cambia de false a true cuando esté implementada
    actions: [create_aks_cluster, create_vnet, ...]
```

No requiere ningún cambio en `ToolManager`, `AgentManager` ni en ningún
Agent existente.

---

## 4. Registrar un Agent nuevo

Mismo principio, validado con `FounderAgent`:

```
1. Crear archivo: agents/<nombre>_agent.py

2. La clase debe:
   - heredar de core.interfaces.agent.Agent
   - implementar run() (en v1.0) — en la versión Task-céntrica (v2.0),
     implementar execute_task(task) según TASK_ENGINE.md §11
   - implementar get_status()
   - nombrarse <Nombre>Agent (PascalCase)

3. Añadir entrada en config/agents.yaml:
   nuevo_agent:
     name: "Nuevo Agent"
     role: "..."
     description: "..."
     active: true
     tools: [lista de tool names que necesita]

4. No se toca core/agent_manager.py. AgentManager._assign_tools()
   ya asigna automáticamente las tools listadas, omitiendo con
   warning las que no estén activas (comportamiento ya probado).
```

### Importante: un Agent no declara tools "fijas" en su código

Tal como establece `ARCHITECTURE.md §3.7`, las tools de un Agent se
declaran en `agents.yaml`, no en el código Python del Agent. Esto es lo
que permite que el mismo `CloudArchitectAgent` use AWS hoy y Azure mañana
sin tocar su clase — solo cambia la lista `tools:` en el YAML.

---

## 5. Registrar una Capability nueva

Las Capabilities son las piezas más pequeñas y reutilizables (ej.
`create_repository`, `provision_vpc` — ver `ARCHITECTURE.md §3.4`).

```
1. Crear archivo: capabilities/<nombre>_capability.py

2. La clase debe:
   - heredar de core.interfaces.capability.Capability
   - implementar execute(params, tools), validate_params(params)
   - declarar required_tools en el constructor

3. No requiere entrada en YAML propia — las Capabilities se referencian
   directamente desde el campo Task.capability (TASK_ENGINE.md §2),
   resuelto en tiempo de ejecución por el Agent que recibe la Task.
```

### Ejemplo

```python
class CreateRepositoryCapability(Capability):
    def __init__(self):
        super().__init__(
            name="create_repository",
            description="Crea un repositorio en GitHub",
            required_tools=["github"]
        )

    def validate_params(self, params: dict) -> bool:
        return "name" in params and "org" in params

    def execute(self, params: dict, tools: dict) -> dict:
        github = tools["github"]
        return github.execute("create_repo", params)
```

---

## 6. Descubrimiento: qué pasa si falta algo

Comportamiento ya implementado y probado en `AgentManager._assign_tools()`:
si un Agent declara una tool que no existe o está `active: false`, se
omite con un `[WARNING]` y el Agent se carga igualmente con las tools
disponibles. Esto se mantiene como comportamiento estándar para todo el
sistema de plugins: **un plugin faltante o inactivo nunca rompe el
arranque de la plataforma**, solo reduce capacidades de forma visible.

```python
[WARNING] Tool 'azure' required by agent 'cloud_architect' is not
available or inactive.
```

---

## 7. Convención de nombres (formalizada)

Ya implementada de forma consistente en `tool_manager.py` y
`agent_manager.py` vía `_to_class_name()`. Se documenta aquí como
contrato explícito para quien añada plugins nuevos:

```
nombre_en_snake_case  →  NombreEnPascalCaseTool / Agent

github                → GitHubTool        (caso especial: sigla)
aws                   → AwsTool
ansible_automation_platform → AnsibleAutomationPlatformTool
cloud_architect       → CloudArchitectAgent
```

Nota: `GitHubTool` rompe la conversión mecánica estricta (`Github` vs
`GitHub`) — esto ya ocurrió en la implementación real y se documenta como
excepción conocida, no como bug. El algoritmo de conversión debe permitir
overrides explícitos de nombre de clase cuando la sigla lo requiera.

---

## 8. Qué NO permite el Plugin System (límites deliberados)

- Un plugin no puede registrarse y activarse automáticamente sin pasar
  por el archivo YAML correspondiente — esto es intencional: la entrada
  en `tools.yaml`/`agents.yaml` es también el punto donde Governance
  puede más adelante exigir revisión antes de activar un plugin nuevo en
  producción (relación con RBAC nivel 5, `GOVERNANCE.md §3`).
- Un plugin no puede sobreescribir una interfaz del core
  (`core/interfaces/`). Si un plugin necesita capacidades que la interfaz
  actual no contempla, eso es señal de que la interfaz necesita
  evolucionar (ver versionado de contratos, nota en `TASK_ENGINE.md`), no
  de que el plugin deba saltársela.

---

## 9. Lo que NO incluye este documento

- Cómo se empaqueta y distribuye un plugin para uso fuera de este
  repositorio (instalación vía pip, marketplace de plugins) → `SDK.md`
- Versionado de plugins (qué pasa si dos plugins requieren versiones
  distintas de una misma interfaz) → Future Work si surge la necesidad
  real, ver criterio de `ADR-003`
