"""
访问日志服务
记录访问日志 / 查询访问日志（分页+筛选）/ 统计分析
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.access_log import AccessLog
from app.models.data_asset import DataAsset
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# 访问动作类型
VALID_ACTIONS = {
    "read",       # 读取
    "write",      # 写入
    "delete",     # 删除
    "export",     # 导出
    "compute",    # 计算
    "preview",    # 预览
    "apply",      # 申请
    "feedback",   # 反馈
    "download",   # 下载
    "share",      # 分享
}


async def record_access(
    db: AsyncSession,
    user_id: str,
    asset_id: Optional[str] = None,
    action: str = "read",
    compute_task_id: Optional[str] = None,
    result: str = "success",
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
) -> dict:
    """
    记录访问日志

    Args:
        user_id: 用户 ID
        asset_id: 数据资产 ID（可选）
        action: 访问动作
        compute_task_id: 关联计算任务 ID（可选）
        result: 访问结果 (success/failure/denied)
        ip_address: 访问 IP
        details: 详细信息

    Returns:
        日志记录摘要
    """
    if action not in VALID_ACTIONS:
        logger.warning(f"Unusual access action: {action}")

    log_entry = AccessLog(
        user_id=uuid.UUID(user_id) if user_id else None,
        asset_id=uuid.UUID(asset_id) if asset_id else None,
        action=action,
        compute_task_id=uuid.UUID(compute_task_id) if compute_task_id else None,
        result=result,
        ip_address=ip_address,
        details=details or {},
    )
    db.add(log_entry)
    await db.commit()

    logger.info(
        f"Access logged: user={user_id}, action={action}, "
        f"asset={asset_id}, result={result}"
    )
    return {
        "log_id": str(log_entry.id),
        "user_id": user_id,
        "asset_id": asset_id,
        "action": action,
        "result": result,
        "timestamp": str(log_entry.created_at),
    }


async def query_access_logs(
    db: AsyncSession,
    params: PaginationParams,
    user_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    action: Optional[str] = None,
    result: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> PaginatedResponse:
    """
    查询访问日志（分页+筛选）

    支持按用户/资产/动作/结果/时间范围筛选
    """
    query = select(AccessLog)

    # 按用户筛选
    if user_id:
        query = query.where(AccessLog.user_id == uuid.UUID(user_id))

    # 按资产筛选
    if asset_id:
        query = query.where(AccessLog.asset_id == uuid.UUID(asset_id))

    # 按动作筛选
    if action:
        if action not in VALID_ACTIONS:
            raise DataValidationError(
                f"无效的访问动作: {action}，允许值: {VALID_ACTIONS}"
            )
        query = query.where(AccessLog.action == action)

    # 按结果筛选
    if result:
        query = query.where(AccessLog.result == result)

    # 按时间范围筛选
    if start_time:
        query = query.where(AccessLog.created_at >= start_time)
    if end_time:
        query = query.where(AccessLog.created_at <= end_time)

    # 默认按时间倒序
    result_data = await paginate_query(db, query, params)
    return result_data


async def get_access_log(
    db: AsyncSession,
    log_id: str,
) -> dict:
    """获取单条访问日志详情"""
    result = await db.execute(
        select(AccessLog).where(AccessLog.id == uuid.UUID(log_id))
    )
    log = result.scalar_one_or_none()
    if not log:
        raise DataNotFoundError("访问日志未找到")

    return {
        "id": str(log.id),
        "user_id": str(log.user_id) if log.user_id else None,
        "asset_id": str(log.asset_id) if log.asset_id else None,
        "action": log.action,
        "compute_task_id": str(log.compute_task_id) if log.compute_task_id else None,
        "result": log.result,
        "ip_address": log.ip_address,
        "details": log.details,
        "created_at": str(log.created_at),
    }


async def get_access_statistics(
    db: AsyncSession,
    asset_id: Optional[str] = None,
    user_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> dict:
    """
    访问统计

    - 总访问量
    - 按动作分类统计
    - 按结果分类统计
    - 活跃用户 Top N
    """
    # 基础查询条件
    conditions = []
    if asset_id:
        conditions.append(AccessLog.asset_id == uuid.UUID(asset_id))
    if user_id:
        conditions.append(AccessLog.user_id == uuid.UUID(user_id))
    if start_time:
        conditions.append(AccessLog.created_at >= start_time)
    if end_time:
        conditions.append(AccessLog.created_at <= end_time)

    base_filter = and_(*conditions) if conditions else True

    # 总访问量
    total_result = await db.execute(
        select(func.count(AccessLog.id)).where(base_filter)
    )
    total = total_result.scalar() or 0

    # 按动作统计
    action_result = await db.execute(
        select(AccessLog.action, func.count(AccessLog.id))
        .where(base_filter)
        .group_by(AccessLog.action)
    )
    action_stats = {row[0]: row[1] for row in action_result.all()}

    # 按结果统计
    result_stats_query = await db.execute(
        select(AccessLog.result, func.count(AccessLog.id))
        .where(base_filter)
        .group_by(AccessLog.result)
    )
    result_stats = {row[0]: row[1] for row in result_stats_query.all()}

    # 活跃用户 Top 10
    top_users_query = await db.execute(
        select(AccessLog.user_id, func.count(AccessLog.id).label("count"))
        .where(base_filter)
        .group_by(AccessLog.user_id)
        .order_by(func.count(AccessLog.id).desc())
        .limit(10)
    )
    top_users = [
        {"user_id": str(row[0]), "access_count": row[1]}
        for row in top_users_query.all()
        if row[0] is not None
    ]

    # 独立用户数
    unique_users_result = await db.execute(
        select(func.count(func.distinct(AccessLog.user_id))).where(base_filter)
    )
    unique_users = unique_users_result.scalar() or 0

    return {
        "total_accesses": total,
        "unique_users": unique_users,
        "by_action": action_stats,
        "by_result": result_stats,
        "top_users": top_users,
        "period": {
            "start": start_time.isoformat() if start_time else None,
            "end": end_time.isoformat() if end_time else None,
        },
    }


async def get_asset_access_history(
    db: AsyncSession,
    asset_id: str,
    limit: int = 50,
) -> list[dict]:
    """获取资产的访问历史"""
    result = await db.execute(
        select(AccessLog)
        .where(AccessLog.asset_id == uuid.UUID(asset_id))
        .order_by(AccessLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "result": log.result,
            "ip_address": log.ip_address,
            "details": log.details,
            "created_at": str(log.created_at),
        }
        for log in logs
    ]


async def check_access_permission(
    db: AsyncSession,
    user_id: str,
    asset_id: str,
    action: str,
) -> bool:
    """
    检查用户是否有权访问资产

    基于访问日志中的历史申请记录判断
    """
    # 查找用户对该资产的已批准申请
    result = await db.execute(
        select(AccessLog).where(
            and_(
                AccessLog.user_id == uuid.UUID(user_id),
                AccessLog.asset_id == uuid.UUID(asset_id),
                AccessLog.action == "apply",
                AccessLog.result == "approved",
            )
        )
    )
    approved = result.scalar_one_or_none()

    if approved:
        # 检查是否在有效期内
        details = approved.details or {}
        duration_days = details.get("duration_days", 30)
        approved_at = approved.created_at

        from datetime import timedelta
        expiry = approved_at + timedelta(days=duration_days)

        if datetime.now(timezone.utc) <= expiry.replace(tzinfo=timezone.utc):
            return True

    return False
