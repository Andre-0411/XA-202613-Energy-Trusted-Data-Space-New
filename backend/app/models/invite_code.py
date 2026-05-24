"""
邀请码模型
InviteCode / OrganizationCertification / OrganizationJoinRequest
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String, Integer, Text, ForeignKey, Index, UniqueConstraint, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class InviteCode(Base, UUIDMixin):
    """邀请码表"""
    __tablename__ = "invite_codes"

    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True,
    )
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_invite_code", "code"),
        Index("idx_invite_status", "status"),
        Index("idx_invite_expires", "expires_at"),
    )


class OrganizationCertification(Base, UUIDMixin):
    """机构认证申请表"""
    __tablename__ = "organization_certifications"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    cert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    business_license_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    legal_person_id_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    credit_report_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    authorization_letter_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    dcmm_cert_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    iso_cert_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    social_credit_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # 一级审核（机构管理员初审）
    first_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    first_review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # 二级审核（平台运营方终审）
    second_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    second_review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    second_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # 兼容字段
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_cert_org_id", "organization_id"),
        Index("idx_cert_status", "status"),
        Index("idx_cert_type", "cert_type"),
    )


class OrganizationJoinRequest(Base, UUIDMixin):
    """机构加入申请表"""
    __tablename__ = "organization_join_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_join_user_id", "user_id"),
        Index("idx_join_org_id", "organization_id"),
        Index("idx_join_status", "status"),
        UniqueConstraint("user_id", "organization_id", "status", name="uq_join_user_org_status"),
    )
