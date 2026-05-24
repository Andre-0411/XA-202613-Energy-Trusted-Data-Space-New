"""
配额管理模型
Quota / QuotaUsageLog
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Text, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Quota(Base, UUIDMixin):
    """配额表"""
    __tablename__ = "quotas"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="资源类型: api_calls/storage_mb/compute_hours/data_assets/users",
    )
    limit_value: Mapped[float] = mapped_column(
        Float, nullable=False, comment="配额上限"
    )
    used_value: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="已使用量"
    )
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="", comment="计量单位"
    )
    period: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly", comment="配额周期: monthly/yearly/permanent"
    )
    alert_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=80.0, comment="告警阈值百分比"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", comment="状态: active/suspended/exceeded"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, comment="扩展配置"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )

    organization = relationship("Organization")
    usage_logs: Mapped[list["QuotaUsageLog"]] = relationship(back_populates="quota")

    __table_args__ = (
        Index("idx_quota_org_id", "organization_id"),
        Index("idx_quota_resource_type", "resource_type"),
        Index("idx_quota_status", "status"),
    )


class QuotaUsageLog(Base, UUIDMixin):
    """配额使用记录表"""
    __tablename__ = "quota_usage_logs"

    quota_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotas.id"), nullable=False
    )
    delta: Mapped[float] = mapped_column(
        Float, nullable=False, comment="变更量（正=消耗, 负=释放）"
    )
    before_value: Mapped[float] = mapped_column(Float, nullable=False, comment="变更前值")
    after_value: Mapped[float] = mapped_column(Float, nullable=False, comment="变更后值")
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="变更原因"
    )
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quota: Mapped["Quota"] = relationship(back_populates="usage_logs")

    __table_args__ = (
        Index("idx_quota_log_quota_id", "quota_id"),
    )
