# tools/observability/grafana/grafana_tool.py
# Implementación de la Grafana Tool para LRA AI Platform.
# Conecta via HTTP API de Grafana.

import os
import requests
from core.interfaces.tool import Tool


class GrafanaTool(Tool):
    """
    Tool para interactuar con Grafana via HTTP API.

    Funciona cuando hay un cluster con Grafana corriendo.
    URL por defecto: http://localhost:3000

    Uso:
        grafana = GrafanaTool()
        grafana.execute("list_dashboards", {})
        grafana.execute("get_alerts", {})
        grafana.execute("get_datasources", {})
    """

    def __init__(self):
        super().__init__(name="grafana", version="1.0.0")
        self._base_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
        self._user     = os.getenv("GRAFANA_USER", "admin")
        self._password = os.getenv("GRAFANA_PASSWORD", "admin")

    def _get(self, endpoint: str, params: dict = None) -> dict:
        try:
            response = requests.get(
                f"{self._base_url}{endpoint}",
                params=params,
                auth=(self._user, self._password),
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:100]}",
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Cannot connect to Grafana at {self._base_url}.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _post(self, endpoint: str, data: dict) -> dict:
        try:
            response = requests.post(
                f"{self._base_url}{endpoint}",
                json=data,
                auth=(self._user, self._password),
                timeout=10
            )
            if response.status_code in (200, 201):
                return {"success": True, "data": response.json()}
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:100]}",
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": f"Cannot connect to Grafana at {self._base_url}.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate(self) -> bool:
        result = self._get("/api/health")
        if result.get("success"):
            version = result["data"].get("version", "unknown")
            print(f"[GrafanaTool] Connected: Grafana {version} at {self._base_url}")
            return True
        print(f"[GrafanaTool] Not available: {result.get('error')}")
        return False

    def get_capabilities(self) -> list:
        return [
            "get_health",
            "list_dashboards",
            "get_dashboard",
            "create_dashboard",
            "list_datasources",
            "get_datasource",
            "get_alerts",
            "list_alert_rules",
            "list_folders",
            "get_org_stats",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(f"Action '{action}' not supported.")

        actions = {
            "get_health":        self._get_health,
            "list_dashboards":   self._list_dashboards,
            "get_dashboard":     self._get_dashboard,
            "create_dashboard":  self._create_dashboard,
            "list_datasources":  self._list_datasources,
            "get_datasource":    self._get_datasource,
            "get_alerts":        self._get_alerts,
            "list_alert_rules":  self._list_alert_rules,
            "list_folders":      self._list_folders,
            "get_org_stats":     self._get_org_stats,
        }
        return actions[action](params)

    def _get_health(self, params: dict) -> dict:
        result = self._get("/api/health")
        if not result.get("success"):
            return {"available": False, "url": self._base_url}
        return {
            "available": True,
            "url": self._base_url,
            "version": result["data"].get("version"),
            "commit": result["data"].get("commit"),
        }

    def _list_dashboards(self, params: dict) -> dict:
        result = self._get("/api/search", {"type": "dash-db"})
        if not result.get("success"):
            return result
        dashboards = [
            {
                "id": d.get("id"),
                "uid": d.get("uid"),
                "title": d.get("title"),
                "folder": d.get("folderTitle", "General"),
                "url": d.get("url"),
            }
            for d in result["data"]
        ]
        return {"dashboards": dashboards, "total": len(dashboards)}

    def _get_dashboard(self, params: dict) -> dict:
        uid = params.get("uid")
        result = self._get(f"/api/dashboards/uid/{uid}")
        if not result.get("success"):
            return result
        dashboard = result["data"].get("dashboard", {})
        return {
            "uid": uid,
            "title": dashboard.get("title"),
            "panels": len(dashboard.get("panels", [])),
            "tags": dashboard.get("tags", []),
        }

    def _create_dashboard(self, params: dict) -> dict:
        title = params.get("title", "New Dashboard")
        payload = {
            "dashboard": {
                "title": title,
                "panels": params.get("panels", []),
                "tags": params.get("tags", ["lra-ai-platform"]),
                "schemaVersion": 16,
                "version": 0,
            },
            "overwrite": params.get("overwrite", False),
            "folderId": params.get("folder_id", 0),
        }
        result = self._post("/api/dashboards/db", payload)
        if not result.get("success"):
            return result
        return {
            "title": title,
            "uid": result["data"].get("uid"),
            "url": result["data"].get("url"),
            "created": True,
        }

    def _list_datasources(self, params: dict) -> dict:
        result = self._get("/api/datasources")
        if not result.get("success"):
            return result
        sources = [
            {
                "id": d.get("id"),
                "name": d.get("name"),
                "type": d.get("type"),
                "url": d.get("url"),
                "default": d.get("isDefault", False),
            }
            for d in result["data"]
        ]
        return {"datasources": sources, "total": len(sources)}

    def _get_datasource(self, params: dict) -> dict:
        name = params.get("name")
        result = self._get(f"/api/datasources/name/{name}")
        if not result.get("success"):
            return result
        d = result["data"]
        return {
            "id": d.get("id"),
            "name": d.get("name"),
            "type": d.get("type"),
            "url": d.get("url"),
        }

    def _get_alerts(self, params: dict) -> dict:
        result = self._get("/api/alerts")
        if not result.get("success"):
            return result
        alerts = [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "state": a.get("state"),
                "dashboard": a.get("dashboardSlug"),
            }
            for a in result["data"]
        ]
        return {
            "alerts": alerts,
            "total": len(alerts),
            "alerting": sum(1 for a in alerts if a.get("state") == "alerting"),
        }

    def _list_alert_rules(self, params: dict) -> dict:
        result = self._get("/api/ruler/grafana/api/v1/rules")
        if not result.get("success"):
            return {"rules": [], "total": 0, "note": "Unified alerting may not be enabled"}
        return {"rules": result.get("data", {}), "total": 0}

    def _list_folders(self, params: dict) -> dict:
        result = self._get("/api/folders")
        if not result.get("success"):
            return result
        folders = [
            {"id": f.get("id"), "uid": f.get("uid"), "title": f.get("title")}
            for f in result["data"]
        ]
        return {"folders": folders, "total": len(folders)}

    def _get_org_stats(self, params: dict) -> dict:
        result = self._get("/api/org/users")
        if not result.get("success"):
            return result
        return {
            "users": len(result["data"]),
            "url": self._base_url,
        }