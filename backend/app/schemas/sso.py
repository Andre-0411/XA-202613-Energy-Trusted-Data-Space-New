"""
SSO (单点登录) Schema
OAuth2.0 / SAML 2.0 统一认证
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class SSOProviderConfig(BaseModel):
    """SSO 提供者配置"""
    provider_id: str = Field(description="提供者 ID")
    name: str = Field(description="提供者名称")
    protocol: str = Field(description="协议: oauth2/saml2/oidc")
    client_id: Optional[str] = Field(default=None, description="OAuth2 Client ID")
    client_secret: Optional[str] = Field(default=None, description="OAuth2 Client Secret")
    authorize_url: Optional[str] = Field(default=None, description="授权 URL")
    token_url: Optional[str] = Field(default=None, description="Token URL")
    userinfo_url: Optional[str] = Field(default=None, description="用户信息 URL")
    redirect_uri: Optional[str] = Field(default=None, description="回调 URL")
    scopes: List[str] = Field(default_factory=lambda: ["openid", "profile", "email"], description="授权范围")
    metadata_url: Optional[str] = Field(default=None, description="SAML/OIDC 元数据 URL")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")


class SSOAuthorizeRequest(BaseModel):
    """SSO 授权请求"""
    provider_id: str = Field(description="提供者 ID")
    redirect_uri: Optional[str] = Field(default=None, description="回调 URL")
    state: Optional[str] = Field(default=None, description="状态参数")


class SSOAuthorizeResponse(BaseModel):
    """SSO 授权响应"""
    authorize_url: str = Field(description="授权 URL")
    state: str = Field(description="状态参数")


class SSOTokenRequest(BaseModel):
    """SSO Token 交换请求"""
    provider_id: str = Field(description="提供者 ID")
    code: str = Field(description="授权码")
    state: Optional[str] = Field(default=None, description="状态参数")
    redirect_uri: Optional[str] = Field(default=None, description="回调 URL")


class SSOTokenResponse(BaseModel):
    """SSO Token 响应"""
    access_token: str = Field(description="访问令牌")
    refresh_token: Optional[str] = Field(default=None, description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(description="过期时间(秒)")
    id_token: Optional[str] = Field(default=None, description="ID Token (OIDC)")
    user_info: Optional[Dict[str, Any]] = Field(default=None, description="用户信息")


class SSOUserInfo(BaseModel):
    """SSO 用户信息"""
    provider_id: str = Field(description="提供者 ID")
    sub: str = Field(description="Subject ID")
    name: Optional[str] = Field(default=None, description="姓名")
    email: Optional[str] = Field(default=None, description="邮箱")
    picture: Optional[str] = Field(default=None, description="头像 URL")
    raw_claims: Dict[str, Any] = Field(default_factory=dict, description="原始声明")


class SAMLAssertionRequest(BaseModel):
    """SAML 断言请求"""
    saml_response: str = Field(description="SAML Response (Base64)")
    relay_state: Optional[str] = Field(default=None, description="RelayState")


class SAMLAssertionResponse(BaseModel):
    """SAML 断言解析响应"""
    name_id: str = Field(description="NameID")
    session_index: Optional[str] = Field(default=None, description="SessionIndex")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="属性")
    issuer: str = Field(description="Issuer")
    not_on_or_after: Optional[datetime] = Field(default=None, description="有效期")


class SSOSessionInfo(BaseModel):
    """SSO 会话信息"""
    session_id: str = Field(description="会话 ID")
    user_id: str = Field(description="用户 ID")
    provider_id: str = Field(description="提供者 ID")
    created_at: datetime = Field(description="创建时间")
    expires_at: datetime = Field(description="过期时间")
    ip_address: Optional[str] = Field(default=None, description="IP 地址")
    user_agent: Optional[str] = Field(default=None, description="User Agent")
