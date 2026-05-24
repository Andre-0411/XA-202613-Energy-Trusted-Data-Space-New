"""
AI Agent 对话历史模型
持久化存储 Agent 对话记录，替代内存 dict
"""
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import String, Text, DateTime, Integer, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class AgentConversation(Base, UUIDMixin, TimestampMixin):
    """Agent 对话历史表"""
    __tablename__ = "agent_conversations"
    __table_args__ = (
        Index("idx_agent_conv_user_id", "user_id"),
        Index("idx_agent_conv_agent_type", "agent_type"),
        Index("idx_agent_conv_conversation_id", "conversation_id", unique=True),
    )

    user_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="用户 ID"
    )
    agent_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Agent 类型: query/trade/security/dispatch"
    )
    conversation_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, comment="对话 ID"
    )
    messages: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]", comment="消息列表 [{role, content}]"
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="消息数量"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "agent_type": self.agent_type,
            "conversation_id": self.conversation_id,
            "messages": self.messages,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
