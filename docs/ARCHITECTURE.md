# ARCHITECTURE.md

## LRA AI Platform — Arquitectura del Sistema

**Versión:** 2.0 (post-refactor: arquitectura centrada en Tasks)
**Estado:** Congelado — este documento es el contrato de la plataforma
**Relacionado:** TASK_ENGINE.md, GOVERNANCE.md, WORKFLOW_ENGINE.md, MEMORY.md

---

## 1. Por qué existe este documento

Este documento define el "ADN" de LRA AI Platform. Antes de escribir una sola
línea de código del Task Engine, Governance Engine o Workflow Engine, este
documento congela las decisiones fundamentales para que el resto del sistema
se construya sobre un contrato estable.

Cualquier cambio a los conceptos definidos aquí debe pasar primero por un ADR
(ver `docs/adr/`) antes de tocar código.

---

## 2. Principio rector

> Los agentes no son el centro del sistema. Son especialistas que ejecutan
> Tasks dentro de un flujo gobernado por políticas, permisos y aprobaciones.

La plataforma no está centrada en agentes. Está centrada en **tareas y
capacidades**, orquestadas por un Workflow Engine y controladas por un
Governance Engine. Los agentes ejecutan trabajo; no deciden ni gobiernan.

```
Usuario
   │
   ▼
Supervisor
   │
   ▼
Workflow Engine
   │
   ▼
Governance Engine ──── Policies, Approvals, Audit, Compliance, Risk
   │
   ▼
Capabilities
   │
   ▼
Tools
   │
   ▼
Providers (AWS, GitHub, Kubernetes, OpenShift...)
```

---

## 3. Glosario de conceptos

### 3.1 Intent

La intención cruda del usuario, en lenguaje natural o estructurado, antes de
ser interpretada.

```
Intent: "Crea una plataforma SaaS en AWS con EKS y CI/CD"
```

El Intent no ejecuta nada. Es la entrada al Supervisor.

### 3.2 Execution Plan

La traducción de un Intent en una secuencia concreta de Tasks, antes de
ejecutarse. Es el objeto más importante de la plataforma desde el punto de
vista del usuario: es lo que se revisa y aprueba.

```
Execution Plan
  id: exec-2026-06-30-001
  intent: "Crea una plataforma SaaS en AWS"
  status: pending_approval
  tasks:
    - create_repository
    - generate_documentation
    - provision_vpc
    - provision_eks
    - setup_cicd
  estimated_impact: medium
  requires_approval: true
```

Un Execution Plan puede pausarse, reanudarse, auditarse y revertirse (ver
TASK_ENGINE.md §5 Rollback).

### 3.3 Task

La unidad atómica de trabajo. Todo en la plataforma —crear un repo, escanear
seguridad, desplegar una app— es una Task. Definición completa en
`TASK_ENGINE.md`.

### 3.4 Capability

Una habilidad pequeña y atómica que una Task invoca. No es "deploy_application"
(demasiado grande), sino piezas componibles:

```
create_repository()
create_vpc()
create_cluster()
build_image()
push_image()
deploy_workload()
create_dashboard()
configure_alerts()
```

Una Task puede componer varias Capabilities. Una Capability usa una o más
Tools para ejecutarse.

### 3.5 Tool

Un módulo que ejecuta acciones reales contra un Provider externo (GitHub API,
AWS CLI, kubectl...). Cada Tool se descompone internamente en servicios
pequeños en vez de un único archivo monolítico:

```
GitHub Tool
  ├── RepositoryService
  ├── BranchService
  ├── IssueService
  ├── PullRequestService
  └── ActionsService
```

### 3.6 Provider

El sistema externo real al que una Tool se conecta: AWS, Azure, GCP, GitHub,
Kubernetes, OpenShift, Jenkins, etc. La plataforma nunca habla con un
Provider directamente — siempre a través de una Tool.

### 3.7 Agent

Un especialista que ejecuta Tasks de un dominio concreto (DevOps, Security,
Cloud Architecture...). Un Agent no decide el plan de ejecución ni tiene
acceso directo a Tools sin pasar por Governance. Recibe Tasks asignadas por
el Workflow Engine y las ejecuta usando Capabilities.

Importante: un Agent **no tiene tools fijas hardcodeadas**. Por ejemplo, hoy
el DevOps Agent puede usar AWS; mañana puede usar Azure sin que el Agent
cambie — solo cambia qué Capability/Tool se le asigna.

### 3.8 Workflow

Una secuencia reutilizable y con nombre de Tasks encadenadas, con
dependencias explícitas entre ellas. Ver `WORKFLOW_ENGINE.md`.

```
Workflow: "create_aws_project"
  Task: bootstrap
  Task: provision_infrastructure   (depends_on: bootstrap)
  Task: setup_cicd                 (depends_on: provision_infrastructure)
  Task: configure_observability    (depends_on: setup_cicd)
```

### 3.9 Governance

La capa que decide si una Task puede ejecutarse, quién debe aprobarla, y deja
registro inmutable de todo lo que ocurrió. Ver `GOVERNANCE.md`. Ninguna Task
llega a una Tool sin pasar por Governance.

### 3.10 Memory

El sistema de contexto persistente de la plataforma, dividido en 4 ámbitos
(Organization, Project, Workflow, Conversation). Ver `MEMORY.md`.

### 3.11 Supervisor

El punto de entrada único. Recibe el Intent del usuario, lo traduce en un
Execution Plan vía el Task Planner, y lo presenta para aprobación antes de
disparar el Workflow Engine.

---

## 4. Flujo completo: de la petición a la ejecución

```
1. Usuario expresa un Intent
       "Despliega la versión 2.4 en producción"

2. Supervisor recibe el Intent

3. Task Planner traduce el Intent en un Execution Plan
       Plan: [build_image, push_ecr, terraform_plan,
              deploy_k8s, smoke_tests, update_docs]

4. El Execution Plan se presenta al usuario
       "¿Deseas ejecutarlo?"

5. Usuario aprueba (Governance: nivel de permiso requerido)

6. Workflow Engine ejecuta las Tasks en orden, respetando dependencias

7. Cada Task pasa por Governance antes de tocar una Tool
       Task → Governance (policy check, approval gate) → Capability → Tool → Provider

8. Cada paso se registra en el Audit Log

9. Si una Task falla, el Workflow Engine puede:
   - reintentar (según política de retry)
   - detenerse y notificar
   - ejecutar rollback de las Tasks ya completadas

10. Al finalizar, se genera un informe y se actualiza Memory
```

---

## 5. Por qué esta arquitectura escala

| Problema con el diseño anterior (v1.0, agentes secuenciales) | Solución en v2.0 |
|---|---|
| Agentes llamándose entre sí directamente | Agentes solo reciben Tasks del Workflow Engine |
| Añadir un agente nuevo requería tocar el flujo completo | Se registra el agente; el planner decide cuándo usarlo |
| No había forma de aprobar/bloquear una acción antes de ejecutarla | Toda Task pasa por Governance antes de llegar a una Tool |
| No había rollback ni auditoría centralizada | Task Engine define ciclo de vida, rollback y audit log nativos |
| Una Tool grande y monolítica (ej. github_tool.py con 11 métodos) | Tools se descomponen en servicios pequeños |
| Memoria única sin separar contexto organizacional de contexto de proyecto | 4 tipos de Memory con alcances distintos |

---

## 6. Qué NO cambia respecto a lo ya construido

- Las interfaces `Tool`, `Agent`, `Capability`, `Memory` (`core/interfaces/`)
  siguen siendo válidas como contratos base; `Task` se añade como una interfaz
  más, no reemplaza a las existentes.
- `ConfigManager`, `ToolManager`, `AgentManager`, `EventBus` siguen siendo
  necesarios y se reutilizan tal cual.
- `GitHubTool` se conserva, pero se reorganiza internamente en servicios
  (ver §3.5) sin romper su interfaz pública `execute()`.
- `FounderAgent` se conserva, pero se refactoriza para que ya no decida el
  flujo, sino que reciba y ejecute Tasks (ver TASK_ENGINE.md §7).

---

## 7. Documentos relacionados

| Documento | Contenido |
|---|---|
| `TASK_ENGINE.md` | Definición completa de Task: ciclo de vida, estados, dependencias, retries, idempotencia, timeouts, rollback |
| `GOVERNANCE.md` | Niveles de permiso, RBAC, Approval Engine, Audit Log, Policy Engine |
| `WORKFLOW_ENGINE.md` | Cómo se encadenan Tasks en Workflows reutilizables |
| `MEMORY.md` | Los 4 tipos de memoria y su alcance |
| `PLUGIN_SYSTEM.md` | Cómo se añaden Agents/Tools/Capabilities nuevas sin tocar el core |
| `SDK.md` | Cómo construir sobre la plataforma desde fuera |
| `docs/adr/` | Registro de decisiones arquitectónicas con contexto y alternativas consideradas |
