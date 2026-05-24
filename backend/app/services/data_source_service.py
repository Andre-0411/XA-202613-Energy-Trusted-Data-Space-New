"""
数据源管理服务
数据源CRUD + 协议适配（DLMS/Modbus/HTTP/WebSocket）+ 启动/停止采集 + 状态/指标查询
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_asset import DataSource
from app.models.access_log import AccessLog
from app.schemas.data_asset import DataSourceCreate, DataSourceResponse
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.services.mqtt_client import mqtt_manager
from app.exceptions import DataNotFoundError, DataSourceError, DataValidationError

logger = logging.getLogger(__name__)

# 支持的协议类型
VALID_PROTOCOL_TYPES = {"DLMS", "Modbus", "HTTP", "WebSocket", "OPC-UA", "MQTT"}


async def list_data_sources(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    protocol_type: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """查询数据源列表（分页+筛选）"""
    query = select(DataSource)
    if organization_id:
        query = query.where(DataSource.organization_id == uuid.UUID(organization_id))
    if protocol_type:
        query = query.where(DataSource.protocol_type == protocol_type)
    if status:
        query = query.where(DataSource.status == status)
    result = await paginate_query(db, query, params, DataSourceResponse)
    return result


async def get_data_source(
    db: AsyncSession,
    source_id: str,
) -> DataSourceResponse:
    """获取数据源详情"""
    result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(source_id))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise DataNotFoundError("数据源未找到")
    return DataSourceResponse.model_validate(source)


async def create_data_source(
    db: AsyncSession,
    request: DataSourceCreate,
    user_id: str,
) -> DataSourceResponse:
    """
    注册数据源

    1. 校验协议类型
    2. 校验连接配置格式
    3. 创建数据源记录
    """
    # 1. 校验协议类型
    if request.protocol_type not in VALID_PROTOCOL_TYPES:
        raise DataValidationError(
            f"不支持的协议类型: {request.protocol_type}，允许值: {VALID_PROTOCOL_TYPES}"
        )

    # 2. 校验连接配置基本结构
    conn_config = request.connection_config
    if not isinstance(conn_config, dict):
        raise DataValidationError("连接配置必须是字典格式")

    required_conn_fields = _get_required_conn_fields(request.protocol_type)
    missing_fields = [f for f in required_conn_fields if f not in conn_config]
    if missing_fields:
        raise DataValidationError(
            f"协议 {request.protocol_type} 缺少必要连接字段: {missing_fields}"
        )

    # 3. 创建数据源
    source = DataSource(
        name=request.name,
        protocol_type=request.protocol_type,
        connection_config=request.connection_config,
        device_did=request.device_did,
        mqtt_topic=request.mqtt_topic,
        collection_interval_ms=request.collection_interval_ms,
        is_critical=request.is_critical,
        edge_preprocess=request.edge_preprocess or {},
        organization_id=uuid.UUID(request.organization_id),
        created_by=uuid.UUID(user_id),
        status="active",
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    logger.info(f"Data source created: {source.id} ({source.name})")
    return DataSourceResponse.model_validate(source)


async def update_data_source(
    db: AsyncSession,
    source_id: str,
    request: DataSourceCreate,
) -> DataSourceResponse:
    """更新数据源配置"""
    result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(source_id))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise DataNotFoundError("数据源未找到")

    # 不允许修改正在采集的数据源
    if source.status == "collecting":
        raise DataSourceError("数据源正在采集中，请先停止采集再修改")

    if request.protocol_type not in VALID_PROTOCOL_TYPES:
        raise DataValidationError(f"不支持的协议类型: {request.protocol_type}")

    source.name = request.name
    source.protocol_type = request.protocol_type
    source.connection_config = request.connection_config
    source.device_did = request.device_did
    source.mqtt_topic = request.mqtt_topic
    source.collection_interval_ms = request.collection_interval_ms
    source.is_critical = request.is_critical
    if request.edge_preprocess is not None:
        source.edge_preprocess = request.edge_preprocess

    await db.commit()
    await db.refresh(source)

    logger.info(f"Data source updated: {source.id}")
    return DataSourceResponse.model_validate(source)


async def delete_data_source(
    db: AsyncSession,
    source_id: str,
) -> None:
    """删除数据源（软删除）"""
    result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(source_id))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise DataNotFoundError("数据源未找到")

    if source.status == "collecting":
        raise DataSourceError("数据源正在采集中，请先停止采集再删除")

    source.status = "deleted"
    await db.commit()
    logger.info(f"Data source deleted: {source.id}")


async def start_collection(
    db: AsyncSession,
    source_id: str,
) -> dict:
    """
    启动数据采集

    1. 校验数据源状态
    2. 通过 MQTT 发布启动指令
    3. 更新状态为 collecting
    """
    result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(source_id))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise DataNotFoundError("数据源未找到")

    if source.status == "collecting":
        raise DataSourceError("数据源已在采集中")

    # 发布 MQTT 启动消息
    topic = source.mqtt_topic or f"energy/collect/{source.device_did or 'default'}"
    mqtt_manager.publish(f"{topic}/start", str(source.id))

    source.status = "collecting"
    await db.commit()

    logger.info(f"Collection started for source: {source.id}")
    return {
        "source_id": str(source.id),
        "status": "collecting",
        "protocol_type": source.protocol_type,
        "collection_interval_ms": source.collection_interval_ms,
        "mqtt_topic": topic,
    }


async def stop_collection(
    db: AsyncSession,
    source_id: str,
) -> dict:
    """停止数据采集"""
    result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(source_id))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise DataNotFoundError("数据源未找到")

    if source.status != "collecting":
        raise DataSourceError("数据源未在采集中")

    # 发布 MQTT 停止消息
    topic = source.mqtt_topic or f"energy/collect/{source.device_did or 'default'}"
    mqtt_manager.publish(f"{topic}/stop", str(source.id))

    source.status = "stopped"
    await db.commit()

    logger.info(f"Collection stopped for source: {source.id}")
    return {
        "source_id": str(source.id),
        "status": "stopped",
    }


async def get_collection_status(
    db: AsyncSession,
    source_id: str,
) -> dict:
    """获取采集状态"""
    result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(source_id))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise DataNotFoundError("数据源未找到")

    return {
        "source_id": str(source.id),
        "status": source.status,
        "protocol_type": source.protocol_type,
        "device_did": source.device_did,
        "collection_interval_ms": source.collection_interval_ms,
        "is_critical": source.is_critical,
    }


async def get_collection_metrics(
    db: AsyncSession,
    source_id: str,
) -> dict:
    """
    获取采集指标

    包括采集频率、最近访问记录统计等
    """
    result = await db.execute(
        select(DataSource).where(DataSource.id == uuid.UUID(source_id))
    )
    source = result.scalar_one_or_none()
    if not source:
        raise DataNotFoundError("数据源未找到")

    # 查询该数据源关联资产的访问统计
    access_count_result = await db.execute(
        select(func.count(AccessLog.id)).where(
            AccessLog.asset_id.in_(
                select(DataSource.assets).where(DataSource.id == source.id)
            )
        )
    )
    access_count = access_count_result.scalar() or 0

    return {
        "source_id": str(source.id),
        "status": source.status,
        "protocol_type": source.protocol_type,
        "collection_interval_ms": source.collection_interval_ms,
        "is_critical": source.is_critical,
        "edge_preprocess": source.edge_preprocess,
        "access_count": access_count,
        "mqtt_connected": mqtt_manager._connected,
    }


def _get_required_conn_fields(protocol_type: str) -> list[str]:
    """获取协议类型所需的连接配置字段"""
    fields_map = {
        "DLMS": ["host", "port", "logical_address"],
        "Modbus": ["host", "port", "unit_id"],
        "HTTP": ["url", "method"],
        "WebSocket": ["url"],
        "OPC-UA": ["endpoint_url"],
        "MQTT": ["broker", "topic"],
    }
    return fields_map.get(protocol_type, [])
