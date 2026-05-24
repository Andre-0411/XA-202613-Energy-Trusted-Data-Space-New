"""连接器管理 API - /api/v1/connectors"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.connector import (
    ConnectorCreate, ConnectorUpdate, ConnectorHeartbeat, ConnectorResponse,
    ConnectorDataSourceCreate, ConnectorDataSourceUpdate, ConnectorDataSourceResponse,
    MetadataDiscoverRequest, MetadataDiscoveryResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import connector_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 连接器 CRUD ====================

@router.post("", response_model=ApiResponse[ConnectorResponse], status_code=201)
async def create_connector(
    request: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """注册连接器"""
    result = await connector_service.create_connector(
        db=db,
        owner_id=user["user_id"],
        organization_id=user.get("organization_id", ""),
        name=request.name,
        connector_type=request.connector_type,
        version=request.version,
        deployment_config=request.deployment_config,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[ConnectorResponse]])
async def list_connectors(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    connector_type: Optional[str] = Query(None, description="类型筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出连接器"""
    result = await connector_service.list_connectors(
        db, pagination, user.get("organization_id"), status, connector_type
    )
    return ApiResponse(data=result)


@router.get("/{connector_id}", response_model=ApiResponse[ConnectorResponse])
async def get_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取连接器详情"""
    result = await connector_service.get_connector(db, connector_id)
    return ApiResponse(data=result)


@router.put("/{connector_id}", response_model=ApiResponse[ConnectorResponse])
async def update_connector(
    connector_id: str,
    request: ConnectorUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新连接器"""
    result = await connector_service.update_connector(
        db, connector_id,
        name=request.name,
        version=request.version,
        deployment_config=request.deployment_config,
        status=request.status,
    )
    return ApiResponse(data=result)


@router.delete("/{connector_id}", response_model=ApiResponse)
async def delete_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除连接器"""
    await connector_service.delete_connector(db, connector_id)
    return ApiResponse(message="连接器已删除")


@router.post("/{connector_id}/heartbeat", response_model=ApiResponse)
async def connector_heartbeat(
    connector_id: str,
    request: ConnectorHeartbeat,
    db: AsyncSession = Depends(get_db),
):
    """连接器心跳上报"""
    result = await connector_service.connector_heartbeat(
        db, connector_id,
        system_status=request.system_status,
        resource_usage=request.resource_usage,
        network_info=request.network_info,
    )
    return ApiResponse(data=result)


# ==================== 数据源管理 ====================

@router.post("/{connector_id}/data-sources", response_model=ApiResponse[ConnectorDataSourceResponse], status_code=201)
async def create_data_source(
    connector_id: str,
    request: ConnectorDataSourceCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建数据源"""
    result = await connector_service.create_data_source(
        db=db,
        connector_id=connector_id,
        name=request.name,
        source_type=request.source_type,
        connection_config=request.connection_config,
        refresh_schedule=request.refresh_schedule,
    )
    return ApiResponse(data=result)


@router.get("/{connector_id}/data-sources", response_model=ApiResponse[PaginatedResponse[ConnectorDataSourceResponse]])
async def list_data_sources(
    connector_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出数据源"""
    result = await connector_service.list_data_sources(db, pagination, connector_id, status)
    return ApiResponse(data=result)


@router.get("/{connector_id}/data-sources/{source_id}", response_model=ApiResponse[ConnectorDataSourceResponse])
async def get_data_source(
    connector_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取数据源详情"""
    result = await connector_service.get_data_source(db, source_id)
    return ApiResponse(data=result)


@router.put("/{connector_id}/data-sources/{source_id}", response_model=ApiResponse[ConnectorDataSourceResponse])
async def update_data_source(
    connector_id: str,
    source_id: str,
    request: ConnectorDataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新数据源"""
    result = await connector_service.update_data_source(
        db, source_id,
        name=request.name,
        connection_config=request.connection_config,
        refresh_schedule=request.refresh_schedule,
        status=request.status,
    )
    return ApiResponse(data=result)


@router.delete("/{connector_id}/data-sources/{source_id}", response_model=ApiResponse)
async def delete_data_source(
    connector_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除数据源"""
    await connector_service.delete_data_source(db, source_id)
    return ApiResponse(message="数据源已删除")


# ==================== 元数据发现 ====================

@router.post("/{connector_id}/discover", response_model=ApiResponse[MetadataDiscoveryResponse], status_code=201)
async def trigger_metadata_discovery(
    connector_id: str,
    request: MetadataDiscoverRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """触发元数据发现"""
    result = await connector_service.trigger_metadata_discovery(
        db=db,
        connector_id=connector_id,
        data_source_id=request.data_source_id,
        discovery_scope=request.discovery_scope,
    )
    return ApiResponse(data=result)


@router.get("/{connector_id}/discoveries", response_model=ApiResponse[PaginatedResponse[MetadataDiscoveryResponse]])
async def list_discoveries(
    connector_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出元数据发现记录"""
    result = await connector_service.list_discoveries(db, pagination, connector_id, status)
    return ApiResponse(data=result)


@router.get("/{connector_id}/discoveries/{discovery_id}", response_model=ApiResponse[MetadataDiscoveryResponse])
async def get_discovery(
    connector_id: str,
    discovery_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取元数据发现详情"""
    result = await connector_service.get_discovery(db, discovery_id)
    return ApiResponse(data=result)


@router.post("/{connector_id}/discoveries/{discovery_id}/approve", response_model=ApiResponse)
async def approve_discovery_security(
    connector_id: str,
    discovery_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批元数据安全"""
    result = await connector_service.update_discovery_security(db, discovery_id, "approved")
    return ApiResponse(data=result)
