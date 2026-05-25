"""
数据资源订阅全流程服务
搜索发现 / 订阅申请 / 审批流程 / 合约配置 / 数据交付 / 使用监控
"""
import uuid
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogRegistration
from app.models.subscription import DataSubscription, DataDelivery
from app.models.contract import Contract
from app.models.workflow import ApprovalWorkflow, ApprovalRecord
from app.models.user import User, Organization
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    DataNotFoundError, DataValidationError, DataAlreadyExistsError,
    PermissionDeniedError, LifecycleStateError,
)

logger = logging.getLogger(__name__)

# 差异化审核周期（天数）
REVIEW_CYCLE_DAYS = {
    "api_service": 3,
    "analysis_report": 3,
    "dataset": 3,
    "data_application": 5,
    "ai_model": 8,
}


# ==================== 搜索发现 ====================

async def search_catalog(
    db: AsyncSession,
    params: PaginationParams,
    keyword: Optional[str] = None,
    catalog_type: Optional[str] = None,
    security_level: Optional[str] = None,
    visibility: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PaginatedResponse:
    """数据目录搜索"""
    query = select(CatalogRegistration).where(
        CatalogRegistration.status == "published",
    )
    if keyword:
        query = query.where(
            CatalogRegistration.name.ilike(f"%{keyword}%")
            | CatalogRegistration.description.ilike(f"%{keyword}%")
        )
    if catalog_type:
        query = query.where(CatalogRegistration.catalog_type == catalog_type)
    if security_level:
        query = query.where(CatalogRegistration.security_level == security_level)
    if visibility:
        query = query.where(CatalogRegistration.visibility == visibility)
    if organization_id:
        query = query.where(CatalogRegistration.organization_id == uuid.UUID(organization_id))
    query = query.order_by(CatalogRegistration.updated_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def get_catalog_detail(db: AsyncSession, catalog_id: str) -> dict:
    """获取数据目录详情（含订阅状态）"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("数据目录不存在")

    return {
        "id": str(catalog.id),
        "catalog_type": catalog.catalog_type,
        "name": catalog.name,
        "description": catalog.description,
        "connector_id": str(catalog.connector_id) if catalog.connector_id else None,
        "organization_id": str(catalog.organization_id),
        "security_level": catalog.security_level,
        "visibility": catalog.visibility,
        "supply_channels": catalog.supply_channels or [],
        "control_protocol": catalog.control_protocol or {},
        "api_config": catalog.api_config or {},
        "status": catalog.status,
        "created_at": catalog.created_at.isoformat(),
        "updated_at": catalog.updated_at.isoformat(),
    }


async def get_recommendations(
    db: AsyncSession,
    user_id: str,
    params: PaginationParams,
    limit: int = 10,
) -> PaginatedResponse:
    """智能推荐：基于用户历史订阅推荐相似目录"""
    # 获取用户已订阅的 catalog_type
    sub_query = (
        select(CatalogRegistration.catalog_type)
        .join(DataSubscription, DataSubscription.catalog_id == CatalogRegistration.id)
        .where(DataSubscription.subscriber_id == uuid.UUID(user_id))
        .distinct()
    )
    sub_result = await db.execute(sub_query)
    subscribed_types = [row[0] for row in sub_result.all()]

    if subscribed_types:
        query = (
            select(CatalogRegistration)
            .where(
                CatalogRegistration.status == "published",
                CatalogRegistration.catalog_type.in_(subscribed_types),
            )
            .order_by(CatalogRegistration.updated_at.desc())
        )
    else:
        # 无订阅历史时推荐最新公开目录
        query = (
            select(CatalogRegistration)
            .where(
                CatalogRegistration.status == "published",
                CatalogRegistration.visibility == "public",
            )
            .order_by(CatalogRegistration.updated_at.desc())
        )

    result = await paginate_query(db, query, params)
    return result


# ==================== 订阅申请 ====================

async def create_subscription_application(
    db: AsyncSession,
    catalog_id: str,
    subscriber_id: str,
    subscriber_org_id: str,
    reason: str,
    subscription_config: Optional[dict] = None,
) -> dict:
    """提交订阅申请"""
    # 验证目录
    cat_result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(catalog_id))
    )
    catalog = cat_result.scalar_one_or_none()
    if not catalog:
        raise DataNotFoundError("数据目录不存在")
    if catalog.status != "published":
        raise DataValidationError(f"目录状态不允许订阅: {catalog.status}")

    # 检查重复订阅
    existing = await db.execute(
        select(DataSubscription).where(
            and_(
                DataSubscription.catalog_id == uuid.UUID(catalog_id),
                DataSubscription.subscriber_id == uuid.UUID(subscriber_id),
                DataSubscription.status.in_(["pending", "level1_approved", "approved", "active"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已存在对此目录的活跃订阅申请")

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

    logger.info(f"Subscription application created: catalog={catalog_id}, subscriber={subscriber_id}")
    return _subscription_to_dict(subscription)


# ==================== 审批流程 ====================

async def first_level_approve(
    db: AsyncSession,
    subscription_id: str,
    approver_id: str,
    approved: bool,
    comment: Optional[str] = None,
) -> dict:
    """一级审批（机构管理员）"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status != "pending":
        raise DataValidationError(f"订阅状态不允许一级审批: {sub.status}")

    if approved:
        sub.status = "level1_approved"
        logger.info(f"Subscription {subscription_id} first-level approved by {approver_id}")
    else:
        sub.status = "rejected"
        sub.approved_by = uuid.UUID(approver_id)
        sub.approved_at = datetime.now(timezone.utc)
        logger.info(f"Subscription {subscription_id} first-level rejected by {approver_id}")

    await db.commit()
    await db.refresh(sub)
    return _subscription_to_dict(sub)


async def second_level_approve(
    db: AsyncSession,
    subscription_id: str,
    approver_id: str,
    approved: bool,
    expires_at: Optional[str] = None,
    comment: Optional[str] = None,
) -> dict:
    """二级审批（平台运营方）"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status != "level1_approved":
        raise DataValidationError(f"订阅状态不允许二级审批: {sub.status}")

    if approved:
        sub.status = "active"
        sub.approved_by = uuid.UUID(approver_id)
        sub.approved_at = datetime.now(timezone.utc)
        if expires_at:
            sub.expires_at = datetime.fromisoformat(expires_at)
        else:
            sub.expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        logger.info(f"Subscription {subscription_id} second-level approved by {approver_id}")
    else:
        sub.status = "rejected"
        sub.approved_by = uuid.UUID(approver_id)
        sub.approved_at = datetime.now(timezone.utc)
        logger.info(f"Subscription {subscription_id} second-level rejected by {approver_id}")

    await db.commit()
    await db.refresh(sub)
    return _subscription_to_dict(sub)


async def reject_subscription(
    db: AsyncSession,
    subscription_id: str,
    reviewer_id: str,
    reason: str,
) -> dict:
    """驳回订阅申请"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status in ("cancelled", "expired", "rejected"):
        raise DataValidationError(f"订阅已终结: {sub.status}")

    sub.status = "rejected"
    sub.approved_by = uuid.UUID(reviewer_id)
    sub.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sub)
    logger.info(f"Subscription {subscription_id} rejected by {reviewer_id}")
    return _subscription_to_dict(sub)


# ==================== 合约配置 ====================

async def configure_contract(
    db: AsyncSession,
    subscription_id: str,
    party_a_org_id: str,
    party_a_user_id: str,
    party_b_org_id: str,
    party_b_user_id: str,
    title: str,
    content: str,
    terms: Optional[dict] = None,
    pricing: Optional[dict] = None,
    effective_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
) -> dict:
    """配置订阅合约"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status != "active":
        raise DataValidationError(f"订阅状态不允许配置合约: {sub.status}")

    # 生成合约编号
    contract_no = f"SUB-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"

    contract = Contract(
        contract_no=contract_no,
        title=title,
        contract_type="data_subscription",
        party_a_org_id=uuid.UUID(party_a_org_id),
        party_a_user_id=uuid.UUID(party_a_user_id),
        party_b_org_id=uuid.UUID(party_b_org_id),
        party_b_user_id=uuid.UUID(party_b_user_id),
        related_subscription_id=uuid.UUID(subscription_id),
        content=content,
        terms=terms or {},
        pricing=pricing or {},
        effective_date=datetime.fromisoformat(effective_date) if effective_date else datetime.now(timezone.utc),
        expiration_date=datetime.fromisoformat(expiration_date) if expiration_date else None,
        status="draft",
        created_by=uuid.UUID(party_a_user_id),
    )
    db.add(contract)
    await db.flush()

    # 关联合约到订阅
    sub.contract_id = contract.id
    await db.commit()
    await db.refresh(contract)

    logger.info(f"Contract configured for subscription={subscription_id}, contract_no={contract_no}")
    return _contract_to_dict(contract)


async def sign_contract(db: AsyncSession, contract_id: str, signer_id: str) -> dict:
    """签署合约（双方签署后生效）"""
    result = await db.execute(
        select(Contract).where(Contract.id == uuid.UUID(contract_id))
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise DataNotFoundError("合约不存在")
    if contract.status not in ("draft", "pending_review"):
        raise DataValidationError(f"合约状态不允许签署: {contract.status}")

    # 简化：直接标记为 active
    contract.status = "active"
    contract.lifecycle_stage = "execution"
    contract.lifecycle_status = "active"
    await db.commit()
    await db.refresh(contract)
    logger.info(f"Contract signed: {contract_id} by {signer_id}")
    return _contract_to_dict(contract)


# ==================== 数据交付 ====================

async def create_delivery(
    db: AsyncSession,
    subscription_id: str,
    delivery_type: str,
    delivery_config: Optional[dict] = None,
) -> dict:
    """创建数据交付（Token生成 → 接口开通）"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status != "active":
        raise DataValidationError(f"订阅状态不允许交付: {sub.status}")

    access_token = secrets.token_urlsafe(48)

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


async def confirm_delivery(db: AsyncSession, delivery_id: str, user_id: str) -> dict:
    """交付确认"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")

    delivery.last_accessed_at = datetime.now(timezone.utc)
    delivery.download_count += 1
    await db.commit()
    await db.refresh(delivery)
    logger.info(f"Delivery confirmed: {delivery_id} by {user_id}")
    return _delivery_to_dict(delivery)


async def revoke_delivery(db: AsyncSession, delivery_id: str) -> bool:
    """撤销交付"""
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


# ==================== 使用监控 ====================

async def record_usage(
    db: AsyncSession,
    delivery_id: str,
) -> dict:
    """记录数据使用（递增调用次数）"""
    result = await db.execute(
        select(DataDelivery).where(DataDelivery.id == uuid.UUID(delivery_id))
    )
    delivery = result.scalar_one_or_none()
    if not delivery:
        raise DataNotFoundError("交付记录不存在")
    if delivery.status != "active":
        raise DataValidationError(f"交付状态无效: {delivery.status}")

    delivery.download_count += 1
    delivery.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(delivery)
    return _delivery_to_dict(delivery)


async def get_subscription_usage(
    db: AsyncSession,
    subscription_id: str,
) -> dict:
    """获取订阅使用统计"""
    sub_result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = sub_result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")

    delivery_result = await db.execute(
        select(DataDelivery).where(DataDelivery.subscription_id == uuid.UUID(subscription_id))
    )
    deliveries = list(delivery_result.scalars().all())

    total_calls = sum(d.download_count for d in deliveries)
    active_deliveries = sum(1 for d in deliveries if d.status == "active")
    last_access = None
    for d in deliveries:
        if d.last_accessed_at:
            if last_access is None or d.last_accessed_at > last_access:
                last_access = d.last_accessed_at

    return {
        "subscription_id": subscription_id,
        "total_calls": total_calls,
        "total_deliveries": len(deliveries),
        "active_deliveries": active_deliveries,
        "last_accessed_at": last_access.isoformat() if last_access else None,
        "status": sub.status,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
    }


async def detect_usage_anomaly(
    db: AsyncSession,
    subscription_id: str,
    threshold_multiplier: float = 3.0,
) -> dict:
    """异常检测：检测使用量异常"""
    delivery_result = await db.execute(
        select(DataDelivery).where(DataDelivery.subscription_id == uuid.UUID(subscription_id))
    )
    deliveries = list(delivery_result.scalars().all())

    if not deliveries:
        return {"subscription_id": subscription_id, "anomaly_detected": False, "reason": "无交付记录"}

    counts = [d.download_count for d in deliveries]
    avg_count = sum(counts) / len(counts) if counts else 0

    anomalies = []
    for d in deliveries:
        if avg_count > 0 and d.download_count > avg_count * threshold_multiplier:
            anomalies.append({
                "delivery_id": str(d.id),
                "download_count": d.download_count,
                "avg_count": round(avg_count, 2),
                "ratio": round(d.download_count / avg_count, 2) if avg_count > 0 else 0,
            })

    return {
        "subscription_id": subscription_id,
        "anomaly_detected": len(anomalies) > 0,
        "total_deliveries": len(deliveries),
        "average_calls": round(avg_count, 2),
        "anomalies": anomalies,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== 订阅管理 ====================

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

    result = await paginate_query(db, query, params)
    return result


async def get_subscription(db: AsyncSession, subscription_id: str) -> dict:
    """获取订阅详情"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    return _subscription_to_dict(sub)


async def cancel_subscription(db: AsyncSession, subscription_id: str, user_id: str) -> bool:
    """取消订阅"""
    result = await db.execute(
        select(DataSubscription).where(DataSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if sub.status in ("cancelled", "expired", "rejected"):
        raise DataValidationError(f"订阅已终结: {sub.status}")
    if str(sub.subscriber_id) != user_id:
        raise PermissionDeniedError("无权取消此订阅")

    sub.status = "cancelled"
    await db.commit()
    logger.info(f"Subscription cancelled: {subscription_id}")
    return True


async def expire_subscriptions(db: AsyncSession) -> int:
    """批量过期到期订阅"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(DataSubscription).where(
            DataSubscription.status == "active",
            DataSubscription.expires_at < now,
        )
    )
    subs = list(result.scalars().all())
    count = 0
    for sub in subs:
        sub.status = "expired"
        count += 1
    if count > 0:
        await db.commit()
        logger.info(f"Expired {count} subscriptions")
    return count


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
    """交付转字典"""
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


def _contract_to_dict(c: Contract) -> dict:
    """合约转字典"""
    return {
        "id": str(c.id),
        "contract_no": c.contract_no,
        "title": c.title,
        "contract_type": c.contract_type,
        "party_a_org_id": str(c.party_a_org_id),
        "party_a_user_id": str(c.party_a_user_id),
        "party_b_org_id": str(c.party_b_org_id),
        "party_b_user_id": str(c.party_b_user_id) if c.party_b_user_id else None,
        "related_subscription_id": str(c.related_subscription_id) if c.related_subscription_id else None,
        "content": c.content,
        "terms": c.terms or {},
        "pricing": c.pricing or {},
        "effective_date": c.effective_date.isoformat() if c.effective_date else None,
        "expiration_date": c.expiration_date.isoformat() if c.expiration_date else None,
        "status": c.status,
        "lifecycle_stage": c.lifecycle_stage,
        "lifecycle_status": c.lifecycle_status,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }
