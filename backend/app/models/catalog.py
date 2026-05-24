"""
数据目录模型
CatalogRegistration / ControlTemplate / AccessScopeRule
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Text, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class CatalogRegistration(Base, UUIDMixin):
    """数据目录登记表"""
    __tablename__ = "catalog_registrations"

    catalog_type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connectors.id"), nullable=True,
    )
    data_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connector_data_sources.id"), nullable=True,
    )
    metadata_discovery_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("metadata_discoveries.id"), nullable=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    security_level: Mapped[str] = mapped_column(String(20), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="public")
    supply_channels: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")
    control_protocol: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    compliance_docs: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")
    api_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    access_rules: Mapped[List["AccessScopeRule"]] = relationship(
        back_populates="catalog", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_catalog_type", "catalog_type"),
        Index("idx_catalog_org", "organization_id"),
        Index("idx_catalog_security", "security_level"),
        Index("idx_catalog_status", "status"),
        Index("idx_catalog_visibility", "visibility"),
    )


class ControlTemplate(Base, UUIDMixin):
    """管控协议模板表"""
    __tablename__ = "control_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template_content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True,
    )
    is_system: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_template_org", "organization_id"),
    )


class AccessScopeRule(Base, UUIDMixin):
    """开放范围管控表"""
    __tablename__ = "access_scope_rules"

    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("catalog_registrations.id"), nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    catalog: Mapped["CatalogRegistration"] = relationship(back_populates="access_rules")

    __table_args__ = (
        Index("idx_scope_catalog", "catalog_id"),
        Index("idx_scope_target", "target_type", "target_id"),
    )
