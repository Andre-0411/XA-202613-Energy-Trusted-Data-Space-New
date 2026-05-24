"""
SLA (服务等级协议) Schema
可用性、响应时间、吞吐量监控
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from pydantic import BaseModel, Field


class SLATarget(BaseModel):
    """SLA 目标"""
    metric_name: str = Field(description="指标名称")
    target_value: float = Field(description="目标值")
    unit: str = Field(description="单位")
    operator: str = Field(default="<=", description="比较运算符: <=, >=, ==")
    description: Optional[str] = Field(default=None, description="描述")


class SLAConfig(BaseModel):
    """SLA 配置"""
    sla_id: str = Field(description="SLA ID")
    name: str = Field(description="SLA 名称")
    service_id: str = Field(description="服务 ID")
    service_name: Optional[str] = Field(default=None, description="服务名称")
    targets: List[SLATarget] = Field(description="SLA 目标列表")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")


class SLAMetricData(BaseModel):
    """SLA 指标数据"""
    metric_name: str = Field(description="指标名称")
    current_value: float = Field(description="当前值")
    target_value: float = Field(description="目标值")
    unit: str = Field(description="单位")
    status: str = Field(description="状态: met/at_risk/breached")
    compliance_percent: float = Field(description="达标百分比")
    trend: Optional[str] = Field(default=None, description="趋势")
    last_measured_at: datetime = Field(default_factory=datetime.utcnow, description="最后测量时间")


class SLAReport(BaseModel):
    """SLA 报告"""
    report_id: str = Field(description="报告 ID")
    sla_id: str = Field(description="SLA ID")
    service_id: str = Field(description="服务 ID")
    period_start: date = Field(description="开始日期")
    period_end: date = Field(description="结束日期")
    overall_compliance: float = Field(description="总体达标率")
    metrics: List[SLAMetricData] = Field(description="指标数据列表")
    breaches: List[Dict[str, Any]] = Field(default_factory=list, description="违规记录")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="生成时间")


class SLAAlertConfig(BaseModel):
    """SLA 告警配置"""
    alert_id: str = Field(description="告警 ID")
    sla_id: str = Field(description="SLA ID")
    metric_name: str = Field(description="指标名称")
    threshold_percent: float = Field(description="阈值百分比")
    notify_channels: List[str] = Field(default_factory=lambda: ["email"], description="通知渠道")
    enabled: bool = Field(default=True, description="是否启用")


class SLADashboardResponse(BaseModel):
    """SLA 仪表盘响应"""
    total_slas: int = Field(default=0, description="SLA 总数")
    met_count: int = Field(default=0, description="达标数量")
    at_risk_count: int = Field(default=0, description="风险数量")
    breached_count: int = Field(default=0, description="违规数量")
    overall_compliance: float = Field(default=100.0, description="总体达标率")
    metrics: List[SLAMetricData] = Field(default_factory=list, description="指标列表")
    recent_breaches: List[Dict[str, Any]] = Field(default_factory=list, description="最近违规")
    period: str = Field(default="30d", description="统计周期")
