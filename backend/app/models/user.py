"""
用户与组织模型
Organization / Department / User
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Boolean, SmallInteger, Integer, Text, ForeignKey, Index, UniqueConstraint,
    DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Organization(Base, UUIDMixin, TimestampMixin):
    """组织表"""
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    org_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="data_consumer",
        comment="生态角色: data_provider/data_consumer/data_intermediary/data_trustee/data_developer/space_operator/regulator/hybrid"
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    did: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default={}, server_default="{}")

    # Relationships
    departments: Mapped[List["Department"]] = relationship(back_populates="organization")
    users: Mapped[List["User"]] = relationship(back_populates="organization")
    parent: Mapped[Optional["Organization"]] = relationship(
        remote_side="Organization.id", foreign_keys=[parent_id]
    )

    __table_args__ = (
        Index("idx_org_parent_id", "parent_id"),
        Index("idx_org_code", "code"),
        Index("idx_org_status", "status"),
    )


class Department(Base, UUIDMixin):
    """部门表"""
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="departments")
    users: Mapped[List["User"]] = relationship(back_populates="department")
    parent: Mapped[Optional["Department"]] = relationship(
        remote_side="Department.id", foreign_keys=[parent_id]
    )

    __table_args__ = (
        Index("idx_dept_org_id", "organization_id"),
        Index("idx_dept_parent_id", "parent_id"),
    )


class User(Base, UUIDMixin, TimestampMixin):
    """用户表"""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    did: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    sm2_public_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="user")
    eco_role: Mapped[str] = mapped_column(
        String(30), nullable=False, default="data_consumer",
        comment="生态角色: data_provider/data_consumer/data_intermediary/data_trustee/data_developer/space_operator/regulator/hybrid"
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    login_fail_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="users")
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")

    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_did", "did"),
        Index("idx_user_org_id", "organization_id"),
        Index("idx_user_dept_id", "department_id"),
        Index("idx_user_status", "status"),
    )
