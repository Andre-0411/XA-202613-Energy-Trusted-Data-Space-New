"""
计算资源配额管理服务
基于 ComputeQuota / ComputeQuotaUsage / ComputeQuotaRequest 模型
提供组织级/用户级配额初始化、消耗、释放、检查、申请审批等功能
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quota_model import ComputeQuota, ComputeQuotaUsage, ComputeQuotaRequest
from app.exceptions import (
    DataNotFoundError, DataValidationError, QuotaExceededError, PermissionDeniedError,
)

logger = logging.getLogger(__name__)

# ==================== 默认配额模板 ====================

# 组织级默认配额
DEFAULT_ORG_QUOTAS: dict[str, dict] = {
    "cpu_hours": {
        "limit_value": 1000.0,
        "unit": "core·h",
        "period": "monthly",
        "alert_threshold": 80.0,
    },
    "memory_gb_hours": {
        "limit_value": 2000.0,
        "unit": "GB·h",
        "period": "monthly",
        "alert_threshold": 80.0,
    },
    "storage_gb": {
        "limit_value": 500.0,
        "unit": "GB",
        "period": "permanent",
        "alert_threshold": 90.0,
    },
    "compute_tasks": {
        "limit_value": 500.0,
        "unit": "task",
        "period": "monthly",
        "alert_threshold": 80.0,
    },
    "gpu_hours": {
        "limit_value": 100.0,
        "unit": "GPU·h",
        "period": "monthly",
        "alert_threshold": 70.0,
    },
}

# 用户级默认配额
DEFAULT_USER_QUOTAS: dict[str, dict] = {
    "cpu_hours": {
        "limit_value": 100.0,
        "unit": "core·h",
        "period": "monthly",
        "alert_threshold": 80.0,
    },
    "memory_gb_hours": {
        "limit_value": 200.0,
        "unit": "GB·h",
        "period": "monthly",
        "alert_threshold": 80.0,
    },
    "storage_gb": {
        "limit_value": 50.0,
        "unit": "GB",
        "period": "permanent",
        "alert_threshold": 90.0,
    },
    "compute_tasks": {
        "limit_value": 50.0,
        "unit": "task",
        "period": "monthly",
        "alert_threshold": 80.0,
    },
    "gpu_hours": {
        "limit_value": 10.0,
        "unit": "GPU·h",
        "period": "monthly",
        "alert_threshold": 70.0,
    },
}


# ==================== 配额初始化 ====================


async def init_organization_quotas(
    db: AsyncSession,
    organization_id: str,
    priority: int = 5,
) -> list[ComputeQuota]:
    """
    为组织初始化默认计算配额

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        priority: 配额优先级 (1=最高, 10=最低)

    Returns:
        创建的配额列表
    """
    org_uuid = uuid.UUID(organization_id)

    # 检查是否已有配额
    existing = await db.execute(
        select(ComputeQuota).where(
            and_(
                ComputeQuota.organization_id == org_uuid,
                ComputeQuota.user_id.is_(None),
            )
        )
    )
    if existing.scalars().first():
        logger.warning(f"Organization {organization_id} already has compute quotas")
        return list(existing.scalars().all())

    quotas: list[ComputeQuota] = []
    for resource_type, defaults in DEFAULT_ORG_QUOTAS.items():
        quota = ComputeQuota(
            organization_id=org_uuid,
            user_id=None,
            resource_type=resource_type,
            limit_value=defaults["limit_value"],
            used_value=0.0,
            unit=defaults["unit"],
            period=defaults["period"],
            alert_threshold=defaults["alert_threshold"],
            status="active",
            priority=priority,
        )
        db.add(quota)
        quotas.append(quota)

    await db.commit()
    for q in quotas:
        await db.refresh(q)

    logger.info(
        f"Initialized {len(quotas)} compute quotas for organization {organization_id}"
    )
    return quotas


async def init_user_quotas(
    db: AsyncSession,
    organization_id: str,
    user_id: str,
    priority: int = 5,
) -> list[ComputeQuota]:
    """
    为用户初始化默认计算配额

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        user_id: 用户 ID
        priority: 配额优先级

    Returns:
        创建的配额列表
    """
    org_uuid = uuid.UUID(organization_id)
    user_uuid = uuid.UUID(user_id)

    # 检查是否已有配额
    existing = await db.execute(
        select(ComputeQuota).where(
            and_(
                ComputeQuota.organization_id == org_uuid,
                ComputeQuota.user_id == user_uuid,
            )
        )
    )
    if existing.scalars().first():
        logger.warning(f"User {user_id} already has compute quotas")
        return list(existing.scalars().all())

    quotas: list[ComputeQuota] = []
    for resource_type, defaults in DEFAULT_USER_QUOTAS.items():
        quota = ComputeQuota(
            organization_id=org_uuid,
            user_id=user_uuid,
            resource_type=resource_type,
            limit_value=defaults["limit_value"],
            used_value=0.0,
            unit=defaults["unit"],
            period=defaults["period"],
            alert_threshold=defaults["alert_threshold"],
            status="active",
            priority=priority,
        )
        db.add(quota)
        quotas.append(quota)

    await db.commit()
    for q in quotas:
        await db.refresh(q)

    logger.info(f"Initialized {len(quotas)} compute quotas for user {user_id}")
    return quotas


# ==================== 配额查询 ====================


async def get_quota(
    db: AsyncSession,
    organization_id: str,
    resource_type: str,
    user_id: Optional[str] = None,
) -> ComputeQuota:
    """
    获取指定配额

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型
        user_id: 用户 ID（None 表示组织级）

    Returns:
        ComputeQuota 实例

    Raises:
        DataNotFoundError: 配额不存在
    """
    conditions = [
        ComputeQuota.organization_id == uuid.UUID(organization_id),
        ComputeQuota.resource_type == resource_type,
    ]
    if user_id:
        conditions.append(ComputeQuota.user_id == uuid.UUID(user_id))
    else:
        conditions.append(ComputeQuota.user_id.is_(None))

    result = await db.execute(
        select(ComputeQuota).where(and_(*conditions))
    )
    quota = result.scalar_one_or_none()
    if not quota:
        scope = f"user={user_id}" if user_id else "org"
        raise DataNotFoundError(
            f"计算配额不存在: org={organization_id}, type={resource_type}, scope={scope}"
        )
    return quota


async def list_quotas(
    db: AsyncSession,
    organization_id: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
) -> list[ComputeQuota]:
    """
    列出配额

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        user_id: 用户 ID（过滤条件，None 不过滤）
        resource_type: 资源类型（过滤条件）
        status: 配额状态（过滤条件）

    Returns:
        配额列表
    """
    conditions = [ComputeQuota.organization_id == uuid.UUID(organization_id)]
    if user_id is not None:
        conditions.append(ComputeQuota.user_id == uuid.UUID(user_id))
    if resource_type:
        conditions.append(ComputeQuota.resource_type == resource_type)
    if status:
        conditions.append(ComputeQuota.status == status)

    result = await db.execute(
        select(ComputeQuota).where(and_(*conditions)).order_by(
            ComputeQuota.resource_type
        )
    )
    return list(result.scalars().all())


async def get_quota_stats(
    db: AsyncSession,
    organization_id: str,
    user_id: Optional[str] = None,
) -> dict:
    """
    获取配额统计信息

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        user_id: 用户 ID

    Returns:
        配额统计信息字典
    """
    quotas = await list_quotas(db, organization_id, user_id)

    alerts: list[str] = []
    total_limit = 0.0
    total_used = 0.0

    for q in quotas:
        total_limit += q.limit_value
        total_used += q.used_value
        if q.limit_value > 0:
            usage_pct = (q.used_value / q.limit_value) * 100
            if usage_pct >= q.alert_threshold:
                alerts.append(
                    f"{q.resource_type}: 使用率 {usage_pct:.1f}% 超过告警阈值 {q.alert_threshold}%"
                )
            if usage_pct >= 100:
                alerts.append(f"{q.resource_type}: 配额已用尽")

    overall_pct = (total_used / total_limit * 100) if total_limit > 0 else 0.0

    return {
        "organization_id": organization_id,
        "user_id": user_id,
        "quotas": [q.__dict__ for q in quotas],
        "total_usage_percent": round(overall_pct, 2),
        "alerts": alerts,
    }


# ==================== 配额更新 ====================


async def update_quota(
    db: AsyncSession,
    organization_id: str,
    resource_type: str,
    user_id: Optional[str] = None,
    limit_value: Optional[float] = None,
    alert_threshold: Optional[float] = None,
    priority: Optional[int] = None,
    status: Optional[str] = None,
    metadata_: Optional[dict] = None,
) -> ComputeQuota:
    """
    更新计算配额

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型
        user_id: 用户 ID
        limit_value: 新的配额上限
        alert_threshold: 新的告警阈值
        priority: 新的优先级
        status: 新的状态
        metadata_: 扩展配置

    Returns:
        更新后的配额
    """
    quota = await get_quota(db, organization_id, resource_type, user_id)

    if limit_value is not None:
        if limit_value < 0:
            raise DataValidationError("配额上限不能为负数")
        # 如果新的限额低于已用量，需要特殊处理
        if limit_value < quota.used_value:
            logger.warning(
                f"New limit {limit_value} < used {quota.used_value} "
                f"for {resource_type}; existing usages remain valid"
            )
        quota.limit_value = limit_value

    if alert_threshold is not None:
        if not (0 <= alert_threshold <= 100):
            raise DataValidationError("告警阈值需在 0-100 之间")
        quota.alert_threshold = alert_threshold

    if priority is not None:
        if not (1 <= priority <= 10):
            raise DataValidationError("优先级需在 1-10 之间")
        quota.priority = priority

    if status is not None:
        valid_statuses = {"active", "suspended", "exceeded", "revoked"}
        if status not in valid_statuses:
            raise DataValidationError(f"无效的状态: {status}，允许值: {valid_statuses}")
        quota.status = status

    if metadata_ is not None:
        quota.metadata_ = metadata_

    await db.commit()
    await db.refresh(quota)

    logger.info(f"Updated compute quota: org={organization_id}, type={resource_type}")
    return quota


# ==================== 配额消耗/释放 ====================


async def check_quota_available(
    db: AsyncSession,
    organization_id: str,
    resource_type: str,
    required_amount: float,
    user_id: Optional[str] = None,
) -> dict:
    """
    检查配额是否可用

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型
        required_amount: 需要的资源量
        user_id: 用户 ID

    Returns:
        检查结果字典，包含 allowed, limit_value, used_value, available, usage_percent 等
    """
    quota = await get_quota(db, organization_id, resource_type, user_id)

    if quota.status != "active":
        return {
            "allowed": False,
            "resource_type": resource_type,
            "limit_value": quota.limit_value,
            "used_value": quota.used_value,
            "available": 0.0,
            "usage_percent": 100.0,
            "is_over_threshold": True,
            "reason": f"配额状态异常: {quota.status}",
        }

    available = max(0.0, quota.limit_value - quota.used_value)
    usage_percent = (
        (quota.used_value / quota.limit_value * 100) if quota.limit_value > 0 else 100.0
    )
    is_over_threshold = usage_percent >= quota.alert_threshold

    allowed = available >= required_amount

    return {
        "allowed": allowed,
        "resource_type": resource_type,
        "limit_value": quota.limit_value,
        "used_value": quota.used_value,
        "available": round(available, 6),
        "usage_percent": round(usage_percent, 2),
        "is_over_threshold": is_over_threshold,
        "reason": None if allowed else f"配额不足: 需要 {required_amount}，可用 {available:.4f}",
    }


async def consume_quota(
    db: AsyncSession,
    organization_id: str,
    resource_type: str,
    amount: float,
    user_id: Optional[str] = None,
    task_id: Optional[str] = None,
    reason: Optional[str] = None,
    operator_id: Optional[str] = None,
) -> ComputeQuotaUsage:
    """
    消耗计算配额

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型
        amount: 消耗量（正数）
        user_id: 用户 ID
        task_id: 关联任务 ID
        reason: 消耗原因
        operator_id: 操作者 ID

    Returns:
        使用记录

    Raises:
        QuotaExceededError: 配额不足
    """
    if amount <= 0:
        raise DataValidationError("消耗量必须为正数")

    quota = await get_quota(db, organization_id, resource_type, user_id)

    if quota.status != "active":
        raise QuotaExceededError(
            f"配额状态异常({quota.status})，无法消耗: {resource_type}"
        )

    before_value = quota.used_value
    after_value = before_value + amount

    if after_value > quota.limit_value:
        raise QuotaExceededError(
            f"配额不足: {resource_type} 已用 {before_value:.4f}/{quota.limit_value}，"
            f"请求 {amount:.4f}，超出上限"
        )

    quota.used_value = after_value

    # 记录使用日志
    usage_log = ComputeQuotaUsage(
        quota_id=quota.id,
        task_id=uuid.UUID(task_id) if task_id else None,
        delta=amount,
        before_value=before_value,
        after_value=after_value,
        reason=reason or f"消耗 {amount} {quota.unit}",
        operator_id=uuid.UUID(operator_id) if operator_id else None,
    )
    db.add(usage_log)

    # 检查告警阈值
    usage_percent = (after_value / quota.limit_value * 100) if quota.limit_value > 0 else 100.0
    if usage_percent >= quota.alert_threshold:
        logger.warning(
            f"Quota alert: {resource_type} usage at {usage_percent:.1f}% "
            f"(threshold: {quota.alert_threshold}%) for org={organization_id}"
        )

    # 超限状态标记
    if usage_percent >= 100.0:
        quota.status = "exceeded"
        logger.warning(f"Quota exceeded: {resource_type} for org={organization_id}")

    await db.commit()
    await db.refresh(usage_log)

    logger.info(
        f"Consumed {amount} {quota.unit} of {resource_type}: "
        f"org={organization_id}, {before_value:.4f} -> {after_value:.4f}"
    )
    return usage_log


async def release_quota(
    db: AsyncSession,
    organization_id: str,
    resource_type: str,
    amount: float,
    user_id: Optional[str] = None,
    task_id: Optional[str] = None,
    reason: Optional[str] = None,
    operator_id: Optional[str] = None,
) -> ComputeQuotaUsage:
    """
    释放计算配额（任务完成/取消后归还资源）

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型
        amount: 释放量（正数）
        user_id: 用户 ID
        task_id: 关联任务 ID
        reason: 释放原因
        operator_id: 操作者 ID

    Returns:
        使用记录
    """
    if amount <= 0:
        raise DataValidationError("释放量必须为正数")

    quota = await get_quota(db, organization_id, resource_type, user_id)

    before_value = quota.used_value
    after_value = max(0.0, before_value - amount)
    released = before_value - after_value

    quota.used_value = after_value

    # 如果之前是 exceeded 状态，恢复正常
    if quota.status == "exceeded" and after_value < quota.limit_value:
        quota.status = "active"
        logger.info(f"Quota {resource_type} status restored to active for org={organization_id}")

    usage_log = ComputeQuotaUsage(
        quota_id=quota.id,
        task_id=uuid.UUID(task_id) if task_id else None,
        delta=-released,
        before_value=before_value,
        after_value=after_value,
        reason=reason or f"释放 {released} {quota.unit}",
        operator_id=uuid.UUID(operator_id) if operator_id else None,
    )
    db.add(usage_log)
    await db.commit()
    await db.refresh(usage_log)

    logger.info(
        f"Released {released} {quota.unit} of {resource_type}: "
        f"org={organization_id}, {before_value:.4f} -> {after_value:.4f}"
    )
    return usage_log


async def get_quota_usage_logs(
    db: AsyncSession,
    organization_id: str,
    resource_type: Optional[str] = None,
    user_id: Optional[str] = None,
    task_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ComputeQuotaUsage]:
    """
    查询配额使用记录

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        resource_type: 资源类型过滤
        user_id: 用户 ID 过滤
        task_id: 任务 ID 过滤
        limit: 返回数量
        offset: 偏移量

    Returns:
        使用记录列表
    """
    # 先获取组织下所有配额 ID
    quota_conditions = [ComputeQuota.organization_id == uuid.UUID(organization_id)]
    if resource_type:
        quota_conditions.append(ComputeQuota.resource_type == resource_type)
    if user_id:
        quota_conditions.append(ComputeQuota.user_id == uuid.UUID(user_id))

    quota_ids_result = await db.execute(
        select(ComputeQuota.id).where(and_(*quota_conditions))
    )
    quota_ids = [row[0] for row in quota_ids_result.all()]

    if not quota_ids:
        return []

    usage_conditions = [ComputeQuotaUsage.quota_id.in_(quota_ids)]
    if task_id:
        usage_conditions.append(ComputeQuotaUsage.task_id == uuid.UUID(task_id))

    result = await db.execute(
        select(ComputeQuotaUsage)
        .where(and_(*usage_conditions))
        .order_by(ComputeQuotaUsage.recorded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


# ==================== 配额申请审批 ====================


async def request_quota_increase(
    db: AsyncSession,
    organization_id: str,
    requester_id: str,
    quota_id: str,
    requested_limit: float,
    reason: str,
) -> ComputeQuotaRequest:
    """
    申请提升配额

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        requester_id: 申请人 ID
        quota_id: 原配额 ID
        requested_limit: 申请的配额上限
        reason: 申请理由

    Returns:
        申请记录

    Raises:
        DataNotFoundError: 配额不存在
        DataValidationError: 参数校验失败
    """
    if requested_limit <= 0:
        raise DataValidationError("申请配额上限必须为正数")
    if len(reason) < 10:
        raise DataValidationError("申请理由至少 10 个字符")

    # 查询原配额
    quota_result = await db.execute(
        select(ComputeQuota).where(ComputeQuota.id == uuid.UUID(quota_id))
    )
    quota = quota_result.scalar_one_or_none()
    if not quota:
        raise DataNotFoundError(f"配额不存在: {quota_id}")

    if str(quota.organization_id) != organization_id:
        raise PermissionDeniedError("无权申请该组织的配额")

    if requested_limit <= quota.limit_value:
        raise DataValidationError(
            f"申请配额({requested_limit})必须大于当前配额({quota.limit_value})"
        )

    # 检查是否有 pending 的申请
    pending_result = await db.execute(
        select(ComputeQuotaRequest).where(
            and_(
                ComputeQuotaRequest.quota_id == uuid.UUID(quota_id),
                ComputeQuotaRequest.status == "pending",
            )
        )
    )
    if pending_result.scalar_one_or_none():
        raise DataValidationError("该配额已有待审批的提升申请")

    request_obj = ComputeQuotaRequest(
        quota_id=uuid.UUID(quota_id),
        organization_id=uuid.UUID(organization_id),
        requester_id=uuid.UUID(requester_id),
        current_limit=quota.limit_value,
        requested_limit=requested_limit,
        reason=reason,
        status="pending",
    )
    db.add(request_obj)
    await db.commit()
    await db.refresh(request_obj)

    logger.info(
        f"Quota increase requested: org={organization_id}, "
        f"type={quota.resource_type}, {quota.limit_value} -> {requested_limit}"
    )
    return request_obj


async def review_quota_request(
    db: AsyncSession,
    request_id: str,
    reviewer_id: str,
    status: str,
    review_comment: Optional[str] = None,
) -> ComputeQuotaRequest:
    """
    审批配额提升申请

    Args:
        db: 异步数据库会话
        request_id: 申请 ID
        reviewer_id: 审批人 ID
        status: 审批结果 (approved/rejected)
        review_comment: 审批意见

    Returns:
        更新后的申请记录

    Raises:
        DataNotFoundError: 申请不存在
        DataValidationError: 状态校验失败
    """
    if status not in ("approved", "rejected"):
        raise DataValidationError(f"无效的审批结果: {status}，允许值: approved/rejected")

    result = await db.execute(
        select(ComputeQuotaRequest).where(
            ComputeQuotaRequest.id == uuid.UUID(request_id)
        )
    )
    request_obj = result.scalar_one_or_none()
    if not request_obj:
        raise DataNotFoundError(f"配额申请不存在: {request_id}")

    if request_obj.status != "pending":
        raise DataValidationError(f"申请已处理，当前状态: {request_obj.status}")

    request_obj.status = status
    request_obj.reviewer_id = uuid.UUID(reviewer_id)
    request_obj.review_comment = review_comment
    request_obj.reviewed_at = datetime.now(timezone.utc)

    # 如果审批通过，更新配额上限
    if status == "approved":
        quota_result = await db.execute(
            select(ComputeQuota).where(
                ComputeQuota.id == request_obj.quota_id
            )
        )
        quota = quota_result.scalar_one_or_none()
        if quota:
            old_limit = quota.limit_value
            quota.limit_value = request_obj.requested_limit
            # 如果之前是 exceeded 状态，恢复 active
            if quota.status == "exceeded" and quota.used_value < quota.limit_value:
                quota.status = "active"
            logger.info(
                f"Quota limit updated: type={quota.resource_type}, "
                f"{old_limit} -> {request_obj.requested_limit}"
            )

    await db.commit()
    await db.refresh(request_obj)

    logger.info(
        f"Quota request reviewed: {request_id}, status={status}, reviewer={reviewer_id}"
    )
    return request_obj


async def list_quota_requests(
    db: AsyncSession,
    organization_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ComputeQuotaRequest]:
    """
    列出配额申请

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        status: 状态过滤
        limit: 返回数量
        offset: 偏移量

    Returns:
        申请列表
    """
    conditions = [
        ComputeQuotaRequest.organization_id == uuid.UUID(organization_id)
    ]
    if status:
        conditions.append(ComputeQuotaRequest.status == status)

    result = await db.execute(
        select(ComputeQuotaRequest)
        .where(and_(*conditions))
        .order_by(ComputeQuotaRequest.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


# ==================== 周期重置 ====================


async def reset_periodic_quotas(
    db: AsyncSession,
    period: str = "monthly",
) -> int:
    """
    重置周期性配额的已用量

    Args:
        db: 异步数据库会话
        period: 要重置的周期类型 (daily/weekly/monthly/yearly)

    Returns:
        重置的配额数量
    """
    result = await db.execute(
        select(ComputeQuota).where(
            and_(
                ComputeQuota.period == period,
                ComputeQuota.status.in_(["active", "exceeded"]),
            )
        )
    )
    quotas = list(result.scalars().all())

    count = 0
    for quota in quotas:
        if quota.used_value > 0:
            old_used = quota.used_value
            # 记录重置日志
            reset_log = ComputeQuotaUsage(
                quota_id=quota.id,
                delta=-old_used,
                before_value=old_used,
                after_value=0.0,
                reason=f"周期重置 ({period})",
            )
            db.add(reset_log)

            quota.used_value = 0.0
            if quota.status == "exceeded":
                quota.status = "active"
            count += 1

    await db.commit()
    logger.info(f"Reset {count} {period} compute quotas")
    return count
