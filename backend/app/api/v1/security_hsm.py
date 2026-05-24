"""
HSM 安全模块 API - /api/v1/security/hsm
软件 HSM 模拟器，提供密钥管理、签名/验签、加密/解密、审计日志、密钥派生、轮换、备份/恢复、Shamir 秘密共享
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.hsm import (
    HsmKeyGenerateRequest,
    HsmKeyResponse,
    HsmSignRequest,
    HsmSignResponse,
    HsmVerifyRequest,
    HsmVerifyResponse,
    HsmEncryptRequest,
    HsmEncryptResponse,
    HsmDecryptRequest,
    HsmDecryptResponse,
    HsmAuditLogResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import hsm_service

router = APIRouter()


# ============================================================
# 新增请求/响应 Schema
# ============================================================


class HsmKeyRotateRequest(BaseModel):
    """HSM 密钥轮换请求"""
    key_id: str = Field(description="待轮换的密钥 ID")


class HsmKeyBackupRequest(BaseModel):
    """HSM 密钥备份请求"""
    key_id: str = Field(description="密钥 ID")
    backup_passphrase: str = Field(description="备份密码")


class HsmKeyRestoreRequest(BaseModel):
    """HSM 密钥恢复请求"""
    backup_data: dict = Field(description="备份数据")
    backup_passphrase: str = Field(description="备份密码")


class HsmDeriveKeyHkdfRequest(BaseModel):
    """HKDF 密钥派生请求"""
    master_key: str = Field(description="主密钥（十六进制）")
    info: str = Field(description="派生上下文信息")
    salt: str = Field(default="", description="盐值（十六进制）")
    key_length: int = Field(default=32, description="输出密钥长度（字节）")


class HsmDeriveKeyPbkdf2Request(BaseModel):
    """PBKDF2 密钥派生请求"""
    password: str = Field(description="密码")
    salt: str = Field(default="", description="盐值（十六进制）")
    iterations: int = Field(default=100000, description="迭代次数")
    key_length: int = Field(default=32, description="输出密钥长度（字节）")


class ShamirSplitRequest(BaseModel):
    """Shamir 秘密共享分割请求"""
    secret: str = Field(description="密钥数据（十六进制）")
    num_shares: int = Field(default=5, description="分割份数")
    threshold: int = Field(default=3, description="恢复阈值")


class ShamirReconstructRequest(BaseModel):
    """Shamir 秘密共享恢复请求"""
    shares: list[dict] = Field(description="共享份额列表")


# ============================================================
# 密钥管理端点
# ============================================================


@router.post("/keys", response_model=ApiResponse[HsmKeyResponse])
async def generate_key(
    request: HsmKeyGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """生成 HSM 密钥"""
    result = await hsm_service.generate_key(
        db=db,
        algorithm=request.algorithm,
        key_size=request.key_size,
        hierarchy=request.hierarchy,
        purpose=request.purpose,
        org_id=request.org_id,
        description=request.description,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/keys", response_model=ApiResponse[PaginatedResponse[HsmKeyResponse]])
async def list_keys(
    algorithm: Optional[str] = Query(None, description="算法过滤: SM2/SM4/RSA"),
    hierarchy: Optional[str] = Query(None, description="层级过滤: root/org/user"),
    key_status: Optional[str] = Query(None, description="状态过滤: active/revoked/expired"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出 HSM 密钥"""
    result = await hsm_service.list_keys(
        db=db,
        params=pagination,
        algorithm=algorithm,
        hierarchy=hierarchy,
        status=key_status,
    )
    return ApiResponse(data=result)


@router.post("/keys/{key_id}/rotate", response_model=ApiResponse)
async def rotate_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """密钥轮换：生成新密钥替换旧密钥，旧密钥标记为 revoked"""
    result = await hsm_service.rotate_key(
        db=db,
        key_id=key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/keys/backup", response_model=ApiResponse)
async def backup_key(
    request: HsmKeyBackupRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """备份密钥：使用 PBKDF2 派生密钥对密钥数据进行二次加密"""
    result = await hsm_service.backup_key(
        db=db,
        key_id=request.key_id,
        backup_passphrase=request.backup_passphrase,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/keys/restore", response_model=ApiResponse)
async def restore_key(
    request: HsmKeyRestoreRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """恢复密钥：从备份数据中恢复密钥"""
    result = await hsm_service.restore_key(
        db=db,
        backup_data=request.backup_data,
        backup_passphrase=request.backup_passphrase,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


# ============================================================
# 签名/验签/加密/解密端点
# ============================================================


@router.post("/sign", response_model=ApiResponse[HsmSignResponse])
async def hsm_sign(
    request: HsmSignRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """HSM 签名"""
    result = await hsm_service.sign(
        db=db,
        key_id=request.key_id,
        data=request.data,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/verify", response_model=ApiResponse[HsmVerifyResponse])
async def hsm_verify(
    request: HsmVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """HSM 验签"""
    result = await hsm_service.verify(
        db=db,
        key_id=request.key_id,
        data=request.data,
        signature=request.signature,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/encrypt", response_model=ApiResponse[HsmEncryptResponse])
async def hsm_encrypt(
    request: HsmEncryptRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """HSM 加密"""
    result = await hsm_service.encrypt(
        db=db,
        key_id=request.key_id,
        plaintext=request.plaintext,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/decrypt", response_model=ApiResponse[HsmDecryptResponse])
async def hsm_decrypt(
    request: HsmDecryptRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """HSM 解密"""
    result = await hsm_service.decrypt(
        db=db,
        key_id=request.key_id,
        ciphertext=request.ciphertext,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


# ============================================================
# 密钥派生端点
# ============================================================


@router.post("/derive-key/hkdf", response_model=ApiResponse)
async def derive_key_hkdf(
    request: HsmDeriveKeyHkdfRequest,
    user: dict = Depends(get_current_user),
):
    """使用 HKDF 从主密钥派生子密钥（RFC 5869）"""
    result = hsm_service.derive_key_hkdf(
        master_key=request.master_key,
        info=request.info,
        salt=request.salt,
        key_length=request.key_length,
    )
    return ApiResponse(data={"derived_key": result})


@router.post("/derive-key/pbkdf2", response_model=ApiResponse)
async def derive_key_pbkdf2(
    request: HsmDeriveKeyPbkdf2Request,
    user: dict = Depends(get_current_user),
):
    """使用 PBKDF2 从密码派生密钥"""
    result = hsm_service.derive_key_pbkdf2(
        password=request.password,
        salt=request.salt,
        iterations=request.iterations,
        key_length=request.key_length,
    )
    return ApiResponse(data={"derived_key": result})


# ============================================================
# Shamir 秘密共享端点
# ============================================================


@router.post("/shamir/split", response_model=ApiResponse)
async def shamir_split(
    request: ShamirSplitRequest,
    user: dict = Depends(get_current_user),
):
    """Shamir 秘密共享分割：将密钥分割为 n 份，任意 k 份可恢复"""
    result = hsm_service.shamir_split(
        secret=request.secret,
        num_shares=request.num_shares,
        threshold=request.threshold,
    )
    return ApiResponse(data={"shares": result, "threshold": request.threshold, "total_shares": request.num_shares})


@router.post("/shamir/reconstruct", response_model=ApiResponse)
async def shamir_reconstruct(
    request: ShamirReconstructRequest,
    user: dict = Depends(get_current_user),
):
    """Shamir 秘密共享恢复：从份额恢复密钥"""
    result = hsm_service.shamir_reconstruct(shares=request.shares)
    return ApiResponse(data={"recovered_secret": result})


# ============================================================
# 审计日志端点
# ============================================================


@router.get("/audit-log", response_model=ApiResponse[PaginatedResponse[HsmAuditLogResponse]])
async def get_audit_log(
    key_id: Optional[str] = Query(None, description="密钥 ID 过滤"),
    operation: Optional[str] = Query(None, description="操作类型过滤"),
    audit_user_id: Optional[str] = Query(None, description="操作用户过滤"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """HSM 审计日志"""
    result = await hsm_service.get_audit_log(
        db=db,
        params=pagination,
        key_id=key_id,
        operation=operation,
        user_id=audit_user_id,
    )
    return ApiResponse(data=result)


# ============================================================
# 健康检查端点
# ============================================================


@router.get("/health", response_model=ApiResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    """HSM 服务健康检查：检查数据库连接、密钥存储、算法支持、PKCS#11 状态"""
    result = await hsm_service.health_check(db=db)
    return ApiResponse(data=result)
