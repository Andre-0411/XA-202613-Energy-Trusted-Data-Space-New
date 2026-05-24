"""数据源 API - /api/v1/data/sources"""
import uuid
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.data_asset import DataSource
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.data_asset import (
    DataSourceCreate, DataSourceResponse,
    ProtocolTestRequest, ProtocolTestResponse, ProtocolInfoResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.utils.pagination import paginate_query
from app.services.mqtt_client import mqtt_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ApiResponse[PaginatedResponse[DataSourceResponse]])
async def list_data_sources(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """数据源列表"""
    query = select(DataSource)
    org_id = user.get("organization_id")
    if org_id:
        query = query.where(DataSource.organization_id == org_id)
    result = await paginate_query(db, query, pagination, DataSourceResponse)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[DataSourceResponse], status_code=201)
async def create_data_source(
    request: DataSourceCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """注册数据源"""
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
        created_by=uuid.UUID(user["user_id"]),
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return ApiResponse(data=DataSourceResponse.model_validate(source))


@router.get("/{source_id}", response_model=ApiResponse[DataSourceResponse])
async def get_data_source(source_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """数据源详情"""
    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)
    return ApiResponse(data=DataSourceResponse.model_validate(source))


@router.put("/{source_id}", response_model=ApiResponse[DataSourceResponse])
async def update_data_source(
    source_id: str, request: DataSourceCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user),
):
    """更新数据源"""
    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)
    source.name = request.name
    source.protocol_type = request.protocol_type
    source.connection_config = request.connection_config
    source.device_did = request.device_did
    source.mqtt_topic = request.mqtt_topic
    source.collection_interval_ms = request.collection_interval_ms
    source.is_critical = request.is_critical
    await db.commit()
    await db.refresh(source)
    return ApiResponse(data=DataSourceResponse.model_validate(source))


@router.delete("/{source_id}", response_model=ApiResponse)
async def delete_data_source(source_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """删除数据源"""
    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)
    source.status = "deleted"
    await db.commit()
    return ApiResponse(message="已删除")


@router.post("/{source_id}/start", response_model=ApiResponse)
async def start_collection(source_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """启动采集"""
    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)
    source.status = "collecting"
    await db.commit()
    # 发布 MQTT 启动消息
    if source.mqtt_topic:
        mqtt_manager.publish(f"energy/collect/{source.device_did or 'default'}/start", source_id)
    return ApiResponse(message="采集已启动")


@router.post("/{source_id}/stop", response_model=ApiResponse)
async def stop_collection(source_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """停止采集"""
    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)
    source.status = "stopped"
    await db.commit()
    return ApiResponse(message="采集已停止")


@router.get("/{source_id}/status", response_model=ApiResponse)
async def get_collection_status(source_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """采集状态"""
    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)
    return ApiResponse(data={"status": source.status, "protocol_type": source.protocol_type})


@router.get("/{source_id}/metrics", response_model=ApiResponse)
async def get_collection_metrics(source_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """采集指标"""
    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)
    return ApiResponse(data={
        "collection_interval_ms": source.collection_interval_ms,
        "is_critical": source.is_critical,
        "status": source.status,
    })


# ==================== 协议适配器端点 ====================


@router.get("/protocols/info", response_model=ApiResponse[ProtocolInfoResponse])
async def get_protocol_info():
    """
    获取支持的协议适配器信息

    返回已注册的协议适配器列表和支持的协议类型。
    """
    # 触发适配器注册
    import app.services.dlms_adapter  # noqa: F401
    import app.services.modbus_adapter  # noqa: F401
    import app.services.iec61850_adapter  # noqa: F401

    from app.services.protocol_adapter import ProtocolAdapterFactory

    return ApiResponse(data=ProtocolInfoResponse(
        supported_protocols=ProtocolAdapterFactory.supported_protocols(),
        adapter_info=ProtocolAdapterFactory.get_adapter_info(),
    ))


@router.post("/protocols/test", response_model=ApiResponse[ProtocolTestResponse])
async def test_protocol_connection(
    request: ProtocolTestRequest,
    user: dict = Depends(get_current_user),
):
    """
    测试协议连接

    根据提供的协议类型和连接配置，尝试建立协议连接并返回连接状态。
    支持 DLMS/Modbus/IEC61850 三种协议。
    """
    # 触发适配器注册
    import app.services.dlms_adapter  # noqa: F401
    import app.services.modbus_adapter  # noqa: F401
    import app.services.iec61850_adapter  # noqa: F401

    from app.services.protocol_adapter import (
        ProtocolAdapterFactory, ProtocolConfig, ProtocolType,
    )

    # 映射协议类型
    protocol_map = {
        "DLMS": ProtocolType.DLMS,
        "Modbus": ProtocolType.MODBUS,
        "IEC61850": ProtocolType.IEC61850,
    }
    protocol_type = protocol_map.get(request.protocol_type)
    if not protocol_type:
        return ApiResponse(data=ProtocolTestResponse(
            protocol_type=request.protocol_type,
            connected=False,
            config_errors=[f"不支持的协议类型: {request.protocol_type}"],
        ))

    # 创建协议配置
    config = ProtocolConfig(
        protocol_type=protocol_type,
        host=request.host,
        port=request.port,
        auth=request.auth,
        device_address=request.device_address,
    )

    # 验证配置
    try:
        adapter = ProtocolAdapterFactory.create(config)
    except ValueError as e:
        return ApiResponse(data=ProtocolTestResponse(
            protocol_type=request.protocol_type,
            connected=False,
            config_errors=[str(e)],
        ))

    # 配置验证
    config_errors = adapter.validate_config()

    # 尝试连接
    connected = False
    try:
        connected = await adapter.connect()
    except Exception as e:
        logger.error(f"协议连接测试失败: {e}")
        config_errors.append(f"连接异常: {str(e)}")
    finally:
        if adapter.is_connected:
            await adapter.disconnect()

    return ApiResponse(data=ProtocolTestResponse(
        protocol_type=request.protocol_type,
        connected=connected,
        device_did=adapter.device_did if connected else None,
        config_errors=config_errors,
        adapter_status=adapter.get_status(),
    ))


@router.get("/{source_id}/protocol/status", response_model=ApiResponse)
async def get_protocol_status(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    获取数据源的协议适配器状态

    返回协议类型、连接配置校验结果和适配器可用性。
    """
    # 触发适配器注册
    import app.services.dlms_adapter  # noqa: F401
    import app.services.modbus_adapter  # noqa: F401
    import app.services.iec61850_adapter  # noqa: F401

    from app.services.protocol_adapter import (
        ProtocolAdapterFactory, ProtocolConfig, ProtocolType,
    )

    result = await db.execute(select(DataSource).where(DataSource.id == uuid.UUID(source_id)))
    source = result.scalar_one_or_none()
    if not source:
        return ApiResponse(code=2001, message="数据源未找到", data=None)

    # 映射协议类型
    protocol_map = {
        "DLMS": ProtocolType.DLMS,
        "Modbus": ProtocolType.MODBUS,
        "IEC61850": ProtocolType.IEC61850,
    }
    protocol_type = protocol_map.get(source.protocol_type)

    adapter_available = False
    config_errors: list[str] = []

    if protocol_type:
        config = ProtocolConfig(
            protocol_type=protocol_type,
            host=source.connection_config.get("host", "localhost"),
            port=source.connection_config.get("port", 0),
            auth=source.connection_config.get("auth"),
            device_address=source.device_did,
        )
        try:
            adapter = ProtocolAdapterFactory.create(config)
            config_errors = adapter.validate_config()
            adapter_available = True
        except ValueError as e:
            config_errors = [str(e)]

    return ApiResponse(data={
        "source_id": source_id,
        "protocol_type": source.protocol_type,
        "status": source.status,
        "adapter_available": adapter_available,
        "config_errors": config_errors,
        "connection_config": {
            "host": source.connection_config.get("host"),
            "port": source.connection_config.get("port"),
        },
    })
