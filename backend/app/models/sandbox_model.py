"""
沙箱服务 - 数据库模型
计算沙箱持久化存储（sandbox_service + compute_sandbox 共用）
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Text, Integer, Float, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


# ==================== sandbox_service.py 使用 ====================

class ComputeSandbox(Base, UUIDMixin, TimestampMixin):
    """计算沙箱模型 - 替代 sandbox_service._sandbox_store 字典"""
    __tablename__ = "compute_sandboxes"
    __table_args__ = (
        Index("idx_sandbox_status", "status"),
        Index("idx_sandbox_created_by", "created_by"),
        Index("idx_sandbox_organization_id", "organization_id"),
        Index("idx_sandbox_task_id", "task_id"),
        Index("idx_sandbox_created_at", "created_at"),
    )

    # 沙箱标识
    sandbox_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="沙箱 ID"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="沙箱名称"
    )

    # 沙箱配置
    algorithm_code: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="算法代码"
    )
    algorithm_hash: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="算法代码哈希"
    )
    input_asset_ids: Mapped[Optional[list[str]]] = mapped_column(
        JSONB, nullable=True, comment="输入资产 ID 列表"
    )
    runtime_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="运行时配置"
    )

    # 沙箱状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending", comment="沙箱状态"
    )

    # 创建信息
    created_by: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="创建者"
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="所属组织 ID"
    )

    # 扫描和导出结果
    scan_result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="安全扫描结果"
    )
    export_result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="导出结果"
    )

    # 关联任务
    task_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="关联计算任务 ID"
    )

    # 时间戳
    destroyed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="销毁时间"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "sandbox_id": self.sandbox_id,
            "name": self.name,
            "status": self.status,
            "algorithm_code": self.algorithm_code,
            "algorithm_hash": self.algorithm_hash,
            "input_asset_ids": self.input_asset_ids,
            "runtime_config": self.runtime_config,
            "created_by": self.created_by,
            "organization_id": self.organization_id,
            "scan_result": self.scan_result,
            "export_result": self.export_result,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "destroyed_at": self.destroyed_at.isoformat() if self.destroyed_at else None,
        }


# ==================== compute_sandbox.py 使用 ====================

class SandboxSession(Base, UUIDMixin, TimestampMixin):
    """沙箱会话模型 - compute_sandbox.py 使用（增强版，含完整生命周期字段）"""
    __tablename__ = "sandbox_sessions"
    __table_args__ = (
        Index("idx_sandbox_session_task_id", "task_id"),
        Index("idx_sandbox_session_status", "status"),
        Index("idx_sandbox_session_created_at", "created_at"),
        Index("idx_sandbox_session_org", "organization_id"),
    )

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, server_default="", comment="沙箱名称",
    )
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compute_tasks.id", ondelete="SET NULL"),
        nullable=True, comment="关联计算任务",
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, nullable=True, comment="沙箱会话 ID",
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True, comment="所属组织",
    )
    container_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="Docker 容器 ID",
    )
    pid: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="进程 ID",
    )
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="subprocess",
        comment="沙箱模式: docker/subprocess",
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="created",
        comment="状态: created/running/completed/failed/timeout/terminated/violation/destroyed",
    )
    algorithm_hash: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="算法代码哈希",
    )
    input_asset_ids: Mapped[Optional[list[str]]] = mapped_column(
        JSONB, nullable=True, comment="输入资产 ID 列表",
    )
    runtime_config: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="运行时配置 (memory_limit, cpu_limit, timeout等)",
    )
    scan_result: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="安全扫描结果",
    )
    export_result: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="出口审核结果",
    )
    memory_limit: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="内存限制 e.g. 2g",
    )
    cpu_limit: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="CPU 限制 e.g. 1.0",
    )
    disk_limit_mb: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="磁盘限制(MB)",
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="300", comment="超时秒数",
    )
    exit_code: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="退出码",
    )
    stdout_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="标准输出摘要",
    )
    stderr_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误输出摘要",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误消息",
    )
    temp_dir: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="临时工作目录",
    )
    work_dir: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="工作目录",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始执行时间",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间",
    )
    destroyed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="销毁时间",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, comment="创建者",
    )

    # Relationships
    resource_usages: Mapped[list["SandboxResourceUsage"]] = relationship(
        back_populates="session",
    )
    violations: Mapped[list["SandboxViolation"]] = relationship(
        back_populates="session",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_id": str(self.task_id) if self.task_id else None,
            "name": self.name,
            "container_id": self.container_id,
            "pid": self.pid,
            "mode": self.mode,
            "status": self.status,
            "algorithm_hash": self.algorithm_hash,
            "input_asset_ids": self.input_asset_ids,
            "runtime_config": self.runtime_config,
            "scan_result": self.scan_result,
            "export_result": self.export_result,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "disk_limit_mb": self.disk_limit_mb,
            "timeout_seconds": self.timeout_seconds,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
            "temp_dir": self.temp_dir,
            "work_dir": self.work_dir,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "destroyed_at": self.destroyed_at.isoformat() if self.destroyed_at else None,
        }


class SandboxResourceUsage(Base, UUIDMixin):
    """沙箱资源使用记录"""
    __tablename__ = "sandbox_resource_usages"
    __table_args__ = (
        Index("idx_sandbox_resource_session_id", "session_id"),
        Index("idx_sandbox_resource_recorded_at", "recorded_at"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sandbox_sessions.id", ondelete="CASCADE"),
        nullable=False, comment="沙箱会话 ID",
    )
    peak_memory_mb: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="峰值内存(MB)",
    )
    avg_cpu_percent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="平均 CPU 使用率(%)",
    )
    disk_used_mb: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="磁盘使用(MB)",
    )
    network_rx_bytes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="网络接收字节数",
    )
    network_tx_bytes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="网络发送字节数",
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="运行时长(秒)",
    )
    cpu_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="CPU 时间(秒)",
    )
    memory_peak_mb: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="峰值内存(MB) - 别名",
    )
    metric_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="指标类型",
    )
    metric_value: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="指标值",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
        comment="记录时间",
    )

    # Relationship
    session: Mapped["SandboxSession"] = relationship(back_populates="resource_usages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "peak_memory_mb": self.peak_memory_mb,
            "avg_cpu_percent": self.avg_cpu_percent,
            "disk_used_mb": self.disk_used_mb,
            "network_rx_bytes": self.network_rx_bytes,
            "network_tx_bytes": self.network_tx_bytes,
            "duration_seconds": self.duration_seconds,
            "cpu_seconds": self.cpu_seconds,
            "metric_type": self.metric_type,
            "metric_value": self.metric_value,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }


class SandboxViolation(Base, UUIDMixin, TimestampMixin):
    """沙箱违规事件"""
    __tablename__ = "sandbox_violations"
    __table_args__ = (
        Index("idx_sandbox_violation_session_id", "session_id"),
        Index("idx_sandbox_violation_type", "violation_type"),
        Index("idx_sandbox_violation_created_at", "created_at"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sandbox_sessions.id", ondelete="CASCADE"),
        nullable=False, comment="沙箱会话 ID",
    )
    violation_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="违规类型: network_access/file_access/process_spawn/dangerous_call/resource_exceeded/data_leak/timeout",
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="medium",
        comment="严重级别: low/medium/high/critical",
    )
    detail: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="违规详情",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="违规描述（别名）",
    )
    source_line: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="触发代码行",
    )
    evidence: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="违规证据",
    )
    action_taken: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="采取措施: logged/blocked/terminated",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
        comment="发生时间",
    )
    violation_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, comment="扩展元数据",
    )

    # Relationship
    session: Mapped["SandboxSession"] = relationship(back_populates="violations")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "violation_type": self.violation_type,
            "severity": self.severity,
            "detail": self.detail,
            "description": self.description,
            "source_line": self.source_line,
            "evidence": self.evidence,
            "action_taken": self.action_taken,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "metadata": self.violation_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
