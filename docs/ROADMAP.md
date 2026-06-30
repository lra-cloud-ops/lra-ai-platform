# ROADMAP.md

## LRA AI Platform — Roadmap

**Versión:** 2.0 (post-refactor: arquitectura centrada en Tasks)
**Relacionado:** ARCHITECTURE.md, TASK_ENGINE.md, EXECUTION_PLAN.md, ADR-003

---

## Fase 0 — Diseño (en curso)

### Hito 1 — Completado ✓
- [x] `ARCHITECTURE.md`
- [x] `TASK_ENGINE.md`
- [x] `ADR-001` — Task como unidad central
- [x] `ADR-002` — Governance antes de ejecución

### Hito 2 — Completado ✓
- [x] `EXECUTION_PLAN.md`
- [x] `ADR-003` — Posponer componentes de escala futura

### Hito 3 — Siguiente
- [ ] `GOVERNANCE.md` — niveles de permiso, RBAC, Approval Engine, Policy
      Engine, Audit Log (estructurados como responsabilidades internas
      diferenciadas, según ADR-003)
- [ ] `WORKFLOW_ENGINE.md` — cómo se resuelve el `task_graph` de un
      Execution Plan, paralelismo, manejo de fallos

### Hito 4
- [ ] `MEMORY.md` — los 4 tipos de memoria (Organization, Project,
      Workflow, Conversation) y su alcance
- [ ] `PLUGIN_SYSTEM.md` — cómo se registran Agents/Tools/Capabilities
      nuevas sin tocar el core

### Hito 5
- [ ] `SDK.md` — cómo construir sobre la plataforma desde fuera

---

## Fase 1 — Implementación del núcleo

Una vez cerrado el Hito 3 (Governance + Workflow Engine en diseño):

- [ ] `core/interfaces/task.py` — interfaz Task
- [ ] `core/interfaces/execution_plan.py` — interfaz ExecutionPlan
- [ ] `core/task_engine.py` — ciclo de vida, retries, timeouts,
      idempotencia (implementa `TASK_ENGINE.md`)
- [ ] `core/governance_engine.py` — mínimo viable: Audit Log + RBAC básico
      + Approval Engine (implementa `GOVERNANCE.md`)
- [ ] `core/workflow_engine.py` — resuelve `task_graph`, ejecuta en orden
      respetando dependencias (implementa `WORKFLOW_ENGINE.md`)
- [ ] `core/task_planner.py` — traduce Intent → Execution Plan
- [ ] `core/supervisor.py` — punto de entrada único

## Fase 2 — Refactor de lo existente sobre el nuevo núcleo

- [ ] Reorganizar `tools/vcs/github/github_tool.py` en servicios
      (`RepositoryService`, `BranchService`, `IssueService`,
      `PullRequestService`, `ActionsService`) sin romper su interfaz
      pública `execute()`
- [ ] Refactorizar `agents/founder_agent.py` para que ejecute Tasks
      individuales en vez de orquestar su propio flujo (ver
      `TASK_ENGINE.md §11`)
- [ ] Migrar la memoria actual (`core/memory_manager.py`, ya construida y
      probada) a Project Memory dentro del nuevo modelo de 4 tipos

## Fase 3 — Segundo y tercer agente

- [ ] Cloud Architect Agent (AWS Tool real con boto3)
- [ ] DevOps Agent (Kubernetes Tool, Terraform Tool)
- [ ] Revisar si en este punto ya es necesario el Resource Model
      (ver Future Work — disparador: "al implementar el segundo Agent")

## Fase 4 — Superficie expuesta
- [ ] CLI (`lra start`, `lra init`, `lra status`)
- [ ] API REST inicial (sin separación Internal/External todavía)
- [ ] Dashboard mínimo (Execution Plans, Tasks pendientes de aprobación,
      Audit Log)

## Fase 5 — Resto de agentes y tools
- [ ] Security Agent (Trivy, Checkov, tfsec, Snyk)
- [ ] SRE Agent (Prometheus, Grafana, CloudWatch)
- [ ] OpenShift Agent
- [ ] Documentation Agent
- [ ] Reviewer Agent
- [ ] Resto del catálogo de Tools (Ansible, Jenkins, ArgoCD, SonarQube...)

---

## Future Work

Componentes identificados como valiosos pero deliberadamente pospuestos
(razonamiento completo en `ADR-003`). Cada uno tiene un disparador
explícito — no son "algún día", son "cuando ocurra X, retomar esto":

| Componente | Disparador para retomarlo |
|---|---|
| **Resource Model** (Repository, VPC, EKS, Namespace, Deployment, Database, Bucket como objetos propios) | Al implementar el segundo Agent (Fase 3) — cuando dos Agents puedan operar sobre el mismo recurso compartido |
| **Resource Inventory** (qué recursos existen por proyecto, sin que cada Agent los redescubra) | Junto con Resource Model |
| **State Store dedicado** (en vez de JSON en disco vía `MemoryManager`) | Cuando se necesite ejecución distribuida (más de un proceso de la plataforma corriendo a la vez) |
| **Scheduler** (tareas programadas: backups diarios, escaneos semanales) | Cuando exista un caso de uso real, no antes |
| **Queue Manager** (cola de Tasks para alta concurrencia) | Cuando se observe contención real con Workflow Engine + Governance ya funcionando |
| **Separación Internal API / External API** | Al construir la API REST (Fase 4) |
| **Separación explícita Capability vs Action** (ej. Capability=GitHub, Action=create_repository) | Se evalúa al implementar `PLUGIN_SYSTEM.md`, si la granularidad actual de Capability resulta insuficiente en la práctica |

---

## Principio rector (no cambia)

> "Los agentes no son el centro del sistema. Son especialistas que ejecutan
> Tasks dentro de un flujo gobernado."

Toda decisión de este roadmap se evalúa contra este principio antes de
añadirse.
