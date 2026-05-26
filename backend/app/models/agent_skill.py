"""
Agent 技能模型
支持技能的存储、检索和学习
"""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, Integer, Float, Boolean, Index, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class AgentSkill(Base, UUIDMixin):
    """Agent技能表"""
    __tablename__ = "agent_skills"

    # 基本信息
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, comment="技能名称")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="技能描述")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general", comment="技能类别")
    
    # 技能内容
    instructions: Mapped[str] = mapped_column(Text, nullable=False, comment="技能执行指令")
    examples: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="示例输入输出")
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, comment="参数定义")
    
    # 触发条件
    trigger_patterns: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, comment="触发模式关键词")
    trigger_keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, comment="触发关键词")
    intent_types: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, comment="意图类型")
    
    # 使用统计
    use_count: Mapped[int] = mapped_column(Integer, default=0, comment="使用次数")
    success_count: Mapped[int] = mapped_column(Integer, default=0, comment="成功次数")
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, comment="成功率")
    avg_execution_time: Mapped[float] = mapped_column(Float, default=0.0, comment="平均执行时间(ms)")
    
    # 学习信息
    source: Mapped[str] = mapped_column(String(50), default="manual", comment="来源: manual/learned/imported")
    learned_from: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="学习来源对话ID")
    confidence: Mapped[float] = mapped_column(Float, default=0.5, comment="置信度(0-1)")
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="最后使用时间")
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否已验证")
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")
    
    # 元数据
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, comment="标签")
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True, comment="扩展元数据")

    __table_args__ = (
        Index("idx_skill_category", "category"),
        Index("idx_skill_source", "source"),
        Index("idx_skill_active", "is_active"),
        Index("idx_skill_confidence", "confidence"),
    )


class SkillExecutionLog(Base, UUIDMixin):
    """技能执行日志"""
    __tablename__ = "skill_execution_logs"

    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 执行信息
    input_text: Mapped[str] = mapped_column(Text, nullable=False, comment="用户输入")
    output_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="输出结果")
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, comment="执行时间(ms)")
    success: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否成功")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    
    # 匹配信息
    match_score: Mapped[float] = mapped_column(Float, default=0.0, comment="匹配分数")
    match_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="匹配方法")
    
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now())

    __table_args__ = (
        Index("idx_exec_skill_id", "skill_id"),
        Index("idx_exec_user_id", "user_id"),
        Index("idx_exec_created", "created_at"),
    )


class UserPreference(Base, UUIDMixin):
    """用户偏好学习"""
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    preference_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="偏好类型")
    preference_key: Mapped[str] = mapped_column(String(100), nullable=False, comment="偏好键")
    preference_value: Mapped[str] = mapped_column(Text, nullable=False, comment="偏好值")
    confidence: Mapped[float] = mapped_column(Float, default=0.5, comment="置信度")
    learned_count: Mapped[int] = mapped_column(Integer, default=1, comment="学习次数")
    last_used_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now())

    __table_args__ = (
        Index("idx_pref_user", "user_id"),
        Index("idx_pref_type", "preference_type"),
    )
