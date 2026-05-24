"""
统一门户服务
仪表盘数据聚合、快速入口、数据概览、活动日志、通知管理
所有数据均来自数据库，无 mock/随机数据
"""
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portal_model import (
    QuickLink, PortalNotification, PortalLayout, ActivityLog,
)
from app.models.data_asset import DataSource, DataAsset
from app.models.compute_task import ComputeTask
from app.models.blockchain import BlockchainTransaction
from app.models.monitor_alert import MonitorAlert
from app.models.user import User, Organization
from app.schemas.portal import (
    PortalDashboardResponse, QuickLinkItem, DataOverviewItem,
    PortalNotification as PortalNotificationSchema,
    PortalLayoutConfig, PortalWidgetConfig, ActivityLogItem,
)

logger = logging.getLogger(__name__)


# ===== 仪表盘 =====

async def get_dashboard_data(
    db: AsyncSession,
    user_id: str,
    role: Optional[str] = None,
    time_range: str = "7d",
) -> PortalDashboardResponse:
    """获取门户仪表盘数据 — 全部从数据库聚合"""
    # 数据资产总数
    assets_result = await db.execute(select(func.count()).select_from(DataAsset))
    data_assets_count = assets_result.scalar() or 0

    # 计算任务总数
    tasks_result = await db.execute(select(func.count()).select_from(ComputeTask))
    compute_tasks_count = tasks_result.scalar() or 0

    # 活跃告警数 (status = 'firing')
    alerts_result = await db.execute(
        select(func.count()).select_from(MonitorAlert).where(
            MonitorAlert.status == "firing"
        )
    )
    active_alerts_count = alerts_result.scalar() or 0

    # 区块链交易数
    bc_result = await db.execute(select(func.count()).select_from(BlockchainTransaction))
    blockchain_transactions = bc_result.scalar() or 0

    # 系统状态: 有严重告警则 warning，否则 healthy
    critical_result = await db.execute(
        select(func.count()).select_from(MonitorAlert).where(
            and_(MonitorAlert.status == "firing", MonitorAlert.severity == "critical")
        )
    )
    system_status = "warning" if (critical_result.scalar() or 0) > 0 else "healthy"

    # 最近活动
    recent_activities = await _get_recent_activities_db(db, user_id, limit=10)

    # 快速链接
    links_result = await db.execute(
        select(QuickLink).order_by(QuickLink.sort_order).limit(20)
    )
    quick_links = [
        {"title": l.title, "icon": l.icon or "", "url": l.url}
        for l in links_result.scalars().all()
    ]

    return PortalDashboardResponse(
        user_id=user_id,
        role=role or "user",
        data_assets_count=data_assets_count,
        compute_tasks_count=compute_tasks_count,
        active_alerts_count=active_alerts_count,
        blockchain_transactions=blockchain_transactions,
        recent_activities=recent_activities,
        quick_links=quick_links,
        system_status=system_status,
        last_updated=datetime.now(timezone.utc),
    )


# ===== 快速链接 =====

async def get_quick_links(db: AsyncSession) -> List[QuickLinkItem]:
    """获取快速链接列表"""
    result = await db.execute(select(QuickLink).order_by(QuickLink.sort_order))
    return [
        QuickLinkItem(
            id=str(l.id),
            title=l.title,
            icon=l.icon or "",
            url=l.url,
            description=None,
            category="general",
            order=l.sort_order,
        )
        for l in result.scalars().all()
    ]


async def add_quick_link(db: AsyncSession, link: QuickLinkItem) -> QuickLinkItem:
    """添加快速链接"""
    new_link = QuickLink(
        title=link.title,
        url=link.url,
        icon=link.icon,
        sort_order=link.order,
        user_id="system",
    )
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)
    return QuickLinkItem(
        id=str(new_link.id),
        title=new_link.title,
        icon=new_link.icon or "",
        url=new_link.url,
        description=None,
        category="general",
        order=new_link.sort_order,
    )


async def remove_quick_link(db: AsyncSession, link_id: str) -> bool:
    """移除快速链接"""
    result = await db.execute(select(QuickLink).where(QuickLink.id == uuid.UUID(link_id)))
    link = result.scalar_one_or_none()
    if not link:
        return False
    await db.delete(link)
    await db.commit()
    return True


# ===== 数据概览 =====

async def get_data_overview(db: AsyncSession, time_range: str = "7d") -> List[DataOverviewItem]:
    """获取数据概览 — 从数据库聚合"""
    # 计算时间范围
    days = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}.get(time_range, 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 数据资产
    assets_total = (await db.execute(select(func.count()).select_from(DataAsset))).scalar() or 0
    assets_new = (await db.execute(
        select(func.count()).select_from(DataAsset).where(DataAsset.created_at >= cutoff)
    )).scalar() or 0

    # 计算任务
    tasks_total = (await db.execute(select(func.count()).select_from(ComputeTask))).scalar() or 0
    tasks_new = (await db.execute(
        select(func.count()).select_from(ComputeTask).where(ComputeTask.created_at >= cutoff)
    )).scalar() or 0

    # 活跃用户
    active_users = (await db.execute(
        select(func.count()).select_from(User).where(User.status == "active")
    )).scalar() or 0

    # 组织数
    org_count = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.status == "active")
    )).scalar() or 0

    # 区块链交易
    bc_total = (await db.execute(select(func.count()).select_from(BlockchainTransaction))).scalar() or 0

    # 告警
    alerts_active = (await db.execute(
        select(func.count()).select_from(MonitorAlert).where(MonitorAlert.status == "firing")
    )).scalar() or 0

    def _change(new_count: int, total: int) -> tuple[float, str]:
        if total == 0:
            return (0.0, "stable")
        pct = round((new_count / max(total - new_count, 1)) * 100, 1)
        trend = "up" if pct > 0 else ("down" if pct < 0 else "stable")
        return (pct, trend)

    pct_assets, trend_assets = _change(assets_new, assets_total)
    pct_tasks, trend_tasks = _change(tasks_new, tasks_total)

    return [
        DataOverviewItem(
            metric_name="数据资产",
            metric_value=assets_total,
            unit="个",
            change_percent=pct_assets,
            trend=trend_assets,
        ),
        DataOverviewItem(
            metric_name="计算任务",
            metric_value=tasks_total,
            unit="个",
            change_percent=pct_tasks,
            trend=trend_tasks,
        ),
        DataOverviewItem(
            metric_name="活跃用户",
            metric_value=active_users,
            unit="人",
            change_percent=None,
            trend="stable",
        ),
        DataOverviewItem(
            metric_name="组织机构",
            metric_value=org_count,
            unit="个",
            change_percent=None,
            trend="stable",
        ),
        DataOverviewItem(
            metric_name="区块链交易",
            metric_value=bc_total,
            unit="笔",
            change_percent=None,
            trend="up",
        ),
        DataOverviewItem(
            metric_name="活跃告警",
            metric_value=alerts_active,
            unit="条",
            change_percent=None,
            trend="down" if alerts_active == 0 else "stable",
        ),
    ]


# ===== 通知 =====

async def get_notifications(
    db: AsyncSession,
    user_id: str,
    unread_only: bool = False,
    limit: int = 20,
) -> List[PortalNotificationSchema]:
    """获取用户通知"""
    conditions = []
    if unread_only:
        conditions.append(PortalNotification.read == False)

    where_clause = and_(*conditions) if conditions else True
    stmt = (
        select(PortalNotification)
        .where(where_clause)
        .order_by(PortalNotification.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        PortalNotificationSchema(
            id=str(n.id),
            title=n.title,
            content=n.content,
            type=n.notification_type,
            read=n.read,
            created_at=n.created_at,
            link=n.link,
        )
        for n in result.scalars().all()
    ]


async def mark_notification_read(db: AsyncSession, notification_id: str) -> bool:
    """标记通知为已读"""
    result = await db.execute(
        select(PortalNotification).where(PortalNotification.id == uuid.UUID(notification_id))
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    notif.read = True
    notif.read_at = datetime.now(timezone.utc)
    await db.commit()
    return True


# ===== 布局配置 =====

async def get_layout_config(db: AsyncSession, user_id: str) -> PortalLayoutConfig:
    """获取用户布局配置"""
    result = await db.execute(
        select(PortalLayout).where(
            and_(PortalLayout.user_id == user_id, PortalLayout.is_default == True)
        )
    )
    layout = result.scalar_one_or_none()

    if layout:
        widgets = [
            PortalWidgetConfig(**w) for w in (layout.layout_config.get("widgets", []))
        ]
        return PortalLayoutConfig(
            user_id=user_id,
            layout_name=layout.name,
            widgets=widgets,
            updated_at=layout.updated_at or layout.created_at,
        )

    # 返回默认布局
    default_widgets = [
        PortalWidgetConfig(
            widget_id="widget_overview",
            widget_type="stat",
            title="数据概览",
            position={"x": 0, "y": 0, "w": 12, "h": 4},
        ),
        PortalWidgetConfig(
            widget_id="widget_alerts",
            widget_type="list",
            title="最近告警",
            position={"x": 0, "y": 4, "w": 6, "h": 4},
        ),
        PortalWidgetConfig(
            widget_id="widget_activities",
            widget_type="list",
            title="最近活动",
            position={"x": 6, "y": 4, "w": 6, "h": 4},
        ),
        PortalWidgetConfig(
            widget_id="widget_quick_links",
            widget_type="list",
            title="快速入口",
            position={"x": 0, "y": 8, "w": 12, "h": 3},
        ),
    ]
    return PortalLayoutConfig(
        user_id=user_id,
        layout_name="default",
        widgets=default_widgets,
        updated_at=datetime.now(timezone.utc),
    )


async def save_layout_config(db: AsyncSession, config: PortalLayoutConfig) -> PortalLayoutConfig:
    """保存用户布局配置"""
    # 查找已有布局
    result = await db.execute(
        select(PortalLayout).where(
            and_(PortalLayout.user_id == config.user_id, PortalLayout.is_default == True)
        )
    )
    layout = result.scalar_one_or_none()

    widgets_data = [w.model_dump() for w in config.widgets]

    if layout:
        layout.name = config.layout_name
        layout.layout_config = {"widgets": widgets_data}
    else:
        layout = PortalLayout(
            user_id=config.user_id,
            name=config.layout_name,
            layout_config={"widgets": widgets_data},
            is_default=True,
        )
        db.add(layout)

    await db.commit()
    config.updated_at = datetime.now(timezone.utc)
    return config


# ===== 活动日志 =====

async def _get_recent_activities_db(
    db: AsyncSession, user_id: str, limit: int = 10
) -> List[dict]:
    """获取最近活动"""
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.user_id == user_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "action": a.action,
            "resource_type": a.details.get("resource_type", "") if a.details else "",
            "timestamp": a.created_at.isoformat() if a.created_at else "",
        }
        for a in result.scalars().all()
    ]


async def log_activity(
    db: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
) -> ActivityLogItem:
    """记录活动日志"""
    log = ActivityLog(
        user_id=user_id,
        action=action,
        details={"resource_type": resource_type, "resource_id": resource_id, "details": details},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return ActivityLogItem(
        id=str(log.id),
        user_id=log.user_id,
        action=log.action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        timestamp=log.created_at,
    )


async def get_activity_logs(
    db: AsyncSession,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 50,
) -> List[ActivityLogItem]:
    """获取活动日志"""
    conditions = []
    if user_id:
        conditions.append(ActivityLog.user_id == user_id)

    where_clause = and_(*conditions) if conditions else True
    stmt = (
        select(ActivityLog)
        .where(where_clause)
        .order_by(ActivityLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    items = []
    for a in logs:
        details = a.details or {}
        if resource_type and details.get("resource_type") != resource_type:
            continue
        items.append(ActivityLogItem(
            id=str(a.id),
            user_id=a.user_id,
            action=a.action,
            resource_type=details.get("resource_type", ""),
            resource_id=details.get("resource_id"),
            details=details.get("details"),
            timestamp=a.created_at,
        ))
    return items
