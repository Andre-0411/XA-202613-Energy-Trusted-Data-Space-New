"""
同态加密 API - /api/v1/compute/he
CKKS/BFV/BGV 集成：数据加密上传 / 同态计算 / 结果解密 / 密钥管理 / 噪声分析
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import he_service

router = APIRouter()


# ==================== 数据加密上传 ====================


@router.post("/encrypt", response_model=ApiResponse)
async def encrypt_upload(
    name: str = Query(..., max_length=200, description="加密任务名称"),
    scheme: str = Query(..., description="HE方案: ckks/bfv/bgv"),
    asset_id: str = Query(..., description="待加密的数据资产 ID"),
    poly_modulus_degree: int = Query(8192, description="多项式模数维度: 4096/8192/16384/32768"),
    scale_bits: int = Query(40, description="缩放因子位数"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    数据加密上传

    使用同态加密方案对数据进行加密，生成密钥对和密文。
    - CKKS: 近似数值计算（浮点运算）
    - BFV: 精确整数计算（计数/统计）
    - BGV: 整数计算（SEAL替代方案）
    """
    encryption_params = {
        "poly_modulus_degree": poly_modulus_degree,
        "scale_bits": scale_bits,
    }

    result = await he_service.encrypt_upload(
        db=db,
        name=name,
        scheme=scheme,
        asset_id=asset_id,
        encryption_params=encryption_params,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


# ==================== 同态加密计算 ====================


@router.post("/compute", response_model=ApiResponse)
async def he_compute(
    name: str = Query(..., max_length=200, description="计算任务名称"),
    scheme: str = Query(..., description="HE方案: ckks/bfv/bgv"),
    operation: str = Query(..., description="计算操作: add/multiply/negate/square/rotate/conjugate"),
    ciphertext_ids: str = Query(..., description="参与计算的密文ID（逗号分隔）"),
    compute_params: Optional[str] = Query(None, description="计算参数 JSON（如旋转步数）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    同态加密计算

    在密文上直接执行计算，无需解密。
    - add: 密文加法（2+个输入，噪声消耗 ≈1 bit）
    - multiply: 密文乘法（2个输入，噪声消耗 ≈poly_modulus_degree/4096*5 bits）
    - negate: 密文取反（1个输入，无噪声消耗）
    - square: 密文平方（1个输入，同乘法噪声消耗）
    - rotate: 密文旋转/CKKS（1个输入，噪声消耗 ≈2 bits）
    - conjugate: 密文共轭/CKKS（1个输入，无噪声消耗）
    """
    ct_ids = [c.strip() for c in ciphertext_ids.split(",") if c.strip()]
    parsed_params = json.loads(compute_params) if compute_params else None

    result = await he_service.he_compute(
        db=db,
        name=name,
        scheme=scheme,
        operation=operation,
        ciphertext_ids=ct_ids,
        compute_params=parsed_params,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


# ==================== 结果解密 ====================


@router.post("/decrypt", response_model=ApiResponse)
async def decrypt_result(
    ciphertext_id: str = Query(..., description="密文 ID"),
    key_id: str = Query(..., description="密钥 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    解密 HE 计算结果

    使用对应私钥解密密文，返回解码后的明文数据和噪声预算报告。
    """
    result = await he_service.decrypt_result(db=db, ciphertext_id=ciphertext_id, key_id=key_id)
    return ApiResponse(data=result)


# ==================== HE 方案与参数查询 ====================


@router.get("/schemes", response_model=ApiResponse)
async def list_he_schemes(user: dict = Depends(get_current_user)):
    """
    查询支持的 HE 方案列表

    返回每种方案支持的操作、数据类型、噪声增长特性、批处理支持等。
    """
    result = await he_service.get_he_schemes()
    return ApiResponse(data=result)


@router.get("/ckks-params", response_model=ApiResponse)
async def list_ckks_params(user: dict = Depends(get_current_user)):
    """
    查询 CKKS 参数集

    返回不同多项式模数维度下的参数配置: 系数模数位数、安全级别、最大槽位数等。
    """
    result = await he_service.get_he_params(scheme="ckks")
    return ApiResponse(data=result)


# ==================== 密文分析 ====================


@router.get("/ciphertexts/{ciphertext_id}/analyze", response_model=ApiResponse)
async def analyze_ciphertext(
    ciphertext_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    分析密文的噪声预算和属性

    返回当前噪声预算、剩余可执行操作数估算、来源信息等。
    噪声预算耗尽后密文将无法正确解密。
    """
    result = await he_service.get_ciphertext_info(db=db, ciphertext_id=ciphertext_id)
    return ApiResponse(data=result)


# ==================== 密钥与密文管理 ====================


@router.get("/keys", response_model=ApiResponse)
async def list_he_keys(
    scheme: Optional[str] = Query(None, description="按方案筛选: ckks/bfv/bgv"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出 HE 密钥（仅返回密钥元数据和哈希，不返回实际密钥材料）"""
    result = await he_service.list_keys(db=db, scheme=scheme, limit=limit, offset=offset)
    return ApiResponse(data=result)


@router.get("/ciphertexts", response_model=ApiResponse)
async def list_he_ciphertexts(
    key_id: Optional[str] = Query(None, description="按密钥 ID 筛选"),
    scheme: Optional[str] = Query(None, description="按方案筛选: ckks/bfv/bgv"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出 HE 密文"""
    result = await he_service.list_he_ciphertexts(
        db=db, key_id=key_id, scheme=scheme, limit=limit, offset=offset,
    )
    return ApiResponse(data=result)


# ==================== HE 统计信息 ====================


@router.get("/statistics", response_model=ApiResponse)
async def get_he_statistics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    获取 HE 服务统计信息

    返回密钥数量、密文数量、按方案分布、支持的参数集等。
    """
    result = await he_service.get_he_statistics(db=db)
    return ApiResponse(data=result)
