"""
MFA (多因素认证) 模型
MfaConfig / MfaBackupCode / MfaSession
"""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Boolean, Integer, Text, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class MfaConfig(Base, UUIDMixin, TimestampMixin):
    """MFA 配置表"""
    __tablename__ = "mfa_configs"

    user_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="totp")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    backup_codes: Mapped[List["MfaBackupCode"]] = relationship(
        back_populates="mfa_config", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["MfaSession"]] = relationship(
        back_populates="mfa_config", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_mfa_config_user_id", "user_id"),
        Index("idx_mfa_config_enabled", "enabled"),
    )


class MfaBackupCode(Base, UUIDMixin):
    """MFA 备份码表"""
    __tablename__ = "mfa_backup_codes"

    mfa_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mfa_configs.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    mfa_config: Mapped["MfaConfig"] = relationship(back_populates="backup_codes")

    __table_args__ = (
        Index("idx_mfa_backup_config_id", "mfa_config_id"),
        Index("idx_mfa_backup_code_hash", "code_hash"),
    )


class MfaSession(Base, UUIDMixin):
    """MFA 会话表"""
    __tablename__ = "mfa_sessions"

    mfa_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mfa_configs.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    mfa_config: Mapped["MfaConfig"] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("idx_mfa_session_session_id", "session_id"),
        Index("idx_mfa_session_config_id", "mfa_config_id"),
        Index("idx_mfa_session_expires_at", "expires_at"),
    )
