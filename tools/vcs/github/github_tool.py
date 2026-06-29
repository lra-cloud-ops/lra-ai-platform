# tools/vcs/github/github_tool.py
# Implementación concreta de la GitHub Tool.
# Conecta LRA AI Platform con la API real de GitHub.

import os
from github import Github, GithubException
from core.interfaces.tool import Tool


class GitHubTool(Tool):
    """
    Tool para interactuar con la API de GitHub.

    Hereda de Tool e implementa todos sus métodos abstractos.
    Usa PyGithub para conectarse a la API real de GitHub.

    Credenciales:
        Lee el token desde la variable de entorno GITHUB_TOKEN.
        El token nunca se hardcodea — siempre desde .env o variables de entorno.

    Uso:
        github = GitHubTool()
        github.execute("list_repos", {"org": "lra-cloud-ops"})
        github.execute("create_repo", {"name": "nuevo-proyecto", "org": "lra-cloud-ops"})
        github.execute("get_file", {"repo": "lra-ai-platform", "path": "README.md"})
    """

    def __init__(self):
        super().__init__(name="github", version="1.0.0")
        self._token = os.getenv("GITHUB_TOKEN")
        self._client = None

    def _get_client(self) -> Github:
        """
        Retorna el cliente de GitHub autenticado.
        Lo crea solo cuando se necesita por primera vez (lazy loading).
        """
        if self._client is None:
            if not self._token:
                raise ValueError(
                    "GITHUB_TOKEN environment variable is not set. "
                    "Add it to your .env file."
                )
            self._client = Github(self._token)
        return self._client

    def validate(self) -> bool:
        """
        Verifica que el token es válido y la conexión funciona.
        Retorna True si está lista, False si hay algún problema.
        """
        try:
            client = self._get_client()
            user = client.get_user()
            print(f"[GitHubTool] Authenticated as: {user.login}")
            return True
        except Exception as e:
            print(f"[GitHubTool] Validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        """Retorna todas las acciones que esta tool puede ejecutar."""
        return [
            "list_repos",
            "get_repo",
            "create_repo",
            "create_branch",
            "get_file",
            "create_file",
            "update_file",
            "create_pr",
            "list_prs",
            "create_issue",
            "list_issues",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        """
        Ejecuta una acción en GitHub.

        Ejemplo:
            github.execute("list_repos", {"org": "lra-cloud-ops"})
            github.execute("create_repo", {"name": "mi-repo", "private": False})
            github.execute("get_file", {"repo": "lra-ai-platform", "path": "README.md"})
        """
        if action not in self.get_capabilities():
            raise ValueError(
                f"Action '{action}' not supported. "
                f"Available: {self.get_capabilities()}"
            )

        actions = {
            "list_repos":    self._list_repos,
            "get_repo":      self._get_repo,
            "create_repo":   self._create_repo,
            "create_branch": self._create_branch,
            "get_file":      self._get_file,
            "create_file":   self._create_file,
            "update_file":   self._update_file,
            "create_pr":     self._create_pr,
            "list_prs":      self._list_prs,
            "create_issue":  self._create_issue,
            "list_issues":   self._list_issues,
        }

        try:
            return actions[action](params)
        except GithubException as e:
            return {"error": str(e), "action": action, "params": params}

    # --- Implementaciones ---

    def _list_repos(self, params: dict) -> dict:
        """Lista repos de un usuario u organización."""
        client = self._get_client()
        org_name = params.get("org")
        if org_name:
            org = client.get_organization(org_name)
            repos = [{"name": r.name, "url": r.html_url, "private": r.private}
                     for r in org.get_repos()]
        else:
            user = client.get_user()
            repos = [{"name": r.name, "url": r.html_url, "private": r.private}
                     for r in user.get_repos()]
        return {"repos": repos, "total": len(repos)}

    def _get_repo(self, params: dict) -> dict:
        """Retorna información de un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        return {
            "name": repo.name,
            "full_name": repo.full_name,
            "url": repo.html_url,
            "description": repo.description,
            "default_branch": repo.default_branch,
            "private": repo.private,
        }

    def _create_repo(self, params: dict) -> dict:
        """Crea un repositorio nuevo."""
        client = self._get_client()
        name = params.get("name")
        description = params.get("description", "")
        private = params.get("private", False)
        org_name = params.get("org")

        if org_name:
            org = client.get_organization(org_name)
            repo = org.create_repo(name=name, description=description, private=private)
        else:
            user = client.get_user()
            repo = user.create_repo(name=name, description=description, private=private)

        return {"name": repo.name, "url": repo.html_url, "created": True}

    def _create_branch(self, params: dict) -> dict:
        """Crea una rama nueva en un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        branch_name = params.get("branch")
        from_branch = params.get("from", "main")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        source = repo.get_branch(from_branch)
        repo.create_git_ref(f"refs/heads/{branch_name}", source.commit.sha)
        return {"branch": branch_name, "from": from_branch, "created": True}

    def _get_file(self, params: dict) -> dict:
        """Lee el contenido de un archivo en un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        path = params.get("path")
        branch = params.get("branch", "main")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        content = repo.get_contents(path, ref=branch)
        return {
            "path": path,
            "content": content.decoded_content.decode("utf-8"),
            "sha": content.sha,
        }

    def _create_file(self, params: dict) -> dict:
        """Crea un archivo nuevo en un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        path = params.get("path")
        content = params.get("content", "")
        message = params.get("message", f"Add {path}")
        branch = params.get("branch", "main")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        repo.create_file(path, message, content, branch=branch)
        return {"path": path, "created": True}

    def _update_file(self, params: dict) -> dict:
        """Actualiza un archivo existente en un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        path = params.get("path")
        content = params.get("content", "")
        message = params.get("message", f"Update {path}")
        branch = params.get("branch", "main")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        existing = repo.get_contents(path, ref=branch)
        repo.update_file(path, message, content, existing.sha, branch=branch)
        return {"path": path, "updated": True}

    def _create_pr(self, params: dict) -> dict:
        """Crea un Pull Request."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        title = params.get("title")
        body = params.get("body", "")
        head = params.get("head")
        base = params.get("base", "main")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        return {"number": pr.number, "url": pr.html_url, "created": True}

    def _list_prs(self, params: dict) -> dict:
        """Lista Pull Requests de un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        state = params.get("state", "open")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        prs = [{"number": pr.number, "title": pr.title, "url": pr.html_url}
               for pr in repo.get_pulls(state=state)]
        return {"prs": prs, "total": len(prs)}

    def _create_issue(self, params: dict) -> dict:
        """Crea un Issue en un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        title = params.get("title")
        body = params.get("body", "")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        issue = repo.create_issue(title=title, body=body)
        return {"number": issue.number, "url": issue.html_url, "created": True}

    def _list_issues(self, params: dict) -> dict:
        """Lista Issues de un repositorio."""
        client = self._get_client()
        repo_name = params.get("repo")
        org_name = params.get("org")
        state = params.get("state", "open")
        full_name = f"{org_name}/{repo_name}" if org_name else repo_name
        repo = client.get_repo(full_name)
        issues = [{"number": i.number, "title": i.title, "url": i.html_url}
                  for i in repo.get_issues(state=state)]
        return {"issues": issues, "total": len(issues)}