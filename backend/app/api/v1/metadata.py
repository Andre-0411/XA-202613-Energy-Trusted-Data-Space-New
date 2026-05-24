"""
元数据 API - /api/v1/data/metadata
元数据 CRUD / 血缘可视化 / 版本管理
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.data_asset import Metadata
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.data_asset import MetadataCreate, MetadataResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import metadata_service

router = APIRouter()


@router.get("", response_model=ApiResponse[PaginatedResponse[MetadataResponse]])
async def list_metadata(
    asset_id: Optional[str] = Query(None, description="按资产 ID 筛选"),
    standard: Optional[str] = Query(None, description="按标准筛选"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """元数据列表"""
    result = await metadata_service.list_metadata(
        db=db,
        params=pagination,
        asset_id=asset_id,
        standard=standard,
    )
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[MetadataResponse], status_code=201)
async def create_metadata(
    request: MetadataCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建元数据（遵循 GB/T 36073-2018）

    每个资产只能有一条元数据记录，版本自动管理
    """
    result = await metadata_service.create_metadata(
        db=db,
        request=request,
        user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.get("/{meta_id}", response_model=ApiResponse[MetadataResponse])
async def get_metadata(
    meta_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """元数据详情"""
    result = await metadata_service.get_metadata(
        db=db,
        metadata_id=meta_id,
    )
    return ApiResponse(data=result)


@router.put("/{meta_id}", response_model=ApiResponse[MetadataResponse])
async def update_metadata(
    meta_id: str,
    request: MetadataCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    更新元数据（自动版本管理）

    更新后版本号自动递增，previous_version_id 指向上一版本
    """
    result = await metadata_service.update_metadata(
        db=db,
        metadata_id=meta_id,
        request=request,
        user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.get("/{meta_id}/lineage", response_model=ApiResponse)
async def get_lineage(
    meta_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    血缘可视化

    返回图结构的 nodes 和 edges，用于前端渲染数据血缘图
    节点类型: source(数据源) / asset(资产) / process(处理) / output(输出)
    """
    result = await metadata_service.get_lineage(
        db=db,
        metadata_id=meta_id,
    )
    return ApiResponse(data=result)


@router.get("/{meta_id}/versions", response_model=ApiResponse)
async def get_versions(
    meta_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    版本列表

    通过 previous_version_id 链回溯所有历史版本
    """
    result = await metadata_service.get_versions(
        db=db,
        metadata_id=meta_id,
    )
    return ApiResponse(data=result)
