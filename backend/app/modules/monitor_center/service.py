from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.models import AuditLog, Alert, AlertRule
from app.schemas.audit import (
    AuditLogResponse,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertResponse,
    SecurityOverview,
    AuditReport,
)
from app.schemas import PaginatedResponse, PaginationParams, MessageResponse


def get_security_overview(db: Session) -> SecurityOverview:
    """Aggregate security overview statistics."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Count today's requests from audit_logs
    today_requests = db.query(AuditLog).filter(
        AuditLog.timestamp >= today_start
    ).count()

    # Count active users today (distinct users with audit logs today)
    active_users_today = db.query(AuditLog.user_id).filter(
        AuditLog.timestamp >= today_start,
        AuditLog.user_id.isnot(None)
    ).distinct().count()

    # Count open alerts
    open_alerts = db.query(Alert).filter(Alert.status == "open").count()

    # Count critical alerts
    critical_alerts = db.query(Alert).filter(
        Alert.severity == "critical",
        Alert.status.in_(["open", "acknowledged"])
    ).count()

    # Compute risk level
    if critical_alerts > 0 or open_alerts > 10:
        risk_level = "high"
    elif open_alerts > 5:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Get recent 5 violations (failed actions)
    recent_violations = db.query(AuditLog).filter(
        AuditLog.status == "failure"
    ).order_by(desc(AuditLog.timestamp)).limit(5).all()

    # Get top 5 accessed resources
    top_resources = db.query(
        AuditLog.resource_type,
        AuditLog.resource_id,
        func.count().label("access_count")
    ).group_by(
        AuditLog.resource_type, AuditLog.resource_id
    ).order_by(desc("access_count")).limit(5).all()

    top_resources_list = [
        {
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "access_count": r.access_count
        }
        for r in top_resources
    ]

    return SecurityOverview(
        total_requests_today=today_requests,
        active_users_today=active_users_today,
        open_alerts=open_alerts,
        critical_alerts=critical_alerts,
        risk_level=risk_level,
        recent_violations=recent_violations,
        top_resources=top_resources_list,
    )


def get_audit_logs(
    db: Session,
    pagination: PaginationParams,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> tuple[list, int]:
    """Query audit_logs with filters."""
    query = db.query(AuditLog)

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    if action:
        query = query.filter(AuditLog.action == action)

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    if status:
        query = query.filter(AuditLog.status == status)

    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)

    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    # Get total count
    total = query.count()

    # Apply pagination
    logs = query.order_by(desc(AuditLog.timestamp)).offset(
        (pagination.page - 1) * pagination.page_size
    ).limit(pagination.page_size).all()

    return logs, total


def get_alert_rules(
    db: Session,
    pagination: PaginationParams,
    enabled: Optional[bool] = None,
    severity: Optional[str] = None,
) -> tuple[list, int]:
    """Query alert rules with filters."""
    query = db.query(AlertRule)

    if enabled is not None:
        query = query.filter(AlertRule.enabled == enabled)

    if severity:
        query = query.filter(AlertRule.severity == severity)

    total = query.count()

    rules = query.order_by(desc(AlertRule.created_at)).offset(
        (pagination.page - 1) * pagination.page_size
    ).limit(pagination.page_size).all()

    return rules, total


def create_alert_rule(
    db: Session, user_id: int, rule_in: AlertRuleCreate
) -> AlertRule:
    """Create a new alert rule."""
    rule = AlertRule(
        name=rule_in.name,
        description=rule_in.description,
        condition=rule_in.condition,
        severity=rule_in.severity,
        enabled=rule_in.enabled,
        actions=rule_in.actions,
        created_by=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_alert_rule(
    db: Session, rule_id: int, rule_in: AlertRuleUpdate
) -> AlertRule:
    """Update an existing alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise ValueError(f"Alert rule with id {rule_id} not found")

    update_data = rule_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def toggle_alert_rule(
    db: Session, rule_id: int, enabled: bool
) -> AlertRule:
    """Toggle an alert rule's enabled status."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise ValueError(f"Alert rule with id {rule_id} not found")

    rule.enabled = enabled
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def delete_alert_rule(db: Session, rule_id: int) -> None:
    """Delete an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise ValueError(f"Alert rule with id {rule_id} not found")

    db.delete(rule)
    db.commit()


def get_alerts(
    db: Session,
    pagination: PaginationParams,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    source: Optional[str] = None,
) -> tuple[list, int]:
    """Query alerts with filters."""
    query = db.query(Alert)

    if status:
        query = query.filter(Alert.status == status)

    if severity:
        query = query.filter(Alert.severity == severity)

    if source:
        query = query.filter(Alert.source == source)

    total = query.count()

    alerts = query.order_by(desc(Alert.created_at)).offset(
        (pagination.page - 1) * pagination.page_size
    ).limit(pagination.page_size).all()

    return alerts, total


def acknowledge_alert(db: Session, user_id: int, alert_id: int) -> Alert:
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError(f"Alert with id {alert_id} not found")

    alert.status = "acknowledged"
    alert.acknowledged_by = user_id
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(db: Session, user_id: int, alert_id: int) -> Alert:
    """Resolve an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError(f"Alert with id {alert_id} not found")

    alert.status = "resolved"
    alert.resolved_by = user_id
    alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


def generate_audit_report(
    db: Session, period_start: datetime, period_end: datetime
) -> AuditReport:
    """Generate a comprehensive audit report."""
    # Total requests in period
    total_requests = db.query(AuditLog).filter(
        and_(
            AuditLog.timestamp >= period_start,
            AuditLog.timestamp <= period_end
        )
    ).count()

    # Top users by activity
    top_users = db.query(
        AuditLog.user_id,
        AuditLog.username,
        func.count().label("activity_count")
    ).filter(
        and_(
            AuditLog.timestamp >= period_start,
            AuditLog.timestamp <= period_end,
            AuditLog.user_id.isnot(None)
        )
    ).group_by(
        AuditLog.user_id, AuditLog.username
    ).order_by(desc("activity_count")).limit(10).all()

    top_users_list = [
        {
            "user_id": u.user_id,
            "username": u.username,
            "activity_count": u.activity_count
        }
        for u in top_users
    ]

    # Top resources accessed
    top_resources = db.query(
        AuditLog.resource_type,
        AuditLog.resource_id,
        func.count().label("access_count")
    ).filter(
        and_(
            AuditLog.timestamp >= period_start,
            AuditLog.timestamp <= period_end
        )
    ).group_by(
        AuditLog.resource_type, AuditLog.resource_id
    ).order_by(desc("access_count")).limit(10).all()

    top_resources_list = [
        {
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "access_count": r.access_count
        }
        for r in top_resources
    ]

    # Alert summary by severity
    alert_summary = {}
    severity_counts = db.query(
        Alert.severity,
        func.count().label("count")
    ).filter(
        and_(
            Alert.created_at >= period_start,
            Alert.created_at <= period_end
        )
    ).group_by(Alert.severity).all()

    for s in severity_counts:
        alert_summary[s.severity] = s.count

    # Recommendations
    recommendations = []
    if alert_summary.get("critical", 0) > 0:
        recommendations.append("Review and address all critical alerts immediately")
    if total_requests > 10000:
        recommendations.append("High traffic detected - consider rate limiting")
    recommendations.append("Continue regular security audits")

    return AuditReport(
        period_start=period_start,
        period_end=period_end,
        total_requests=total_requests,
        top_users=top_users_list,
        top_resources=top_resources_list,
        alert_summary=alert_summary,
        recommendations=recommendations,
    )
