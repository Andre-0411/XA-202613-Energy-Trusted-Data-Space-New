"""
可验证凭证 API - /api/v1/security/vc
签发VC + 验证VC + 撤销VC + VC列表
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.security import VcIssueRequest, VcVerifyRequest
from app.utils.deps import get_current_user
from app.services import vc_service

router = APIRouter()


@router.post("/issue", response_model=ApiResponse)
async def issue_vc(
    request: VcIssueRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """签发VC（SM2签名，包含issuer/subject/claims/expiration）"""
    result = await vc_service.issue_vc(
        db=db,
        request=request,
        issuer_private_key="",
    )
    return ApiResponse(data=result)


@router.post("/verify", response_model=ApiResponse)
async def verify_vc(
    request: VcVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """验证VC（签名验证+过期检查+撤销检查）"""
    result = await vc_service.verify_vc(db=db, request=request)
    return ApiResponse(data=result)


@router.post("/{vc_id}/revoke", response_model=ApiResponse)
async def revoke_vc(
    vc_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """撤销VC（加入撤销列表）"""
    result = await vc_service.revoke_vc(
        db=db,
        vc_id=vc_id,
        revoked_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/list", response_model=ApiResponse)
async def list_vcs(
    issuer_did: Optional[str] = Query(None, description="签发方 DID"),
    subject_did: Optional[str] = Query(None, description="持有方 DID"),
    vc_type: Optional[str] = Query(None, description="凭证类型"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """VC列表"""
    result = await vc_service.list_vcs(
        db=db,
        issuer_did=issuer_did,
        subject_did=subject_did,
        vc_type=vc_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)
