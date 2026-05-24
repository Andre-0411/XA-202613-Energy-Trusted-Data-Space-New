"""
SSO (单点登录) 模型
SsoProvider / SsoSession / SsoPendingAuth
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


class SsoProvider(Base, UUIDMixin, TimestampMixin):
    """SSO 提供者配置表"""
    __tablename__ = "sso_providers"

    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)  # oauth2/saml2/oidc
    client_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    client_secret: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    authorize_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    token_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    userinfo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    redirect_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    scopes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=["openid", "profile", "email"])
    metadata_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    sessions: Mapped[List["SsoSession"]] = relationship(
        back_populates="provider",
        foreign_keys="SsoSession.provider_id_ref",
        primaryjoin="SsoSession.provider_id_ref == SsoProvider.provider_id",
    )

    __table_args__ = (
        Index("idx_sso_provider_provider_id", "provider_id"),
        Index("idx_sso_provider_enabled", "enabled"),
    )


class SsoSession(Base, UUIDMixin):
    """SSO 会话表"""
    __tablename__ = "sso_sessions"

    session_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_id_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    provider: Mapped["SsoProvider"] = relationship(
        back_populates="sessions",
        foreign_keys=[provider_id_ref],
        primaryjoin="SsoSession.provider_id_ref == SsoProvider.provider_id",
    )

    __table_args__ = (
        Index("idx_sso_session_session_id", "session_id"),
        Index("idx_sso_session_user_id", "user_id"),
        Index("idx_sso_session_provider", "provider_id_ref"),
        Index("idx_sso_session_expires_at", "expires_at"),
    )


class SsoPendingAuth(Base, UUIDMixin):
    """SSO 待处理授权表"""
    __tablename__ = "sso_pending_auths"

    state: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    redirect_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("idx_sso_pending_state", "state"),
        Index("idx_sso_pending_expires_at", "expires_at"),
    )
