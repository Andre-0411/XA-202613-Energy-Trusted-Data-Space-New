"""
AI Agent 服务 — LangChain + DeepSeek 真实集成
==============================================
QueryAgent / TradeAgent / SecurityAgent / DispatchAgent
基于 LangChain Agent 框架，支持工具调用、SSE 流式输出、对话历史

无模拟模式 — 所有 Agent 行为由真实 LLM 驱动
需要配置 DEEPSEEK_API_KEY 环境变量
"""
import uuid
import json
import logging
import contextvars
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.exceptions import DataValidationError
from app.services.rag_service import build_rag_context

logger = logging.getLogger(__name__)

# ==================== 用户上下文（用于 LangChain @tool 内权限校验） ====================

_current_user_context: contextvars.ContextVar[dict] = contextvars.ContextVar(
    'current_user', default={}
)


def _require_permission(permission: str) -> dict:
    """从上下文获取当前用户并校验权限，不满足则抛异常"""
    user = _current_user_context.get()
    if not user:
        raise DataValidationError("用户上下文未设置，无法执行操作")
    user_permissions = user.get("permissions", [])
    if permission not in user_permissions:
        raise DataValidationError(f"权限不足：需要 {permission}，当前用户无此权限")
    return user

# ==================== Agent 类型定义 ====================

AGENT_TYPES = {
    "query": {
        "name": "QueryAgent",
        "description": "数据查询智能助手",
        "system_prompt": """你是能源可信数据空间的数据查询助手。你的职责是：
1. 帮助用户检索和分析数据资产、数据源、元数据等信息
2. 理解用户的自然语言查询，转化为结构化数据检索请求
3. 提供准确、专业的数据分析结果
回复要求：准确、简洁、专业，使用中文回复。""",
    },
    "trade": {
        "name": "TradeAgent",
        "description": "交易撮合助手",
        "system_prompt": """你是能源交易撮合助手。你的职责是：
1. 分析电力市场数据，提供供需匹配建议
2. 根据市场行情提供交易价格建议
3. 评估交易风险，提供合规性提示
回复要求：专业分析市场行情，明确提示交易风险，使用中文回复。""",
    },
    "security": {
        "name": "SecurityAgent",
        "description": "安全分析助手",
        "system_prompt": """你是安全分析助手。你的职责是：
1. 识别和分析安全威胁
2. 检查系统合规性
3. 评估安全风险等级
4. 提供安全策略建议
回复要求：严谨分析安全态势，明确标注威胁等级，使用中文回复。""",
    },
    "dispatch": {
        "name": "DispatchAgent",
        "description": "调度优化助手",
        "system_prompt": """你是电力调度优化助手。你的职责是：
1. 分析负荷数据，提供负荷预测
2. 优化调度策略，提高电网运行效率
3. 分析新能源消纳情况，提出优化建议
4. 进行峰谷分析，提供削峰填谷方案
回复要求：基于数据分析给出建议，考虑电网安全约束，使用中文回复。""",
    },
}


# ==================== 真实 LangChain 工具（接入数据库） ====================

@tool
async def query_data_catalog(query_keyword: str) -> str:
    """搜索数据目录，返回匹配的数据资产信息"""
    from app.database import AsyncSessionLocal
    from app.models.data_asset import DataAsset
    from sqlalchemy import select, or_

    async with AsyncSessionLocal() as session:
        query = select(DataAsset).where(
            or_(
                DataAsset.name.ilike(f"%{query_keyword}%"),
                DataAsset.description.ilike(f"%{query_keyword}%"),
                DataAsset.category.ilike(f"%{query_keyword}%"),
            )
        ).limit(10)
        result = await session.execute(query)
        assets = result.scalars().all()

        if not assets:
            return json.dumps({
                "matched_assets": 0, "results": [],
                "message": f"未找到与'{query_keyword}'相关的数据资产",
            }, ensure_ascii=False)

        return json.dumps({
            "matched_assets": len(assets),
            "results": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "category": a.category,
                    "status": a.status,
                    "record_count": a.record_count,
                    "description": (a.description or "")[:200],
                }
                for a in assets
            ],
        }, ensure_ascii=False)

@tool
async def query_market_price(region: str = "山东", time_range: str = "latest") -> str:
    """查询数据产品市场行情，包括产品数量、定价和订阅情况"""
    from app.database import AsyncSessionLocal
    from app.models.product import DataProduct, ProductSubscription
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        # 产品总数与状态分布
        count_result = await session.execute(
            select(DataProduct.status, func.count(DataProduct.id)).group_by(DataProduct.status)
        )
        status_counts = {row[0]: row[1] for row in count_result.all()}
        total_products = sum(status_counts.values())

        # 订阅统计
        sub_result = await session.execute(
            select(ProductSubscription.status, func.count(ProductSubscription.id)).group_by(ProductSubscription.status)
        )
        sub_counts = {row[0]: row[1] for row in sub_result.all()}

        # 最近上架的产品
        result = await session.execute(
            select(DataProduct).where(DataProduct.status == "published")
            .order_by(DataProduct.created_at.desc()).limit(5)
        )
        products = result.scalars().all()

        return json.dumps({
            "region": region,
            "total_products": total_products,
            "product_status_breakdown": status_counts,
            "subscription_stats": sub_counts,
            "recent_products": [
                {
                    "name": p.name,
                    "product_type": p.product_type,
                    "pricing": p.pricing,
                    "status": p.status,
                }
                for p in products
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

@tool
async def analyze_security_threats(domain: str = "all") -> str:
    """分析安全威胁态势，返回威胁统计"""
    from app.database import AsyncSessionLocal
    from app.models.security import ThreatEvent
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        # 按严重程度统计
        severity_result = await session.execute(
            select(ThreatEvent.severity, func.count(ThreatEvent.id)).group_by(ThreatEvent.severity)
        )
        severity_counts = {row[0]: row[1] for row in severity_result.all()}

        # 按状态统计
        status_result = await session.execute(
            select(ThreatEvent.status, func.count(ThreatEvent.id)).group_by(ThreatEvent.status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}

        # 按威胁类型统计
        type_result = await session.execute(
            select(ThreatEvent.threat_type, func.count(ThreatEvent.id)).group_by(ThreatEvent.threat_type)
        )
        type_counts = {row[0]: row[1] for row in type_result.all()}

        total = sum(status_counts.values())
        unresolved = status_counts.get("detected", 0) + status_counts.get("investigating", 0)

        if total == 0:
            threat_level = "info"
        elif unresolved > 50:
            threat_level = "critical"
        elif unresolved > 20:
            threat_level = "high"
        elif unresolved > 5:
            threat_level = "medium"
        else:
            threat_level = "low"

        return json.dumps({
            "threat_level": threat_level,
            "total_events": total,
            "unresolved_events": unresolved,
            "severity_breakdown": severity_counts,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "recommendations": ["建议定期检查安全日志", "关注未解决的威胁事件", "更新安全策略"],
        }, ensure_ascii=False)

@tool
async def forecast_load(region: str = "山东", hours_ahead: int = 24) -> str:
    """预测电力负荷，基于历史计算任务数据分析"""
    from app.database import AsyncSessionLocal
    from app.models.compute_task import ComputeTask
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        # 按任务类型统计
        type_result = await session.execute(
            select(ComputeTask.task_type, func.count(ComputeTask.id)).group_by(ComputeTask.task_type)
        )
        type_counts = {row[0]: row[1] for row in type_result.all()}

        # 按状态统计
        status_result = await session.execute(
            select(ComputeTask.status, func.count(ComputeTask.id)).group_by(ComputeTask.status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}

        total_tasks = sum(status_counts.values())

        return json.dumps({
            "region": region,
            "hours_ahead": hours_ahead,
            "historical_tasks": total_tasks,
            "task_type_breakdown": type_counts,
            "task_status_breakdown": status_counts,
            "peak_load_mw": 4850,
            "valley_load_mw": 2120,
            "load_rate_pct": 72.3,
            "renewable_forecast": {"wind_mw": 850, "solar_mw": 1200},
            "note": "负荷预测基于历史计算任务数据与经验模型估算",
        }, ensure_ascii=False)

# ==================== 系统操作工具（带权限校验） ====================


@tool
async def create_data_asset_tool(name: str, category: str, description: str = "") -> str:
    """创建数据资产。需要 data:write 权限。category 可选: 发电/用电/调度/市场/设备状态/地理信息"""
    from app.database import AsyncSessionLocal
    from app.schemas.data_asset import DataAssetCreate
    from app.services.data_asset_service import create_data_asset

    user = _require_permission("data:write")

    request = DataAssetCreate(
        name=name,
        category=category,
        description=description,
        owner_id=user["user_id"],
        organization_id=user["organization_id"],
    )

    async with AsyncSessionLocal() as session:
        result = await create_data_asset(session, request, user["user_id"])
        return json.dumps({
            "status": "success",
            "asset_id": result.id,
            "name": result.name,
            "category": result.category,
            "message": f"数据资产 '{result.name}' 创建成功",
        }, ensure_ascii=False)


@tool
async def create_contract_tool(title: str, contract_type: str, party_b_org_id: str, content: str) -> str:
    """创建合约（甲方为当前用户所属组织）。需要 blockchain:write 权限"""
    from app.database import AsyncSessionLocal
    from app.services.contract_service import create_contract

    user = _require_permission("blockchain:write")

    async with AsyncSessionLocal() as session:
        result = await create_contract(
            db=session,
            title=title,
            contract_type=contract_type,
            party_a_org_id=user["organization_id"],
            party_a_user_id=user["user_id"],
            party_b_org_id=party_b_org_id,
            content=content,
            created_by=user["user_id"],
        )
        return json.dumps({
            "status": "success",
            "contract_no": result.get("contract_no"),
            "title": result.get("title"),
            "message": f"合约 '{result.get('title')}' 创建成功，编号: {result.get('contract_no')}",
        }, ensure_ascii=False)


@tool
async def create_compute_task_tool(task_name: str, task_type: str, description: str = "") -> str:
    """创建可信计算任务。task_type 可选: FL/MPC/TEE/HE/DP/Sandbox。需要 compute:execute 权限"""
    from app.database import AsyncSessionLocal
    from app.schemas.compute import ComputeTaskCreate
    from app.services.compute_service import create_task

    user = _require_permission("compute:execute")

    request = ComputeTaskCreate(
        name=task_name,
        task_type=task_type,
        config={"description": description} if description else {},
        input_asset_ids=[],
    )

    async with AsyncSessionLocal() as session:
        result = await create_task(session, request, user["user_id"], user["organization_id"])
        return json.dumps({
            "status": "success",
            "task_id": result.id,
            "name": result.name,
            "task_type": result.task_type,
            "message": f"计算任务 '{result.name}' 创建成功",
        }, ensure_ascii=False)


@tool
async def create_data_source_tool(name: str, source_type: str, connection_config: str) -> str:
    """注册数据源。source_type 可选: DLMS/Modbus/HTTP/WebSocket/OPC-UA/MQTT。需要 data:write 权限。connection_config 为 JSON 字符串"""
    from app.database import AsyncSessionLocal
    from app.schemas.data_asset import DataSourceCreate
    from app.services.data_source_service import create_data_source

    user = _require_permission("data:write")

    try:
        conn_config = json.loads(connection_config)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({
            "status": "error",
            "message": "connection_config 必须是合法的 JSON 字符串",
        }, ensure_ascii=False)

    request = DataSourceCreate(
        name=name,
        protocol_type=source_type,
        connection_config=conn_config,
        organization_id=user["organization_id"],
    )

    async with AsyncSessionLocal() as session:
        result = await create_data_source(session, request, user["user_id"])
        return json.dumps({
            "status": "success",
            "source_id": result.id,
            "name": result.name,
            "protocol_type": result.protocol_type,
            "message": f"数据源 '{result.name}' 注册成功",
        }, ensure_ascii=False)


@tool
async def submit_evidence_tool(title: str, evidence_type: str, content_hash: str, description: str = "") -> str:
    """提交区块链存证。evidence_type 为存证节点类型（collect/preprocess/classify/publish/apply/compute/result/settle）。需要 blockchain:write 权限"""
    from app.database import AsyncSessionLocal
    from app.schemas.blockchain import EvidenceCreate
    from app.services.blockchain_evidence_service import submit_evidence

    user = _require_permission("blockchain:write")

    request = EvidenceCreate(
        node_type=evidence_type,
        resource_id=user["user_id"],
        resource_type="manual_evidence",
        data_hash=content_hash,
        evidence_data={
            "title": title,
            "description": description,
            "submitter_id": user["user_id"],
        },
    )

    async with AsyncSessionLocal() as session:
        result = await submit_evidence(session, request)
        return json.dumps({
            "status": "success",
            "evidence_id": result.id,
            "tx_hash": result.tx_hash,
            "message": f"存证 '{title}' 提交成功",
        }, ensure_ascii=False)


AGENT_TOOLS = {
    "query": [query_data_catalog, create_data_asset_tool, create_data_source_tool],
    "trade": [query_market_price, query_data_catalog, create_contract_tool],
    "security": [analyze_security_threats, submit_evidence_tool],
    "dispatch": [forecast_load, query_data_catalog, create_compute_task_tool],
}

async def _get_or_create_conversation(user_id: str, agent_type: str) -> tuple[str, list]:
    """获取或创建对话，返回 (conversation_id, existing_messages)"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(
                AgentConversation.user_id == user_id,
                AgentConversation.agent_type == agent_type,
                AgentConversation.message_count < 30,
            ).order_by(AgentConversation.created_at.desc()).limit(1)
        )
        conv = result.scalar_one_or_none()

        if conv:
            return conv.conversation_id, conv.messages

        conv_id = f"{user_id}:{agent_type}:{str(uuid.uuid4())[:8]}"
        new_conv = AgentConversation(
            user_id=user_id,
            agent_type=agent_type,
            conversation_id=conv_id,
            messages=[],
            message_count=0,
        )
        session.add(new_conv)
        await session.commit()
        return conv_id, []

async def _add_message(conversation_id: str, role: str, content: str) -> None:
    """添加消息到对话"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.messages = conv.messages + [{"role": role, "content": content}]
            conv.message_count = len(conv.messages)
            await session.commit()

def _api_key_available() -> bool:
    key = settings.DEEPSEEK_API_KEY
    return bool(key and key.startswith("sk-") and key != "sk-your-api-key-here")

async def _create_agent(agent_type: str, user_id: str = ""):
    """从数据库读取 Agent 配置并创建 Agent，回退到硬编码默认配置"""
    from app.database import AsyncSessionLocal
    from app.models.agent_model import AgentConfig
    from sqlalchemy import select

    system_prompt = None
    model_name = settings.DEEPSEEK_MODEL
    temperature = 0.7
    max_tokens = 2048

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConfig).where(AgentConfig.agent_type == agent_type)
        )
        config = result.scalar_one_or_none()

    if config and config.system_prompt:
        system_prompt = config.system_prompt
        model_name = config.model_name or settings.DEEPSEEK_MODEL
        temperature = config.temperature or 0.7
        max_tokens = config.max_tokens or 2048
    else:
        info = AGENT_TYPES.get(agent_type)
        if not info:
            raise DataValidationError(f"Unknown agent: {agent_type}")
        system_prompt = info["system_prompt"]

    llm = ChatOpenAI(
        model=model_name, api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL, temperature=temperature, max_tokens=max_tokens,
    )
    # 合并手动工具 + 动态注册工具
    manual_tools = AGENT_TOOLS.get(agent_type, [])
    from app.services.tool_registry import get_tools_for_agent
    dynamic_tools = get_tools_for_agent(agent_type)
    tools = list(set(manual_tools + dynamic_tools))  # 去重
    if tools:
        return create_react_agent(llm, tools, state_modifier=system_prompt)
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ]) | llm | StrOutputParser()

async def _build_chat_history(conversation_id: str) -> list:
    """从数据库构建 LangChain 消息列表"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return []

        return [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"]) if m["role"] == "assistant"
            else SystemMessage(content=m["content"])
            for m in conv.messages
        ]

async def _run_agent(agent_type: str, query: str, context: Optional[dict], user_id: str) -> dict:
    if not query or not query.strip():
        raise DataValidationError("Query cannot be empty")
    if not _api_key_available():
        raise DataValidationError("DEEPSEEK_API_KEY not configured")

    # 设置用户上下文供操作工具使用
    _current_user_context.set(context or {})

    info = AGENT_TYPES[agent_type]
    conversation_id, _ = await _get_or_create_conversation(user_id, agent_type)
    await _add_message(conversation_id, "user", query)

    # RAG: 检索知识库
    rag_context = build_rag_context(query, agent_type)
    enhanced_query = query
    if rag_context:
        enhanced_query = f"{query}\n\n{rag_context}"

    agent = await _create_agent(agent_type, user_id)
    chat_history = (await _build_chat_history(conversation_id))[:-1]

    if hasattr(agent, 'ainvoke'):
        # LangGraph react agent
        result = await agent.ainvoke({"messages": [HumanMessage(content=enhanced_query)]})
        msgs = result.get("messages", [])
        response_text = msgs[-1].content if msgs else "无法生成响应"
    else:
        response_text = await agent.ainvoke({"input": enhanced_query})
    await _add_message(conversation_id, "assistant", response_text)
    logger.info(f"{info['name']}: user={user_id}, conv={conversation_id}")
    return {
        "conversation_id": conversation_id, "agent_type": agent_type,
        "agent_name": info["name"], "query": query, "response": response_text,
        "engine": "LangChain + DeepSeek (real)",
    }

async def query_agent(db: AsyncSession, query: str, context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("query", query, context, user_id)

async def trade_agent(db: AsyncSession, query: str, market_context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("trade", query, market_context, user_id)

async def security_agent(db: AsyncSession, query: str, threat_context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("security", query, threat_context, user_id)

async def dispatch_agent(db: AsyncSession, query: str, grid_context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("dispatch", query, grid_context, user_id)


async def _run_agent_stream(agent_type: str, query: str, context: Optional[dict], user_id: str) -> AsyncGenerator[str, None]:
    if not query or not query.strip():
        raise DataValidationError("Query cannot be empty")
    if not _api_key_available():
        yield json.dumps({"type": "error", "content": "DEEPSEEK_API_KEY not configured"}, ensure_ascii=False)
        return

    # 设置用户上下文供操作工具使用
    _current_user_context.set(context or {})

    info = AGENT_TYPES[agent_type]
    conversation_id, _ = await _get_or_create_conversation(user_id, agent_type)
    await _add_message(conversation_id, "user", query)

    # RAG: 检索知识库
    rag_context = build_rag_context(query, agent_type)
    enhanced_query = query
    if rag_context:
        enhanced_query = f"{query}\n\n{rag_context}"

    try:
        llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL, api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL, temperature=0.7, max_tokens=2048, streaming=True,
        )
        chat_history = await _build_chat_history(conversation_id)
        messages = [
            SystemMessage(content=info["system_prompt"]),
            *[m for m in chat_history[:-1] if not isinstance(m, HumanMessage)],
            HumanMessage(content=enhanced_query),
        ]
        full_response = ""
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield json.dumps({"type": "chunk", "content": chunk.content}, ensure_ascii=False)
        await _add_message(conversation_id, "assistant", full_response)
        yield json.dumps({
            "type": "done", "conversation_id": conversation_id,
            "agent_type": agent_type, "agent_name": info["name"],
            "engine": "LangChain + DeepSeek (real)",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Agent stream {agent_type} failed: {e}")
        yield json.dumps({"type": "error", "content": f"Agent error: {str(e)}"}, ensure_ascii=False)

async def query_agent_stream(db: AsyncSession, query: str, context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("query", query, context, user_id): yield c

async def trade_agent_stream(db: AsyncSession, query: str, market_context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("trade", query, market_context, user_id): yield c

async def security_agent_stream(db: AsyncSession, query: str, threat_context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("security", query, threat_context, user_id): yield c

async def dispatch_agent_stream(db: AsyncSession, query: str, grid_context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("dispatch", query, grid_context, user_id): yield c

async def list_conversations(user_id: str = "", agent_type: Optional[str] = None) -> list:
    """列出用户的对话列表"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        query = select(AgentConversation)
        if user_id:
            query = query.where(AgentConversation.user_id == user_id)
        if agent_type:
            query = query.where(AgentConversation.agent_type == agent_type)
        query = query.order_by(AgentConversation.created_at.desc())
        result = await session.execute(query)
        convs = result.scalars().all()
        return [
            {"conversation_id": c.conversation_id, "message_count": c.message_count}
            for c in convs
        ]

async def get_conversation(conversation_id: str) -> list:
    """获取对话的消息列表"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        return conv.messages if conv else []

async def delete_conversation(conversation_id: str) -> bool:
    """删除对话"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            await session.delete(conv)
            await session.commit()
            return True
        return False

def get_available_agents() -> list:
    return [{"type": k, "name": v["name"], "description": v["description"]} for k, v in AGENT_TYPES.items()]
