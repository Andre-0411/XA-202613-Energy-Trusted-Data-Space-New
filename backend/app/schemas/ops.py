"""
运营 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class ComplianceReportCreate(BaseModel):
    """创建合规报告"""
    organization_id: str = Field(description="组织 ID")
    report_type: str = Field(description="类型")
    period: str = Field(description="报告周期")


class ComplianceReportResponse(BaseModel):
    """合规报告响应"""
    id: str
    organization_id: str
    report_type: str
    period: str
    findings: dict
    gdpr_checklist: Optional[dict] = None
    data_security_checklist: Optional[dict] = None
    status: str
    generated_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class KpiDashboardResponse(BaseModel):
    """KPI 仪表盘响应"""
    total_assets: int = 0
    total_compute_tasks: int = 0
    active_users: int = 0
    total_organizations: int = 0
    blockchain_transactions: int = 0
    security_incidents: int = 0
    avg_response_time_ms: float = 0.0
    uptime_percentage: float = 99.9
    data_quality_avg: float = 0.0
    compliance_score: float = 0.0


class BillingSummaryResponse(BaseModel):
    """计费汇总响应"""
    total_revenue: float = 0.0
    pending_payments: float = 0.0
    completed_payments: float = 0.0
    overdue_payments: float = 0.0
    billing_by_service: dict = Field(default_factory=dict)
    billing_by_month: dict = Field(default_factory=dict)
