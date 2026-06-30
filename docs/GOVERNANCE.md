# GOVERNANCE.md

## LRA AI Platform — Governance Engine

**Versión:** 1.0
**Estado:** Congelado — este documento es el contrato de la plataforma
**Depende de:** ARCHITECTURE.md, TASK_ENGINE.md, EXECUTION_PLAN.md
**Consumido por:** WORKFLOW_ENGINE.md, Supervisor, todos los Agents

---

## 1. Por qué Governance existe

Según ADR-002, ninguna Task pasa de `PENDING` a `RUNNING` sin una decisión
explícita de Governance. Este documento define cómo se toma esa decisión.

Governance no es el Audit Log. El Audit Log es una consecuencia de
Governance (todo queda registrado), pero la función central es **decidir,
antes de que algo ocurra, si puede ocurrir y quién debe autorizarlo**.

> "No dejaría que un agente hiciera esto: AWS → Delete Cluster. Nunca.
> Siempre: Agent → Capability → Approval → Tool → AWS."

---

## 2. Estructura interna (según ADR-003)

Governance se mantiene como un único documento y un único punto de entrada
conceptual (`GovernanceEngine`), pero internamente se organiza en cuatro
responsabilidades diferenciadas, cada una con un límite de responsabilidad
claro:

```
GovernanceEngine
   │
   ├── PolicyEngine     → evalúa reglas: ¿esta Task está permitida aquí?
   ├── ApprovalEngine    → gestiona aprobaciones humanas pendientes
   ├── AuditEngine       → registra todo lo que pasó, de forma inmutable
   └── RBAC              → resuelve quién es el usuario y qué nivel tiene
```

Una Task entra al `GovernanceEngine` y sale con una decisión:
`APPROVED` (puede ejecutarse, automática o ya autorizada) o `REJECTED`
(no se ejecuta), o queda en espera visible como `PENDING_APPROVAL`.

---

## 3. RBAC — Niveles de permiso

Cinco niveles, de menor a mayor capacidad de impacto. Cada usuario o
proceso automatizado tiene asignado un nivel; cada tipo de Task requiere
un nivel mínimo para ejecutarse.

| Nivel | Nombre | Puede hacer | Ejemplos de Task |
|---|---|---|---|
| **1** | Solo lectura | Leer repos, leer Kubernetes, leer AWS, leer documentación, leer logs | `get_repo`, `list_pods`, `get_metrics` |
| **2** | Proponer cambios | Crear PR, crear documentación, crear Terraform, crear Helm, crear Dockerfile — todo queda pendiente de revisión | `create_pull_request`, `generate_documentation` |
| **3** | Desarrollo | Hacer commits, crear ramas, ejecutar pruebas, desplegar en entornos de desarrollo. Nunca en producción | `create_branch`, `deploy_to_dev`, `run_tests` |
| **4** | Producción | Solo tras aprobación explícita de un plan generado | `deploy_to_production`, `terraform_apply_prod` |
| **5** | Administrador | Cambiar configuración, agentes, herramientas, permisos, políticas | `update_agent_config`, `modify_policy` |

El nivel de un usuario se resuelve en el momento en que el `Intent` llega
al Supervisor, y se adjunta a cada Task generada para ese Execution Plan
(`TASK_ENGINE.md §2`, campo `governance`).

---

## 4. PolicyEngine

Evalúa reglas declarativas sobre qué requisitos debe cumplir una Task o un
Execution Plan antes de poder ejecutarse. Las políticas se definen por
entorno, no están hardcodeadas en el código de cada Agent.

### Ejemplo de política

```yaml
production:
  requires:
    - security_scan
    - unit_tests
    - approval
    - architecture_review

development:
  requires:
    - unit_tests
```

Si una Task de tipo `deploy_to_production` llega sin que su Execution Plan
incluya una Task `security_scan` ya `COMPLETED`, el PolicyEngine la
rechaza inmediatamente — no llega siquiera a la cola de aprobación humana.
Esto es lo que se quiere decir con "Deployment bloqueado" en el documento
original de visión: la política bloquea antes de que un humano tenga que
notarlo.

### Relación con `estimated_impact` del Execution Plan

El PolicyEngine es quien calcula `estimated_impact` (`EXECUTION_PLAN.md
§2`) evaluando el conjunto de Tasks del plan contra las políticas del
entorno destino.

---

## 5. ApprovalEngine

Gestiona las Tasks/Plans que requieren aprobación humana explícita
(nivel 4 en adelante, o cualquier política que lo exija).

```
Task con governance.requires_approval = true
   │
   ▼
ApprovalEngine la coloca en PENDING_APPROVAL
   │
   ▼
Visible en el Dashboard: "¿Deseas ejecutarlo?"
   │
   ├── Usuario aprueba  → Task pasa a APPROVED → Workflow Engine la ejecuta
   └── Usuario rechaza  → Task pasa a REJECTED → no se ejecuta, queda auditada
```

Una aprobación se registra con: quién aprobó, cuándo, y opcionalmente un
comentario. Esto se adjunta al campo `approved_by` del Execution Plan
(`EXECUTION_PLAN.md §2`) y al `audit_trail` de la Task correspondiente.

Las aprobaciones no son "todo o nada" a nivel de plan completo: el
ApprovalEngine puede aprobar Tasks individuales dentro de un plan mayor,
permitiendo que un usuario revise paso a paso un cambio complejo antes de
autorizar la parte más sensible.

---

## 6. AuditEngine

Registra de forma inmutable cada evento emitido por el Task Engine
(`TASK_ENGINE.md §9`) y el Execution Plan (`EXECUTION_PLAN.md §8`). El
Audit Log nunca se edita ni se borra — solo se añade.

### Ejemplo de entrada

```
11:30  founder         → task.completed   → create_repository (client-api)
11:32  cloud_architect → task.completed   → provision_vpc
11:34  devops          → task.completed   → setup_cicd_pipeline
11:36  ruben.liquenson → plan.approved    → exec-2026-06-30-001
11:37  devops          → task.started     → terraform_apply (production)
```

Cada entrada incluye: timestamp, actor (Agent o usuario humano), tipo de
evento, Task/Plan afectado, y el resultado si aplica. El AuditEngine es
de solo escritura desde la perspectiva de cualquier otro componente — ni
siquiera un Administrador (nivel 5) puede modificar entradas existentes,
solo añadir nuevas (ej. una nota de incidente posterior).

---

## 7. Flujo completo de una Task a través de Governance

```
Task creada (status: PENDING)
   │
   ▼
RBAC resuelve el nivel del actor que la origina
   │
   ▼
PolicyEngine evalúa si la Task cumple los requisitos del entorno
   │
   ├── No cumple  → status: REJECTED → AuditEngine registra el rechazo
   │
   └── Cumple
        │
        ▼
   ¿Requiere aprobación humana? (según nivel RBAC + política)
        │
        ├── No → status: APPROVED automáticamente → AuditEngine registra
        │
        └── Sí → status: PENDING_APPROVAL
                    │
                    ▼
              ApprovalEngine espera decisión humana
                    │
                    ├── Aprobada → status: APPROVED → AuditEngine registra
                    └── Rechazada → status: REJECTED → AuditEngine registra
```

Solo una Task en `APPROVED` puede ser tomada por el Workflow Engine para
pasar a `RUNNING`.

---

## 8. Riesgo: ¿qué pasa si Governance falla?

Tal como se estableció en ADR-002, el GovernanceEngine es un punto crítico
del sistema. Su comportamiento ante fallo interno es:

> **Denegar por defecto.** Si el PolicyEngine, ApprovalEngine o RBAC no
> pueden resolver una decisión (error interno, timeout, dependencia
> caída), la Task se marca `REJECTED` con `error.reason = "governance
> unavailable"`. Nunca se aprueba por omisión.

Esto se documenta explícitamente porque es la diferencia entre un sistema
seguro por diseño y uno que falla de forma insegura.

---

## 9. Risk Assessment (nota de alcance)

El documento de visión original menciona un componente de "Risk
Assessment" dentro de Governance. En esta versión 1.0, el riesgo se
modela de forma simple a través de `estimated_impact` (calculado por
PolicyEngine, ver §4) con cuatro niveles (`low | medium | high |
critical`). Un motor de evaluación de riesgo más sofisticado (scoring
dinámico, histórico de incidentes por tipo de Task) queda fuera de
alcance de este documento y se añade a `ROADMAP.md §Future Work` si se
identifica la necesidad concreta tras operar la plataforma con varios
agentes reales.

---

## 10. Lo que NO incluye este documento

- Cómo el Workflow Engine usa las decisiones de Governance para decidir
  qué Tasks ejecutar en paralelo → `WORKFLOW_ENGINE.md`
- Dónde se persisten físicamente las entradas del Audit Log → trabajo
  futuro relacionado con State Store, ver `ADR-003`
- El detalle de un Resource Model para políticas a nivel de recurso
  individual (ej. "este bucket específico requiere aprobación") → pospuesto,
  ver `ADR-003`
