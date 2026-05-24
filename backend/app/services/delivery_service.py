"""
数据交付服务
数据交付记录管理/文件下载/API访问
"""
import uuid
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import DataSubscription, DataDelivery
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


async def create_delivery(
    db: AsyncSession,
    subscription_id: str,
    delivery_type: str,
    delivery_config: Optional[dict] = None,
) -> dict:
    """创建数据交付记录"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status != "approved":
        raise DataValidationError("只有已审核通过的订阅可以创建交付")

    access_token = secrets.token_urlsafe(64)

    delivery = DataDelivery(
        subscription_id=uuid.UUID(subscription_id),
        delivery_type=delivery_type,
        delivery_config=delivery_config or {},
        access_token=access_token,
        status="active",
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    logger.info(f"Delivery created: subscription={subscription_id}, type={delivery_type}")
    return _delivery_to_dict(delivery)


async def get_delivery(db: AsyncSession, delivery_id: str) -> dict:
    """获取交付详情"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")
    return _delivery_to_dict(delivery)


async def access_delivery(
    db: AsyncSession,
    delivery_id: str,
    access_token: Optional[str] = None,
) -> dict:
    """访问数据交付（记录下载次数和最后访问时间）"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
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

    logger.info(f"Delivery accessed: {delivery_id}, count={delivery.download_count}")
    return _delivery_to_dict(delivery)


async def list_deliveries(
    db: AsyncSession,
    subscription_id: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    """列出交付记录"""
    query = select(DataDelivery)
    if subscription_id:
        query = query.where(DataDelivery.subscription_id == uuid.UUID(subscription_id))
    if status:
        query = query.where(DataDelivery.status == status)
    query = query.order_by(DataDelivery.created_at.desc())

    result = await db.execute(query)
    deliveries = result.scalars().all()
    return [_delivery_to_dict(d) for d in deliveries]


async def revoke_delivery(db: AsyncSession, delivery_id: str) -> dict:
    """撤销交付（使令牌失效）"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")

    delivery.status = "revoked"
    delivery.access_token = None
    await db.commit()
    await db.refresh(delivery)

    logger.info(f"Delivery revoked: {delivery_id}")
    return _delivery_to_dict(delivery)


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
