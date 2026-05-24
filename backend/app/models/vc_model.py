"""
VC 服务 - 数据库模型
可验证凭证持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Boolean, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class VerifiableCredential(Base, UUIDMixin, TimestampMixin):
    """可验证凭证模型 - 替代 _vc_store 字典"""
    __tablename__ = "verifiable_credentials"
    __table_args__ = (
        Index("idx_vc_issuer_did", "issuer_did"),
        Index("idx_vc_subject_did", "subject_did"),
        Index("idx_vc_revoked", "revoked"),
        Index("idx_vc_issued_at", "issued_at"),
    )

    # 凭证内容
    document: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="凭证文档"
    )

    # 发行信息
    issuer_did: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="发行者 DID"
    )
    subject_did: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="主体 DID"
    )

    # 状态
    revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", comment="是否已撤销"
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="发行时间"
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="撤销时间"
    )
    revoked_by: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="撤销者"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "id": str(self.id),
            "document": self.document,
            "issuer_did": self.issuer_did,
            "subject_did": self.subject_did,
            "revoked": self.revoked,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_by": self.revoked_by,
        }


class RevocationEntry(Base, UUIDMixin, TimestampMixin):
    """撤销列表条目模型 - 替代 _revocation_list set"""
    __tablename__ = "vc_revocation_list"
    __table_args__ = (
        Index("idx_revocation_vc_id", "vc_id"),
        Index("idx_revocation_revoked_at", "revoked_at"),
    )

    vc_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, comment="被撤销的凭证 ID"
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="撤销原因"
    )
    revoked_by: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="撤销者"
    )
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="撤销时间"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "vc_id": self.vc_id,
            "reason": self.reason,
            "revoked_by": self.revoked_by,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }