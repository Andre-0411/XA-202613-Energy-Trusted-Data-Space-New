"""
产品交付服务
产品订阅/交付管理
"""
import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import (
    DataProduct, ProductSubscription, ProductDelivery,
)
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError

logger = logging.getLogger(__name__)


# ==================== 产品订阅 ====================

async def create_product_subscription(
    db: AsyncSession,
    product_id: str,
    subscriber_id: str,
    subscriber_org_id: str,
    reason: Optional[str] = None,
    subscription_config: Optional[dict] = None,
    delivery_config: Optional[dict] = None,
) -> dict:
    """创建产品订阅申请"""
    # 验证产品
    prod_result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")
    if product.status != "published":
        raise DataValidationError("只能订阅已发布的产品")

    # 检查重复订阅
    existing = await db.execute(
        select(ProductSubscription).where(
            and_(
                ProductSubscription.product_id == uuid.UUID(product_id),
                ProductSubscription.subscriber_id == uuid.UUID(subscriber_id),
                ProductSubscription.status.in_(["pending", "approved"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已存在对此产品的订阅申请")

    subscription = ProductSubscription(
        product_id=uuid.UUID(product_id),
        subscriber_id=uuid.UUID(subscriber_id),
        subscriber_org_id=uuid.UUID(subscriber_org_id),
        reason=reason,
        subscription_config=subscription_config or {},
        delivery_config=delivery_config or {},
        status="pending",
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    logger.info(f"Product subscription created: product={product_id}, subscriber={subscriber_id}")
    return _product_subscription_to_dict(subscription)


async def review_product_subscription(
    db: AsyncSession,
    subscription_id: str,
    reviewer_id: str,
    status: str,
    expires_at: Optional[str] = None,
) -> dict:
    """审核产品订阅"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("产品订阅不存在")
    if sub.status != "pending":
        raise DataValidationError(f"订阅状态不为待审批: {sub.status}")

    sub.status = status
    sub.approved_by = uuid.UUID(reviewer_id)
    sub.approved_at = datetime.now(timezone.utc)
    if expires_at:
        sub.expires_at = datetime.fromisoformat(expires_at)

    await db.commit()
    await db.refresh(sub)
    logger.info(f"Product subscription {subscription_id} reviewed: {status}")
    return _product_subscription_to_dict(sub)


async def get_product_subscription(db: AsyncSession, subscription_id: str) -> dict:
    """获取产品订阅详情"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("产品订阅不存在")

    # 加载交付记录
    del_result = await db.execute(
        select(ProductDelivery).where(ProductDelivery.subscription_id == sub.id)
    )
    deliveries = del_result.scalars().all()

    sub_dict = _product_subscription_to_dict(sub)
    sub_dict["deliveries"] = [_delivery_to_dict(d) for d in deliveries]
    return sub_dict


async def list_product_subscriptions(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    product_id: Optional[str] = None,
    subscriber_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出产品订阅"""
    query = select(ProductSubscription)
    if status:
        query = query.where(ProductSubscription.status == status)
    if product_id:
        query = query.where(ProductSubscription.product_id == uuid.UUID(product_id))
    if subscriber_id:
        query = query.where(ProductSubscription.subscriber_id == uuid.UUID(subscriber_id))
    query = query.order_by(ProductSubscription.created_at.desc())

    from app.schemas.product import ProductSubscriptionResponse
    result = await paginate_query(db, query, params, ProductSubscriptionResponse)
    return result


async def cancel_product_subscription(
    db: AsyncSession,
    subscription_id: str,
    user_id: str,
) -> dict:
    """取消产品订阅"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("产品订阅不存在")
    if sub.subscriber_id != uuid.UUID(user_id):
        raise DataValidationError("只有订阅者本人可以取消")

    sub.status = "cancelled"
    await db.commit()
    await db.refresh(sub)
    logger.info(f"Product subscription cancelled: {subscription_id}")
    return _product_subscription_to_dict(sub)


# ==================== 产品交付 ====================

async def create_product_delivery(
    db: AsyncSession,
    subscription_id: str,
    delivery_type: str,
    delivery_config: Optional[dict] = None,
) -> dict:
    """创建产品交付记录"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("产品订阅不存在")
    if sub.status != "approved":
        raise DataValidationError("只有已审核通过的订阅可以创建交付")

    access_token = secrets.token_urlsafe(64)

    delivery = ProductDelivery(
        subscription_id=uuid.UUID(subscription_id),
        delivery_type=delivery_type,
        delivery_config=delivery_config or {},
        access_token=access_token,
        status="active",
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    logger.info(f"Product delivery created: subscription={subscription_id}")
    return _delivery_to_dict(delivery)


async def access_product_delivery(
    db: AsyncSession,
    delivery_id: str,
    access_token: Optional[str] = None,
) -> dict:
    """访问产品交付"""
    result = await db.execute(
        select(ProductDelivery).where(ProductDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")
    if delivery.status != "active":
        raise DataValidationError(f"交付状态无效: {delivery.status}")
    if access_token and delivery.access_token != access_token:
        raise DataValidationError("访问令牌无效")

    delivery.download_count += 1
    delivery.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(delivery)

    logger.info(f"Product delivery accessed: {delivery_id}")
    return _delivery_to_dict(delivery)


# ==================== Helpers ====================

def _product_subscription_to_dict(sub: ProductSubscription) -> dict:
    """产品订阅转字典"""
    return {
        "id": str(sub.id),
        "product_id": str(sub.product_id),
        "subscriber_id": str(sub.subscriber_id),
        "subscriber_org_id": str(sub.subscriber_org_id),
        "reason": sub.reason,
        "contract_id": str(sub.contract_id) if sub.contract_id else None,
        "subscription_config": sub.subscription_config or {},
        "delivery_config": sub.delivery_config or {},
        "status": sub.status,
        "approved_by": str(sub.approved_by) if sub.approved_by else None,
        "approved_at": sub.approved_at.isoformat() if sub.approved_at else None,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "created_at": sub.created_at.isoformat(),
        "updated_at": sub.updated_at.isoformat(),
    }


def _delivery_to_dict(d: ProductDelivery) -> dict:
    """产品交付转字典"""
    return {
        "id": str(d.id),
        "subscription_id": str(d.subscription_id),
        "delivery_type": d.delivery_type,
        "delivery_config": d.delivery_config or {},
        "access_token": d.access_token,
        "access_url": d.access_url,
        "download_count": d.download_count,
        "last_accessed_at": d.last_accessed_at.isoformat() if d.last_accessed_at else None,
        "status": d.status,
        "created_at": d.created_at.isoformat(),
    }
