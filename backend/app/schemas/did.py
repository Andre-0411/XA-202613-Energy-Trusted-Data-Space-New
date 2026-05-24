"""
DID（去中心化标识符）Schema
DID 文档、创建请求、VC 签发/验证
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class VerificationMethod(BaseModel):
    """验证方法"""
    id: str = Field(description="验证方法 ID")
    type: str = Field(description="验证方法类型: SM2VerificationKey2021")
    controller: str = Field(description="控制者 DID")
    publicKeyHex: str = Field(description="SM2 公钥（十六进制）")


class ServiceEndpoint(BaseModel):
    """服务端点"""
    id: str = Field(description="服务端点 ID")
    type: str = Field(description="服务类型")
    serviceEndpoint: str = Field(description="服务 URL")


class DidDocument(BaseModel):
    """W3C DID Document"""
    context: list[str] = Field(default=["https://www.w3.org/ns/did/v1"], description="JSON-LD 上下文")
    id: str = Field(description="DID 标识符")
    controller: Optional[str] = Field(default=None, description="控制者 DID")
    verificationMethod: list[VerificationMethod] = Field(default_factory=list, description="验证方法列表")
    authentication: list[str] = Field(default_factory=list, description="认证方法 ID 列表")
    assertionMethod: Optional[list[str]] = Field(default=None, description="声明方法 ID 列表")
    service: Optional[list[ServiceEndpoint]] = Field(default=None, description="服务端点列表")
    created: Optional[str] = Field(default=None, description="创建时间")
    updated: Optional[str] = Field(default=None, description="更新时间")
    deactivated: Optional[bool] = Field(default=None, description="是否已停用")

    model_config = {"from_attributes": True}


class DidCreateRequest(BaseModel):
    """创建 DID 请求"""
    method: str = Field(default="did:tds", description="DID 方法: did:tds")
    public_key: str = Field(description="SM2 公钥（十六进制）")
    controller: Optional[str] = Field(default=None, description="控制者 DID")
    service_endpoints: Optional[list[ServiceEndpoint]] = Field(default=None, description="服务端点列表")


class DidResponse(BaseModel):
    """DID 响应"""
    id: Optional[str] = Field(default=None, description="数据库 ID")
    did: str = Field(description="DID 标识符")
    method: str = Field(description="DID 方法")
    document: dict = Field(description="DID Document")
    controller: Optional[str] = Field(default=None, description="控制者 DID")
    status: str = Field(default="active", description="状态: active/deactivated")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")

    model_config = {"from_attributes": True}


class DidUpdateRequest(BaseModel):
    """更新 DID Document 请求"""
    service_endpoints: Optional[list[ServiceEndpoint]] = Field(default=None, description="新的服务端点列表")
    add_verification_method: Optional[list[VerificationMethod]] = Field(default=None, description="添加的验证方法")
    remove_verification_method: Optional[list[str]] = Field(default=None, description="移除的验证方法 ID 列表")


class VcCredentialSubject(BaseModel):
    """VC 凭证主体"""
    id: str = Field(description="持有方 DID")
    claims: dict = Field(description="声明内容")


class VcProof(BaseModel):
    """VC 证明"""
    type: str = Field(description="证明类型: SM2Signature2021")
    created: str = Field(description="创建时间")
    proofPurpose: str = Field(description="证明目的: assertionMethod")
    verificationMethod: str = Field(description="验证方法 ID")
    signature: str = Field(description="SM2 签名值")


class VerifiableCredential(BaseModel):
    """W3C Verifiable Credential v2.0"""
    context: list[str] = Field(description="JSON-LD 上下文")
    id: str = Field(description="VC ID")
    type: list[str] = Field(description="凭证类型")
    issuer: str = Field(description="签发方 DID")
    subject: str = Field(description="持有方 DID")
    issuanceDate: str = Field(description="签发日期")
    expirationDate: Optional[str] = Field(default=None, description="过期日期")
    credentialSubject: dict = Field(description="凭证主体")
    credentialStatus: Optional[dict] = Field(default=None, description="凭证状态")
    proof: Optional[VcProof] = Field(default=None, description="证明")


class VcIssueRequest(BaseModel):
    """签发 VC 请求"""
    issuer_did: str = Field(description="签发方 DID")
    subject_did: str = Field(description="持有方 DID")
    vc_type: str = Field(description="凭证类型")
    claims: dict = Field(description="声明内容")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")
    credential_status_type: Optional[str] = Field(default=None, description="凭证状态类型: revocationList2020")


class VcVerifyRequest(BaseModel):
    """验证 VC 请求"""
    vc_id: str = Field(description="凭证 ID")
    vc_data: Optional[dict] = Field(default=None, description="凭证数据")


class VcVerifyResult(BaseModel):
    """VC 验证结果"""
    vc_id: str = Field(description="凭证 ID")
    signature_valid: bool = Field(description="签名是否有效")
    not_expired: bool = Field(description="是否未过期")
    not_revoked: bool = Field(description="是否未撤销")
    overall_valid: bool = Field(description="综合验证结果")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")
    verified_at: Optional[str] = Field(default=None, description="验证时间")


class VcRevokeRequest(BaseModel):
    """撤销 VC 请求"""
    reason: Optional[str] = Field(default=None, description="撤销原因")
