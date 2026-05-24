"""
配额管理 API - /api/v1/ops/quota
配额 CRUD + 使用检查 + 使用/释放 + 告警 + 使用记录
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.quota import (
    QuotaCreate, QuotaUpdate, QuotaResponse, QuotaCheckRequest,
    QuotaCheckResponse, QuotaUsageLogResponse, MonthlyReportRequest,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import quota_service

router = APIRouter()


@router.post("", response_model=ApiResponse[QuotaResponse], status_code=201)
async def create_quota(
    request: QuotaCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建配额"""
    result = await quota_service.create_quota(db=db, request=request)
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[QuotaResponse]])
async def list_quotas(
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    status: Optional[str] = Query(None, description="状态"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查询配额列表"""
    result = await quota_service.list_quotas(
        db=db,
        params=pagination,
        organization_id=organization_id,
        resource_type=resource_type,
        status=status,
    )
    return ApiResponse(data=result)


@router.get("/{quota_id}", response_model=ApiResponse[QuotaResponse])
async def get_quota(
    quota_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取配额详情"""
    result = await quota_service.get_quota(db=db, quota_id=quota_id)
    return ApiResponse(data=result)


@router.put("/{quota_id}", response_model=ApiResponse[QuotaResponse])
async def update_quota(
    quota_id: str,
    request: QuotaUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新配额"""
    result = await quota_service.update_quota(
        db=db, quota_id=quota_id, request=request,
    )
    return ApiResponse(data=result)


@router.delete("/{quota_id}", response_model=ApiResponse)
async def delete_quota(
    quota_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除配额"""
    await quota_service.delete_quota(db=db, quota_id=quota_id)
    return ApiResponse(message="配额已删除")


@router.post("/check", response_model=ApiResponse[QuotaCheckResponse])
async def check_quota(
    request: QuotaCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """检查配额是否足够"""
    result = await quota_service.check_quota(db=db, request=request)
    return ApiResponse(data=result)


@router.post("/consume", response_model=ApiResponse[QuotaUsageLogResponse])
async def consume_quota(
    organization_id: str = Query(description="组织 ID"),
    resource_type: str = Query(description="资源类型"),
    amount: float = Query(gt=0, description="消耗量"),
    reason: str = Query(default="", description="原因"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """消耗配额"""
    result = await quota_service.consume_quota(
        db=db,
        organization_id=organization_id,
        resource_type=resource_type,
        amount=amount,
        reason=reason,
        operator_id=user.get("user_id"),
    )
    return ApiResponse(data=result)


@router.post("/release", response_model=ApiResponse[QuotaUsageLogResponse])
async def release_quota(
    organization_id: str = Query(description="组织 ID"),
    resource_type: str = Query(description="资源类型"),
    amount: float = Query(gt=0, description="释放量"),
    reason: str = Query(default="", description="原因"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """释放配额"""
    result = await quota_service.release_quota(
        db=db,
        organization_id=organization_id,
        resource_type=resource_type,
        amount=amount,
        reason=reason,
    )
    return ApiResponse(data=result)


@router.get("/{quota_id}/usage-logs", response_model=ApiResponse)
async def get_quota_usage_logs(
    quota_id: str,
    limit: int = Query(default=50, le=200, description="限制数量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取配额使用记录"""
    result = await quota_service.get_quota_usage_logs(
        db=db, quota_id=quota_id, limit=limit,
    )
    return ApiResponse(data=[r.model_dump() for r in result])


@router.get("/alerts/check", response_model=ApiResponse)
async def check_quota_alerts(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """检查配额告警"""
    alerts = await quota_service.check_quota_alerts(db=db)
    return ApiResponse(data={"alerts": alerts, "total": len(alerts)})


@router.post("/reset", response_model=ApiResponse)
async def reset_periodic_quotas(
    period: str = Query(default="monthly", description="配额周期"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """重置周期配额"""
    count = await quota_service.reset_periodic_quotas(db=db, period=period)
    return ApiResponse(data={"reset_count": count})
