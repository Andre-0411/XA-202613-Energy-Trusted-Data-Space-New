"""
TEE 服务 - 数据库模型
可信执行环境实例持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class TeeInstance(Base, UUIDMixin, TimestampMixin):
    """TEE 实例模型 - 替代 _tee_instances 字典"""
    __tablename__ = "tee_instances"
    __table_args__ = (
        Index("idx_tee_instance_status", "status"),
        Index("idx_tee_instance_runtime", "runtime"),
        Index("idx_tee_instance_created_at", "created_at"),
    )

    # 实例标识
    instance_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="TEE 实例 ID"
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="关联的计算任务 ID"
    )

    # 运行时配置
    runtime: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="TEE 运行时"
    )
    enclave_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="飞地配置"
    )

    # 实例状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending", comment="实例状态"
    )

    # 测量值
    mr_enclave: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="飞地测量值"
    )
    mr_signer: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="签名者测量值"
    )
    ra_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="远程证明状态"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "instance_id": self.instance_id,
            "task_id": self.task_id,
            "runtime": self.runtime,
            "status": self.status,
            "enclave_config": self.enclave_config,
            "mr_enclave": self.mr_enclave,
            "mr_signer": self.mr_signer,
            "ra_status": self.ra_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }