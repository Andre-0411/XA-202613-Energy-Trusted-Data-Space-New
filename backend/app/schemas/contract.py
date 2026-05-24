"""
合约 Schema
Contract / ContractAmendment
"""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 合约 ====================

class ContractCreate(BaseModel):
    """创建合约"""
    title: str = Field(description="合约标题")
    contract_type: str = Field(description="合约类型: data_subscription/product_subscription/joint_compute/custom")
    party_b_org_id: str = Field(description="乙方组织 ID")
    party_b_user_id: Optional[str] = Field(default=None, description="乙方用户 ID")
    related_subscription_id: Optional[str] = Field(default=None, description="关联订阅 ID")
    related_product_id: Optional[str] = Field(default=None, description="关联产品 ID")
    content: str = Field(description="合约正文")
    terms: dict = Field(default_factory=dict, description="合约条款")
    pricing: dict = Field(default_factory=dict, description="定价信息")
    effective_date: Optional[str] = Field(default=None, description="生效日期 ISO 8601")
    expiration_date: Optional[str] = Field(default=None, description="到期日期 ISO 8601")


class PricingConfig(BaseModel):
    """定价值配置"""
    pricing_model: str = Field(default="fixed", description="定价模式: fixed/subscription/per_usage/tiered")
    price: float = Field(default=0.0, description="价格")
    currency: str = Field(default="CNY", description="货币")
    billing_cycle: Optional[str] = Field(default=None, description="计费周期: monthly/quarterly/yearly")
    config: dict = Field(default_factory=dict, description="扩展配置")


class ContractAmendment(BaseModel):
    """合约变更/终止申请"""
    amendment_type: str = Field(default="change", description="变更类型: change/terminate")
    reason: str = Field(description="变更原因")
    changes: dict = Field(default_factory=dict, description="变更内容")


class AmendmentReview(BaseModel):
    """审核合约变更"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")


class ContractUpdate(BaseModel):
    """更新合约"""
    title: Optional[str] = Field(default=None, description="合约标题")
    content: Optional[str] = Field(default=None, description="合约正文")
    terms: Optional[dict] = Field(default=None, description="合约条款")
    pricing: Optional[dict] = Field(default=None, description="定价信息")
    effective_date: Optional[str] = Field(default=None, description="生效日期")
    expiration_date: Optional[str] = Field(default=None, description="到期日期")
    status: Optional[str] = Field(default=None, description="状态")


class ContractApproval(BaseModel):
    """审批合约"""
    action: str = Field(description="审批动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审批意见")


class ContractSign(BaseModel):
    """签署合约"""
    signature_data: str = Field(default="", description="签名数据（SM2）")
    blockchain_enabled: bool = Field(default=False, description="是否上链存证")


class ContractResponse(BaseModel):
    """合约响应"""
    id: str = Field(description="合约 ID")
    contract_no: str = Field(description="合约编号")
    title: str = Field(description="标题")
    contract_type: str = Field(description="合约类型")
    party_a_org_id: str = Field(description="甲方组织 ID")
    party_a_user_id: str = Field(description="甲方用户 ID")
    party_b_org_id: str = Field(description="乙方组织 ID")
    party_b_user_id: Optional[str] = Field(default=None)
    related_subscription_id: Optional[str] = Field(default=None)
    related_product_id: Optional[str] = Field(default=None)
    content: str = Field(description="合约正文")
    terms: dict = Field(default_factory=dict)
    pricing: dict = Field(default_factory=dict)
    effective_date: Optional[str] = Field(default=None)
    expiration_date: Optional[str] = Field(default=None)
    blockchain_tx_hash: Optional[str] = Field(default=None)
    blockchain_contract_address: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    created_by: str = Field(description="创建者 ID")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    amendments: List["ContractAmendmentResponse"] = Field(default_factory=list)


# ==================== 合约修订 ====================

class ContractAmendmentCreate(BaseModel):
    """创建合约修订"""
    contract_id: str = Field(description="合约 ID")
    reason: str = Field(description="修订原因")
    changes: dict = Field(default_factory=dict, description="变更内容")
    new_terms: dict = Field(default_factory=dict, description="变更后条款")


class ContractAmendmentReview(BaseModel):
    """审核合约修订"""
    status: str = Field(description="审核结果: approved/rejected")
    review_comment: Optional[str] = Field(default=None, description="审核意见")


class ContractAmendmentResponse(BaseModel):
    """合约修订响应"""
    id: str = Field(description="修订 ID")
    contract_id: str = Field(description="合约 ID")
    amendment_no: int = Field(description="修订序号")
    reason: str = Field(description="修订原因")
    changes: dict = Field(default_factory=dict)
    previous_terms: dict = Field(default_factory=dict)
    new_terms: dict = Field(default_factory=dict)
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    created_by: str = Field(description="创建者 ID")
    created_at: str = Field(description="创建时间")


# 重建引用
ContractResponse.model_rebuild()
