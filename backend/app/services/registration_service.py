"""
注册/认证服务
邀请码管理 / 机构认证 / 机构加入申请 / 自定义角色 / 用户角色
"""
import uuid
import secrets
import string
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite_code import InviteCode, OrganizationCertification, OrganizationJoinRequest
from app.models.certification import CustomRole, UserRole
from app.models.user import Organization, User
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError, PermissionDeniedError

logger = logging.getLogger(__name__)


def _generate_code(length: int = 8) -> str:
    """生成随机邀请码"""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# ==================== 邀请码 ====================

async def create_invite_code(
    db: AsyncSession,
    created_by: str,
    organization_id: Optional[str] = None,
    max_uses: int = 1,
    expires_at: str = "",
) -> dict:
    """创建邀请码"""
    code = _generate_code()
    # 确保唯一
    existing = await db.execute(select(InviteCode).where(InviteCode.code == code))
    while existing.scalar_one_or_none():
        code = _generate_code()
        existing = await db.execute(select(InviteCode).where(InviteCode.code == code))

    invite = InviteCode(
        code=code,
        created_by=uuid.UUID(created_by),
        organization_id=uuid.UUID(organization_id) if organization_id else None,
        max_uses=max_uses,
        used_count=0,
        error_count=0,
        status="active",
        expires_at=datetime.fromisoformat(expires_at),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    logger.info(f"Invite code created: {code} by user {created_by}")
    return {
        "id": str(invite.id),
        "code": invite.code,
        "created_by": str(invite.created_by),
        "organization_id": str(invite.organization_id) if invite.organization_id else None,
        "max_uses": invite.max_uses,
        "used_count": invite.used_count,
        "error_count": invite.error_count,
        "status": invite.status,
        "expires_at": invite.expires_at.isoformat(),
        "created_at": invite.created_at.isoformat(),
    }


async def list_invite_codes(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出邀请码"""
    query = select(InviteCode)
    if status:
        query = query.where(InviteCode.status == status)
    if organization_id:
        query = query.where(InviteCode.organization_id == uuid.UUID(organization_id))
    query = query.order_by(InviteCode.created_at.desc())

    from app.schemas.registration import InviteCodeResponse
    result = await paginate_query(db, query, params, InviteCodeResponse)
    return result


async def verify_invite_code(db: AsyncSession, code: str) -> dict:
    """验证邀请码"""
    result = await db.execute(select(InviteCode).where(InviteCode.code == code))
    invite = result.scalar_one_or_none()
    if not invite:
        raise DataNotFoundError("邀请码不存在")
    if invite.status != "active":
        raise DataValidationError(f"邀请码状态无效: {invite.status}")
    if invite.expires_at < datetime.now(timezone.utc):
        invite.status = "expired"
        await db.commit()
        raise DataValidationError("邀请码已过期")
    if invite.used_count >= invite.max_uses:
        invite.status = "used_up"
        await db.commit()
        raise DataValidationError("邀请码已用完")

    return {
        "valid": True,
        "organization_id": str(invite.organization_id) if invite.organization_id else None,
        "remaining_uses": invite.max_uses - invite.used_count,
    }


async def use_invite_code(db: AsyncSession, code: str) -> bool:
    """使用邀请码（递增计数）"""
    result = await db.execute(select(InviteCode).where(InviteCode.code == code))
    invite = result.scalar_one_or_none()
    if not invite:
        return False
    invite.used_count += 1
    if invite.used_count >= invite.max_uses:
        invite.status = "used_up"
    await db.commit()
    return True


# ==================== 机构认证 ====================

async def create_certification(
    db: AsyncSession,
    organization_id: str,
    cert_type: str,
    **kwargs,
) -> dict:
    """创建机构认证申请"""
    # 检查是否已有待审批的申请
    existing = await db.execute(
        select(OrganizationCertification).where(
            and_(
                OrganizationCertification.organization_id == uuid.UUID(organization_id),
                OrganizationCertification.status == "pending",
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataValidationError("已有待审批的认证申请")

    cert = OrganizationCertification(
        organization_id=uuid.UUID(organization_id),
        cert_type=cert_type,
        business_license_url=kwargs.get("business_license_url"),
        legal_person_id_url=kwargs.get("legal_person_id_url"),
        credit_report_url=kwargs.get("credit_report_url"),
        authorization_letter_url=kwargs.get("authorization_letter_url"),
        dcmm_cert_url=kwargs.get("dcmm_cert_url"),
        iso_cert_url=kwargs.get("iso_cert_url"),
        social_credit_code=kwargs.get("social_credit_code"),
        status="pending",
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)

    logger.info(f"Certification created: org={organization_id}, type={cert_type}")
    return {
        "id": str(cert.id),
        "organization_id": str(cert.organization_id),
        "cert_type": cert.cert_type,
        "status": cert.status,
        "created_at": cert.created_at.isoformat(),
        "updated_at": cert.updated_at.isoformat(),
    }


async def list_certifications(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出认证申请"""
    query = select(OrganizationCertification)
    if status:
        query = query.where(OrganizationCertification.status == status)
    if organization_id:
        query = query.where(OrganizationCertification.organization_id == uuid.UUID(organization_id))
    query = query.order_by(OrganizationCertification.created_at.desc())

    from app.schemas.registration import CertificationResponse
    result = await paginate_query(db, query, params, CertificationResponse)
    return result


async def review_certification(
    db: AsyncSession,
    cert_id: str,
    reviewer_id: str,
    status: str,
    review_comment: Optional[str] = None,
) -> dict:
    """审核认证申请"""
    result = await db.execute(
        select(OrganizationCertification).where(OrganizationCertification.id == uuid.UUID(cert_id))
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise DataNotFoundError("认证申请不存在")
    if cert.status != "pending":
        raise DataValidationError(f"认证申请状态不为待审批: {cert.status}")

    cert.status = status
    cert.reviewer_id = uuid.UUID(reviewer_id)
    cert.review_comment = review_comment
    cert.reviewed_at = datetime.now(timezone.utc)

    # 如果审批通过，更新组织认证状态
    if status == "approved":
        org_result = await db.execute(select(Organization).where(Organization.id == cert.organization_id))
        org = org_result.scalar_one_or_none()
        if org:
            org.status = "certified"
            logger.info(f"Organization {cert.organization_id} certified with type {cert.cert_type}")

    await db.commit()
    logger.info(f"Certification {cert_id} reviewed: {status} by {reviewer_id}")
    return {
        "id": str(cert.id),
        "status": cert.status,
        "reviewed_at": cert.reviewed_at.isoformat(),
    }


async def get_certification(db: AsyncSession, cert_id: str) -> dict:
    """获取认证申请详情"""
    result = await db.execute(
        select(OrganizationCertification).where(OrganizationCertification.id == uuid.UUID(cert_id))
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise DataNotFoundError("认证申请不存在")
    return {
        "id": str(cert.id),
        "organization_id": str(cert.organization_id),
        "cert_type": cert.cert_type,
        "business_license_url": cert.business_license_url,
        "legal_person_id_url": cert.legal_person_id_url,
        "credit_report_url": cert.credit_report_url,
        "authorization_letter_url": cert.authorization_letter_url,
        "dcmm_cert_url": cert.dcmm_cert_url,
        "iso_cert_url": cert.iso_cert_url,
        "social_credit_code": cert.social_credit_code,
        "status": cert.status,
        "reviewer_id": str(cert.reviewer_id) if cert.reviewer_id else None,
        "review_comment": cert.review_comment,
        "reviewed_at": cert.reviewed_at.isoformat() if cert.reviewed_at else None,
        "created_at": cert.created_at.isoformat(),
        "updated_at": cert.updated_at.isoformat(),
    }


# ==================== 机构加入申请 ====================

async def create_join_request(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    reason: Optional[str] = None,
) -> dict:
    """创建机构加入申请"""
    # 检查重复申请
    existing = await db.execute(
        select(OrganizationJoinRequest).where(
            and_(
                OrganizationJoinRequest.user_id == uuid.UUID(user_id),
                OrganizationJoinRequest.organization_id == uuid.UUID(organization_id),
                OrganizationJoinRequest.status == "pending",
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataValidationError("已有待审批的加入申请")

    request = OrganizationJoinRequest(
        user_id=uuid.UUID(user_id),
        organization_id=uuid.UUID(organization_id),
        reason=reason,
        status="pending",
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)

    logger.info(f"Join request created: user={user_id}, org={organization_id}")
    return {
        "id": str(request.id),
        "user_id": str(request.user_id),
        "organization_id": str(request.organization_id),
        "reason": request.reason,
        "status": request.status,
        "created_at": request.created_at.isoformat(),
        "updated_at": request.updated_at.isoformat(),
    }


async def list_join_requests(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出加入申请"""
    query = select(OrganizationJoinRequest)
    if status:
        query = query.where(OrganizationJoinRequest.status == status)
    if organization_id:
        query = query.where(OrganizationJoinRequest.organization_id == uuid.UUID(organization_id))
    if user_id:
        query = query.where(OrganizationJoinRequest.user_id == uuid.UUID(user_id))
    query = query.order_by(OrganizationJoinRequest.created_at.desc())

    from app.schemas.registration import JoinRequestResponse
    result = await paginate_query(db, query, params, JoinRequestResponse)
    return result


async def review_join_request(
    db: AsyncSession,
    request_id: str,
    reviewer_id: str,
    status: str,
    review_comment: Optional[str] = None,
) -> dict:
    """审核加入申请"""
    result = await db.execute(
        select(OrganizationJoinRequest).where(OrganizationJoinRequest.id == uuid.UUID(request_id))
    )
    join_req = result.scalar_one_or_none()
    if not join_req:
        raise DataNotFoundError("加入申请不存在")
    if join_req.status != "pending":
        raise DataValidationError(f"申请状态不为待审批: {join_req.status}")

    join_req.status = status
    join_req.reviewer_id = uuid.UUID(reviewer_id)
    join_req.review_comment = review_comment
    join_req.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    logger.info(f"Join request {request_id} reviewed: {status} by {reviewer_id}")
    return {
        "id": str(join_req.id),
        "status": join_req.status,
        "reviewed_at": join_req.reviewed_at.isoformat(),
    }


# ==================== 自定义角色 ====================

async def create_role(
    db: AsyncSession,
    organization_id: str,
    name: str,
    description: Optional[str] = None,
    permissions: Optional[dict] = None,
    created_by: Optional[str] = None,
) -> dict:
    """创建自定义角色"""
    # 检查同名角色
    existing = await db.execute(
        select(CustomRole).where(
            and_(
                CustomRole.organization_id == uuid.UUID(organization_id),
                CustomRole.name == name,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError(f"角色名称 '{name}' 已存在")

    role = CustomRole(
        name=name,
        description=description,
        organization_id=uuid.UUID(organization_id),
        permissions=permissions or {},
        is_system=False,
        status="active",
        created_by=uuid.UUID(created_by) if created_by else None,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    logger.info(f"Custom role created: {name} in org {organization_id}")
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "organization_id": str(role.organization_id),
        "permissions": role.permissions,
        "is_system": role.is_system,
        "status": role.status,
        "created_by": str(role.created_by) if role.created_by else None,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
    }


async def list_roles(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出自定义角色"""
    query = select(CustomRole)
    if organization_id:
        query = query.where(CustomRole.organization_id == uuid.UUID(organization_id))
    if status:
        query = query.where(CustomRole.status == status)
    query = query.order_by(CustomRole.created_at.desc())

    from app.schemas.registration import CustomRoleResponse
    result = await paginate_query(db, query, params, CustomRoleResponse)
    return result


async def get_role(db: AsyncSession, role_id: str) -> dict:
    """获取角色详情"""
    result = await db.execute(select(CustomRole).where(CustomRole.id == uuid.UUID(role_id)))
    role = result.scalar_one_or_none()
    if not role:
        raise DataNotFoundError("角色不存在")
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "organization_id": str(role.organization_id),
        "permissions": role.permissions,
        "is_system": role.is_system,
        "status": role.status,
        "created_by": str(role.created_by) if role.created_by else None,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
    }


async def update_role(db: AsyncSession, role_id: str, **kwargs) -> dict:
    """更新角色"""
    result = await db.execute(select(CustomRole).where(CustomRole.id == uuid.UUID(role_id)))
    role = result.scalar_one_or_none()
    if not role:
        raise DataNotFoundError("角色不存在")
    if role.is_system:
        raise PermissionDeniedError("系统角色不可修改")

    for field in ["name", "description", "permissions", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(role, field, kwargs[field])

    await db.commit()
    await db.refresh(role)
    logger.info(f"Role updated: {role_id}")
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "organization_id": str(role.organization_id),
        "permissions": role.permissions,
        "is_system": role.is_system,
        "status": role.status,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
    }


async def delete_role(db: AsyncSession, role_id: str) -> bool:
    """删除角色（软删除）"""
    result = await db.execute(select(CustomRole).where(CustomRole.id == uuid.UUID(role_id)))
    role = result.scalar_one_or_none()
    if not role:
        raise DataNotFoundError("角色不存在")
    if role.is_system:
        raise PermissionDeniedError("系统角色不可删除")

    role.status = "deleted"
    await db.commit()
    logger.info(f"Role deleted: {role_id}")
    return True


# ==================== 用户角色 ====================

async def assign_user_role(
    db: AsyncSession,
    user_id: str,
    role_id: str,
    assigned_by: Optional[str] = None,
) -> dict:
    """分配用户角色"""
    # 检查重复分配
    existing = await db.execute(
        select(UserRole).where(
            and_(
                UserRole.user_id == uuid.UUID(user_id),
                UserRole.role_id == uuid.UUID(role_id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("用户已拥有该角色")

    user_role = UserRole(
        user_id=uuid.UUID(user_id),
        role_id=uuid.UUID(role_id),
        assigned_by=uuid.UUID(assigned_by) if assigned_by else None,
    )
    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)

    logger.info(f"User role assigned: user={user_id}, role={role_id}")
    return {
        "id": str(user_role.id),
        "user_id": str(user_role.user_id),
        "role_id": str(user_role.role_id),
        "assigned_by": str(user_role.assigned_by) if user_role.assigned_by else None,
        "assigned_at": user_role.assigned_at.isoformat(),
    }


async def remove_user_role(db: AsyncSession, user_id: str, role_id: str) -> bool:
    """移除用户角色"""
    result = await db.execute(
        select(UserRole).where(
            and_(
                UserRole.user_id == uuid.UUID(user_id),
                UserRole.role_id == uuid.UUID(role_id),
            )
        )
    )
    user_role = result.scalar_one_or_none()
    if not user_role:
        raise DataNotFoundError("用户角色关联不存在")

    await db.delete(user_role)
    await db.commit()
    logger.info(f"User role removed: user={user_id}, role={role_id}")
    return True


async def list_user_roles(
    db: AsyncSession,
    params: PaginationParams,
    user_id: Optional[str] = None,
    role_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出用户角色"""
    query = select(UserRole)
    if user_id:
        query = query.where(UserRole.user_id == uuid.UUID(user_id))
    if role_id:
        query = query.where(UserRole.role_id == uuid.UUID(role_id))
    query = query.order_by(UserRole.assigned_at.desc())

    from app.schemas.registration import UserRoleResponse
    result = await paginate_query(db, query, params, UserRoleResponse)
    return result
