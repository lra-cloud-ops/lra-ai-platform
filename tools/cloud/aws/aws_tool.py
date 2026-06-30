# tools/cloud/aws/aws_tool.py
# Implementación de la AWS Tool para LRA AI Platform.
# Conecta la plataforma con AWS real via boto3.

import os
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from tools.cloud.base_cloud_tool import BaseCloudTool


class AWSTool(BaseCloudTool):
    """
    Tool para interactuar con AWS via boto3.

    Credenciales: usa las credenciales configuradas en el sistema
    (AWS CLI, variables de entorno o IAM role). Nunca hardcodeadas.

    Uso:
        aws = AWSTool()
        aws.execute("list_s3_buckets", {})
        aws.execute("create_eks_cluster", {"name": "lra-prod", "region": "eu-west-1"})
        aws.execute("describe_instances", {"region": "eu-west-1"})
    """

    def __init__(self):
        super().__init__(name="aws", provider="aws", version="1.0.0")
        self._region = os.getenv("AWS_DEFAULT_REGION", "eu-west-1")
        self._clients: dict = {}

    def _get_client(self, service: str, region: str = None) -> boto3.client:
        """Retorna un cliente boto3 para el servicio dado. Reutiliza clientes."""
        key = f"{service}:{region or self._region}"
        if key not in self._clients:
            self._clients[key] = boto3.client(
                service,
                region_name=region or self._region
            )
        return self._clients[key]

    def validate(self) -> bool:
        """Verifica que las credenciales AWS son válidas."""
        try:
            sts = self._get_client("sts")
            identity = sts.get_caller_identity()
            print(f"[AWSTool] Authenticated as: {identity['Arn']}")
            return True
        except Exception as e:
            print(f"[AWSTool] Validation failed: {e}")
            return False

    def get_capabilities(self) -> list:
        return [
            "get_caller_identity",
            "list_s3_buckets",
            "create_s3_bucket",
            "list_ec2_instances",
            "describe_instances",
            "list_eks_clusters",
            "describe_eks_cluster",
            "create_eks_cluster",
            "list_ecr_repos",
            "create_ecr_repo",
            "list_iam_users",
            "get_iam_user",
            "create_iam_role",
            "list_vpcs",
            "describe_vpc",
            "list_cloudwatch_alarms",
            "create_cloudwatch_alarm",
            "get_cloudwatch_metrics",
        ]

    def execute(self, action: str, params: dict = {}) -> dict:
        if action not in self.get_capabilities():
            raise ValueError(
                f"Action '{action}' not supported. "
                f"Available: {self.get_capabilities()}"
            )

        actions = {
            "get_caller_identity":     self._get_caller_identity,
            "list_s3_buckets":         self._list_s3_buckets,
            "create_s3_bucket":        self._create_s3_bucket,
            "list_ec2_instances":      self._list_ec2_instances,
            "describe_instances":      self._list_ec2_instances,
            "list_eks_clusters":       self._list_eks_clusters,
            "describe_eks_cluster":    self._describe_eks_cluster,
            "create_eks_cluster":      self._create_eks_cluster,
            "list_ecr_repos":          self._list_ecr_repos,
            "create_ecr_repo":         self._create_ecr_repo,
            "list_iam_users":          self._list_iam_users,
            "get_iam_user":            self._get_iam_user,
            "create_iam_role":         self._create_iam_role,
            "list_vpcs":               self._list_vpcs,
            "describe_vpc":            self._describe_vpc,
            "list_cloudwatch_alarms":  self._list_cloudwatch_alarms,
            "create_cloudwatch_alarm": self._create_cloudwatch_alarm,
            "get_cloudwatch_metrics":  self._get_cloudwatch_metrics,
        }

        try:
            return actions[action](params)
        except ClientError as e:
            return {"error": e.response["Error"]["Message"], "action": action}
        except BotoCoreError as e:
            return {"error": str(e), "action": action}

    # --- BaseCloudTool interface ---

    def get_identity(self) -> dict:
        return self._get_caller_identity({})

    def list_compute(self, params: dict = None) -> dict:
        return self._list_ec2_instances(params or {})

    def list_storage(self, params: dict = None) -> dict:
        return self._list_s3_buckets(params or {})

    def list_networks(self, params: dict = None) -> dict:
        return self._list_vpcs(params or {})

    def list_kubernetes(self, params: dict = None) -> dict:
        return self._list_eks_clusters(params or {})

    def list_registries(self, params: dict = None) -> dict:
        return self._list_ecr_repos(params or {})

    # --- Implementaciones ---

    def _get_caller_identity(self, params: dict) -> dict:
        sts = self._get_client("sts")
        return sts.get_caller_identity()

    def _list_s3_buckets(self, params: dict) -> dict:
        s3 = self._get_client("s3")
        response = s3.list_buckets()
        buckets = [{"name": b["Name"], "created": str(b["CreationDate"])}
                   for b in response.get("Buckets", [])]
        return {"buckets": buckets, "total": len(buckets)}

    def _create_s3_bucket(self, params: dict) -> dict:
        name = params.get("name")
        region = params.get("region", self._region)
        s3 = self._get_client("s3", region)
        if region == "us-east-1":
            s3.create_bucket(Bucket=name)
        else:
            s3.create_bucket(
                Bucket=name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        return {"bucket": name, "region": region, "created": True}

    def _list_ec2_instances(self, params: dict) -> dict:
        region = params.get("region", self._region)
        ec2 = self._get_client("ec2", region)
        response = ec2.describe_instances()
        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                name = next(
                    (tag["Value"] for tag in instance.get("Tags", [])
                     if tag["Key"] == "Name"), "unnamed"
                )
                instances.append({
                    "id": instance["InstanceId"],
                    "name": name,
                    "type": instance["InstanceType"],
                    "state": instance["State"]["Name"],
                    "region": region,
                })
        return {"instances": instances, "total": len(instances)}

    def _list_eks_clusters(self, params: dict) -> dict:
        region = params.get("region", self._region)
        eks = self._get_client("eks", region)
        response = eks.list_clusters()
        clusters = response.get("clusters", [])
        return {"clusters": clusters, "total": len(clusters), "region": region}

    def _describe_eks_cluster(self, params: dict) -> dict:
        name = params.get("name")
        region = params.get("region", self._region)
        eks = self._get_client("eks", region)
        response = eks.describe_cluster(name=name)
        cluster = response.get("cluster", {})
        return {
            "name": cluster.get("name"),
            "status": cluster.get("status"),
            "version": cluster.get("version"),
            "endpoint": cluster.get("endpoint"),
            "region": region,
        }

    def _create_eks_cluster(self, params: dict) -> dict:
        name = params.get("name")
        region = params.get("region", self._region)
        role_arn = params.get("role_arn")
        subnet_ids = params.get("subnet_ids", [])
        version = params.get("version", "1.29")
        eks = self._get_client("eks", region)
        response = eks.create_cluster(
            name=name,
            version=version,
            roleArn=role_arn,
            resourcesVpcConfig={"subnetIds": subnet_ids},
        )
        cluster = response.get("cluster", {})
        return {
            "name": cluster.get("name"),
            "status": cluster.get("status"),
            "region": region,
            "created": True,
        }

    def _list_ecr_repos(self, params: dict) -> dict:
        region = params.get("region", self._region)
        ecr = self._get_client("ecr", region)
        response = ecr.describe_repositories()
        repos = [{"name": r["repositoryName"], "uri": r["repositoryUri"]}
                 for r in response.get("repositories", [])]
        return {"repositories": repos, "total": len(repos)}

    def _create_ecr_repo(self, params: dict) -> dict:
        name = params.get("name")
        region = params.get("region", self._region)
        ecr = self._get_client("ecr", region)
        response = ecr.create_repository(repositoryName=name)
        repo = response.get("repository", {})
        return {
            "name": repo.get("repositoryName"),
            "uri": repo.get("repositoryUri"),
            "created": True,
        }

    def _list_iam_users(self, params: dict) -> dict:
        iam = self._get_client("iam")
        response = iam.list_users()
        users = [{"name": u["UserName"], "arn": u["Arn"]}
                 for u in response.get("Users", [])]
        return {"users": users, "total": len(users)}

    def _get_iam_user(self, params: dict) -> dict:
        username = params.get("username", "liquenson-cli")
        iam = self._get_client("iam")
        response = iam.get_user(UserName=username)
        user = response.get("User", {})
        return {"name": user.get("UserName"), "arn": user.get("Arn")}

    def _create_iam_role(self, params: dict) -> dict:
        name = params.get("name")
        policy_document = params.get("assume_role_policy")
        iam = self._get_client("iam")
        response = iam.create_role(
            RoleName=name,
            AssumeRolePolicyDocument=str(policy_document),
        )
        role = response.get("Role", {})
        return {"name": role.get("RoleName"), "arn": role.get("Arn"), "created": True}

    def _list_vpcs(self, params: dict) -> dict:
        region = params.get("region", self._region)
        ec2 = self._get_client("ec2", region)
        response = ec2.describe_vpcs()
        vpcs = [{"id": v["VpcId"], "cidr": v["CidrBlock"],
                 "default": v["IsDefault"]}
                for v in response.get("Vpcs", [])]
        return {"vpcs": vpcs, "total": len(vpcs), "region": region}

    def _describe_vpc(self, params: dict) -> dict:
        vpc_id = params.get("vpc_id")
        region = params.get("region", self._region)
        ec2 = self._get_client("ec2", region)
        response = ec2.describe_vpcs(VpcIds=[vpc_id])
        vpcs = response.get("Vpcs", [])
        if not vpcs:
            return {"error": f"VPC {vpc_id} not found"}
        v = vpcs[0]
        return {"id": v["VpcId"], "cidr": v["CidrBlock"], "default": v["IsDefault"]}

    def _list_cloudwatch_alarms(self, params: dict) -> dict:
        region = params.get("region", self._region)
        cw = self._get_client("cloudwatch", region)
        response = cw.describe_alarms()
        alarms = [{"name": a["AlarmName"], "state": a["StateValue"]}
                  for a in response.get("MetricAlarms", [])]
        return {"alarms": alarms, "total": len(alarms)}

    def _create_cloudwatch_alarm(self, params: dict) -> dict:
        region = params.get("region", self._region)
        cw = self._get_client("cloudwatch", region)
        cw.put_metric_alarm(
            AlarmName=params.get("name"),
            MetricName=params.get("metric", "CPUUtilization"),
            Namespace=params.get("namespace", "AWS/EC2"),
            Statistic=params.get("statistic", "Average"),
            Period=params.get("period", 300),
            EvaluationPeriods=params.get("evaluation_periods", 2),
            Threshold=params.get("threshold", 80.0),
            ComparisonOperator=params.get("comparison", "GreaterThanThreshold"),
        )
        return {"alarm": params.get("name"), "created": True}

    def _get_cloudwatch_metrics(self, params: dict) -> dict:
        region = params.get("region", self._region)
        cw = self._get_client("cloudwatch", region)
        response = cw.list_metrics(
            Namespace=params.get("namespace", "AWS/EC2"),
        )
        metrics = [{"name": m["MetricName"], "namespace": m["Namespace"]}
                   for m in response.get("Metrics", [])[:20]]
        return {"metrics": metrics, "total": len(metrics)}