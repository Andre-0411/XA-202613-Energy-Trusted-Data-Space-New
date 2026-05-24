"""
密钥管理 API - /api/v1/security/keys
密钥CRUD + 轮换 + 审计 + Shamir分割/恢复
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.security import KeyGenerateRequest
from app.utils.deps import get_current_user
from app.services import key_service

router = APIRouter()


class ShamirSplitRequest(BaseModel):
    """Shamir 分割请求"""
    secret: str = Field(description="待分割的秘密")
    n: int = Field(default=5, ge=2, le=20, description="总份数")
    k: int = Field(default=3, ge=2, le=20, description="恢复阈值")


class ShamirCombineRequest(BaseModel):
    """Shamir 恢复请求"""
    shares: list[dict] = Field(description="份额列表，每个份额包含 index/x/y")


@router.get("", response_model=ApiResponse)
async def list_keys(
    algorithm: Optional[str] = Query(None, description="算法: SM2/SM4/SM9"),
    status: Optional[str] = Query(None, description="状态: active/rotated/destroyed"),
    hierarchy_level: Optional[str] = Query(None, description="层级: master/kek/dek"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """密钥列表"""
    result = await key_service.list_keys(
        db=db,
        algorithm=algorithm,
        status=status,
        hierarchy_level=hierarchy_level,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.post("/generate", response_model=ApiResponse)
async def generate_key(
    request: KeyGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """生成密钥（SM2/SM4/SM9，返回key_id）"""
    result = await key_service.generate_key(
        db=db,
        algorithm=request.algorithm,
        hierarchy_level=request.hierarchy_level,
        purpose=request.purpose,
        parent_key_id=request.parent_key_id,
        created_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/{key_id}", response_model=ApiResponse)
async def get_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """密钥详情"""
    result = await key_service.get_key(db=db, key_id=key_id)
    return ApiResponse(data=result)


@router.post("/{key_id}/rotate", response_model=ApiResponse)
async def rotate_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """轮换密钥（生成新密钥，旧密钥标记为rotated）"""
    result = await key_service.rotate_key(
        db=db,
        key_id=key_id,
        rotated_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/{key_id}/audit", response_model=ApiResponse)
async def get_key_audit(
    key_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """使用审计日志"""
    result = await key_service.get_key_audit_log(
        db=db, key_id=key_id, limit=limit, offset=offset,
    )
    return ApiResponse(data=result)


@router.post("/shamir/split", response_model=ApiResponse)
async def shamir_split(
    request: ShamirSplitRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Shamir秘密分割（将密钥分为n份，需k份恢复）"""
    result = await key_service.shamir_split(
        secret=request.secret,
        n=request.n,
        k=request.k,
    )
    return ApiResponse(data=result)


@router.post("/shamir/combine", response_model=ApiResponse)
async def shamir_combine(
    request: ShamirCombineRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Shamir秘密恢复（从k份份额恢复密钥）"""
    result = await key_service.shamir_combine(shares=request.shares)
    return ApiResponse(data=result)
