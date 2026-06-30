# tools/containers/kubernetes/kubernetes_tool.py
# Implementación de la Kubernetes Tool para LRA AI Platform.
# Ejecuta comandos kubectl reales via subprocess.

import os
import subprocess
import json
from core.interfaces.tool import Tool


class KubernetesTool(Tool):
    """
    Tool para interactuar con Kubernetes via kubectl.

    Ejecuta comandos kubectl reales contra el cluster configurado
    en el kubeconfig del sistema.

    Uso:
        k8s = KubernetesTool()
        k8s.execute("get_pods", {"namespace": "default"})
        k8s.execute("get_deployments", {"namespace": "production"})
        k8s.execute("scale_deployment", {"name": "api", "replicas": 3})
    """

    def __init__(self):
        super().__init__(name="kubernetes", version="1.0.0")
        self._kubectl = self._find_kubectl()
        self._kubeconfig = os.getenv("KUBECONFIG", "")

    def _find_kubectl(self) -> str:
        import shutil
        return shutil.which("kubectl") or "kubectl"

    def _run(self, args: list, output_json: bool = True) -> dict:
        """Ejecuta un comando kubectl."""
        cmd = [self._kubectl] + args
        if output_json:
            cmd += ["-o", "json"]

        env = {**os.environ}
        if self._kubeconfig:
            env["KUBECONFIG"] = self._kubeconfig

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=env
            )
            output = result.stdout.strip()

            if output_json and output:
                try:
                    return {
                        "success": result.returncode == 0,
                        "data": json.loads(output),
                        "stderr": result.stderr.strip(),
                        "returncode": result.returncode,
                    }
                except json.JSONDecodeError:
                    pass

            return {
                "success": result.returncode == 0,
                "stdout": output,
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "stderr": "kubectl binary not found",
                "returncode": -1,
            }

    def validate(self) -> bool:
        """Verifica que kubectl está instalado y conectado a un cluster."""
        result = self._run(["version", "--client"], output_json=False)
        if result["success"]:
            print(f"[KubernetesTool] kubectl available: {result['stdout'][:60]}")
            return True
        print(f"[KubernetesTool] Validation failed: {result['stderr']}")
        return False

    def get_capabilities(self) -> list:
        return [
            "get_pods",
            "get_deployments",
            "get_services",
            "get_namespaces",
            "get_nodes",
            "get_configmaps",
            "get_secrets",
            "get_ingresses",
            "get_logs",
            "describe_pod",
            "describe_deployment",
            "apply_manifest",
            "delete_manifest",
            "scale_deployment",
            "rollout_status",
            "rollout_restart",
            "exec_command",
            "port_forward",
            "get_events",
            "top_nodes",
            "top_pods",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(
                f"Action '{action}' not supported. "
                f"Available: {self.get_capabilities()}"
            )

        actions = {
            "get_pods":            self._get_pods,
            "get_deployments":     self._get_deployments,
            "get_services":        self._get_services,
            "get_namespaces":      self._get_namespaces,
            "get_nodes":           self._get_nodes,
            "get_configmaps":      self._get_configmaps,
            "get_secrets":         self._get_secrets,
            "get_ingresses":       self._get_ingresses,
            "get_logs":            self._get_logs,
            "describe_pod":        self._describe_pod,
            "describe_deployment": self._describe_deployment,
            "apply_manifest":      self._apply_manifest,
            "delete_manifest":     self._delete_manifest,
            "scale_deployment":    self._scale_deployment,
            "rollout_status":      self._rollout_status,
            "rollout_restart":     self._rollout_restart,
            "exec_command":        self._exec_command,
            "port_forward":        self._port_forward,
            "get_events":          self._get_events,
            "top_nodes":           self._top_nodes,
            "top_pods":            self._top_pods,
        }

        return actions[action](params)

    # --- Implementaciones ---

    def _ns(self, params: dict) -> list:
        """Retorna el flag de namespace si está especificado."""
        ns = params.get("namespace")
        return ["-n", ns] if ns else ["--all-namespaces"]

    def _get_pods(self, params: dict) -> dict:
        result = self._run(["get", "pods"] + self._ns(params))
        if result.get("success") and "data" in result:
            pods = [{"name": i["metadata"]["name"],
                     "namespace": i["metadata"]["namespace"],
                     "status": i["status"].get("phase", "Unknown"),
                     "ready": self._pod_ready(i)}
                    for i in result["data"].get("items", [])]
            return {"pods": pods, "total": len(pods)}
        return result

    def _pod_ready(self, pod: dict) -> bool:
        conditions = pod.get("status", {}).get("conditions", [])
        for c in conditions:
            if c.get("type") == "Ready":
                return c.get("status") == "True"
        return False

    def _get_deployments(self, params: dict) -> dict:
        result = self._run(["get", "deployments"] + self._ns(params))
        if result.get("success") and "data" in result:
            deployments = [{"name": i["metadata"]["name"],
                            "namespace": i["metadata"]["namespace"],
                            "replicas": i["spec"].get("replicas", 0),
                            "ready": i["status"].get("readyReplicas", 0)}
                           for i in result["data"].get("items", [])]
            return {"deployments": deployments, "total": len(deployments)}
        return result

    def _get_services(self, params: dict) -> dict:
        result = self._run(["get", "services"] + self._ns(params))
        if result.get("success") and "data" in result:
            services = [{"name": i["metadata"]["name"],
                         "namespace": i["metadata"]["namespace"],
                         "type": i["spec"].get("type"),
                         "cluster_ip": i["spec"].get("clusterIP")}
                        for i in result["data"].get("items", [])]
            return {"services": services, "total": len(services)}
        return result

    def _get_namespaces(self, params: dict) -> dict:
        result = self._run(["get", "namespaces"])
        if result.get("success") and "data" in result:
            namespaces = [{"name": i["metadata"]["name"],
                           "status": i["status"].get("phase")}
                          for i in result["data"].get("items", [])]
            return {"namespaces": namespaces, "total": len(namespaces)}
        return result

    def _get_nodes(self, params: dict) -> dict:
        result = self._run(["get", "nodes"])
        if result.get("success") and "data" in result:
            nodes = [{"name": i["metadata"]["name"],
                      "status": self._node_status(i),
                      "roles": self._node_roles(i),
                      "version": i["status"].get("nodeInfo", {}).get("kubeletVersion")}
                     for i in result["data"].get("items", [])]
            return {"nodes": nodes, "total": len(nodes)}
        return result

    def _node_status(self, node: dict) -> str:
        for c in node.get("status", {}).get("conditions", []):
            if c.get("type") == "Ready":
                return "Ready" if c.get("status") == "True" else "NotReady"
        return "Unknown"

    def _node_roles(self, node: dict) -> list:
        labels = node.get("metadata", {}).get("labels", {})
        return [k.split("/")[-1] for k in labels
                if k.startswith("node-role.kubernetes.io/")]

    def _get_configmaps(self, params: dict) -> dict:
        result = self._run(["get", "configmaps"] + self._ns(params))
        if result.get("success") and "data" in result:
            cms = [{"name": i["metadata"]["name"],
                    "namespace": i["metadata"]["namespace"]}
                   for i in result["data"].get("items", [])
                   if i["metadata"]["name"] != "kube-root-ca.crt"]
            return {"configmaps": cms, "total": len(cms)}
        return result

    def _get_secrets(self, params: dict) -> dict:
        result = self._run(["get", "secrets"] + self._ns(params))
        if result.get("success") and "data" in result:
            secrets = [{"name": i["metadata"]["name"],
                        "namespace": i["metadata"]["namespace"],
                        "type": i.get("type")}
                       for i in result["data"].get("items", [])]
            return {"secrets": secrets, "total": len(secrets)}
        return result

    def _get_ingresses(self, params: dict) -> dict:
        result = self._run(["get", "ingresses"] + self._ns(params))
        if result.get("success") and "data" in result:
            ingresses = [{"name": i["metadata"]["name"],
                          "namespace": i["metadata"]["namespace"]}
                         for i in result["data"].get("items", [])]
            return {"ingresses": ingresses, "total": len(ingresses)}
        return result

    def _get_logs(self, params: dict) -> dict:
        pod = params.get("pod")
        namespace = params.get("namespace", "default")
        container = params.get("container")
        tail = params.get("tail", 50)
        args = ["logs", pod, "-n", namespace, f"--tail={tail}"]
        if container:
            args += ["-c", container]
        return self._run(args, output_json=False)

    def _describe_pod(self, params: dict) -> dict:
        pod = params.get("pod")
        namespace = params.get("namespace", "default")
        return self._run(["describe", "pod", pod, "-n", namespace],
                         output_json=False)

    def _describe_deployment(self, params: dict) -> dict:
        name = params.get("name")
        namespace = params.get("namespace", "default")
        return self._run(["describe", "deployment", name, "-n", namespace],
                         output_json=False)

    def _apply_manifest(self, params: dict) -> dict:
        file_path = params.get("file")
        return self._run(["apply", "-f", file_path], output_json=False)

    def _delete_manifest(self, params: dict) -> dict:
        file_path = params.get("file")
        return self._run(["delete", "-f", file_path], output_json=False)

    def _scale_deployment(self, params: dict) -> dict:
        name = params.get("name")
        replicas = params.get("replicas", 1)
        namespace = params.get("namespace", "default")
        result = self._run(
            ["scale", "deployment", name,
             f"--replicas={replicas}", "-n", namespace],
            output_json=False
        )
        print(f"[KubernetesTool] Scaled {name} to {replicas} replicas")
        return result

    def _rollout_status(self, params: dict) -> dict:
        name = params.get("name")
        namespace = params.get("namespace", "default")
        return self._run(["rollout", "status", f"deployment/{name}",
                          "-n", namespace], output_json=False)

    def _rollout_restart(self, params: dict) -> dict:
        name = params.get("name")
        namespace = params.get("namespace", "default")
        return self._run(["rollout", "restart", f"deployment/{name}",
                          "-n", namespace], output_json=False)

    def _exec_command(self, params: dict) -> dict:
        pod = params.get("pod")
        namespace = params.get("namespace", "default")
        command = params.get("command", ["sh", "-c", "echo hello"])
        return self._run(
            ["exec", pod, "-n", namespace, "--"] + command,
            output_json=False
        )

    def _port_forward(self, params: dict) -> dict:
        pod = params.get("pod")
        namespace = params.get("namespace", "default")
        ports = params.get("ports", "8080:8080")
        return self._run(
            ["port-forward", pod, ports, "-n", namespace],
            output_json=False
        )

    def _get_events(self, params: dict) -> dict:
        return self._run(["get", "events"] + self._ns(params))

    def _top_nodes(self, params: dict) -> dict:
        return self._run(["top", "nodes"], output_json=False)

    def _top_pods(self, params: dict) -> dict:
        return self._run(["top", "pods"] + self._ns(params), output_json=False)