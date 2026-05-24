"""认证 API - /api/v1/auth"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.auth import LoginRequest, MfaVerifyRequest, RefreshTokenRequest, TokenResponse, SessionResponse
from app.schemas.common import ApiResponse
from app.services import auth_service
from app.utils.deps import get_current_user

router = APIRouter()


# ===== 独立登录请求 Schema =====

class DidLoginBody(BaseModel):
    """DID 签名登录请求体"""
    did: str = Field(description="用户 DID")
    signature: str = Field(description="SM2 签名")
    challenge: str = Field(description="挑战值")


class CertificateLoginBody(BaseModel):
    """SM2 证书登录请求体"""
    certificate: str = Field(description="SM2 证书 PEM")
    signature: str = Field(description="签名值")
    challenge: str = Field(description="挑战值")


class ChangePasswordBody(BaseModel):
    """修改密码请求体"""
    old_password: str = Field(description="旧密码")
    new_password: str = Field(description="新密码")


class UnlockAccountBody(BaseModel):
    """解锁账户请求体"""
    user_id: str = Field(description="要解锁的用户 ID")


# ===== 登录端点 =====

@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """登录（DID/密码/SM2证书三种模式）"""
    if request.auth_type == "password":
        tokens = await auth_service.authenticate_password(db, request.username, request.password)
    elif request.auth_type == "did":
        tokens = await auth_service.authenticate_did(db, request.did, request.signature, request.challenge)
    elif request.auth_type == "certificate":
        tokens = await auth_service.authenticate_certificate(db, request.certificate, request.signature, request.challenge)
    else:
        return ApiResponse(code=1000, message="不支持的认证类型", data=None)
    return ApiResponse(data=tokens)


@router.post("/login/did", response_model=ApiResponse[TokenResponse])
async def login_with_did(request: DidLoginBody, db: AsyncSession = Depends(get_db)):
    """DID 签名登录（独立端点）"""
    tokens = await auth_service.authenticate_did(db, request.did, request.signature, request.challenge)
    return ApiResponse(data=tokens)


@router.post("/login/certificate", response_model=ApiResponse[TokenResponse])
async def login_with_certificate(request: CertificateLoginBody, db: AsyncSession = Depends(get_db)):
    """SM2 证书登录（独立端点）"""
    tokens = await auth_service.authenticate_certificate(db, request.certificate, request.signature, request.challenge)
    return ApiResponse(data=tokens)


@router.post("/mfa/verify", response_model=ApiResponse[TokenResponse])
async def mfa_verify(request: MfaVerifyRequest, db: AsyncSession = Depends(get_db)):
    """MFA 验证"""
    tokens = await auth_service.verify_mfa(db, request.user_id, request.code, request.session_id)
    return ApiResponse(data=tokens)


@router.post("/logout", response_model=ApiResponse)
async def logout(user: dict = Depends(get_current_user)):
    """登出"""
    await auth_service.logout(user["token"])
    return ApiResponse(message="已登出")


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """刷新 Token"""
    tokens = await auth_service.refresh_access_token(db, request.refresh_token)
    return ApiResponse(data=tokens)


@router.get("/session", response_model=ApiResponse[SessionResponse])
async def get_session(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前会话"""
    session = await auth_service.get_session(db, user["user_id"])
    return ApiResponse(data=session)


@router.post("/change-password", response_model=ApiResponse)
async def change_password(
    request: ChangePasswordBody,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    await auth_service.change_password(
        db=db,
        user_id=user["user_id"],
        old_password=request.old_password,
        new_password=request.new_password,
    )
    return ApiResponse(message="密码修改成功")


@router.post("/unlock", response_model=ApiResponse)
async def unlock_account(
    request: UnlockAccountBody,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    解锁账户（管理员接口）

    仅 admin 角色可调用。清除 Redis 和数据库中的锁定状态。
    """
    # 权限检查：仅 admin 可解锁
    current_role = user.get("role", "")
    if current_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 1006, "message": "仅管理员可执行此操作"},
        )

    result = await auth_service.unlock_account(db, request.user_id)
    return ApiResponse(message="账户已解锁", data=result)


@router.get("/lockout-status/{user_id}", response_model=ApiResponse)
async def get_lockout_status(
    user_id: str,
    user: dict = Depends(get_current_user),
):
    """
    查询账户锁定状态

    返回用户的登录失败次数和锁定剩余时间。仅管理员或用户本人可查询。
    """
    # 仅管理员或用户本人可查询
    if user.get("role") != "admin" and user.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 1006, "message": "仅管理员或用户本人可查询锁定状态"},
        )
    lockout_info = await auth_service.get_login_lockout_status(user_id)
    return ApiResponse(data=lockout_info)
