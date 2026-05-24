"""
AI Agent 管理服务
知识库管理、模型配置、Agent 参数调节 - 真实数据库实现
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import DataValidationError, DataNotFoundError as NotFoundError
from app.models.agent_model import KnowledgeBase, KnowledgeDocument, AgentConfig

logger = logging.getLogger(__name__)


# ==================== 默认 Agent 配置（首次启动时初始化） ====================

DEFAULT_AGENTS = [
    {
        "agent_type": "query",
        "name": "查询代理",
        "description": "智能数据查询，支持自然语言转 SQL",
        "system_prompt": """你是能源可信数据空间的数据查询助手。你的职责是：
1. 帮助用户检索和分析数据资产、数据源、元数据等信息
2. 理解用户的自然语言查询，转化为结构化数据检索请求
3. 提供准确、专业的数据分析结果

回复要求：
- 准确、简洁、专业
- 使用中文回复
- 如需澄清用户意图，请主动提问
- 提供数据时说明数据来源和时间范围""",
        "model_name": "deepseek-chat",
        "model_provider": "deepseek",
        "temperature": 0.7,
        "max_tokens": 2048,
        "enabled": True,
    },
    {
        "agent_type": "trade",
        "name": "交易代理",
        "description": "数据交易撮合与定价建议",
        "system_prompt": """你是能源交易撮合助手。你的职责是：
1. 分析电力市场数据，提供供需匹配建议
2. 根据市场行情提供交易价格建议
3. 评估交易风险，提供合规性提示

回复要求：
- 专业分析市场行情
- 明确提示交易风险
- 遵守交易合规要求
- 使用中文回复""",
        "model_name": "deepseek-chat",
        "model_provider": "deepseek",
        "temperature": 0.7,
        "max_tokens": 2048,
        "enabled": True,
    },
    {
        "agent_type": "security",
        "name": "安全代理",
        "description": "安全策略审查与风险预警",
        "system_prompt": """你是安全分析助手。你的职责是：
1. 识别和分析安全威胁
2. 检查系统合规性
3. 评估安全风险等级
4. 提供安全策略建议

回复要求：
- 严谨分析安全态势
- 明确标注威胁等级
- 提供可执行的安全建议
- 使用中文回复""",
        "model_name": "deepseek-chat",
        "model_provider": "deepseek",
        "temperature": 0.5,
        "max_tokens": 2048,
        "enabled": True,
    },
    {
        "agent_type": "dispatch",
        "name": "调度代理",
        "description": "任务调度优化与资源分配",
        "system_prompt": """你是电力调度优化助手。你的职责是：
1. 分析负荷数据，提供负荷预测
2. 优化调度策略，提高电网运行效率
3. 分析新能源消纳情况，提出优化建议
4. 进行峰谷分析，提供削峰填谷方案

回复要求：
- 基于数据分析给出建议
- 考虑电网安全约束
- 关注经济性和可靠性平衡
- 使用中文回复""",
        "model_name": "deepseek-chat",
        "model_provider": "deepseek",
        "temperature": 0.6,
        "max_tokens": 2048,
        "enabled": True,
    },
]


async def _ensure_default_agents(db: AsyncSession) -> None:
    """确保默认 Agent 配置存在（首次启动时初始化）"""
    result = await db.execute(select(func.count(AgentConfig.id)))
    count = result.scalar()
    if count == 0:
        for agent_data in DEFAULT_AGENTS:
            agent = AgentConfig(
                id=uuid.uuid4(),
                organization_id="system",
                knowledge_base_ids=[],
                tools=[],
                usage_count=0,
                **agent_data,
            )
            db.add(agent)
        await db.commit()
        logger.info("Initialized default agent configs in database")


# ==================== 知识库管理 ====================

async def list_knowledge_bases(
    db: AsyncSession,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """获取知识库列表"""
    query = select(KnowledgeBase)

    if category:
        query = query.where(KnowledgeBase.status == category)

    # 获取总数
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(KnowledgeBase.created_at.desc())
    result = await db.execute(query)
    items = [kb.to_dict() for kb in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


async def create_knowledge_base(db: AsyncSession, data: dict, org_id: str = "system") -> dict:
    """创建知识库"""
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        name=data["name"],
        description=data.get("description", ""),
        organization_id=org_id,
        embedding_model=data.get("embedding_model", "text-embedding-ada-002"),
        chunk_size=data.get("chunk_size", 1000),
        chunk_overlap=data.get("chunk_overlap", 200),
        document_count=0,
        status="active",
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)

    logger.info(f"Created knowledge base: {kb.id} - {data['name']}")
    return kb.to_dict()


async def get_knowledge_base(db: AsyncSession, kb_id: str) -> dict:
    """获取知识库详情"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundError(f"知识库 {kb_id} 不存在")
    return kb.to_dict()


async def update_knowledge_base(db: AsyncSession, kb_id: str, data: dict) -> dict:
    """更新知识库"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundError(f"知识库 {kb_id} 不存在")

    for key, value in data.items():
        if value is not None and hasattr(kb, key) and key not in ("id", "created_at"):
            setattr(kb, key, value)

    await db.commit()
    await db.refresh(kb)

    logger.info(f"Updated knowledge base: {kb_id}")
    return kb.to_dict()


async def delete_knowledge_base(db: AsyncSession, kb_id: str) -> bool:
    """删除知识库"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise NotFoundError(f"知识库 {kb_id} 不存在")

    # 检查是否有关联的 Agent
    agent_result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.knowledge_base_ids.contains([kb_id])
        )
    )
    agents = agent_result.scalars().all()
    if agents:
        agent_names = ", ".join(a.name for a in agents)
        raise DataValidationError(f"知识库 {kb_id} 正在被 Agent [{agent_names}] 使用，请先解除关联")

    # 删除关联文档
    doc_result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)
    )
    for doc in doc_result.scalars().all():
        await db.delete(doc)

    await db.delete(kb)
    await db.commit()

    logger.info(f"Deleted knowledge base: {kb_id}")
    return True


# ==================== 文档管理 ====================

async def list_documents(db: AsyncSession, kb_id: str, page: int = 1, page_size: int = 20) -> dict:
    """获取知识库文档列表"""
    # 验证知识库存在
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    if not kb_result.scalar_one_or_none():
        raise NotFoundError(f"知识库 {kb_id} 不存在")

    query = select(KnowledgeDocument).where(KnowledgeDocument.knowledge_base_id == kb_id)

    # 获取总数
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(KnowledgeDocument.created_at.desc())
    result = await db.execute(query)
    items = [doc.to_dict() for doc in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


async def add_document(db: AsyncSession, kb_id: str, data: dict) -> dict:
    """添加文档到知识库"""
    # 验证知识库存在
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise NotFoundError(f"知识库 {kb_id} 不存在")

    doc = KnowledgeDocument(
        id=uuid.uuid4(),
        knowledge_base_id=kb_id,
        filename=data.get("title", data.get("filename", "未命名文档")),
        file_type=data.get("content_type", data.get("file_type", "text/plain")),
        file_size=data.get("file_size", len(data.get("content", ""))),
        chunk_count=max(1, len(data.get("content", "")) // kb.chunk_size),
        status="indexed",
        doc_metadata=data.get("metadata", {}),
        uploaded_by=data.get("uploaded_by", "system"),
        content=data.get("content"),
    )
    db.add(doc)

    # 更新知识库文档计数
    count_result = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.knowledge_base_id == kb_id
        )
    )
    kb.document_count = (count_result.scalar() or 0) + 1

    await db.commit()
    await db.refresh(doc)

    logger.info(f"Added document {doc.id} to knowledge base {kb_id}")
    return doc.to_dict()


async def delete_document(db: AsyncSession, kb_id: str, doc_id: str) -> bool:
    """删除文档"""
    # 验证知识库存在
    kb_result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise NotFoundError(f"知识库 {kb_id} 不存在")

    # 查找文档
    doc_result = await db.execute(
        select(KnowledgeDocument).where(
            and_(
                KnowledgeDocument.id == doc_id,
                KnowledgeDocument.knowledge_base_id == kb_id,
            )
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"文档 {doc_id} 不存在")

    await db.delete(doc)

    # 更新知识库文档计数
    count_result = await db.execute(
        select(func.count(KnowledgeDocument.id)).where(
            and_(
                KnowledgeDocument.knowledge_base_id == kb_id,
                KnowledgeDocument.id != doc_id,
            )
        )
    )
    kb.document_count = count_result.scalar() or 0

    await db.commit()

    logger.info(f"Deleted document {doc_id} from knowledge base {kb_id}")
    return True


# ==================== 模型配置 ====================

async def get_model_config() -> dict:
    """获取当前模型配置"""
    return {
        "provider": "deepseek",
        "model_name": settings.DEEPSEEK_MODEL,
        "api_key_set": bool(settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY != "sk-your-api-key-here"),
        "base_url": settings.DEEPSEEK_BASE_URL,
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "metadata": {},
    }


async def update_model_config(data: dict) -> dict:
    """更新模型配置"""
    logger.info(f"Model config update requested: {data}")
    config = await get_model_config()
    for key, value in data.items():
        if value is not None and key in config:
            config[key] = value
    return config


# ==================== Agent 配置 ====================

async def list_agent_configs(db: AsyncSession) -> list[dict]:
    """获取所有 Agent 配置"""
    await _ensure_default_agents(db)

    result = await db.execute(
        select(AgentConfig).order_by(AgentConfig.created_at)
    )
    agents = result.scalars().all()

    items = []
    for agent in agents:
        agent_dict = agent.to_dict()
        # 获取知识库名称
        kb_names = []
        if agent.knowledge_base_ids:
            for kb_id in agent.knowledge_base_ids:
                kb_result = await db.execute(
                    select(KnowledgeBase.name).where(KnowledgeBase.id == kb_id)
                )
                kb_name = kb_result.scalar_one_or_none()
                if kb_name:
                    kb_names.append(kb_name)
        agent_dict["knowledge_base_names"] = kb_names
        items.append(agent_dict)

    return items


async def get_agent_config(db: AsyncSession, agent_type: str) -> dict:
    """获取 Agent 配置"""
    await _ensure_default_agents(db)

    result = await db.execute(
        select(AgentConfig).where(AgentConfig.agent_type == agent_type)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise NotFoundError(f"Agent {agent_type} 不存在")

    agent_dict = agent.to_dict()
    # 获取知识库名称
    kb_names = []
    if agent.knowledge_base_ids:
        for kb_id in agent.knowledge_base_ids:
            kb_result = await db.execute(
                select(KnowledgeBase.name).where(KnowledgeBase.id == kb_id)
            )
            kb_name = kb_result.scalar_one_or_none()
            if kb_name:
                kb_names.append(kb_name)
    agent_dict["knowledge_base_names"] = kb_names

    return agent_dict


async def update_agent_config(db: AsyncSession, agent_type: str, data: dict) -> dict:
    """更新 Agent 配置"""
    result = await db.execute(
        select(AgentConfig).where(AgentConfig.agent_type == agent_type)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise NotFoundError(f"Agent {agent_type} 不存在")

    # 处理模型配置嵌套更新
    model_config = data.pop("model_config", None)

    for key, value in data.items():
        if value is not None and hasattr(agent, key) and key not in ("id", "created_at"):
            setattr(agent, key, value)

    if model_config and isinstance(model_config, dict):
        field_mapping = {
            "model_name": "model_name",
            "model_provider": "model_provider",
            "temperature": "temperature",
            "max_tokens": "max_tokens",
            "system_prompt": "system_prompt",
        }
        for src_key, dst_key in field_mapping.items():
            if src_key in model_config and model_config[src_key] is not None:
                setattr(agent, dst_key, model_config[src_key])

    await db.commit()
    await db.refresh(agent)

    logger.info(f"Updated agent config: {agent_type}")

    agent_dict = agent.to_dict()
    # 获取知识库名称
    kb_names = []
    if agent.knowledge_base_ids:
        for kb_id in agent.knowledge_base_ids:
            kb_result = await db.execute(
                select(KnowledgeBase.name).where(KnowledgeBase.id == kb_id)
            )
            kb_name = kb_result.scalar_one_or_none()
            if kb_name:
                kb_names.append(kb_name)
    agent_dict["knowledge_base_names"] = kb_names

    return agent_dict


# ==================== 统计数据 ====================

async def get_agent_stats(db: AsyncSession) -> dict:
    """获取 Agent 统计数据"""
    await _ensure_default_agents(db)

    # Agent 统计
    agent_count_result = await db.execute(select(func.count(AgentConfig.id)))
    total_agents = agent_count_result.scalar() or 0

    active_count_result = await db.execute(
        select(func.count(AgentConfig.id)).where(AgentConfig.enabled == True)
    )
    active_agents = active_count_result.scalar() or 0

    # 知识库统计
    kb_count_result = await db.execute(select(func.count(KnowledgeBase.id)))
    total_knowledge_bases = kb_count_result.scalar() or 0

    # 文档统计
    doc_count_result = await db.execute(select(func.count(KnowledgeDocument.id)))
    total_documents = doc_count_result.scalar() or 0

    # 使用量统计
    usage_result = await db.execute(
        select(func.sum(AgentConfig.usage_count))
    )
    total_queries = usage_result.scalar() or 0

    model_config = await get_model_config()

    return {
        "total_agents": total_agents,
        "active_agents": active_agents,
        "total_knowledge_bases": total_knowledge_bases,
        "total_documents": total_documents,
        "total_queries_today": total_queries,
        "avg_response_time": 0,
        "model_provider": model_config["provider"],
        "model_name": model_config["model_name"],
    }
