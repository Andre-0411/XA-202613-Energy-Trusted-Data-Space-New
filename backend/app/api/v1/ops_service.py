"""
服务管理 API - /api/v1/ops/services
服务目录CRUD + 订阅管理 + 审批
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.service import ServiceCatalog, Subscription
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.service import (
    ServiceCreate, ServiceResponse,
    SubscriptionCreate, SubscriptionResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.utils.pagination import paginate_query
from app.exceptions import DataNotFoundError, PermissionDeniedError

router = APIRouter()


@router.get("", response_model=ApiResponse[PaginatedResponse[ServiceResponse]])
async def list_services(
    category: Optional[str] = Query(None, description="分类过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """服务目录"""
    query = select(ServiceCatalog)
    if category:
        query = query.where(ServiceCatalog.category == category)
    if status:
        query = query.where(ServiceCatalog.status == status)
    result = await paginate_query(db, query, pagination, ServiceResponse)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[ServiceResponse], status_code=201)
async def create_service(
    request: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建服务"""
    service = ServiceCatalog(
        name=request.name,
        category=request.category,
        parent_id=uuid.UUID(request.parent_id) if request.parent_id else None,
        level=request.level,
        description=request.description,
        pricing_model=request.pricing_model,
        pricing_config=request.pricing_config,
        quota_limit=request.quota_limit,
        status="active",
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return ApiResponse(data=ServiceResponse.model_validate(service))


@router.get("/{service_id}", response_model=ApiResponse[ServiceResponse])
async def get_service(
    service_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """服务详情"""
    result = await db.execute(
        select(ServiceCatalog).where(
            ServiceCatalog.id == uuid.UUID(service_id)
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise DataNotFoundError(message=f"服务不存在: {service_id}")
    return ApiResponse(data=ServiceResponse.model_validate(service))


@router.put("/{service_id}", response_model=ApiResponse[ServiceResponse])
async def update_service(
    service_id: str,
    request: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新服务"""
    result = await db.execute(
        select(ServiceCatalog).where(
            ServiceCatalog.id == uuid.UUID(service_id)
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise DataNotFoundError(message=f"服务不存在: {service_id}")

    service.name = request.name
    service.category = request.category
    service.description = request.description
    service.pricing_model = request.pricing_model
    service.pricing_config = request.pricing_config
    service.quota_limit = request.quota_limit

    await db.commit()
    await db.refresh(service)
    return ApiResponse(data=ServiceResponse.model_validate(service))


@router.get("/{service_id}/subscriptions", response_model=ApiResponse[PaginatedResponse[SubscriptionResponse]])
async def list_subscriptions(
    service_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """订阅列表"""
    query = select(Subscription).where(
        Subscription.service_id == uuid.UUID(service_id)
    )
    result = await paginate_query(db, query, pagination, SubscriptionResponse)
    return ApiResponse(data=result)


@router.post("/{service_id}/subscribe", response_model=ApiResponse[SubscriptionResponse], status_code=201)
async def subscribe_service(
    service_id: str,
    request: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """订阅服务"""
    # 验证服务存在
    svc_result = await db.execute(
        select(ServiceCatalog).where(
            ServiceCatalog.id == uuid.UUID(service_id)
        )
    )
    if not svc_result.scalar_one_or_none():
        raise DataNotFoundError(message=f"服务不存在: {service_id}")

    subscription = Subscription(
        user_id=uuid.UUID(user["user_id"]),
        service_id=uuid.UUID(service_id),
        status="pending",
        start_date=request.start_date,
        end_date=request.end_date,
        quota_used=0,
        approval_status="pending",
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return ApiResponse(data=SubscriptionResponse.model_validate(subscription))


@router.put("/subscriptions/{sub_id}/approve", response_model=ApiResponse[SubscriptionResponse])
async def approve_subscription(
    sub_id: str,
    approved: bool = True,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批订阅"""
    result = await db.execute(
        select(Subscription).where(Subscription.id == uuid.UUID(sub_id))
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise DataNotFoundError(message=f"订阅不存在: {sub_id}")

    if approved:
        subscription.approval_status = "approved"
        subscription.status = "active"
        subscription.approved_by = uuid.UUID(user["user_id"])
    else:
        subscription.approval_status = "rejected"
        subscription.status = "cancelled"

    await db.commit()
    await db.refresh(subscription)
    return ApiResponse(data=SubscriptionResponse.model_validate(subscription))
