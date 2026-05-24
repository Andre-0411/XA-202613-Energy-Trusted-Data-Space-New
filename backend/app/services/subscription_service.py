"""
数据资源订阅服务
DataSubscription / DataDelivery
"""
import uuid
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import DataSubscription, DataDelivery
from app.models.catalog import CatalogRegistration
from app.models.user import User, Organization
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError, PermissionDeniedError

logger = logging.getLogger(__name__)


def _generate_access_token() -> str:
    """生成数据交付访问令牌"""
    return secrets.token_urlsafe(48)


def _subscription_to_dict(sub: DataSubscription, deliveries: list = None) -> dict:
    """将订阅对象序列化为字典"""
    delivery_list = []
    if deliveries:
        for d in deliveries:
            delivery_list.append({
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
            })

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
        "deliveries": delivery_list,
    }


def _delivery_to_dict(d: DataDelivery) -> dict:
    """将交付对象序列化为字典"""
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


# ==================== 数据订阅 CRUD ====================

async def create_subscription(
    db: AsyncSession,
    subscriber_id: str,
    subscriber_org_id: str,
    catalog_id: str,
    reason: Optional[str] = None,
    subscription_config: Optional[dict] = None,
) -> dict:
    """创建数据资源订阅申请"""
    # 检查目录是否存在
    catalog_result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = catalog_result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("数据目录不存在")
    if catalog.status != "published":
        raise DataValidationError(f"数据目录状态不允许订阅: {catalog.status}")

    # 检查是否已有订阅
    existing = await db.execute(
        select(DataSubscription).where(
            and_(
                DataSubscription.catalog_id == uuid.UUID(catalog_id),
                DataSubscription.subscriber_id == uuid.UUID(subscriber_id),
                DataSubscription.status.in_(["pending", "approved", "active"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已存在对此目录的活跃订阅")

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

    logger.info(f"Subscription created: catalog={catalog_id}, subscriber={subscriber_id}")
    return _subscription_to_dict(subscription)


async def list_subscriptions(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    catalog_id: Optional[str] = None,
    subscriber_id: Optional[str] = None,
    subscriber_org_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出数据订阅"""
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


async def get_subscription(db: AsyncSession, subscription_id: str) -> dict:
    """获取订阅详情"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")

    # 获取交付记录
    deliveries_result = await db.execute(
        select(DataDelivery)
        .where(DataDelivery.subscription_id == sub.id)
        .order_by(DataDelivery.created_at.desc())
    )
    deliveries = list(deliveries_result.scalars().all())

    return _subscription_to_dict(sub, deliveries)


async def update_subscription(
    db: AsyncSession,
    subscription_id: str,
    **kwargs,
) -> dict:
    """更新订阅"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status not in ["pending", "active"]:
        raise DataValidationError(f"当前状态不允许修改: {sub.status}")

    for field in ["reason", "subscription_config", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(sub, field, kwargs[field])

    await db.commit()
    await db.refresh(sub)
    logger.info(f"Subscription updated: {subscription_id}")
    return _subscription_to_dict(sub)


async def review_subscription(
    db: AsyncSession,
    subscription_id: str,
    reviewer_id: str,
    status: str,
    expires_at: Optional[str] = None,
) -> dict:
    """审核订阅申请"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status != "pending":
        raise DataValidationError(f"订阅状态不为待审批: {sub.status}")

    if status not in ["approved", "rejected"]:
        raise DataValidationError(f"无效的审核状态: {status}")

    sub.status = status
    sub.approved_by = uuid.UUID(reviewer_id)
    sub.approved_at = datetime.now(timezone.utc)
    if status == "approved":
        sub.status = "active"
        if expires_at:
            sub.expires_at = datetime.fromisoformat(expires_at)

    await db.commit()
    logger.info(f"Subscription {subscription_id} reviewed: {status} by {reviewer_id}")
    return _subscription_to_dict(sub)


async def cancel_subscription(db: AsyncSession, subscription_id: str, user_id: str) -> bool:
    """取消订阅"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status in ["cancelled", "expired"]:
        raise DataValidationError(f"订阅已终结: {sub.status}")

    # 只有订阅者本人或管理员可以取消
    if str(sub.subscriber_id) != user_id:
        raise PermissionDeniedError("无权取消此订阅")

    sub.status = "cancelled"
    await db.commit()
    logger.info(f"Subscription cancelled: {subscription_id}")
    return True


# ==================== 数据交付 ====================

async def create_delivery(
    db: AsyncSession,
    subscription_id: str,
    delivery_type: str,
    delivery_config: Optional[dict] = None,
) -> dict:
    """创建数据交付"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status != "active":
        raise DataValidationError(f"订阅状态不允许创建交付: {sub.status}")

    access_token = _generate_access_token()

    delivery = DataDelivery(
        subscription_id=uuid.UUID(subscription_id),
        delivery_type=delivery_type,
        delivery_config=delivery_config or {},
        access_token=access_token,
        download_count=0,
        status="active",
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    logger.info(f"Delivery created: subscription={subscription_id}, type={delivery_type}")
    return _delivery_to_dict(delivery)


async def list_deliveries(
    db: AsyncSession,
    params: PaginationParams,
    subscription_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出交付记录"""
    query = select(DataDelivery)
    if subscription_id:
        query = query.where(DataDelivery.subscription_id == uuid.UUID(subscription_id))
    if status:
        query = query.where(DataDelivery.status == status)
    query = query.order_by(DataDelivery.created_at.desc())

    from app.schemas.subscription import DataDeliveryResponse
    result = await paginate_query(db, query, params, DataDeliveryResponse)
    return result


async def get_delivery(db: AsyncSession, delivery_id: str) -> dict:
    """获取交付详情"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")
    return _delivery_to_dict(delivery)


async def record_download(db: AsyncSession, delivery_id: str) -> dict:
    """记录下载（递增下载计数）"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")
    if delivery.status != "active":
        raise DataValidationError(f"交付记录状态无效: {delivery.status}")

    delivery.download_count += 1
    delivery.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(delivery)

    logger.info(f"Download recorded: delivery={delivery_id}, count={delivery.download_count}")
    return _delivery_to_dict(delivery)


async def revoke_delivery(db: AsyncSession, delivery_id: str) -> bool:
    """撤销交付（使访问令牌失效）"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")

    delivery.status = "revoked"
    delivery.access_token = None
    await db.commit()
    logger.info(f"Delivery revoked: {delivery_id}")
    return True
