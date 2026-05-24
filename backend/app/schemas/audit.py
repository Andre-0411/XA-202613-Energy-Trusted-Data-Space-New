from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    detail: Optional[str]
    ip_address: Optional[str]
    status: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    condition: Dict[str, Any] = Field(..., description="告警条件配置")
    severity: str = Field(default="medium", description="low/medium/high/critical")
    action_type: str = Field(default="log", description="log/email/webhook/block")


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    action_type: Optional[str] = None
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    condition: Dict[str, Any]
    severity: str
    action_type: str
    enabled: bool
    last_triggered_at: Optional[datetime]
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: int
    rule_id: Optional[int]
    title: str
    content: str
    severity: str
    status: str
    source: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[int]
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class SecurityOverview(BaseModel):
    total_requests_today: int
    active_users_today: int
    open_alerts: int
    critical_alerts: int
    risk_level: str = "low"
    recent_violations: List[Dict[str, Any]] = []
    top_resources: List[Dict[str, Any]] = []


class AuditReport(BaseModel):
    report_id: str
    title: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    summary: Dict[str, Any]
    top_users: List[Dict[str, Any]]
    top_resources: List[Dict[str, Any]]
    alert_summary: Dict[str, int]
    recommendations: List[str] = []
