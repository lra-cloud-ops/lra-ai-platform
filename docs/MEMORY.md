# MEMORY.md

## LRA AI Platform — Memory

**Versión:** 1.0
**Estado:** Congelado — este documento es el contrato de la plataforma
**Depende de:** ARCHITECTURE.md, TASK_ENGINE.md
**Consumido por:** Agents, Task Planner, Supervisor

---

## 1. Por qué una sola Memory no era suficiente

La versión inicial (`core/memory_manager.py`, ya construida y probada en
este proyecto) implementa un único ámbito: memoria por proyecto. Funciona
bien para "¿qué stack usa `lracloudops`?", pero no distingue entre tipos
de contexto que tienen ciclos de vida y alcances muy distintos:

- Un estándar de naming de la organización no pertenece a un proyecto
  específico, y no debería tener que copiarse en cada uno.
- El estado de un Execution Plan en curso es efímero — no tiene sentido
  que viva mezclado con el contexto permanente del proyecto.
- Lo que el usuario dijo hace dos mensajes en esta conversación no debería
  persistir igual que el stack tecnológico de un proyecto.

Por eso Memory se divide en 4 tipos con alcance y tiempo de vida
diferenciados.

---

## 2. Los 4 tipos de Memory

```
Memory
   │
   ├── OrganizationMemory   → alcance: toda LRA CloudOps
   ├── ProjectMemory        → alcance: un proyecto específico
   ├── WorkflowMemory       → alcance: una ejecución de Workflow en curso
   └── ConversationMemory   → alcance: una sesión de conversación con el usuario
```

| Tipo | Alcance | Tiempo de vida | Ejemplo de contenido |
|---|---|---|---|
| **Organization** | Toda LRA CloudOps | Permanente | Naming conventions, políticas de seguridad por defecto, módulos de Terraform reutilizables, estándares de documentación |
| **Project** | Un proyecto (`lracloudops`, `client-api`...) | Permanente, por proyecto | Stack tecnológico, ADRs, último deploy, equipo asignado, recursos provisionados |
| **Workflow** | Una ejecución de Execution Plan | Vive mientras el plan está activo; se archiva al completarse | Estado intermedio de Tasks en curso, decisiones tomadas durante esta ejecución específica |
| **Conversation** | Una sesión de chat con el usuario | Vive mientras dura la conversación | Lo que el usuario pidió hace 2 mensajes, aclaraciones dadas, Intent original sin procesar |

---

## 3. Jerarquía de resolución

Cuando un Agent necesita contexto, consulta los 4 tipos en orden de
especificidad, de más general a más específico, y el valor más específico
gana si hay conflicto:

```
1. Organization Memory   (base: "así se hacen las cosas en LRA CloudOps")
2. Project Memory        (sobreescribe si el proyecto define algo distinto)
3. Workflow Memory       (sobreescribe si esta ejecución concreta lo requiere)
4. Conversation Memory   (lo más reciente que dijo el usuario, máxima prioridad)
```

### Ejemplo

```
Organization Memory:  naming_convention = "kebab-case"
Project Memory:       (sin override — usa el de la organización)
Workflow Memory:      region = "eu-west-1"  (decidido para esta ejecución)
Conversation Memory:  "en realidad usa eu-south-2"  (el usuario lo acaba de pedir)

Resultado efectivo para esta Task: region = "eu-south-2"
```

Esta jerarquía es la que permite que `OrganizationMemory` funcione como
default razonable sin obligar a cada proyecto a repetir la configuración,
mientras el usuario sigue pudiendo anular cualquier decisión en el momento.

---

## 4. OrganizationMemory

Compartida por todos los proyectos. No pertenece a ningún Agent ni
proyecto en particular — es el equivalente a un "estándar de empresa".

```python
org_memory.save("naming_convention", "kebab-case")
org_memory.save("default_region", "eu-west-1")
org_memory.save("required_tags", ["team", "environment", "cost-center"])
org_memory.save("terraform_modules", {
    "vpc": "github.com/lra-cloud-ops/terraform-vpc-module",
    "eks": "github.com/lra-cloud-ops/terraform-eks-module"
})
```

Cualquier proyecto nuevo creado por el Founder Agent hereda estos valores
por defecto salvo que algo más específico los anule (§3).

---

## 5. ProjectMemory

Es la que ya existe y funciona hoy (`core/memory_manager.py` /
`ProjectMemory`, probada con `lracloudops` durante la construcción de
esta plataforma). Se conserva sin cambios estructurales — solo pasa a
convivir con los otros 3 tipos en vez de ser el único.

```python
project_memory = memory_manager.get_memory("lracloudops")
project_memory.save("stack", ["Astro", "Tailwind", "Cloudflare"])
project_memory.save("last_deploy", "2026-06-29")
```

Persistencia: JSON en disco bajo `memory/<project>/context.json`, igual
que hoy.

---

## 6. WorkflowMemory

Vive durante la ejecución de un Execution Plan concreto y se archiva (no
se borra, pasa a solo lectura) cuando el plan llega a un estado terminal
(`COMPLETED`, `FAILED`, `ROLLED_BACK`, `CANCELLED` — ver
`EXECUTION_PLAN.md §3`).

```python
workflow_memory = memory_manager.get_workflow_memory("exec-2026-06-30-001")
workflow_memory.save("vpc_id", "vpc-0a1b2c3d")   # decidido por una Task,
                                                    # lo necesita la siguiente
```

Esto resuelve un problema concreto: una Task de `provision_eks` necesita
saber el `vpc_id` que generó la Task `provision_vpc` anterior en el mismo
plan, sin que ese dato tenga que escribirse permanentemente en
ProjectMemory si el plan todavía no se completó (podría fallar y hacer
rollback).

Al completarse el plan con éxito, los valores relevantes de
WorkflowMemory se promueven a ProjectMemory (ver §8).

---

## 7. ConversationMemory

El contexto de la sesión de chat actual con el usuario. No persiste más
allá de la conversación activa (a diferencia de los otros 3 tipos).

```python
conv_memory = memory_manager.get_conversation_memory(session_id)
conv_memory.save("last_intent", "Crea una plataforma SaaS en AWS")
conv_memory.save("clarifications", {"region": "eu-south-2"})
```

Esto es lo que permite que el Supervisor entienda referencias como
"hazlo también para el segundo" sin que el usuario tenga que repetir todo
el contexto en cada mensaje.

---

## 8. Promoción de datos entre tipos

El único flujo de promoción automática definido en esta versión es
**Workflow → Project**, al completarse un Execution Plan con éxito:

```
Execution Plan COMPLETED
   │
   ▼
Workflow Engine promueve los valores relevantes de
WorkflowMemory a ProjectMemory
   │
   ▼
ej. vpc_id, cluster_name, último deploy quedan
permanentemente en el contexto del proyecto
```

No hay promoción automática hacia OrganizationMemory — eso requeriría una
decisión humana explícita (ej. "este patrón de Terraform debería ser el
estándar de la organización"), fuera de alcance de esta versión.

---

## 9. Relación con Governance y Audit

Los cambios a `OrganizationMemory` (al ser compartidos por toda la
plataforma) requieren nivel RBAC 5 (Administrador, ver `GOVERNANCE.md
§3`) y quedan registrados en el AuditEngine como cualquier otra acción de
configuración global.

Los cambios a `ProjectMemory` y `WorkflowMemory` se consideran efectos
secundarios normales de la ejecución de Tasks y se auditan como parte del
`audit_trail` de la Task que los originó (`TASK_ENGINE.md §2`), sin
requerir aprobación adicional propia.

---

## 10. Lo que NO incluye este documento

- Dónde se persisten físicamente `WorkflowMemory` y `ConversationMemory`
  más allá del proceso actual (sobrevivir un reinicio en medio de un plan
  pausado) → relacionado con State Store, pospuesto en `ADR-003`
- Búsqueda semántica o indexada sobre el contenido de Memory (más allá de
  `list_keys()`/`load(key)` por clave exacta, ya soportado por la
  interfaz `Memory` existente) → si se necesita, se evalúa junto con
  `PLUGIN_SYSTEM.md` o como Future Work
