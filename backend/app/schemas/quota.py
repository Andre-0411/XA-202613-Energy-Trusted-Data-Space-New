"""
配额管理 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class QuotaCreate(BaseModel):
    """创建配额"""
    organization_id: str = Field(description="组织 ID")
    resource_type: str = Field(description="资源类型: api_calls/storage_mb/compute_hours/data_assets/users")
    limit_value: float = Field(gt=0, description="配额上限")
    unit: str = Field(default="", description="计量单位")
    period: str = Field(default="monthly", description="配额周期: monthly/yearly/permanent")
    alert_threshold: float = Field(default=80.0, ge=0, le=100, description="告警阈值百分比")


class QuotaUpdate(BaseModel):
    """更新配额"""
    limit_value: Optional[float] = Field(default=None, gt=0, description="配额上限")
    alert_threshold: Optional[float] = Field(default=None, ge=0, le=100, description="告警阈值百分比")
    status: Optional[str] = Field(default=None, description="状态")


class QuotaResponse(BaseModel):
    """配额响应"""
    id: str
    organization_id: str
    resource_type: str
    limit_value: float
    used_value: float
    unit: str
    period: str
    alert_threshold: float
    status: str
    usage_percent: float = Field(default=0.0, description="使用百分比")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuotaCheckRequest(BaseModel):
    """配额检查请求"""
    organization_id: str = Field(description="组织 ID")
    resource_type: str = Field(description="资源类型")
    requested_amount: float = Field(gt=0, description="请求量")


class QuotaCheckResponse(BaseModel):
    """配额检查响应"""
    allowed: bool = Field(description="是否允许")
    organization_id: str
    resource_type: str
    limit_value: float
    used_value: float
    remaining: float
    usage_percent: float
    message: str = Field(default="", description="提示信息")


class QuotaUsageLogResponse(BaseModel):
    """配额使用记录响应"""
    id: str
    quota_id: str
    delta: float
    before_value: float
    after_value: float
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MonthlyReportRequest(BaseModel):
    """月度报告请求"""
    period: str = Field(description="账期 YYYY-MM")
    organization_id: Optional[str] = Field(default=None, description="指定组织 ID")
