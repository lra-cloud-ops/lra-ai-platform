# agents/sre_agent.py
# SRE Agent — gestiona observabilidad, métricas y fiabilidad.
# v2.0 Task-centric: ejecuta Tasks individuales asignadas por WorkflowEngine.

from core.interfaces.agent import Agent
from core.interfaces.task import Task


class SREAgent(Agent):
    """
    SRE Agent de LRA AI Platform.

    Especialidad: observabilidad, métricas, alertas y fiabilidad
    de infraestructura y aplicaciones.

    Tasks que sabe ejecutar:
        check_cloudwatch_alarms    → lista alarmas AWS CloudWatch
        get_cloudwatch_metrics     → consulta métricas CloudWatch
        get_log_groups             → lista grupos de logs CloudWatch
        get_logs                   → lee logs de CloudWatch
        check_prometheus_alerts    → verifica alertas activas Prometheus
        query_prometheus           → ejecuta query PromQL
        get_prometheus_targets     → lista targets monitorizados
        check_grafana_health       → verifica estado de Grafana
        list_grafana_dashboards    → lista dashboards de Grafana
        generate_sre_report        → genera informe de observabilidad

    Tools que usa:
        - cloudwatch → métricas, alarmas y logs AWS
        - prometheus → métricas y alertas (cuando disponible)
        - grafana    → dashboards y alertas (cuando disponible)
    """

    _TASK_HANDLERS = [
        "check_cloudwatch_alarms",
        "get_cloudwatch_metrics",
        "get_log_groups",
        "get_logs",
        "check_prometheus_alerts",
        "query_prometheus",
        "get_prometheus_targets",
        "check_grafana_health",
        "list_grafana_dashboards",
        "generate_sre_report",
    ]

    def execute_task(self, task: Task) -> dict:
        handlers = {
            "check_cloudwatch_alarms": self._check_cloudwatch_alarms,
            "get_cloudwatch_metrics":  self._get_cloudwatch_metrics,
            "get_log_groups":          self._get_log_groups,
            "get_logs":                self._get_logs,
            "check_prometheus_alerts": self._check_prometheus_alerts,
            "query_prometheus":        self._query_prometheus,
            "get_prometheus_targets":  self._get_prometheus_targets,
            "check_grafana_health":    self._check_grafana_health,
            "list_grafana_dashboards": self._list_grafana_dashboards,
            "generate_sre_report":     self._generate_sre_report,
        }

        handler = handlers.get(task.type)
        if handler is None:
            raise ValueError(
                f"SREAgent does not handle task type '{task.type}'. "
                f"Supported: {list(handlers.keys())}"
            )
        return handler(task.params)

    def run(self, task: str, context: dict = {}) -> dict:
        """Compatibilidad v1.0."""
        t = Task(type=task.replace(" ", "_"), params=context, assigned_to="sre")
        return self.execute_task(t)

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tools": list(self.tools.keys()),
            "supported_tasks": self._TASK_HANDLERS,
        }

    # --- CloudWatch ---

    def _check_cloudwatch_alarms(self, params: dict) -> dict:
        cw = self.get_tool("cloudwatch")
        print(f"[SREAgent] Checking CloudWatch alarms...")
        result = cw.execute("list_alarms", params)
        alarms = result.get("alarms", [])
        firing = [a for a in alarms if a["state"] == "ALARM"]
        print(f"[SREAgent] {len(alarms)} alarms, {len(firing)} firing")
        return {
            "total": len(alarms),
            "firing": len(firing),
            "ok": sum(1 for a in alarms if a["state"] == "OK"),
            "insufficient_data": sum(1 for a in alarms if a["state"] == "INSUFFICIENT_DATA"),
            "firing_alarms": firing,
            "all_alarms": alarms,
        }

    def _get_cloudwatch_metrics(self, params: dict) -> dict:
        cw = self.get_tool("cloudwatch")
        namespace = params.get("namespace", "AWS/EC2")
        print(f"[SREAgent] Getting CloudWatch metrics for {namespace}...")
        return cw.execute("list_metrics", params)

    def _get_log_groups(self, params: dict) -> dict:
        cw = self.get_tool("cloudwatch")
        print(f"[SREAgent] Listing CloudWatch log groups...")
        return cw.execute("list_log_groups", params)

    def _get_logs(self, params: dict) -> dict:
        cw = self.get_tool("cloudwatch")
        log_group = params.get("log_group")
        print(f"[SREAgent] Getting logs from {log_group}...")
        return cw.execute("get_logs", params)

    # --- Prometheus ---

    def _check_prometheus_alerts(self, params: dict) -> dict:
        try:
            prom = self.get_tool("prometheus")
            print(f"[SREAgent] Checking Prometheus alerts...")
            return prom.execute("get_alerts", params)
        except ValueError:
            return {"available": False, "note": "Prometheus tool not registered"}

    def _query_prometheus(self, params: dict) -> dict:
        try:
            prom = self.get_tool("prometheus")
            query = params.get("query", "up")
            print(f"[SREAgent] Querying Prometheus: {query}")
            return prom.execute("query", params)
        except ValueError:
            return {"available": False, "note": "Prometheus tool not registered"}

    def _get_prometheus_targets(self, params: dict) -> dict:
        try:
            prom = self.get_tool("prometheus")
            print(f"[SREAgent] Getting Prometheus targets...")
            return prom.execute("get_targets", params)
        except ValueError:
            return {"available": False, "note": "Prometheus tool not registered"}

    # --- Grafana ---

    def _check_grafana_health(self, params: dict) -> dict:
        try:
            grafana = self.get_tool("grafana")
            print(f"[SREAgent] Checking Grafana health...")
            return grafana.execute("get_health", params)
        except ValueError:
            return {"available": False, "note": "Grafana tool not registered"}

    def _list_grafana_dashboards(self, params: dict) -> dict:
        try:
            grafana = self.get_tool("grafana")
            print(f"[SREAgent] Listing Grafana dashboards...")
            return grafana.execute("list_dashboards", params)
        except ValueError:
            return {"available": False, "note": "Grafana tool not registered"}

    # --- Informe SRE ---

    def _generate_sre_report(self, params: dict) -> dict:
        """
        Genera un informe de observabilidad consolidado.
        Usa CloudWatch (siempre), Prometheus y Grafana (si disponibles).
        """
        print(f"[SREAgent] Generating SRE report...")
        report = {}

        # CloudWatch — siempre disponible con AWS
        try:
            cw = self.get_tool("cloudwatch")
            report["cloudwatch"] = {
                "alarms": cw.execute("list_alarms", {}),
                "log_groups": cw.execute("list_log_groups", {}),
                "metrics": cw.execute("list_metrics",
                                      {"namespace": "AWS/EC2"}),
            }
        except ValueError:
            report["cloudwatch"] = {"available": False}

        # Prometheus — opcional
        try:
            prom = self.get_tool("prometheus")
            prom_status = prom.execute("get_status", {})
            if prom_status.get("available"):
                report["prometheus"] = {
                    "status": prom_status,
                    "alerts": prom.execute("get_alerts", {}),
                    "targets": prom.execute("get_targets", {}),
                }
            else:
                report["prometheus"] = {"available": False}
        except ValueError:
            report["prometheus"] = {"available": False}

        # Grafana — opcional
        try:
            grafana = self.get_tool("grafana")
            grafana_health = grafana.execute("get_health", {})
            if grafana_health.get("available"):
                report["grafana"] = {
                    "health": grafana_health,
                    "dashboards": grafana.execute("list_dashboards", {}),
                }
            else:
                report["grafana"] = {"available": False}
        except ValueError:
            report["grafana"] = {"available": False}

        # Summary
        cw_alarms = report.get("cloudwatch", {}).get("alarms", {})
        firing = cw_alarms.get("alarms", [])
        firing_count = sum(1 for a in firing if a.get("state") == "ALARM")

        report["summary"] = {
            "cloudwatch_alarms": cw_alarms.get("total", 0),
            "firing_alarms": firing_count,
            "prometheus_available": report.get("prometheus", {}).get("available", False),
            "grafana_available": report.get("grafana", {}).get("available", False),
            "status": "ALERT" if firing_count > 0 else "OK",
        }

        print(f"[SREAgent] SRE report complete. Status: {report['summary']['status']}")
        return report