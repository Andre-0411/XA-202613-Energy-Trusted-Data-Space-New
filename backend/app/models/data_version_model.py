"""
数据版本服务 - 数据库模型
数据版本和标签持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Integer, Text, func, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class DataVersion(Base, UUIDMixin, TimestampMixin):
    """数据版本模型 - 替代 _versions 字典"""
    __tablename__ = "data_versions"
    __table_args__ = (
        Index("idx_data_version_asset_id", "asset_id"),
        Index("idx_data_version_version_number", "version_number"),
        Index("idx_data_version_parent_id", "parent_version_id"),
        Index("idx_data_version_created_at", "created_at"),
        UniqueConstraint("asset_id", "version_number", name="uq_data_version_asset_version"),
    )

    # 版本标识
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="版本号"
    )
    asset_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="资产 ID"
    )

    # 版本信息
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="版本描述"
    )
    data_hash: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="数据哈希"
    )
    size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="数据大小(bytes)"
    )
    record_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="记录数"
    )

    # 版本元数据
    schema_info: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="Schema 信息"
    )
    diff_from_parent: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="与父版本的差异"
    )
    version_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="版本元数据"
    )

    # 父版本
    parent_version_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="父版本 ID"
    )

    # 创建信息
    created_by: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="创建者"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "id": str(self.id),
            "version_number": self.version_number,
            "asset_id": self.asset_id,
            "description": self.description,
            "data_hash": self.data_hash,
            "size_bytes": self.size_bytes,
            "record_count": self.record_count,
            "schema_info": self.schema_info,
            "diff_from_parent": self.diff_from_parent,
            "metadata": self.version_metadata,
            "parent_version_id": self.parent_version_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VersionTag(Base, UUIDMixin, TimestampMixin):
    """版本标签模型 - 替代 _tags 字典"""
    __tablename__ = "version_tags"
    __table_args__ = (
        Index("idx_version_tag_name", "tag_name"),
        Index("idx_version_tag_asset_id", "asset_id"),
        Index("idx_version_tag_version_id", "version_id"),
        UniqueConstraint("asset_id", "tag_name", name="uq_version_tag_asset_tag"),
    )

    tag_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="标签名称"
    )
    asset_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="资产 ID"
    )
    version_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="版本 ID"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="标签描述"
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="创建者"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "tag_name": self.tag_name,
            "asset_id": self.asset_id,
            "version_id": self.version_id,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CurrentVersion(Base, UUIDMixin, TimestampMixin):
    """当前版本模型 - 替代 _current 字典"""
    __tablename__ = "current_versions"
    __table_args__ = (
        Index("idx_current_version_asset_id", "asset_id"),
        UniqueConstraint("asset_id", name="uq_current_version_asset"),
    )

    asset_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="资产 ID"
    )
    version_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="当前版本 ID"
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="当前版本号"
    )
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="更新者"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "asset_id": self.asset_id,
            "version_id": self.version_id,
            "version_number": self.version_number,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }