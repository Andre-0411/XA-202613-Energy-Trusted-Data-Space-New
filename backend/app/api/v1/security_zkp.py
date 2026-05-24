"""
零知识证明 API - /api/v1/security/zkp
Groth16证明/验证 + BBS+签名/验证 + Bulletproofs范围证明/验证 + 证明记录列表
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.security import ZkpProveRequest
from app.utils.deps import get_current_user
from app.services import zkp_service

router = APIRouter()


class Groth16VerifyRequest(BaseModel):
    """Groth16 验证请求"""
    proof: dict = Field(description="证明数据 (pi_a, pi_b, pi_c)")
    public_signals: list[str] = Field(description="公开信号列表")


class BbsSignRequest(BaseModel):
    """BBS+ 签名请求"""
    private_key: str = Field(description="签名私钥")
    messages: list[str] = Field(description="消息列表")


class BbsVerifyRequest(BaseModel):
    """BBS+ 验证请求"""
    public_key: str = Field(description="公钥")
    messages: list[str] = Field(description="消息列表")
    signature: dict = Field(description="BBS+ 签名 (e, s, a_prime, b_prime)")


class BulletproofsProveRequest(BaseModel):
    """Bulletproofs 范围证明请求"""
    value: int = Field(description="待证明的值")
    min_val: int = Field(default=0, description="最小值")
    max_val: int = Field(default=2**64 - 1, description="最大值")


class BulletproofsVerifyRequest(BaseModel):
    """Bulletproofs 验证请求"""
    proof: dict = Field(description="范围证明数据")
    min_val: int = Field(default=0, description="最小值")
    max_val: int = Field(default=2**64 - 1, description="最大值")


@router.post("/groth16/prove", response_model=ApiResponse)
async def groth16_prove(
    request: ZkpProveRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Groth16证明生成"""
    result = await zkp_service.groth16_prove(
        db=db,
        circuit_id=request.circuit_id or "",
        private_input=request.private_input,
        public_input=request.public_input,
        prover_did="",
    )
    return ApiResponse(data=result)


@router.post("/groth16/verify", response_model=ApiResponse)
async def groth16_verify(
    request: Groth16VerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Groth16证明验证"""
    result = await zkp_service.groth16_verify(
        db=db,
        proof=request.proof,
        public_signals=request.public_signals,
    )
    return ApiResponse(data=result)


@router.post("/bbs/sign", response_model=ApiResponse)
async def bbs_sign(
    request: BbsSignRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """BBS+签名"""
    result = await zkp_service.bbs_sign(
        db=db,
        private_key=request.private_key,
        messages=request.messages,
    )
    return ApiResponse(data=result)


@router.post("/bbs/verify", response_model=ApiResponse)
async def bbs_verify(
    request: BbsVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """BBS+验证"""
    result = await zkp_service.bbs_verify(
        db=db,
        public_key=request.public_key,
        messages=request.messages,
        signature=request.signature,
    )
    return ApiResponse(data=result)


@router.post("/bulletproofs/prove", response_model=ApiResponse)
async def bulletproofs_prove(
    request: BulletproofsProveRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Bulletproofs范围证明（证明 value ∈ [min_val, max_val] 不泄露 value）"""
    result = await zkp_service.bulletproofs_prove(
        db=db,
        value=request.value,
        min_val=request.min_val,
        max_val=request.max_val,
    )
    return ApiResponse(data=result)


@router.post("/bulletproofs/verify", response_model=ApiResponse)
async def bulletproofs_verify(
    request: BulletproofsVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Bulletproofs范围证明验证"""
    result = await zkp_service.bulletproofs_verify(
        db=db,
        proof=request.proof,
        min_val=request.min_val,
        max_val=request.max_val,
    )
    return ApiResponse(data=result)


# ============================================================
# 证明记录列表端点
# ============================================================


@router.get("/proofs", response_model=ApiResponse)
async def list_proofs(
    proof_type: Optional[str] = Query(default=None, description="证明类型过滤: groth16/bbs/bulletproofs"),
    limit: int = Query(default=20, ge=1, le=100, description="分页大小"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出证明记录（数据库查询）"""
    result = await zkp_service.list_proofs(
        db=db,
        proof_type=proof_type,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)
