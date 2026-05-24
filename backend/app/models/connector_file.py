"""
连接器文件/文件集/API代理模型
ConnectorFile / FileSet / ApiProxy
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Text, Boolean, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class FileSet(Base, UUIDMixin):
    """文件集表（一组相关文件）"""
    __tablename__ = "file_sets"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationships
    files: Mapped[List["ConnectorFile"]] = relationship(
        back_populates="file_set", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_fset_org", "organization_id"),
        Index("idx_fset_status", "status"),
    )


class ConnectorFile(Base, UUIDMixin):
    """连接器文件表"""
    __tablename__ = "connector_files"

    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connectors.id"), nullable=False,
    )
    file_set_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("file_sets.id"), nullable=True,
    )
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="存储路径")
    file_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="csv/json/xml/pdf/parquet/xlsx")
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="SHA256内容哈希")
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="数据行数")
    column_schema: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]", comment="列结构定义")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # Relationships
    file_set: Mapped[Optional["FileSet"]] = relationship(back_populates="files")

    __table_args__ = (
        Index("idx_cfile_connector", "connector_id"),
        Index("idx_cfile_set", "file_set_id"),
        Index("idx_cfile_type", "file_type"),
        Index("idx_cfile_status", "status"),
    )


class ApiProxy(Base, UUIDMixin):
    """API代理表"""
    __tablename__ = "api_proxies"

    connector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("connectors.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="目标URL")
    http_method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET", comment="GET/POST/PUT/DELETE")
    request_headers: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    request_params: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="请求参数模板")
    request_body_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="请求体模板")
    response_mapping: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="响应字段映射")
    auth_config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", comment="认证配置")
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=60, comment="每分钟请求限制")
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=30000, comment="超时毫秒")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_aproxy_connector", "connector_id"),
        Index("idx_aproxy_enabled", "is_enabled"),
        Index("idx_aproxy_status", "status"),
    )
