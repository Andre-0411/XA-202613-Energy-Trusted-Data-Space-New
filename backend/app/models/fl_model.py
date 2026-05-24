"""
联邦学习服务 - 数据库模型
FL 模型持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class FlModel(Base, UUIDMixin, TimestampMixin):
    """联邦学习模型 - 替代 _model_store 字典"""
    __tablename__ = "fl_models"
    __table_args__ = (
        Index("idx_fl_model_task_id", "task_id"),
        Index("idx_fl_model_status", "status"),
        Index("idx_fl_model_algorithm", "algorithm"),
        Index("idx_fl_model_created_at", "created_at"),
    )

    # 模型标识
    model_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, comment="模型 ID"
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="关联的计算任务 ID"
    )

    # 模型信息
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="模型名称"
    )
    algorithm: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="算法名称"
    )
    participants: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, comment="参与者列表"
    )

    # 模型参数
    model_params: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="模型参数"
    )

    # 模型状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending", comment="模型状态"
    )

    # 评估信息
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="评估指标"
    )
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="评估时间"
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，兼容原有接口"""
        return {
            "model_id": self.model_id,
            "task_id": self.task_id,
            "name": self.name,
            "algorithm": self.algorithm,
            "participants": self.participants,
            "model_params": self.model_params,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metrics": self.metrics,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }