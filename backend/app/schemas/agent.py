"""
AI Agent Schema
代理请求/响应、会话管理、流式响应
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """代理消息"""
    role: str = Field(description="角色: user/assistant/system")
    content: str = Field(description="消息内容")
    timestamp: Optional[str] = Field(default=None, description="时间戳")


class AgentConversation(BaseModel):
    """代理会话"""
    conversation_id: str = Field(description="会话 ID")
    agent_type: str = Field(description="代理类型: query/trade/security/dispatch")
    messages: list[AgentMessage] = Field(default_factory=list, description="消息历史")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


class AgentStreamChunk(BaseModel):
    """代理流式响应块"""
    type: str = Field(description="块类型: content/done/error/info")
    content: Optional[str] = Field(default=None, description="文本内容")
    conversation_id: Optional[str] = Field(default=None, description="会话 ID")
    agent_type: Optional[str] = Field(default=None, description="代理类型")
    agent_name: Optional[str] = Field(default=None, description="代理名称")


class AgentConfig(BaseModel):
    """代理配置"""
    agent_type: str = Field(description="代理类型: query/trade/security/dispatch")
    name: str = Field(description="代理名称")
    description: str = Field(description="代理描述")
    system_prompt: str = Field(description="系统提示词")
    model: Optional[str] = Field(default=None, description="使用的模型")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=2000, ge=1, le=8000, description="最大 token 数")
    enabled: bool = Field(default=True, description="是否启用")


class AgentStats(BaseModel):
    """代理统计"""
    total_queries: int = Field(default=0, description="总查询数")
    total_queries_today: int = Field(default=0, description="今日查询数")
    active_agents: int = Field(default=0, description="活跃代理数")
    success_rate: float = Field(default=0.0, description="成功率")
    avg_response_time: float = Field(default=0.0, description="平均响应时间(ms)")


class AgentTypeInfo(BaseModel):
    """代理类型信息"""
    type: str = Field(description="代理类型标识")
    name: str = Field(description="代理名称")
    description: str = Field(description="代理描述")
    icon: str = Field(default="smart_toy", description="图标名称")


class KnowledgeBaseCreate(BaseModel):
    """创建知识库"""
    name: str = Field(max_length=200, description="知识库名称")
    description: Optional[str] = Field(default=None, description="描述")
    category: Optional[str] = Field(default=None, description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str = Field(description="知识库 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None, description="描述")
    category: Optional[str] = Field(default=None, description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")
    document_count: int = Field(default=0, description="文档数量")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str = Field(description="文档 ID")
    knowledge_base_id: str = Field(description="知识库 ID")
    name: str = Field(description="文档名称")
    content_type: str = Field(description="内容类型")
    size_bytes: int = Field(default=0, description="大小(字节)")
    status: str = Field(description="状态: processing/ready/failed")
    created_at: str = Field(description="创建时间")
