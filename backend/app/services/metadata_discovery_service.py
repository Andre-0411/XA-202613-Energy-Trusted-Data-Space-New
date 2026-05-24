"""
元数据发现服务
自动发现连接器中的数据结构/字段信息
"""
import uuid
import logging
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Connector
from app.models.connector_file import ConnectorFile
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


async def discover_metadata_from_connector(
    db: AsyncSession,
    connector_id: str,
    discover_type: str = "auto",
) -> dict:
    """从连接器发现元数据"""
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    discovered_fields = []
    tables = []

    if connector.protocol_type in ("http", "https", "rest"):
        # HTTP/REST 类型：从 connection_config 推断
        config = connector.connection_config or {}
        endpoint = config.get("endpoint", "")
        discovered_fields = [
            {"name": "endpoint", "type": "string", "value": endpoint},
            {"name": "method", "type": "string", "value": config.get("method", "GET")},
        ]
        tables = [{"name": "api_response", "fields": discovered_fields}]

    elif connector.protocol_type in ("modbus", "mqtt", "iec61850", "opcua", "dlms"):
        # IoT 协议类型：从 topic/register 映射推断
        config = connector.connection_config or {}
        discovered_fields = [
            {"name": "topic", "type": "string", "value": config.get("topic", "")},
            {"name": "qos", "type": "integer", "value": config.get("qos", 0)},
        ]
        tables = [{"name": "iot_data", "fields": discovered_fields}]

    elif connector.protocol_type in ("jdbc", "postgresql", "mysql"):
        # 数据库类型
        config = connector.connection_config or {}
        discovered_fields = [
            {"name": "database", "type": "string", "value": config.get("database", "")},
            {"name": "schema", "type": "string", "value": config.get("schema", "public")},
        ]
        tables = [{"name": "db_tables", "fields": discovered_fields}]

    else:
        discovered_fields = []
        tables = []

    logger.info(f"Metadata discovered for connector {connector_id}: {len(tables)} tables")
    return {
        "connector_id": connector_id,
        "protocol_type": connector.protocol_type,
        "discover_type": discover_type,
        "tables": tables,
        "field_count": sum(len(t.get("fields", [])) for t in tables),
        "discovered_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


async def discover_metadata_from_file(
    db: AsyncSession,
    file_id: str,
) -> dict:
    """从已上传的文件发现元数据"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id))
    )
    file_obj = result.scalar_one_or_none()
    if not file_obj:
        raise DataNotFoundError("文件不存在")

    columns = file_obj.column_schema or []
    file_type = file_obj.file_type
    row_count = file_obj.row_count or 0

    # 根据列结构推断字段类型
    enriched_columns = []
    for col in columns:
        if isinstance(col, dict):
            enriched_columns.append({
                "name": col.get("name", "unknown"),
                "type": col.get("type", "string"),
                "nullable": col.get("nullable", True),
                "description": col.get("description", ""),
            })

    logger.info(f"Metadata discovered for file {file_id}: {len(enriched_columns)} columns")
    return {
        "file_id": file_id,
        "file_name": file_obj.file_name,
        "file_type": file_type,
        "row_count": row_count,
        "columns": enriched_columns,
        "column_count": len(enriched_columns),
        "discovered_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


async def get_connector_schema_summary(
    db: AsyncSession,
    connector_id: str,
) -> dict:
    """获取连接器的 schema 摘要"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.connector_id == uuid.UUID(connector_id))
    )
    files = result.scalars().all()

    total_rows = sum(f.row_count or 0 for f in files)
    total_size = sum(f.file_size_bytes or 0 for f in files)
    file_types = list(set(f.file_type for f in files))

    all_columns = set()
    for f in files:
        for col in (f.column_schema or []):
            if isinstance(col, dict):
                all_columns.add(col.get("name", ""))

    return {
        "connector_id": connector_id,
        "file_count": len(files),
        "total_rows": total_rows,
        "total_size_bytes": total_size,
        "file_types": file_types,
        "unique_columns": sorted(list(all_columns - {""})),
    }
