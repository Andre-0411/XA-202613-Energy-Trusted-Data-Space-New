"""注册/认证 API - /api/v1/registration"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginatedRequest
from app.schemas.registration import (
    InviteCodeCreate, InviteCodeResponse,
    CertificationCreate, CertificationResponse, CertificationReview,
    JoinRequestCreate, JoinRequestResponse, JoinRequestReview,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import registration_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R001: 邀请码管理 ====================

@router.post("/invite-codes", response_model=ApiResponse[InviteCodeResponse], status_code=201)
async def create_invite_code(
    request: InviteCodeCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建邀请码"""
    result = await registration_service.create_invite_code(
        db=db,
        created_by=user["user_id"],
        organization_id=request.organization_id,
        max_uses=request.max_uses,
        expires_at=request.expires_at,
    )
    return ApiResponse(data=result)


@router.get("/invite-codes", response_model=ApiResponse[PaginatedResponse[InviteCodeResponse]])
async def list_invite_codes(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    organization_id: str = Query(None, description="组织ID过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出邀请码"""
    result = await registration_service.list_invite_codes(
        db=db, params=pagination, status=status, organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/invite-codes/verify/{code}", response_model=ApiResponse)
async def verify_invite_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """验证邀请码"""
    result = await registration_service.verify_invite_code(db=db, code=code)
    return ApiResponse(data=result)


# ==================== R002: 机构认证 ====================

@router.post("/certifications", response_model=ApiResponse[CertificationResponse], status_code=201)
async def create_certification(
    request: CertificationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建机构认证申请"""
    result = await registration_service.create_certification(
        db=db,
        organization_id=user.get("organization_id", ""),
        cert_type=request.cert_type,
        business_license_url=request.business_license_url,
        legal_person_id_url=request.legal_person_id_url,
        credit_report_url=request.credit_report_url,
        authorization_letter_url=request.authorization_letter_url,
        dcmm_cert_url=request.dcmm_cert_url,
        iso_cert_url=request.iso_cert_url,
        social_credit_code=request.social_credit_code,
    )
    return ApiResponse(data=result)


@router.get("/certifications", response_model=ApiResponse[PaginatedResponse[CertificationResponse]])
async def list_certifications(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    organization_id: str = Query(None, description="组织ID过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出认证申请"""
    result = await registration_service.list_certifications(
        db=db, params=pagination, status=status, organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/certifications/{cert_id}", response_model=ApiResponse)
async def get_certification(
    cert_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取认证申请详情"""
    result = await registration_service.get_certification(db=db, cert_id=cert_id)
    return ApiResponse(data=result)


@router.put("/certifications/{cert_id}/review", response_model=ApiResponse)
async def review_certification(
    cert_id: str,
    request: CertificationReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核认证申请"""
    result = await registration_service.review_certification(
        db=db, cert_id=cert_id, reviewer_id=user["user_id"],
        status=request.status, review_comment=request.review_comment,
    )
    return ApiResponse(data=result)


# ==================== R003: 机构加入申请 ====================

@router.post("/join-requests", response_model=ApiResponse[JoinRequestResponse], status_code=201)
async def create_join_request(
    request: JoinRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建机构加入申请"""
    result = await registration_service.create_join_request(
        db=db, user_id=user["user_id"],
        organization_id=request.organization_id, reason=request.reason,
    )
    return ApiResponse(data=result)


@router.get("/join-requests", response_model=ApiResponse[PaginatedResponse[JoinRequestResponse]])
async def list_join_requests(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    organization_id: str = Query(None, description="组织ID过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出加入申请"""
    result = await registration_service.list_join_requests(
        db=db, params=pagination, status=status, organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.put("/join-requests/{request_id}/review", response_model=ApiResponse)
async def review_join_request(
    request_id: str,
    request: JoinRequestReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核加入申请"""
    result = await registration_service.review_join_request(
        db=db, request_id=request_id, reviewer_id=user["user_id"],
        status=request.status, review_comment=request.review_comment,
    )
    return ApiResponse(data=result)
