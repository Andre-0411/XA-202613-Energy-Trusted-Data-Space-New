"""
访问日志模型
AccessLog
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class AccessLog(Base, UUIDMixin):
    """访问日志表"""
    __tablename__ = "access_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    compute_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compute_tasks.id"), nullable=True
    )
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default={}, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    asset = relationship("DataAsset", back_populates="access_logs", lazy="selectin")

    __table_args__ = (
        Index("idx_access_user_id", "user_id"),
        Index("idx_access_asset_id", "asset_id"),
        Index("idx_access_created_at", "created_at"),
    )
