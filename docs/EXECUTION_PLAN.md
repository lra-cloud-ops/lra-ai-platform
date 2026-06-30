# EXECUTION_PLAN.md

## LRA AI Platform — Execution Plan

**Versión:** 1.0
**Estado:** Congelado — este documento es el contrato de la plataforma
**Depende de:** ARCHITECTURE.md, TASK_ENGINE.md
**Consumido por:** GOVERNANCE.md, WORKFLOW_ENGINE.md, Supervisor

---

## 1. Por qué Execution Plan necesita su propio contrato

`ARCHITECTURE.md` introdujo el Execution Plan como concepto (§3.2) pero solo
con un ejemplo ilustrativo, sin ciclo de vida formal. Es el objeto más
visible para el usuario — no ve Tasks individuales sueltas, ve "el plan que
va a ejecutarse" y decide si aprobarlo. Por eso necesita el mismo nivel de
rigor que ya recibió Task en `TASK_ENGINE.md`.

---

## 2. Anatomía de un Execution Plan

```
ExecutionPlan
  id              str    — identificador único (uuid)
  intent          str    — la petición original del usuario, en texto
  status          enum   — ver §3 Ciclo de vida
  tasks           list   — lista ordenada de Task ids que lo componen
  task_graph      dict   — dependencias entre las tasks (quién depende de quién)
  requires_approval bool — si necesita aprobación humana antes de ejecutarse
  approved_by     str    — quién aprobó, None si no ha sido aprobado
  estimated_impact enum  — low | medium | high | critical
  created_at      str    — timestamp ISO
  updated_at      str    — timestamp ISO
  started_at      str    — timestamp ISO, None si no ha empezado
  completed_at    str    — timestamp ISO, None si no ha terminado
  rollback_plan   list   — ids de Tasks de rollback, en orden inverso
  result_summary  dict   — resumen de lo ejecutado (qué falló, qué completó)
  audit_trail     list   — eventos emitidos por este plan
```

### Ejemplo concreto

```json
{
  "id": "exec-2026-06-30-001",
  "intent": "Crea una plataforma SaaS en AWS con EKS y CI/CD",
  "status": "pending_approval",
  "tasks": ["task-001", "task-002", "task-003", "task-004", "task-005"],
  "task_graph": {
    "task-001": [],
    "task-002": ["task-001"],
    "task-003": ["task-002"],
    "task-004": ["task-002"],
    "task-005": ["task-003", "task-004"]
  },
  "requires_approval": true,
  "approved_by": null,
  "estimated_impact": "medium",
  "created_at": "2026-06-30T09:00:00",
  "updated_at": "2026-06-30T09:00:00",
  "started_at": null,
  "completed_at": null,
  "rollback_plan": [],
  "result_summary": null,
  "audit_trail": []
}
```

---

## 3. Ciclo de vida (estados)

```
CREATED ──► VALIDATED ──► PENDING_APPROVAL ──► APPROVED ──► RUNNING ──► COMPLETED
   │             │               │                              │
   │             │               │                              └──► FAILED ──► ROLLED_BACK
   │             │               ▼
   │             │           REJECTED
   │             ▼
   │         INVALID
   │
   └──► CANCELLED (en cualquier punto antes de RUNNING)
```

| Estado | Significado |
|---|---|
| `CREATED` | El Task Planner generó el plan a partir del Intent |
| `VALIDATED` | Las Tasks que lo componen son coherentes (dependencias resolubles, sin ciclos) |
| `INVALID` | Falló la validación — el plan nunca se presenta al usuario |
| `PENDING_APPROVAL` | Esperando decisión humana (si `requires_approval = true`) |
| `APPROVED` | Autorizado para ejecutarse (manual o automático según política) |
| `REJECTED` | El usuario o una política lo bloqueó — no se ejecuta |
| `RUNNING` | El Workflow Engine está ejecutando las Tasks del plan |
| `COMPLETED` | Todas las Tasks terminaron en `COMPLETED` |
| `FAILED` | Una o más Tasks terminaron en `FAILED` sin recuperación posible |
| `ROLLED_BACK` | Tras un fallo, se ejecutó el rollback de las Tasks ya completadas |
| `CANCELLED` | Cancelado manualmente antes de `RUNNING` |

Un Execution Plan en `PENDING_APPROVAL` es exactamente lo que ve el usuario
en el Dashboard como "¿Deseas ejecutarlo?" (ver ARCHITECTURE.md §4, paso 4).

---

## 4. Validación antes de presentar el plan

Antes de pasar a `PENDING_APPROVAL`, el plan se valida (`VALIDATED` o
`INVALID`):

- El `task_graph` no contiene dependencias circulares
- Cada Task referenciada existe y tiene `type` reconocido por algún Agent
  registrado
- No hay Tasks duplicadas con el mismo `idempotency_key` dentro del mismo
  plan

Un plan `INVALID` nunca llega al usuario — se registra en el Audit Log como
un intento fallido de planificación, útil para depurar el Task Planner.

---

## 5. Relación con Governance

`requires_approval` y `estimated_impact` no los decide el plan por sí
mismo — los calcula Governance evaluando las Tasks que lo componen (ver
ADR-002: ninguna Task se ejecuta sin pasar por Governance). El Execution
Plan hereda el nivel de control más estricto entre todas sus Tasks: si una
sola Task requiere aprobación de nivel 4 (producción), el plan completo
queda en `PENDING_APPROVAL` aunque el resto de Tasks sean de solo lectura.

---

## 6. Relación con Workflow Engine

El Execution Plan es la unidad que el Workflow Engine recibe para
ejecutar. El Workflow Engine:

1. Toma el `task_graph` y determina el orden de ejecución respetando
   dependencias (igual que define `TASK_ENGINE.md §4` a nivel de Task
   individual, pero aplicado al conjunto completo del plan)
2. Ejecuta Tasks en paralelo cuando no tienen dependencias entre sí
3. Si una Task falla sin recuperación, detiene el plan y lo marca `FAILED`
4. Dispara el `rollback_plan` si corresponde, transicionando a
   `ROLLED_BACK`

El detalle de cómo el Workflow Engine resuelve el grafo de dependencias se
documenta en `WORKFLOW_ENGINE.md` (pendiente).

---

## 7. Pausar y reanudar

Un Execution Plan en `RUNNING` puede pausarse (las Tasks ya `RUNNING` no se
interrumpen, pero no se disparan Tasks nuevas) y reanudarse después. Esto
es relevante para flujos largos (ej. aprovisionar infraestructura multi-AZ)
donde un humano puede necesitar intervenir a mitad de camino sin perder el
progreso ya hecho. El estado intermedio se persiste — ver nota en §9.

---

## 8. Eventos emitidos

```
plan.created
plan.validated
plan.invalid
plan.pending_approval
plan.approved
plan.rejected
plan.started
plan.paused
plan.resumed
plan.completed
plan.failed
plan.rollback_started
plan.rollback_completed
plan.cancelled
```

Igual que con Task (`TASK_ENGINE.md §9`), estos eventos alimentan el
Dashboard y el Audit Log sin que ningún componente necesite hacer polling.

---

## 9. Nota sobre persistencia (relacionado con Future Work)

Este documento asume que el estado de un Execution Plan se persiste de
forma que sobreviva un reinicio de la plataforma (necesario para poder
pausar/reanudar como describe §7). El mecanismo concreto de persistencia
(ej. un State Store dedicado) se deja fuera del alcance de este documento
y queda registrado como trabajo futuro — ver `ROADMAP.md §Future Work` y
`ADR-003`.

---

## 10. Lo que NO incluye este documento

- Cómo se resuelve el orden de ejecución y el paralelismo dentro del plan
  → `WORKFLOW_ENGINE.md`
- Cómo se calcula `requires_approval` y `estimated_impact` → `GOVERNANCE.md`
- Dónde y cómo se persiste físicamente el estado → trabajo futuro,
  ver `ADR-003`
