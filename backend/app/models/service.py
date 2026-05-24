"""
运营服务模型
ServiceCatalog / Subscription / BillingRecord
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    String, SmallInteger, Integer, Numeric, Text, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ServiceCatalog(Base, UUIDMixin):
    """服务目录表"""
    __tablename__ = "service_catalog"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_catalog.id"), nullable=True
    )
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pricing_model: Mapped[str] = mapped_column(String(20), nullable=False)
    pricing_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quota_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="service")
    parent: Mapped[Optional["ServiceCatalog"]] = relationship(
        remote_side="ServiceCatalog.id", foreign_keys=[parent_id]
    )


class Subscription(Base, UUIDMixin):
    """服务订阅表"""
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_catalog.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    quota_used: Mapped[int] = mapped_column(Integer, default=0)
    approval_status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    service: Mapped["ServiceCatalog"] = relationship(back_populates="subscriptions")
    billing_records: Mapped[list["BillingRecord"]] = relationship(back_populates="subscription")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])


class BillingRecord(Base, UUIDMixin):
    """计费记录表"""
    __tablename__ = "billing_records"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), nullable=False)
    usage_detail: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="pending")
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    subscription: Mapped["Subscription"] = relationship(back_populates="billing_records")
