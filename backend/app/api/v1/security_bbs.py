"""
BBS+ 签名方案 API - /api/v1/security/bbs
BBS+ 密钥生成 / 签名 / 验证 / 选择性披露（含零知识证明）
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import bbs_plus_service
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Request 模型
# ============================================================


class BbsKeyGenRequest(BaseModel):
    """BBS+ 密钥对生成请求"""
    message_count: int = Field(default=10, ge=1, le=100, description="支持的最大消息数量")
    curve: str = Field(default="BLS12-381", description="椭圆曲线: BLS12-381 / BN254")
    label: str = Field(default="", description="密钥标签")


class BbsSignRequest(BaseModel):
    """BBS+ 签名请求"""
    key_id: str = Field(description="密钥 ID")
    messages: list[str] = Field(min_length=1, description="待签名消息列表")
    header: str = Field(default="", description="可选头部数据")


class BbsVerifyRequest(BaseModel):
    """BBS+ 签名验证请求"""
    public_key: str = Field(description="公钥（十六进制字符串）")
    messages: list[str] = Field(min_length=1, description="消息列表")
    signature: dict = Field(description="BBS+ 签名数据（包含 A, e, s 等字段）")
    header: str = Field(default="", description="可选头部数据")


class BbsDiscloseRequest(BaseModel):
    """BBS+ 选择性披露请求"""
    signature_id: str = Field(description="签名 ID")
    disclosed_indices: list[int] = Field(description="需要披露的消息索引列表")
    public_key: str = Field(description="公钥（十六进制字符串）")


# ============================================================
# API 端点
# ============================================================


@router.post("/keys/generate", response_model=ApiResponse)
async def generate_key_pair(
    request: BbsKeyGenRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """BBS+ 密钥对生成

    生成基于 BLS12-381 曲线的 BBS+ 公私钥对及消息生成器。
    """
    try:
        result = await bbs_plus_service.generate_key_pair(
            db=db,
            message_count=request.message_count,
            curve=request.curve,
            label=request.label,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        logger.warning(f"BBS+ 密钥生成参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"BBS+ 密钥生成失败: {e}")
        return ApiResponse(code=4000, message=f"密钥生成失败: {e}", data=None)


@router.post("/sign", response_model=ApiResponse)
async def sign(
    request: BbsSignRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """BBS+ 签名

    使用指定密钥对消息列表生成 BBS+ 签名（支持后续选择性披露）。
    """
    try:
        result = await bbs_plus_service.sign(
            db=db,
            key_id=request.key_id,
            messages=request.messages,
            header=request.header,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataNotFoundError as e:
        logger.warning(f"BBS+ 签名 - 密钥不存在: {e}")
        return ApiResponse(code=2001, message=e.message, data=None)
    except DataValidationError as e:
        logger.warning(f"BBS+ 签名参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"BBS+ 签名失败: {e}")
        return ApiResponse(code=4000, message=f"签名失败: {e}", data=None)


@router.post("/verify", response_model=ApiResponse)
async def verify(
    request: BbsVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """BBS+ 签名验证

    验证 BBS+ 签名对给定消息列表的有效性。
    """
    try:
        result = await bbs_plus_service.verify(
            db=db,
            public_key=request.public_key,
            messages=request.messages,
            signature=request.signature,
            header=request.header,
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        logger.warning(f"BBS+ 验证参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"BBS+ 验证失败: {e}")
        return ApiResponse(code=4000, message=f"验证失败: {e}", data=None)


@router.post("/disclose", response_model=ApiResponse)
async def selective_disclose(
    request: BbsDiscloseRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """BBS+ 选择性披露

    从完整签名中仅披露指定索引的消息，隐藏其他消息并生成零知识证明。
    """
    try:
        result = await bbs_plus_service.selective_disclose(
            db=db,
            signature_id=request.signature_id,
            disclosed_indices=request.disclosed_indices,
            public_key=request.public_key,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataNotFoundError as e:
        logger.warning(f"BBS+ 选择性披露 - 签名不存在: {e}")
        return ApiResponse(code=2001, message=e.message, data=None)
    except DataValidationError as e:
        logger.warning(f"BBS+ 选择性披露参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"BBS+ 选择性披露失败: {e}")
        return ApiResponse(code=4000, message=f"选择性披露失败: {e}", data=None)


@router.get("/keys", response_model=ApiResponse)
async def list_key_pairs(
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出 BBS+ 密钥对（当前用户）"""
    try:
        result = await bbs_plus_service.list_key_pairs(
            db=db,
            user_id=user.get("user_id", ""),
            limit=limit,
            offset=offset,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"查询 BBS+ 密钥对失败: {e}")
        return ApiResponse(code=4000, message=f"查询失败: {e}", data=None)


@router.get("/signatures", response_model=ApiResponse)
async def list_signatures(
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出 BBS+ 签名记录"""
    try:
        result = await bbs_plus_service.list_signatures(
            db=db,
            limit=limit,
            offset=offset,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"查询 BBS+ 签名失败: {e}")
        return ApiResponse(code=4000, message=f"查询失败: {e}", data=None)
