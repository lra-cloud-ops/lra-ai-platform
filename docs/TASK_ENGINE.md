# TASK_ENGINE.md

## LRA AI Platform — Task Engine

**Versión:** 1.0
**Estado:** Congelado — este documento es el contrato de la plataforma
**Depende de:** ARCHITECTURE.md
**Consumido por:** GOVERNANCE.md, WORKFLOW_ENGINE.md, todos los Agents

---

## 1. Por qué Task es el objeto más importante del sistema

Todo lo que la plataforma hace —crear un repo, escanear seguridad, desplegar
una app, generar documentación— es una Task. Si la estructura de Task cambia
en el futuro, el impacto se propaga a Workflow Engine, Governance Engine,
Supervisor, todos los Agents, el Dashboard, la API, el CLI y el Audit Log.
Por eso este contrato se congela antes de implementar nada.

Ver ADR-001 para el razonamiento completo de por qué Task (y no Agent) es la
unidad central del sistema.

---

## 2. Anatomía de una Task

```
Task
  id              str    — identificador único (uuid)
  type            str    — qué hace, ej. "create_repository"
  params          dict   — parámetros de entrada
  status          enum   — ver §3 Ciclo de vida
  priority        enum   — low | normal | high | critical
  assigned_to     str    — nombre del Agent responsable
  capability      str    — qué Capability ejecuta esta Task
  depends_on      list   — ids de otras Tasks que deben completarse antes
  retry_policy    dict   — ver §6
  timeout_seconds int    — ver §7
  idempotency_key str    — ver §8
  created_at      str    — timestamp ISO
  updated_at      str    — timestamp ISO
  started_at      str    — timestamp ISO, None si no ha empezado
  completed_at    str    — timestamp ISO, None si no ha terminado
  result          dict   — salida de la ejecución
  error           dict   — detalle del fallo si status == failed
  governance      dict   — decisión de Governance (ver GOVERNANCE.md)
  audit_trail     list   — eventos emitidos por esta Task (ver §9)
```

### Ejemplo concreto

```json
{
  "id": "task-7f3a9c",
  "type": "create_repository",
  "params": {
    "name": "client-api",
    "org": "lra-cloud-ops",
    "private": false
  },
  "status": "pending",
  "priority": "normal",
  "assigned_to": "founder",
  "capability": "create_repository",
  "depends_on": [],
  "retry_policy": {"max_attempts": 2, "backoff_seconds": 5},
  "timeout_seconds": 60,
  "idempotency_key": "create_repository:lra-cloud-ops/client-api",
  "created_at": "2026-06-30T09:00:00",
  "updated_at": "2026-06-30T09:00:00",
  "started_at": null,
  "completed_at": null,
  "result": null,
  "error": null,
  "governance": {"requires_approval": false, "permission_level": 2},
  "audit_trail": []
}
```

---

## 3. Ciclo de vida (estados)

```
PENDING ──► APPROVED ──► RUNNING ──► COMPLETED
   │            │            │
   │            │            └──► FAILED ──► RETRYING ──► RUNNING
   │            │                     │
   │            ▼                     └──► CANCELLED (manual o tras agotar retries)
   │        REJECTED
   │
   └──► CANCELLED (el usuario cancela antes de aprobar)
```

| Estado | Significado |
|---|---|
| `PENDING` | Task creada, esperando paso por Governance |
| `APPROVED` | Governance autorizó la ejecución (automática o manual) |
| `REJECTED` | Governance bloqueó la Task — no se ejecuta |
| `RUNNING` | La Task está ejecutándose contra una Tool real |
| `COMPLETED` | Terminó exitosamente, `result` contiene la salida |
| `FAILED` | Terminó con error, `error` contiene el detalle |
| `RETRYING` | Falló pero el retry_policy permite reintentar |
| `CANCELLED` | Cancelada manualmente o tras agotar reintentos |

Solo `COMPLETED` y `FAILED`/`CANCELLED` son estados terminales. Toda
transición de estado emite un evento al Event Bus (ver §9).

---

## 4. Dependencias entre Tasks

Una Task puede declarar `depends_on: [task_id, ...]`. El Workflow Engine
nunca ejecuta una Task hasta que todas sus dependencias estén en `COMPLETED`.

```
Task: provision_eks
  depends_on: [provision_vpc]

Task: setup_cicd
  depends_on: [provision_eks, create_repository]
```

Si una dependencia termina en `FAILED` o `CANCELLED`, las Tasks que dependen
de ella pasan automáticamente a `CANCELLED` (no se ejecutan a ciegas).

---

## 5. Rollback

Cada Task que modifica estado externo debe poder declarar su operación
inversa. No es obligatorio para Tasks de solo lectura.

```
Task: create_repository
  rollback_type: "delete_repository"
  rollback_params: {"name": "client-api", "org": "lra-cloud-ops"}
```

Cuando un Execution Plan falla a mitad de camino, el Workflow Engine puede
ejecutar el rollback de todas las Tasks `COMPLETED` en orden inverso. El
rollback en sí también es una Task, y también pasa por Governance.

---

## 6. Reintentos (retry_policy)

```json
{"max_attempts": 3, "backoff_seconds": 5, "backoff_multiplier": 2}
```

Solo se reintentan fallos considerados transitorios (timeouts de red,
rate limits de API). Errores de validación o rechazos de Governance nunca
se reintentan automáticamente.

---

## 7. Timeouts

Toda Task tiene un `timeout_seconds`. Si se supera, la Task pasa a `FAILED`
con `error.reason = "timeout"`, independientemente de si la operación
subyacente seguía corriendo del lado del Provider. Esto evita que una Task
colgada bloquee el Workflow Engine indefinidamente.

---

## 8. Idempotencia

Cada Task tiene un `idempotency_key` derivado de su `type` + `params`
relevantes. Si se intenta ejecutar dos veces la misma Task con la misma
key (ej. por un reintento manual del usuario), el Task Engine detecta la
key repetida y devuelve el resultado ya conocido en vez de duplicar el
efecto (ej. no intenta crear el mismo repo dos veces).

---

## 9. Eventos emitidos

Cada cambio de estado de una Task publica un evento en el Event Bus
(`core/event_bus.py`, ya construido):

```
task.created
task.approved
task.rejected
task.started
task.completed
task.failed
task.retrying
task.cancelled
task.rollback_started
task.rollback_completed
```

Estos eventos son lo que alimenta el Audit Log de Governance y el Dashboard
en tiempo real — ningún componente necesita preguntar activamente por el
estado; se suscribe a estos eventos.

---

## 10. Relación entre Task, Capability y Tool

```
Task (type="create_repository")
   │
   ▼
Capability (create_repository)        ← pieza pequeña y reutilizable
   │
   ▼
Tool (GitHubTool → RepositoryService) ← ejecuta contra el Provider real
   │
   ▼
Provider (GitHub API)
```

Una Task siempre invoca exactamente una Capability principal (puede haber
Capabilities auxiliares para validación). La Capability decide qué Tool(s)
usar. La Task nunca llama a una Tool directamente.

---

## 11. Cómo cambia el FounderAgent con este contrato

Antes (v1.0): `FounderAgent.run("init project", {...})` decidía internamente
todos los pasos y los ejecutaba en secuencia.

Después (v2.0): el `FounderAgent` se convierte en un ejecutor de Tasks. El
Workflow Engine le asigna Tasks una a una (`create_repository`,
`generate_readme`, `generate_architecture_doc`...) y el Agent solo sabe
ejecutar la Capability que esa Task le pide, sin orquestar el resto del
flujo. La orquestación vive en el Workflow Engine, no en el Agent.

```python
# Antes
founder.run("init project", {"name": "client-api", ...})

# Después
task = Task(type="create_repository", params={"name": "client-api", ...})
founder.execute_task(task)   # el Agent solo ejecuta UNA Task
```

---

## 12. Lo que NO incluye este documento

- Cómo se decide si una Task requiere aprobación humana → `GOVERNANCE.md`
- Cómo se encadenan múltiples Tasks en un flujo con nombre reutilizable →
  `WORKFLOW_ENGINE.md`
- Cómo se persiste el contexto que una Task puede leer/escribir →
  `MEMORY.md`
