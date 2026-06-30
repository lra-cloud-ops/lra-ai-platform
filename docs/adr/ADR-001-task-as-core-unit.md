# ADR-001: Task como unidad central del sistema (en vez de Agent)

**Estado:** Aceptado
**Fecha:** 2026-06-30
**Relacionado:** ARCHITECTURE.md, TASK_ENGINE.md

---

## Contexto

La primera versión de LRA AI Platform (v1.0) se diseñó con un flujo
secuencial donde los Agents se llamaban entre sí directamente:

```
Usuario → Founder → Architect → DevOps → SRE → Documentation
```

Esto funcionó para construir y probar el primer agente real (`FounderAgent`),
que efectivamente creó un repositorio en GitHub con documentación generada
automáticamente.

## Problema

Este diseño no escala más allá de una demo:

1. Añadir un agente nuevo (ej. un especialista de Azure) requiere modificar
   el flujo de llamadas existente.
2. No hay un punto único donde insertar aprobación humana, políticas de
   seguridad o auditoría — cada agente tendría que implementarlo por su
   cuenta.
3. No existe una unidad de trabajo lo bastante pequeña como para poder
   reintentar, cancelar o revertir de forma aislada.
4. Los agentes acoplados directamente entre sí hacen imposible reordenar,
   paralelizar o reutilizar pasos del flujo en otros contextos.

## Alternativas consideradas

**A. Mantener el flujo secuencial de agentes (v1.0)**
Descartado. No resuelve gobernanza, auditoría ni reintentos, y el
acoplamiento entre agentes crece de forma combinatoria con cada agente
nuevo.

**B. Centrar el sistema en Capabilities directamente, sin Task**
Descartado. Las Capabilities son útiles como piezas atómicas reutilizables,
pero no tienen ciclo de vida propio (estado, dependencias, retries,
rollback). Sin un objeto que represente "una unidad de trabajo en curso",
no hay forma de auditar ni de pausar/reanudar el sistema.

**C. Centrar el sistema en Task, con Agents como ejecutores** (elegida)
Una Task es una unidad atómica con identidad propia, estado, dependencias y
ciclo de vida. Los Agents dejan de decidir el flujo y pasan a ejecutar Tasks
que les asigna un Workflow Engine. Esto permite insertar Governance entre
"se decidió hacer esto" y "se ejecutó esto" de forma uniforme para
cualquier Agent o Tool presente o futura.

## Decisión

Se adopta Task como la unidad central del sistema. La jerarquía pasa a ser:

```
Usuario → Supervisor → Workflow → Task → Governance → Capability → Tool → Provider
```

Los Agents son especialistas que ejecutan Tasks; no orquestan el flujo ni
llaman a otros Agents directamente.

## Consecuencias

**Positivas:**
- Cualquier acción de la plataforma es auditable, aprobable y reversible de
  forma uniforme, sin importar qué Agent o Tool esté detrás.
- Añadir un Agent nuevo no requiere tocar el flujo existente — solo se
  registra y el Task Planner decide cuándo asignarle Tasks.
- Reintentos, timeouts e idempotencia se resuelven una vez en el Task
  Engine, no en cada Agent por separado.

**Negativas / costos asumidos:**
- Mayor complejidad inicial: hay que construir Task Engine, Workflow Engine
  y Governance Engine antes de poder añadir el segundo Agent real.
- El `FounderAgent` ya construido en v1.0 requiere refactor para ejecutar
  Tasks individuales en vez de orquestar su propio flujo interno.
- Mayor número de objetos a serializar y persistir (cada Task, no solo el
  resultado final).

## Referencias

- TASK_ENGINE.md — contrato completo de Task
- ADR-002 — por qué Governance se evalúa antes de la ejecución, no después
