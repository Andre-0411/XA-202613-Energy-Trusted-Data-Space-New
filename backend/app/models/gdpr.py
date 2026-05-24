"""
GDPR/数据安全法合规模型
DataSubjectRequest - 数据主体请求（访问权、删除权、可携带权、更正权）
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Text, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class DataSubjectRequest(Base, UUIDMixin):
    """数据主体请求表"""
    __tablename__ = "data_subject_requests"

    request_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="请求类型: access/erasure/portability/rectification/restrict_processing",
    )
    subject_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="数据主体用户 ID（平台内用户）"
    )
    subject_email: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="数据主体邮箱（外部请求者）"
    )
    subject_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="数据主体姓名"
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True,
        comment="关联组织 ID"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="请求描述"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="状态: pending/in_progress/completed/rejected/expired",
    )
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="normal",
        comment="优先级: low/normal/high/urgent",
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="处理人 ID"
    )
    response_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="响应数据（导出结果/处理记录）"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="拒绝原因"
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="截止日期"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    subject_user = relationship("User", foreign_keys=[subject_user_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    organization = relationship("Organization")

    __table_args__ = (
        Index("idx_dsr_type", "request_type"),
        Index("idx_dsr_status", "status"),
        Index("idx_dsr_subject_user", "subject_user_id"),
        Index("idx_dsr_org_id", "organization_id"),
    )
