"""
收益分配 API - /api/v1/ops/revenue
收益计算 + 结算单管理 + 收益汇总
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import revenue_service

router = APIRouter()


@router.get("/calculate", response_model=ApiResponse)
async def calculate_revenue(
    period: str = Query(description="账期 YYYY-MM"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    计算收益分配

    收益计算模型：
    - 数据质量权重: 40%
    - 使用次数权重: 60%
    - 平台服务费: 5%
    - 算法贡献: 10%
    - 数据治理奖励: 5%
    """
    result = await revenue_service.calculate_revenue_distribution(
        db=db,
        period=period,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/summary", response_model=ApiResponse)
async def get_revenue_summary(
    start_period: Optional[str] = Query(None, description="开始账期 YYYY-MM"),
    end_period: Optional[str] = Query(None, description="结束账期 YYYY-MM"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """收益分配汇总"""
    result = await revenue_service.get_revenue_summary(
        db=db,
        start_period=start_period,
        end_period=end_period,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.post("/settlements", response_model=ApiResponse)
async def create_settlement(
    period: str = Query(description="账期 YYYY-MM"),
    organization_id: str = Query(description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建结算单"""
    result = await revenue_service.create_settlement(
        db=db,
        period=period,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/settlements", response_model=ApiResponse)
async def list_settlements(
    period: Optional[str] = Query(None, description="账期 YYYY-MM"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    status: Optional[str] = Query(None, description="状态: pending/confirmed"),
    user: dict = Depends(get_current_user),
):
    """列出结算单"""
    result = await revenue_service.list_settlements(
        period=period,
        organization_id=organization_id,
        status=status,
    )
    return ApiResponse(data=result)


@router.post("/settlements/{settlement_id}/confirm", response_model=ApiResponse)
async def confirm_settlement(
    settlement_id: str,
    user: dict = Depends(get_current_user),
):
    """确认结算单"""
    result = await revenue_service.confirm_settlement(settlement_id)
    if not result:
        return ApiResponse(code=2001, message="结算单未找到")
    return ApiResponse(data=result)
