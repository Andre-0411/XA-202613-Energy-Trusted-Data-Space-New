"""
连接器服务
连接器管理 / 数据源配置 / 元数据发现
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.connector import Connector, ConnectorDataSource, MetadataDiscovery
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


# ==================== 连接器 ====================

async def create_connector(
    db: AsyncSession,
    organization_id: str,
    name: str,
    connector_type: str = "lite",
    version: Optional[str] = None,
    deployment_config: Optional[dict] = None,
    created_by: Optional[str] = None,
) -> dict:
    """创建连接器"""
    connector = Connector(
        name=name,
        connector_type=connector_type,
        version=version,
        organization_id=uuid.UUID(organization_id),
        deployment_config=deployment_config or {},
        status="offline",
        created_by=uuid.UUID(created_by) if created_by else None,
    )
    db.add(connector)
    await db.commit()
    await db.refresh(connector)

    logger.info(f"Connector created: {name} in org {organization_id}")
    return _connector_to_dict(connector)


async def list_connectors(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
    connector_type: Optional[str] = None,
) -> PaginatedResponse:
    """列出连接器"""
    query = select(Connector).options(selectinload(Connector.data_sources))
    if organization_id:
        query = query.where(Connector.organization_id == uuid.UUID(organization_id))
    if status:
        query = query.where(Connector.status == status)
    if connector_type:
        query = query.where(Connector.connector_type == connector_type)
    query = query.order_by(Connector.registered_at.desc())

    from app.schemas.connector import ConnectorResponse
    result = await paginate_query(db, query, params, ConnectorResponse)
    return result


async def get_connector(db: AsyncSession, connector_id: str) -> dict:
    """获取连接器详情"""
    result = await db.execute(
        select(Connector)
        .options(selectinload(Connector.data_sources))
        .where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")
    return _connector_to_dict(connector, include_sources=True)


async def update_connector(db: AsyncSession, connector_id: str, **kwargs) -> dict:
    """更新连接器"""
    result = await db.execute(select(Connector).where(Connector.id == uuid.UUID(connector_id)))
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    for field in ["name", "connector_type", "version", "deployment_config", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(connector, field, kwargs[field])

    await db.commit()
    await db.refresh(connector)
    logger.info(f"Connector updated: {connector_id}")
    return _connector_to_dict(connector)


async def delete_connector(db: AsyncSession, connector_id: str) -> bool:
    """删除连接器"""
    result = await db.execute(select(Connector).where(Connector.id == uuid.UUID(connector_id)))
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    await db.delete(connector)
    await db.commit()
    logger.info(f"Connector deleted: {connector_id}")
    return True


async def connector_heartbeat(
    db: AsyncSession,
    connector_id: str,
    status: str,
    metrics: Optional[dict] = None,
) -> dict:
    """连接器心跳"""
    result = await db.execute(select(Connector).where(Connector.id == uuid.UUID(connector_id)))
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    connector.status = status
    connector.last_heartbeat = datetime.now(timezone.utc)
    await db.commit()

    logger.debug(f"Connector heartbeat: {connector_id}, status={status}")
    return {
        "id": str(connector.id),
        "status": connector.status,
        "last_heartbeat": connector.last_heartbeat.isoformat(),
    }


# ==================== 数据源配置 ====================

async def create_data_source(
    db: AsyncSession,
    connector_id: str,
    name: str,
    db_type: str,
    host: str,
    port: int,
    username: Optional[str] = None,
    password: Optional[str] = None,
    database_name: Optional[str] = None,
    schema_name: Optional[str] = None,
) -> dict:
    """创建数据源配置"""
    # 验证连接器存在
    conn_result = await db.execute(select(Connector).where(Connector.id == uuid.UUID(connector_id)))
    if not conn_result.scalar_one_or_none():
        raise DataNotFoundError("连接器不存在")

    ds = ConnectorDataSource(
        connector_id=uuid.UUID(connector_id),
        name=name,
        db_type=db_type,
        host=host,
        port=port,
        username=username,
        password_encrypted=password,  # TODO: SM4加密
        database_name=database_name,
        schema_name=schema_name,
        status="active",
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)

    logger.info(f"Connector data source created: {name} for connector {connector_id}")
    return _datasource_to_dict(ds)


async def list_data_sources(
    db: AsyncSession,
    params: PaginationParams,
    connector_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出数据源配置"""
    query = select(ConnectorDataSource)
    if connector_id:
        query = query.where(ConnectorDataSource.connector_id == uuid.UUID(connector_id))
    if status:
        query = query.where(ConnectorDataSource.status == status)
    query = query.order_by(ConnectorDataSource.created_at.desc())

    from app.schemas.connector import ConnectorDataSourceResponse
    result = await paginate_query(db, query, params, ConnectorDataSourceResponse)
    return result


async def get_data_source(db: AsyncSession, ds_id: str) -> dict:
    """获取数据源配置详情"""
    result = await db.execute(
        select(ConnectorDataSource).where(ConnectorDataSource.id == uuid.UUID(ds_id))
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise DataNotFoundError("数据源配置不存在")
    return _datasource_to_dict(ds)


async def update_data_source(db: AsyncSession, ds_id: str, **kwargs) -> dict:
    """更新数据源配置"""
    result = await db.execute(
        select(ConnectorDataSource).where(ConnectorDataSource.id == uuid.UUID(ds_id))
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise DataNotFoundError("数据源配置不存在")

    for field in ["name", "db_type", "host", "port", "username", "database_name", "schema_name", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(ds, field, kwargs[field])
    if "password" in kwargs and kwargs["password"] is not None:
        ds.password_encrypted = kwargs["password"]  # TODO: SM4加密

    await db.commit()
    await db.refresh(ds)
    logger.info(f"Connector data source updated: {ds_id}")
    return _datasource_to_dict(ds)


async def delete_data_source(db: AsyncSession, ds_id: str) -> bool:
    """删除数据源配置"""
    result = await db.execute(
        select(ConnectorDataSource).where(ConnectorDataSource.id == uuid.UUID(ds_id))
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise DataNotFoundError("数据源配置不存在")

    await db.delete(ds)
    await db.commit()
    logger.info(f"Connector data source deleted: {ds_id}")
    return True


# ==================== 元数据发现 ====================

async def trigger_metadata_discovery(
    db: AsyncSession,
    data_source_id: str,
    table_name: Optional[str] = None,
) -> dict:
    """触发元数据发现

    实际连接数据库查询 schema 信息，并将结果持久化到 MetadataDiscovery 表。
    当前实现为模拟采集，生产环境可替换为真实数据库 schema 查询逻辑。
    """
    # 验证数据源存在
    ds_result = await db.execute(
        select(ConnectorDataSource).where(ConnectorDataSource.id == uuid.UUID(data_source_id))
    )
    ds = ds_result.scalar_one_or_none()
    if not ds:
        raise DataNotFoundError("数据源配置不存在")

    # 根据 db_type 生成对应的默认表名
    # 实际生产环境应通过数据库连接查询 information_schema
    db_type_tables = {
        "postgresql": ["users", "orders", "data_assets", "transactions", "audit_logs"],
        "mysql": ["users", "orders", "products", "transactions", "logs"],
        "oracle": ["USERS", "ORDERS", "PRODUCTS", "TRANSACTIONS", "LOG_TABLE"],
        "mssql": ["Users", "Orders", "Products", "Transactions", "AuditLogs"],
    }
    default_tables = db_type_tables.get(
        ds.db_type.lower() if ds.db_type else "postgresql",
        ["table_a", "table_b", "table_c", "table_d", "table_e"]
    )

    if table_name:
        table_names = [table_name]
    else:
        table_names = default_tables

    discovered_tables = []
    for tbl in table_names:
        # 检查是否已存在同名记录，存在则更新，不存在则新建
        existing = await db.execute(
            select(MetadataDiscovery).where(
                and_(
                    MetadataDiscovery.data_source_id == uuid.UUID(data_source_id),
                    MetadataDiscovery.table_name == tbl,
                )
            )
        )
        disc = existing.scalar_one_or_none()
        if disc:
            disc.updated_at = datetime.now(timezone.utc)
        else:
            disc = MetadataDiscovery(
                data_source_id=uuid.UUID(data_source_id),
                table_name=tbl,
                table_comment=f"表 {tbl}",
                column_count=5,
                row_count=0,  # 实际应查询 count(*)
                columns=[
                    {"name": "id", "type": "uuid", "nullable": False, "comment": "主键"},
                    {"name": "name", "type": "varchar(200)", "nullable": True, "comment": "名称"},
                    {"name": "status", "type": "varchar(20)", "nullable": False, "comment": "状态"},
                    {"name": "created_at", "type": "timestamp", "nullable": False, "comment": "创建时间"},
                    {"name": "updated_at", "type": "timestamp", "nullable": False, "comment": "更新时间"},
                ],
                security_level="internal",
                sensitive_fields=[],
            )
            db.add(disc)
        discovered_tables.append(tbl)

    # 更新数据源最后同步时间
    ds.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(
        f"Metadata discovery completed for data source {data_source_id} "
        f"({ds.db_type}@{ds.host}): {len(discovered_tables)} tables"
    )
    return {
        "data_source_id": data_source_id,
        "db_type": ds.db_type,
        "host": ds.host,
        "discovered_tables": discovered_tables,
        "total": len(discovered_tables),
    }


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

    from app.schemas.connector import MetadataDiscoveryResponse
    result = await paginate_query(db, query, params, MetadataDiscoveryResponse)
    return result


async def get_discovery(db: AsyncSession, discovery_id: str) -> dict:
    """获取元数据发现详情"""
    result = await db.execute(
        select(MetadataDiscovery).where(MetadataDiscovery.id == uuid.UUID(discovery_id))
    )
    discovery = result.scalar_one_or_none()
    if not discovery:
        raise DataNotFoundError("元数据发现记录不存在")
    return {
        "id": str(discovery.id),
        "data_source_id": str(discovery.data_source_id),
        "table_name": discovery.table_name,
        "table_comment": discovery.table_comment,
        "column_count": discovery.column_count,
        "row_count": discovery.row_count,
        "columns": discovery.columns,
        "security_level": discovery.security_level,
        "sensitive_fields": discovery.sensitive_fields,
        "discovered_at": discovery.discovered_at.isoformat(),
        "updated_at": discovery.updated_at.isoformat(),
    }


async def update_discovery_security(
    db: AsyncSession,
    discovery_id: str,
    security_level: str,
    sensitive_fields: Optional[list] = None,
) -> dict:
    """更新元数据安全等级"""
    result = await db.execute(
        select(MetadataDiscovery).where(MetadataDiscovery.id == uuid.UUID(discovery_id))
    )
    discovery = result.scalar_one_or_none()
    if not discovery:
        raise DataNotFoundError("元数据发现记录不存在")

    discovery.security_level = security_level
    if sensitive_fields is not None:
        discovery.sensitive_fields = sensitive_fields
    await db.commit()

    logger.info(f"Discovery {discovery_id} security level updated to {security_level}")
    return {
        "id": str(discovery.id),
        "security_level": discovery.security_level,
        "sensitive_fields": discovery.sensitive_fields,
    }


# ==================== 辅助函数 ====================

def _connector_to_dict(connector: Connector, include_sources: bool = False) -> dict:
    """连接器转字典"""
    data = {
        "id": str(connector.id),
        "name": connector.name,
        "connector_type": connector.connector_type,
        "version": connector.version,
        "organization_id": str(connector.organization_id),
        "deployment_config": connector.deployment_config,
        "status": connector.status,
        "last_heartbeat": connector.last_heartbeat.isoformat() if connector.last_heartbeat else None,
        "registered_at": connector.registered_at.isoformat(),
        "created_by": str(connector.created_by) if connector.created_by else None,
    }
    if include_sources and hasattr(connector, "data_sources"):
        data["data_sources"] = [_datasource_to_dict(ds) for ds in (connector.data_sources or [])]
    else:
        data["data_sources"] = []
    return data


def _datasource_to_dict(ds: ConnectorDataSource) -> dict:
    """数据源配置转字典"""
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
