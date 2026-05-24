"""数据产品上架 API - /api/v1/product-publish"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.product import (
    ProductPublishRequest, ProductPublishResponse,
    ProductPublishReview, UnpublishRequest, UnpublishReview,
    ControlProtocolConfig, ComplianceDocUpload,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import product_publish_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R028: 产品上架申请 ====================

@router.post("/", response_model=ApiResponse[ProductPublishResponse], status_code=201)
async def create_publish_request(
    request: ProductPublishRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """提交上架申请"""
    result = await product_publish_service.create_publish_request(
        db=db,
        product_id=request.product_id,
        applicant_id=user["user_id"],
        organization_id=user["organization_id"],
        data=request.dict(),
    )
    return ApiResponse(data=result)


@router.get("/", response_model=ApiResponse[PaginatedResponse[ProductPublishResponse]])
async def list_publish_requests(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取上架申请列表"""
    result = await product_publish_service.list_publish_requests(
        db=db, organization_id=user.get("organization_id"),
        status=status, params=pagination,
    )
    return ApiResponse(data=result)


@router.put("/{request_id}/review", response_model=ApiResponse)
async def review_publish_request(
    request_id: str,
    request: ProductPublishReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核上架申请"""
    result = await product_publish_service.review_publish_request(
        db=db, request_id=request_id,
        reviewer_id=user["user_id"],
        action=request.action,
        comment=request.comment,
    )
    return ApiResponse(data=result)


# ==================== R030: 管控协议配置 ====================

@router.post("/{request_id}/control-protocol", response_model=ApiResponse)
async def configure_publish_control_protocol(
    request_id: str,
    request: ControlProtocolConfig,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """配置管控协议"""
    result = await product_publish_service.configure_control_protocol(
        db=db, request_id=request_id, protocol_config=request.dict(),
    )
    return ApiResponse(data=result)


# ==================== R031: 合规材料上传 ====================

@router.post("/{request_id}/compliance-docs", response_model=ApiResponse)
async def upload_publish_compliance_docs(
    request_id: str,
    request: ComplianceDocUpload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """上传合规材料"""
    result = await product_publish_service.upload_compliance_docs(
        db=db, request_id=request_id, docs=request.docs,
    )
    return ApiResponse(data=result)


# ==================== R032: 产品下架 ====================

@router.post("/unpublish", response_model=ApiResponse, status_code=201)
async def create_unpublish_request(
    request: UnpublishRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """提交下架申请"""
    result = await product_publish_service.create_unpublish_request(
        db=db,
        product_id=request.product_id,
        applicant_id=user["user_id"],
        reason=request.reason,
    )
    return ApiResponse(data=result)


@router.put("/unpublish/{request_id}/review", response_model=ApiResponse)
async def review_unpublish_request(
    request_id: str,
    request: UnpublishReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核下架申请"""
    result = await product_publish_service.review_unpublish_request(
        db=db, request_id=request_id,
        reviewer_id=user["user_id"],
        action=request.action,
        comment=request.comment,
    )
    return ApiResponse(data=result)
