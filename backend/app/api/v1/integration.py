"""
互联互通 API — /api/v1/integration
安全技术系统与外部系统集成管理
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services.integration_service import (
    integration_bus, SystemType,
    register_terminal, register_edge_node, register_cloud_storage, register_business_app,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 连接器管理 ====================

@router.get("/connectors", response_model=ApiResponse)
async def list_connectors(
    user: dict = Depends(get_current_user),
):
    """列出所有已注册的连接器"""
    return ApiResponse(data={
        "connectors": integration_bus.get_all_status(),
        "stats": integration_bus.get_stats(),
    })


@router.get("/connectors/{connector_id}", response_model=ApiResponse)
async def get_connector(
    connector_id: str,
    user: dict = Depends(get_current_user),
):
    """获取连接器详情"""
    connector = integration_bus.get_connector(connector_id)
    if not connector:
        return ApiResponse(code=2001, message="连接器未找到", data=None)
    return ApiResponse(data=connector.get_status())


@router.delete("/connectors/{connector_id}", response_model=ApiResponse)
async def remove_connector(
    connector_id: str,
    user: dict = Depends(get_current_user),
):
    """移除连接器"""
    connector = integration_bus.get_connector(connector_id)
    if not connector:
        return ApiResponse(code=2001, message="连接器未找到", data=None)

    await connector.disconnect()
    del integration_bus.connectors[connector_id]
    return ApiResponse(message=f"连接器 {connector_id} 已移除")


# ==================== 数据采集终端 ====================

@router.post("/terminal/register", response_model=ApiResponse)
async def register_terminal_endpoint(
    name: str = "数据采集终端",
    protocol: str = "mqtt",
    endpoint: str = "mqtt://localhost:1883",
    device_did: str = "",
    topics: str = "",
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    注册数据采集终端

    支持协议: mqtt, opcua, modbus, http
    """
    topic_list = [t.strip() for t in topics.split(",") if t.strip()] if topics else []
    org_id = user.get("organization_id", "")

    result = await register_terminal(
        db=db, name=name, protocol=protocol,
        endpoint=endpoint, device_did=device_did,
        topics=topic_list, org_id=org_id,
    )
    return ApiResponse(data=result)


# ==================== 边缘计算节点 ====================

@router.post("/edge/register", response_model=ApiResponse)
async def register_edge_endpoint(
    name: str = "边缘计算节点",
    node_id: str = "",
    endpoint: str = "http://localhost:9000",
    capabilities: str = "inference,preprocessing",
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    注册边缘计算节点

    能力: inference(推理), preprocessing(预处理), aggregation(聚合)
    """
    cap_list = [c.strip() for c in capabilities.split(",") if c.strip()]
    org_id = user.get("organization_id", "")

    result = await register_edge_node(
        db=db, name=name, node_id=node_id,
        endpoint=endpoint, capabilities=cap_list, org_id=org_id,
    )
    return ApiResponse(data=result)


@router.post("/edge/{connector_id}/deploy", response_model=ApiResponse)
async def deploy_to_edge(
    connector_id: str,
    task_type: str = "inference",
    model_name: str = "default",
    user: dict = Depends(get_current_user),
):
    """部署计算任务到边缘节点"""
    connector = integration_bus.get_connector(connector_id)
    if not connector:
        return ApiResponse(code=2001, message="边缘节点未找到", data=None)

    from app.services.integration_service import EdgeConnector
    if not isinstance(connector, EdgeConnector):
        return ApiResponse(code=2002, message="连接器类型不匹配", data=None)

    result = await connector.deploy_task({
        "task_type": task_type,
        "model_name": model_name,
    })
    return ApiResponse(data=result)


# ==================== 云端数据中心 ====================

@router.post("/cloud/register", response_model=ApiResponse)
async def register_cloud_endpoint(
    name: str = "云端存储",
    storage_type: str = "s3",
    endpoint: str = "http://localhost:9000",
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    注册云端存储

    类型: s3, postgresql, mysql, mongodb
    """
    org_id = user.get("organization_id", "")

    result = await register_cloud_storage(
        db=db, name=name, storage_type=storage_type,
        endpoint=endpoint, org_id=org_id,
    )
    return ApiResponse(data=result)


@router.post("/cloud/{connector_id}/sync", response_model=ApiResponse)
async def sync_cloud_data(
    connector_id: str,
    direction: str = "inbound",
    user: dict = Depends(get_current_user),
):
    """数据同步"""
    connector = integration_bus.get_connector(connector_id)
    if not connector:
        return ApiResponse(code=2001, message="云端连接器未找到", data=None)

    from app.services.integration_service import CloudConnector, DataFlowDirection
    if not isinstance(connector, CloudConnector):
        return ApiResponse(code=2002, message="连接器类型不匹配", data=None)

    dir_enum = DataFlowDirection(direction) if direction in [d.value for d in DataFlowDirection] else DataFlowDirection.INBOUND
    result = await connector.sync_data(dir_enum)
    return ApiResponse(data=result)


# ==================== 业务应用系统 ====================

@router.post("/business/register", response_model=ApiResponse)
async def register_business_endpoint(
    name: str = "业务系统",
    integration_type: str = "rest",
    endpoint: str = "http://localhost:3000",
    api_key: str = "",
    webhook_url: str = "",
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    注册业务应用系统

    类型: rest, websocket, webhook, message_queue
    """
    org_id = user.get("organization_id", "")

    result = await register_business_app(
        db=db, name=name, integration_type=integration_type,
        endpoint=endpoint, api_key=api_key,
        webhook_url=webhook_url, org_id=org_id,
    )
    return ApiResponse(data=result)


@router.post("/business/{connector_id}/webhook", response_model=ApiResponse)
async def trigger_webhook(
    connector_id: str,
    event_type: str = "data_updated",
    payload: str = "{}",
    user: dict = Depends(get_current_user),
):
    """触发Webhook通知"""
    connector = integration_bus.get_connector(connector_id)
    if not connector:
        return ApiResponse(code=2001, message="业务系统连接器未找到", data=None)

    from app.services.integration_service import BusinessConnector
    if not isinstance(connector, BusinessConnector):
        return ApiResponse(code=2002, message="连接器类型不匹配", data=None)

    import json
    event = {"event_type": event_type, "payload": json.loads(payload)}
    success = await connector.trigger_webhook(event)
    return ApiResponse(data={"triggered": success, "event_type": event_type})


# ==================== 系统状态 ====================

@router.get("/status", response_model=ApiResponse)
async def get_integration_status(
    user: dict = Depends(get_current_user),
):
    """获取互联互通系统状态"""
    health = await integration_bus.health_check_all()
    return ApiResponse(data={
        "stats": integration_bus.get_stats(),
        "health": health,
        "supported_systems": [t.value for t in SystemType],
    })


@router.post("/health-check", response_model=ApiResponse)
async def run_health_check(
    user: dict = Depends(get_current_user),
):
    """执行全量健康检查"""
    results = await integration_bus.health_check_all()
    healthy = sum(1 for v in results.values() if v)
    total = len(results)
    return ApiResponse(data={
        "healthy": healthy,
        "total": total,
        "results": results,
    })
