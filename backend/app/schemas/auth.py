"""
认证 Schema
LoginRequest / MfaVerifyRequest / TokenResponse / SessionResponse
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class PasswordLoginRequest(BaseModel):
    """密码登录请求"""
    username: str = Field(description="用户名")
    password: str = Field(description="密码")
    auth_type: str = Field(default="password", description="认证类型: password")


class DidLoginRequest(BaseModel):
    """DID 登录请求"""
    did: str = Field(description="用户 DID")
    signature: str = Field(description="SM2 签名")
    challenge: str = Field(description="挑战值")
    auth_type: str = Field(default="did", description="认证类型: did")


class CertificateLoginRequest(BaseModel):
    """SM2 证书登录请求"""
    certificate: str = Field(description="SM2 证书 PEM")
    signature: str = Field(description="签名值")
    challenge: str = Field(description="挑战值")
    auth_type: str = Field(default="certificate", description="认证类型: certificate")


class LoginRequest(BaseModel):
    """统一登录请求（DID/密码/SM2证书三种模式）"""
    username: Optional[str] = Field(default=None, description="用户名(密码模式)")
    password: Optional[str] = Field(default=None, description="密码(密码模式)")
    did: Optional[str] = Field(default=None, description="DID(DID模式)")
    signature: Optional[str] = Field(default=None, description="签名(DID/证书模式)")
    challenge: Optional[str] = Field(default=None, description="挑战值(DID/证书模式)")
    certificate: Optional[str] = Field(default=None, description="SM2证书(证书模式)")
    auth_type: str = Field(default="password", description="认证类型: password/did/certificate")


class MfaVerifyRequest(BaseModel):
    """MFA 验证请求"""
    code: str = Field(description="MFA 验证码")
    user_id: str = Field(description="用户 ID")
    session_id: Optional[str] = Field(default=None, description="MFA 会话 ID")


class UserInfo(BaseModel):
    """用户基本信息"""
    user_id: str = Field(description="用户ID")
    username: str = Field(description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱")
    phone: Optional[str] = Field(default=None, description="手机号")
    role: str = Field(description="角色")
    did: Optional[str] = Field(default=None, description="DID")
    organization_id: Optional[str] = Field(default=None, description="组织ID")
    department_id: Optional[str] = Field(default=None, description="部门ID")
    status: str = Field(default="active", description="状态")
    permissions: list[str] = Field(default_factory=list, description="权限列表")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间(秒)")
    mfa_required: bool = Field(default=False, description="是否需要 MFA")
    mfa_session_id: Optional[str] = Field(default=None, description="MFA 会话 ID")
    user: Optional[UserInfo] = Field(default=None, description="用户信息")


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str = Field(description="刷新令牌")


class SessionResponse(BaseModel):
    """会话响应"""
    user_id: str = Field(description="用户 ID")
    username: str = Field(description="用户名")
    did: Optional[str] = Field(default=None, description="用户 DID")
    role: str = Field(description="角色")
    permissions: list[str] = Field(default_factory=list, description="权限列表")
    organization_id: str = Field(description="组织 ID")
    organization_name: Optional[str] = Field(default=None, description="组织名称")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")
