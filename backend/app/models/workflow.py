"""
审批工作流模型
ApprovalWorkflow / ApprovalRecord
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Text, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ApprovalWorkflow(Base, UUIDMixin):
    """审批工作流模板表"""
    __tablename__ = "approval_workflows"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="certification/subscription/product_publish/product_unpublish/demand_claim/contract")
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True,
    )
    steps: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]", comment="审批步骤定义JSON数组")
    is_system: Mapped[bool] = mapped_column(default=False, comment="是否系统内置")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    records: Mapped[List["ApprovalRecord"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_wf_type", "workflow_type"),
        Index("idx_wf_org", "organization_id"),
        Index("idx_wf_status", "status"),
    )


class ApprovalRecord(Base, UUIDMixin):
    """审批记录表"""
    __tablename__ = "approval_records"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_workflows.id"), nullable=False,
    )
    business_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="业务类型")
    business_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, comment="业务对象ID")
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="当前审批步骤")
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approval_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="审批提交数据")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="pending/in_progress/approved/rejected/cancelled")
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    workflow: Mapped["ApprovalWorkflow"] = relationship(back_populates="records")

    __table_args__ = (
        Index("idx_ar_workflow", "workflow_id"),
        Index("idx_ar_business", "business_type", "business_id"),
        Index("idx_ar_applicant", "applicant_id"),
        Index("idx_ar_status", "status"),
    )
