"""
计算任务模型
ComputeTask / DagDefinition / TaskSignature
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, SmallInteger, Integer, Text, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class DagDefinition(Base, UUIDMixin, TimestampMixin):
    """DAG 定义表"""
    __tablename__ = "dag_definitions"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nodes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    edges: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    tasks: Mapped[list["ComputeTask"]] = relationship(back_populates="dag")


class ComputeTask(Base, UUIDMixin, TimestampMixin):
    """计算任务表"""
    __tablename__ = "compute_tasks"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scenario: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    dag_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dag_definitions.id"), nullable=True
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_asset_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(SmallInteger, default=0)
    result_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    result_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )

    # Relationships
    dag: Mapped[Optional["DagDefinition"]] = relationship(back_populates="tasks")
    signatures: Mapped[list["TaskSignature"]] = relationship(back_populates="task")

    __table_args__ = (
        Index("idx_task_type", "task_type"),
        Index("idx_task_status", "status"),
        Index("idx_task_created_by", "created_by"),
        Index("idx_task_scenario", "scenario"),
    )


class TaskSignature(Base, UUIDMixin):
    """任务签名表"""
    __tablename__ = "task_signatures"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compute_tasks.id"), nullable=False
    )
    signer_did: Mapped[str] = mapped_column(String(128), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(
        nullable=False, default=lambda: datetime.now()
    )

    # Relationships
    task: Mapped["ComputeTask"] = relationship(back_populates="signatures")

    __table_args__ = (
        UniqueConstraint("task_id", "signer_did", name="uq_task_signer"),
    )
