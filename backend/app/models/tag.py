"""
标签模型
Tag / AssetTag
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class Tag(Base, UUIDMixin):
    """标签表"""
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    asset_tags: Mapped[list["AssetTag"]] = relationship(back_populates="tag")
    parent: Mapped[Optional["Tag"]] = relationship(remote_side="Tag.id", foreign_keys=[parent_id])

    __table_args__ = (
        Index("idx_tag_dimension", "dimension"),
        Index("idx_tag_name", "name"),
        UniqueConstraint("name", "dimension", name="uq_tag_name_dimension"),
    )


class AssetTag(Base):
    """资产标签关联表"""
    __tablename__ = "asset_tags"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False, primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False, primary_key=True
    )

    # Relationships
    asset = relationship("DataAsset", back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="asset_tags")
