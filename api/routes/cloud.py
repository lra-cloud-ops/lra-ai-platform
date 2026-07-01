# api/routes/cloud.py
# Rutas para revisión de infraestructura cloud.

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

router = APIRouter()


class ReviewRequest(BaseModel):
    region: Optional[str] = "eu-west-1"
    clouds: Optional[list] = ["aws"]


@router.get("/review/{cloud}")
def review_cloud(cloud: str, region: str = "eu-west-1"):
    """
    Revisa la infraestructura de una cloud.
    cloud: aws | azure | gcp | multicloud
    """
    from agents.cloud_architect_agent import CloudArchitectAgent
    from tools.cloud.aws.aws_tool import AWSTool
    from tools.cloud.azure.azure_tool import AzureTool
    from tools.cloud.gcp.gcp_tool import GCPTool
    from core.interfaces.task import Task

    valid = ["aws", "azure", "gcp", "multicloud"]
    if cloud not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cloud '{cloud}'. Valid: {valid}"
        )

    agent = CloudArchitectAgent(
        name="Cloud Architect",
        role="Architecture Designer",
        description="Reviews multi-cloud infrastructure"
    )
    agent.register_tool(AWSTool())
    agent.register_tool(AzureTool())
    agent.register_tool(GCPTool())

    task_type = "review_multicloud" if cloud == "multicloud" else f"review_{cloud}_architecture"
    task = Task(type=task_type, params={"region": region}, assigned_to="cloud_architect")
    result = agent.execute_task(task)

    if cloud == "multicloud":
        return {
            "type": "multicloud_report",
            "summary": result.get("total_summary", {}),
        }

    return {
        "cloud": cloud,
        "region": region,
        "summary": result.get("summary", {}),
        "identity": result.get("identity", {}),
    }


@router.get("/aws/s3")
def list_s3_buckets():
    """Lista los buckets S3 de la cuenta AWS."""
    from tools.cloud.aws.aws_tool import AWSTool
    aws = AWSTool()
    return aws.execute("list_s3_buckets", {})


@router.get("/aws/vpcs")
def list_vpcs(region: str = "eu-west-1"):
    """Lista las VPCs de la cuenta AWS."""
    from tools.cloud.aws.aws_tool import AWSTool
    aws = AWSTool()
    return aws.execute("list_vpcs", {"region": region})


@router.get("/aws/eks")
def list_eks_clusters(region: str = "eu-west-1"):
    """Lista los clusters EKS de la cuenta AWS."""
    from tools.cloud.aws.aws_tool import AWSTool
    aws = AWSTool()
    return aws.execute("list_eks_clusters", {"region": region})


@router.get("/aws/ecr")
def list_ecr_repos(region: str = "eu-west-1"):
    """Lista los repositorios ECR de la cuenta AWS."""
    from tools.cloud.aws.aws_tool import AWSTool
    aws = AWSTool()
    return aws.execute("list_ecr_repos", {"region": region})


@router.get("/azure/resource-groups")
def list_resource_groups():
    """Lista los resource groups de Azure."""
    from tools.cloud.azure.azure_tool import AzureTool
    azure = AzureTool()
    return azure.execute("list_resource_groups", {})


@router.get("/gcp/projects")
def list_gcp_projects():
    """Lista los proyectos de GCP."""
    from tools.cloud.gcp.gcp_tool import GCPTool
    gcp = GCPTool()
    return gcp.execute("list_projects", {})