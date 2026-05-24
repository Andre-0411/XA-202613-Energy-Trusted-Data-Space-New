"""
认证管理服务
机构认证/加入申请/角色/用户角色管理的独立封装
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite_code import OrganizationCertification, OrganizationJoinRequest
from app.models.certification import CustomRole, UserRole
from app.models.user import Organization, User
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError, PermissionDeniedError

logger = logging.getLogger(__name__)


# ==================== 机构认证（增强） ====================

async def get_certification_detail(db: AsyncSession, cert_id: str) -> dict:
    """获取认证详情（含关联组织信息）"""
    result = await db.execute(
        select(OrganizationCertification).where(OrganizationCertification.id == uuid.UUID(cert_id))
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise DataNotFoundError("认证申请不存在")

    org_result = await db.execute(select(Organization).where(Organization.id == cert.organization_id))
    org = org_result.scalar_one_or_none()

    reviewer_name = None
    if cert.reviewer_id:
        user_result = await db.execute(select(User).where(User.id == cert.reviewer_id))
        reviewer = user_result.scalar_one_or_none()
        if reviewer:
            reviewer_name = reviewer.username

    return {
        "id": str(cert.id),
        "organization_id": str(cert.organization_id),
        "organization_name": org.name if org else None,
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
        "reviewer_name": reviewer_name,
        "review_comment": cert.review_comment,
        "reviewed_at": cert.reviewed_at.isoformat() if cert.reviewed_at else None,
        "created_at": cert.created_at.isoformat(),
        "updated_at": cert.updated_at.isoformat(),
    }


async def list_certifications_enhanced(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
    cert_type: Optional[str] = None,
) -> PaginatedResponse:
    """列出认证申请（增强过滤）"""
    query = select(OrganizationCertification)
    if status:
        query = query.where(OrganizationCertification.status == status)
    if organization_id:
        query = query.where(OrganizationCertification.organization_id == uuid.UUID(organization_id))
    if cert_type:
        query = query.where(OrganizationCertification.cert_type == cert_type)
    query = query.order_by(OrganizationCertification.created_at.desc())

    from app.schemas.registration import CertificationResponse
    result = await paginate_query(db, query, params, CertificationResponse)
    return result


async def get_certification_stats(db: AsyncSession, organization_id: Optional[str] = None) -> dict:
    """获取认证统计"""
    base_filter = []
    if organization_id:
        base_filter.append(OrganizationCertification.organization_id == uuid.UUID(organization_id))

    pending_q = select(OrganizationCertification).where(
        and_(OrganizationCertification.status == "pending", *base_filter)
    )
    approved_q = select(OrganizationCertification).where(
        and_(OrganizationCertification.status == "approved", *base_filter)
    )
    rejected_q = select(OrganizationCertification).where(
        and_(OrganizationCertification.status == "rejected", *base_filter)
    )

    pending_r = await db.execute(pending_q)
    approved_r = await db.execute(approved_q)
    rejected_r = await db.execute(rejected_q)

    return {
        "pending_count": len(pending_r.scalars().all()),
        "approved_count": len(approved_r.scalars().all()),
        "rejected_count": len(rejected_r.scalars().all()),
    }
