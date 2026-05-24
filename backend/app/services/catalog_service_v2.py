"""
数据目录管理服务 V2
目录注册/更新/审核/下架的增强版本
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogRegistration
from app.models.connector import Connector
from app.models.user import Organization
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


async def register_catalog_entry(
    db: AsyncSession,
    connector_id: str,
    data_name: str,
    data_type: str,
    description: str,
    organization_id: str,
    registered_by: str,
    **kwargs,
) -> dict:
    """注册数据目录条目"""
    # 验证连接器存在
    conn_result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = conn_result.scalar_one_or_none()
    if not connector:
        raise DataNotFoundError("连接器不存在")

    catalog = CatalogRegistration(
        connector_id=uuid.UUID(connector_id),
        data_name=data_name,
        data_type=data_type,
        description=description,
        classification_level=kwargs.get("classification_level", "public"),
        industry_tags=kwargs.get("industry_tags", []),
        geographic_scope=kwargs.get("geographic_scope", "regional"),
        update_frequency=kwargs.get("update_frequency", "realtime"),
        quality_score=kwargs.get("quality_score", 0),
        schema_definition=kwargs.get("schema_definition", {}),
        sample_data=kwargs.get("sample_data", []),
        pricing_model=kwargs.get("pricing_model", "free"),
        access_control=kwargs.get("access_control", {}),
        security_policy=kwargs.get("security_policy", {}),
        metadata_extra=kwargs.get("metadata_extra", {}),
        organization_id=uuid.UUID(organization_id),
        registered_by=uuid.UUID(registered_by),
        status="pending",
    )
    db.add(catalog)
    await db.commit()
    await db.refresh(catalog)

    logger.info(f"Catalog entry registered: {data_name} from connector {connector_id}")
    return _catalog_to_dict(catalog)


async def update_catalog_entry(
    db: AsyncSession,
    catalog_id: str,
    **kwargs,
) -> dict:
    """更新目录条目"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("目录条目不存在")

    allowed_fields = [
        "data_name", "data_type", "description", "classification_level",
        "industry_tags", "geographic_scope", "update_frequency",
        "quality_score", "schema_definition", "sample_data",
        "pricing_model", "access_control", "security_policy", "metadata_extra",
    ]
    for field in allowed_fields:
        if field in kwargs and kwargs[field] is not None:
            setattr(catalog, field, kwargs[field])

    await db.commit()
    await db.refresh(catalog)
    logger.info(f"Catalog entry updated: {catalog_id}")
    return _catalog_to_dict(catalog)


async def review_catalog_entry(
    db: AsyncSession,
    catalog_id: str,
    reviewer_id: str,
    status: str,
    review_comment: Optional[str] = None,
) -> dict:
    """审核目录条目"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("目录条目不存在")
    if catalog.status != "pending":
        raise DataValidationError(f"目录状态不为待审批: {catalog.status}")

    catalog.status = status
    if status == "approved":
        catalog.approved_by = uuid.UUID(reviewer_id)
        catalog.approved_at = datetime.now(timezone.utc)

    await db.commit()
    logger.info(f"Catalog entry {catalog_id} reviewed: {status}")
    return _catalog_to_dict(catalog)


async def unpublish_catalog_entry(
    db: AsyncSession,
    catalog_id: str,
    user_id: str,
    reason: Optional[str] = None,
) -> dict:
    """下架目录条目"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("目录条目不存在")
    if catalog.status != "approved":
        raise DataValidationError("只有已审核通过的目录可以下架")

    catalog.status = "unpublished"
    await db.commit()
    await db.refresh(catalog)
    logger.info(f"Catalog entry unpublished: {catalog_id}")
    return _catalog_to_dict(catalog)


async def get_catalog_detail(db: AsyncSession, catalog_id: str) -> dict:
    """获取目录条目详情"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("目录条目不存在")
    return _catalog_to_dict(catalog)


async def list_catalog_entries(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
    data_type: Optional[str] = None,
    classification_level: Optional[str] = None,
    keyword: Optional[str] = None,
) -> PaginatedResponse:
    """列出目录条目"""
    query = select(CatalogRegistration)
    if status:
        query = query.where(CatalogRegistration.status == status)
    if organization_id:
        query = query.where(CatalogRegistration.organization_id == uuid.UUID(organization_id))
    if data_type:
        query = query.where(CatalogRegistration.data_type == data_type)
    if classification_level:
        query = query.where(CatalogRegistration.classification_level == classification_level)
    if keyword:
        query = query.where(CatalogRegistration.data_name.ilike(f"%{keyword}%"))
    query = query.order_by(CatalogRegistration.created_at.desc())

    from app.schemas.catalog_registration import CatalogRegistrationResponse
    result = await paginate_query(db, query, params, CatalogRegistrationResponse)
    return result


async def get_catalog_stats(db: AsyncSession, organization_id: Optional[str] = None) -> dict:
    """获取目录统计"""
    base = []
    if organization_id:
        base.append(CatalogRegistration.organization_id == uuid.UUID(organization_id))

    approved_q = select(CatalogRegistration).where(and_(CatalogRegistration.status == "approved", *base))
    pending_q = select(CatalogRegistration).where(and_(CatalogRegistration.status == "pending", *base))
    total_q = select(CatalogRegistration).where(and_(*base)) if base else select(CatalogRegistration)

    approved_r = await db.execute(approved_q)
    pending_r = await db.execute(pending_q)
    total_r = await db.execute(total_q)

    return {
        "total_count": len(total_r.scalars().all()),
        "approved_count": len(approved_r.scalars().all()),
        "pending_count": len(pending_r.scalars().all()),
    }


def _catalog_to_dict(catalog: CatalogRegistration) -> dict:
    """目录条目转字典"""
    return {
        "id": str(catalog.id),
        "connector_id": str(catalog.connector_id),
        "data_name": catalog.data_name,
        "data_type": catalog.data_type,
        "description": catalog.description,
        "classification_level": catalog.classification_level,
        "industry_tags": catalog.industry_tags or [],
        "geographic_scope": catalog.geographic_scope,
        "update_frequency": catalog.update_frequency,
        "quality_score": catalog.quality_score,
        "schema_definition": catalog.schema_definition or {},
        "sample_data": catalog.sample_data or [],
        "pricing_model": catalog.pricing_model,
        "access_control": catalog.access_control or {},
        "security_policy": catalog.security_policy or {},
        "metadata_extra": catalog.metadata_extra or {},
        "organization_id": str(catalog.organization_id),
        "registered_by": str(catalog.registered_by),
        "approved_by": str(catalog.approved_by) if catalog.approved_by else None,
        "approved_at": catalog.approved_at.isoformat() if catalog.approved_at else None,
        "status": catalog.status,
        "created_at": catalog.created_at.isoformat(),
        "updated_at": catalog.updated_at.isoformat(),
    }
