"""
MQTT 数据采集模型
MqttDevice / MqttDataRecord / MqttAlarm
"""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Boolean, Integer, BigInteger, Float, Text, ForeignKey, Index, DateTime, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class MqttDevice(Base, UUIDMixin, TimestampMixin):
    """MQTT 设备表"""
    __tablename__ = "mqtt_devices"

    device_did: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    enterprise: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    capacity_kw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="online")
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    device_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default={})

    # Relationships
    data_records: Mapped[List["MqttDataRecord"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    alarms: Mapped[List["MqttAlarm"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_mqtt_device_did", "device_did"),
        Index("idx_mqtt_device_status", "status"),
        Index("idx_mqtt_device_enterprise", "enterprise"),
    )


class MqttDataRecord(Base, UUIDMixin):
    """MQTT 数据采集记录表"""
    __tablename__ = "mqtt_data_records"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mqtt_devices.id", ondelete="CASCADE"), nullable=False
    )
    device_did: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    device: Mapped["MqttDevice"] = relationship(back_populates="data_records")

    __table_args__ = (
        Index("idx_mqtt_data_device_did", "device_did"),
        Index("idx_mqtt_data_data_type", "data_type"),
        Index("idx_mqtt_data_timestamp", "timestamp"),
        Index("idx_mqtt_data_device_type", "device_did", "data_type"),
        Index("idx_mqtt_data_stored_at", "stored_at"),
    )


class MqttAlarm(Base, UUIDMixin):
    """MQTT 告警记录表"""
    __tablename__ = "mqtt_alarms"

    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mqtt_devices.id", ondelete="SET NULL"), nullable=True
    )
    device_did: Mapped[str] = mapped_column(String(128), nullable=False)
    alarm_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default={})
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    device: Mapped[Optional["MqttDevice"]] = relationship(back_populates="alarms")

    __table_args__ = (
        Index("idx_mqtt_alarm_device_did", "device_did"),
        Index("idx_mqtt_alarm_type", "alarm_type"),
        Index("idx_mqtt_alarm_severity", "severity"),
        Index("idx_mqtt_alarm_timestamp", "timestamp"),
    )
