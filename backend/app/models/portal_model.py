"""
门户服务 - 数据库模型
门户配置持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Boolean, Integer, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class QuickLink(Base, UUIDMixin, TimestampMixin):
    """快捷链接模型 - 替代 _quick_links 字典"""
    __tablename__ = "portal_quick_links"
    __table_args__ = (
        Index("idx_portal_quicklink_user_id", "user_id"),
        Index("idx_portal_quicklink_sort_order", "sort_order"),
    )

    user_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="用户 ID"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="链接标题"
    )
    url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="链接地址"
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="图标"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="排序顺序"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "url": self.url,
            "icon": self.icon,
            "sort_order": self.sort_order,
        }


class PortalNotification(Base, UUIDMixin, TimestampMixin):
    """门户通知模型 - 替代 _notifications 字典"""
    __tablename__ = "portal_notifications"
    __table_args__ = (
        Index("idx_portal_notif_user_id", "user_id"),
        Index("idx_portal_notif_read", "read"),
        Index("idx_portal_notif_type", "notification_type"),
        Index("idx_portal_notif_priority", "priority"),
        Index("idx_portal_notif_category", "category"),
        Index("idx_portal_notif_created_at", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="用户 ID"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="通知标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="通知内容"
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="info", comment="通知类型: info/warning/error/success"
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="normal", comment="优先级: low/normal/high/urgent"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="system", comment="分类: system/task/security/billing"
    )
    target_users: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="目标用户ID列表，null表示全员"
    )
    sender: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="system", comment="发送者"
    )
    read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", comment="是否已读"
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="阅读时间"
    )
    link: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="关联链接"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "type": self.notification_type,
            "priority": self.priority,
            "category": self.category,
            "target_users": self.target_users,
            "sender": self.sender,
            "read": self.read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "link": self.link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PortalLayout(Base, UUIDMixin, TimestampMixin):
    """门户布局配置模型 - 替代 _layouts 字典"""
    __tablename__ = "portal_layouts"
    __table_args__ = (
        Index("idx_portal_layout_user_id", "user_id"),
        Index("idx_portal_layout_default", "is_default"),
    )

    user_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="用户 ID"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="布局名称"
    )
    layout_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="布局配置"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", comment="是否默认"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "layout": self.layout_config,
            "is_default": self.is_default,
        }


class ActivityLog(Base, UUIDMixin, TimestampMixin):
    """活动日志模型 - 替代 _activity_logs 字典"""
    __tablename__ = "portal_activity_logs"
    __table_args__ = (
        Index("idx_portal_activity_user_id", "user_id"),
        Index("idx_portal_activity_action", "action"),
        Index("idx_portal_activity_created_at", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="用户 ID"
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="操作类型"
    )
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="操作详情"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True, comment="IP 地址"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }