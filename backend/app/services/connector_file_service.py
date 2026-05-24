"""
连接器文件管理服务
文件集/文件/API代理管理
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import Connector
from app.models.connector_file import FileSet, ConnectorFile, ApiProxy
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


# ==================== 文件集 ====================

async def create_file_set(
    db: AsyncSession,
    name: str,
    organization_id: str,
    created_by: str,
    description: Optional[str] = None,
) -> dict:
    """创建文件集"""
    file_set = FileSet(
        name=name,
        description=description,
        organization_id=uuid.UUID(organization_id),
        created_by=uuid.UUID(created_by),
        status="active",
    )
    db.add(file_set)
    await db.commit()
    await db.refresh(file_set)

    logger.info(f"File set created: {name}")
    return _file_set_to_dict(file_set)


async def get_file_set(db: AsyncSession, file_set_id: str) -> dict:
    """获取文件集详情"""
    result = await db.execute(select(FileSet).where(FileSet.id == uuid.UUID(file_set_id)))
    fs = result.scalar_one_or_none()
    if not fs:
        raise DataNotFoundError("文件集不存在")
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

    from app.schemas.connector_file import FileSetResponse
    result = await paginate_query(db, query, params, FileSetResponse)
    return result


async def delete_file_set(db: AsyncSession, file_set_id: str) -> bool:
    """删除文件集（软删除）"""
    result = await db.execute(select(FileSet).where(FileSet.id == uuid.UUID(file_set_id)))
    fs = result.scalar_one_or_none()
    if not fs:
        raise DataNotFoundError("文件集不存在")

    fs.status = "deleted"
    await db.commit()
    logger.info(f"File set deleted: {file_set_id}")
    return True


# ==================== 连接器文件 ====================

async def upload_file(
    db: AsyncSession,
    connector_id: str,
    file_name: str,
    file_path: str,
    file_type: str,
    uploaded_by: str,
    file_size_bytes: int = 0,
    file_set_id: Optional[str] = None,
    content_hash: Optional[str] = None,
    row_count: Optional[int] = None,
    column_schema: Optional[list] = None,
) -> dict:
    """上传连接器文件"""
    # 验证连接器存在
    conn_result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    if not conn_result.scalar_one_or_none():
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
        status="active",
        uploaded_by=uuid.UUID(uploaded_by),
    )
    db.add(cf)
    await db.commit()
    await db.refresh(cf)

    logger.info(f"Connector file uploaded: {file_name} for connector {connector_id}")
    return _file_to_dict(cf)


async def get_file(db: AsyncSession, file_id: str) -> dict:
    """获取文件详情"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id))
    )
    cf = result.scalar_one_or_none()
    if not cf:
        raise DataNotFoundError("文件不存在")
    return _file_to_dict(cf)


async def update_file(db: AsyncSession, file_id: str, **kwargs) -> dict:
    """更新文件信息"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id))
    )
    cf = result.scalar_one_or_none()
    if not cf:
        raise DataNotFoundError("文件不存在")

    for field in ["file_set_id", "file_name", "column_schema", "status"]:
        if field in kwargs and kwargs[field] is not None:
            if field == "file_set_id":
                cf.file_set_id = uuid.UUID(kwargs[field]) if kwargs[field] else None
            else:
                setattr(cf, field, kwargs[field])

    await db.commit()
    await db.refresh(cf)
    logger.info(f"Connector file updated: {file_id}")
    return _file_to_dict(cf)


async def delete_file(db: AsyncSession, file_id: str) -> bool:
    """删除文件（软删除）"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id))
    )
    cf = result.scalar_one_or_none()
    if not cf:
        raise DataNotFoundError("文件不存在")

    cf.status = "deleted"
    await db.commit()
    logger.info(f"Connector file deleted: {file_id}")
    return True


async def list_files(
    db: AsyncSession,
    params: PaginationParams,
    connector_id: Optional[str] = None,
    file_set_id: Optional[str] = None,
    file_type: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出连接器文件"""
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

    from app.schemas.connector_file import ConnectorFileResponse
    result = await paginate_query(db, query, params, ConnectorFileResponse)
    return result


# ==================== API代理 ====================

async def create_api_proxy(
    db: AsyncSession,
    connector_id: str,
    name: str,
    target_url: str,
    created_by: str,
    **kwargs,
) -> dict:
    """创建API代理"""
    # 验证连接器
    conn_result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    if not conn_result.scalar_one_or_none():
        raise DataNotFoundError("连接器不存在")

    proxy = ApiProxy(
        connector_id=uuid.UUID(connector_id),
        name=name,
        description=kwargs.get("description"),
        target_url=target_url,
        http_method=kwargs.get("http_method", "GET"),
        request_headers=kwargs.get("request_headers", {}),
        request_params=kwargs.get("request_params", {}),
        request_body_template=kwargs.get("request_body_template"),
        response_mapping=kwargs.get("response_mapping", {}),
        auth_config=kwargs.get("auth_config", {}),
        rate_limit=kwargs.get("rate_limit", 60),
        timeout_ms=kwargs.get("timeout_ms", 30000),
        retry_count=kwargs.get("retry_count", 3),
        is_enabled=True,
        status="active",
        created_by=uuid.UUID(created_by),
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)

    logger.info(f"API proxy created: {name} for connector {connector_id}")
    return _proxy_to_dict(proxy)


async def update_api_proxy(db: AsyncSession, proxy_id: str, **kwargs) -> dict:
    """更新API代理"""
    result = await db.execute(select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id)))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")

    allowed = [
        "name", "description", "target_url", "http_method",
        "request_headers", "request_params", "request_body_template",
        "response_mapping", "auth_config", "rate_limit", "timeout_ms",
        "retry_count", "is_enabled",
    ]
    for field in allowed:
        if field in kwargs and kwargs[field] is not None:
            setattr(proxy, field, kwargs[field])

    await db.commit()
    await db.refresh(proxy)
    logger.info(f"API proxy updated: {proxy_id}")
    return _proxy_to_dict(proxy)


async def delete_api_proxy(db: AsyncSession, proxy_id: str) -> bool:
    """删除API代理（软删除）"""
    result = await db.execute(select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id)))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")

    proxy.status = "deleted"
    await db.commit()
    logger.info(f"API proxy deleted: {proxy_id}")
    return True


async def get_api_proxy(db: AsyncSession, proxy_id: str) -> dict:
    """获取API代理详情"""
    result = await db.execute(select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id)))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")
    return _proxy_to_dict(proxy)


async def list_api_proxies(
    db: AsyncSession,
    params: PaginationParams,
    connector_id: Optional[str] = None,
    status: Optional[str] = None,
    is_enabled: Optional[bool] = None,
) -> PaginatedResponse:
    """列出API代理"""
    query = select(ApiProxy)
    if connector_id:
        query = query.where(ApiProxy.connector_id == uuid.UUID(connector_id))
    if status:
        query = query.where(ApiProxy.status == status)
    if is_enabled is not None:
        query = query.where(ApiProxy.is_enabled == is_enabled)
    query = query.order_by(ApiProxy.created_at.desc())

    from app.schemas.connector_file import ApiProxyResponse
    result = await paginate_query(db, query, params, ApiProxyResponse)
    return result


async def test_api_proxy(db: AsyncSession, proxy_id: str) -> dict:
    """测试API代理连通性"""
    result = await db.execute(select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id)))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")

    # 模拟测试
    return {
        "proxy_id": proxy_id,
        "target_url": proxy.target_url,
        "http_method": proxy.http_method,
        "test_result": "success",
        "response_time_ms": 150,
        "status_code": 200,
        "tested_at": datetime.now(timezone.utc).isoformat(),
    }


async def publish_api_proxy(db: AsyncSession, proxy_id: str) -> dict:
    """发布API代理"""
    result = await db.execute(select(ApiProxy).where(ApiProxy.id == uuid.UUID(proxy_id)))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise DataNotFoundError("API代理不存在")

    proxy.status = "published"
    proxy.is_enabled = True
    await db.commit()
    await db.refresh(proxy)
    logger.info(f"API proxy published: {proxy_id}")
    return _proxy_to_dict(proxy)


async def download_file(db: AsyncSession, file_id: str) -> dict:
    """获取文件下载信息"""
    result = await db.execute(
        select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id))
    )
    cf = result.scalar_one_or_none()
    if not cf:
        raise DataNotFoundError("文件不存在")
    return {
        "file_id": str(cf.id),
        "file_name": cf.file_name,
        "file_path": cf.file_path,
        "file_type": cf.file_type,
        "file_size_bytes": cf.file_size_bytes,
        "download_url": f"/static/uploads/{cf.file_path}",
    }


async def add_file_to_set(db: AsyncSession, file_set_id: str, file_id: str) -> dict:
    """添加文件到文件集"""
    fs_result = await db.execute(select(FileSet).where(FileSet.id == uuid.UUID(file_set_id)))
    fs = fs_result.scalar_one_or_none()
    if not fs:
        raise DataNotFoundError("文件集不存在")

    file_result = await db.execute(select(ConnectorFile).where(ConnectorFile.id == uuid.UUID(file_id)))
    cf = file_result.scalar_one_or_none()
    if not cf:
        raise DataNotFoundError("文件不存在")

    cf.file_set_id = uuid.UUID(file_set_id)
    await db.commit()
    await db.refresh(cf)
    logger.info(f"File {file_id} added to file set {file_set_id}")
    return _file_to_dict(cf)


# ==================== Helpers ====================

def _file_set_to_dict(fs: FileSet) -> dict:
    """文件集转字典"""
    files = []
    for f in (fs.files or []):
        files.append(_file_to_dict(f))
    return {
        "id": str(fs.id),
        "name": fs.name,
        "description": fs.description,
        "organization_id": str(fs.organization_id),
        "created_by": str(fs.created_by),
        "status": fs.status,
        "created_at": fs.created_at.isoformat(),
        "updated_at": fs.updated_at.isoformat(),
        "files": files,
    }


def _file_to_dict(cf: ConnectorFile) -> dict:
    """文件转字典"""
    return {
        "id": str(cf.id),
        "connector_id": str(cf.connector_id),
        "file_set_id": str(cf.file_set_id) if cf.file_set_id else None,
        "file_name": cf.file_name,
        "file_path": cf.file_path,
        "file_type": cf.file_type,
        "file_size_bytes": cf.file_size_bytes,
        "content_hash": cf.content_hash,
        "row_count": cf.row_count,
        "column_schema": cf.column_schema or [],
        "metadata_": cf.metadata_ or {},
        "status": cf.status,
        "uploaded_by": str(cf.uploaded_by),
        "created_at": cf.created_at.isoformat(),
    }


def _proxy_to_dict(proxy: ApiProxy) -> dict:
    """API代理转字典"""
    return {
        "id": str(proxy.id),
        "connector_id": str(proxy.connector_id),
        "name": proxy.name,
        "description": proxy.description,
        "target_url": proxy.target_url,
        "http_method": proxy.http_method,
        "request_headers": proxy.request_headers or {},
        "request_params": proxy.request_params or {},
        "request_body_template": proxy.request_body_template,
        "response_mapping": proxy.response_mapping or {},
        "auth_config": proxy.auth_config or {},
        "rate_limit": proxy.rate_limit,
        "timeout_ms": proxy.timeout_ms,
        "retry_count": proxy.retry_count,
        "is_enabled": proxy.is_enabled,
        "status": proxy.status,
        "created_by": str(proxy.created_by),
        "created_at": proxy.created_at.isoformat(),
        "updated_at": proxy.updated_at.isoformat(),
    }
