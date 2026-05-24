"""
国密算法 Schema
SM2 / SM3 / SM4 密钥对、签名、加密结果
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class KeyPair(BaseModel):
    """SM2 密钥对"""
    private_key: str = Field(description="SM2 私钥（十六进制）")
    public_key: str = Field(description="SM2 公钥（十六进制）")
    algorithm: str = Field(default="SM2", description="算法类型")
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class Signature(BaseModel):
    """签名结果"""
    algorithm: str = Field(description="算法类型")
    operation: str = Field(description="操作类型: sign/verify")
    signature: Optional[str] = Field(default=None, description="签名值（十六进制）")
    is_valid: Optional[bool] = Field(default=None, description="验签结果")
    data_hash: Optional[str] = Field(default=None, description="数据 SM3 哈希")
    signed_at: Optional[str] = Field(default=None, description="签名时间")
    verified_at: Optional[str] = Field(default=None, description="验签时间")


class EncryptResult(BaseModel):
    """加密结果"""
    algorithm: str = Field(description="算法类型")
    operation: str = Field(description="操作类型: encrypt/decrypt")
    ciphertext: Optional[str] = Field(default=None, description="密文（十六进制）")
    plaintext: Optional[str] = Field(default=None, description="明文")
    iv: Optional[str] = Field(default=None, description="初始化向量（ZUC）")
    encrypted_at: Optional[str] = Field(default=None, description="加密时间")
    decrypted_at: Optional[str] = Field(default=None, description="解密时间")


class HashResult(BaseModel):
    """哈希结果"""
    algorithm: str = Field(default="SM3", description="算法类型")
    operation: str = Field(default="hash", description="操作类型")
    hash: str = Field(description="哈希值（十六进制）")
    hashed_at: str = Field(description="哈希时间")


class Sm2SignRequest(BaseModel):
    """SM2 签名请求"""
    private_key: str = Field(description="SM2 私钥（十六进制）")
    public_key: str = Field(description="SM2 公钥（十六进制）")
    data: str = Field(description="待签名数据")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class Sm2VerifyRequest(BaseModel):
    """SM2 验签请求"""
    public_key: str = Field(description="SM2 公钥（十六进制）")
    data: str = Field(description="原始数据")
    signature: str = Field(description="签名值（十六进制）")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class Sm2EncryptRequest(BaseModel):
    """SM2 加密请求"""
    public_key: str = Field(description="SM2 公钥（十六进制）")
    plaintext: str = Field(description="明文")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class Sm2DecryptRequest(BaseModel):
    """SM2 解密请求"""
    private_key: str = Field(description="SM2 私钥（十六进制）")
    public_key: str = Field(description="SM2 公钥（十六进制）")
    ciphertext: str = Field(description="密文")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class Sm3HashRequest(BaseModel):
    """SM3 哈希请求"""
    data: str = Field(description="待哈希数据")


class Sm4EncryptRequest(BaseModel):
    """SM4 加密请求"""
    key: str = Field(description="SM4 密钥（十六进制，32字符=16字节）")
    plaintext: str = Field(description="明文")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class Sm4DecryptRequest(BaseModel):
    """SM4 解密请求"""
    key: str = Field(description="SM4 密钥（十六进制）")
    ciphertext: str = Field(description="密文")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class Sm9SignRequest(BaseModel):
    """SM9 签名请求"""
    master_private_key: str = Field(description="SM9 主私钥")
    data: str = Field(description="待签名数据")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class Sm9VerifyRequest(BaseModel):
    """SM9 验签请求"""
    master_public_key: str = Field(description="SM9 主公钥")
    data: str = Field(description="原始数据")
    signature: str = Field(description="签名值")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")


class ZucEncryptRequest(BaseModel):
    """ZUC 加密请求"""
    key: str = Field(description="ZUC 密钥（十六进制）")
    iv: str = Field(description="初始化向量（十六进制）")
    plaintext: str = Field(description="明文")
    key_id: Optional[str] = Field(default=None, description="关联密钥 ID")
