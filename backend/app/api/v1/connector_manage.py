"""连接器管理 API - /api/v1/connector-manage"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.connector import (
    ConnectorCreate, ConnectorResponse, ConnectorUpdate, ConnectorHeartbeat,
    ConnectorDataSourceCreate, ConnectorDataSourceUpdate, ConnectorDataSourceResponse,
    MetadataDiscoverRequest, MetadataDiscoveryResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import connector_service, metadata_discovery_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R008-R009: 连接器管理 ====================

@router.post("", response_model=ApiResponse[ConnectorResponse], status_code=201)
async def create_connector(
    request: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """注册连接器"""
    result = await connector_service.create_connector(
        db=db, name=request.name, protocol_type=request.protocol_type,
        connection_config=request.connection_config,
        organization_id=user.get("organization_id", ""),
        created_by=user["user_id"],
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[ConnectorResponse]])
async def list_connectors(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    protocol_type: str = Query(None, description="协议类型过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出连接器"""
    result = await connector_service.list_connectors(
        db=db, params=pagination, status=status, connector_type=protocol_type,
        organization_id=user.get("organization_id"),
    )
    return ApiResponse(data=result)


@router.get("/{connector_id}", response_model=ApiResponse[ConnectorResponse])
async def get_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取连接器详情"""
    result = await connector_service.get_connector(db=db, connector_id=connector_id)
    return ApiResponse(data=result)


@router.put("/{connector_id}", response_model=ApiResponse[ConnectorResponse])
async def update_connector(
    connector_id: str,
    request: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新连接器"""
    result = await connector_service.update_connector(
        db=db, connector_id=connector_id,
        name=request.name, protocol_type=request.protocol_type,
        connection_config=request.connection_config,
    )
    return ApiResponse(data=result)


@router.delete("/{connector_id}", response_model=ApiResponse)
async def delete_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除连接器"""
    await connector_service.delete_connector(db=db, connector_id=connector_id)
    return ApiResponse(message="连接器已删除")


# ==================== R010-R011: 连接器测试/发现 ====================

@router.post("/{connector_id}/test", response_model=ApiResponse)
async def test_connector(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """测试连接器连通性"""
    result = await connector_service.test_connector(db=db, connector_id=connector_id)
    return ApiResponse(data=result)


@router.post("/{connector_id}/discover", response_model=ApiResponse)
async def discover_metadata(
    connector_id: str,
    discover_type: str = Query("auto", description="发现类型"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """自动发现连接器元数据"""
    result = await metadata_discovery_service.discover_metadata_from_connector(
        db=db, connector_id=connector_id, discover_type=discover_type,
    )
    return ApiResponse(data=result)


@router.get("/{connector_id}/schema-summary", response_model=ApiResponse)
async def get_schema_summary(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取连接器Schema摘要"""
    result = await metadata_discovery_service.get_connector_schema_summary(
        db=db, connector_id=connector_id,
    )
    return ApiResponse(data=result)


# ==================== 连接器心跳 ====================

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
    status: str = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出数据源"""
    result = await connector_service.list_data_sources(db, pagination, connector_id, status)
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


# ==================== 元数据发现记录 ====================

@router.get("/{connector_id}/discoveries", response_model=ApiResponse[PaginatedResponse[MetadataDiscoveryResponse]])
async def list_discoveries(
    connector_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态筛选"),
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
