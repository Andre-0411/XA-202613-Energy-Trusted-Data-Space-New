"""
SSO (单点登录) API 端点
OAuth2.0/OIDC/SAML2.0 授权、Token 交换、用户信息
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.sso import (
    SSOProviderConfig, SSOAuthorizeRequest, SSOAuthorizeResponse,
    SSOTokenRequest, SSOTokenResponse, SSOUserInfo,
    SAMLAssertionRequest, SAMLAssertionResponse,
    SSOSessionInfo,
)
from app.services import sso_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sso/providers", summary="列出 SSO 提供者")
async def list_providers():
    """
    列出所有 SSO 提供者配置
    """
    providers = await sso_service.list_providers()
    return {"providers": [p.model_dump() for p in providers]}


@router.get("/sso/providers/{provider_id}", summary="获取 SSO 提供者")
async def get_provider(provider_id: str):
    """
    获取指定 SSO 提供者配置
    """
    provider = await sso_service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="SSO 提供者未找到")
    return provider.model_dump()


@router.post("/sso/providers", summary="添加 SSO 提供者")
async def add_provider(config: SSOProviderConfig):
    """
    添加 SSO 提供者
    """
    result = await sso_service.add_provider(config)
    return result.model_dump()


@router.delete("/sso/providers/{provider_id}", summary="删除 SSO 提供者")
async def remove_provider(provider_id: str):
    """
    删除 SSO 提供者
    """
    success = await sso_service.remove_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="SSO 提供者未找到")
    return {"success": True, "message": "SSO 提供者已删除"}


@router.post("/sso/authorize", response_model=SSOAuthorizeResponse, summary="SSO 授权")
async def authorize(request: SSOAuthorizeRequest):
    """
    生成 SSO 授权 URL
    """
    try:
        result = await sso_service.generate_authorize_url(
            provider_id=request.provider_id,
            redirect_uri=request.redirect_uri,
            state=request.state,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sso/token", response_model=SSOTokenResponse, summary="SSO Token 交换")
async def exchange_token(request: SSOTokenRequest):
    """
    使用授权码交换 Token
    """
    try:
        result = await sso_service.exchange_token(
            provider_id=request.provider_id,
            code=request.code,
            state=request.state,
            redirect_uri=request.redirect_uri,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sso/userinfo", response_model=SSOUserInfo, summary="获取 SSO 用户信息")
async def get_user_info(access_token: str = Query(description="访问令牌")):
    """
    获取 SSO 用户信息
    """
    try:
        result = await sso_service.get_user_info(access_token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/sso/saml/assertion", response_model=SAMLAssertionResponse, summary="SAML 断言解析")
async def parse_saml_assertion(request: SAMLAssertionRequest):
    """
    解析 SAML 断言
    """
    try:
        result = await sso_service.parse_saml_assertion(
            saml_response=request.saml_response,
            relay_state=request.relay_state,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sso/sessions", summary="列出 SSO 会话")
async def list_sessions(user_id: Optional[str] = Query(default=None)):
    """
    列出 SSO 会话
    """
    sessions = await sso_service.list_sessions(user_id)
    return {"sessions": [s.model_dump() for s in sessions]}


@router.delete("/sso/sessions/{session_id}", summary="删除 SSO 会话")
async def invalidate_session(session_id: str):
    """
    使 SSO 会话失效
    """
    success = await sso_service.invalidate_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话未找到")
    return {"success": True, "message": "会话已失效"}
