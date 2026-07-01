# LRA AI Platform

> **AI-Assisted Engineering Platform for DevOps, Platform Engineering and Cloud Operations**

LRA AI Platform is an enterprise-grade multi-agent platform that enables DevOps and Platform
Engineering teams to design, provision, deploy, review, and document infrastructure projects
using AI-powered agents with real tool integrations.

Built by **[Ruben Liquenson](https://www.linkedin.com/in/ruben-liquenson-490961269/)** —
DevOps Engineer | Cloud Engineer | AWS | Kubernetes | Terraform | GitOps
at [LRA CloudOps](https://github.com/lra-cloud-ops) — Las Palmas de Gran Canaria, España.

---

## Quick Start

### Installation

```bash
git clone https://github.com/lra-cloud-ops/lra-ai-platform.git
cd lra-ai-platform
pip install -r requirements.txt
cp .env.example .env
# Add your GITHUB_TOKEN to .env
```

### CLI

```bash
python cli/lra.py status
python cli/lra.py review aws
python cli/lra.py review multicloud
python cli/lra.py plan "Crea un proyecto nuevo llamado client-api"
python cli/lra.py init "Crea un proyecto nuevo llamado client-api"
python cli/lra.py agents
python cli/lra.py tools
python cli/lra.py memory lracloudops
```

### API REST

```bash
python api/app.py
# Docs: http://localhost:8000/docs
```

---

## Architecture

Task-centric: agents execute Tasks, they don't own the flow.

```
Intent → Supervisor → TaskPlanner → ExecutionPlan
                                         │
                                   WorkflowEngine (DAG, parallelism)
                                         │
                                   GovernanceEngine (RBAC, Policy, Audit)
                                         │
                                   TaskEngine (retry, timeout, idempotency)
                                         │
                                   Agent.execute_task()
                                         │
                                   Tool → Provider (AWS, GitHub, kubectl...)
```

---

## What's Built

### Agents

| Agent | Status | Tools |
|---|---|---|
| Founder Agent | ✅ Live | github |
| Cloud Architect | ✅ Live | aws, azure, gcp |
| DevOps Engineer | ✅ Live | terraform, kubernetes, ansible |
| Security Engineer | 📋 Defined | trivy, checkov, vault, snyk |
| SRE | 📋 Defined | prometheus, grafana, aws |
| OpenShift Agent | 📋 Defined | openshift, kubernetes |
| Documentation | 📋 Defined | github |
| Reviewer | 📋 Defined | github, trivy |

### Tools (Live)

| Tool | Integration |
|---|---|
| GitHub | PyGithub → repos, PRs, files, issues |
| AWS | boto3 → S3, EC2, EKS, ECR, VPC, IAM, CloudWatch |
| Azure | azure-sdk → VMs, VNets, AKS, ACR, Storage |
| GCP | gcloud CLI → GCE, GCS, GKE, VPC, Cloud Run |
| Terraform | subprocess → init, plan, apply, destroy |
| Kubernetes | kubectl → pods, deployments, scale, logs |
| Ansible | WSL2 → playbooks, ad-hoc, vault |

### Surface

| Interface | Description |
|---|---|
| `lra status` | Platform health |
| `lra review aws/azure/gcp/multicloud` | Live infrastructure review |
| `lra plan <intent>` | Generate Execution Plan |
| `lra init <intent>` | Create project end-to-end |
| `GET /api/v1/platform/status` | REST status |
| `GET /api/v1/cloud/review/{cloud}` | REST cloud review |
| `POST /api/v1/projects/plan` | REST plan generation |

### Memory (4 types)

| Type | Scope |
|---|---|
| OrganizationMemory | All projects (naming, region, modules) |
| ProjectMemory | One project (stack, team, last deploy) |
| WorkflowMemory | One Execution Plan in progress |
| ConversationMemory | Current session |

Resolution: **Conversation > Workflow > Project > Organization**

---

## Governance

```
Levels: READ_ONLY → PROPOSE → DEVELOPMENT → PRODUCTION → ADMIN
Policy:
  production: requires [security_scan, approval, architecture_review]
  development: requires []
Fail-safe: any internal error → DENY (never auto-approve)
```

---

## Roadmap

| Phase | Status |
|---|---|
| Phase 0 — Design (11 docs + 4 ADRs) | ✅ Complete |
| Phase 1 — Core Engine | ✅ Complete |
| Phase 2 — Memory (4 types) | ✅ Complete |
| Phase 3 — Multi-cloud + DevOps Agent | ✅ Complete |
| Phase 4 — CLI + REST API | ✅ Complete |
| Phase 5 — Security, SRE, OpenShift, Docs, Reviewer Agents | 🔄 Next |
| Phase 6 — Dashboard | 📋 Planned |

---

## Tech Stack

Python 3.11+, FastAPI, Click, boto3, azure-sdk, gcloud, kubectl, terraform, Ansible (WSL2), PyGithub, PyYAML

Design: Task-centric, Pub/Sub EventBus, lazy loading, Plugin system, ADR-documented, BaseCloudTool abstraction

---

## Author

**Ruben Liquenson** — DevOps Engineer | Cloud Engineer | AWS | Kubernetes | Terraform | GitOps

- Las Palmas de Gran Canaria, Canarias, España
- LinkedIn: [ruben-liquenson](https://www.linkedin.com/in/ruben-liquenson-490961269/)
- GitHub: [@Liquenson](https://github.com/Liquenson)
- Org: [lra-cloud-ops](https://github.com/lra-cloud-ops)

---

*LRA AI Platform — where Platform Engineering meets AI-assisted automation.*
