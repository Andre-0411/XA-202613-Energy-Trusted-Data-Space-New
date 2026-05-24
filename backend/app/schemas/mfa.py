"""
MFA (多因素认证) Schema
TOTP 密钥生成、验证、备份码管理
"""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


class MfaSetupRequest(BaseModel):
    """MFA 设置请求"""
    user_id: str = Field(description="用户 ID")
    method: str = Field(default="totp", description="MFA 方法: totp/sms/email")


class MfaSetupResponse(BaseModel):
    """MFA 设置响应"""
    secret: str = Field(description="TOTP 密钥")
    qr_code_url: str = Field(description="二维码 URL")
    backup_codes: List[str] = Field(description="备份码列表")
    method: str = Field(description="MFA 方法")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")


class MfaVerifyRequest(BaseModel):
    """MFA 验证请求"""
    user_id: str = Field(description="用户 ID")
    code: str = Field(description="MFA 验证码")
    session_id: Optional[str] = Field(default=None, description="MFA 会话 ID")


class MfaVerifyResponse(BaseModel):
    """MFA 验证响应"""
    verified: bool = Field(description="验证结果")
    session_id: Optional[str] = Field(default=None, description="会话 ID")
    message: str = Field(description="消息")


class MfaEnableRequest(BaseModel):
    """MFA 启用请求"""
    user_id: str = Field(description="用户 ID")
    code: str = Field(description="验证当前 TOTP 码以确认启用")


class MfaDisableRequest(BaseModel):
    """MFA 禁用请求"""
    user_id: str = Field(description="用户 ID")
    password: str = Field(description="用户密码确认")
    code: Optional[str] = Field(default=None, description="MFA 验证码")


class MfaStatusResponse(BaseModel):
    """MFA 状态响应"""
    user_id: str = Field(description="用户 ID")
    enabled: bool = Field(description="是否启用 MFA")
    method: Optional[str] = Field(default=None, description="MFA 方法")
    backup_codes_remaining: int = Field(default=0, description="剩余备份码数量")
    last_verified_at: Optional[datetime] = Field(default=None, description="最后验证时间")


class BackupCodeVerifyRequest(BaseModel):
    """备份码验证请求"""
    user_id: str = Field(description="用户 ID")
    backup_code: str = Field(description="备份码")


class MfaBackupCodesResponse(BaseModel):
    """备份码响应"""
    backup_codes: List[str] = Field(description="备份码列表")
    regenerated_at: datetime = Field(default_factory=datetime.utcnow, description="重新生成时间")
