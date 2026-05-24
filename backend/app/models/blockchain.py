"""
区块链模型
BlockchainTransaction / NftAsset / EvidenceRecord
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, BigInteger, Text, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class NftAsset(Base, UUIDMixin):
    """NFT 资产表"""
    __tablename__ = "nft_assets"

    token_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id"), nullable=False
    )
    owner_did: Mapped[str] = mapped_column(String(128), nullable=False)
    creator_did: Mapped[str] = mapped_column(String(128), nullable=False)
    token_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    evidence_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    block_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    asset = relationship("DataAsset")


class EvidenceRecord(Base, UUIDMixin):
    """存证记录表"""
    __tablename__ = "evidence_records"

    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    data_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), default="v1.0")
    evidence_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    block_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    __table_args__ = (
        Index("idx_evidence_node_type", "node_type"),
        Index("idx_evidence_resource", "resource_id", "resource_type"),
        Index("idx_evidence_tx_hash", "tx_hash"),
    )


class BlockchainTransaction(Base, UUIDMixin):
    """链上交易记录表"""
    __tablename__ = "blockchain_transactions"

    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    contract_address: Mapped[str] = mapped_column(String(128), nullable=False)
    method: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    from_address: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    block_number: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    gas_used: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationship to evidence
    evidence: Mapped[Optional["EvidenceRecord"]] = relationship(
        primaryjoin="BlockchainTransaction.tx_hash == foreign(EvidenceRecord.tx_hash)",
        uselist=False,
    )
