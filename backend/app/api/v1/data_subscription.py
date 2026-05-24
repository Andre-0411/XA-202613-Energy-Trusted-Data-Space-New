"""数据资源订阅 API - /api/v1/data-subscriptions"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.subscription import (
    DataSubscriptionCreate, DataSubscriptionUpdate, DataSubscriptionResponse,
    DataSubscriptionReview as SubscriptionReview, DeliveryInfo,
    DataDeliveryCreate, DataDeliveryResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import data_subscription_service, delivery_service, subscription_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R016: 数据资源搜索与浏览 ====================

@router.get("/resources/search", response_model=ApiResponse)
async def search_data_resources(
    keyword: str = Query(None, description="搜索关键词"),
    security_level: str = Query(None, description="安全等级"),
    catalog_type: str = Query(None, description="目录类型"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """搜索数据资源"""
    result = await data_subscription_service.search_resources(
        db=db, keyword=keyword, security_level=security_level,
        catalog_type=catalog_type, params=pagination,
    )
    return ApiResponse(data=result)


@router.get("/resources/browse", response_model=ApiResponse)
async def browse_data_resources(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """浏览数据资源中心"""
    result = await data_subscription_service.browse_resources(
        db=db, params=pagination,
    )
    return ApiResponse(data=result)


# ==================== R017: 订阅申请 ====================

@router.post("/", response_model=ApiResponse[DataSubscriptionResponse], status_code=201)
async def create_subscription(
    request: DataSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """提交订阅申请"""
    result = await data_subscription_service.create_subscription(
        db=db,
        catalog_id=request.catalog_id,
        subscriber_id=user["user_id"],
        subscriber_org_id=user["organization_id"],
        reason=request.reason,
        subscription_config=request.subscription_config,
    )
    return ApiResponse(data=result)


@router.get("/", response_model=ApiResponse[PaginatedResponse[DataSubscriptionResponse]])
async def list_subscriptions(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取订阅列表"""
    result = await data_subscription_service.list_subscriptions(
        db=db, subscriber_id=user["user_id"], status=status, params=pagination,
    )
    return ApiResponse(data=result)


# ==================== R018: 订阅审批 ====================

@router.put("/{subscription_id}/review", response_model=ApiResponse)
async def review_subscription(
    subscription_id: str,
    request: SubscriptionReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批订阅（含合约/协议配置）"""
    result = await data_subscription_service.review_subscription(
        db=db, subscription_id=subscription_id,
        reviewer_id=user["user_id"],
        action=request.action,
        comment=request.comment,
        contract_id=request.contract_id,
        subscription_config=request.subscription_config,
    )
    return ApiResponse(data=result)


@router.get("/{subscription_id}", response_model=ApiResponse[DataSubscriptionResponse])
async def get_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取订阅详情"""
    result = await data_subscription_service.get_subscription(
        db=db, subscription_id=subscription_id,
    )
    return ApiResponse(data=result)


# ==================== R019: 数据交付 ====================

@router.post("/{subscription_id}/deliver", response_model=ApiResponse)
async def trigger_delivery(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """触发数据交付"""
    result = await delivery_service.trigger_delivery(
        db=db, subscription_id=subscription_id,
    )
    return ApiResponse(data=result)


@router.get("/{subscription_id}/delivery", response_model=ApiResponse[DeliveryInfo])
async def get_delivery_info(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取交付信息"""
    result = await delivery_service.get_delivery_info(
        db=db, subscription_id=subscription_id,
    )
    return ApiResponse(data=result)


# ==================== 订阅更新/取消 ====================

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


@router.post("/{subscription_id}/cancel", response_model=ApiResponse)
async def cancel_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """取消订阅"""
    await subscription_service.cancel_subscription(db, subscription_id, user["user_id"])
    return ApiResponse(message="订阅已取消")


# ==================== 数据交付管理 ====================

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
