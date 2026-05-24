from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.utils.deps import get_current_user, require_role
from app.database import get_sync_db
from app.models import User, AuditLog, AlertRule, Alert as AlertModel
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
from app.modules.monitor_center import service

router = APIRouter(prefix="/api/monitor-center", tags=["数据监管中心"])


@router.get("/security/overview", response_model=SecurityOverview)
def get_security_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Get security overview statistics."""
    return service.get_security_overview(db)


@router.get("/audit/log", response_model=PaginatedResponse[AuditLogResponse])
def get_audit_logs(
    pagination: PaginationParams = Depends(),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Get audit logs with pagination and filters."""
    logs, total = service.get_audit_logs(
        db=db,
        pagination=pagination,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    return PaginatedResponse(
        items=logs,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/audit/report", response_model=AuditReport)
def get_audit_report(
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Generate audit report for a period."""
    return service.generate_audit_report(db, start_date, end_date)


@router.get("/alert-rule/list", response_model=PaginatedResponse[AlertRuleResponse])
def get_alert_rules(
    pagination: PaginationParams = Depends(),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Get alert rules with pagination and filters."""
    rules, total = service.get_alert_rules(
        db=db,
        pagination=pagination,
        enabled=enabled,
        severity=severity,
    )
    return PaginatedResponse(
        items=rules,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/alert-rule", response_model=AlertRuleResponse)
def create_alert_rule(
    rule_in: AlertRuleCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_sync_db),
):
    """Create a new alert rule (admin only)."""
    return service.create_alert_rule(db, current_user.id, rule_in)


@router.put("/alert-rule/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: int,
    rule_in: AlertRuleUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_sync_db),
):
    """Update an alert rule (admin only)."""
    return service.update_alert_rule(db, rule_id, rule_in)


@router.post("/alert-rule/{rule_id}/toggle", response_model=AlertRuleResponse)
def toggle_alert_rule(
    rule_id: int,
    enabled: bool,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_sync_db),
):
    """Toggle alert rule enabled status (admin only)."""
    return service.toggle_alert_rule(db, rule_id, enabled)


@router.delete("/alert-rule/{rule_id}", response_model=MessageResponse)
def delete_alert_rule(
    rule_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_sync_db),
):
    """Delete an alert rule (admin only)."""
    service.delete_alert_rule(db, rule_id)
    return MessageResponse(message="Alert rule deleted successfully")


@router.get("/alert/list", response_model=PaginatedResponse[AlertResponse])
def get_alerts(
    pagination: PaginationParams = Depends(),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    source: Optional[str] = Query(None, description="Filter by source"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Get alerts with pagination and filters."""
    alerts, total = service.get_alerts(
        db=db,
        pagination=pagination,
        status=status,
        severity=severity,
        source=source,
    )
    return PaginatedResponse(
        items=alerts,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/alert/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Acknowledge an alert."""
    return service.acknowledge_alert(db, current_user.id, alert_id)


@router.post("/alert/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    """Resolve an alert."""
    return service.resolve_alert(db, current_user.id, alert_id)
