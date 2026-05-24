"""
MPC 服务 - 数据库模型
多方安全计算会话持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class MpcSession(Base, UUIDMixin, TimestampMixin):
    """MPC 会话模型 - 替代 _mpc_sessions 字典"""
    __tablename__ = "mpc_sessions"
    __table_args__ = (
        Index("idx_mpc_session_status", "status"),
        Index("idx_mpc_session_protocol", "protocol"),
        Index("idx_mpc_session_created_at", "created_at"),
    )

    # 会话标识
    session_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="MPC 会话 ID"
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="关联的计算任务 ID"
    )

    # 会话配置
    protocol: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="MPC 协议"
    )
    participants: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, comment="参与者列表"
    )
    party_endpoints: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="参与方端点映射"
    )

    # 会话状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending", comment="会话状态"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "protocol": self.protocol,
            "participants": self.participants,
            "status": self.status,
            "party_endpoints": self.party_endpoints,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }