"""
国密算法 API - /api/v1/security/gmssl
SM2签名/验签/加密/解密 + SM3哈希 + SM4加密/解密 + SM9签名/验签 + ZUC加密
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import gmssl_service

router = APIRouter()


# ==================== Request Models ====================

class Sm2SignRequest(BaseModel):
    """SM2 签名请求"""
    key_id: str = Field(description="密钥ID（引用服务端存储的密钥）")
    public_key: str = Field(description="SM2 公钥（十六进制）")
    data: str = Field(description="待签名数据")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class Sm2VerifyRequest(BaseModel):
    """SM2 验签请求"""
    public_key: str = Field(description="SM2 公钥（十六进制）")
    data: str = Field(description="原始数据")
    signature: str = Field(description="签名值（十六进制）")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class Sm2EncryptRequest(BaseModel):
    """SM2 加密请求"""
    public_key: str = Field(description="SM2 公钥（十六进制）")
    plaintext: str = Field(description="明文")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class Sm2DecryptRequest(BaseModel):
    """SM2 解密请求"""
    key_id: str = Field(description="密钥ID（引用服务端存储的密钥）")
    public_key: str = Field(description="SM2 公钥（十六进制）")
    ciphertext: str = Field(description="密文")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class Sm3HashRequest(BaseModel):
    """SM3 哈希请求"""
    data: str = Field(description="待哈希数据")


class Sm4EncryptRequest(BaseModel):
    """SM4 加密请求"""
    key: str = Field(description="SM4 密钥（十六进制，32字符）")
    plaintext: str = Field(description="明文")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class Sm4DecryptRequest(BaseModel):
    """SM4 解密请求"""
    key: str = Field(description="SM4 密钥（十六进制，32字符）")
    ciphertext: str = Field(description="密文")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class Sm9SignRequest(BaseModel):
    """SM9 签名请求"""
    master_private_key: str = Field(description="SM9 主私钥")
    data: str = Field(description="待签名数据")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class Sm9VerifyRequest(BaseModel):
    """SM9 验签请求"""
    master_public_key: str = Field(description="SM9 主公钥")
    data: str = Field(description="原始数据")
    signature: str = Field(description="签名值")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


class ZucEncryptRequest(BaseModel):
    """ZUC 加密请求"""
    key: str = Field(description="ZUC 密钥（十六进制）")
    iv: str = Field(description="初始化向量（十六进制）")
    plaintext: str = Field(description="明文")
    key_id: str | None = Field(default=None, description="关联密钥 ID")


# ==================== Endpoints ====================

@router.post("/sm2/sign", response_model=ApiResponse)
async def sm2_sign(
    request: Sm2SignRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM2签名"""
    result = await gmssl_service.sm2_sign(
        db=db,
        private_key=request.private_key,
        public_key=request.public_key,
        data=request.data,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/sm2/verify", response_model=ApiResponse)
async def sm2_verify(
    request: Sm2VerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM2验签"""
    result = await gmssl_service.sm2_verify(
        db=db,
        public_key=request.public_key,
        data=request.data,
        signature=request.signature,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/sm2/encrypt", response_model=ApiResponse)
async def sm2_encrypt(
    request: Sm2EncryptRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM2加密"""
    result = await gmssl_service.sm2_encrypt(
        db=db,
        public_key=request.public_key,
        plaintext=request.plaintext,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/sm2/decrypt", response_model=ApiResponse)
async def sm2_decrypt(
    request: Sm2DecryptRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM2解密"""
    result = await gmssl_service.sm2_decrypt(
        db=db,
        private_key=request.private_key,
        public_key=request.public_key,
        ciphertext=request.ciphertext,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/sm3/hash", response_model=ApiResponse)
async def sm3_hash(
    request: Sm3HashRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM3哈希"""
    result = await gmssl_service.sm3_hash(data=request.data)
    return ApiResponse(data=result)


@router.post("/sm4/encrypt", response_model=ApiResponse)
async def sm4_encrypt(
    request: Sm4EncryptRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM4加密"""
    result = await gmssl_service.sm4_encrypt(
        db=db,
        key=request.key,
        plaintext=request.plaintext,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/sm4/decrypt", response_model=ApiResponse)
async def sm4_decrypt(
    request: Sm4DecryptRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM4解密"""
    result = await gmssl_service.sm4_decrypt(
        db=db,
        key=request.key,
        ciphertext=request.ciphertext,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/sm9/sign", response_model=ApiResponse)
async def sm9_sign(
    request: Sm9SignRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM9签名"""
    result = await gmssl_service.sm9_sign(
        db=db,
        master_private_key=request.master_private_key,
        data=request.data,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/sm9/verify", response_model=ApiResponse)
async def sm9_verify(
    request: Sm9VerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """SM9验签"""
    result = await gmssl_service.sm9_verify(
        db=db,
        master_public_key=request.master_public_key,
        data=request.data,
        signature=request.signature,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/zuc/encrypt", response_model=ApiResponse)
async def zuc_encrypt(
    request: ZucEncryptRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """ZUC流加密"""
    result = await gmssl_service.zuc_encrypt(
        db=db,
        key=request.key,
        iv=request.iv,
        plaintext=request.plaintext,
        key_id=request.key_id,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)
