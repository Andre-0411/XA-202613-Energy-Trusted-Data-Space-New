"""
集群服务 - 数据库模型
集群节点和调度持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Integer, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class ClusterNode(Base, UUIDMixin, TimestampMixin):
    """集群节点模型 - 替代 _nodes 字典"""
    __tablename__ = "cluster_nodes"
    __table_args__ = (
        Index("idx_cluster_node_name", "name"),
        Index("idx_cluster_node_type", "node_type"),
        Index("idx_cluster_node_status", "status"),
        Index("idx_cluster_node_region", "region"),
        Index("idx_cluster_node_organization_id", "organization_id"),
    )

    # 节点标识
    node_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="节点 ID"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="节点名称"
    )
    node_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="节点类型"
    )
    endpoint: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="节点端点"
    )
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="区域"
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="所属组织 ID"
    )

    # 节点状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="unknown", comment="节点状态"
    )
    capabilities: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="节点能力"
    )
    active_tasks: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="活跃任务数"
    )

    # 心跳和注册
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后心跳时间"
    )
    registered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="注册时间"
    )
    node_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="节点元数据"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type,
            "endpoint": self.endpoint,
            "region": self.region,
            "organization_id": self.organization_id,
            "status": self.status,
            "capabilities": self.capabilities,
            "active_tasks": self.active_tasks,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "metadata": self.node_metadata,
        }


class TaskDispatch(Base, UUIDMixin, TimestampMixin):
    """任务调度模型 - 替代 _dispatches 字典"""
    __tablename__ = "task_dispatches"
    __table_args__ = (
        Index("idx_task_dispatch_task_id", "task_id"),
        Index("idx_task_dispatch_node_id", "node_id"),
        Index("idx_task_dispatch_status", "status"),
        Index("idx_task_dispatch_dispatched_at", "dispatched_at"),
    )

    # 调度标识
    dispatch_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="调度 ID"
    )
    task_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="任务 ID"
    )
    node_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="节点 ID"
    )
    node_endpoint: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="节点端点"
    )

    # 调度状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending", comment="调度状态"
    )
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="调度时间"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "dispatch_id": self.dispatch_id,
            "task_id": self.task_id,
            "node_id": self.node_id,
            "node_endpoint": self.node_endpoint,
            "status": self.status,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
        }