"""
HSM 安全模块 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class HsmKeyGenerateRequest(BaseModel):
    """HSM 密钥生成请求"""
    algorithm: str = Field(description="算法: SM2/SM4/RSA")
    key_size: int = Field(default=2048, description="密钥长度（RSA 使用，SM4 固定 128 位，SM2 固定 256 位）")
    hierarchy: str = Field(default="user", description="密钥层级: root/org/user")
    purpose: str = Field(default="general", description="密钥用途: sign/encrypt/general")
    org_id: Optional[str] = Field(default=None, description="所属组织 ID")
    description: Optional[str] = Field(default=None, description="密钥描述")


class HsmKeyResponse(BaseModel):
    """HSM 密钥响应"""
    key_id: str = Field(description="密钥唯一标识")
    algorithm: str = Field(description="算法类型")
    hierarchy: str = Field(description="密钥层级")
    purpose: str = Field(description="密钥用途")
    org_id: Optional[str] = None
    description: Optional[str] = None
    status: str = Field(description="状态: active/revoked/expired")
    public_key: Optional[str] = Field(default=None, description="公钥（非对称算法）")
    has_private_key: bool = Field(default=True, description="是否包含私钥")
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class HsmSignRequest(BaseModel):
    """HSM 签名请求"""
    key_id: str = Field(description="密钥 ID")
    data: str = Field(description="待签名数据（Base64 编码）")


class HsmSignResponse(BaseModel):
    """HSM 签名响应"""
    key_id: str
    algorithm: str
    signature: str = Field(description="签名值（十六进制）")
    data_hash: str = Field(description="数据哈希")
    signed_at: datetime


class HsmVerifyRequest(BaseModel):
    """HSM 验签请求"""
    key_id: str = Field(description="密钥 ID")
    data: str = Field(description="原始数据（Base64 编码）")
    signature: str = Field(description="签名值（十六进制）")


class HsmVerifyResponse(BaseModel):
    """HSM 验签响应"""
    key_id: str
    algorithm: str
    is_valid: bool
    verified_at: datetime


class HsmEncryptRequest(BaseModel):
    """HSM 加密请求"""
    key_id: str = Field(description="密钥 ID")
    plaintext: str = Field(description="明文数据（Base64 编码）")


class HsmEncryptResponse(BaseModel):
    """HSM 加密响应"""
    key_id: str
    algorithm: str
    ciphertext: str = Field(description="密文（十六进制）")
    encrypted_at: datetime


class HsmDecryptRequest(BaseModel):
    """HSM 解密请求"""
    key_id: str = Field(description="密钥 ID")
    ciphertext: str = Field(description="密文（十六进制）")


class HsmDecryptResponse(BaseModel):
    """HSM 解密响应"""
    key_id: str
    algorithm: str
    plaintext: str = Field(description="明文数据（Base64 编码）")
    decrypted_at: datetime


class HsmAuditLogResponse(BaseModel):
    """HSM 审计日志响应"""
    id: str
    key_id: str
    operation: str
    user_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    status: str = Field(description="操作状态: success/failure")
    created_at: datetime

    model_config = {"from_attributes": True}
