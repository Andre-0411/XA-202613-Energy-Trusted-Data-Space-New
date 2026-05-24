"""
配额管理服务
配额 CRUD、使用量追踪、超额检查、超额告警、配额重置
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quota import Quota, QuotaUsageLog
from app.models.user import Organization
from app.schemas.quota import (
    QuotaCreate, QuotaUpdate, QuotaResponse, QuotaCheckRequest,
    QuotaCheckResponse, QuotaUsageLogResponse,
)
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, QuotaExceededError

logger = logging.getLogger(__name__)


async def create_quota(
    db: AsyncSession,
    request: QuotaCreate,
) -> QuotaResponse:
    """
    创建配额

    Args:
        db: 数据库会话
        request: 创建请求

    Returns:
        配额响应
    """
    # 验证组织存在
    org_result = await db.execute(
        select(Organization).where(
            Organization.id == uuid.UUID(request.organization_id)
        )
    )
    if not org_result.scalar_one_or_none():
        raise DataNotFoundError(message=f"组织不存在: {request.organization_id}")

    # 检查是否已存在同类型配额
    existing = await db.execute(
        select(Quota).where(
            and_(
                Quota.organization_id == uuid.UUID(request.organization_id),
                Quota.resource_type == request.resource_type,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataValidationError(
            message=f"该组织已存在 {request.resource_type} 类型的配额"
        )

    quota = Quota(
        organization_id=uuid.UUID(request.organization_id),
        resource_type=request.resource_type,
        limit_value=request.limit_value,
        used_value=0.0,
        unit=request.unit,
        period=request.period,
        alert_threshold=request.alert_threshold,
        status="active",
    )
    db.add(quota)
    await db.commit()
    await db.refresh(quota)

    logger.info(f"配额创建: org={request.organization_id}, type={request.resource_type}, limit={request.limit_value}")
    return _quota_to_response(quota)


async def update_quota(
    db: AsyncSession,
    quota_id: str,
    request: QuotaUpdate,
) -> QuotaResponse:
    """
    更新配额

    Args:
        db: 数据库会话
        quota_id: 配额 ID
        request: 更新请求

    Returns:
        配额响应
    """
    result = await db.execute(
        select(Quota).where(Quota.id == uuid.UUID(quota_id))
    )
    quota = result.scalar_one_or_none()
    if not quota:
        raise DataNotFoundError(message=f"配额不存在: {quota_id}")

    if request.limit_value is not None:
        quota.limit_value = request.limit_value
    if request.alert_threshold is not None:
        quota.alert_threshold = request.alert_threshold
    if request.status is not None:
        quota.status = request.status

    await db.commit()
    await db.refresh(quota)
    logger.info(f"配额更新: {quota_id}")
    return _quota_to_response(quota)


async def get_quota(
    db: AsyncSession,
    quota_id: str,
) -> QuotaResponse:
    """获取配额详情"""
    result = await db.execute(
        select(Quota).where(Quota.id == uuid.UUID(quota_id))
    )
    quota = result.scalar_one_or_none()
    if not quota:
        raise DataNotFoundError(message=f"配额不存在: {quota_id}")
    return _quota_to_response(quota)


async def list_quotas(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """
    查询配额列表

    Args:
        db: 数据库会话
        params: 分页参数
        organization_id: 组织 ID
        resource_type: 资源类型
        status: 状态

    Returns:
        分页配额列表
    """
    query = select(Quota)
    if organization_id:
        query = query.where(Quota.organization_id == uuid.UUID(organization_id))
    if resource_type:
        query = query.where(Quota.resource_type == resource_type)
    if status:
        query = query.where(Quota.status == status)

    query = query.order_by(Quota.created_at.desc())
    result = await paginate_query(db, query, params, QuotaResponse)
    return result


async def delete_quota(
    db: AsyncSession,
    quota_id: str,
) -> bool:
    """删除配额"""
    result = await db.execute(
        select(Quota).where(Quota.id == uuid.UUID(quota_id))
    )
    quota = result.scalar_one_or_none()
    if not quota:
        raise DataNotFoundError(message=f"配额不存在: {quota_id}")

    await db.delete(quota)
    await db.commit()
    logger.info(f"配额删除: {quota_id}")
    return True


# ==================== 配额使用检查 ====================

async def check_quota(
    db: AsyncSession,
    request: QuotaCheckRequest,
) -> QuotaCheckResponse:
    """
    检查配额是否足够

    Args:
        db: 数据库会话
        request: 检查请求

    Returns:
        检查结果
    """
    result = await db.execute(
        select(Quota).where(
            and_(
                Quota.organization_id == uuid.UUID(request.organization_id),
                Quota.resource_type == request.resource_type,
            )
        )
    )
    quota = result.scalar_one_or_none()
    if not quota:
        raise DataNotFoundError(
            message=f"未找到组织 {request.organization_id} 的 {request.resource_type} 配额"
        )

    remaining = max(0, quota.limit_value - quota.used_value)
    usage_percent = round(quota.used_value / quota.limit_value * 100, 2) if quota.limit_value > 0 else 100.0
    allowed = remaining >= request.requested_amount

    message = ""
    if not allowed:
        message = f"配额不足: 请求 {request.requested_amount}{quota.unit}，剩余 {remaining}{quota.unit}"
    elif usage_percent >= quota.alert_threshold:
        message = f"配额使用已达 {usage_percent}%，超过告警阈值 {quota.alert_threshold}%"

    return QuotaCheckResponse(
        allowed=allowed,
        organization_id=request.organization_id,
        resource_type=request.resource_type,
        limit_value=quota.limit_value,
        used_value=quota.used_value,
        remaining=remaining,
        usage_percent=usage_percent,
        message=message,
    )


async def consume_quota(
    db: AsyncSession,
    organization_id: str,
    resource_type: str,
    amount: float,
    reason: str = "",
    operator_id: Optional[str] = None,
) -> QuotaUsageLogResponse:
    """
    消耗配额

    Args:
        db: 数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型
        amount: 消耗量
        reason: 原因
        operator_id: 操作人 ID

    Returns:
        使用记录
    """
    result = await db.execute(
        select(Quota).where(
            and_(
                Quota.organization_id == uuid.UUID(organization_id),
                Quota.resource_type == resource_type,
            )
        )
    )
    quota = result.scalar_one_or_none()
    if not quota:
        raise DataNotFoundError(
            message=f"未找到组织 {organization_id} 的 {resource_type} 配额"
        )

    if quota.status != "active":
        raise DataValidationError(message=f"配额状态为 {quota.status}，无法消耗")

    before_value = quota.used_value
    after_value = before_value + amount

    if after_value > quota.limit_value:
        # 标记为超限
        quota.status = "exceeded"
        logger.warning(
            f"配额超限: org={organization_id}, type={resource_type}, "
            f"used={after_value}, limit={quota.limit_value}"
        )

    quota.used_value = after_value

    log_entry = QuotaUsageLog(
        quota_id=quota.id,
        delta=amount,
        before_value=before_value,
        after_value=after_value,
        reason=reason,
        operator_id=uuid.UUID(operator_id) if operator_id else None,
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    logger.info(
        f"配额消耗: org={organization_id}, type={resource_type}, "
        f"amount={amount}, before={before_value}, after={after_value}"
    )
    return QuotaUsageLogResponse.model_validate(log_entry)


async def release_quota(
    db: AsyncSession,
    organization_id: str,
    resource_type: str,
    amount: float,
    reason: str = "",
) -> QuotaUsageLogResponse:
    """
    释放配额

    Args:
        db: 数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型
        amount: 释放量
        reason: 原因

    Returns:
        使用记录
    """
    result = await db.execute(
        select(Quota).where(
            and_(
                Quota.organization_id == uuid.UUID(organization_id),
                Quota.resource_type == resource_type,
            )
        )
    )
    quota = result.scalar_one_or_none()
    if not quota:
        raise DataNotFoundError(
            message=f"未找到组织 {organization_id} 的 {resource_type} 配额"
        )

    before_value = quota.used_value
    after_value = max(0, before_value - amount)
    delta = after_value - before_value  # 负数

    quota.used_value = after_value

    # 恢复状态
    if quota.status == "exceeded" and after_value < quota.limit_value:
        quota.status = "active"

    log_entry = QuotaUsageLog(
        quota_id=quota.id,
        delta=delta,
        before_value=before_value,
        after_value=after_value,
        reason=reason,
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    logger.info(f"配额释放: org={organization_id}, type={resource_type}, amount={amount}")
    return QuotaUsageLogResponse.model_validate(log_entry)


async def get_quota_usage_logs(
    db: AsyncSession,
    quota_id: str,
    limit: int = 50,
) -> List[QuotaUsageLogResponse]:
    """获取配额使用记录"""
    result = await db.execute(
        select(QuotaUsageLog)
        .where(QuotaUsageLog.quota_id == uuid.UUID(quota_id))
        .order_by(QuotaUsageLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [QuotaUsageLogResponse.model_validate(log) for log in logs]


# ==================== 配额告警 ====================

async def check_quota_alerts(
    db: AsyncSession,
) -> List[dict]:
    """
    检查所有配额告警（超过阈值的配额）

    Returns:
        告警列表
    """
    result = await db.execute(
        select(Quota).where(Quota.status == "active")
    )
    quotas = result.scalars().all()

    alerts = []
    for quota in quotas:
        if quota.limit_value <= 0:
            continue
        usage_percent = round(quota.used_value / quota.limit_value * 100, 2)
        if usage_percent >= quota.alert_threshold:
            severity = "critical" if usage_percent >= 95 else "warning"
            alerts.append({
                "quota_id": str(quota.id),
                "organization_id": str(quota.organization_id),
                "resource_type": quota.resource_type,
                "used_value": quota.used_value,
                "limit_value": quota.limit_value,
                "usage_percent": usage_percent,
                "threshold": quota.alert_threshold,
                "severity": severity,
                "message": f"{quota.resource_type} 配额使用 {usage_percent}%，超过阈值 {quota.alert_threshold}%",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            })

    return alerts


async def reset_periodic_quotas(
    db: AsyncSession,
    period: str = "monthly",
) -> int:
    """
    重置周期配额（每月初调用）

    Args:
        db: 数据库会话
        period: 配额周期

    Returns:
        重置数量
    """
    result = await db.execute(
        select(Quota).where(
            and_(
                Quota.period == period,
                Quota.used_value > 0,
            )
        )
    )
    quotas = result.scalars().all()

    reset_count = 0
    for quota in quotas:
        before = quota.used_value
        quota.used_value = 0.0
        if quota.status == "exceeded":
            quota.status = "active"

        log_entry = QuotaUsageLog(
            quota_id=quota.id,
            delta=-before,
            before_value=before,
            after_value=0.0,
            reason=f"周期重置 ({period})",
        )
        db.add(log_entry)
        reset_count += 1

    await db.commit()
    logger.info(f"配额周期重置: period={period}, count={reset_count}")
    return reset_count


# ==================== 辅助函数 ====================

def _quota_to_response(quota: Quota) -> QuotaResponse:
    """将 Quota 模型转换为响应"""
    usage_percent = round(quota.used_value / quota.limit_value * 100, 2) if quota.limit_value > 0 else 0.0
    return QuotaResponse(
        id=str(quota.id),
        organization_id=str(quota.organization_id),
        resource_type=quota.resource_type,
        limit_value=quota.limit_value,
        used_value=quota.used_value,
        unit=quota.unit,
        period=quota.period,
        alert_threshold=quota.alert_threshold,
        status=quota.status,
        usage_percent=usage_percent,
        created_at=quota.created_at,
        updated_at=quota.updated_at,
    )
