"""
数据服务市场 API - /api/v1/data/market
可申请数据资产列表 / 资产详情 / 数据分类 / 市场统计
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.data_asset import DataAsset
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.data_asset import DataAssetResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.utils.pagination import paginate_query

router = APIRouter()


@router.get("/assets", response_model=ApiResponse[PaginatedResponse[DataAssetResponse]])
async def list_market_assets(
    pagination: PaginationParams = Depends(get_pagination_params),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    category: Optional[str] = Query(None, description="数据分类"),
    sensitivity_level: Optional[str] = Query(None, description="安全等级"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取可申请的数据资产列表（带分页、搜索、筛选）"""
    query = select(DataAsset).where(
        DataAsset.status.in_(["published", "active"]),
    )

    # 关键词搜索
    if keyword:
        search_term = f"%{keyword}%"
        query = query.where(
            or_(
                DataAsset.name.ilike(search_term),
                DataAsset.description.ilike(search_term),
            )
        )

    # 分类筛选
    if category:
        query = query.where(DataAsset.category == category)

    # 安全等级筛选
    if sensitivity_level:
        level_map = {"public": 4, "internal": 3, "confidential": 2, "secret": 1}
        level_num = level_map.get(sensitivity_level)
        if level_num is not None:
            query = query.where(DataAsset.classification_level == level_num)

    result = await paginate_query(db, query, pagination, DataAssetResponse)
    return ApiResponse(data=result)


@router.get("/assets/{asset_id}", response_model=ApiResponse[DataAssetResponse])
async def get_market_asset_detail(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取数据资产详情"""
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="数据资产未找到", data=None)
    if asset.status not in ("published", "active"):
        return ApiResponse(code=2002, message="数据资产不可用", data=None)
    return ApiResponse(data=DataAssetResponse.model_validate(asset))


@router.get("/categories", response_model=ApiResponse)
async def list_market_categories(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取数据分类列表（含每个分类的资产数量）"""
    result = await db.execute(
        select(
            DataAsset.category,
            func.count(DataAsset.id).label("count"),
        )
        .where(
            DataAsset.status.in_(["published", "active"]),
        )
        .group_by(DataAsset.category)
        .order_by(func.count(DataAsset.id).desc())
    )
    rows = result.all()
    categories = [
        {"category": row.category, "count": row.count}
        for row in rows
    ]
    return ApiResponse(data=categories)


@router.get("/stats", response_model=ApiResponse)
async def get_market_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取市场统计数据（资产总数、可申请数、本月新增、热门分类等）"""
    # 资产总数
    total_result = await db.execute(
        select(func.count(DataAsset.id)).where(
            DataAsset.status.in_(["published", "active"]),
        )
    )
    total_assets = total_result.scalar() or 0

    # 可申请数（已发布且状态为 active 的资产）
    available_result = await db.execute(
        select(func.count(DataAsset.id)).where(
            DataAsset.status.in_(["published", "active"]),
        )
    )
    available_assets = available_result.scalar() or 0

    # 本月新增
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_result = await db.execute(
        select(func.count(DataAsset.id)).where(
            DataAsset.created_at >= month_start,
            DataAsset.status.in_(["published", "active"]),
        )
    )
    monthly_new = new_result.scalar() or 0

    # 热门分类（数量最多的分类）
    hot_cat_result = await db.execute(
        select(
            DataAsset.category,
            func.count(DataAsset.id).label("count"),
        )
        .where(DataAsset.status.in_(["published", "active"]))
        .group_by(DataAsset.category)
        .order_by(func.count(DataAsset.id).desc())
        .limit(1)
    )
    hot_cat_row = hot_cat_result.first()
    hot_category = hot_cat_row.category if hot_cat_row else "未知"

    return ApiResponse(data={
        "total_assets": total_assets,
        "available_assets": available_assets,
        "monthly_new": monthly_new,
        "hot_category": hot_category,
    })
