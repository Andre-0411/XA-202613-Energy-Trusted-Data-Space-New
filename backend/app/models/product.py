"""
数据产品模型
ProductProject / ProjectMember / DataProduct / ProductAcceptance
ProductPublishRequest / ProductUnpublishRequest
ProductSubscription / ProductDelivery
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


class ProductProject(Base, UUIDMixin):
    """数据产品项目表"""
    __tablename__ = "product_projects"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_type: Mapped[str] = mapped_column(String(30), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    data_sources: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    members: Mapped[List["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )
    products: Mapped[List["DataProduct"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_project_org", "organization_id"),
        Index("idx_project_owner", "owner_id"),
        Index("idx_project_type", "project_type"),
        Index("idx_project_status", "status"),
    )


class ProjectMember(Base, UUIDMixin):
    """项目成员表"""
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_projects.id"), nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    project: Mapped["ProductProject"] = relationship(back_populates="members")

    __table_args__ = (
        Index("idx_pm_project", "project_id"),
        Index("idx_pm_user", "user_id"),
        Index("uq_project_member", "project_id", "user_id", unique=True),
    )


class DataProduct(Base, UUIDMixin):
    """数据产品表"""
    __tablename__ = "data_products"

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_projects.id"), nullable=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_type: Mapped[str] = mapped_column(String(30), nullable=False)
    compute_engine: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    technical_spec: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    pricing: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    delivery_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    compliance_docs: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")
    control_protocol: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="development")
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    project: Mapped[Optional["ProductProject"]] = relationship(back_populates="products")

    __table_args__ = (
        Index("idx_product_project", "project_id"),
        Index("idx_product_org", "organization_id"),
        Index("idx_product_type", "product_type"),
        Index("idx_product_status", "status"),
    )


class ProductAcceptance(Base, UUIDMixin):
    """产品验收记录表"""
    __tablename__ = "product_acceptances"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_products.id"), nullable=False,
    )
    acceptor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    test_result: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_acceptance_product", "product_id"),
    )


class ProductPublishRequest(Base, UUIDMixin):
    """产品上架申请表"""
    __tablename__ = "product_publish_requests"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_products.id"), nullable=False,
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    review_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    control_protocol: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    compliance_docs: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")
    pricing_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_publish_product", "product_id"),
        Index("idx_publish_status", "status"),
        Index("idx_publish_deadline", "review_deadline"),
    )


class ProductUnpublishRequest(Base, UUIDMixin):
    """产品下架申请表"""
    __tablename__ = "product_unpublish_requests"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_products.id"), nullable=False,
    )
    applicant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_unpublish_product", "product_id"),
    )


class ProductSubscription(Base, UUIDMixin):
    """产品订阅申请表"""
    __tablename__ = "product_subscriptions"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_products.id"), nullable=False,
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
    delivery_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
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
    deliveries: Mapped[List["ProductDelivery"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_psub_product", "product_id"),
        Index("idx_psub_subscriber", "subscriber_id"),
        Index("idx_psub_status", "status"),
    )


class ProductDelivery(Base, UUIDMixin):
    """产品交付记录表"""
    __tablename__ = "product_deliveries"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_subscriptions.id"), nullable=False,
    )
    delivery_type: Mapped[str] = mapped_column(String(30), nullable=False)
    delivery_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    access_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    subscription: Mapped["ProductSubscription"] = relationship(back_populates="deliveries")

    __table_args__ = (
        Index("idx_pdelivery_sub", "subscription_id"),
    )
