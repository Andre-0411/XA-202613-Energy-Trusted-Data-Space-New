"""
计算资源配额管理 API
提供配额查询、更新、检查、消耗、释放、使用记录、申请审批等接口
"""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.schemas.compute_quota import (
    ComputeQuotaResponse,
    ComputeQuotaUpdate,
    ComputeQuotaCheckRequest,
    ComputeQuotaCheckResponse,
    ComputeQuotaConsumeRequest,
    ComputeQuotaReleaseRequest,
    ComputeQuotaRequestCreate,
    ComputeQuotaRequestReview,
    ComputeQuotaRequestResponse,
    ComputeQuotaUsageResponse,
    ComputeQuotaStatsResponse,
)
from app.services import compute_quota_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 配额初始化 ====================


@router.post(
    "/init/org/{organization_id}",
    response_model=ApiResponse[list[ComputeQuotaResponse]],
    summary="初始化组织计算配额",
)
async def init_organization_quotas(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    priority: int = Query(default=5, ge=1, le=10, description="配额优先级"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """为指定组织初始化默认计算配额（CPU/内存/存储/任务数/GPU）"""
    quotas = await compute_quota_service.init_organization_quotas(
        db, organization_id, priority
    )
    return ApiResponse(
        data=[ComputeQuotaResponse.model_validate(q) for q in quotas],
        message=f"已初始化 {len(quotas)} 项配额",
    )


@router.post(
    "/init/user/{organization_id}/{user_id}",
    response_model=ApiResponse[list[ComputeQuotaResponse]],
    summary="初始化用户计算配额",
)
async def init_user_quotas(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    user_id: str = None,
    priority: int = Query(default=5, ge=1, le=10, description="配额优先级"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """为指定用户初始化默认计算配额"""
    quotas = await compute_quota_service.init_user_quotas(
        db, organization_id, user_id, priority
    )
    return ApiResponse(
        data=[ComputeQuotaResponse.model_validate(q) for q in quotas],
        message=f"已初始化 {len(quotas)} 项用户配额",
    )


# ==================== 配额查询 ====================


@router.get(
    "/{organization_id}",
    response_model=ApiResponse[list[ComputeQuotaResponse]],
    summary="查询组织计算配额",
)
async def list_quotas(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    user_id: Optional[str] = Query(default=None, description="用户 ID（不过滤则查组织级）"),
    resource_type: Optional[str] = Query(default=None, description="资源类型过滤"),
    status: Optional[str] = Query(default=None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """查询组织/用户的计算配额列表"""
    quotas = await compute_quota_service.list_quotas(
        db, organization_id, user_id, resource_type, status
    )
    return ApiResponse(
        data=[ComputeQuotaResponse.model_validate(q) for q in quotas],
    )


@router.get(
    "/{organization_id}/detail",
    response_model=ApiResponse[ComputeQuotaResponse],
    summary="查询单个计算配额",
)
async def get_quota(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    resource_type: str = Query(description="资源类型"),
    user_id: Optional[str] = Query(default=None, description="用户 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """查询指定资源类型的计算配额详情"""
    quota = await compute_quota_service.get_quota(
        db, organization_id, resource_type, user_id
    )
    return ApiResponse(data=ComputeQuotaResponse.model_validate(quota))


@router.get(
    "/{organization_id}/stats",
    response_model=ApiResponse[ComputeQuotaStatsResponse],
    summary="计算配额统计",
)
async def get_quota_stats(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    user_id: Optional[str] = Query(default=None, description="用户 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取组织/用户的计算配额统计信息，包括使用率和告警"""
    stats = await compute_quota_service.get_quota_stats(
        db, organization_id, user_id
    )
    return ApiResponse(data=ComputeQuotaStatsResponse(**stats))


# ==================== 配额更新 ====================


@router.put(
    "/{organization_id}",
    response_model=ApiResponse[ComputeQuotaResponse],
    summary="更新计算配额",
)
async def update_quota(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    body: ComputeQuotaUpdate = None,
    resource_type: str = Query(description="资源类型"),
    user_id: Optional[str] = Query(default=None, description="用户 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """更新指定资源类型的计算配额（上限/告警阈值/优先级/状态）"""
    quota = await compute_quota_service.update_quota(
        db, organization_id, resource_type, user_id,
        limit_value=body.limit_value,
        alert_threshold=body.alert_threshold,
        priority=body.priority,
        status=body.status,
        metadata_=body.metadata_,
    )
    return ApiResponse(data=ComputeQuotaResponse.model_validate(quota))


# ==================== 配额检查/消耗/释放 ====================


@router.post(
    "/check",
    response_model=ApiResponse[ComputeQuotaCheckResponse],
    summary="检查配额是否可用",
)
async def check_quota(
    user: dict = Depends(get_current_user),
    body: ComputeQuotaCheckRequest = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """检查指定资源类型的配额是否足够"""
    result = await compute_quota_service.check_quota_available(
        db, body.organization_id, body.resource_type,
        body.required_amount, body.user_id,
    )
    return ApiResponse(data=ComputeQuotaCheckResponse(**result))


@router.post(
    "/consume",
    response_model=ApiResponse[ComputeQuotaUsageResponse],
    summary="消耗配额",
)
async def consume_quota(
    user: dict = Depends(get_current_user),
    body: ComputeQuotaConsumeRequest = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """消耗指定资源类型的计算配额"""
    usage = await compute_quota_service.consume_quota(
        db, body.organization_id, body.resource_type, body.amount,
        user_id=body.user_id, task_id=body.task_id, reason=body.reason,
    )
    return ApiResponse(
        data=ComputeQuotaUsageResponse.model_validate(usage),
        message="配额消耗成功",
    )


@router.post(
    "/release",
    response_model=ApiResponse[ComputeQuotaUsageResponse],
    summary="释放配额",
)
async def release_quota(
    user: dict = Depends(get_current_user),
    body: ComputeQuotaReleaseRequest = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """释放指定资源类型的计算配额（任务完成/取消后归还）"""
    usage = await compute_quota_service.release_quota(
        db, body.organization_id, body.resource_type, body.amount,
        user_id=body.user_id, task_id=body.task_id, reason=body.reason,
    )
    return ApiResponse(
        data=ComputeQuotaUsageResponse.model_validate(usage),
        message="配额释放成功",
    )


# ==================== 使用记录 ====================


@router.get(
    "/{organization_id}/usage",
    response_model=ApiResponse[list[ComputeQuotaUsageResponse]],
    summary="查询配额使用记录",
)
async def get_usage_logs(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    resource_type: Optional[str] = Query(default=None, description="资源类型过滤"),
    user_id: Optional[str] = Query(default=None, description="用户 ID 过滤"),
    task_id: Optional[str] = Query(default=None, description="任务 ID 过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """查询计算配额的使用/变更记录"""
    logs = await compute_quota_service.get_quota_usage_logs(
        db, organization_id, resource_type, user_id, task_id, limit, offset,
    )
    return ApiResponse(
        data=[ComputeQuotaUsageResponse.model_validate(log) for log in logs],
    )


# ==================== 配额申请审批 ====================


@router.post(
    "/request",
    response_model=ApiResponse[ComputeQuotaRequestResponse],
    summary="申请提升配额",
)
async def create_quota_request(
    user: dict = Depends(get_current_user),
    body: ComputeQuotaRequestCreate = None,
    user_id: str = Query(description="申请人 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """提交计算配额提升申请"""
    request_obj = await compute_quota_service.request_quota_increase(
        db, body.organization_id, user_id, body.quota_id,
        body.requested_limit, body.reason,
    )
    return ApiResponse(
        data=ComputeQuotaRequestResponse.model_validate(request_obj),
        message="配额提升申请已提交",
    )


@router.put(
    "/request/{request_id}/review",
    response_model=ApiResponse[ComputeQuotaRequestResponse],
    summary="审批配额申请",
)
async def review_quota_request(
    user: dict = Depends(get_current_user),
    request_id: str = None,
    body: ComputeQuotaRequestReview = None,
    reviewer_id: str = Query(description="审批人 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """审批配额提升申请（批准/拒绝）"""
    request_obj = await compute_quota_service.review_quota_request(
        db, request_id, reviewer_id, body.status, body.review_comment,
    )
    return ApiResponse(
        data=ComputeQuotaRequestResponse.model_validate(request_obj),
        message=f"配额申请已{('批准' if body.status == 'approved' else '拒绝')}",
    )


@router.get(
    "/{organization_id}/requests",
    response_model=ApiResponse[list[ComputeQuotaRequestResponse]],
    summary="查询配额申请列表",
)
async def list_quota_requests(
    user: dict = Depends(get_current_user),
    organization_id: str = None,
    status: Optional[str] = Query(default=None, description="状态过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """查询组织的配额提升申请列表"""
    requests = await compute_quota_service.list_quota_requests(
        db, organization_id, status, limit, offset,
    )
    return ApiResponse(
        data=[ComputeQuotaRequestResponse.model_validate(r) for r in requests],
    )


# ==================== 周期重置 ====================


@router.post(
    "/reset/{period}",
    response_model=ApiResponse[dict],
    summary="重置周期配额",
)
async def reset_periodic_quotas(
    user: dict = Depends(get_current_user),
    period: str = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """重置指定周期类型的所有计算配额已用量（daily/weekly/monthly/yearly）"""
    valid_periods = {"daily", "weekly", "monthly", "yearly"}
    if period not in valid_periods:
        return ApiResponse(code=400, message=f"无效的周期类型: {period}，允许值: {valid_periods}")

    count = await compute_quota_service.reset_periodic_quotas(db, period)
    return ApiResponse(
        data={"reset_count": count, "period": period},
        message=f"已重置 {count} 项 {period} 配额",
    )
