"""
数据质量 API - /api/v1/data/quality
质量报告列表 / 报告详情 / 触发质量检查 / 质量统计
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.compliance import DataQualityReport
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.data_asset import QualityReportResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import quality_service

router = APIRouter()


# ===== 请求 Schema =====

class QualityCheckRequest(BaseModel):
    """质量检查请求体"""
    asset_id: str = Field(..., description="数据资产 ID")
    asset_name: Optional[str] = Field(None, description="资产名称")
    dimensions: Optional[list[str]] = Field(None, description="检查维度列表")
    sample_size: Optional[int] = Field(None, description="采样数量")


@router.get("", response_model=ApiResponse[PaginatedResponse[QualityReportResponse]])
@router.get("/", response_model=ApiResponse[PaginatedResponse[QualityReportResponse]])
@router.get("/reports", response_model=ApiResponse[PaginatedResponse[QualityReportResponse]])
async def list_quality_reports(
    asset_id: Optional[str] = Query(None, description="按资产 ID 筛选"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="最低质量得分"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    质量报告列表

    支持按资产 ID 和最低得分筛选
    """
    result = await quality_service.list_quality_reports(
        db=db,
        params=pagination,
        asset_id=asset_id,
        min_score=min_score,
    )
    return ApiResponse(data=result)


@router.get("/reports/{report_id}", response_model=ApiResponse[QualityReportResponse])
async def get_quality_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取质量报告详情"""
    result = await quality_service.get_quality_report(
        db=db,
        report_id=report_id,
    )
    return ApiResponse(data=result)


@router.post("/check", response_model=ApiResponse[QualityReportResponse])
async def trigger_quality_check(
    request: QualityCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    触发数据质量检查

    检查维度:
    - completeness: 完整性（空值率、字段覆盖率）
    - timeliness: 时效性（数据延迟、实时性）
    - accuracy: 准确性（数值范围、格式合规）
    - consistency: 一致性（跨表一致、类型一致）

    不指定 dimensions 则检查全部维度。综合得分基于加权平均计算。
    """
    result = await quality_service.trigger_quality_check(
        db=db,
        asset_id=request.asset_id,
        check_dimensions=request.dimensions,
    )
    return ApiResponse(data=result)


@router.get("/statistics", response_model=ApiResponse)
async def get_quality_statistics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    质量统计概览

    返回已检查资产数量、平均质量得分、等级分布、维度平均分、趋势数据等。
    """
    result = await quality_service.get_quality_statistics(db=db)
    return ApiResponse(data=result)


@router.get("/latest/{asset_id}", response_model=ApiResponse)
async def get_latest_quality_report(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取资产的最新质量报告"""
    result = await quality_service.get_latest_report_for_asset(
        db=db,
        asset_id=asset_id,
    )
    if result is None:
        return ApiResponse(code=2001, message="该资产暂无质量报告", data=None)
    return ApiResponse(data=result)
