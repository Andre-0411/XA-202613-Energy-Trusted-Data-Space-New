"""
监控告警服务 - 数据库模型
告警持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Boolean, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class MonitorAlert(Base, UUIDMixin, TimestampMixin):
    """监控告警模型 - 替代 _alerts_store 字典"""
    __tablename__ = "monitor_alerts"
    __table_args__ = (
        Index("idx_monitor_alert_type", "type"),
        Index("idx_monitor_alert_severity", "severity"),
        Index("idx_monitor_alert_status", "status"),
        Index("idx_monitor_alert_fired_at", "fired_at"),
        Index("idx_monitor_alert_source", "source"),
    )

    # 告警信息
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="告警类型"
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="严重程度"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="告警标题"
    )
    message: Mapped[str] = mapped_column(
        Text, nullable=False, comment="告警消息"
    )
    source: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="告警来源"
    )

    # 告警状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="firing", comment="告警状态"
    )
    acknowledged_by: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="确认人"
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="确认时间"
    )

    # 元数据
    alert_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="告警元数据"
    )
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="触发时间"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "id": str(self.id),
            "type": self.type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "metadata": self.alert_metadata,
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
        }