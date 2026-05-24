"""数据产品 API - /api/v1/products"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.product import (
    ProductProjectCreate, ProductProjectUpdate, ProductProjectResponse, ProjectMemberCreate, ProjectMemberResponse,
    DataProductCreate, DataProductUpdate, DataProductResponse,
    ProductAcceptanceCreate, ProductAcceptanceResponse,
    ProductPublishCreate, ProductPublishReview, ProductPublishRequestResponse,
    ProductUnpublishCreate, ProductUnpublishResponse,
    ProductSubscriptionCreate, ProductSubscriptionReview, ProductSubscriptionResponse,
    ProductDeliveryCreate, ProductDeliveryResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import product_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 产品项目 ====================

@router.post("/projects", response_model=ApiResponse[ProductProjectResponse], status_code=201)
async def create_project(
    request: ProductProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建产品项目"""
    result = await product_service.create_project(
        db=db,
        owner_id=user["user_id"],
        organization_id=user.get("organization_id", ""),
        name=request.name,
        project_type=request.project_type,
        description=request.description,
        data_sources=request.data_sources,
    )
    return ApiResponse(data=result)


@router.get("/projects", response_model=ApiResponse[PaginatedResponse[ProductProjectResponse]])
async def list_projects(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    project_type: Optional[str] = Query(None, description="项目类型"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出产品项目"""
    result = await product_service.list_projects(
        db, pagination, user.get("organization_id"), status=status, project_type=project_type
    )
    return ApiResponse(data=result)


@router.get("/projects/{project_id}", response_model=ApiResponse[ProductProjectResponse])
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取项目详情"""
    result = await product_service.get_project(db, project_id)
    return ApiResponse(data=result)


@router.put("/projects/{project_id}", response_model=ApiResponse[ProductProjectResponse])
async def update_project(
    project_id: str,
    request: ProductProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新项目"""
    result = await product_service.update_project(
        db, project_id,
        name=request.name,
        description=request.description,
        project_type=request.project_type,
        data_sources=request.data_sources,
        status=request.status,
    )
    return ApiResponse(data=result)


@router.delete("/projects/{project_id}", response_model=ApiResponse)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除项目"""
    await product_service.delete_project(db, project_id)
    return ApiResponse(message="项目已删除")


@router.post("/projects/{project_id}/members", response_model=ApiResponse[ProjectMemberResponse], status_code=201)
async def add_project_member(
    project_id: str,
    request: ProjectMemberCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """添加项目成员"""
    result = await product_service.add_project_member(db, project_id, request.user_id, request.role)
    return ApiResponse(data=result)


@router.delete("/projects/{project_id}/members/{member_user_id}", response_model=ApiResponse)
async def remove_project_member(
    project_id: str,
    member_user_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """移除项目成员"""
    await product_service.remove_project_member(db, project_id, member_user_id)
    return ApiResponse(message="成员已移除")


# ==================== 数据产品 CRUD ====================

@router.post("", response_model=ApiResponse[DataProductResponse], status_code=201)
async def create_product(
    request: DataProductCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建数据产品"""
    result = await product_service.create_product(
        db=db,
        owner_id=user["user_id"],
        organization_id=user.get("organization_id", ""),
        name=request.name,
        product_type=request.product_type,
        project_id=request.project_id,
        description=request.description,
        compute_engine=request.compute_engine,
        version=request.version,
        technical_spec=request.technical_spec,
        pricing=request.pricing,
        delivery_config=request.delivery_config,
        compliance_docs=request.compliance_docs,
        control_protocol=request.control_protocol,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[DataProductResponse]])
async def list_products(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    product_type: Optional[str] = Query(None, description="产品类型"),
    project_id: Optional[str] = Query(None, description="项目 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出数据产品"""
    result = await product_service.list_products(
        db, pagination, user.get("organization_id"), status=status,
        product_type=product_type, project_id=project_id,
    )
    return ApiResponse(data=result)


@router.get("/{product_id}", response_model=ApiResponse[DataProductResponse])
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取产品详情"""
    result = await product_service.get_product(db, product_id)
    return ApiResponse(data=result)


@router.put("/{product_id}", response_model=ApiResponse[DataProductResponse])
async def update_product(
    product_id: str,
    request: DataProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新数据产品"""
    result = await product_service.update_product(
        db, product_id,
        name=request.name,
        description=request.description,
        product_type=request.product_type,
        compute_engine=request.compute_engine,
        version=request.version,
        technical_spec=request.technical_spec,
        pricing=request.pricing,
        delivery_config=request.delivery_config,
        compliance_docs=request.compliance_docs,
        control_protocol=request.control_protocol,
        status=request.status,
    )
    return ApiResponse(data=result)


@router.delete("/{product_id}", response_model=ApiResponse)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除数据产品"""
    await product_service.delete_product(db, product_id)
    return ApiResponse(message="数据产品已删除")


# ==================== 产品验收 ====================

@router.post("/{product_id}/acceptances", response_model=ApiResponse[ProductAcceptanceResponse], status_code=201)
async def create_acceptance(
    product_id: str,
    request: ProductAcceptanceCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建产品验收"""
    result = await product_service.create_acceptance(
        db, product_id, request.acceptor_id, request.test_result, request.comment
    )
    return ApiResponse(data=result)


@router.get("/{product_id}/acceptances", response_model=ApiResponse[PaginatedResponse[ProductAcceptanceResponse]])
async def list_acceptances(
    product_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出验收记录"""
    result = await product_service.list_acceptances(db, pagination, product_id, status)
    return ApiResponse(data=result)


@router.post("/acceptances/{acceptance_id}/review", response_model=ApiResponse)
async def review_acceptance(
    acceptance_id: str,
    status: str = Query(..., description="审核结果: approved/rejected"),
    comment: Optional[str] = Query(None, description="审核意见"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核产品验收"""
    result = await product_service.review_acceptance(db, acceptance_id, status, comment)
    return ApiResponse(data=result)


# ==================== 产品上下架 ====================

@router.post("/{product_id}/publish", response_model=ApiResponse[ProductPublishRequestResponse], status_code=201)
async def create_publish_request(
    product_id: str,
    request: ProductPublishCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建上架申请"""
    result = await product_service.create_publish_request(
        db=db,
        product_id=product_id,
        applicant_id=user["user_id"],
        organization_id=user.get("organization_id", ""),
        review_deadline=request.review_deadline,
        control_protocol=request.control_protocol,
        compliance_docs=request.compliance_docs,
        pricing_config=request.pricing_config,
    )
    return ApiResponse(data=result)


@router.get("/publish-requests", response_model=ApiResponse[PaginatedResponse[ProductPublishRequestResponse]])
async def list_publish_requests(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    product_id: Optional[str] = Query(None, description="产品 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出上架申请"""
    result = await product_service.list_publish_requests(
        db, pagination, status, product_id, user.get("organization_id")
    )
    return ApiResponse(data=result)


@router.post("/publish-requests/{request_id}/review", response_model=ApiResponse)
async def review_publish_request(
    request_id: str,
    request: ProductPublishReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核上架申请"""
    result = await product_service.review_publish_request(
        db, request_id, user["user_id"], request.status, request.review_comment
    )
    return ApiResponse(data=result)


@router.post("/{product_id}/unpublish", response_model=ApiResponse[ProductUnpublishResponse], status_code=201)
async def create_unpublish_request(
    product_id: str,
    request: ProductUnpublishCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建下架申请"""
    result = await product_service.create_unpublish_request(db, product_id, user["user_id"], request.reason)
    return ApiResponse(data=result)


@router.post("/unpublish-requests/{request_id}/review", response_model=ApiResponse)
async def review_unpublish_request(
    request_id: str,
    request: ProductPublishReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核下架申请"""
    result = await product_service.review_unpublish_request(
        db, request_id, user["user_id"], request.status, request.review_comment
    )
    return ApiResponse(data=result)


# ==================== 产品订阅 ====================

@router.post("/{product_id}/subscriptions", response_model=ApiResponse[ProductSubscriptionResponse], status_code=201)
async def create_product_subscription(
    product_id: str,
    request: ProductSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建产品订阅"""
    result = await product_service.create_product_subscription(
        db=db,
        product_id=product_id,
        subscriber_id=user["user_id"],
        subscriber_org_id=user.get("organization_id", ""),
        reason=request.reason,
        subscription_config=request.subscription_config,
        delivery_config=request.delivery_config,
    )
    return ApiResponse(data=result)


@router.get("/{product_id}/subscriptions", response_model=ApiResponse[PaginatedResponse[ProductSubscriptionResponse]])
async def list_product_subscriptions(
    product_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出产品订阅"""
    result = await product_service.list_product_subscriptions(db, pagination, status, product_id)
    return ApiResponse(data=result)


@router.post("/subscriptions/{subscription_id}/review", response_model=ApiResponse)
async def review_product_subscription(
    subscription_id: str,
    request: ProductSubscriptionReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核产品订阅"""
    result = await product_service.review_product_subscription(
        db, subscription_id, user["user_id"], request.status, request.expires_at
    )
    return ApiResponse(data=result)


# ==================== 产品交付 ====================

@router.post("/subscriptions/{subscription_id}/deliveries", response_model=ApiResponse[ProductDeliveryResponse], status_code=201)
async def create_product_delivery(
    subscription_id: str,
    request: ProductDeliveryCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建产品交付"""
    result = await product_service.create_product_delivery(
        db, subscription_id, request.delivery_type, request.delivery_config
    )
    return ApiResponse(data=result)


@router.post("/deliveries/{delivery_id}/download", response_model=ApiResponse)
async def record_product_download(
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """记录产品下载"""
    result = await product_service.record_product_download(db, delivery_id)
    return ApiResponse(data=result)
