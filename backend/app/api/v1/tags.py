"""
标签 API - /api/v1/data/tags
标签列表 / 创建标签 / 按维度聚合 / 标签分配
三维标签体系 / 搜索筛选
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import tag_service

router = APIRouter()


class BatchAssignTagsRequest(BaseModel):
    """批量分配标签请求"""
    asset_id: str = Field(..., description="资产ID")
    tag_ids: list[str] = Field(..., description="标签ID列表")


@router.get("", response_model=ApiResponse)
async def list_tags(
    dimension: Optional[str] = Query(None, description="按维度筛选: industry/security/business/format/source/topic/business_dimension/technical_dimension/quality_dimension"),
    parent_id: Optional[str] = Query(None, description="按父标签 ID 筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    标签列表

    支持按维度和父标签筛选，返回每个标签关联的资产数量
    """
    result = await tag_service.list_tags(
        db=db,
        dimension=dimension,
        parent_id=parent_id,
    )
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse, status_code=201)
async def create_tag(
    name: str = Query(..., max_length=100, description="标签名称"),
    dimension: str = Query(..., description="标签维度: industry/security/business/format/source/topic/business_dimension/technical_dimension/quality_dimension"),
    parent_id: Optional[str] = Query(None, description="父标签 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建标签

    同维度下标签名称不可重复。维度说明：
    - industry: 行业维度（电力、煤炭、石油等）
    - security: 安全维度（核心、重要、敏感、公开）
    - business: 业务维度（发电、用电、调度等）
    - format: 格式维度（结构化、时序等）
    - source: 来源维度（IoT采集、人工录入等）
    - topic: 主题维度（实时监控、统计分析等）
    - business_dimension: 业务维度-三维（行业/场景/用途）
    - technical_dimension: 技术维度-三维（格式/协议/频率）
    - quality_dimension: 质量维度-三维（完整性/准确性/时效性）
    """
    result = await tag_service.create_tag(
        db=db,
        name=name,
        dimension=dimension,
        parent_id=parent_id,
    )
    return ApiResponse(data=result)


@router.get("/dimensions", response_model=ApiResponse)
async def get_tags_by_dimension(
    db: AsyncSession = Depends(get_db),
):
    """
    按维度聚合标签

    返回每个维度下的标签列表，包括维度描述和预设标签
    """
    result = await tag_service.get_tags_by_dimension(db=db)
    return ApiResponse(data=result)


@router.get("/three-dimensional", response_model=ApiResponse)
async def get_three_dimensional_tags(
    db: AsyncSession = Depends(get_db),
):
    """
    获取三维标签体系结构

    返回业务维度/技术维度/质量维度的层级结构，包含预设标签和已创建标签。
    - 业务维度：行业/场景/用途
    - 技术维度：格式/协议/频率
    - 质量维度：完整性/准确性/时效性
    """
    result = await tag_service.get_three_dimensional_tags(db=db)
    return ApiResponse(data=result)


@router.get("/search", response_model=ApiResponse)
async def search_tags(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    dimensions: Optional[str] = Query(None, description="维度筛选（逗号分隔）"),
    asset_id: Optional[str] = Query(None, description="资产ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索/筛选标签

    支持按关键词、维度、资产ID进行筛选
    """
    dim_list = None
    if dimensions:
        dim_list = [d.strip() for d in dimensions.split(",") if d.strip()]

    result = await tag_service.search_tags(
        db=db,
        keyword=keyword,
        dimensions=dim_list,
        asset_id=asset_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=result)


@router.get("/statistics", response_model=ApiResponse)
async def get_tag_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    获取标签统计信息

    返回各维度标签数量、热门标签、标签使用趋势等
    """
    result = await tag_service.get_tag_statistics(db=db)
    return ApiResponse(data=result)


@router.get("/assets", response_model=ApiResponse)
async def get_assets_by_tags(
    tag_ids: str = Query(..., description="标签ID列表（逗号分隔）"),
    match_mode: str = Query("any", description="匹配模式: any(匹配任意)/all(匹配全部)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
):
    """
    按标签筛选资产

    支持两种匹配模式：
    - any: 匹配任意一个标签
    - all: 匹配所有标签
    """
    tag_id_list = [tid.strip() for tid in tag_ids.split(",") if tid.strip()]
    result = await tag_service.get_assets_by_tags(
        db=db,
        tag_ids=tag_id_list,
        match_mode=match_mode,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=result)


@router.post("/batch-assign", response_model=ApiResponse)
async def batch_assign_tags(
    request: BatchAssignTagsRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    批量为资产分配标签

    一次性为资产分配多个标签，已关联的标签会跳过
    """
    result = await tag_service.batch_assign_tags(
        db=db,
        asset_id=request.asset_id,
        tag_ids=request.tag_ids,
    )
    return ApiResponse(data=result)


@router.post("/{tag_id}/assign/{asset_id}", response_model=ApiResponse)
async def assign_tag_to_asset(
    tag_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """为资产分配标签"""
    result = await tag_service.assign_tag_to_asset(
        db=db,
        asset_id=asset_id,
        tag_id=tag_id,
    )
    return ApiResponse(data=result)


@router.delete("/{tag_id}/remove/{asset_id}", response_model=ApiResponse)
async def remove_tag_from_asset(
    tag_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """从资产移除标签"""
    await tag_service.remove_tag_from_asset(
        db=db,
        asset_id=asset_id,
        tag_id=tag_id,
    )
    return ApiResponse(message="标签已移除")


@router.delete("/{tag_id}", response_model=ApiResponse)
async def delete_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除标签（同时解除所有资产关联）"""
    await tag_service.delete_tag(
        db=db,
        tag_id=tag_id,
    )
    return ApiResponse(message="标签已删除")
