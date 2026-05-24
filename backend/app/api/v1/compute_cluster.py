"""
计算集群节点管理 API - /api/v1/compute/cluster
节点注册/心跳/任务派发/集群状态
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.compute import (
    ClusterNodeCreate, ClusterNodeUpdate, ClusterNodeResponse,
    ClusterStatus, ClusterDispatchRequest, ClusterDispatchResponse,
    NodeHeartbeat,
)
from app.utils.deps import get_current_user
from app.services import cluster_service

router = APIRouter()


@router.post("/nodes", response_model=ApiResponse[ClusterNodeResponse], status_code=201)
async def register_node(
    request: ClusterNodeCreate,
    user: dict = Depends(get_current_user),
):
    """注册新的集群节点"""
    result = await cluster_service.register_node(request=request)
    return ApiResponse(data=result)


@router.get("/nodes", response_model=ApiResponse[list[ClusterNodeResponse]])
async def list_nodes(
    node_type: Optional[str] = Query(None, description="节点类型: FATE/MPC/TEE/HE/通用"),
    status: Optional[str] = Query(None, description="节点状态: online/offline/disabled"),
    region: Optional[str] = Query(None, description="部署区域"),
    user: dict = Depends(get_current_user),
):
    """列出所有集群节点"""
    result = await cluster_service.list_nodes(
        node_type=node_type,
        status=status,
        region=region,
    )
    return ApiResponse(data=result)


@router.get("/nodes/{node_id}", response_model=ApiResponse[ClusterNodeResponse])
async def get_node(
    node_id: str,
    user: dict = Depends(get_current_user),
):
    """获取节点详情"""
    result = await cluster_service.get_node(node_id=node_id)
    return ApiResponse(data=result)


@router.put("/nodes/{node_id}", response_model=ApiResponse[ClusterNodeResponse])
async def update_node(
    node_id: str,
    request: ClusterNodeUpdate,
    user: dict = Depends(get_current_user),
):
    """更新节点信息"""
    result = await cluster_service.update_node(node_id=node_id, request=request)
    return ApiResponse(data=result)


@router.delete("/nodes/{node_id}", response_model=ApiResponse)
async def delete_node(
    node_id: str,
    user: dict = Depends(get_current_user),
):
    """移除集群节点"""
    await cluster_service.delete_node(node_id=node_id)
    return ApiResponse(message="节点已移除")


@router.post("/nodes/{node_id}/heartbeat", response_model=ApiResponse[ClusterNodeResponse])
async def node_heartbeat(
    node_id: str,
    request: NodeHeartbeat,
    user: dict = Depends(get_current_user),
):
    """节点心跳上报"""
    result = await cluster_service.heartbeat(node_id=node_id, hb=request)
    return ApiResponse(data=result)


@router.get("/status", response_model=ApiResponse[ClusterStatus])
async def cluster_status(
    user: dict = Depends(get_current_user),
):
    """获取集群整体状态"""
    result = await cluster_service.get_cluster_status()
    return ApiResponse(data=result)


@router.post("/dispatch", response_model=ApiResponse[ClusterDispatchResponse])
async def dispatch_task(
    request: ClusterDispatchRequest,
    user: dict = Depends(get_current_user),
):
    """派发计算任务到集群节点"""
    result = await cluster_service.dispatch_task(request=request)
    return ApiResponse(data=result)
