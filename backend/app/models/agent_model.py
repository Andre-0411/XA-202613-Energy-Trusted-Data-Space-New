"""
智能体管理服务 - 数据库模型
知识库、文档和智能体配置持久化存储
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import String, DateTime, Boolean, Integer, Float, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class KnowledgeBase(Base, UUIDMixin, TimestampMixin):
    """知识库模型 - 替代 _knowledge_bases 字典"""
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        Index("idx_kb_name", "name"),
        Index("idx_kb_organization_id", "organization_id"),
    )

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="知识库名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="知识库描述"
    )
    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="所属组织 ID"
    )
    embedding_model: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="text-embedding-ada-002", comment="嵌入模型"
    )
    chunk_size: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1000", comment="分块大小"
    )
    chunk_overlap: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="200", comment="分块重叠"
    )
    document_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="文档数量"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="active", comment="状态"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "organization_id": self.organization_id,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "document_count": self.document_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeDocument(Base, UUIDMixin, TimestampMixin):
    """知识文档模型 - 替代 _documents 字典"""
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        Index("idx_kdoc_kb_id", "knowledge_base_id"),
        Index("idx_kdoc_status", "status"),
        Index("idx_kdoc_filename", "filename"),
    )

    knowledge_base_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="所属知识库 ID"
    )
    filename: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="文件名"
    )
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="文件类型"
    )
    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="文件大小(bytes)"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="分块数量"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="processing", comment="处理状态"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="错误消息"
    )
    doc_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, comment="文档元数据"
    )
    uploaded_by: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="上传者"
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="文档内容"
    )
    embedding: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="文档向量"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "knowledge_base_id": self.knowledge_base_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "error_message": self.error_message,
            "metadata": self.doc_metadata,
            "uploaded_by": self.uploaded_by,
            "has_content": self.content is not None,
            "has_embedding": self.embedding is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentConfig(Base, UUIDMixin, TimestampMixin):
    """智能体配置模型 - 替代 _agent_configs 字典"""
    __tablename__ = "agent_configs"
    __table_args__ = (
        Index("idx_agent_name", "name"),
        Index("idx_agent_type", "agent_type"),
        Index("idx_agent_organization_id", "organization_id"),
        Index("idx_agent_enabled", "enabled"),
    )

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="智能体名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="智能体描述"
    )
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="智能体类型"
    )
    organization_id: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="所属组织 ID"
    )

    # 模型配置
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="gpt-3.5-turbo", comment="模型名称"
    )
    model_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="openai", comment="模型提供商"
    )
    temperature: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.7", comment="温度参数"
    )
    max_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="2000", comment="最大 token 数"
    )
    system_prompt: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="系统提示词"
    )

    # 知识库关联
    knowledge_base_ids: Mapped[Optional[list[str]]] = mapped_column(
        JSONB, nullable=True, comment="关联知识库 ID 列表"
    )
    tools: Mapped[Optional[list[str]]] = mapped_column(
        JSONB, nullable=True, comment="可用工具列表"
    )

    # 状态
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", comment="是否启用"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", comment="使用次数"
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后使用时间"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "organization_id": self.organization_id,
            "system_prompt": self.system_prompt,  # 顶层 system_prompt（前端期望）
            "model_config": {
                "model_name": self.model_name,
                "model_provider": self.model_provider,
                "provider": self.model_provider,  # 前端别名
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "system_prompt": self.system_prompt,
                "base_url": "",  # 前端期望此字段
            },
            "knowledge_base_ids": self.knowledge_base_ids,
            "tools": self.tools,
            "enabled": self.enabled,
            "usage_count": self.usage_count,
            "total_queries": self.usage_count,  # 前端期望的字段名
            "avg_response_time": 0,  # 前端期望此字段（默认 0）
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }