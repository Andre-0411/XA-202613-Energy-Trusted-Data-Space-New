"""
合约模型
Contract / ContractAmendment
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


class Contract(Base, UUIDMixin):
    """合约表"""
    __tablename__ = "contracts"

    contract_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="data_subscription/product_subscription/joint_compute/custom")
    party_a_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    party_a_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    party_b_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    party_b_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    related_subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="关联订阅ID"
    )
    related_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="关联产品ID"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="合约正文")
    terms: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="合约条款JSON")
    pricing: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="定价信息")
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    blockchain_contract_address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", comment="draft/pending_review/active/expired/terminated/completed/disputed")
    lifecycle_stage: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, default=None, comment="生命周期阶段"
    )
    lifecycle_status: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, default=None, comment="生命周期状态"
    )
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
    amendments: Mapped[List["ContractAmendment"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_contract_no", "contract_no"),
        Index("idx_contract_type", "contract_type"),
        Index("idx_contract_party_a", "party_a_org_id"),
        Index("idx_contract_party_b", "party_b_org_id"),
        Index("idx_contract_status", "status"),
    )


class ContractAmendment(Base, UUIDMixin):
    """合约修订记录表"""
    __tablename__ = "contract_amendments"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False,
    )
    amendment_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reason: Mapped[str] = mapped_column(Text, nullable=False, comment="修订原因")
    changes: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="变更内容")
    previous_terms: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="变更前条款")
    new_terms: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="变更后条款")
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="pending/approved/rejected")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    contract: Mapped["Contract"] = relationship(back_populates="amendments")

    __table_args__ = (
        Index("idx_amendment_contract", "contract_id"),
        Index("idx_amendment_status", "status"),
    )
