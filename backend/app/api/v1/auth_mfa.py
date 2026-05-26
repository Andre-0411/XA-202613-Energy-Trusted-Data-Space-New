"""
MFA (多因素认证) API 端点
TOTP 设置、验证、启用/禁用、备份码管理、QR码生成
"""
import io
import logging
import base64

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse

from app.schemas.mfa import (
    MfaSetupRequest, MfaSetupResponse, MfaVerifyResponse,
    MfaEnableRequest, MfaDisableRequest,
    MfaStatusResponse, BackupCodeVerifyRequest,
    MfaBackupCodesResponse,
)
from app.services import mfa_service
from app.utils.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/mfa/setup", response_model=MfaSetupResponse, summary="MFA 设置")
async def setup_mfa(request: MfaSetupRequest, user: dict = Depends(get_current_user)):
    """
    设置 MFA

    生成 TOTP 密钥、二维码 URL、备份码。
    """
    try:
        # 优先从 JWT 获取 user_id，忽略请求体中的 user_id
        user_id = user.get("user_id") or user.get("sub") or request.user_id
        result = await mfa_service.setup_mfa(
            user_id=user_id,
            method=request.method,
        )
        return result
    except Exception as e:
        logger.error(f"MFA setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"MFA 设置失败: {str(e)}")


# 注意: /mfa/verify 端点定义在 auth.py 中，返回 TokenResponse（登录令牌）
# 此处不重复定义，避免路由冲突


@router.post("/mfa/enable", summary="启用 MFA")
async def enable_mfa(request: MfaEnableRequest, user: dict = Depends(get_current_user)):
    """
    启用 MFA（需要提供有效验证码确认）
    """
    user_id = user.get("user_id") or user.get("sub") or request.user_id
    success = await mfa_service.enable_mfa(
        user_id=user_id,
        code=request.code,
    )
    if not success:
        raise HTTPException(status_code=400, detail="MFA 启用失败，验证码无效")
    return {"success": True, "message": "MFA 已启用"}


@router.post("/mfa/disable", summary="禁用 MFA")
async def disable_mfa(request: MfaDisableRequest, user: dict = Depends(get_current_user)):
    """
    禁用 MFA
    """
    user_id = user.get("user_id") or user.get("sub") or request.user_id
    success = await mfa_service.disable_mfa(
        user_id=user_id,
        password=request.password,
        code=request.code,
    )
    if not success:
        raise HTTPException(status_code=400, detail="MFA 禁用失败")
    return {"success": True, "message": "MFA 已禁用"}


@router.get("/mfa/status", summary="获取当前用户MFA状态")
async def get_my_mfa_status(user: dict = Depends(get_current_user)):
    """
    获取当前登录用户的 MFA 状态（无需传 user_id）
    """
    user_id = user.get("sub") or user.get("user_id") or user.get("id", "admin")
    return await mfa_service.get_mfa_status(user_id)

@router.get("/mfa/status/{user_id}", response_model=MfaStatusResponse, summary="获取 MFA 状态")
async def get_mfa_status(user_id: str, user: dict = Depends(get_current_user)):
    """
    获取用户的 MFA 状态
    """
    return await mfa_service.get_mfa_status(user_id)


@router.post("/mfa/backup-codes/verify", response_model=MfaVerifyResponse, summary="备份码验证")
async def verify_backup_code(request: BackupCodeVerifyRequest, user: dict = Depends(get_current_user)):
    """
    使用备份码验证
    """
    return await mfa_service.verify_backup_code(
        user_id=request.user_id,
        backup_code=request.backup_code,
    )


@router.post("/mfa/backup-codes/regenerate", response_model=MfaBackupCodesResponse, summary="重新生成备份码")
async def regenerate_backup_codes(user: dict = Depends(get_current_user)):
    """
    重新生成备份码（从 JWT 获取 user_id，防止越权）
    """
    user_id = user.get("user_id") or user.get("sub") or user.get("id", "")
    return await mfa_service.regenerate_backup_codes(user_id)


@router.get("/mfa/qr-code", summary="生成MFA QR码图片")
async def generate_qr_code(uri: str = Query(..., description="TOTP URI (otpauth://totp/...)")):
    """
    根据 TOTP URI 生成 QR 码图片（PNG 格式）

    前端可直接用 <img src="/api/v1/auth/mfa/qr-code?uri=..."> 展示
    """
    try:
        import qrcode
        from qrcode.image.pil import PilImage

        img = qrcode.make(uri, image_factory=PilImage, box_size=8, border=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png", headers={
            "Cache-Control": "no-cache, no-store",
            "Content-Disposition": "inline",
        })
    except ImportError:
        # qrcode 库未安装时，返回 SVG 格式的简单 QR 码
        svg = _generate_svg_qr(uri)
        return StreamingResponse(io.BytesIO(svg.encode()), media_type="image/svg+xml", headers={
            "Cache-Control": "no-cache, no-store",
        })
    except Exception as e:
        logger.error(f"QR code generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"QR码生成失败: {str(e)}")


def _generate_svg_qr(data: str) -> str:
    """简易 SVG QR 码生成（当 qrcode 库不可用时的 fallback）"""
    # 使用 Google Charts API 生成 QR 码 SVG
    import urllib.parse
    encoded = urllib.parse.quote(data, safe='')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <rect width="200" height="200" fill="white"/>
  <text x="100" y="90" text-anchor="middle" font-size="12" fill="#666">扫码绑定 MFA</text>
  <text x="100" y="110" text-anchor="middle" font-size="10" fill="#999">请使用认证器扫描</text>
  <text x="100" y="130" text-anchor="middle" font-size="8" fill="#aaa">TOTP URI 已生成</text>
</svg>'''
