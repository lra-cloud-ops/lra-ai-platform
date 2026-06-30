# LRA AI Platform

> **AI-Assisted Engineering Platform for DevOps, Platform Engineering and Cloud Operations**

LRA AI Platform is an enterprise-grade multi-agent platform that enables DevOps and Platform
Engineering teams to design, provision, deploy, review, and document infrastructure projects
using AI-powered agents with real tool integrations.

Built by **[Ruben Liquenson](https://www.linkedin.com/in/ruben-liquenson-490961269/)** —
DevOps Engineer | Cloud Engineer | AWS | Kubernetes | Terraform | GitOps at [LRA CloudOps](https://github.com/lra-cloud-ops).

---

## The Problem It Solves

Setting up a new project from scratch — repo, infrastructure, CI/CD, observability,
documentation — normally takes a full day of manual work, repeated identically every time.

LRA AI Platform automates that flow end-to-end, with enterprise controls:

```
You:      "Create a new project called client-api with EKS and CI/CD"

Platform: Execution Plan:
            1. create_repository    → Founder Agent
            2. provision_vpc        → Cloud Architect Agent  (coming Phase 3)
            3. provision_eks        → Cloud Architect Agent  (coming Phase 3)
            4. setup_cicd           → DevOps Agent           (coming Phase 3)
            5. configure_monitoring → SRE Agent              (coming Phase 5)

          Requires approval? No (development environment)
          Execute? [yes/no]

          ✓ Repository created: github.com/lra-cloud-ops/client-api
          ✓ README.md, ARCHITECTURE.md, ROADMAP.md generated
```

What normally takes a day, the platform delivers in minutes — following your own standards.

---

## Architecture

The platform is built around a **Task-centric architecture** (not agent-centric). Agents are
specialists that execute Tasks; they don't own the flow.

```
Intent (text)
    │
    ▼
Supervisor ──► TaskPlanner ──► ExecutionPlan (task graph)
                                    │
                                    ▼
                              WorkflowEngine
                              (topological sort, parallelism)
                                    │
                              For each Task:
                                    │
                                    ▼
                              GovernanceEngine
                              (RBAC, Policy, Approval, Audit)
                                    │
                                    ▼
                              TaskEngine
                              (retry, timeout, idempotency)
                                    │
                                    ▼
                              Agent.execute_task()
                                    │
                                    ▼
                              Capability → Tool → Provider
                              (GitHub, AWS, kubectl, Terraform...)
```

Key design decisions are documented in [`docs/adr/`](docs/adr/).

---

## What's Built (v1.0)

### Core Engine

| Component | File | Description |
|---|---|---|
| Task | `core/interfaces/task.py` | Atomic unit of work with full lifecycle, retries, timeout, idempotency |
| ExecutionPlan | `core/interfaces/execution_plan.py` | DAG of Tasks with cycle detection and topological sort |
| GovernanceEngine | `core/governance_engine.py` | RBAC (5 levels), PolicyEngine, ApprovalEngine, AuditEngine |
| TaskEngine | `core/task_engine.py` | Lifecycle orchestration, retry with backoff, idempotency cache |
| WorkflowEngine | `core/workflow_engine.py` | Parallel task execution, failure cascade, rollback |
| TaskPlanner | `core/task_planner.py` | Intent → ExecutionPlan via named Workflow templates |
| Supervisor | `core/supervisor.py` | Single entry point: plan → describe → approve → execute |
| MemoryManager | `core/memory_manager.py` | Facade for all 4 memory types |

### Memory System (4 types)

| Type | Scope | Persistence |
|---|---|---|
| `OrganizationMemory` | All LRA CloudOps projects | JSON on disk |
| `ProjectMemory` | One project (lracloudops, client-api...) | JSON on disk |
| `WorkflowMemory` | One Execution Plan in progress | JSON, archived on completion |
| `ConversationMemory` | Current chat session | RAM only |

Resolution hierarchy: **Conversation > Workflow > Project > Organization**

### Tools (1 implemented, 20+ catalogued)

| Tool | Status | Actions |
|---|---|---|
| GitHub | ✅ Implemented | create_repo, create_branch, create_pr, get_file, create_file, list_repos... |
| AWS | 📋 Catalogued | create_eks, create_vpc, create_s3, deploy_lambda... |
| Kubernetes | 📋 Catalogued | apply_manifest, get_pods, scale_deployment, get_logs... |
| Terraform | 📋 Catalogued | init, plan, apply, destroy, validate... |
| Ansible | 📋 Catalogued | run_playbook, run_adhoc, encrypt_vault... |
| OpenShift | 📋 Catalogued | create_project, deploy_app, install_operator... |
| + 15 more | 📋 Catalogued | Jenkins, ArgoCD, SonarQube, Trivy, Vault, Prometheus... |

### Agents (1 implemented, 8 defined)

| Agent | Status | Speciality |
|---|---|---|
| Founder Agent | ✅ Implemented | Creates repos, generates README/ARCHITECTURE/ROADMAP |
| Cloud Architect | 📋 Defined | AWS/Azure/GCP architecture, Terraform |
| DevOps Engineer | 📋 Defined | Docker, Kubernetes, Helm, CI/CD, ArgoCD |
| Security Engineer | 📋 Defined | Trivy, Checkov, tfsec, Vault |
| SRE | 📋 Defined | Prometheus, Grafana, Loki, CloudWatch |
| OpenShift Agent | 📋 Defined | OC, Operators, Pipelines, GitOps |
| Documentation | 📋 Defined | ADR, Runbooks, Architecture docs |
| Reviewer | 📋 Defined | PR review, code quality, security scan |

---

## Quick Start

### Requirements

- Python 3.11+
- Git
- GitHub account with a Personal Access Token

### Installation

```bash
git clone https://github.com/lra-cloud-ops/lra-ai-platform.git
cd lra-ai-platform
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN
```

### Run

```python
from dotenv import load_dotenv
load_dotenv()

from core.supervisor import Supervisor
from core.governance_engine import PermissionLevel

supervisor = Supervisor.build()

# Check platform status
print(supervisor.status())

# Create a new project
plan, tasks = supervisor.plan(
    "Crea un proyecto nuevo llamado my-service",
    params={"name": "my-service", "org": "lra-cloud-ops"}
)

print(supervisor.describe(plan, tasks))

result = supervisor.execute(
    plan, tasks,
    actor="your.name",
    actor_level=PermissionLevel.DEVELOPMENT,
    environment="development"
)
print(result)
```

---

## Project Structure

```
lra-ai-platform/
├── agents/                    # Agent implementations
│   └── founder_agent.py       ✅ Task-centric v2.0
├── core/
│   ├── interfaces/            # Contracts (Tool, Agent, Capability, Memory, Task, ExecutionPlan)
│   ├── memory/                # 4 memory types + MemoryResolver
│   ├── config_manager.py      # Reads YAML config files
│   ├── tool_manager.py        # Lazy-loads Tools by name
│   ├── agent_manager.py       # Lazy-loads Agents, assigns tools
│   ├── memory_manager.py      # Facade for all memory types
│   ├── event_bus.py           # Pub/Sub for internal events
│   ├── governance_engine.py   # RBAC, Policy, Approval, Audit
│   ├── task_engine.py         # Task lifecycle orchestration
│   ├── workflow_engine.py     # Multi-task DAG execution
│   ├── task_planner.py        # Intent → ExecutionPlan
│   └── supervisor.py          # Single entry point
├── tools/
│   └── vcs/github/            ✅ Real GitHub API integration
├── config/
│   ├── agents.yaml            # 8 agents defined
│   ├── tools.yaml             # 20+ tools catalogued
│   ├── config.yaml            # Platform configuration
│   └── workflows/
│       └── create_project.yaml  ✅ First reusable Workflow template
├── docs/
│   ├── ARCHITECTURE.md        # Full system design
│   ├── TASK_ENGINE.md         # Task contract
│   ├── EXECUTION_PLAN.md      # ExecutionPlan contract
│   ├── GOVERNANCE.md          # RBAC, policies, audit
│   ├── WORKFLOW_ENGINE.md     # Parallel execution design
│   ├── MEMORY.md              # 4 memory types design
│   ├── PLUGIN_SYSTEM.md       # How to add new components
│   ├── SDK.md                 # How to build on the platform
│   ├── ROADMAP.md             # Implementation phases
│   └── adr/                   # Architecture Decision Records
│       ├── ADR-001            # Task as core unit
│       ├── ADR-002            # Governance before execution
│       ├── ADR-003            # Deferred scale components
│       └── ADR-004            # Rule-based Task Planner
└── memory/                    # Runtime project memory (git-ignored)
```

---

## Governance Model

Every Task passes through the GovernanceEngine before execution.
**No Task reaches a Tool without a decision.** On internal error: deny by default.

```
Permission Levels:
  1 - READ_ONLY    → list repos, read metrics, inspect clusters
  2 - PROPOSE      → create PRs, generate docs, propose Terraform
  3 - DEVELOPMENT  → commits, branches, deploy to dev, run tests
  4 - PRODUCTION   → deploy to production (requires human approval)
  5 - ADMIN        → modify agents, tools, policies
```

Policies are declared in YAML per environment, not hardcoded:

```yaml
production:
  requires:
    - security_scan
    - approval
    - architecture_review
development:
  requires: []
```

---

## Roadmap

| Phase | Status | Content |
|---|---|---|
| Phase 0 — Design | ✅ Complete | 11 frozen design documents + 4 ADRs |
| Phase 1 — Core Engine | ✅ Complete | Task, Governance, Workflow, Supervisor, FounderAgent, GitHubTool |
| Phase 2 — Memory | ✅ Complete | 4 memory types + MemoryResolver hierarchy |
| Phase 3 — Agents | 🔄 Next | Cloud Architect (AWS Tool), DevOps Agent |
| Phase 4 — Surface | 📋 Planned | CLI (`lra start`, `lra init`), FastAPI, Dashboard |
| Phase 5 — Agents | 📋 Planned | Security, SRE, OpenShift, Documentation, Reviewer |

Full roadmap with Future Work (Resource Model, State Store, Scheduler): [`docs/ROADMAP.md`](docs/ROADMAP.md)

---

## Tech Stack

**Platform:** Python 3.11+, PyYAML, PyGithub, python-dotenv

**Integrations (live):** GitHub API

**Integrations (catalogued):** AWS (boto3), Kubernetes, Terraform, Ansible, Docker,
Helm, ArgoCD, Jenkins, SonarQube, OpenShift, Trivy, Checkov, Vault, Prometheus,
Grafana, Jira, Slack, VMware, Podman, Vagrant

**Design patterns:** Task-centric architecture, Pub/Sub (EventBus), Lazy loading,
Singleton per component, Plugin system, ADR-documented decisions, Fail-safe Governance

---

## Organization

Part of **[LRA CloudOps](https://github.com/lra-cloud-ops)** — a collection of
DevOps and Platform Engineering projects.

| Repository | Description |
|---|---|
| [lra-ai-platform](https://github.com/lra-cloud-ops/lra-ai-platform) | This platform |
| [aws-terraform-devops](https://github.com/lra-cloud-ops/aws-terraform-devops) | AWS + Terraform lab |
| [k8s-devops-platform](https://github.com/lra-cloud-ops/k8s-devops-platform) | Kubernetes + GitOps |
| [gitops-stack](https://github.com/lra-cloud-ops/gitops-stack) | ArgoCD + Helm |

---

## Author

**Ruben Liquenson** — DevOps Engineer | Cloud Engineer | AWS | Kubernetes | Terraform | GitOps

- 4+ years designing production AWS infrastructure
- Stack: AWS EKS, Terraform, Kubernetes, Ansible, GitHub Actions, ArgoCD, Prometheus/Grafana
- Based in Las Palmas de Gran Canaria, Canarias, España
- LinkedIn: [ruben-liquenson](https://www.linkedin.com/in/ruben-liquenson-490961269/)
- GitHub: [@Liquenson](https://github.com/Liquenson)
- Org: [lra-cloud-ops](https://github.com/lra-cloud-ops)

---

*LRA AI Platform — where Platform Engineering meets AI-assisted automation.*
