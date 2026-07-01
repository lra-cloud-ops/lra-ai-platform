# LRA AI Platform

> **AI-Assisted Engineering Platform for DevOps, Platform Engineering and Cloud Operations**

LRA AI Platform is an enterprise-grade multi-agent platform that enables DevOps and Platform
Engineering teams to design, provision, deploy, review, and document infrastructure projects
using AI-powered agents with real tool integrations.

Built by **[Ruben Liquenson](https://www.linkedin.com/in/ruben-liquenson-490961269/)** —
DevOps Engineer | Cloud Engineer | AWS | Kubernetes | Terraform | GitOps
at [LRA CloudOps](https://github.com/lra-cloud-ops) — Las Palmas de Gran Canaria, España.

---

## What It Does

```
You:      "Crea un proyecto nuevo llamado client-api"

Platform: Execution Plan:
            1. create_repository    → Founder Agent    → GitHub API
            2. generate_documentation → Founder Agent  → README + ARCHITECTURE + ROADMAP

          Execute? [y/N]: y

          ✓ Repository created: github.com/lra-cloud-ops/client-api
          ✓ README.md, ARCHITECTURE.md, ROADMAP.md generated
```

What normally takes hours, the platform delivers in seconds — following your own standards.

---

## Quick Start

### Requirements

- Python 3.11+
- AWS CLI, Azure CLI, gcloud CLI configured
- WSL2 (for Ansible on Windows)

### Installation

```bash
git clone https://github.com/lra-cloud-ops/lra-ai-platform.git
cd lra-ai-platform
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your credentials
```

### Start the Platform

**Option A — Terminal (development, live logs)**
```bash
# Terminal 1
python api/app.py

# Then open dashboard in browser
start dashboard/index.html   # Windows
# or open dashboard/index.html manually
```

**Option B — Docker (production/demo, runs in background)**
```bash
docker-compose up -d
# API:       http://localhost:8000
# Dashboard: http://localhost:3001
```

**Stop the platform**
```bash
# Terminal
Ctrl+C

# Docker
docker-compose down
```

> Note: do not run both options at the same time — both use port 8000.

### CLI

```bash
make status                                              # Platform health
make review                                              # Multi-cloud review
python cli/lra.py init "Crea un proyecto llamado X"     # Create project
python cli/lra.py plan "escanea seguridad"              # Generate plan
python cli/lra.py review aws                             # AWS infrastructure
python cli/lra.py agents                                 # List agents
python cli/lra.py workflows                              # List workflows
```

### Optional — Set up alias

```bash
# Add to ~/.bashrc
alias lra="python /c/Users/lique/workspace/lra-ai-platform/cli/lra.py"
source ~/.bashrc

# Then use directly
lra status
lra review aws
lra init "Crea un proyecto llamado X"
```

---

## Analyze Projects

### Local project → save docs locally
```python
from agents.documentation_agent import DocumentationAgent
from tools.local.local_tool import LocalTool
from core.interfaces.task import Task

agent = DocumentationAgent(name='docs', role='writer', description='')
agent.register_tool(LocalTool())

task = Task(
    type='analyze_local_project',
    params={
        'path': 'C:/Users/lique/workspace/mi-proyecto',
        'save': True,
        'save_to': 'local',
    },
    assigned_to='documentation'
)
result = agent.execute_task(task)
```

### Local project → save docs to GitHub
```python
task = Task(
    type='analyze_local_project',
    params={
        'path': 'C:/Users/lique/workspace/mi-proyecto',
        'save': True,
        'save_to': 'github',
        'repo': 'mi-repo',
        'org': 'lra-cloud-ops',
    },
    assigned_to='documentation'
)
```

### GitHub repo → analyze and save docs
```python
from agents.documentation_agent import DocumentationAgent
from tools.vcs.github.github_tool import GitHubTool
from core.interfaces.task import Task

agent = DocumentationAgent(name='docs', role='writer', description='')
agent.register_tool(GitHubTool())

task = Task(
    type='analyze_repository',
    params={
        'repo': 'aws-terraform-devops-lab',
        'org': 'lra-cloud-ops',
        'save': True,
    },
    assigned_to='documentation'
)
result = agent.execute_task(task)
```

---

## Architecture

Task-centric: agents execute Tasks, they never orchestrate directly.

```
Intent (text)
    │
    ▼
Supervisor → TaskPlanner → ExecutionPlan (DAG)
                                │
                          WorkflowEngine
                          (topological sort, parallelism)
                                │
                          GovernanceEngine
                          (RBAC 5 levels, Policy, Audit)
                                │
                          TaskEngine
                          (retry, timeout, idempotency)
                                │
                          Agent.execute_task()
                                │
                          Tool → Provider
                          (GitHub, AWS, kubectl, Terraform...)
```

Key design decisions documented in [`docs/adr/`](docs/adr/).

---

## Agents (8)

| Agent | Speciality | Tools |
|---|---|---|
| **Founder Agent** ✅ | Creates repos, generates docs | github |
| **Cloud Architect** ✅ | Reviews AWS/Azure/GCP infrastructure | aws, azure, gcp, github |
| **DevOps Engineer** ✅ | Terraform, Kubernetes, Ansible | terraform, kubernetes, ansible, github |
| **Security Engineer** ✅ | Vulnerability and IaC scanning | trivy, checkov, github |
| **SRE** ✅ | Observability, alerts, reliability | cloudwatch, prometheus, grafana |
| **OpenShift Agent** ✅ | OC CLI, Operators, Pipelines | openshift, kubernetes, github |
| **Documentation Agent** ✅ | README, ADR, Runbooks, local + GitHub | github, local |
| **Reviewer Agent** ✅ | PR review, code quality, security | github, trivy, checkov |

---

## Tools (14 live integrations)

| Tool | Status | Integration |
|---|---|---|
| GitHub | ✅ Live | PyGithub → repos, PRs, files, issues |
| AWS | ✅ Live | boto3 → S3, EC2, EKS, ECR, VPC, IAM, CloudWatch |
| Azure | ✅ Live | azure-sdk → VMs, VNets, AKS, ACR, Storage |
| GCP | ✅ Live | gcloud CLI → GCE, GCS, GKE, VPC, Cloud Run |
| Terraform | ✅ Live | subprocess → init, plan, apply, destroy |
| Kubernetes | ✅ Live | kubectl → pods, deployments, scale, logs |
| Ansible | ✅ Live | WSL2 → playbooks, ad-hoc, vault |
| Trivy | ✅ Live | subprocess → image, fs, k8s, terraform scans |
| Checkov | ✅ Live | python -m → terraform, k8s, dockerfile, gha |
| CloudWatch | ✅ Live | boto3 → alarms, metrics, logs |
| Prometheus | ✅ Live | HTTP API → query, alerts, targets |
| Grafana | ✅ Live | HTTP API → dashboards, health, alerts |
| OpenShift | ✅ Live | oc CLI → projects, deployments, operators |
| Local | ✅ Live | filesystem → analyze, detect stack, save files |

---

## Workflows (8)

| Workflow | Agents | Tasks |
|---|---|---|
| `create_project` | Founder | create_repository → generate_documentation |
| `full_project_setup` | Founder + Security + SRE | repo + docs + security scan + alarms |
| `deploy_eks` | DevOps | tf init → tf plan → tf apply → k8s nodes |
| `infrastructure_review` | CloudArchitect + SRE | multicloud review → alarms → SRE report |
| `security_review` | Security + Reviewer | scan repo → list PRs → security report |
| `openshift_deploy` | OpenShift | get projects → create → deploy → expose |
| `documentation_update` | Documentation | analyze repo → ADR → changelog |
| `pr_review` | Reviewer | security scan → quality check → review report |

---

## CLI Commands

| Command | Description |
|---|---|
| `lra status` | Platform health (agents, tools, workflows) |
| `lra agents` | List all agents with roles and tools |
| `lra tools` | List tools by category |
| `lra workflows` | List registered workflow templates |
| `lra plan <intent>` | Generate Execution Plan without executing |
| `lra init <intent>` | Create project end-to-end |
| `lra review aws\|azure\|gcp\|multicloud` | Live infrastructure review |
| `lra memory <project>` | Show org defaults + project context |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/docs` | Interactive API documentation |
| GET | `/api/v1/platform/status` | Platform status |
| GET | `/api/v1/platform/agents` | List agents |
| GET | `/api/v1/platform/tools` | List tools |
| GET | `/api/v1/platform/audit` | Audit log |
| GET | `/api/v1/cloud/review/{cloud}` | Cloud infrastructure review |
| GET | `/api/v1/cloud/aws/s3` | List S3 buckets |
| GET | `/api/v1/cloud/aws/vpcs` | List VPCs |
| POST | `/api/v1/projects/plan` | Generate Execution Plan |
| POST | `/api/v1/projects/execute` | Execute a plan |

---

## Governance Model

Every Task passes through GovernanceEngine before execution.
**Fail-safe: deny by default on any internal error.**

```
Permission Levels:
  1 - READ_ONLY    → list repos, read metrics
  2 - PROPOSE      → create PRs, generate docs
  3 - DEVELOPMENT  → commits, deploy to dev (default)
  4 - PRODUCTION   → deploy to production (requires approval)
  5 - ADMIN        → modify agents, tools, policies
```

---

## Memory System (4 types)

| Type | Scope | Persistence |
|---|---|---|
| `OrganizationMemory` | All projects | JSON on disk |
| `ProjectMemory` | One project | JSON on disk |
| `WorkflowMemory` | One Execution Plan | JSON, archived on completion |
| `ConversationMemory` | Current session | RAM only |

Resolution hierarchy: **Conversation > Workflow > Project > Organization**

---

## Tests

```bash
make test
# 33 tests in 0.14s — TaskPlanner, GovernanceEngine, all 8 Agents
```

---

## CI/CD

Every push to `main` triggers:
- **Lint** → flake8 + YAML validation + Python syntax check
- **Structure** → verifies all required files and agents exist
- **Tests** → pytest 33 tests
- **Security** → Trivy filesystem scan + Checkov IaC scan

---

## Project Structure

```
lra-ai-platform/
├── agents/                    # 8 Agent implementations
├── api/                       # REST API (FastAPI)
│   └── routes/                # platform, projects, cloud
├── cli/lra.py                 # CLI (Click)
├── config/
│   ├── agents.yaml            # 8 agents configured
│   ├── tools.yaml             # 14 live tools + catalogued
│   ├── config.yaml            # Platform configuration
│   └── workflows/             # 8 workflow templates
├── core/
│   ├── interfaces/            # Tool, Agent, Task, ExecutionPlan contracts
│   ├── memory/                # 4 memory types + MemoryResolver
│   ├── governance_engine.py   # RBAC, Policy, Approval, Audit
│   ├── task_engine.py         # Lifecycle, retry, timeout, idempotency
│   ├── workflow_engine.py     # DAG execution, parallelism
│   ├── task_planner.py        # Intent → ExecutionPlan
│   └── supervisor.py          # Single entry point
├── dashboard/index.html       # Web dashboard
├── docs/                      # 11 design docs + 4 ADRs
├── tests/                     # 33 tests
├── tools/                     # 14 live tool integrations
│   ├── cloud/                 # AWS, Azure, GCP + BaseCloudTool
│   ├── containers/            # Kubernetes, OpenShift
│   ├── iac/                   # Terraform, Ansible
│   ├── local/                 # Local filesystem analysis
│   ├── observability/         # CloudWatch, Prometheus, Grafana
│   ├── security/              # Trivy, Checkov
│   └── vcs/                   # GitHub
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Makefile Commands

```bash
make install    # Install dependencies
make run        # Start API server
make status     # Platform status
make review     # Multi-cloud review
make test       # Run 33 tests
make lint       # Run flake8
make security   # Security scan plan
make clean      # Remove cache
```

---

## Tech Stack

**Platform:** Python 3.11+, FastAPI, Uvicorn, Click, PyYAML, python-dotenv

**Cloud SDKs:** boto3 (AWS), azure-sdk-for-python (Azure), gcloud CLI (GCP)

**DevOps Tools:** Terraform v1.15+, kubectl v1.35+, Ansible v2.10+ (WSL2), oc v4.22+

**Security:** Trivy v0.69+, Checkov v3.3+

**Observability:** CloudWatch (boto3), Prometheus HTTP API, Grafana HTTP API

**VCS:** PyGithub

**Design:** Task-centric architecture, Pub/Sub EventBus, Lazy loading,
Plugin system, ADR-documented decisions, Fail-safe Governance,
BaseCloudTool abstraction for multi-cloud extensibility

---

## Organization

Part of **[LRA CloudOps](https://github.com/lra-cloud-ops)**

| Repository | Description |
|---|---|
| [lra-ai-platform](https://github.com/lra-cloud-ops/lra-ai-platform) | This platform |
| [aws-terraform-devops-lab](https://github.com/lra-cloud-ops/aws-terraform-devops-lab) | AWS + Terraform + EKS lab |
| [k8s-devops-platform](https://github.com/lra-cloud-ops/k8s-devops-platform) | Kubernetes + GitOps |
| [k8s-on-premise](https://github.com/lra-cloud-ops/k8s-on-premise) | Bare metal K8s with Vagrant |

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
