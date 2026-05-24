"""
MFA (多因素认证) API 端点
TOTP 设置、验证、启用/禁用、备份码管理
"""
import logging

from fastapi import APIRouter, HTTPException, Depends

from app.schemas.mfa import (
    MfaSetupRequest, MfaSetupResponse, MfaVerifyResponse,
    MfaEnableRequest, MfaDisableRequest,
    MfaStatusResponse, BackupCodeVerifyRequest,
    MfaBackupCodesResponse,
)
from app.services import mfa_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/mfa/setup", response_model=MfaSetupResponse, summary="MFA 设置")
async def setup_mfa(request: MfaSetupRequest):
    """
    设置 MFA

    生成 TOTP 密钥、二维码 URL、备份码。
    """
    try:
        result = await mfa_service.setup_mfa(
            user_id=request.user_id,
            method=request.method,
        )
        return result
    except Exception as e:
        logger.error(f"MFA setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"MFA 设置失败: {str(e)}")


# 注意: /mfa/verify 端点定义在 auth.py 中，返回 TokenResponse（登录令牌）
# 此处不重复定义，避免路由冲突


@router.post("/mfa/enable", summary="启用 MFA")
async def enable_mfa(request: MfaEnableRequest):
    """
    启用 MFA（需要提供有效验证码确认）
    """
    success = await mfa_service.enable_mfa(
        user_id=request.user_id,
        code=request.code,
    )
    if not success:
        raise HTTPException(status_code=400, detail="MFA 启用失败，验证码无效")
    return {"success": True, "message": "MFA 已启用"}


@router.post("/mfa/disable", summary="禁用 MFA")
async def disable_mfa(request: MfaDisableRequest):
    """
    禁用 MFA
    """
    success = await mfa_service.disable_mfa(
        user_id=request.user_id,
        password=request.password,
        code=request.code,
    )
    if not success:
        raise HTTPException(status_code=400, detail="MFA 禁用失败")
    return {"success": True, "message": "MFA 已禁用"}


@router.get("/mfa/status/{user_id}", response_model=MfaStatusResponse, summary="获取 MFA 状态")
async def get_mfa_status(user_id: str):
    """
    获取用户的 MFA 状态
    """
    return await mfa_service.get_mfa_status(user_id)


@router.post("/mfa/backup-codes/verify", response_model=MfaVerifyResponse, summary="备份码验证")
async def verify_backup_code(request: BackupCodeVerifyRequest):
    """
    使用备份码验证
    """
    return await mfa_service.verify_backup_code(
        user_id=request.user_id,
        backup_code=request.backup_code,
    )


@router.post("/mfa/backup-codes/regenerate", response_model=MfaBackupCodesResponse, summary="重新生成备份码")
async def regenerate_backup_codes(user_id: str):
    """
    重新生成备份码
    """
    return await mfa_service.regenerate_backup_codes(user_id)
