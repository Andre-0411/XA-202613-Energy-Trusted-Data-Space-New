"""
AI Agent 管理 Schema
知识库管理、模型配置、Agent 参数调节
"""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 知识库管理 ====================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库"""
    name: str = Field(max_length=200, description="知识库名称")
    description: Optional[str] = Field(default=None, description="知识库描述")
    category: str = Field(default="general", description="分类: general/energy/trade/security/dispatch")
    embedding_model: str = Field(default="text-embedding-v2", description="向量化模型")
    chunk_size: int = Field(default=512, ge=64, le=2048, description="分块大小")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="分块重叠")
    metadata: dict = Field(default_factory=dict, description="扩展元数据")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库"""
    name: Optional[str] = Field(default=None, max_length=200, description="知识库名称")
    description: Optional[str] = Field(default=None, description="知识库描述")
    category: Optional[str] = Field(default=None, description="分类")
    embedding_model: Optional[str] = Field(default=None, description="向量化模型")
    chunk_size: Optional[int] = Field(default=None, ge=64, le=2048, description="分块大小")
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=500, description="分块重叠")
    metadata: Optional[dict] = Field(default=None, description="扩展元数据")


class KnowledgeBaseResponse(BaseModel):
    """知识库响应"""
    id: str = Field(description="知识库 ID")
    name: str = Field(description="知识库名称")
    description: Optional[str] = None
    category: str = Field(description="分类")
    embedding_model: str = Field(description="向量化模型")
    chunk_size: int = Field(description="分块大小")
    chunk_overlap: int = Field(description="分块重叠")
    document_count: int = Field(default=0, description="文档数量")
    total_tokens: int = Field(default=0, description="总 token 数")
    status: str = Field(default="active", description="状态: active/indexing/error")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    metadata: dict = Field(default_factory=dict)


class DocumentUpload(BaseModel):
    """上传文档到知识库"""
    title: str = Field(max_length=500, description="文档标题")
    content: str = Field(description="文档内容")
    content_type: str = Field(default="text/plain", description="内容类型: text/plain, text/markdown, application/pdf")
    metadata: dict = Field(default_factory=dict, description="文档元数据")


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str = Field(description="文档 ID")
    knowledge_base_id: str = Field(description="所属知识库 ID")
    title: str = Field(description="文档标题")
    content_type: str = Field(description="内容类型")
    chunk_count: int = Field(default=0, description="分块数量")
    token_count: int = Field(default=0, description="token 数量")
    status: str = Field(default="indexed", description="状态: indexing/indexed/error")
    created_at: datetime = Field(description="上传时间")
    metadata: dict = Field(default_factory=dict)


# ==================== 模型配置 ====================

class ModelConfig(BaseModel):
    """模型配置"""
    provider: str = Field(default="deepseek", description="模型提供商: deepseek/openai/zhipu/qwen")
    model_name: str = Field(default="deepseek-chat", description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API Key（仅管理员可修改）")
    base_url: Optional[str] = Field(default=None, description="API Base URL")
    max_tokens: int = Field(default=2048, ge=256, le=32768, description="最大输出 token")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top P 参数")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="存在惩罚")
    metadata: dict = Field(default_factory=dict, description="扩展配置")


class ModelConfigResponse(BaseModel):
    """模型配置响应（隐藏 API Key）"""
    provider: str = Field(description="模型提供商")
    model_name: str = Field(description="模型名称")
    api_key_set: bool = Field(description="是否已设置 API Key")
    base_url: str = Field(description="API Base URL")
    max_tokens: int = Field(description="最大输出 token")
    temperature: float = Field(description="温度参数")
    top_p: float = Field(description="Top P 参数")
    frequency_penalty: float = Field(description="频率惩罚")
    presence_penalty: float = Field(description="存在惩罚")
    metadata: dict = Field(default_factory=dict)


# ==================== Agent 配置 ====================

class AgentConfigUpdate(BaseModel):
    """更新 Agent 配置"""
    agent_type: str = Field(description="Agent 类型: query/trade/security/dispatch")
    name: Optional[str] = Field(default=None, max_length=100, description="Agent 名称")
    description: Optional[str] = Field(default=None, description="Agent 描述")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    knowledge_base_ids: Optional[list[str]] = Field(default=None, description="关联知识库 ID 列表")
    llm_config: Optional[ModelConfig] = Field(default=None, description="模型配置覆盖")
    enabled: Optional[bool] = Field(default=None, description="是否启用")
    metadata: Optional[dict] = Field(default=None, description="扩展配置")


class AgentConfigResponse(BaseModel):
    """Agent 配置响应"""
    agent_type: str = Field(description="Agent 类型")
    name: str = Field(description="Agent 名称")
    description: str = Field(description="Agent 描述")
    system_prompt: str = Field(description="系统提示词")
    knowledge_base_ids: list[str] = Field(default_factory=list, description="关联知识库 ID 列表")
    knowledge_base_names: list[str] = Field(default_factory=list, description="关联知识库名称列表")
    llm_config: ModelConfigResponse = Field(description="模型配置")
    enabled: bool = Field(description="是否启用")
    total_queries: int = Field(default=0, description="总查询次数")
    avg_response_time: float = Field(default=0.0, description="平均响应时间(ms)")
    last_used_at: Optional[datetime] = Field(default=None, description="最后使用时间")
    metadata: dict = Field(default_factory=dict)


# ==================== 统计数据 ====================

class AgentStats(BaseModel):
    """Agent 统计数据"""
    total_agents: int = Field(description="Agent 总数")
    active_agents: int = Field(description="活跃 Agent 数")
    total_knowledge_bases: int = Field(description="知识库总数")
    total_documents: int = Field(description="文档总数")
    total_queries_today: int = Field(description="今日查询总数")
    avg_response_time: float = Field(description="平均响应时间(ms)")
    model_provider: str = Field(description="当前模型提供商")
    model_name: str = Field(description="当前模型名称")
