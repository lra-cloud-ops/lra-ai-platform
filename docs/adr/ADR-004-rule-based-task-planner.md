# ADR-004: Task Planner basado en reglas (Workflows con nombre) en v1, IA real como mejora futura

**Estado:** Aceptado
**Fecha:** 2026-06-30
**Relacionado:** WORKFLOW_ENGINE.md §2, SDK.md §3

---

## Contexto

`task_planner.py` traduce el `Intent` del usuario (texto libre) en un
`ExecutionPlan` concreto. Con `Task`, `ExecutionPlan`, `GovernanceEngine`,
`TaskEngine` y `WorkflowEngine` ya implementados y probados end-to-end,
queda decidir cómo el planner interpreta el lenguaje natural.

## Problema

Usar un modelo de lenguaje (Claude) para interpretar el Intent es más
flexible, pero introduce una dependencia externa (API key, latencia, costo
por llamada) justo en el componente que todavía no tiene pruebas de
integración con el resto del núcleo recién construido.

## Alternativas consideradas

**A. IA real desde el día 1**
Descartado por ahora. Acopla la primera prueba del Task Planner a la
disponibilidad de una API externa, justo cuando lo que se necesita validar
es que el planner entrega un `ExecutionPlan` con un `task_graph` válido
que `WorkflowEngine` pueda ejecutar — eso es independiente de cómo se
genera el plan.

**B. Reglas simples basadas en Workflows con nombre** (elegida)
Se usa el concepto de Workflow como plantilla, ya definido en
`WORKFLOW_ENGINE.md §2`. El planner hace mapeo por palabras clave del
Intent a un Workflow registrado (ej. "crea... repo/proyecto" →
`create_project` workflow), e instancia sus Tasks con los parámetros
extraídos del Intent. Predecible, sin dependencias externas, fácil de
testear de forma determinista.

## Decisión

`task_planner.py` v1.0 usa mapeo por keywords contra Workflows
registrados en `config/workflows/`. Cuando el Intent no matchea ningún
Workflow conocido, el planner retorna un plan `INVALID` con
`reason: "no_matching_workflow"` en vez de adivinar.

La integración con Claude (vía API, interpretando el Intent con más
flexibilidad y generando `task_graph` para casos no cubiertos por un
Workflow con nombre) queda registrada como mejora futura.

## Consecuencias

**Positivas:**
- El Task Planner se puede probar de inmediato sin configurar
  credenciales adicionales, completando la cadena Intent → Plan →
  Governance → Execution de principio a fin con el resto del núcleo ya
  construido.
- Comportamiento determinista: el mismo Intent siempre genera el mismo
  plan, útil para tests automatizados futuros.

**Negativas / costos asumidos:**
- Solo cubre Intents que matchean un Workflow predefinido. Un Intent
  genuinamente novedoso (sin Workflow registrado) no genera un plan
  parcial inteligente — falla explícitamente.
- Requiere mantener Workflows en YAML a mano según crecen los casos de
  uso, hasta que se implemente la versión con IA.

## Referencias

- WORKFLOW_ENGINE.md §2 — Workflow como plantilla reutilizable
- SDK.md §3 — flujo de consumidor vía Supervisor
- Future Work (a añadir en ROADMAP.md): Task Planner con interpretación
  vía Claude API para Intents sin Workflow predefinido
