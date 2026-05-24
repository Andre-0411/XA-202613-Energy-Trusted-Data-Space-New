"""
ZKP 服务 - 数据库模型
零知识证明持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Boolean, Integer, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class ZkpProof(Base, UUIDMixin, TimestampMixin):
    """零知识证明模型 - 替代 _proof_store 字典"""
    __tablename__ = "zkp_proofs"
    __table_args__ = (
        Index("idx_zkp_proof_type", "proof_type"),
        Index("idx_zkp_proof_prover_did", "prover_did"),
        Index("idx_zkp_proof_circuit_id", "circuit_id"),
        Index("idx_zkp_proof_verified", "verified"),
        Index("idx_zkp_proof_created_at", "created_at"),
    )

    # 证明信息
    proof_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="证明类型"
    )
    prover_did: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="证明者 DID"
    )
    circuit_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="电路 ID"
    )

    # 证明数据
    public_inputs: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="公开输入"
    )
    proof_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="证明数据"
    )

    # 范围证明特定字段
    messages_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="消息数量"
    )
    range_min: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="范围最小值"
    )
    range_max: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="范围最大值"
    )

    # 验证状态
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", comment="是否已验证"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="验证时间"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        result = {
            "id": str(self.id),
            "proof_type": self.proof_type,
            "prover_did": self.prover_did,
            "circuit_id": self.circuit_id,
            "public_inputs": self.public_inputs,
            "proof_data": self.proof_data,
            "verified": self.verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        # range 证明特定字段
        if self.proof_type == "range":
            result["messages_count"] = self.messages_count
            result["range"] = {
                "min": self.range_min,
                "max": self.range_max,
            }
        return result