"""
增强结算 API - /api/v1/blockchain/settlement-enhanced
自动结算 + 收益分配
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services.settlement_service import (
    create_daily_settlement,
    get_settlement_detail,
    list_pending_settlements,
    calculate_revenue_distribution,
)
from app.services.billing_rule_service import calculate_cost

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/daily", response_model=ApiResponse)
async def trigger_daily_settlement(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    触发每日自动结算

    请求体:
    {
        "settlement_date": "2024-01-15"  // 可选，默认昨天
    }
    """
    settlement_date = body.get("settlement_date")
    try:
        result = await create_daily_settlement(
            db=db,
            settlement_date=settlement_date,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Daily settlement failed: {e}")
        return ApiResponse(code=4030, message=f"每日结算失败: {e}", data=None)


@router.post("/revenue-distribution", response_model=ApiResponse)
async def calc_revenue_distribution(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """
    计算收益分配

    请求体:
    {
        "total_amount": 1000.0,
        "usage_details": [
            {
                "provider_id": "org-1",
                "usage_count": 10,
                "algorithm_did": "did:example:algo1",
                "governance_did": "did:example:gov1"
            }
        ]
    }
    """
    from decimal import Decimal

    total_amount = body.get("total_amount", 0)
    usage_details = body.get("usage_details", [])

    if total_amount <= 0:
        return ApiResponse(code=2003, message="total_amount 必须大于 0", data=None)

    try:
        result = calculate_revenue_distribution(
            total_amount=Decimal(str(total_amount)),
            usage_details=usage_details,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Revenue distribution calculation failed: {e}")
        return ApiResponse(code=4020, message=f"收益分配计算失败: {e}", data=None)


@router.get("/pending", response_model=ApiResponse)
async def get_pending(
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取待结算的使用记录"""
    try:
        records = await list_pending_settlements(db=db, limit=limit)
        return ApiResponse(data={
            "records": records,
            "total": len(records),
        })
    except Exception as e:
        logger.error(f"Pending settlements query failed: {e}")
        return ApiResponse(code=4030, message=f"查询失败: {e}", data=None)


@router.get("/{settlement_id}", response_model=ApiResponse)
async def get_detail(
    settlement_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取结算详情"""
    try:
        result = await get_settlement_detail(db=db, settlement_id=settlement_id)
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Settlement detail query failed: {e}")
        return ApiResponse(code=4030, message=f"查询失败: {e}", data=None)
