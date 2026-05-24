"""
数据目录 API - /api/v1/data/catalog
浏览 / 搜索 / 脱敏预览 / 申请使用 / 评价反馈
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.data_asset import DataAssetResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import catalog_service

router = APIRouter()


@router.get("/suggestions", response_model=ApiResponse)
async def get_search_suggestions(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索建议（自动补全）

    基于已有资产名称和标签，返回匹配的搜索建议。
    """
    result = await catalog_service.get_search_suggestions(
        db=db,
        keyword=keyword,
        limit=limit,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[DataAssetResponse]])
async def browse_catalog(
    pagination: PaginationParams = Depends(get_pagination_params),
    category: Optional[str] = Query(None, description="按大类筛选"),
    classification_level: Optional[int] = Query(None, ge=1, le=4, description="按敏感级别筛选"),
    organization_id: Optional[str] = Query(None, description="按组织 ID 筛选"),
    db: AsyncSession = Depends(get_db),
):
    """浏览数据目录（只展示已发布资产）"""
    result = await catalog_service.browse_catalog(
        db=db,
        params=pagination,
        category=category,
        classification_level=classification_level,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/search", response_model=ApiResponse[PaginatedResponse[DataAssetResponse]])
async def search_catalog(
    q: str = Query("", description="搜索关键词"),
    category: Optional[str] = Query(None, description="按大类筛选"),
    classification_level: Optional[int] = Query(None, ge=1, le=4, description="按敏感级别筛选"),
    min_level: Optional[int] = Query(None, ge=1, le=4, description="最低级别"),
    max_level: Optional[int] = Query(None, ge=1, le=4, description="最高级别"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
):
    """搜索/筛选数据目录"""
    result = await catalog_service.search_catalog(
        db=db,
        params=pagination,
        q=q,
        category=category,
        classification_level=classification_level,
        min_level=min_level,
        max_level=max_level,
    )
    return ApiResponse(data=result)


@router.get("/{asset_id}/preview", response_model=ApiResponse)
async def preview_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """脱敏预览（最多10条，敏感字段掩码处理）"""
    result = await catalog_service.preview_asset(
        db=db,
        asset_id=asset_id,
        user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.post("/{asset_id}/apply", response_model=ApiResponse)
async def apply_for_access(
    asset_id: str,
    purpose: str = Query("", description="使用目的"),
    duration_days: int = Query(30, ge=1, le=365, description="申请使用天数"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """申请使用数据资产"""
    result = await catalog_service.apply_for_access(
        db=db,
        asset_id=asset_id,
        user_id=user["user_id"],
        purpose=purpose,
        duration_days=duration_days,
    )
    return ApiResponse(data=result)


@router.post("/{asset_id}/feedback", response_model=ApiResponse)
async def feedback_asset(
    asset_id: str,
    rating: int = Query(..., ge=1, le=5, description="评分 1-5"),
    comment: str = Query("", description="评价内容"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """评价反馈"""
    result = await catalog_service.submit_feedback(
        db=db,
        asset_id=asset_id,
        user_id=user["user_id"],
        rating=rating,
        comment=comment,
    )
    return ApiResponse(data=result)
