"""
任务状态实时追踪服务

通过 WebSocket 推送计算任务状态变更:
- 排队中 (queued/pending)
- 运行中 (running)
- 已完成 (completed)
- 失败 (failed)
- 已取消 (cancelled)
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import ComputeTask
from app.exceptions import ComputeTaskNotFoundError

logger = logging.getLogger(__name__)

# 状态变更事件类型
STATUS_EVENT_TYPES = {
    "draft": "task.created",
    "pending": "task.queued",
    "running": "task.started",
    "completed": "task.completed",
    "failed": "task.failed",
    "cancelled": "task.cancelled",
}


async def notify_task_status_change(
    task_id: str,
    old_status: str,
    new_status: str,
    progress: int = 0,
    error_message: str = "",
    extra_data: Optional[dict] = None,
) -> None:
    """
    推送任务状态变更通知

    通过 WebSocket 管理器向订阅该任务的用户推送状态变更。

    Args:
        task_id: 任务 ID
        old_status: 原状态
        new_status: 新状态
        progress: 进度百分比
        error_message: 错误信息（失败时）
        extra_data: 附加数据
    """
    event_type = STATUS_EVENT_TYPES.get(new_status, "task.updated")

    message = {
        "type": "task_status_change",
        "event": event_type,
        "task_id": task_id,
        "old_status": old_status,
        "new_status": new_status,
        "progress": progress,
        "error_message": error_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **(extra_data or {}),
    }

    try:
        from app.services.websocket_manager import get_ws_manager
        ws_manager = get_ws_manager()
        # 推送到任务频道
        await ws_manager.broadcast_to_channel(
            channel=f"task:{task_id}",
            message=message,
        )
        # 推送到全局计算任务频道
        await ws_manager.broadcast_to_channel(
            channel="compute:tasks",
            message=message,
        )
        logger.info(f"Task status notification sent: {task_id} {old_status} -> {new_status}")
    except Exception as e:
        logger.warning(f"Failed to send task status notification: {e}")


async def notify_task_progress(
    task_id: str,
    progress: int,
    stage: str = "",
    detail: str = "",
) -> None:
    """
    推送任务进度更新

    Args:
        task_id: 任务 ID
        progress: 进度百分比 (0-100)
        stage: 当前阶段
        detail: 阶段详情
    """
    message = {
        "type": "task_progress",
        "task_id": task_id,
        "progress": progress,
        "stage": stage,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        from app.services.websocket_manager import get_ws_manager
        ws_manager = get_ws_manager()
        await ws_manager.broadcast_to_channel(
            channel=f"task:{task_id}",
            message=message,
        )
    except Exception as e:
        logger.warning(f"Failed to send task progress notification: {e}")


async def get_task_status_summary(
    db: AsyncSession,
    organization_id: Optional[str] = None,
) -> dict:
    """
    获取任务状态汇总

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID（可选过滤）

    Returns:
        任务状态统计
    """
    conditions = []
    if organization_id:
        import uuid
        conditions.append(ComputeTask.organization_id == uuid.UUID(organization_id))

    # 各状态计数
    status_counts = {}
    for status in ["draft", "pending", "running", "completed", "failed", "cancelled"]:
        query = select(func.count(ComputeTask.id)).where(
            and_(ComputeTask.status == status, *conditions)
        )
        result = await db.execute(query)
        status_counts[status] = result.scalar() or 0

    # 总数
    total = sum(status_counts.values())

    # 活跃任务数
    active = status_counts.get("running", 0) + status_counts.get("pending", 0)

    return {
        "total": total,
        "active": active,
        "status_breakdown": status_counts,
        "summary": {
            "queued": status_counts.get("pending", 0),
            "running": status_counts.get("running", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "cancelled": status_counts.get("cancelled", 0),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def get_running_tasks(
    db: AsyncSession,
    organization_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """
    获取正在运行的任务列表

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID
        limit: 返回数量限制

    Returns:
        运行中的任务列表
    """
    import uuid as uuid_mod
    conditions = [ComputeTask.status.in_(["running", "pending"])]
    if organization_id:
        conditions.append(ComputeTask.organization_id == uuid_mod.UUID(organization_id))

    result = await db.execute(
        select(ComputeTask)
        .where(and_(*conditions))
        .order_by(ComputeTask.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()

    return [
        {
            "task_id": str(t.id),
            "name": t.name,
            "task_type": t.task_type,
            "status": t.status,
            "progress": t.progress,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks
    ]
