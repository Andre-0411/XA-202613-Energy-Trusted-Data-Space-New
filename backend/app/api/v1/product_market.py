"""数据产品市场 API - /api/v1/product-market"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.product import (
    ProductMarketItem, ProductSubscriptionCreate,
    ProductSubscriptionResponse, ProductSubscriptionReview,
    ContractFiling, ProductDeliveryInfo,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import product_market_service, product_delivery_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R033: 产品市场搜索与推荐 ====================

@router.get("/search", response_model=ApiResponse)
async def search_products(
    keyword: str = Query(None, description="搜索关键词"),
    product_type: str = Query(None, description="产品类型"),
    pricing_type: str = Query(None, description="定价类型"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """搜索数据产品"""
    result = await product_market_service.search_products(
        db=db, keyword=keyword, product_type=product_type,
        pricing_type=pricing_type, params=pagination,
    )
    return ApiResponse(data=result)


@router.get("/recommend", response_model=ApiResponse)
async def recommend_products(
    limit: int = Query(10, description="推荐数量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """产品推荐"""
    result = await product_market_service.recommend_products(
        db=db, user_id=user["user_id"], limit=limit,
    )
    return ApiResponse(data=result)


# ==================== R034: 产品订阅 ====================

@router.post("/subscriptions", response_model=ApiResponse[ProductSubscriptionResponse], status_code=201)
async def create_product_subscription(
    request: ProductSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """提交产品订阅申请"""
    result = await product_market_service.create_subscription(
        db=db,
        product_id=request.product_id,
        subscriber_id=user["user_id"],
        subscriber_org_id=user["organization_id"],
        reason=request.reason,
        subscription_config=request.subscription_config,
    )
    return ApiResponse(data=result)


@router.get("/subscriptions", response_model=ApiResponse[PaginatedResponse[ProductSubscriptionResponse]])
async def list_product_subscriptions(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取产品订阅列表"""
    result = await product_market_service.list_subscriptions(
        db=db, subscriber_id=user["user_id"], status=status, params=pagination,
    )
    return ApiResponse(data=result)


@router.put("/subscriptions/{subscription_id}/review", response_model=ApiResponse)
async def review_product_subscription(
    subscription_id: str,
    request: ProductSubscriptionReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批产品订阅"""
    result = await product_market_service.review_subscription(
        db=db, subscription_id=subscription_id,
        reviewer_id=user["user_id"],
        action=request.action,
        comment=request.comment,
    )
    return ApiResponse(data=result)


# ==================== R035: 合约备案 ====================

@router.post("/subscriptions/{subscription_id}/contract", response_model=ApiResponse)
async def file_contract(
    subscription_id: str,
    request: ContractFiling,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """备案合约"""
    result = await product_market_service.file_contract(
        db=db, subscription_id=subscription_id,
        contract_id=request.contract_id,
    )
    return ApiResponse(data=result)


# ==================== R036: 产品交付 ====================

@router.post("/subscriptions/{subscription_id}/deliver", response_model=ApiResponse)
async def trigger_product_delivery(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """触发产品交付"""
    result = await product_delivery_service.trigger_delivery(
        db=db, subscription_id=subscription_id,
    )
    return ApiResponse(data=result)


@router.get("/subscriptions/{subscription_id}/delivery", response_model=ApiResponse[ProductDeliveryInfo])
async def get_product_delivery(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取产品交付信息"""
    result = await product_delivery_service.get_delivery_info(
        db=db, subscription_id=subscription_id,
    )
    return ApiResponse(data=result)
