"""Portal dashboard service module."""

from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    User,
    Organization,
    DataAsset,
    ComputeTask,
    AuditLog,
    Alert,
    AuthToken,
    EvidenceRecord,
    SystemStat,
)
from app.schemas import DashboardOverview, DashboardCard


def get_dashboard_overview(db: Session) -> DashboardOverview:
    """
    Get dashboard overview with aggregated stats from all tables.
    Returns DashboardOverview with cards, recent activities, system status, and announcements.
    """
    # Count statistics
    user_count = db.query(func.count(User.id)).scalar() or 0
    org_count = db.query(func.count(Organization.id)).filter(Organization.status == "active").scalar() or 0
    asset_count = db.query(func.count(DataAsset.id)).filter(DataAsset.status == "active").scalar() or 0
    task_count = db.query(func.count(ComputeTask.id)).scalar() or 0
    evidence_count = db.query(func.count(EvidenceRecord.id)).scalar() or 0
    token_count = db.query(func.count(AuthToken.id)).filter(AuthToken.status == "approved").scalar() or 0
    alert_count = db.query(func.count(Alert.id)).filter(Alert.status == "open").scalar() or 0

    # Build dashboard cards
    cards = [
        DashboardCard(title="用户总数", value=user_count, icon="users"),
        DashboardCard(title="活跃组织", value=org_count, icon="organization"),
        DashboardCard(title="数据资产", value=asset_count, icon="database"),
        DashboardCard(title="计算任务", value=task_count, icon="compute"),
        DashboardCard(title="证据记录", value=evidence_count, icon="evidence"),
        DashboardCard(title="有效令牌", value=token_count, icon="token"),
        DashboardCard(title="待处理告警", value=alert_count, icon="alert"),
    ]

    # Get recent 10 audit logs as activities
    recent_logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )

    recent_activities = [
        {
            "id": log.id,
            "action": log.action,
            "username": log.username,
            "resource_type": log.resource_type,
            "detail": log.detail,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in recent_logs
    ]

    # System status (simplified - assume DB is connected since we're querying)
    system_status = {
        "database": "connected",
        "redis": "unknown",  # Would need Redis connection check
        "api": "operational",
        "blockchain": "unknown",  # Would need blockchain connection check
    }

    # Get announcements
    announcements = get_system_announcements(db, limit=5)

    return DashboardOverview(
        cards=cards,
        recent_activities=recent_activities,
        system_status=system_status,
        announcements=announcements,
    )


def get_system_announcements(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get system announcements.
    Returns list of announcement dicts (hardcoded for now).
    """
    announcements = [
        {
            "id": 1,
            "title": "系统维护通知",
            "content": "将于本周六凌晨2:00-4:00进行系统维护，届时服务将暂时不可用。",
            "type": "maintenance",
            "priority": "high",
            "created_at": "2026-05-16T10:00:00",
        },
        {
            "id": 2,
            "title": "新功能上线：数据资产版本管理",
            "content": "现已支持数据资产的多版本管理，您可以在资产详情页查看历史版本。",
            "type": "feature",
            "priority": "medium",
            "created_at": "2026-05-15T09:00:00",
        },
        {
            "id": 3,
            "title": "安全提示：请及时更新密码",
            "content": "为保障账户安全，建议定期更新密码，并使用强密码策略。",
            "type": "security",
            "priority": "medium",
            "created_at": "2026-05-14T14:00:00",
        },
        {
            "id": 4,
            "title": "新增数据提供方：国家电网",
            "content": "欢迎国家电网加入能源可信数据空间，现已可访问其共享的数据资产。",
            "type": "partner",
            "priority": "low",
            "created_at": "2026-05-13T11:00:00",
        },
        {
            "id": 5,
            "title": "系统使用培训通知",
            "content": "将于下周三下午2点举办线上培训，介绍系统新功能及最佳实践。",
            "type": "training",
            "priority": "low",
            "created_at": "2026-05-12T16:00:00",
        },
    ]

    return announcements[:limit]
