# agents/founder_agent.py
# Founder Agent — v2.0, arquitectura Task-céntrica (TASK_ENGINE.md §11)
# Ejecuta Tasks individuales asignadas por el WorkflowEngine.
# Ya no orquesta su propio flujo — solo recibe y ejecuta una Task a la vez.

from core.interfaces.agent import Agent
from core.interfaces.task import Task, TaskStatus


class FounderAgent(Agent):
    """
    Founder Agent de LRA AI Platform — v2.0

    Especialidad: inicialización de proyectos nuevos.
    Ejecuta Tasks individuales del dominio de creación de proyectos.

    Tasks que sabe ejecutar:
        create_repository      → crea un repo en GitHub
        generate_documentation → genera README, ARCHITECTURE, ROADMAP
        create_file            → crea un archivo en un repo
        list_projects          → lista repos de la organización

    Tools que usa:
        - github → crear repo, crear archivos, listar repos
    """

    # Mapa de tipo de Task a método interno
    _TASK_HANDLERS = [
        "create_repository",
        "generate_documentation",
        "create_file",
        "list_projects",
    ]

    def execute_task(self, task: Task) -> dict:
        """
        Ejecuta una Task individual asignada por el WorkflowEngine.
        Ver TASK_ENGINE.md §11 — el Agent ya no decide el flujo,
        solo ejecuta la Capability indicada en task.capability o task.type.
        """
        handlers = {
            "create_repository":     self._create_repository,
            "generate_documentation": self._generate_documentation,
            "create_file":           self._create_file,
            "list_projects":         self._list_projects,
        }

        handler = handlers.get(task.type)
        if handler is None:
            raise ValueError(
                f"FounderAgent does not handle task type '{task.type}'. "
                f"Supported: {list(handlers.keys())}"
            )

        return handler(task.params)

    def run(self, task: str, context: dict = {}) -> dict:
        """
        Compatibilidad v1.0 — mantiene el método run() para no romper
        scripts o pruebas existentes. Internamente delega a execute_task().
        """
        from core.interfaces.task import Task
        t = Task(type=task.replace(" ", "_"), params=context, assigned_to="founder")
        return self.execute_task(t)

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tools": list(self.tools.keys()),
            "supported_tasks": self._TASK_HANDLERS,
        }

    # --- Implementaciones de cada Task ---

    def _create_repository(self, params: dict) -> dict:
        """Crea un repositorio en GitHub."""
        github = self.get_tool("github")
        result = github.execute("create_repo", {
            "name": params.get("name"),
            "description": params.get("description", ""),
            "org": params.get("org", "lra-cloud-ops"),
            "private": params.get("private", False),
        })
        print(f"[FounderAgent] Repository created: {result.get('url')}")
        return result

    def _generate_documentation(self, params: dict) -> dict:
        """Genera README, ARCHITECTURE y ROADMAP en el repo."""
        github = self.get_tool("github")
        name = params.get("name")
        org  = params.get("org", "lra-cloud-ops")
        desc = params.get("description", "")
        stack = params.get("stack", [])
        results = {}

        docs = {
            "README.md":       self._build_readme(name, desc, stack),
            "ARCHITECTURE.md": self._build_architecture(name, desc, stack),
            "ROADMAP.md":      self._build_roadmap(name),
        }

        for path, content in docs.items():
            results[path] = github.execute("create_file", {
                "repo": name, "org": org, "path": path,
                "content": content, "message": f"docs: add {path}",
            })
            print(f"[FounderAgent] {path} created.")

        return results

    def _create_file(self, params: dict) -> dict:
        """Crea un archivo arbitrario en un repo."""
        github = self.get_tool("github")
        return github.execute("create_file", params)

    def _list_projects(self, params: dict) -> dict:
        """Lista repos de la organización."""
        github = self.get_tool("github")
        return github.execute("list_repos", {
            "org": params.get("org", "lra-cloud-ops")
        })

    # --- Generadores de documentación ---

    def _build_readme(self, name: str, description: str, stack: list) -> str:
        stack_section = "\n".join(f"- {s}" for s in stack) if stack else "- TBD"
        return f"""# {name}

{description}

## Overview

This project is part of the **LRA CloudOps** organization and is managed
by **LRA AI Platform**.

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

---
*Generated by LRA AI Platform — Founder Agent v2.0*
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

## ADR (Architecture Decision Records)

- ADR-001: Initial architecture definition

---
*Generated by LRA AI Platform — Founder Agent v2.0*
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
*Generated by LRA AI Platform — Founder Agent v2.0*
"""