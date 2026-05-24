"""
连接器模型
Connector / ConnectorDataSource / MetadataDiscovery
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Integer, BigInteger, Text, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Connector(Base, UUIDMixin):
    """连接器表"""
    __tablename__ = "connectors"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(20), nullable=False, default="lite")
    version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    deployment_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )

    # Relationships
    data_sources: Mapped[List["ConnectorDataSource"]] = relationship(
        back_populates="connector", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_connector_org", "organization_id"),
        Index("idx_connector_status", "status"),
        Index("idx_connector_type", "connector_type"),
    )


class ConnectorDataSource(Base, UUIDMixin):
    """数据源配置表（连接器侧）"""
    __tablename__ = "connector_data_sources"

    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connectors.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    db_type: Mapped[str] = mapped_column(String(30), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    database_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    schema_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    connector: Mapped["Connector"] = relationship(back_populates="data_sources")
    discoveries: Mapped[List["MetadataDiscovery"]] = relationship(
        back_populates="data_source", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_cds_connector", "connector_id"),
        Index("idx_cds_status", "status"),
    )


class MetadataDiscovery(Base, UUIDMixin):
    """元数据发现记录表"""
    __tablename__ = "metadata_discoveries"

    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connector_data_sources.id"), nullable=False,
    )
    table_name: Mapped[str] = mapped_column(String(200), nullable=False)
    table_comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    row_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    columns: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    security_level: Mapped[str] = mapped_column(String(20), nullable=False, default="public")
    sensitive_fields: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    data_source: Mapped["ConnectorDataSource"] = relationship(back_populates="discoveries")

    __table_args__ = (
        Index("idx_discovery_source", "data_source_id"),
        Index("idx_discovery_table", "table_name"),
        Index("idx_discovery_security", "security_level"),
    )
