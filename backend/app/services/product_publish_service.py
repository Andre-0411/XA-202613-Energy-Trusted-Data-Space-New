"""
产品上架/下架服务
产品发布申请/审核/管理
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import (
    DataProduct, ProductPublishRequest, ProductUnpublishRequest,
)
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError

logger = logging.getLogger(__name__)


# ==================== 上架申请 ====================

async def create_publish_request(
    db: AsyncSession,
    product_id: str,
    applicant_id: str,
    organization_id: str,
    review_deadline: Optional[str] = None,
    control_protocol: Optional[dict] = None,
    compliance_docs: Optional[list] = None,
    pricing_config: Optional[dict] = None,
) -> dict:
    """创建产品上架申请"""
    # 验证产品存在
    prod_result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    # 检查重复申请
    existing = await db.execute(
        select(ProductPublishRequest).where(
            ProductPublishRequest.product_id == uuid.UUID(product_id),
            ProductPublishRequest.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已有待审批的上架申请")

    request = ProductPublishRequest(
        product_id=uuid.UUID(product_id),
        applicant_id=uuid.UUID(applicant_id),
        organization_id=uuid.UUID(organization_id),
        review_deadline=datetime.fromisoformat(review_deadline) if review_deadline else None,
        control_protocol=control_protocol or {},
        compliance_docs=compliance_docs or [],
        pricing_config=pricing_config or {},
        status="pending",
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)

    logger.info(f"Product publish request created: product={product_id}")
    return _publish_request_to_dict(request)


async def review_publish_request(
    db: AsyncSession,
    request_id: str,
    reviewer_id: str,
    status: str,
    review_comment: Optional[str] = None,
) -> dict:
    """审核产品上架申请"""
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

    # 如果审批通过，更新产品状态
    if status == "approved":
        request.published_at = datetime.now(timezone.utc)
        prod_result = await db.execute(
            select(DataProduct).where(DataProduct.id == request.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.status = "published"
            product.published_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(request)
    logger.info(f"Product publish request {request_id} reviewed: {status}")
    return _publish_request_to_dict(request)


async def get_publish_request(db: AsyncSession, request_id: str) -> dict:
    """获取上架申请详情"""
    result = await db.execute(
        select(ProductPublishRequest).where(ProductPublishRequest.id == uuid.UUID(request_id))
    )
    request = result.scalar_one_or_none()
    if not request:
        raise DataNotFoundError("上架申请不存在")
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

    from app.schemas.product import ProductPublishRequestResponse
    result = await paginate_query(db, query, params, ProductPublishRequestResponse)
    return result


# ==================== 下架申请 ====================

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

    # 如果审批通过，更新产品状态
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


async def list_unpublish_requests(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    product_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出下架申请"""
    query = select(ProductUnpublishRequest)
    if status:
        query = query.where(ProductUnpublishRequest.status == status)
    if product_id:
        query = query.where(ProductUnpublishRequest.product_id == uuid.UUID(product_id))
    query = query.order_by(ProductUnpublishRequest.created_at.desc())

    from app.schemas.product import ProductUnpublishResponse
    result = await paginate_query(db, query, params, ProductUnpublishResponse)
    return result


# ==================== Helpers ====================

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
