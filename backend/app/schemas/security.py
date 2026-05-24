"""
安全 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """创建策略"""
    name: str = Field(max_length=200, description="策略名称")
    policy_type: str = Field(description="类型: RBAC/ABAC")
    rules: dict = Field(description="策略规则")
    priority: int = Field(default=0, description="优先级")


class PolicyEvaluateRequest(BaseModel):
    """策略评估请求"""
    subject_did: str = Field(description="主体 DID")
    resource_type: str = Field(description="资源类型")
    resource_id: str = Field(description="资源 ID")
    action: str = Field(description="请求动作")
    context: Optional[dict] = Field(default=None, description="ABAC 上下文")


class DidCreate(BaseModel):
    """创建 DID"""
    method: str = Field(default="did:fisco", description="DID 方法")
    public_key: str = Field(description="SM2 公钥")
    controller: Optional[str] = Field(default=None, description="控制者 DID")


class DidResponse(BaseModel):
    """DID 响应"""
    id: str
    did: str
    method: str
    document: dict
    controller: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VcIssueRequest(BaseModel):
    """签发 VC 请求"""
    issuer_did: str = Field(description="签发方 DID")
    subject_did: str = Field(description="持有方 DID")
    vc_type: str = Field(description="凭证类型")
    claims: dict = Field(description="声明内容")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")


class VcVerifyRequest(BaseModel):
    """验证 VC 请求"""
    vc_id: str = Field(description="凭证 ID")
    vc_data: Optional[dict] = Field(default=None, description="凭证数据")


class KeyGenerateRequest(BaseModel):
    """生成密钥请求"""
    algorithm: str = Field(description="算法: SM2/SM4/AES")
    hierarchy_level: str = Field(description="层级: master/kek/dek")
    purpose: str = Field(description="用途")
    parent_key_id: Optional[str] = Field(default=None, description="父密钥 ID")


class ThreatResponse(BaseModel):
    """威胁事件响应"""
    id: str
    threat_type: str
    severity: str
    source: Optional[str] = None
    description: str
    indicators: Optional[dict] = None
    affected_resources: Optional[list[str]] = None
    status: str
    assigned_to: Optional[str] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ZkpProveRequest(BaseModel):
    """ZKP 证明请求"""
    proof_type: str = Field(description="证明类型: groth16/bbs/bulletproofs")
    circuit_id: Optional[str] = Field(default=None, description="电路 ID")
    private_input: dict = Field(description="私有输入")
    public_input: dict = Field(description="公开输入")
