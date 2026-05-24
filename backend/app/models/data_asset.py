"""
数据资产模型
DataSource / DataAsset / Metadata
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, SmallInteger, Integer, BigInteger, Text, Float,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class DataSource(Base, UUIDMixin, TimestampMixin):
    """数据源表"""
    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    protocol_type: Mapped[str] = mapped_column(String(20), nullable=False)
    connection_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    device_did: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    mqtt_topic: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    collection_interval_ms: Mapped[int] = mapped_column(Integer, default=5000)
    is_critical: Mapped[bool] = mapped_column(default=False)
    edge_preprocess: Mapped[dict] = mapped_column(JSONB, default={}, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    assets: Mapped[list["DataAsset"]] = relationship(back_populates="source")
    organization = relationship("Organization")

    __table_args__ = (
        Index("idx_source_protocol", "protocol_type"),
        Index("idx_source_org_id", "organization_id"),
        Index("idx_source_device_did", "device_did"),
        Index("idx_source_status", "status"),
    )


class DataAsset(Base, UUIDMixin, TimestampMixin):
    """数据资产表"""
    __tablename__ = "data_assets"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    classification_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=4)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schema_def: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    storage_format: Mapped[str] = mapped_column(String(20), default="parquet")
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    record_count: Mapped[int] = mapped_column(BigInteger, default=0)
    nft_token_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, default=None
    )

    # Relationships
    source: Mapped[Optional["DataSource"]] = relationship(back_populates="assets")
    metadata_entry: Mapped[Optional["Metadata"]] = relationship(back_populates="asset", uselist=False)
    tags: Mapped[list["AssetTag"]] = relationship(back_populates="asset")
    access_logs: Mapped[list["AccessLog"]] = relationship(back_populates="asset")
    quality_reports: Mapped[list["DataQualityReport"]] = relationship(back_populates="asset")
    ratings: Mapped[list["DataAssetRating"]] = relationship(
        back_populates="asset", foreign_keys="DataAssetRating.asset_id"
    )
    owner = relationship("User", foreign_keys=[owner_id])

    __table_args__ = (
        Index("idx_asset_category", "category"),
        Index("idx_asset_level", "classification_level"),
        Index("idx_asset_status", "status"),
        Index("idx_asset_owner_id", "owner_id"),
        Index("idx_asset_org_id", "organization_id"),
        Index("idx_asset_nft_token", "nft_token_id"),
    )


class Metadata(Base, UUIDMixin):
    """元数据表"""
    __tablename__ = "metadata"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False, unique=True
    )
    standard: Mapped[str] = mapped_column(String(50), default="GB/T 36073-2018")
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    lineage_graph: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("metadata.id"), nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    asset: Mapped["DataAsset"] = relationship(back_populates="metadata_entry")

    __table_args__ = (
        Index("idx_meta_asset_id", "asset_id"),
        Index("idx_meta_version", "version"),
    )


class DataAssetRating(Base, UUIDMixin, TimestampMixin):
    """数据资产评价/评分表"""
    __tablename__ = "data_asset_ratings"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    user_name: Mapped[str] = mapped_column(String(100), nullable=False, default="匿名用户")
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=[])

    # Relationships
    asset: Mapped["DataAsset"] = relationship(
        "DataAsset", back_populates="ratings", foreign_keys=[asset_id]
    )

    __table_args__ = (
        Index("idx_rating_asset_id", "asset_id"),
        Index("idx_rating_user_id", "user_id"),
        Index("idx_rating_rating", "rating"),
    )
