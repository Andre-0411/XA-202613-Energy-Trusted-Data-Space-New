"""
SSO (单点登录) 服务
OAuth2.0 Provider 管理、Token 交换、SAML 断言解析、会话管理
使用 PostgreSQL 数据库持久化存储
"""
import uuid
import logging
import secrets
import hashlib
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.sso_model import SsoProvider, SsoSession, SsoPendingAuth
from app.schemas.sso import (
    SSOProviderConfig, SSOAuthorizeResponse, SSOTokenResponse,
    SSOUserInfo, SAMLAssertionResponse, SSOSessionInfo,
)

logger = logging.getLogger(__name__)


def _provider_model_to_schema(provider: SsoProvider) -> SSOProviderConfig:
    """将数据库模型转换为 Schema"""
    return SSOProviderConfig(
        provider_id=provider.provider_id,
        name=provider.name,
        protocol=provider.protocol,
        client_id=provider.client_id,
        client_secret=provider.client_secret,
        authorize_url=provider.authorize_url,
        token_url=provider.token_url,
        userinfo_url=provider.userinfo_url,
        redirect_uri=provider.redirect_uri,
        scopes=provider.scopes or ["openid", "profile", "email"],
        metadata_url=provider.metadata_url,
        enabled=provider.enabled,
        created_at=provider.created_at,
    )


def _session_model_to_schema(session: SsoSession) -> SSOSessionInfo:
    """将数据库会话模型转换为 Schema"""
    return SSOSessionInfo(
        session_id=session.session_id,
        user_id=session.user_id,
        provider_id=session.provider_id_ref,
        created_at=session.created_at,
        expires_at=session.expires_at,
        ip_address=session.ip_address,
        user_agent=session.user_agent,
    )


async def _init_default_providers(session: AsyncSession):
    """初始化默认 SSO 提供者配置（如果不存在）"""
    default_providers = [
        SSOProviderConfig(
            provider_id="oauth2_default",
            name="OAuth2.0 默认提供者",
            protocol="oauth2",
            client_id="energy-data-space-client",
            client_secret="energy-data-space-secret",
            authorize_url="https://auth.example.com/oauth2/authorize",
            token_url="https://auth.example.com/oauth2/token",
            userinfo_url="https://auth.example.com/oauth2/userinfo",
            redirect_uri="http://localhost:3000/api/v1/sso/callback",
            scopes=["openid", "profile", "email"],
            enabled=True,
        ),
        SSOProviderConfig(
            provider_id="oidc_default",
            name="OIDC 默认提供者",
            protocol="oidc",
            client_id="energy-oidc-client",
            client_secret="energy-oidc-secret",
            authorize_url="https://id.example.com/authorize",
            token_url="https://id.example.com/token",
            userinfo_url="https://id.example.com/userinfo",
            redirect_uri="http://localhost:3000/api/v1/sso/callback",
            scopes=["openid", "profile", "email", "groups"],
            metadata_url="https://id.example.com/.well-known/openid-configuration",
            enabled=True,
        ),
        SSOProviderConfig(
            provider_id="saml_default",
            name="SAML 2.0 默认提供者",
            protocol="saml2",
            metadata_url="https://id.example.com/saml/metadata",
            redirect_uri="http://localhost:3000/api/v1/sso/saml/callback",
            enabled=True,
        ),
    ]

    for provider_config in default_providers:
        result = await session.execute(
            select(SsoProvider).where(SsoProvider.provider_id == provider_config.provider_id)
        )
        existing = result.scalar_one_or_none()
        if not existing:
            provider = SsoProvider(
                provider_id=provider_config.provider_id,
                name=provider_config.name,
                protocol=provider_config.protocol,
                client_id=provider_config.client_id,
                client_secret=provider_config.client_secret,
                authorize_url=provider_config.authorize_url,
                token_url=provider_config.token_url,
                userinfo_url=provider_config.userinfo_url,
                redirect_uri=provider_config.redirect_uri,
                scopes=provider_config.scopes,
                metadata_url=provider_config.metadata_url,
                enabled=provider_config.enabled,
            )
            session.add(provider)

    await session.commit()


async def _ensure_providers_initialized():
    """确保默认提供者已初始化"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SsoProvider).limit(1))
        if not result.scalar_one_or_none():
            await _init_default_providers(session)


async def list_providers() -> List[SSOProviderConfig]:
    """
    列出所有 SSO 提供者

    Returns:
        提供者配置列表
    """
    await _ensure_providers_initialized()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SsoProvider))
        providers = result.scalars().all()
        return [_provider_model_to_schema(p) for p in providers]


async def get_provider(provider_id: str) -> Optional[SSOProviderConfig]:
    """
    获取 SSO 提供者配置

    Args:
        provider_id: 提供者 ID

    Returns:
        提供者配置
    """
    await _ensure_providers_initialized()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SsoProvider).where(SsoProvider.provider_id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if provider:
            return _provider_model_to_schema(provider)
        return None


async def add_provider(config: SSOProviderConfig) -> SSOProviderConfig:
    """
    添加 SSO 提供者

    Args:
        config: 提供者配置

    Returns:
        添加的提供者配置
    """
    async with AsyncSessionLocal() as session:
        provider = SsoProvider(
            provider_id=config.provider_id,
            name=config.name,
            protocol=config.protocol,
            client_id=config.client_id,
            client_secret=config.client_secret,
            authorize_url=config.authorize_url,
            token_url=config.token_url,
            userinfo_url=config.userinfo_url,
            redirect_uri=config.redirect_uri,
            scopes=config.scopes,
            metadata_url=config.metadata_url,
            enabled=config.enabled,
        )
        session.add(provider)
        await session.commit()

        logger.info(f"SSO provider added: {config.provider_id}")
        return config


async def remove_provider(provider_id: str) -> bool:
    """
    移除 SSO 提供者

    Args:
        provider_id: 提供者 ID

    Returns:
        是否成功移除
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SsoProvider).where(SsoProvider.provider_id == provider_id)
        )
        provider = result.scalar_one_or_none()

        if provider:
            await session.delete(provider)
            await session.commit()
            logger.info(f"SSO provider removed: {provider_id}")
            return True
        return False


async def generate_authorize_url(
    provider_id: str,
    redirect_uri: Optional[str] = None,
    state: Optional[str] = None,
) -> SSOAuthorizeResponse:
    """
    生成授权 URL

    Args:
        provider_id: 提供者 ID
        redirect_uri: 回调 URL
        state: 状态参数

    Returns:
        授权响应
    """
    await _ensure_providers_initialized()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SsoProvider).where(SsoProvider.provider_id == provider_id)
        )
        provider = result.scalar_one_or_none()

        if not provider:
            raise ValueError(f"SSO provider not found: {provider_id}")

        if not provider.enabled:
            raise ValueError(f"SSO provider is disabled: {provider_id}")

        # 生成 state 参数
        if not state:
            state = secrets.token_urlsafe(32)

        # 存储待处理授权
        pending_auth = SsoPendingAuth(
            state=state,
            provider_id=provider_id,
            redirect_uri=redirect_uri or provider.redirect_uri,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        session.add(pending_auth)
        await session.commit()

        # 构建授权 URL
        actual_redirect = redirect_uri or provider.redirect_uri

        if provider.protocol in ("oauth2", "oidc"):
            params = {
                "response_type": "code",
                "client_id": provider.client_id,
                "redirect_uri": actual_redirect,
                "scope": " ".join(provider.scopes or ["openid", "profile", "email"]),
                "state": state,
            }
            authorize_url = f"{provider.authorize_url}?{urlencode(params)}"
        elif provider.protocol == "saml2":
            # SAML 重定向绑定
            provider_schema = _provider_model_to_schema(provider)
            params = {
                "SAMLRequest": _generate_saml_request(provider_schema),
                "RelayState": state,
            }
            authorize_url = f"{provider.metadata_url}?{urlencode(params)}"
        else:
            raise ValueError(f"Unsupported protocol: {provider.protocol}")

        return SSOAuthorizeResponse(
            authorize_url=authorize_url,
            state=state,
        )


async def exchange_token(
    provider_id: str,
    code: str,
    state: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> SSOTokenResponse:
    """
    交换 Token

    Args:
        provider_id: 提供者 ID
        code: 授权码
        state: 状态参数
        redirect_uri: 回调 URL

    Returns:
        Token 响应
    """
    await _ensure_providers_initialized()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SsoProvider).where(SsoProvider.provider_id == provider_id)
        )
        provider = result.scalar_one_or_none()

        if not provider:
            raise ValueError(f"SSO provider not found: {provider_id}")

        # 验证 state
        if state:
            pending_result = await session.execute(
                select(SsoPendingAuth).where(SsoPendingAuth.state == state)
            )
            pending = pending_result.scalar_one_or_none()
            if pending:
                expires_at = pending.expires_at.replace(tzinfo=timezone.utc) if pending.expires_at.tzinfo is None else pending.expires_at
                if expires_at < datetime.now(timezone.utc):
                    await session.delete(pending)
                    await session.commit()
                    raise ValueError("Authorization state expired")
                await session.delete(pending)
                await session.commit()

        # 模拟 Token 交换（实际应调用提供者 API）
        mock_user_info = {
            "sub": f"sso_user_{uuid.uuid4().hex[:8]}",
            "name": "SSO 测试用户",
            "email": "sso_user@example.com",
            "picture": None,
        }

        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        id_token = None

        if provider.protocol == "oidc":
            # 模拟 ID Token
            id_token = base64.urlsafe_b64encode(
                json.dumps({"sub": mock_user_info["sub"], "iss": provider.name}).encode()
            ).decode()

        # 创建 SSO 会话
        session_id = str(uuid.uuid4())
        sso_session = SsoSession(
            session_id=session_id,
            user_id=mock_user_info["sub"],
            provider_id_ref=provider_id,
            access_token=access_token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        session.add(sso_session)
        await session.commit()

        return SSOTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=86400,
            id_token=id_token,
            user_info=mock_user_info,
        )


async def get_user_info(access_token: str) -> SSOUserInfo:
    """
    获取用户信息

    Args:
        access_token: 访问令牌

    Returns:
        用户信息
    """
    async with AsyncSessionLocal() as session:
        # 查找会话
        result = await session.execute(
            select(SsoSession).where(SsoSession.access_token == access_token)
        )
        sso_session = result.scalar_one_or_none()

        if not sso_session:
            raise ValueError("Invalid access token")

        # 模拟用户信息
        return SSOUserInfo(
            provider_id=sso_session.provider_id_ref,
            sub=sso_session.user_id,
            name="SSO 用户",
            email="sso_user@example.com",
            picture=None,
            raw_claims={"sub": sso_session.user_id, "iss": sso_session.provider_id_ref},
        )


async def parse_saml_assertion(saml_response: str, relay_state: Optional[str] = None) -> SAMLAssertionResponse:
    """
    解析 SAML 断言

    Args:
        saml_response: SAML Response (Base64)
        relay_state: RelayState

    Returns:
        SAML 断言响应
    """
    try:
        # Base64 解码
        decoded = base64.b64decode(saml_response).decode("utf-8")

        # 模拟 SAML 断言解析（实际应使用 xmlsec 库）
        return SAMLAssertionResponse(
            name_id=f"saml_user_{uuid.uuid4().hex[:8]}@example.com",
            session_index=f"_session_{uuid.uuid4().hex[:16]}",
            attributes={
                "email": "saml_user@example.com",
                "firstName": "SAML",
                "lastName": "用户",
                "groups": ["users", "data-analysts"],
            },
            issuer="https://id.example.com/saml2",
            not_on_or_after=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    except Exception as e:
        logger.error(f"SAML assertion parsing failed: {e}")
        raise ValueError(f"SAML assertion parsing failed: {str(e)}")


async def create_sso_session(
    user_id: str,
    provider_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SSOSessionInfo:
    """
    创建 SSO 会话

    Args:
        user_id: 用户 ID
        provider_id: 提供者 ID
        ip_address: IP 地址
        user_agent: User Agent

    Returns:
        会话信息
    """
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        sso_session = SsoSession(
            session_id=session_id,
            user_id=user_id,
            provider_id_ref=provider_id,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=now + timedelta(hours=24),
        )
        session.add(sso_session)
        await session.commit()

        return SSOSessionInfo(
            session_id=session_id,
            user_id=user_id,
            provider_id=provider_id,
            created_at=now,
            expires_at=now + timedelta(hours=24),
            ip_address=ip_address,
            user_agent=user_agent,
        )


async def list_sessions(user_id: Optional[str] = None) -> List[SSOSessionInfo]:
    """
    列出 SSO 会话

    Args:
        user_id: 用户 ID（可选过滤）

    Returns:
        会话列表
    """
    async with AsyncSessionLocal() as session:
        query = select(SsoSession)
        if user_id:
            query = query.where(SsoSession.user_id == user_id)

        result = await session.execute(query)
        sessions = result.scalars().all()
        return [_session_model_to_schema(s) for s in sessions]


async def invalidate_session(session_id: str) -> bool:
    """
    使会话失效

    Args:
        session_id: 会话 ID

    Returns:
        是否成功
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SsoSession).where(SsoSession.session_id == session_id)
        )
        sso_session = result.scalar_one_or_none()

        if sso_session:
            await session.delete(sso_session)
            await session.commit()
            logger.info(f"SSO session invalidated: {session_id}")
            return True
        return False


def _generate_saml_request(provider: SSOProviderConfig) -> str:
    """生成 SAML AuthnRequest（模拟）"""
    request_id = f"_{uuid.uuid4().hex}"
    saml_request = (
        f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
        f'ID="{request_id}" Version="2.0" IssueInstant="{datetime.now(timezone.utc).isoformat()}Z">'
        f'<saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">'
        f'{provider.redirect_uri}</saml:Issuer>'
        f'</samlp:AuthnRequest>'
    )
    return base64.b64encode(saml_request.encode()).decode()
