"""
合规报告模型
ComplianceReport / DataQualityReport
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ComplianceReport(Base, UUIDMixin):
    """合规报告表"""
    __tablename__ = "compliance_reports"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    findings: Mapped[dict] = mapped_column(JSONB, nullable=False)
    gdpr_checklist: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    data_security_checklist: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    generated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    organization = relationship("Organization")


class DataQualityReport(Base, UUIDMixin):
    """数据质量报告表"""
    __tablename__ = "data_quality_reports"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False
    )
    completeness: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    timeliness_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    consistency: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    overall_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    asset: Mapped["DataAsset"] = relationship(back_populates="quality_reports")

    __table_args__ = (
        Index("idx_quality_asset_id", "asset_id"),
    )
