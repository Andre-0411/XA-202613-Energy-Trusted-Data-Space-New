"""
数据资源订阅服务
数据订阅申请/审核/管理
"""
import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import DataSubscription, DataDelivery
from app.models.catalog import CatalogRegistration
from app.models.user import Organization, User
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError

logger = logging.getLogger(__name__)


async def create_subscription(
    db: AsyncSession,
    catalog_id: str,
    subscriber_id: str,
    subscriber_org_id: str,
    reason: Optional[str] = None,
    subscription_config: Optional[dict] = None,
) -> dict:
    """创建数据订阅申请"""
    # 验证目录存在且已审核
    cat_result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = cat_result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("数据目录不存在")
    if catalog.status != "approved":
        raise DataValidationError("只能订阅已审核通过的数据目录")

    # 检查重复订阅
    existing = await db.execute(
        select(DataSubscription).where(
            and_(
                DataSubscription.catalog_id == uuid.UUID(catalog_id),
                DataSubscription.subscriber_id == uuid.UUID(subscriber_id),
                DataSubscription.status.in_(["pending", "approved"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已存在对此数据的订阅申请")

    subscription = DataSubscription(
        catalog_id=uuid.UUID(catalog_id),
        subscriber_id=uuid.UUID(subscriber_id),
        subscriber_org_id=uuid.UUID(subscriber_org_id),
        reason=reason,
        subscription_config=subscription_config or {},
        status="pending",
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    logger.info(f"Data subscription created: catalog={catalog_id}, subscriber={subscriber_id}")
    return _subscription_to_dict(subscription)


async def review_subscription(
    db: AsyncSession,
    subscription_id: str,
    reviewer_id: str,
    status: str,
    expires_at: Optional[str] = None,
) -> dict:
    """审核数据订阅"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅申请不存在")
    if sub.status != "pending":
        raise DataValidationError(f"订阅状态不为待审批: {sub.status}")

    sub.status = status
    sub.approved_by = uuid.UUID(reviewer_id)
    sub.approved_at = datetime.now(timezone.utc)
    if expires_at:
        sub.expires_at = datetime.fromisoformat(expires_at)

    await db.commit()
    await db.refresh(sub)
    logger.info(f"Data subscription {subscription_id} reviewed: {status}")
    return _subscription_to_dict(sub)


async def cancel_subscription(
    db: AsyncSession,
    subscription_id: str,
    user_id: str,
) -> dict:
    """取消数据订阅"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.subscriber_id != uuid.UUID(user_id):
        raise DataValidationError("只有订阅者本人可以取消订阅")
    if sub.status not in ("pending", "approved"):
        raise DataValidationError(f"订阅状态不可取消: {sub.status}")

    sub.status = "cancelled"
    await db.commit()
    await db.refresh(sub)
    logger.info(f"Data subscription cancelled: {subscription_id}")
    return _subscription_to_dict(sub)


async def get_subscription(db: AsyncSession, subscription_id: str) -> dict:
    """获取订阅详情"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")

    # 加载交付记录
    del_result = await db.execute(
        select(DataDelivery).where(DataDelivery.subscription_id == sub.id)
    )
    deliveries = del_result.scalars().all()

    sub_dict = _subscription_to_dict(sub)
    sub_dict["deliveries"] = [_delivery_to_dict(d) for d in deliveries]
    return sub_dict


async def list_subscriptions(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    catalog_id: Optional[str] = None,
    subscriber_id: Optional[str] = None,
    subscriber_org_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出订阅"""
    query = select(DataSubscription)
    if status:
        query = query.where(DataSubscription.status == status)
    if catalog_id:
        query = query.where(DataSubscription.catalog_id == uuid.UUID(catalog_id))
    if subscriber_id:
        query = query.where(DataSubscription.subscriber_id == uuid.UUID(subscriber_id))
    if subscriber_org_id:
        query = query.where(DataSubscription.subscriber_org_id == uuid.UUID(subscriber_org_id))
    query = query.order_by(DataSubscription.created_at.desc())

    from app.schemas.subscription import DataSubscriptionResponse
    result = await paginate_query(db, query, params, DataSubscriptionResponse)
    return result


async def get_subscription_stats(
    db: AsyncSession,
    organization_id: Optional[str] = None,
) -> dict:
    """获取订阅统计"""
    base = []
    if organization_id:
        base.append(DataSubscription.subscriber_org_id == uuid.UUID(organization_id))

    pending_r = await db.execute(
        select(DataSubscription).where(and_(DataSubscription.status == "pending", *base))
    )
    approved_r = await db.execute(
        select(DataSubscription).where(and_(DataSubscription.status == "approved", *base))
    )
    total_r = await db.execute(select(DataSubscription).where(and_(*base)) if base else select(DataSubscription))

    return {
        "total_count": len(total_r.scalars().all()),
        "pending_count": len(pending_r.scalars().all()),
        "approved_count": len(approved_r.scalars().all()),
    }


# ==================== Helpers ====================

def _subscription_to_dict(sub: DataSubscription) -> dict:
    """订阅转字典"""
    return {
        "id": str(sub.id),
        "catalog_id": str(sub.catalog_id),
        "subscriber_id": str(sub.subscriber_id),
        "subscriber_org_id": str(sub.subscriber_org_id),
        "reason": sub.reason,
        "contract_id": str(sub.contract_id) if sub.contract_id else None,
        "subscription_config": sub.subscription_config or {},
        "status": sub.status,
        "approved_by": str(sub.approved_by) if sub.approved_by else None,
        "approved_at": sub.approved_at.isoformat() if sub.approved_at else None,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "created_at": sub.created_at.isoformat(),
        "updated_at": sub.updated_at.isoformat(),
    }


def _delivery_to_dict(d: DataDelivery) -> dict:
    """交付记录转字典"""
    return {
        "id": str(d.id),
        "subscription_id": str(d.subscription_id),
        "delivery_type": d.delivery_type,
        "delivery_config": d.delivery_config or {},
        "access_token": d.access_token,
        "file_path": d.file_path,
        "download_count": d.download_count,
        "last_accessed_at": d.last_accessed_at.isoformat() if d.last_accessed_at else None,
        "status": d.status,
        "created_at": d.created_at.isoformat(),
    }
