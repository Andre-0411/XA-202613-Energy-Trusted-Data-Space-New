"""
同态加密服务 - 数据库模型
HE 密钥和密文持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Integer, func, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class HeKey(Base, UUIDMixin, TimestampMixin):
    """HE 密钥模型 - 替代 _he_keys 字典"""
    __tablename__ = "he_keys"
    __table_args__ = (
        Index("idx_he_key_scheme", "scheme"),
        Index("idx_he_key_created_at", "created_at"),
    )

    # 密钥标识
    key_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="HE 密钥 ID"
    )

    # 密钥参数
    scheme: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="加密方案"
    )
    poly_modulus_degree: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="多项式模数度"
    )
    coeff_modulus_bits: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="系数模数位数"
    )

    # 密钥哈希（不存储实际密钥）
    public_key_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="公钥哈希"
    )
    secret_key_hash: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="私钥哈希"
    )

    # 序列化密钥数据 (base64 encoded TenSEAL context)
    key_data: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="序列化的 TenSEAL Context (base64)"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "key_id": self.key_id,
            "scheme": self.scheme,
            "poly_modulus_degree": self.poly_modulus_degree,
            "coeff_modulus_bits": self.coeff_modulus_bits,
            "public_key_hash": self.public_key_hash,
            "secret_key_hash": self.secret_key_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class HeCiphertext(Base, UUIDMixin, TimestampMixin):
    """HE 密文模型 - 替代 _he_ciphertexts 字典"""
    __tablename__ = "he_ciphertexts"
    __table_args__ = (
        Index("idx_he_ciphertext_key_id", "key_id"),
        Index("idx_he_ciphertext_scheme", "scheme"),
        Index("idx_he_ciphertext_asset_id", "asset_id"),
        Index("idx_he_ciphertext_created_at", "created_at"),
    )

    # 密文标识
    ciphertext_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="密文 ID"
    )
    key_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="使用的密钥 ID"
    )

    # 密文参数
    scheme: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="加密方案"
    )
    asset_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="关联资产 ID"
    )
    size_params: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="大小参数"
    )

    # 序列化密文数据 (base64 encoded TenSEAL vector)
    ciphertext_data: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="序列化的密文向量 (base64)"
    )

    # 来源信息
    source_operation: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="来源操作"
    )
    source_ciphertexts: Mapped[Optional[list[str]]] = mapped_column(
        JSONB, nullable=True, comment="来源密文 ID 列表"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "ciphertext_id": self.ciphertext_id,
            "key_id": self.key_id,
            "scheme": self.scheme,
            "asset_id": self.asset_id,
            "size_params": self.size_params,
            "source_operation": self.source_operation,
            "source_ciphertexts": self.source_ciphertexts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }