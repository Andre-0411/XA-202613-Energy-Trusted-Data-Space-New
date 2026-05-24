"""
审批工作流 Schema
ApprovalWorkflow / ApprovalRecord
"""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 工作流模板 ====================

class WorkflowCreate(BaseModel):
    """创建工作流模板"""
    name: str = Field(description="工作流名称")
    description: Optional[str] = Field(default=None, description="描述")
    workflow_type: str = Field(description="工作流类型: certification/subscription/product_publish/product_unpublish/demand_claim/contract")
    steps: list = Field(default_factory=list, description="审批步骤定义")


class WorkflowUpdate(BaseModel):
    """更新工作流模板"""
    name: Optional[str] = Field(default=None, description="工作流名称")
    description: Optional[str] = Field(default=None, description="描述")
    steps: Optional[list] = Field(default=None, description="审批步骤定义")
    status: Optional[str] = Field(default=None, description="状态")


class WorkflowResponse(BaseModel):
    """工作流模板响应"""
    id: str = Field(description="工作流 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    workflow_type: str = Field(description="类型")
    organization_id: Optional[str] = Field(default=None)
    steps: list = Field(default_factory=list)
    is_system: bool = Field(default=False)
    status: str = Field(description="状态")
    created_by: str = Field(description="创建者 ID")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 审批记录 ====================

class ApprovalRecordCreate(BaseModel):
    """发起审批"""
    workflow_id: str = Field(description="工作流模板 ID")
    business_type: str = Field(description="业务类型")
    business_id: str = Field(description="业务对象 ID")
    approval_data: dict = Field(default_factory=dict, description="审批提交数据")


class ApprovalAction(BaseModel):
    """审批操作"""
    action: str = Field(description="操作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审批意见")


class WorkflowApproval(BaseModel):
    """审批通过"""
    comment: Optional[str] = Field(default=None, description="审批意见")


class WorkflowRejection(BaseModel):
    """审批拒绝"""
    comment: Optional[str] = Field(default=None, description="拒绝原因")


class ApprovalRecordResponse(BaseModel):
    """审批记录响应"""
    id: str = Field(description="记录 ID")
    workflow_id: str = Field(description="工作流 ID")
    business_type: str = Field(description="业务类型")
    business_id: str = Field(description="业务对象 ID")
    applicant_id: str = Field(description="申请人 ID")
    current_step: int = Field(description="当前步骤")
    total_steps: int = Field(description="总步骤数")
    approval_data: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[str] = Field(default=None)
    reject_reason: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
