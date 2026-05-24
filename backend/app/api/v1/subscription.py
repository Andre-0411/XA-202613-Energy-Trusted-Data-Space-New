"""数据资源订阅 API - /api/v1/subscriptions"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.subscription import (
    DataSubscriptionCreate, DataSubscriptionUpdate, DataSubscriptionReview, DataSubscriptionResponse,
    DataDeliveryCreate, DataDeliveryResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import subscription_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 数据订阅 CRUD ====================

@router.post("", response_model=ApiResponse[DataSubscriptionResponse], status_code=201)
async def create_subscription(
    request: DataSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建数据资源订阅申请"""
    result = await subscription_service.create_subscription(
        db=db,
        subscriber_id=user["user_id"],
        subscriber_org_id=user.get("organization_id", ""),
        catalog_id=request.catalog_id,
        reason=request.reason,
        subscription_config=request.subscription_config,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[DataSubscriptionResponse]])
async def list_subscriptions(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    catalog_id: Optional[str] = Query(None, description="目录 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出数据订阅"""
    result = await subscription_service.list_subscriptions(
        db, pagination, status, catalog_id, user.get("user_id"), user.get("organization_id")
    )
    return ApiResponse(data=result)


@router.get("/{subscription_id}", response_model=ApiResponse[DataSubscriptionResponse])
async def get_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取订阅详情"""
    result = await subscription_service.get_subscription(db, subscription_id)
    return ApiResponse(data=result)


@router.put("/{subscription_id}", response_model=ApiResponse[DataSubscriptionResponse])
async def update_subscription(
    subscription_id: str,
    request: DataSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新订阅"""
    result = await subscription_service.update_subscription(
        db, subscription_id,
        reason=request.reason,
        subscription_config=request.subscription_config,
        status=request.status,
    )
    return ApiResponse(data=result)


@router.post("/{subscription_id}/review", response_model=ApiResponse)
async def review_subscription(
    subscription_id: str,
    request: DataSubscriptionReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核订阅申请"""
    result = await subscription_service.review_subscription(
        db=db,
        subscription_id=subscription_id,
        reviewer_id=user["user_id"],
        status=request.status,
        expires_at=request.expires_at,
    )
    return ApiResponse(data=result)


@router.post("/{subscription_id}/cancel", response_model=ApiResponse)
async def cancel_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """取消订阅"""
    await subscription_service.cancel_subscription(db, subscription_id, user["user_id"])
    return ApiResponse(message="订阅已取消")


# ==================== 数据交付 ====================

@router.post("/{subscription_id}/deliveries", response_model=ApiResponse[DataDeliveryResponse], status_code=201)
async def create_delivery(
    subscription_id: str,
    request: DataDeliveryCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建数据交付"""
    result = await subscription_service.create_delivery(
        db=db,
        subscription_id=subscription_id,
        delivery_type=request.delivery_type,
        delivery_config=request.delivery_config,
    )
    return ApiResponse(data=result)


@router.get("/{subscription_id}/deliveries", response_model=ApiResponse[PaginatedResponse[DataDeliveryResponse]])
async def list_deliveries(
    subscription_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出交付记录"""
    result = await subscription_service.list_deliveries(db, pagination, subscription_id)
    return ApiResponse(data=result)


@router.post("/{subscription_id}/deliveries/{delivery_id}/download", response_model=ApiResponse)
async def record_download(
    subscription_id: str,
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """记录下载"""
    result = await subscription_service.record_download(db, delivery_id)
    return ApiResponse(data=result)


@router.post("/{subscription_id}/deliveries/{delivery_id}/revoke", response_model=ApiResponse)
async def revoke_delivery(
    subscription_id: str,
    delivery_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """撤销交付"""
    await subscription_service.revoke_delivery(db, delivery_id)
    return ApiResponse(message="交付已撤销")
