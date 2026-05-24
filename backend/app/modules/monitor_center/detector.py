from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, Alert, AlertRule


def evaluate_alert_rule(rule: AlertRule, context: dict) -> bool:
    """
    Evaluate an alert rule's condition against current context.

    The condition JSON can have types:
    - {"type": "frequency", "threshold": 50, "window_minutes": 5}
    - {"type": "ip_anomaly"}
    - {"type": "export", "min_size_mb": 100}
    - {"type": "failed_login", "threshold": 5}
    """
    condition = rule.condition

    if not condition or "type" not in condition:
        return False

    condition_type = condition["type"]

    if condition_type == "frequency":
        threshold = condition.get("threshold", 50)
        return context.get("request_count", 0) > threshold

    elif condition_type == "ip_anomaly":
        return context.get("is_new_ip", False) is True

    elif condition_type == "export":
        min_size_mb = condition.get("min_size_mb", 100)
        return context.get("export_size_mb", 0) > min_size_mb

    elif condition_type == "failed_login":
        threshold = condition.get("threshold", 5)
        return context.get("failed_login_count", 0) > threshold

    return False


def create_alert(db: Session, rule: AlertRule, context: dict) -> Alert:
    """Create an alert record from a triggered rule."""
    alert = Alert(
        rule_id=rule.id,
        severity=rule.severity,
        title=f"Alert: {rule.name}",
        description=f"Rule '{rule.name}' was triggered. Context: {context}",
        source="detector",
        status="open",
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def record_audit_log(
    db: Session,
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    detail: Optional[str] = None,
) -> AuditLog:
    """Create an audit log entry."""
    audit_log = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
        detail=detail,
        timestamp=datetime.utcnow(),
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def check_audit_rules(
    db: Session,
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    resource_type: str,
    ip_address: Optional[str],
) -> list[Alert]:
    """
    Run all enabled alert rules against the current action context.
    Return any triggered alerts.
    """
    # Get all enabled alert rules
    enabled_rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()

    triggered_alerts = []

    for rule in enabled_rules:
        # Build context for rule evaluation
        context = {
            "user_id": user_id,
            "username": username,
            "action": action,
            "resource_type": resource_type,
            "ip_address": ip_address,
        }

        # Check if rule applies to this action
        if rule.actions and action not in rule.actions:
            continue

        # Evaluate the rule
        if evaluate_alert_rule(rule, context):
            alert = create_alert(db, rule, context)
            triggered_alerts.append(alert)

    return triggered_alerts
