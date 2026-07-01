# tools/observability/prometheus/prometheus_tool.py
# Implementación de la Prometheus Tool para LRA AI Platform.
# Conecta via HTTP API de Prometheus.

import os
import requests
from datetime import datetime, timedelta
from core.interfaces.tool import Tool


class PrometheusTool(Tool):
    """
    Tool para interactuar con Prometheus via HTTP API.

    Funciona cuando hay un cluster con Prometheus corriendo.
    URL por defecto: http://localhost:9090

    Uso:
        prom = PrometheusTool()
        prom.execute("query", {"query": "up"})
        prom.execute("get_alerts", {})
        prom.execute("get_targets", {})
    """

    def __init__(self):
        super().__init__(name="prometheus", version="1.0.0")
        self._base_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

    def _get(self, endpoint: str, params: dict = None) -> dict:
        try:
            response = requests.get(
                f"{self._base_url}{endpoint}",
                params=params,
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
                "error": f"Cannot connect to Prometheus at {self._base_url}. "
                         "Is Prometheus running?",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate(self) -> bool:
        result = self._get("/api/v1/status/buildinfo")
        if result.get("success"):
            version = result["data"].get("data", {}).get("version", "unknown")
            print(f"[PrometheusTool] Connected: Prometheus {version} at {self._base_url}")
            return True
        print(f"[PrometheusTool] Not available: {result.get('error')}")
        return False

    def get_capabilities(self) -> list:
        return [
            "query",
            "query_range",
            "get_alerts",
            "get_alert_rules",
            "get_targets",
            "get_labels",
            "get_series",
            "get_status",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(f"Action '{action}' not supported.")

        actions = {
            "query":           self._query,
            "query_range":     self._query_range,
            "get_alerts":      self._get_alerts,
            "get_alert_rules": self._get_alert_rules,
            "get_targets":     self._get_targets,
            "get_labels":      self._get_labels,
            "get_series":      self._get_series,
            "get_status":      self._get_status,
        }
        return actions[action](params)

    def _query(self, params: dict) -> dict:
        """Ejecuta una query PromQL instantánea."""
        query = params.get("query", "up")
        result = self._get("/api/v1/query", {"query": query})
        if not result.get("success"):
            return result
        data = result["data"].get("data", {})
        return {
            "query": query,
            "results": data.get("result", []),
            "total": len(data.get("result", [])),
        }

    def _query_range(self, params: dict) -> dict:
        """Ejecuta una query PromQL en un rango de tiempo."""
        query = params.get("query", "up")
        hours = params.get("hours", 1)
        end   = datetime.utcnow()
        start = end - timedelta(hours=hours)
        result = self._get("/api/v1/query_range", {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": params.get("step", "60s"),
        })
        if not result.get("success"):
            return result
        data = result["data"].get("data", {})
        return {
            "query": query,
            "results": data.get("result", []),
            "total": len(data.get("result", [])),
        }

    def _get_alerts(self, params: dict) -> dict:
        """Retorna las alertas activas."""
        result = self._get("/api/v1/alerts")
        if not result.get("success"):
            return result
        alerts = result["data"].get("data", {}).get("alerts", [])
        return {
            "alerts": [
                {
                    "name": a.get("labels", {}).get("alertname"),
                    "state": a.get("state"),
                    "severity": a.get("labels", {}).get("severity"),
                    "summary": a.get("annotations", {}).get("summary", ""),
                }
                for a in alerts
            ],
            "total": len(alerts),
            "firing": sum(1 for a in alerts if a.get("state") == "firing"),
        }

    def _get_alert_rules(self, params: dict) -> dict:
        """Retorna las reglas de alerta configuradas."""
        result = self._get("/api/v1/rules")
        if not result.get("success"):
            return result
        groups = result["data"].get("data", {}).get("groups", [])
        rules = []
        for group in groups:
            for rule in group.get("rules", []):
                if rule.get("type") == "alerting":
                    rules.append({
                        "name": rule.get("name"),
                        "state": rule.get("state"),
                        "group": group.get("name"),
                    })
        return {"rules": rules, "total": len(rules)}

    def _get_targets(self, params: dict) -> dict:
        """Retorna los targets monitorizados."""
        result = self._get("/api/v1/targets")
        if not result.get("success"):
            return result
        data = result["data"].get("data", {})
        active = data.get("activeTargets", [])
        return {
            "targets": [
                {
                    "job": t.get("labels", {}).get("job"),
                    "instance": t.get("labels", {}).get("instance"),
                    "health": t.get("health"),
                }
                for t in active
            ],
            "total": len(active),
            "healthy": sum(1 for t in active if t.get("health") == "up"),
        }

    def _get_labels(self, params: dict) -> dict:
        """Retorna todos los labels disponibles."""
        result = self._get("/api/v1/labels")
        if not result.get("success"):
            return result
        return {"labels": result["data"].get("data", []) }

    def _get_series(self, params: dict) -> dict:
        """Busca series de tiempo que coincidan con un selector."""
        match = params.get("match", "{job!=\"\"}")
        result = self._get("/api/v1/series", {"match[]": match})
        if not result.get("success"):
            return result
        series = result["data"].get("data", [])
        return {"series": series[:20], "total": len(series)}

    def _get_status(self, params: dict) -> dict:
        """Retorna el estado general de Prometheus."""
        result = self._get("/api/v1/status/buildinfo")
        if not result.get("success"):
            return {"available": False, "url": self._base_url}
        data = result["data"].get("data", {})
        return {
            "available": True,
            "url": self._base_url,
            "version": data.get("version"),
            "goVersion": data.get("goVersion"),
        }