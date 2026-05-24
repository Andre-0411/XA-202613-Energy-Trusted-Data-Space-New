"""
计算资源配额 Schema
ComputeQuota / ComputeQuotaUsage / ComputeQuotaRequest 相关 Pydantic 模型
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 配额 ====================


class ComputeQuotaResponse(BaseModel):
    """计算配额响应"""
    id: str = Field(description="配额 ID")
    organization_id: str = Field(description="所属组织")
    user_id: Optional[str] = Field(default=None, description="所属用户（null=组织级）")
    resource_type: str = Field(description="资源类型")
    limit_value: float = Field(description="配额上限")
    used_value: float = Field(description="已使用量")
    unit: str = Field(description="计量单位")
    period: str = Field(description="配额周期")
    alert_threshold: float = Field(description="告警阈值百分比")
    status: str = Field(description="配额状态")
    priority: int = Field(description="配额优先级")
    metadata_: Optional[dict] = Field(default=None, description="扩展配置")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComputeQuotaUpdate(BaseModel):
    """更新计算配额"""
    limit_value: Optional[float] = Field(default=None, ge=0, description="配额上限")
    alert_threshold: Optional[float] = Field(
        default=None, ge=0, le=100, description="告警阈值百分比"
    )
    priority: Optional[int] = Field(default=None, ge=1, le=10, description="配额优先级")
    status: Optional[str] = Field(default=None, description="配额状态")
    metadata_: Optional[dict] = Field(default=None, description="扩展配置")


class ComputeQuotaCheckRequest(BaseModel):
    """配额检查请求"""
    organization_id: str = Field(description="组织 ID")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    resource_type: str = Field(description="资源类型")
    required_amount: float = Field(gt=0, description="需要的资源量")


class ComputeQuotaCheckResponse(BaseModel):
    """配额检查响应"""
    allowed: bool = Field(description="是否允许")
    resource_type: str = Field(description="资源类型")
    limit_value: float = Field(description="配额上限")
    used_value: float = Field(description="已使用量")
    available: float = Field(description="可用量")
    usage_percent: float = Field(description="使用率百分比")
    is_over_threshold: bool = Field(description="是否超过告警阈值")


class ComputeQuotaConsumeRequest(BaseModel):
    """配额消耗请求"""
    organization_id: str = Field(description="组织 ID")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    resource_type: str = Field(description="资源类型")
    amount: float = Field(gt=0, description="消耗量")
    task_id: Optional[str] = Field(default=None, description="关联任务 ID")
    reason: Optional[str] = Field(default=None, description="消耗原因")


class ComputeQuotaReleaseRequest(BaseModel):
    """配额释放请求"""
    organization_id: str = Field(description="组织 ID")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    resource_type: str = Field(description="资源类型")
    amount: float = Field(gt=0, description="释放量")
    task_id: Optional[str] = Field(default=None, description="关联任务 ID")
    reason: Optional[str] = Field(default=None, description="释放原因")


# ==================== 使用记录 ====================


class ComputeQuotaUsageResponse(BaseModel):
    """配额使用记录响应"""
    id: str = Field(description="记录 ID")
    quota_id: str = Field(description="配额 ID")
    task_id: Optional[str] = Field(default=None, description="关联任务 ID")
    delta: float = Field(description="变更量")
    before_value: float = Field(description="变更前值")
    after_value: float = Field(description="变更后值")
    reason: Optional[str] = Field(default=None, description="变更原因")
    operator_id: Optional[str] = Field(default=None, description="操作者")
    recorded_at: datetime

    model_config = {"from_attributes": True}


# ==================== 配额申请 ====================


class ComputeQuotaRequestCreate(BaseModel):
    """配额提升申请"""
    quota_id: str = Field(description="原配额 ID")
    organization_id: str = Field(description="申请组织")
    requested_limit: float = Field(gt=0, description="申请配额上限")
    reason: str = Field(min_length=10, max_length=2000, description="申请理由")


class ComputeQuotaRequestReview(BaseModel):
    """配额申请审批"""
    status: str = Field(description="审批结果: approved/rejected")
    review_comment: Optional[str] = Field(default=None, max_length=2000, description="审批意见")


class ComputeQuotaRequestResponse(BaseModel):
    """配额申请响应"""
    id: str = Field(description="申请 ID")
    quota_id: str = Field(description="原配额 ID")
    organization_id: str = Field(description="申请组织")
    requester_id: str = Field(description="申请人")
    current_limit: float = Field(description="当前配额上限")
    requested_limit: float = Field(description="申请配额上限")
    reason: str = Field(description="申请理由")
    status: str = Field(description="申请状态")
    reviewer_id: Optional[str] = Field(default=None, description="审批人")
    review_comment: Optional[str] = Field(default=None, description="审批意见")
    reviewed_at: Optional[datetime] = Field(default=None, description="审批时间")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComputeQuotaStatsResponse(BaseModel):
    """配额统计响应"""
    organization_id: str = Field(description="组织 ID")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    quotas: list[ComputeQuotaResponse] = Field(description="配额列表")
    total_usage_percent: float = Field(description="总体使用率")
    alerts: list[str] = Field(default_factory=list, description="告警列表")
