"""
SLA 服务 - 数据库模型
SLA 配置和报告持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Boolean, Float, Integer, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class SLAConfig(Base, UUIDMixin, TimestampMixin):
    """SLA 配置模型 - 替代 _sla_configs 字典"""
    __tablename__ = "sla_configs"
    __table_args__ = (
        Index("idx_sla_config_service_name", "service_name"),
        Index("idx_sla_config_enabled", "enabled"),
    )

    service_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="服务名称"
    )
    availability_target: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="99.9", comment="可用性目标(%)"
    )
    response_time_target: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="500", comment="响应时间目标(ms)"
    )
    error_rate_target: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0", comment="错误率目标(%)"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="配置描述"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", comment="是否启用"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "availability_target": self.availability_target,
            "response_time_target": self.response_time_target,
            "error_rate_target": self.error_rate_target,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SLAReport(Base, UUIDMixin, TimestampMixin):
    """SLA 报告模型 - 替代 _sla_reports 字典"""
    __tablename__ = "sla_reports"
    __table_args__ = (
        Index("idx_sla_report_service_name", "service_name"),
        Index("idx_sla_report_period_start", "period_start"),
        Index("idx_sla_report_period_end", "period_end"),
    )

    service_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="服务名称"
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="报告期开始"
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="报告期结束"
    )

    # SLA 指标
    availability: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="实际可用性(%)"
    )
    avg_response_time: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="平均响应时间(ms)"
    )
    error_rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="实际错误率(%)"
    )
    total_requests: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="总请求数"
    )
    failed_requests: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="失败请求数"
    )

    # 报告状态
    met_sla: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="是否满足 SLA"
    )
    report_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="详细报告数据"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "availability": self.availability,
            "avg_response_time": self.avg_response_time,
            "error_rate": self.error_rate,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "met_sla": self.met_sla,
            "report_data": self.report_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SLAAlertConfig(Base, UUIDMixin, TimestampMixin):
    """SLA 告警配置模型 - 替代 _sla_alerts 字典"""
    __tablename__ = "sla_alert_configs"
    __table_args__ = (
        Index("idx_sla_alert_service_name", "service_name"),
        Index("idx_sla_alert_enabled", "enabled"),
    )

    service_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="服务名称"
    )
    metric: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="监控指标"
    )
    threshold: Mapped[float] = mapped_column(
        Float, nullable=False, comment="告警阈值"
    )
    operator: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="比较操作符"
    )
    notification_channels: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, comment="通知渠道"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", comment="是否启用"
    )
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后触发时间"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "metric": self.metric,
            "threshold": self.threshold,
            "operator": self.operator,
            "notification_channels": self.notification_channels,
            "enabled": self.enabled,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
        }


class MetricHistory(Base, UUIDMixin, TimestampMixin):
    """指标历史模型 - 替代 _metric_history 字典"""
    __tablename__ = "sla_metric_history"
    __table_args__ = (
        Index("idx_metric_history_service_name", "service_name"),
        Index("idx_metric_history_metric", "metric"),
        Index("idx_metric_history_timestamp", "timestamp"),
    )

    service_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="服务名称"
    )
    metric: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="指标名称"
    )
    value: Mapped[float] = mapped_column(
        Float, nullable=False, comment="指标值"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="采集时间"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "service_name": self.service_name,
            "metric": self.metric,
            "value": self.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }