"""组织管理 API - /api/v1/org-management"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginatedRequest
from app.schemas.registration import (
    CustomRoleCreate, CustomRoleResponse,
    UserRoleAssign, UserRoleResponse,
    InviteCodeCreate, InviteCodeResponse,
    CertificationCreate, CertificationResponse, CertificationReview,
    JoinRequestCreate, JoinRequestResponse, JoinRequestReview,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import role_service, registration_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R004-R005: 角色管理 ====================

@router.post("/roles", response_model=ApiResponse[CustomRoleResponse], status_code=201)
async def create_role(
    request: CustomRoleCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建自定义角色"""
    result = await role_service.create_custom_role(
        db=db,
        organization_id=user.get("organization_id", ""),
        name=request.name,
        description=request.description,
        permissions=request.permissions,
        created_by=user["user_id"],
    )
    return ApiResponse(data=result)


@router.get("/roles", response_model=ApiResponse[PaginatedResponse[CustomRoleResponse]])
async def list_roles(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出自定义角色"""
    result = await role_service.list_roles(
        db=db, params=pagination,
        organization_id=user.get("organization_id"), status=status,
    )
    return ApiResponse(data=result)


@router.get("/roles/{role_id}", response_model=ApiResponse)
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取角色详情"""
    result = await role_service.get_role_detail(db=db, role_id=role_id)
    return ApiResponse(data=result)


@router.put("/roles/{role_id}", response_model=ApiResponse[CustomRoleResponse])
async def update_role(
    role_id: str,
    request: CustomRoleCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新角色"""
    result = await role_service.update_custom_role(
        db=db, role_id=role_id,
        name=request.name, description=request.description,
        permissions=request.permissions,
    )
    return ApiResponse(data=result)


@router.delete("/roles/{role_id}", response_model=ApiResponse)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除角色"""
    await role_service.delete_custom_role(db=db, role_id=role_id)
    return ApiResponse(message="角色已删除")


# ==================== R006-R007: 用户角色 ====================

@router.post("/user-roles", response_model=ApiResponse[UserRoleResponse], status_code=201)
async def assign_user_role(
    request: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """分配用户角色"""
    result = await role_service.assign_role_to_user(
        db=db, user_id=request.user_id, role_id=request.role_id,
        assigned_by=user["user_id"],
    )
    return ApiResponse(data=result)


@router.get("/user-roles", response_model=ApiResponse[PaginatedResponse[UserRoleResponse]])
async def list_user_roles(
    pagination: PaginationParams = Depends(get_pagination_params),
    user_id: str = Query(None, description="用户ID过滤"),
    role_id: str = Query(None, description="角色ID过滤"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出用户角色"""
    result = await role_service.list_user_roles(
        db=db, params=pagination, user_id=user_id, role_id=role_id,
    )
    return ApiResponse(data=result)


@router.delete("/user-roles", response_model=ApiResponse)
async def remove_user_role(
    user_id: str = Query(..., description="用户ID"),
    role_id: str = Query(..., description="角色ID"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """移除用户角色"""
    await role_service.revoke_role_from_user(db=db, user_id=user_id, role_id=role_id)
    return ApiResponse(message="用户角色已移除")


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
