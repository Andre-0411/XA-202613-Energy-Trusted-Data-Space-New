"""
需求 Schema
Demand / DemandClaim
"""
from typing import Optional, List
from datetime import datetime, date

from pydantic import BaseModel, Field


# ==================== 需求 ====================

class DemandCreate(BaseModel):
    """创建需求"""
    demand_type: str = Field(description="需求类型: data_product/custom_compute/joint_model/data_access")
    title: str = Field(description="需求标题")
    description: str = Field(description="需求描述")
    technical_requirements: dict = Field(default_factory=dict, description="技术需求")
    budget_range: Optional[str] = Field(default=None, description="预算范围")
    deadline: Optional[str] = Field(default=None, description="截止日期 ISO 8601")
    security_risk_assessment: dict = Field(default_factory=dict, description="安全风险评估")


class DemandUpdate(BaseModel):
    """更新需求"""
    demand_type: Optional[str] = Field(default=None, description="需求类型")
    title: Optional[str] = Field(default=None, description="需求标题")
    description: Optional[str] = Field(default=None, description="需求描述")
    technical_requirements: Optional[dict] = Field(default=None, description="技术需求")
    budget_range: Optional[str] = Field(default=None, description="预算范围")
    deadline: Optional[str] = Field(default=None, description="截止日期")
    security_risk_assessment: Optional[dict] = Field(default=None, description="安全风险评估")
    status: Optional[str] = Field(default=None, description="状态")


class DemandPublish(BaseModel):
    """发布需求"""
    pass  # 只需改变状态，无额外参数


class DemandStatusUpdate(BaseModel):
    """更新需求状态"""
    status: str = Field(description="目标状态: open/closed/suspended")


class RiskAssessment(BaseModel):
    """安全风险评估"""
    risk_level: str = Field(default="medium", description="风险等级: low/medium/high/critical")
    assessment_result: dict = Field(default_factory=dict, description="评估结果")
    mitigation_measures: list = Field(default_factory=list, description="缓解措施")
    comment: Optional[str] = Field(default=None, description="评估备注")


class DemandResponse(BaseModel):
    """需求响应"""
    id: str = Field(description="需求 ID")
    demand_type: str = Field(description="需求类型")
    title: str = Field(description="标题")
    description: str = Field(description="描述")
    technical_requirements: dict = Field(default_factory=dict)
    budget_range: Optional[str] = Field(default=None)
    deadline: Optional[str] = Field(default=None)
    organization_id: str = Field(description="发布组织 ID")
    publisher_id: str = Field(description="发布者 ID")
    security_risk_assessment: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    claimed_by_org: Optional[str] = Field(default=None)
    claimed_by_user: Optional[str] = Field(default=None)
    claimed_at: Optional[str] = Field(default=None)
    published_at: Optional[str] = Field(default=None)
    closed_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    claims: List["DemandClaimResponse"] = Field(default_factory=list)


# ==================== 需求认领 ====================

class DemandClaimCreate(BaseModel):
    """创建需求认领"""
    demand_id: str = Field(description="需求 ID")
    proposal: Optional[str] = Field(default=None, description="方案提议")


class DemandClaimReview(BaseModel):
    """审核需求认领"""
    status: str = Field(description="审核结果: approved/rejected")


class DemandClaimResponse(BaseModel):
    """需求认领响应"""
    id: str = Field(description="认领 ID")
    demand_id: str = Field(description="需求 ID")
    claimer_id: str = Field(description="认领者 ID")
    claimer_org_id: str = Field(description="认领者组织 ID")
    proposal: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    reviewed_by: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")


# 重建引用
DemandResponse.model_rebuild()
