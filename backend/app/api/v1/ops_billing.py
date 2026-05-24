"""
计费 API - /api/v1/ops/billing
计费记录 + 月度账单 + 计费汇总 + 账单明细下载 + 账单生成 + 账单统计
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.service import BillingRecordResponse
from app.schemas.ops import BillingSummaryResponse
from app.schemas.billing import (
    BillResponse,
    BillGenerateRequest,
    BillGenerateResponse,
    BillStatisticsResponse,
    BillDownloadResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import billing_service

router = APIRouter()


@router.get("/records", response_model=ApiResponse[PaginatedResponse[BillingRecordResponse]])
async def get_billing_records(
    subscription_id: Optional[str] = Query(None, description="订阅 ID"),
    payment_status: Optional[str] = Query(None, description="支付状态: pending/paid/overdue"),
    billing_period: Optional[str] = Query(None, description="账期 YYYY-MM"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """计费记录"""
    result = await billing_service.get_billing_records(
        db=db,
        params=pagination,
        subscription_id=subscription_id,
        payment_status=payment_status,
        billing_period=billing_period,
    )
    return ApiResponse(data=result)


@router.get("/invoice/{period}", response_model=ApiResponse)
async def get_monthly_invoice(
    period: str,
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """月度账单"""
    result = await billing_service.get_monthly_invoice(
        db=db,
        period=period,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/summary", response_model=ApiResponse[BillingSummaryResponse])
async def get_billing_summary(
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """计费汇总"""
    result = await billing_service.get_billing_summary(
        db=db,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/bills", response_model=ApiResponse[PaginatedResponse[BillingRecordResponse]])
async def get_bills(
    billing_period: Optional[str] = Query(None, description="账期 YYYY-MM"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    bill_status: Optional[str] = Query(None, description="账单状态: draft/issued/paid/overdue"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """账单列表"""
    result = await billing_service.get_bills(
        db=db,
        params=pagination,
        billing_period=billing_period,
        organization_id=organization_id,
        status=bill_status,
    )
    return ApiResponse(data=result)


@router.get("/bills/{bill_id}/download", response_model=ApiResponse[BillDownloadResponse])
async def download_bill(
    bill_id: str,
    fmt: str = Query(default="csv", description="下载格式: csv/json"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """下载账单明细"""
    result = await billing_service.download_bill_detail(
        db=db,
        bill_id=bill_id,
        fmt=fmt,
    )
    return ApiResponse(data=result)


@router.get("/statistics", response_model=ApiResponse[BillStatisticsResponse])
async def get_billing_statistics(
    start_period: Optional[str] = Query(None, description="开始账期 YYYY-MM"),
    end_period: Optional[str] = Query(None, description="结束账期 YYYY-MM"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """账单统计"""
    result = await billing_service.get_billing_statistics(
        db=db,
        start_period=start_period,
        end_period=end_period,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.post("/generate", response_model=ApiResponse[BillGenerateResponse])
async def generate_monthly_bill(
    request: BillGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """生成月度账单"""
    result = await billing_service.generate_monthly_bill(
        db=db,
        billing_period=request.billing_period,
        organization_id=request.organization_id,
    )
    return ApiResponse(data=result)


@router.get("/monthly-report", response_model=ApiResponse)
async def get_monthly_billing_report(
    period: str = Query(description="账期 YYYY-MM"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    获取月度账单报告

    包含账单汇总、按服务分类、统计信息。
    """
    result = await billing_service.get_monthly_report(
        db=db,
        period=period,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)
