"""
数据资源订阅模型
DataSubscription / DataDelivery
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


class DataSubscription(Base, UUIDMixin):
    """数据资源订阅申请表"""
    __tablename__ = "data_subscriptions"

    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalog_registrations.id"), nullable=False,
    )
    subscriber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    subscriber_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contract_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    subscription_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    deliveries: Mapped[List["DataDelivery"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_sub_catalog", "catalog_id"),
        Index("idx_subscriber", "subscriber_id"),
        Index("idx_sub_org", "subscriber_org_id"),
        Index("idx_sub_status", "status"),
    )


class DataDelivery(Base, UUIDMixin):
    """数据交付记录表"""
    __tablename__ = "data_deliveries"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_subscriptions.id"), nullable=False,
    )
    delivery_type: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    subscription: Mapped["DataSubscription"] = relationship(back_populates="deliveries")

    __table_args__ = (
        Index("idx_delivery_sub", "subscription_id"),
        Index("idx_delivery_type", "delivery_type"),
        Index("idx_delivery_status", "status"),
    )
