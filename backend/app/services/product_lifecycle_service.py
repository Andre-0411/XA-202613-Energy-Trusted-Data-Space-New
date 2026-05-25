"""
数据产品全生命周期服务
产品开发 / 上架审核 / 订阅交付 / 版本管理
"""
import uuid
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import (
    ProductProject, ProjectMember, DataProduct, ProductAcceptance,
    ProductPublishRequest, ProductUnpublishRequest,
    ProductSubscription, ProductDelivery,
)
from app.models.contract import Contract
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    DataNotFoundError, DataValidationError, DataAlreadyExistsError,
    PermissionDeniedError, LifecycleStateError,
)

logger = logging.getLogger(__name__)

# 5种产品类型
VALID_PRODUCT_TYPES = ("api_service", "analysis_report", "data_application", "ai_model", "dataset")

# 差异化审核周期（天数）
REVIEW_CYCLE_DAYS = {
    "api_service": 3,
    "analysis_report": 3,
    "dataset": 3,
    "data_application": 5,
    "ai_model": 8,
}

# 产品状态机
PRODUCT_STATUS_FLOW = {
    "development": ["testing", "deleted"],
    "testing": ["development", "review_pending", "deleted"],
    "review_pending": ["testing", "compliance_check", "rejected"],
    "compliance_check": ["quality_review", "rejected"],
    "quality_review": ["published", "rejected"],
    "published": ["unpublished", "maintenance"],
    "unpublished": ["review_pending", "deleted"],
    "maintenance": ["published", "unpublished"],
    "rejected": ["development", "testing", "deleted"],
    "deleted": [],
}


# ==================== 产品开发 ====================

async def create_project(
    db: AsyncSession,
    name: str,
    project_type: str,
    organization_id: str,
    owner_id: str,
    description: Optional[str] = None,
    data_sources: Optional[list] = None,
) -> dict:
    """创建产品项目"""
    project = ProductProject(
        name=name,
        description=description,
        project_type=project_type,
        organization_id=uuid.UUID(organization_id),
        owner_id=uuid.UUID(owner_id),
        data_sources=data_sources or [],
        status="active",
    )
    db.add(project)
    await db.flush()

    # 自动添加 owner 为项目成员
    owner_member = ProjectMember(
        project_id=project.id,
        user_id=uuid.UUID(owner_id),
        role="owner",
    )
    db.add(owner_member)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Product project created: {name} by {owner_id}")
    return _project_to_dict(project)


async def add_project_member(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    role: str = "member",
) -> dict:
    """添加项目成员"""
    existing = await db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == uuid.UUID(project_id),
                ProjectMember.user_id == uuid.UUID(user_id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("用户已是项目成员")

    member = ProjectMember(
        project_id=uuid.UUID(project_id),
        user_id=uuid.UUID(user_id),
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    logger.info(f"Project member added: project={project_id}, user={user_id}")
    return {
        "id": str(member.id),
        "project_id": str(member.project_id),
        "user_id": str(member.user_id),
        "role": member.role,
        "joined_at": member.joined_at.isoformat(),
    }


async def list_projects(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    project_type: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出产品项目"""
    query = select(ProductProject)
    if organization_id:
        query = query.where(ProductProject.organization_id == uuid.UUID(organization_id))
    if project_type:
        query = query.where(ProductProject.project_type == project_type)
    if status:
        query = query.where(ProductProject.status == status)
    query = query.order_by(ProductProject.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def get_project(db: AsyncSession, project_id: str) -> dict:
    """获取产品项目详情"""
    result = await db.execute(
        select(ProductProject).where(ProductProject.id == uuid.UUID(project_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise DataNotFoundError("产品项目不存在")
    return _project_to_dict(project)


# ==================== 数据产品 CRUD ====================

async def create_product(
    db: AsyncSession,
    name: str,
    product_type: str,
    organization_id: str,
    owner_id: str,
    project_id: Optional[str] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
    technical_spec: Optional[dict] = None,
    pricing: Optional[dict] = None,
    delivery_config: Optional[dict] = None,
) -> dict:
    """创建数据产品"""
    if product_type not in VALID_PRODUCT_TYPES:
        raise DataValidationError(f"无效的产品类型: {product_type}, 可选: {VALID_PRODUCT_TYPES}")

    product = DataProduct(
        project_id=uuid.UUID(project_id) if project_id else None,
        name=name,
        description=description,
        product_type=product_type,
        version=version,
        organization_id=uuid.UUID(organization_id),
        owner_id=uuid.UUID(owner_id),
        technical_spec=technical_spec or {},
        pricing=pricing or {},
        delivery_config=delivery_config or {},
        status="development",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    logger.info(f"Data product created: {name} ({product_type})")
    return _product_to_dict(product)


async def update_product(db: AsyncSession, product_id: str, **kwargs) -> dict:
    """更新数据产品"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    allowed = [
        "name", "description", "product_type", "version",
        "technical_spec", "pricing", "delivery_config",
    ]
    for field in allowed:
        if field in kwargs and kwargs[field] is not None:
            setattr(product, field, kwargs[field])

    await db.commit()
    await db.refresh(product)
    logger.info(f"Data product updated: {product_id}")
    return _product_to_dict(product)


async def get_product(db: AsyncSession, product_id: str) -> dict:
    """获取数据产品详情"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")
    return _product_to_dict(product)


async def list_products(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    product_type: Optional[str] = None,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    keyword: Optional[str] = None,
) -> PaginatedResponse:
    """列出数据产品"""
    query = select(DataProduct)
    if organization_id:
        query = query.where(DataProduct.organization_id == uuid.UUID(organization_id))
    if product_type:
        query = query.where(DataProduct.product_type == product_type)
    if status:
        query = query.where(DataProduct.status == status)
    if project_id:
        query = query.where(DataProduct.project_id == uuid.UUID(project_id))
    if keyword:
        query = query.where(DataProduct.name.ilike(f"%{keyword}%"))
    query = query.order_by(DataProduct.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def delete_product(db: AsyncSession, product_id: str) -> bool:
    """删除数据产品（软删除）"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")
    if product.status == "published":
        raise DataValidationError("已发布产品不可直接删除，请先下架")

    product.status = "deleted"
    await db.commit()
    logger.info(f"Data product deleted: {product_id}")
    return True


# ==================== 产品状态流转 ====================

async def transition_product_status(
    db: AsyncSession,
    product_id: str,
    target_status: str,
    operator_id: str,
) -> dict:
    """产品状态流转"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    current = product.status
    allowed_targets = PRODUCT_STATUS_FLOW.get(current, [])
    if target_status not in allowed_targets:
        raise LifecycleStateError(
            f"不允许从 {current} 转换到 {target_status}, 允许: {allowed_targets}"
        )

    product.status = target_status
    if target_status == "published":
        product.published_at = datetime.now(timezone.utc)
    elif target_status == "unpublished":
        product.published_at = None

    await db.commit()
    await db.refresh(product)
    logger.info(f"Product {product_id} status: {current} → {target_status}")
    return _product_to_dict(product)


# ==================== 产品验收 ====================

async def create_acceptance(
    db: AsyncSession,
    product_id: str,
    acceptor_id: str,
    test_result: Optional[dict] = None,
    comment: Optional[str] = None,
) -> dict:
    """创建产品验收"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    acceptance = ProductAcceptance(
        product_id=uuid.UUID(product_id),
        acceptor_id=uuid.UUID(acceptor_id),
        test_result=test_result or {},
        status="pending",
        comment=comment,
    )
    db.add(acceptance)
    await db.commit()
    await db.refresh(acceptance)

    logger.info(f"Product acceptance created: product={product_id}")
    return _acceptance_to_dict(acceptance)


async def review_acceptance(
    db: AsyncSession,
    acceptance_id: str,
    status: str,
    comment: Optional[str] = None,
) -> dict:
    """审核产品验收"""
    result = await db.execute(
        select(ProductAcceptance).where(ProductAcceptance.id == uuid.UUID(acceptance_id))
    )
    acceptance = result.scalar_one_or_none()
    if not acceptance:
        raise DataNotFoundError("验收记录不存在")

    acceptance.status = status
    if comment:
        acceptance.comment = comment
    if status == "accepted":
        acceptance.accepted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(acceptance)
    logger.info(f"Product acceptance {acceptance_id} reviewed: {status}")
    return _acceptance_to_dict(acceptance)


# ==================== 上架审核（差异化周期） ====================

async def submit_for_review(
    db: AsyncSession,
    product_id: str,
    applicant_id: str,
    organization_id: str,
    control_protocol: Optional[dict] = None,
    compliance_docs: Optional[list] = None,
    pricing_config: Optional[dict] = None,
) -> dict:
    """提交产品上架审核"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")
    if product.status not in ("testing", "rejected"):
        raise DataValidationError(f"产品状态不允许提交审核: {product.status}")

    # 检查重复申请
    existing = await db.execute(
        select(ProductPublishRequest).where(
            ProductPublishRequest.product_id == uuid.UUID(product_id),
            ProductPublishRequest.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已有待审批的上架申请")

    # 计算差异化审核截止日期
    review_days = REVIEW_CYCLE_DAYS.get(product.product_type, 3)
    review_deadline = datetime.now(timezone.utc) + timedelta(days=review_days)

    request = ProductPublishRequest(
        product_id=uuid.UUID(product_id),
        applicant_id=uuid.UUID(applicant_id),
        organization_id=uuid.UUID(organization_id),
        review_deadline=review_deadline,
        control_protocol=control_protocol or {},
        compliance_docs=compliance_docs or [],
        pricing_config=pricing_config or {},
        status="pending",
    )
    db.add(request)

    # 更新产品状态
    product.status = "review_pending"

    await db.commit()
    await db.refresh(request)

    logger.info(
        f"Product {product_id} submitted for review, "
        f"type={product.product_type}, deadline={review_deadline.isoformat()}"
    )
    return {
        **_publish_request_to_dict(request),
        "review_cycle_days": review_days,
    }


async def compliance_check(
    db: AsyncSession,
    request_id: str,
    checker_id: str,
    passed: bool,
    comment: Optional[str] = None,
) -> dict:
    """合规检查"""
    result = await db.execute(
        select(ProductPublishRequest).where(ProductPublishRequest.id == uuid.UUID(request_id))
    )
    request = result.scalar_one_or_none()
    if not request:
        raise DataNotFoundError("上架申请不存在")
    if request.status != "pending":
        raise DataValidationError(f"申请状态不允许合规检查: {request.status}")

    if passed:
        request.status = "compliance_passed"
        # 更新产品状态
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "compliance_check"
    else:
        request.status = "rejected"
        request.reviewer_id = uuid.UUID(checker_id)
        request.review_comment = comment
        request.reviewed_at = datetime.now(timezone.utc)
        # 回退产品状态
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "rejected"

    await db.commit()
    await db.refresh(request)
    logger.info(f"Compliance check for request {request_id}: {'passed' if passed else 'rejected'}")
    return _publish_request_to_dict(request)


async def quality_review(
    db: AsyncSession,
    request_id: str,
    reviewer_id: str,
    passed: bool,
    comment: Optional[str] = None,
) -> dict:
    """质量评估（最终审核）"""
    result = await db.execute(
        select(ProductPublishRequest).where(ProductPublishRequest.id == uuid.UUID(request_id))
    )
    request = result.scalar_one_or_none()
    if not request:
        raise DataNotFoundError("上架申请不存在")
    if request.status != "compliance_passed":
        raise DataValidationError(f"申请状态不允许质量评估: {request.status}")

    request.reviewer_id = uuid.UUID(reviewer_id)
    request.review_comment = comment
    request.reviewed_at = datetime.now(timezone.utc)

    if passed:
        request.status = "approved"
        request.published_at = datetime.now(timezone.utc)
        # 更新产品状态为已发布
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "published"
            product.published_at = datetime.now(timezone.utc)
    else:
        request.status = "rejected"
        # 回退产品状态
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "rejected"

    await db.commit()
    await db.refresh(request)
    logger.info(f"Quality review for request {request_id}: {'approved' if passed else 'rejected'}")
    return _publish_request_to_dict(request)


async def review_publish_request(
    db: AsyncSession,
    request_id: str,
    reviewer_id: str,
    status: str,
    review_comment: Optional[str] = None,
) -> dict:
    """通用审核上架申请（兼容旧接口）"""
    result = await db.execute(
        select(ProductPublishRequest).where(ProductPublishRequest.id == uuid.UUID(request_id))
    )
    request = result.scalar_one_or_none()
    if not request:
        raise DataNotFoundError("上架申请不存在")
    if request.status != "pending":
        raise DataValidationError(f"申请状态不为待审批: {request.status}")

    request.status = status
    request.reviewer_id = uuid.UUID(reviewer_id)
    request.review_comment = review_comment
    request.reviewed_at = datetime.now(timezone.utc)

    if status == "approved":
        request.published_at = datetime.now(timezone.utc)
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "published"
            product.published_at = datetime.now(timezone.utc)
    elif status == "rejected":
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "rejected"

    await db.commit()
    await db.refresh(request)
    logger.info(f"Publish request {request_id} reviewed: {status}")
    return _publish_request_to_dict(request)


async def list_publish_requests(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    product_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出上架申请"""
    query = select(ProductPublishRequest)
    if status:
        query = query.where(ProductPublishRequest.status == status)
    if product_id:
        query = query.where(ProductPublishRequest.product_id == uuid.UUID(product_id))
    if organization_id:
        query = query.where(ProductPublishRequest.organization_id == uuid.UUID(organization_id))
    query = query.order_by(ProductPublishRequest.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


# ==================== 下架 ====================

async def create_unpublish_request(
    db: AsyncSession,
    product_id: str,
    applicant_id: str,
    reason: Optional[str] = None,
) -> dict:
    """创建产品下架申请"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")
    if product.status != "published":
        raise DataValidationError(f"产品状态不允许下架: {product.status}")

    request = ProductUnpublishRequest(
        product_id=uuid.UUID(product_id),
        applicant_id=uuid.UUID(applicant_id),
        reason=reason,
        status="pending",
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)

    logger.info(f"Product unpublish request created: product={product_id}")
    return _unpublish_request_to_dict(request)


async def review_unpublish_request(
    db: AsyncSession,
    request_id: str,
    reviewer_id: str,
    status: str,
    review_comment: Optional[str] = None,
) -> dict:
    """审核产品下架申请"""
    result = await db.execute(
        select(ProductUnpublishRequest).where(ProductUnpublishRequest.id == uuid.UUID(request_id))
    )
    request = result.scalar_one_or_none()
    if not request:
        raise DataNotFoundError("下架申请不存在")
    if request.status != "pending":
        raise DataValidationError(f"申请状态不为待审批: {request.status}")

    request.status = status
    request.reviewer_id = uuid.UUID(reviewer_id)
    request.review_comment = review_comment
    request.reviewed_at = datetime.now(timezone.utc)

    if status == "approved":
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "unpublished"
            product.published_at = None

    await db.commit()
    await db.refresh(request)
    logger.info(f"Product unpublish request {request_id} reviewed: {status}")
    return _unpublish_request_to_dict(request)


# ==================== 产品订阅交付 ====================

async def create_product_subscription(
    db: AsyncSession,
    product_id: str,
    subscriber_id: str,
    subscriber_org_id: str,
    reason: Optional[str] = None,
    subscription_config: Optional[dict] = None,
) -> dict:
    """创建产品订阅"""
    prod_result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")
    if product.status != "published":
        raise DataValidationError(f"产品状态不允许订阅: {product.status}")

    # 检查重复订阅
    existing = await db.execute(
        select(ProductSubscription).where(
            and_(
                ProductSubscription.product_id == uuid.UUID(product_id),
                ProductSubscription.subscriber_id == uuid.UUID(subscriber_id),
                ProductSubscription.status.in_(["pending", "approved", "active"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已存在对此产品的活跃订阅")

    subscription = ProductSubscription(
        product_id=uuid.UUID(product_id),
        subscriber_id=uuid.UUID(subscriber_id),
        subscriber_org_id=uuid.UUID(subscriber_org_id),
        reason=reason,
        subscription_config=subscription_config or {},
        status="pending",
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    logger.info(f"Product subscription created: product={product_id}, subscriber={subscriber_id}")
    return _product_subscription_to_dict(subscription)


async def approve_product_subscription(
    db: AsyncSession,
    subscription_id: str,
    approver_id: str,
    approved: bool,
    expires_at: Optional[str] = None,
) -> dict:
    """审批产品订阅"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("产品订阅不存在")
    if sub.status != "pending":
        raise DataValidationError(f"订阅状态不允许审批: {sub.status}")

    if approved:
        sub.status = "active"
        sub.approved_by = uuid.UUID(approver_id)
        sub.approved_at = datetime.now(timezone.utc)
        sub.expires_at = (
            datetime.fromisoformat(expires_at)
            if expires_at
            else datetime.now(timezone.utc) + timedelta(days=365)
        )
    else:
        sub.status = "rejected"
        sub.approved_by = uuid.UUID(approver_id)
        sub.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(sub)
    logger.info(f"Product subscription {subscription_id}: {'approved' if approved else 'rejected'}")
    return _product_subscription_to_dict(sub)


async def create_product_delivery(
    db: AsyncSession,
    subscription_id: str,
    delivery_type: str,
    delivery_config: Optional[dict] = None,
    access_url: Optional[str] = None,
) -> dict:
    """创建产品交付（Token生成 → 接口开通）"""
    result = await db.execute(
        select(ProductSubscription).where(ProductSubscription.id == uuid.UUID(subscription_id))
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise DataNotFoundError("产品订阅不存在")
    if sub.status != "active":
        raise DataValidationError(f"订阅状态不允许交付: {sub.status}")

    access_token = secrets.token_urlsafe(48)

    delivery = ProductDelivery(
        subscription_id=uuid.UUID(subscription_id),
        delivery_type=delivery_type,
        delivery_config=delivery_config or {},
        access_token=access_token,
        access_url=access_url,
        download_count=0,
        status="active",
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    logger.info(f"Product delivery created: subscription={subscription_id}")
    return _product_delivery_to_dict(delivery)


async def list_product_subscriptions(
    db: AsyncSession,
    params: PaginationParams,
    product_id: Optional[str] = None,
    subscriber_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出产品订阅"""
    query = select(ProductSubscription)
    if product_id:
        query = query.where(ProductSubscription.product_id == uuid.UUID(product_id))
    if subscriber_id:
        query = query.where(ProductSubscription.subscriber_id == uuid.UUID(subscriber_id))
    if status:
        query = query.where(ProductSubscription.status == status)
    query = query.order_by(ProductSubscription.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


# ==================== 版本管理 ====================

async def update_product_version(
    db: AsyncSession,
    product_id: str,
    new_version: str,
    changelog: Optional[str] = None,
    technical_spec: Optional[dict] = None,
) -> dict:
    """更新产品版本"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    old_version = product.version
    product.version = new_version
    if technical_spec:
        product.technical_spec = technical_spec

    await db.commit()
    await db.refresh(product)
    logger.info(f"Product {product_id} version: {old_version} → {new_version}")
    return _product_to_dict(product)


async def rollback_product_version(
    db: AsyncSession,
    product_id: str,
    target_version: str,
) -> dict:
    """回滚产品版本（记录操作，版本号回退）"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    old_version = product.version
    product.version = target_version
    product.status = "maintenance"

    await db.commit()
    await db.refresh(product)
    logger.info(f"Product {product_id} rolled back: {old_version} → {target_version}")
    return _product_to_dict(product)


# ==================== Helpers ====================

def _project_to_dict(project: ProductProject) -> dict:
    """项目转字典"""
    members = []
    for m in (project.members or []):
        members.append({
            "id": str(m.id),
            "project_id": str(m.project_id),
            "user_id": str(m.user_id),
            "role": m.role,
            "joined_at": m.joined_at.isoformat(),
        })
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "project_type": project.project_type,
        "organization_id": str(project.organization_id),
        "owner_id": str(project.owner_id),
        "data_sources": project.data_sources or [],
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "members": members,
    }


def _product_to_dict(product: DataProduct) -> dict:
    """产品转字典"""
    return {
        "id": str(product.id),
        "project_id": str(product.project_id) if product.project_id else None,
        "name": product.name,
        "description": product.description,
        "product_type": product.product_type,
        "compute_engine": product.compute_engine,
        "version": product.version,
        "organization_id": str(product.organization_id),
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
    }


def _acceptance_to_dict(a: ProductAcceptance) -> dict:
    """验收转字典"""
    return {
        "id": str(a.id),
        "product_id": str(a.product_id),
        "acceptor_id": str(a.acceptor_id),
        "test_result": a.test_result or {},
        "status": a.status,
        "comment": a.comment,
        "accepted_at": a.accepted_at.isoformat() if a.accepted_at else None,
        "created_at": a.created_at.isoformat(),
    }


def _publish_request_to_dict(r: ProductPublishRequest) -> dict:
    """上架申请转字典"""
    return {
        "id": str(r.id),
        "product_id": str(r.product_id),
        "applicant_id": str(r.applicant_id),
        "organization_id": str(r.organization_id),
        "review_deadline": r.review_deadline.isoformat() if r.review_deadline else None,
        "control_protocol": r.control_protocol or {},
        "compliance_docs": r.compliance_docs or [],
        "pricing_config": r.pricing_config or {},
        "status": r.status,
        "reviewer_id": str(r.reviewer_id) if r.reviewer_id else None,
        "review_comment": r.review_comment,
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "published_at": r.published_at.isoformat() if r.published_at else None,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


def _unpublish_request_to_dict(r: ProductUnpublishRequest) -> dict:
    """下架申请转字典"""
    return {
        "id": str(r.id),
        "product_id": str(r.product_id),
        "applicant_id": str(r.applicant_id),
        "reason": r.reason,
        "status": r.status,
        "reviewer_id": str(r.reviewer_id) if r.reviewer_id else None,
        "review_comment": r.review_comment,
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "created_at": r.created_at.isoformat(),
    }


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


def _product_delivery_to_dict(d: ProductDelivery) -> dict:
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
