"""
安全管控模型
SecurityPolicy / PolicyAssignment / DidDocument / VcRecord / KeyStore / KeyUsageLog / ThreatEvent / ThreatAction
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, SmallInteger, Text, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class SecurityPolicy(Base, UUIDMixin):
    """安全策略表"""
    __tablename__ = "security_policies"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    assignments: Mapped[list["PolicyAssignment"]] = relationship(back_populates="policy")


class PolicyAssignment(Base, UUIDMixin):
    """策略分配表"""
    __tablename__ = "policy_assignments"

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("security_policies.id"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    policy: Mapped["SecurityPolicy"] = relationship(back_populates="assignments")


class DidDocument(Base, UUIDMixin):
    """DID 文档表"""
    __tablename__ = "did_documents"

    did: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    method: Mapped[str] = mapped_column(String(30), nullable=False, default="did:fisco")
    document: Mapped[dict] = mapped_column(JSONB, nullable=False)
    controller: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )


class VcRecord(Base, UUIDMixin):
    """可验证凭证表"""
    __tablename__ = "vc_records"

    vc_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    issuer_did: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_did: Mapped[str] = mapped_column(String(128), nullable=False)
    vc_type: Mapped[str] = mapped_column(String(100), nullable=False)
    claims: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    issued_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class KeyStore(Base, UUIDMixin):
    """密钥存储表"""
    __tablename__ = "key_store"

    key_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    algorithm: Mapped[str] = mapped_column(String(20), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    hierarchy_level: Mapped[str] = mapped_column(String(10), nullable=False)
    parent_key_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    rotated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    usage_logs: Mapped[list["KeyUsageLog"]] = relationship(back_populates="key")


class KeyUsageLog(Base, UUIDMixin):
    """密钥使用日志表"""
    __tablename__ = "key_usage_logs"

    key_id: Mapped[str] = mapped_column(String(64), ForeignKey("key_store.key_id"), nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    key: Mapped["KeyStore"] = relationship(back_populates="usage_logs")

    __table_args__ = (
        Index("idx_key_usage_key_id", "key_id"),
    )


class ThreatEvent(Base, UUIDMixin):
    """威胁事件表"""
    __tablename__ = "threat_events"

    threat_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    indicators: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    affected_resources: Mapped[Optional[list]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="detected")
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    actions: Mapped[list["ThreatAction"]] = relationship(back_populates="threat")


class ThreatAction(Base, UUIDMixin):
    """威胁处置表"""
    __tablename__ = "threat_actions"

    threat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threat_events.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    performed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    threat: Mapped["ThreatEvent"] = relationship(back_populates="actions")
