# agents/founder_agent.py
# Founder Agent — inicializa proyectos nuevos en LRA CloudOps.
# Es el primer agente que trabaja cuando se crea un proyecto desde cero.

from core.interfaces.agent import Agent
from core.event_bus import Event


class FounderAgent(Agent):
    """
    Founder Agent de LRA AI Platform.

    Responsabilidades:
        1. Descubrir requisitos del proyecto
        2. Diseñar la estructura de carpetas
        3. Crear el repositorio en GitHub
        4. Generar documentación base (README, ARCHITECTURE, ROADMAP)
        5. Registrar el proyecto en la memoria de la plataforma

    Tools que usa:
        - github → crear repo, crear archivos, crear ramas
        - linux  → operaciones de sistema de archivos (futuro)

    Uso:
        founder = FounderAgent(name="Founder Agent", role="Project Initializer", description="...")
        founder.register_tool(github_tool)
        founder.run("init project", {
            "name": "observability-platform",
            "description": "Plataforma de observabilidad con Prometheus y Grafana",
            "org": "lra-cloud-ops",
            "stack": ["Prometheus", "Grafana", "Loki", "Tempo"],
            "private": False
        })
    """

    def run(self, task: str, context: dict = {}) -> dict:
        """
        Ejecuta una tarea de inicialización de proyecto.

        Tareas soportadas:
            "init project"     → crea repo + estructura + documentación
            "create repo"      → solo crea el repositorio
            "generate docs"    → solo genera la documentación base
            "list projects"    → lista repos de la organización
        """
        print(f"\n[FounderAgent] Starting task: '{task}'")

        tasks = {
            "init project":  self._init_project,
            "create repo":   self._create_repo,
            "generate docs": self._generate_docs,
            "list projects": self._list_projects,
        }

        if task not in tasks:
            return {
                "error": f"Task '{task}' not supported.",
                "available_tasks": list(tasks.keys())
            }

        result = tasks[task](context)
        print(f"[FounderAgent] Task '{task}' completed.")
        return result

    def get_status(self) -> dict:
        """Retorna el estado actual del agente."""
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tools": list(self.tools.keys()),
        }

    def _init_project(self, context: dict) -> dict:
        """
        Inicializa un proyecto completo desde cero.
        Crea el repo y genera toda la documentación base.
        """
        name        = context.get("name")
        description = context.get("description", "")
        org         = context.get("org", "lra-cloud-ops")
        stack       = context.get("stack", [])
        private     = context.get("private", False)

        if not name:
            return {"error": "Project name is required."}

        print(f"[FounderAgent] Initializing project: {name}")
        results = {}

        # 1. Crear el repositorio
        print(f"[FounderAgent] Creating repository {org}/{name}...")
        github = self.get_tool("github")
        repo_result = github.execute("create_repo", {
            "name": name,
            "description": description,
            "org": org,
            "private": private,
        })
        results["repo"] = repo_result
        print(f"[FounderAgent] Repository created: {repo_result.get('url')}")

        # 2. Generar documentación base
        print(f"[FounderAgent] Generating base documentation...")
        docs_result = self._generate_docs({
            "name": name,
            "description": description,
            "org": org,
            "stack": stack,
        })
        results["docs"] = docs_result

        return {
            "project": name,
            "org": org,
            "url": repo_result.get("url"),
            "results": results,
            "status": "initialized",
        }

    def _create_repo(self, context: dict) -> dict:
        """Crea únicamente el repositorio en GitHub."""
        github = self.get_tool("github")
        return github.execute("create_repo", {
            "name": context.get("name"),
            "description": context.get("description", ""),
            "org": context.get("org", "lra-cloud-ops"),
            "private": context.get("private", False),
        })

    def _generate_docs(self, context: dict) -> dict:
        """
        Genera la documentación base del proyecto:
            - README.md
            - ARCHITECTURE.md
            - ROADMAP.md
        """
        github  = self.get_tool("github")
        name    = context.get("name")
        desc    = context.get("description", "")
        org     = context.get("org", "lra-cloud-ops")
        stack   = context.get("stack", [])
        results = {}

        # README.md
        readme = self._build_readme(name, desc, stack)
        results["README"] = github.execute("create_file", {
            "repo": name,
            "org": org,
            "path": "README.md",
            "content": readme,
            "message": "docs: add README.md",
        })
        print(f"[FounderAgent] README.md created.")

        # ARCHITECTURE.md
        architecture = self._build_architecture(name, desc, stack)
        results["ARCHITECTURE"] = github.execute("create_file", {
            "repo": name,
            "org": org,
            "path": "ARCHITECTURE.md",
            "content": architecture,
            "message": "docs: add ARCHITECTURE.md",
        })
        print(f"[FounderAgent] ARCHITECTURE.md created.")

        # ROADMAP.md
        roadmap = self._build_roadmap(name)
        results["ROADMAP"] = github.execute("create_file", {
            "repo": name,
            "org": org,
            "path": "ROADMAP.md",
            "content": roadmap,
            "message": "docs: add ROADMAP.md",
        })
        print(f"[FounderAgent] ROADMAP.md created.")

        return results

    def _list_projects(self, context: dict) -> dict:
        """Lista todos los repositorios de la organización."""
        github = self.get_tool("github")
        org = context.get("org", "lra-cloud-ops")
        return github.execute("list_repos", {"org": org})

    # --- Generadores de documentación ---

    def _build_readme(self, name: str, description: str, stack: list) -> str:
        stack_section = "\n".join(f"- {s}" for s in stack) if stack else "- TBD"
        return f"""# {name}

{description}

## Overview

This project is part of the **LRA CloudOps** organization and is managed by **LRA AI Platform**.

## Tech Stack

{stack_section}

## Getting Started

```bash
git clone https://github.com/lra-cloud-ops/{name}.git
cd {name}
```

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)

## Team

**LRA CloudOps** — Ruben Liquenson, Kelvin Osaigbovo, Darwin Pochet

---
*Generated by LRA AI Platform — Founder Agent*
"""

    def _build_architecture(self, name: str, description: str, stack: list) -> str:
        stack_section = "\n".join(f"- {s}" for s in stack) if stack else "- TBD"
        return f"""# Architecture — {name}

## Overview

{description}

## Tech Stack

{stack_section}

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| TBD | TBD |

## Architecture Diagram

## ADR (Architecture Decision Records)

- ADR-001: Initial architecture definition

---
*Generated by LRA AI Platform — Founder Agent*
"""

    def _build_roadmap(self, name: str) -> str:
        return f"""# Roadmap — {name}

## Phase 1 — Foundation
- [ ] Initial setup
- [ ] Core infrastructure
- [ ] Basic documentation

## Phase 2 — Development
- [ ] Core features
- [ ] Testing
- [ ] CI/CD pipeline

## Phase 3 — Production
- [ ] Security hardening
- [ ] Monitoring and observability
- [ ] Production deployment

---
*Generated by LRA AI Platform — Founder Agent*
"""