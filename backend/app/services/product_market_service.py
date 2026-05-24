"""
数据产品市场服务
产品浏览/搜索/推荐
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import DataProduct, ProductSubscription
from app.models.user import Organization
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError

logger = logging.getLogger(__name__)


async def browse_market(
    db: AsyncSession,
    params: PaginationParams,
    keyword: Optional[str] = None,
    product_type: Optional[str] = None,
    pricing_model: Optional[str] = None,
    industry_tag: Optional[str] = None,
) -> PaginatedResponse:
    """浏览数据产品市场（仅已发布产品）"""
    query = select(DataProduct).where(DataProduct.status == "published")
    if keyword:
        query = query.where(DataProduct.name.ilike(f"%{keyword}%"))
    if product_type:
        query = query.where(DataProduct.product_type == product_type)
    if pricing_model:
        query = query.where(DataProduct.pricing["model"].as_string() == pricing_model)
    query = query.order_by(DataProduct.published_at.desc())

    from app.schemas.product import DataProductResponse
    result = await paginate_query(db, query, params, DataProductResponse)
    return result


async def get_product_detail_for_market(db: AsyncSession, product_id: str) -> dict:
    """获取产品市场详情（含统计）"""
    result = await db.execute(
        select(DataProduct).where(
            and_(
                DataProduct.id == uuid.UUID(product_id),
                DataProduct.status == "published",
            )
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("产品不存在或未发布")

    # 统计订阅数
    sub_count_result = await db.execute(
        select(func.count(ProductSubscription.id)).where(
            and_(
                ProductSubscription.product_id == product.id,
                ProductSubscription.status == "approved",
            )
        )
    )
    subscriber_count = sub_count_result.scalar() or 0

    # 统计组织信息
    org_result = await db.execute(
        select(Organization).where(Organization.id == product.organization_id)
    )
    org = org_result.scalar_one_or_none()

    return {
        "id": str(product.id),
        "project_id": str(product.project_id) if product.project_id else None,
        "name": product.name,
        "description": product.description,
        "product_type": product.product_type,
        "compute_engine": product.compute_engine,
        "version": product.version,
        "organization_id": str(product.organization_id),
        "organization_name": org.name if org else None,
        "owner_id": str(product.owner_id),
        "technical_spec": product.technical_spec or {},
        "pricing": product.pricing or {},
        "delivery_config": product.delivery_config or {},
        "compliance_docs": product.compliance_docs or [],
        "control_protocol": product.control_protocol or {},
        "status": product.status,
        "published_at": product.published_at.isoformat() if product.published_at else None,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
        "subscriber_count": subscriber_count,
    }


async def get_market_stats(db: AsyncSession) -> dict:
    """获取市场统计数据"""
    # 已发布产品总数
    published_count_result = await db.execute(
        select(func.count(DataProduct.id)).where(DataProduct.status == "published")
    )
    published_count = published_count_result.scalar() or 0

    # 总订阅数
    subscription_count_result = await db.execute(
        select(func.count(ProductSubscription.id)).where(ProductSubscription.status == "approved")
    )
    subscription_count = subscription_count_result.scalar() or 0

    # 产品类型分布
    type_dist_result = await db.execute(
        select(DataProduct.product_type, func.count(DataProduct.id))
        .where(DataProduct.status == "published")
        .group_by(DataProduct.product_type)
    )
    type_distribution = {row[0]: row[1] for row in type_dist_result.all()}

    return {
        "published_product_count": published_count,
        "total_subscription_count": subscription_count,
        "type_distribution": type_distribution,
    }


async def search_products(
    db: AsyncSession,
    params: PaginationParams,
    keyword: Optional[str] = None,
    query_text: Optional[str] = None,
    product_type: Optional[str] = None,
    pricing_type: Optional[str] = None,
    pricing_model: Optional[str] = None,
) -> PaginatedResponse:
    """全文搜索产品"""
    search_term = keyword or query_text
    query = select(DataProduct).where(DataProduct.status == "published")
    if search_term:
        query = query.where(DataProduct.name.ilike(f"%{search_term}%"))
    if product_type:
        query = query.where(DataProduct.product_type == product_type)
    if pricing_type or pricing_model:
        model = pricing_type or pricing_model
        query = query.where(DataProduct.pricing["model"].as_string() == model)
    query = query.order_by(DataProduct.published_at.desc())

    from app.schemas.product import DataProductResponse
    result = await paginate_query(db, query, params, DataProductResponse)
    return result


async def list_subscriptions(
    db: AsyncSession,
    params: PaginationParams,
    subscriber_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出产品订阅"""
    query = select(ProductSubscription)
    if subscriber_id:
        query = query.where(ProductSubscription.subscriber_id == uuid.UUID(subscriber_id))
    if status:
        query = query.where(ProductSubscription.status == status)
    query = query.order_by(ProductSubscription.created_at.desc())

    from app.schemas.product import ProductSubscriptionResponse
    result = await paginate_query(db, query, params, ProductSubscriptionResponse)
    return result


async def create_subscription(
    db: AsyncSession,
    product_id: str,
    subscriber_id: str,
    subscriber_org_id: str,
    reason: Optional[str] = None,
    subscription_config: Optional[dict] = None,
) -> dict:
    """创建产品订阅"""
    sub = ProductSubscription(
        product_id=uuid.UUID(product_id),
        subscriber_id=uuid.UUID(subscriber_id),
        subscriber_org_id=uuid.UUID(subscriber_org_id),
        reason=reason,
        subscription_config=subscription_config or {},
        status="pending",
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return _subscription_to_dict(sub)


async def review_subscription(
    db: AsyncSession,
    subscription_id: str,
    reviewer_id: str,
    action: str = "approve",
    comment: Optional[str] = None,
) -> dict:
    """审批产品订阅"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    if action == "approve":
        sub.status = "approved"
    else:
        sub.status = "rejected"
    sub.approved_by = uuid.UUID(reviewer_id)
    sub.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sub)
    return _subscription_to_dict(sub)


async def recommend_products(
    db: AsyncSession,
    user_id: str,
    limit: int = 10,
) -> list:
    """推荐产品（简单实现：按最新发布推荐）"""
    query = (
        select(DataProduct)
        .where(DataProduct.status == "published")
        .order_by(DataProduct.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    products = result.scalars().all()
    return [_product_to_dict(p) for p in products]


async def file_contract(
    db: AsyncSession,
    subscription_id: str,
    contract_id: str,
) -> dict:
    """备案合约"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("订阅不存在")
    sub.contract_id = uuid.UUID(contract_id)
    await db.commit()
    await db.refresh(sub)
    return _subscription_to_dict(sub)


def _subscription_to_dict(sub: ProductSubscription) -> dict:
    """订阅转字典"""
    return {
        "id": str(sub.id),
        "product_id": str(sub.product_id),
        "subscriber_id": str(sub.subscriber_id),
        "subscriber_org_id": str(sub.subscriber_org_id),
        "reason": sub.reason,
        "contract_id": str(sub.contract_id) if sub.contract_id else None,
        "subscription_config": sub.subscription_config,
        "delivery_config": sub.delivery_config,
        "status": sub.status,
        "approved_by": str(sub.approved_by) if sub.approved_by else None,
        "approved_at": sub.approved_at.isoformat() if sub.approved_at else None,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "created_at": sub.created_at.isoformat(),
        "updated_at": sub.updated_at.isoformat(),
    }


def _product_to_dict(product: DataProduct) -> dict:
    """产品转字典"""
    return {
        "id": str(product.id),
        "name": product.name,
        "description": product.description,
        "product_type": product.product_type,
        "status": product.status,
        "created_at": product.created_at.isoformat(),
    }
