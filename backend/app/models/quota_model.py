"""
计算资源配额数据模型
ComputeQuota / ComputeQuotaUsage / ComputeQuotaRequest
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Text, ForeignKey, Index, func, DateTime,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class ComputeQuota(Base, UUIDMixin, TimestampMixin):
    """计算资源配额表 — 组织级/用户级"""
    __tablename__ = "compute_quotas"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
        comment="所属组织",
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="所属用户（null 表示组织级配额）",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="资源类型: cpu_hours/memory_gb_hours/storage_gb/compute_tasks/gpu_hours",
    )
    limit_value: Mapped[float] = mapped_column(
        Float, nullable=False, comment="配额上限",
    )
    used_value: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="已使用量",
    )
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="", comment="计量单位",
    )
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly",
        comment="配额周期: daily/weekly/monthly/yearly/permanent",
    )
    alert_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=80.0,
        comment="告警阈值百分比 (0-100)",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        comment="状态: active/suspended/exceeded/revoked",
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5,
        comment="配额优先级 (1=最高, 10=最低)",
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, comment="扩展配置",
    )

    # Relationships
    usage_logs: Mapped[list["ComputeQuotaUsage"]] = relationship(
        back_populates="quota",
    )
    requests: Mapped[list["ComputeQuotaRequest"]] = relationship(
        back_populates="quota",
    )

    __table_args__ = (
        Index("idx_compute_quota_org", "organization_id"),
        Index("idx_compute_quota_user", "user_id"),
        Index("idx_compute_quota_type", "resource_type"),
        Index("idx_compute_quota_status", "status"),
    )


class ComputeQuotaUsage(Base, UUIDMixin):
    """计算配额使用记录表"""
    __tablename__ = "compute_quota_usages"

    quota_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compute_quotas.id"), nullable=False,
        comment="配额 ID",
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compute_tasks.id"), nullable=True,
        comment="关联计算任务",
    )
    delta: Mapped[float] = mapped_column(
        Float, nullable=False, comment="变更量（正=消耗, 负=释放）",
    )
    before_value: Mapped[float] = mapped_column(
        Float, nullable=False, comment="变更前值",
    )
    after_value: Mapped[float] = mapped_column(
        Float, nullable=False, comment="变更后值",
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="变更原因",
    )
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="操作者",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
        comment="记录时间",
    )

    # Relationship
    quota: Mapped["ComputeQuota"] = relationship(
        back_populates="usage_logs",
    )

    __table_args__ = (
        Index("idx_compute_usage_quota", "quota_id"),
        Index("idx_compute_usage_task", "task_id"),
    )


class ComputeQuotaRequest(Base, UUIDMixin, TimestampMixin):
    """配额提升申请表"""
    __tablename__ = "compute_quota_requests"

    quota_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compute_quotas.id"), nullable=False,
        comment="原配额 ID",
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
        comment="申请组织",
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
        comment="申请人",
    )
    current_limit: Mapped[float] = mapped_column(
        Float, nullable=False, comment="当前配额上限",
    )
    requested_limit: Mapped[float] = mapped_column(
        Float, nullable=False, comment="申请配额上限",
    )
    reason: Mapped[str] = mapped_column(
        Text, nullable=False, comment="申请理由",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="状态: pending/approved/rejected",
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
        comment="审批人",
    )
    review_comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="审批意见",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="审批时间",
    )

    # Relationship
    quota: Mapped["ComputeQuota"] = relationship(
        back_populates="requests",
    )

    __table_args__ = (
        Index("idx_compute_quota_req_org", "organization_id"),
        Index("idx_compute_quota_req_status", "status"),
    )
