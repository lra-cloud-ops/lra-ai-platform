# tools/observability/cloudwatch/cloudwatch_tool.py
# Implementación de la CloudWatch Tool para LRA AI Platform.
# Conecta la plataforma con AWS CloudWatch via boto3.

import os
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from core.interfaces.tool import Tool


class CloudwatchTool(Tool):
    """
    Tool para interactuar con AWS CloudWatch via boto3.

    Permite consultar métricas, alarmas y logs de infraestructura AWS.

    Uso:
        cw = CloudwatchTool()
        cw.execute("list_alarms", {})
        cw.execute("get_metrics", {"namespace": "AWS/EC2", "metric": "CPUUtilization"})
        cw.execute("get_logs", {"log_group": "/aws/eks/cluster/cluster"})
    """

    def __init__(self):
        super().__init__(name="cloudwatch", version="1.0.0")
        self._region = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")
        self._clients: dict = {}

    def _get_client(self, service: str, region: str = None):
        key = f"{service}:{region or self._region}"
        if key not in self._clients:
            self._clients[key] = boto3.client(
                service, region_name=region or self._region
            )
        return self._clients[key]

    def validate(self) -> bool:
        try:
            cw = self._get_client("cloudwatch")
            cw.describe_alarms(MaxRecords=1)
            print(f"[CloudWatchTool] Connected to CloudWatch in {self._region}")
            return True
        except Exception as e:
            print(f"[CloudWatchTool] Validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        return [
            "list_alarms",
            "get_alarm_state",
            "create_alarm",
            "delete_alarm",
            "get_metrics",
            "list_metrics",
            "put_metric_data",
            "get_metric_statistics",
            "list_log_groups",
            "get_logs",
            "get_dashboard",
            "list_dashboards",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(f"Action '{action}' not supported.")

        actions = {
            "list_alarms":          self._list_alarms,
            "get_alarm_state":      self._get_alarm_state,
            "create_alarm":         self._create_alarm,
            "delete_alarm":         self._delete_alarm,
            "get_metrics":          self._get_metrics,
            "list_metrics":         self._list_metrics,
            "put_metric_data":      self._put_metric_data,
            "get_metric_statistics": self._get_metric_statistics,
            "list_log_groups":      self._list_log_groups,
            "get_logs":             self._get_logs,
            "get_dashboard":        self._get_dashboard,
            "list_dashboards":      self._list_dashboards,
        }

        try:
            return actions[action](params)
        except ClientError as e:
            return {"error": e.response["Error"]["Message"], "action": action}

    # --- Implementaciones ---

    def _list_alarms(self, params: dict) -> dict:
        """Lista todas las alarmas de CloudWatch."""
        cw = self._get_client("cloudwatch")
        state = params.get("state")  # OK | ALARM | INSUFFICIENT_DATA
        kwargs = {}
        if state:
            kwargs["StateValue"] = state
        response = cw.describe_alarms(**kwargs)
        alarms = [
            {
                "name": a["AlarmName"],
                "state": a["StateValue"],
                "metric": a.get("MetricName", ""),
                "namespace": a.get("Namespace", ""),
                "threshold": a.get("Threshold", 0),
                "description": a.get("AlarmDescription", ""),
            }
            for a in response.get("MetricAlarms", [])
        ]
        return {"alarms": alarms, "total": len(alarms)}

    def _get_alarm_state(self, params: dict) -> dict:
        """Retorna el estado de una alarma específica."""
        cw = self._get_client("cloudwatch")
        name = params.get("name")
        response = cw.describe_alarms(AlarmNames=[name])
        alarms = response.get("MetricAlarms", [])
        if not alarms:
            return {"error": f"Alarm '{name}' not found"}
        a = alarms[0]
        return {
            "name": a["AlarmName"],
            "state": a["StateValue"],
            "reason": a.get("StateReason", ""),
            "metric": a.get("MetricName", ""),
            "threshold": a.get("Threshold", 0),
        }

    def _create_alarm(self, params: dict) -> dict:
        """Crea una alarma de CloudWatch."""
        cw = self._get_client("cloudwatch")
        cw.put_metric_alarm(
            AlarmName=params.get("name"),
            AlarmDescription=params.get("description", ""),
            MetricName=params.get("metric", "CPUUtilization"),
            Namespace=params.get("namespace", "AWS/EC2"),
            Statistic=params.get("statistic", "Average"),
            Period=params.get("period", 300),
            EvaluationPeriods=params.get("evaluation_periods", 2),
            Threshold=params.get("threshold", 80.0),
            ComparisonOperator=params.get("comparison", "GreaterThanThreshold"),
            TreatMissingData=params.get("treat_missing", "notBreaching"),
        )
        print(f"[CloudWatchTool] Alarm '{params.get('name')}' created.")
        return {"alarm": params.get("name"), "created": True}

    def _delete_alarm(self, params: dict) -> dict:
        """Elimina una alarma de CloudWatch."""
        cw = self._get_client("cloudwatch")
        name = params.get("name")
        cw.delete_alarms(AlarmNames=[name])
        return {"alarm": name, "deleted": True}

    def _list_metrics(self, params: dict) -> dict:
        """Lista métricas disponibles."""
        cw = self._get_client("cloudwatch")
        kwargs = {}
        if params.get("namespace"):
            kwargs["Namespace"] = params["namespace"]
        if params.get("metric"):
            kwargs["MetricName"] = params["metric"]
        response = cw.list_metrics(**kwargs)
        metrics = [
            {"name": m["MetricName"], "namespace": m["Namespace"]}
            for m in response.get("Metrics", [])[:20]
        ]
        return {"metrics": metrics, "total": len(metrics)}

    def _get_metrics(self, params: dict) -> dict:
        """Alias de list_metrics para compatibilidad."""
        return self._list_metrics(params)

    def _get_metric_statistics(self, params: dict) -> dict:
        """Obtiene estadísticas de una métrica en un periodo de tiempo."""
        cw = self._get_client("cloudwatch")
        end_time   = datetime.utcnow()
        start_time = end_time - timedelta(hours=params.get("hours", 1))

        response = cw.get_metric_statistics(
            Namespace=params.get("namespace", "AWS/EC2"),
            MetricName=params.get("metric", "CPUUtilization"),
            StartTime=start_time,
            EndTime=end_time,
            Period=params.get("period", 300),
            Statistics=params.get("statistics", ["Average", "Maximum"]),
            Dimensions=params.get("dimensions", []),
        )
        datapoints = sorted(
            response.get("Datapoints", []),
            key=lambda x: x["Timestamp"]
        )
        return {
            "metric": params.get("metric"),
            "namespace": params.get("namespace"),
            "datapoints": [
                {
                    "timestamp": str(d["Timestamp"]),
                    "average": d.get("Average"),
                    "maximum": d.get("Maximum"),
                    "unit": d.get("Unit"),
                }
                for d in datapoints
            ],
            "total": len(datapoints),
        }

    def _put_metric_data(self, params: dict) -> dict:
        """Publica datos personalizados en CloudWatch."""
        cw = self._get_client("cloudwatch")
        cw.put_metric_data(
            Namespace=params.get("namespace", "LRA/Platform"),
            MetricData=[{
                "MetricName": params.get("metric"),
                "Value": params.get("value"),
                "Unit": params.get("unit", "Count"),
                "Timestamp": datetime.utcnow(),
            }]
        )
        return {"published": True, "metric": params.get("metric")}

    def _list_log_groups(self, params: dict) -> dict:
        """Lista los grupos de logs de CloudWatch Logs."""
        logs = self._get_client("logs")
        kwargs = {}
        if params.get("prefix"):
            kwargs["logGroupNamePrefix"] = params["prefix"]
        response = logs.describe_log_groups(**kwargs)
        groups = [
            {
                "name": g["logGroupName"],
                "retention": g.get("retentionInDays", "never"),
                "stored_bytes": g.get("storedBytes", 0),
            }
            for g in response.get("logGroups", [])
        ]
        return {"log_groups": groups, "total": len(groups)}

    def _get_logs(self, params: dict) -> dict:
        """Lee los últimos eventos de un grupo de logs."""
        logs = self._get_client("logs")
        log_group = params.get("log_group")
        limit = params.get("limit", 20)
        try:
            response = logs.describe_log_streams(
                logGroupName=log_group,
                orderBy="LastEventTime",
                descending=True,
                limit=1,
            )
            streams = response.get("logStreams", [])
            if not streams:
                return {"log_group": log_group, "events": [], "total": 0}

            stream_name = streams[0]["logStreamName"]
            events_response = logs.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                limit=limit,
            )
            events = [
                {
                    "timestamp": str(datetime.fromtimestamp(e["timestamp"] / 1000)),
                    "message": e["message"].strip(),
                }
                for e in events_response.get("events", [])
            ]
            return {
                "log_group": log_group,
                "stream": stream_name,
                "events": events,
                "total": len(events),
            }
        except ClientError as e:
            return {"error": str(e), "log_group": log_group}

    def _list_dashboards(self, params: dict) -> dict:
        """Lista los dashboards de CloudWatch."""
        cw = self._get_client("cloudwatch")
        response = cw.list_dashboards()
        dashboards = [
            {"name": d["DashboardName"], "arn": d.get("DashboardArn", "")}
            for d in response.get("DashboardEntries", [])
        ]
        return {"dashboards": dashboards, "total": len(dashboards)}

    def _get_dashboard(self, params: dict) -> dict:
        """Retorna el contenido de un dashboard."""
        cw = self._get_client("cloudwatch")
        name = params.get("name")
        response = cw.get_dashboard(DashboardName=name)
        return {
            "name": name,
            "body": response.get("DashboardBody", ""),
        }