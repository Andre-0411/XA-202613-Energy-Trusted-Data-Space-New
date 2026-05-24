"""
FATE 集成服务 - 数据库模型
FATE 任务持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Float, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class FateJob(Base, UUIDMixin, TimestampMixin):
    """FATE 任务模型 - 替代 _fate_jobs 字典"""
    __tablename__ = "fate_jobs"
    __table_args__ = (
        Index("idx_fate_job_status", "status"),
        Index("idx_fate_job_mode", "mode"),
        Index("idx_fate_job_algorithm", "algorithm"),
        Index("idx_fate_job_created_at", "created_at"),
    )

    # 任务标识
    job_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="FATE 任务 ID"
    )
    mode: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="计算模式"
    )
    algorithm: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="算法名称"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending", comment="任务状态"
    )

    # 任务配置
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="任务配置"
    )

    # 任务结果
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="任务指标"
    )
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="任务结果"
    )
    progress: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="任务进度"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "job_id": self.job_id,
            "mode": self.mode,
            "algorithm": self.algorithm,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "config": self.config,
            "metrics": self.metrics,
            "result": self.result,
            "progress": self.progress,
        }