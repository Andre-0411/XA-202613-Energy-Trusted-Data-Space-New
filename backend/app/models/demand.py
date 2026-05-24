"""
需求模型
Demand / DemandClaim
"""
import uuid
from datetime import datetime, date, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Text, Date, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Demand(Base, UUIDMixin):
    """需求表"""
    __tablename__ = "demands"

    demand_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    technical_requirements: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    budget_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    publisher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    security_risk_assessment: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    claimed_by_org: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True,
    )
    claimed_by_user: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    claims: Mapped[List["DemandClaim"]] = relationship(
        back_populates="demand", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_demand_type", "demand_type"),
        Index("idx_demand_org", "organization_id"),
        Index("idx_demand_status", "status"),
        Index("idx_demand_publisher", "publisher_id"),
        Index("idx_demand_deadline", "deadline"),
    )


class DemandClaim(Base, UUIDMixin):
    """需求认领记录表"""
    __tablename__ = "demand_claims"

    demand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("demands.id"), nullable=False,
    )
    claimer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    claimer_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    proposal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    demand: Mapped["Demand"] = relationship(back_populates="claims")

    __table_args__ = (
        Index("idx_claim_demand", "demand_id"),
        Index("idx_claim_claimer", "claimer_id"),
    )
