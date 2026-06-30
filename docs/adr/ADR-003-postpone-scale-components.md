# ADR-003: Posponer Resource Model, State Store, Scheduler, Queue Manager y separación Internal/External API

**Estado:** Aceptado
**Fecha:** 2026-06-30
**Relacionado:** ARCHITECTURE.md, TASK_ENGINE.md, EXECUTION_PLAN.md

---

## Contexto

Tras congelar `ARCHITECTURE.md`, `TASK_ENGINE.md` y los ADR-001/002, se
recibió una revisión externa de la arquitectura que propone 10 mejoras
adicionales antes de continuar con `GOVERNANCE.md` y `WORKFLOW_ENGINE.md`.
De esas 10, algunas cierran lagunas reales en lo ya escrito; otras
introducen componentes propios de una plataforma operando a una escala que
LRA AI Platform todavía no tiene (1 agente implementado, 1 Tool real).

## Problema

Diseñar contra una escala futura hipotética, antes de implementar el
primer Task Engine funcional, tiene un costo real: cada documento nuevo es
una superficie más a mantener coherente, y el riesgo concreto es no pasar
nunca de la fase de diseño a la de código. Es necesario distinguir entre
"laguna en el contrato ya escrito" y "feature para cuando la plataforma
tenga tráfico real".

## Alternativas consideradas

**A. Escribir los 10 documentos/cambios propuestos antes de tocar código**
Descartado. Cuatro sesiones de diseño sin una sola línea de Task Engine
implementada es una señal de alerta, no de rigor. Varias de las piezas
propuestas (Scheduler para tareas programadas, Queue Manager para 500
Tasks concurrentes, Resource Inventory distribuido) resuelven problemas de
escala que no existen todavía con un solo Agent real operando.

**B. Ignorar la revisión por completo y seguir solo con lo ya planeado**
Descartado. La revisión identifica un hueco real: `EXECUTION_PLAN.md` se
mencionaba como concepto en `ARCHITECTURE.md` pero nunca recibió ciclo de
vida propio, a diferencia de `Task`. Ese hueco sí debía cerrarse antes de
implementar Governance/Workflow, que dependen de él.

**C. Cerrar el hueco real ahora; posponer el resto como trabajo futuro
explícito** (elegida)
Se escribe `EXECUTION_PLAN.md` inmediatamente, porque Governance y
Workflow Engine necesitan ese contrato para funcionar. El resto de
propuestas se documenta como Future Work en `ROADMAP.md`, con su
justificación, para no perder el criterio de la revisión ni bloquear el
inicio de la implementación.

## Decisión

Se escribe `EXECUTION_PLAN.md` como parte del hito de diseño actual.

Se posponen explícitamente, registrados en `ROADMAP.md §Future Work`:

| Propuesta | Por qué se pospone | Se retoma cuando |
|---|---|---|
| Resource Model (Repository, VPC, EKS como objetos) | Útil cuando varias Tasks de distintos Agents operan sobre el mismo recurso compartido; con 1 Agent no hay colisión que resolver | Al implementar el segundo Agent (Cloud Architect o DevOps) |
| State Store dedicado | El estado de Task/Plan puede persistir inicialmente en el mismo mecanismo de `MemoryManager` (JSON en disco) ya construido y probado | Cuando se necesite ejecución distribuida (más de un proceso de la plataforma corriendo a la vez) |
| Scheduler (tareas programadas tipo cron) | Ningún Workflow actual lo necesita; todos se disparan por Intent de usuario | Cuando exista un caso de uso real (ej. backup diario, escaneo de seguridad semanal) |
| Queue Manager para alta concurrencia | Diseñado para 500 Tasks simultáneas; hoy el volumen real es 1 Task a la vez | Cuando el Workflow Engine y Governance estén implementados y se observe contención real |
| Separación Internal API / External API | Prematuro sin haber construido siquiera la API REST inicial | Al implementar `api/` (Fase posterior del roadmap general) |
| División de Governance en 4 sub-engines (Policy/Approval/Audit/Compliance) | Se conserva como estructura interna *dentro* de `GOVERNANCE.md`, no como 4 documentos separados | Se evalúa al escribir `GOVERNANCE.md`, no requiere ADR propio |
| Resource Inventory | Depende de que exista primero el Resource Model | Junto con Resource Model |
| Versionado de contratos (Task v1, v2...) | Anotación de una línea en `TASK_ENGINE.md`, no requiere documento propio | Se añade como nota, no se pospone como feature |

## Consecuencias

**Positivas:**
- El hito de diseño se cierra con un alcance acotado y se pasa a
  implementación, evitando la parálisis por diseño.
- Las ideas de la revisión no se pierden — quedan trazables en
  `ROADMAP.md` con su disparador concreto ("se retoma cuando...").
- `EXECUTION_PLAN.md` cierra una inconsistencia real: Task tenía ciclo de
  vida formal y Execution Plan no.

**Negativas / riesgos asumidos:**
- Si el segundo y tercer Agent se implementan más rápido de lo previsto,
  el Resource Model puede volverse urgente antes de lo planeado — debe
  vigilarse al implementar Cloud Architect Agent.
- Usar `MemoryManager` (JSON en disco) como mecanismo de persistencia
  temporal para Task/Plan State no soporta ejecución concurrente real; es
  aceptable mientras la plataforma corra como un solo proceso.

## Referencias

- ADR-001 — Task como unidad central
- ADR-002 — Governance antes de ejecución
- EXECUTION_PLAN.md — contrato cerrado en este mismo hito
- ROADMAP.md §Future Work — registro detallado de lo pospuesto
