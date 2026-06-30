#!/usr/bin/env python3
# cli/lra.py
# CLI de LRA AI Platform — interfaz de línea de comandos.
# Uso: python cli/lra.py <comando>

import click
import json
import sys
import os

# Añadir el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def get_supervisor():
    """Inicializa y retorna el Supervisor de la plataforma."""
    from core.supervisor import Supervisor
    return Supervisor.build()


@click.group()
@click.version_option(version="1.0.0", prog_name="lra")
def cli():
    """
    LRA AI Platform CLI

    Plataforma de ingeniería asistida por IA para DevOps y Platform Engineering.

    Comandos disponibles:

    \b
      lra status              → estado de la plataforma
      lra init <intent>       → crear/inicializar un proyecto
      lra plan <intent>       → generar un execution plan sin ejecutar
      lra review <cloud>      → revisar infraestructura cloud
      lra agents              → listar agentes disponibles
      lra tools               → listar tools disponibles
      lra workflows           → listar workflows disponibles
      lra memory <proyecto>   → ver memoria de un proyecto
    """
    pass


@cli.command()
def status():
    """Muestra el estado actual de la plataforma."""
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho("  LRA AI Platform — Status", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")

    try:
        supervisor = get_supervisor()
        s = supervisor.status()

        click.echo()
        click.secho(f"  Platform:     {s['platform']}", fg="green")
        click.secho(f"  Version:      {s.get('version', '1.0.0')}", fg="green")
        click.secho(f"  Environment:  {s.get('environment', 'development')}", fg="yellow")
        click.echo()

        agents = s.get("agents", {})
        click.secho(f"  Agents:       {agents.get('available_agents', 0)} available", fg="cyan")

        tools = s.get("tools", {})
        click.secho(f"  Tools:        {tools.get('available_tools', 0)} available", fg="cyan")

        workflows = s.get("workflows", [])
        click.secho(f"  Workflows:    {len(workflows)} registered", fg="cyan")

        pending = s.get("pending_approvals", [])
        if pending:
            click.secho(f"  ⚠ Pending approvals: {len(pending)}", fg="yellow", bold=True)
        else:
            click.secho(f"  Approvals:    None pending", fg="green")

        click.echo()
        click.secho("  Status: ✓ Platform running", fg="green", bold=True)

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")

    click.echo()


@cli.command()
@click.argument("intent")
@click.option("--name", "-n", default=None, help="Nombre del proyecto")
@click.option("--org", "-o", default="lra-cloud-ops", help="Organización GitHub")
@click.option("--actor", "-a", default="cli.user", help="Usuario que ejecuta")
@click.option("--env", "-e", default="development", help="Entorno (development/production)")
@click.option("--dry-run", is_flag=True, help="Genera el plan sin ejecutar")
def init(intent, name, org, actor, env, dry_run):
    """
    Inicializa un proyecto nuevo a partir de un intent.

    Ejemplos:

    \b
      lra init "Crea un proyecto nuevo llamado client-api"
      lra init "nuevo proyecto" --name client-api --org lra-cloud-ops
      lra init "Crea una plataforma SaaS" --dry-run
    """
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho("  LRA AI Platform — Init", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")
    click.echo()
    click.secho(f"  Intent: {intent}", fg="white")
    click.echo()

    try:
        from core.governance_engine import PermissionLevel
        supervisor = get_supervisor()

        params = {"org": org}
        if name:
            params["name"] = name

        plan, tasks = supervisor.plan(intent, params)

        if not tasks:
            click.secho("  ✗ No matching workflow for this intent.", fg="red")
            click.echo()
            click.secho("  Available workflows:", fg="yellow")
            for wf in supervisor.task_planner.list_workflows():
                click.secho(f"    - {wf}", fg="white")
            click.echo()
            return

        # Mostrar el plan
        click.secho("  Execution Plan:", fg="cyan", bold=True)
        levels = plan.topological_order()
        for i, level in enumerate(levels):
            for task_id in level:
                task = tasks[task_id]
                parallel = " ⟵ parallel" if len(level) > 1 else ""
                click.secho(f"    {i+1}. {task.type} → {task.assigned_to}{parallel}", fg="white")

        click.echo()
        click.secho(f"  Requires approval: {plan.requires_approval}", fg="yellow")
        click.echo()

        if dry_run:
            click.secho("  [DRY RUN] Plan generated but not executed.", fg="yellow", bold=True)
            click.echo()
            return

        # Confirmar antes de ejecutar
        if not click.confirm("  Execute this plan?"):
            click.secho("  Cancelled.", fg="yellow")
            click.echo()
            return

        click.echo()
        click.secho("  Executing...", fg="cyan")
        click.echo()

        result = supervisor.execute(
            plan, tasks,
            actor=actor,
            actor_level=PermissionLevel.DEVELOPMENT,
            environment=env
        )

        click.echo()
        if result.get("status") == "completed":
            click.secho("  ✓ Plan completed successfully.", fg="green", bold=True)
            summary = result.get("summary", {})
            if summary:
                completed = summary.get("completed_tasks", [])
                click.secho(f"  Tasks completed: {', '.join(completed)}", fg="green")
        else:
            click.secho(f"  ✗ Plan {result.get('status', 'failed')}.", fg="red", bold=True)

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")

    click.echo()


@cli.command()
@click.argument("intent")
@click.option("--org", "-o", default="lra-cloud-ops", help="Organización GitHub")
def plan(intent, org):
    """
    Genera un Execution Plan sin ejecutarlo.

    Ejemplos:

    \b
      lra plan "Crea un proyecto nuevo llamado client-api"
      lra plan "Despliega la app en EKS"
    """
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho("  LRA AI Platform — Plan", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")
    click.echo()
    click.secho(f"  Intent: {intent}", fg="white")
    click.echo()

    try:
        supervisor = get_supervisor()
        execution_plan, tasks = supervisor.plan(intent, {"org": org})

        if not tasks:
            click.secho("  ✗ No matching workflow for this intent.", fg="red")
            click.echo()
            return

        click.secho(f"  Plan ID: {execution_plan.id}", fg="cyan")
        click.secho(f"  Tasks:   {len(tasks)}", fg="cyan")
        click.echo()
        click.secho("  Execution order:", fg="white", bold=True)

        levels = execution_plan.topological_order()
        for i, level in enumerate(levels):
            for task_id in level:
                task = tasks[task_id]
                parallel = " ⟵ parallel" if len(level) > 1 else ""
                click.secho(f"    {i+1}. {task.type} → {task.assigned_to}{parallel}", fg="white")

        click.echo()
        click.secho("  Use 'lra init' to execute this plan.", fg="yellow")

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")

    click.echo()


@cli.command()
@click.argument("cloud", default="aws",
                type=click.Choice(["aws", "azure", "gcp", "multicloud"], case_sensitive=False))
@click.option("--region", "-r", default="eu-west-1", help="Región cloud")
@click.option("--save", "-s", is_flag=True, help="Guarda el informe en GitHub")
@click.option("--repo", default=None, help="Repositorio donde guardar el informe")
def review(cloud, region, save, repo):
    """
    Revisa la infraestructura de una o más clouds.

    Ejemplos:

    \b
      lra review aws
      lra review azure
      lra review gcp
      lra review multicloud
      lra review aws --region eu-west-1 --save --repo lra-ai-platform
    """
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho(f"  LRA AI Platform — Review ({cloud.upper()})", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")
    click.echo()

    try:
        from agents.cloud_architect_agent import CloudArchitectAgent
        from tools.cloud.aws.aws_tool import AWSTool
        from tools.cloud.azure.azure_tool import AzureTool
        from tools.cloud.gcp.gcp_tool import GCPTool
        from tools.vcs.github.github_tool import GitHubTool
        from core.interfaces.task import Task

        agent = CloudArchitectAgent(
            name="Cloud Architect",
            role="Architecture Designer",
            description="Reviews multi-cloud infrastructure"
        )
        agent.register_tool(AWSTool())
        agent.register_tool(AzureTool())
        agent.register_tool(GCPTool())
        if save:
            agent.register_tool(GitHubTool())

        params = {"region": region}
        if save and repo:
            params["repo"] = repo
            params["clouds"] = [cloud] if cloud != "multicloud" else ["aws", "azure", "gcp"]

        if cloud == "multicloud":
            task_type = "review_multicloud"
        else:
            task_type = f"review_{cloud}_architecture"

        click.secho(f"  Reviewing {cloud.upper()} infrastructure...", fg="cyan")
        click.echo()

        task = Task(type=task_type, params=params, assigned_to="cloud_architect")
        result = agent.execute_task(task)

        if cloud == "multicloud":
            click.secho("  Multi-Cloud Summary:", fg="cyan", bold=True)
            for provider, summary in result.get("total_summary", {}).items():
                click.echo()
                click.secho(f"  {provider.upper()}:", fg="white", bold=True)
                for k, v in summary.items():
                    icon = "  ✓" if v > 0 else "  ·"
                    color = "green" if v > 0 else "white"
                    click.secho(f"  {icon} {k}: {v}", fg=color)
        else:
            summary = result.get("summary", {})
            click.secho(f"  {cloud.upper()} Summary:", fg="cyan", bold=True)
            click.echo()
            for k, v in summary.items():
                icon = "  ✓" if v > 0 else "  ·"
                color = "green" if v > 0 else "white"
                click.secho(f"  {icon} {k}: {v}", fg=color)

        click.echo()
        click.secho("  ✓ Review complete.", fg="green", bold=True)

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")
        import traceback
        traceback.print_exc()

    click.echo()


@cli.command()
def agents():
    """Lista todos los agentes disponibles en la plataforma."""
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho("  LRA AI Platform — Agents", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")
    click.echo()

    try:
        supervisor = get_supervisor()
        agent_list = supervisor.agent_manager.summary()

        for name, info in agent_list.get("agents", {}).items():
            status_icon = "✓" if info.get("loaded") else "·"
            color = "green" if info.get("loaded") else "white"
            click.secho(f"  {status_icon} {name}", fg=color, bold=True)
            click.secho(f"    Role:  {info.get('role', '')}", fg="white")
            click.secho(f"    Tools: {', '.join(info.get('tools', []))}", fg="cyan")
            click.echo()

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")

    click.echo()


@cli.command()
def tools():
    """Lista todas las tools disponibles en la plataforma."""
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho("  LRA AI Platform — Tools", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")
    click.echo()

    try:
        supervisor = get_supervisor()
        tool_summary = supervisor.tool_manager.summary()
        available = tool_summary.get("tools", [])

        categories = {}
        for tool_name in available:
            tool_config = supervisor.config.get_tool(tool_name)
            category = tool_config.get("category", "other")
            categories.setdefault(category, []).append(tool_name)

        for category, tool_names in sorted(categories.items()):
            click.secho(f"  {category.upper()}:", fg="cyan", bold=True)
            for tool_name in sorted(tool_names):
                click.secho(f"    ✓ {tool_name}", fg="green")
            click.echo()

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")

    click.echo()


@cli.command()
def workflows():
    """Lista todos los workflows disponibles."""
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho("  LRA AI Platform — Workflows", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")
    click.echo()

    try:
        supervisor = get_supervisor()
        wf_list = supervisor.task_planner.list_workflows()

        for wf in wf_list:
            click.secho(f"  ✓ {wf}", fg="green")
        click.echo()

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")

    click.echo()


@cli.command()
@click.argument("project")
def memory(project):
    """
    Muestra la memoria de un proyecto.

    Ejemplos:

    \b
      lra memory lracloudops
      lra memory client-api
    """
    click.echo()
    click.secho("═" * 50, fg="blue")
    click.secho(f"  LRA AI Platform — Memory ({project})", fg="blue", bold=True)
    click.secho("═" * 50, fg="blue")
    click.echo()

    try:
        from core.memory_manager import MemoryManager
        mm = MemoryManager()

        # Organization memory
        org = mm.get_organization_memory()
        click.secho("  Organization defaults:", fg="cyan", bold=True)
        for key in org.list_keys():
            click.secho(f"    {key}: {org.load(key)}", fg="white")
        click.echo()

        # Project memory
        proj = mm.get_project_memory(project)
        keys = proj.list_keys()
        if keys:
            click.secho(f"  Project '{project}':", fg="cyan", bold=True)
            for key in keys:
                click.secho(f"    {key}: {proj.load(key)}", fg="white")
        else:
            click.secho(f"  No memory found for project '{project}'.", fg="yellow")

        click.echo()
        click.secho(f"  All projects with memory: {mm.list_projects()}", fg="white")

    except Exception as e:
        click.secho(f"  ✗ Error: {e}", fg="red")

    click.echo()


if __name__ == "__main__":
    cli()