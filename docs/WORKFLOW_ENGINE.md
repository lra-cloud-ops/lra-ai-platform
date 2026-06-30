# WORKFLOW_ENGINE.md

## LRA AI Platform — Workflow Engine

**Versión:** 1.0
**Estado:** Congelado — este documento es el contrato de la plataforma
**Depende de:** ARCHITECTURE.md, TASK_ENGINE.md, EXECUTION_PLAN.md, GOVERNANCE.md
**Consumido por:** Supervisor, Dashboard

---

## 1. Qué hace el Workflow Engine

Recibe un Execution Plan ya `APPROVED` (`EXECUTION_PLAN.md §3`) y ejecuta
las Tasks que lo componen en el orden correcto, respetando el
`task_graph`, paralelizando lo que se pueda, y manejando fallos según la
política de cada Task. No decide si algo está permitido —eso ya lo
resolvió Governance antes de que el plan llegara aquí— solo decide
**cuándo** y **en qué orden** ejecutar lo ya aprobado.

```
Execution Plan (APPROVED)
      │
      ▼
Workflow Engine
      │
      ├── resuelve el task_graph
      ├── ejecuta Tasks respetando dependencias
      ├── paraleliza Tasks independientes
      ├── reacciona a fallos (retry / stop / rollback)
      └── actualiza el estado del Execution Plan
```

---

## 2. Workflow como plantilla reutilizable

Antes de hablar de ejecución, hay que distinguir dos cosas que comparten
nombre pero no son lo mismo:

- **Workflow** (plantilla): una secuencia de tipos de Task con nombre,
  reutilizable, definida una vez. Ejemplo: `"create_aws_project"`.
- **Execution Plan** (instancia): el resultado concreto de aplicar un
  Workflow (o de que el Task Planner genere uno ad-hoc) a un Intent
  específico del usuario, con Tasks ya parametrizadas.

```
Workflow (plantilla, vive en config/workflows/)
  name: create_aws_project
  tasks:
    - type: bootstrap
    - type: provision_infrastructure
      depends_on: [bootstrap]
    - type: setup_cicd
      depends_on: [provision_infrastructure]
    - type: configure_observability
      depends_on: [setup_cicd]

         │
         │  el Task Planner instancia el Workflow con parámetros concretos
         ▼

Execution Plan (instancia, vive en runtime)
  id: exec-2026-06-30-001
  tasks: [task-001, task-002, task-003, task-004]
  task_graph: {...}
```

Los Workflows con nombre se definen como YAML en `config/workflows/`,
siguiendo el mismo patrón ya usado para `agents.yaml` y `tools.yaml`
(`config_manager.py`, ya construido). No todo Execution Plan viene de un
Workflow con nombre — el Task Planner también puede generar planes ad-hoc
para Intents que no calzan con ninguna plantilla conocida.

---

## 3. Resolución del task_graph

El `task_graph` (`EXECUTION_PLAN.md §2`) es un grafo dirigido acíclico
(DAG). El Workflow Engine lo resuelve con un ordenamiento topológico
estándar:

```
task-001: []                          → sin dependencias, ejecuta primero
task-002: [task-001]                  → espera a task-001
task-003: [task-002]                  → espera a task-002
task-004: [task-002]                  → espera a task-002 (paralela a task-003)
task-005: [task-003, task-004]        → espera a ambas
```

```
Orden de ejecución:
  Nivel 0: task-001
  Nivel 1: task-002
  Nivel 2: task-003, task-004   (en paralelo, ninguna depende de la otra)
  Nivel 3: task-005
```

La validación de que el grafo no tiene ciclos ya ocurrió antes, al pasar
el Execution Plan de `CREATED` a `VALIDATED` (`EXECUTION_PLAN.md §4`). El
Workflow Engine asume un grafo válido al recibirlo.

---

## 4. Paralelismo

Todas las Tasks de un mismo "nivel" del grafo (sin dependencias entre sí)
se disparan a la vez. El límite de concurrencia real depende de cuántos
Agents distintos estén disponibles para tomar Tasks simultáneamente — si
dos Tasks paralelas requieren el mismo Agent, ese Agent las procesa en
secuencia internamente (el Workflow Engine no obliga paralelismo dentro
de un mismo Agent, solo lo permite entre Agents distintos).

Nota de alcance: el verdadero paralelismo a gran escala (cientos de Tasks
simultáneas con un pool de workers) es el problema que resuelve el Queue
Manager pospuesto en `ADR-003`. En esta versión, el paralelismo es
cooperativo y limitado al número de Agents activos.

---

## 5. Manejo de fallos

Cuando una Task pasa a `FAILED` (`TASK_ENGINE.md §3`):

```
Task FAILED
   │
   ▼
¿Tiene retry_policy con intentos restantes?
   │
   ├── Sí → status: RETRYING → se reintenta tras el backoff configurado
   │
   └── No
        │
        ▼
   Todas las Tasks que dependen de ella (directa o transitivamente)
   pasan a CANCELLED (TASK_ENGINE.md §4 — no se ejecutan a ciegas)
        │
        ▼
   El Execution Plan completo pasa a FAILED
        │
        ▼
   ¿El plan tiene rollback_plan definido?
        │
        ├── Sí → plan.status: ROLLED_BACK → se ejecutan las Tasks de
        │         rollback en orden inverso a como se completaron
        │
        └── No → el plan queda en FAILED, requiere intervención manual
```

Las Tasks ya `COMPLETED` en el momento del fallo no se tocan
automáticamente salvo que el rollback las incluya explícitamente.

---

## 6. Pausar y reanudar

Tal como anticipa `EXECUTION_PLAN.md §7`, el Workflow Engine soporta
pausar un plan en `RUNNING`:

```
plan.pause()
   → las Tasks ya RUNNING terminan su ejecución normalmente
   → no se disparan Tasks nuevas, aunque sus dependencias se cumplan
   → plan.status: PAUSED (estado adicional, solo alcanzable desde RUNNING)

plan.resume()
   → plan.status: RUNNING
   → se reanuda el disparo de Tasks pendientes según el task_graph
```

Esto requiere que el Workflow Engine pueda reconstruir en qué punto del
grafo se quedó — se apoya en el estado ya persistido de cada Task
individual (`status`, `completed_at`), no en un mecanismo aparte.

---

## 7. Relación con Governance durante la ejecución

Aunque el plan completo ya fue `APPROVED` antes de llegar al Workflow
Engine, cada Task individual sigue pasando por el flujo de Governance
descrito en `GOVERNANCE.md §7` antes de transicionar a `RUNNING`. Esto es
intencional: la aprobación del plan autoriza la intención general, pero
una política puede seguir bloqueando una Task específica si las
condiciones cambiaron entre la aprobación y el momento de ejecución (ej.
un `security_scan` posterior detecta algo nuevo). El Workflow Engine no
asume que "plan aprobado" equivale a "todas las Tasks se ejecutan sin
más preguntas".

---

## 8. Relación con Agents

El Workflow Engine no ejecuta Tasks directamente — las asigna al Agent
correspondiente (`Task.assigned_to`, `TASK_ENGINE.md §2`) y espera el
resultado. El Agent invoca la Capability indicada en `Task.capability`.
El Workflow Engine es agnóstico a qué hace el Agent internamente; solo le
importa el resultado (`COMPLETED` o `FAILED`) y el `result`/`error`
devuelto.

```
Workflow Engine
   │
   │  asigna Task a Agent según Task.assigned_to
   ▼
Agent.execute_task(task)
   │
   │  invoca la Capability indicada en task.capability
   ▼
Capability → Tool → Provider
   │
   ▼
resultado vuelve al Workflow Engine
```

---

## 9. Eventos emitidos (adicionales a los de Task y Plan)

```
workflow.template_loaded
workflow.instantiated
workflow.task_dispatched
workflow.level_completed       (todas las Tasks de un nivel del grafo terminaron)
```

Estos se suman a los ya definidos en `TASK_ENGINE.md §9` y
`EXECUTION_PLAN.md §8`; no los reemplazan.

---

## 10. Lo que NO incluye este documento

- Cómo se calcula si una Task requiere aprobación → `GOVERNANCE.md`
- Cómo se persiste el estado para sobrevivir un reinicio durante una
  pausa → trabajo futuro relacionado con State Store, ver `ADR-003`
- Verdadero paralelismo a gran escala con pool de workers → Queue
  Manager, pospuesto en `ADR-003`
