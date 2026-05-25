"""
连接器管理服务
连接器部署管理 / 文件库管理 / API代理管理 / 状态管理
"""
import uuid
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Connector, ConnectorDataSource, MetadataDiscovery
from app.models.connector_file import ConnectorFile, FileSet, ApiProxy
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    DataNotFoundError, DataValidationError, DataAlreadyExistsError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


# ==================== 连接器部署管理 ====================

VALID_CONNECTOR_TYPES = ("lite", "standard", "custom")
VALID_CONNECTOR_STATUSES = ("offline", "deploying", "verifying", "running", "stopped", "error", "maintenance")


async def create_connector(
    db: AsyncSession,
    name: str,
    connector_type: str,
    organization_id: str,
    created_by: str,
    deployment_config: Optional[dict] = None,
    version: Optional[str] = None,
) -> dict:
    """创建连接器（选择类型 → 配置参数）"""
    if connector_type not in VALID_CONNECTOR_TYPES:
        raise DataValidationError(f"无效的连接器类型: {connector_type}, 可选: {VALID_CONNECTOR_TYPES}")

    connector = Connector(
        name=name,
        connector_type=connector_type,
        organization_id=uuid.UUID(organization_id),
        deployment_config=deployment_config or {},
        version=version,
        status="offline",
        created_by=uuid.UUID(created_by),
    )
    db.add(connector)
    await db.commit()
    await db.refresh(connector)

    logger.info(f"Connector created: {name}, type={connector_type}, org={organization_id}")
    return _connector_to_dict(connector)


async def deploy_connector(db: AsyncSession, connector_id: str) -> dict:
    """部署连接器（offline/deploying → deploying）"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    if connector.status not in ("offline", "error"):
        raise DataValidationError(f"当前状态不允许部署: {connector.status}")

    connector.status = "deploying"
    await db.commit()
    await db.refresh(connector)
    logger.info(f"Connector deploying: {connector_id}")
    return _connector_to_dict(connector)


async def verify_connector(db: AsyncSession, connector_id: str) -> dict:
    """验证连接器（deploying → verifying）"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    if connector.status != "deploying":
        raise DataValidationError(f"当前状态不允许验证: {connector.status}")

    connector.status = "verifying"
    await db.commit()
    await db.refresh(connector)
    logger.info(f"Connector verifying: {connector_id}")
    return _connector_to_dict(connector)


async def activate_connector(db: AsyncSession, connector_id: str) -> dict:
    """激活连接器（verifying → running）"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    if connector.status != "verifying":
        raise DataValidationError(f"当前状态不允许激活: {connector.status}")

    connector.status = "running"
    connector.last_heartbeat = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(connector)
    logger.info(f"Connector activated: {connector_id}")
    return _connector_to_dict(connector)


async def stop_connector(db: AsyncSession, connector_id: str) -> dict:
    """停止连接器"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    if connector.status not in ("running", "maintenance"):
        raise DataValidationError(f"当前状态不允许停止: {connector.status}")

    connector.status = "stopped"
    await db.commit()
    await db.refresh(connector)
    logger.info(f"Connector stopped: {connector_id}")
    return _connector_to_dict(connector)


async def set_connector_maintenance(db: AsyncSession, connector_id: str) -> dict:
    """设置连接器为维护状态"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    if connector.status not in ("running", "stopped"):
        raise DataValidationError(f"当前状态不允许设为维护中: {connector.status}")

    connector.status = "maintenance"
    await db.commit()
    await db.refresh(connector)
    logger.info(f"Connector set to maintenance: {connector_id}")
    return _connector_to_dict(connector)


async def heartbeat_connector(db: AsyncSession, connector_id: str) -> dict:
    """连接器心跳上报"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    connector.last_heartbeat = datetime.now(timezone.utc)
    if connector.status == "stopped":
        connector.status = "running"
    await db.commit()
    await db.refresh(connector)
    return _connector_to_dict(connector)


async def update_connector(
    db: AsyncSession, connector_id: str, **kwargs,
) -> dict:
    """更新连接器配置"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    for field in ["name", "deployment_config", "version"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(connector, field, kwargs[field])

    await db.commit()
    await db.refresh(connector)
    logger.info(f"Connector updated: {connector_id}")
    return _connector_to_dict(connector)


async def get_connector(db: AsyncSession, connector_id: str) -> dict:
    """获取连接器详情"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    return _connector_to_dict(connector)


async def list_connectors(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    connector_type: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出连接器"""
    query = select(Connector)
    if organization_id:
        query = query.where(Connector.organization_id == uuid.UUID(organization_id))
    if connector_type:
        query = query.where(Connector.connector_type == connector_type)
    if status:
        query = query.where(Connector.status == status)
    query = query.order_by(Connector.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def delete_connector(db: AsyncSession, connector_id: str) -> bool:
    """删除连接器"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    if connector.status == "running":
        raise DataValidationError("运行中的连接器不可删除，请先停止")

    await db.delete(connector)
    await db.commit()
    logger.info(f"Connector deleted: {connector_id}")
    return True


# ==================== 数据源管理 ====================

async def create_data_source(
    db: AsyncSession,
    connector_id: str,
    name: str,
    db_type: str,
    host: str,
    port: int,
    username: Optional[str] = None,
    password_encrypted: Optional[str] = None,
    database_name: Optional[str] = None,
    schema_name: Optional[str] = None,
) -> dict:
    """创建数据源配置"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    ds = ConnectorDataSource(
        connector_id=uuid.UUID(connector_id),
        name=name,
        db_type=db_type,
        host=host,
        port=port,
        username=username,
        password_encrypted=password_encrypted,
        database_name=database_name,
        schema_name=schema_name,
        status="active",
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    logger.info(f"Data source created: {name} for connector={connector_id}")
    return _data_source_to_dict(ds)


async def list_data_sources(
    db: AsyncSession,
    params: PaginationParams,
    connector_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出数据源"""
    query = select(ConnectorDataSource)
    if connector_id:
        query = query.where(ConnectorDataSource.connector_id == uuid.UUID(connector_id))
    if status:
        query = query.where(ConnectorDataSource.status == status)
    query = query.order_by(ConnectorDataSource.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def update_data_source(db: AsyncSession, data_source_id: str, **kwargs) -> dict:
    """更新数据源配置"""
    result = await db.execute(
        select(ConnectorDataSource).where(ConnectorDataSource.id == uuid.UUID(data_source_id))
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise DataNotFoundError("数据源不存在")

    for field in ["name", "db_type", "host", "port", "username", "password_encrypted",
                  "database_name", "schema_name", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(ds, field, kwargs[field])

    await db.commit()
    await db.refresh(ds)
    logger.info(f"Data source updated: {data_source_id}")
    return _data_source_to_dict(ds)


async def delete_data_source(db: AsyncSession, data_source_id: str) -> bool:
    """删除数据源"""
    result = await db.execute(
        select(ConnectorDataSource).where(ConnectorDataSource.id == uuid.UUID(data_source_id))
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise DataNotFoundError("数据源不存在")

    await db.delete(ds)
    await db.commit()
    logger.info(f"Data source deleted: {data_source_id}")
    return True


# ==================== 元数据发现 ====================

async def record_metadata_discovery(
    db: AsyncSession,
    data_source_id: str,
    table_name: str,
    columns: list,
    table_comment: Optional[str] = None,
    column_count: Optional[int] = None,
    row_count: Optional[int] = None,
    security_level: str = "public",
    sensitive_fields: Optional[list] = None,
) -> dict:
    """记录元数据发现"""
    result = await db.execute(
        select(ConnectorDataSource).where(ConnectorDataSource.id == uuid.UUID(data_source_id))
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise DataNotFoundError("数据源不存在")

    discovery = MetadataDiscovery(
        data_source_id=uuid.UUID(data_source_id),
        table_name=table_name,
        table_comment=table_comment,
        column_count=column_count or len(columns),
        row_count=row_count,
        columns=columns,
        security_level=security_level,
        sensitive_fields=sensitive_fields or [],
    )
    db.add(discovery)
    ds.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(discovery)

    logger.info(f"Metadata discovery recorded: table={table_name}, source={data_source_id}")
    return _discovery_to_dict(discovery)


async def list_discoveries(
    db: AsyncSession,
    params: PaginationParams,
    data_source_id: Optional[str] = None,
    security_level: Optional[str] = None,
) -> PaginatedResponse:
    """列出元数据发现记录"""
    query = select(MetadataDiscovery)
    if data_source_id:
        query = query.where(MetadataDiscovery.data_source_id == uuid.UUID(data_source_id))
    if security_level:
        query = query.where(MetadataDiscovery.security_level == security_level)
    query = query.order_by(MetadataDiscovery.discovered_at.desc())

    result = await paginate_query(db, query, params)
    return result


# ==================== 文件库管理 ====================

async def create_file_set(
    db: AsyncSession,
    name: str,
    organization_id: str,
    created_by: str,
    description: Optional[str] = None,
) -> dict:
    """创建文件集"""
    fs = FileSet(
        name=name,
        description=description,
        organization_id=uuid.UUID(organization_id),
        created_by=uuid.UUID(created_by),
        status="active",
    )
    db.add(fs)
    await db.commit()
    await db.refresh(fs)
    logger.info(f"File set created: {name}, org={organization_id}")
    return _file_set_to_dict(fs)


async def list_file_sets(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出文件集"""
    query = select(FileSet)
    if organization_id:
        query = query.where(FileSet.organization_id == uuid.UUID(organization_id))
    if status:
        query = query.where(FileSet.status == status)
    query = query.order_by(FileSet.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def upload_file(
    db: AsyncSession,
    connector_id: str,
    file_name: str,
    file_path: str,
    file_type: str,
    file_size_bytes: int,
    uploaded_by: str,
    file_set_id: Optional[str] = None,
    content_hash: Optional[str] = None,
    row_count: Optional[int] = None,
    column_schema: Optional[list] = None,
    metadata_: Optional[dict] = None,
) -> dict:
    """上传文件到连接器"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    cf = ConnectorFile(
        connector_id=uuid.UUID(connector_id),
        file_set_id=uuid.UUID(file_set_id) if file_set_id else None,
        file_name=file_name,
        file_path=file_path,
        file_type=file_type,
        file_size_bytes=file_size_bytes,
        content_hash=content_hash,
        row_count=row_count,
        column_schema=column_schema or [],
        metadata_=metadata_ or {},
        status="active",
        uploaded_by=uuid.UUID(uploaded_by),
    )
    db.add(cf)
    await db.commit()
    await db.refresh(cf)
    logger.info(f"File uploaded: {file_name} to connector={connector_id}")
    return _file_to_dict(cf)


async def list_files(
    db: AsyncSession,
    params: PaginationParams,
    connector_id: Optional[str] = None,
    file_set_id: Optional[str] = None,
    file_type: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出文件"""
    query = select(ConnectorFile)
    if connector_id:
        query = query.where(ConnectorFile.connector_id == uuid.UUID(connector_id))
    if file_set_id:
        query = query.where(ConnectorFile.file_set_id == uuid.UUID(file_set_id))
    if file_type:
        query = query.where(ConnectorFile.file_type == file_type)
    if status:
        query = query.where(ConnectorFile.status == status)
    query = query.order_by(ConnectorFile.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def get_file(db: AsyncSession, file_id: str) -> dict:
    """获取文件详情"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id))
    )
    f = result.scalar_one_or_none()
    if not f:
        raise DataNotFoundError("文件不存在")
    return _file_to_dict(f)


async def delete_file(db: AsyncSession, file_id: str) -> bool:
    """删除文件"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id))
    )
    f = result.scalar_one_or_none()
    if not f:
        raise DataNotFoundError("文件不存在")

    f.status = "deleted"
    await db.commit()
    logger.info(f"File deleted: {file_id}")
    return True


async def search_files(
    db: AsyncSession,
    params: PaginationParams,
    keyword: str,
    connector_id: Optional[str] = None,
    file_type: Optional[str] = None,
) -> PaginatedResponse:
    """搜索文件"""
    query = select(ConnectorFile).where(
        ConnectorFile.status == "active",
        ConnectorFile.file_name.ilike(f"%{keyword}%"),
    )
    if connector_id:
        query = query.where(ConnectorFile.connector_id == uuid.UUID(connector_id))
    if file_type:
        query = query.where(ConnectorFile.file_type == file_type)
    query = query.order_by(ConnectorFile.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


# ==================== API代理管理 ====================

async def register_api_proxy(
    db: AsyncSession,
    connector_id: str,
    name: str,
    target_url: str,
    created_by: str,
    description: Optional[str] = None,
    http_method: str = "GET",
    request_headers: Optional[dict] = None,
    request_params: Optional[dict] = None,
    request_body_template: Optional[str] = None,
    response_mapping: Optional[dict] = None,
    auth_config: Optional[dict] = None,
    rate_limit: int = 60,
    timeout_ms: int = 30000,
    retry_count: int = 3,
) -> dict:
    """注册API端点"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    proxy = ApiProxy(
        connector_id=uuid.UUID(connector_id),
        name=name,
        description=description,
        target_url=target_url,
        http_method=http_method.upper(),
        request_headers=request_headers or {},
        request_params=request_params or {},
        request_body_template=request_body_template,
        response_mapping=response_mapping or {},
        auth_config=auth_config or {},
        rate_limit=rate_limit,
        timeout_ms=timeout_ms,
        retry_count=retry_count,
        is_enabled=True,
        status="active",
        created_by=uuid.UUID(created_by),
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    logger.info(f"API proxy registered: {name} for connector={connector_id}")
    return _api_proxy_to_dict(proxy)


async def list_api_proxies(
    db: AsyncSession,
    params: PaginationParams,
    connector_id: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出API代理"""
    query = select(ApiProxy)
    if connector_id:
        query = query.where(ApiProxy.connector_id == uuid.UUID(connector_id))
    if is_enabled is not None:
        query = query.where(ApiProxy.is_enabled == is_enabled)
    if status:
        query = query.where(ApiProxy.status == status)
    query = query.order_by(ApiProxy.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def update_api_proxy(db: AsyncSession, proxy_id: str, **kwargs) -> dict:
    """更新API代理配置"""
    result = await db.execute(
        select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id))
    )
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")

    allowed = [
        "name", "description", "target_url", "http_method", "request_headers",
        "request_params", "request_body_template", "response_mapping",
        "auth_config", "rate_limit", "timeout_ms", "retry_count", "is_enabled",
    ]
    for field in allowed:
        if field in kwargs and kwargs[field] is not None:
            setattr(proxy, field, kwargs[field])

    await db.commit()
    await db.refresh(proxy)
    logger.info(f"API proxy updated: {proxy_id}")
    return _api_proxy_to_dict(proxy)


async def toggle_api_proxy(db: AsyncSession, proxy_id: str, enabled: bool) -> dict:
    """启用/禁用API代理"""
    result = await db.execute(
        select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id))
    )
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")

    proxy.is_enabled = enabled
    await db.commit()
    await db.refresh(proxy)
    logger.info(f"API proxy {'enabled' if enabled else 'disabled'}: {proxy_id}")
    return _api_proxy_to_dict(proxy)


async def delete_api_proxy(db: AsyncSession, proxy_id: str) -> bool:
    """删除API代理"""
    result = await db.execute(
        select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id))
    )
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")

    await db.delete(proxy)
    await db.commit()
    logger.info(f"API proxy deleted: {proxy_id}")
    return True


# ==================== Helpers ====================

def _connector_to_dict(c: Connector) -> dict:
    """连接器转字典"""
    return {
        "id": str(c.id),
        "name": c.name,
        "connector_type": c.connector_type,
        "version": c.version,
        "organization_id": str(c.organization_id),
        "deployment_config": c.deployment_config or {},
        "status": c.status,
        "last_heartbeat": c.last_heartbeat.isoformat() if c.last_heartbeat else None,
        "registered_at": c.registered_at.isoformat() if c.registered_at else None,
        "created_by": str(c.created_by) if c.created_by else None,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def _data_source_to_dict(ds: ConnectorDataSource) -> dict:
    """数据源转字典"""
    return {
        "id": str(ds.id),
        "connector_id": str(ds.connector_id),
        "name": ds.name,
        "db_type": ds.db_type,
        "host": ds.host,
        "port": ds.port,
        "username": ds.username,
        "database_name": ds.database_name,
        "schema_name": ds.schema_name,
        "status": ds.status,
        "last_sync_at": ds.last_sync_at.isoformat() if ds.last_sync_at else None,
        "created_at": ds.created_at.isoformat(),
    }


def _discovery_to_dict(d: MetadataDiscovery) -> dict:
    """元数据发现转字典"""
    return {
        "id": str(d.id),
        "data_source_id": str(d.data_source_id),
        "table_name": d.table_name,
        "table_comment": d.table_comment,
        "column_count": d.column_count,
        "row_count": d.row_count,
        "columns": d.columns or [],
        "security_level": d.security_level,
        "sensitive_fields": d.sensitive_fields or [],
        "discovered_at": d.discovered_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


def _file_set_to_dict(fs: FileSet) -> dict:
    """文件集转字典"""
    return {
        "id": str(fs.id),
        "name": fs.name,
        "description": fs.description,
        "organization_id": str(fs.organization_id),
        "created_by": str(fs.created_by),
        "status": fs.status,
        "created_at": fs.created_at.isoformat(),
        "updated_at": fs.updated_at.isoformat(),
    }


def _file_to_dict(f: ConnectorFile) -> dict:
    """文件转字典"""
    return {
        "id": str(f.id),
        "connector_id": str(f.connector_id),
        "file_set_id": str(f.file_set_id) if f.file_set_id else None,
        "file_name": f.file_name,
        "file_path": f.file_path,
        "file_type": f.file_type,
        "file_size_bytes": f.file_size_bytes,
        "content_hash": f.content_hash,
        "row_count": f.row_count,
        "column_schema": f.column_schema or [],
        "metadata": f.metadata_ or {},
        "status": f.status,
        "uploaded_by": str(f.uploaded_by),
        "created_at": f.created_at.isoformat(),
    }


def _api_proxy_to_dict(p: ApiProxy) -> dict:
    """API代理转字典"""
    return {
        "id": str(p.id),
        "connector_id": str(p.connector_id),
        "name": p.name,
        "description": p.description,
        "target_url": p.target_url,
        "http_method": p.http_method,
        "request_headers": p.request_headers or {},
        "request_params": p.request_params or {},
        "request_body_template": p.request_body_template,
        "response_mapping": p.response_mapping or {},
        "auth_config": p.auth_config or {},
        "rate_limit": p.rate_limit,
        "timeout_ms": p.timeout_ms,
        "retry_count": p.retry_count,
        "is_enabled": p.is_enabled,
        "status": p.status,
        "created_by": str(p.created_by),
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }
