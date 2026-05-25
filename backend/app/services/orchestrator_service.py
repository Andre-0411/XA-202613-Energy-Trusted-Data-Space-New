"""
Orchestrator Agent — 多Agent协作编排服务
========================================
功能：
- 意图分析：用LLM分析用户复杂需求，拆分为子任务
- 任务调度：将子任务分配给对应的Agent（Query/Trade/Security/Dispatch）
- 结果汇总：收集各Agent结果，用LLM生成最终回答

典型场景：
- "评估山东新能源消纳方案" → DispatchAgent(消纳分析) + SecurityAgent(合规检查) + TradeAgent(经济评估)
- "分析昨天安全事件" → SecurityAgent(威胁分析) + QueryAgent(数据查询) → 生成报告
"""
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.exceptions import DataValidationError

logger = logging.getLogger(__name__)

# ==================== Agent 类型与能力映射 ====================

AGENT_CAPABILITIES = {
    "query": {
        "name": "QueryAgent",
        "description": "数据查询 — 搜索数据资产、元数据、数据目录，统计系统信息",
        "keywords": ["查询", "搜索", "查找", "数据", "资产", "目录", "元数据", "统计", "列表", "数量"],
    },
    "trade": {
        "name": "TradeAgent",
        "description": "交易结算 — 市场价格分析、报价策略、供需匹配、交易风险评估",
        "keywords": ["交易", "市场", "价格", "报价", "结算", "买卖", "供需", "合同", "收益"],
    },
    "security": {
        "name": "SecurityAgent",
        "description": "安全分析 — 威胁检测、合规审计、异常行为分析、安全报告",
        "keywords": ["安全", "威胁", "攻击", "漏洞", "合规", "审计", "存证", "加密", "防护"],
    },
    "dispatch": {
        "name": "DispatchAgent",
        "description": "调度优化 — 负荷预测、新能源消纳、调度策略、储能优化",
        "keywords": ["调度", "负荷", "预测", "发电", "新能源", "消纳", "储能", "优化", "电网"],
    },
}


# ==================== 意图分析 ====================

async def _analyze_intent(query: str) -> dict:
    """
    用LLM分析用户意图，拆分为子任务

    返回：
        {
            "is_complex": bool,          # 是否为复杂多Agent任务
            "sub_tasks": [
                {"agent_type": "query", "task": "查询...", "priority": 1},
                ...
            ],
            "summary_strategy": "sequential" | "parallel",  # 执行策略
        }
    """
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key or not api_key.startswith("sk-"):
        # 无API Key时使用关键词匹配回退
        return _fallback_intent_analysis(query)

    try:
        llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            api_key=api_key,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.1,
            max_tokens=1024,
        )

        agent_desc = "\n".join(
            f"- {atype}: {info['description']}（关键词：{'、'.join(info['keywords'][:5])}）"
            for atype, info in AGENT_CAPABILITIES.items()
        )

        prompt = f"""你是能源可信数据空间的任务编排器。分析用户需求，判断是否需要多个Agent协作完成。

可用Agent类型：
{agent_desc}

用户需求：{query}

请以JSON格式返回分析结果：
{{
    "is_complex": true/false,
    "sub_tasks": [
        {{"agent_type": "agent类型", "task": "具体子任务描述", "priority": 1}}
    ],
    "summary_strategy": "parallel" 或 "sequential"
}}

规则：
1. 如果需求只需要一个Agent就能完成，is_complex=false，sub_tasks只包含一个任务
2. 如果需求需要多个Agent协作，is_complex=true，按执行优先级排列子任务
3. priority越小越先执行
4. summary_strategy: 可并行的用parallel，有依赖关系的用sequential
5. 只返回JSON，不要其他内容"""

        result = await llm.ainvoke([
            SystemMessage(content="你是任务编排分析器，只输出JSON。"),
            HumanMessage(content=prompt),
        ])

        # 解析JSON
        text = result.content.strip()
        # 提取JSON部分
        if "```" in text:
            import re
            json_match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
            if json_match:
                text = json_match.group(1).strip()

        parsed = json.loads(text)

        # 验证结构
        if "sub_tasks" not in parsed:
            raise ValueError("Missing sub_tasks")

        return parsed

    except Exception as e:
        logger.warning(f"LLM intent analysis failed, using fallback: {e}")
        return _fallback_intent_analysis(query)


def _fallback_intent_analysis(query: str) -> dict:
    """基于关键词的回退意图分析"""
    query_lower = query.lower()
    scores = {}
    for atype, info in AGENT_CAPABILITIES.items():
        score = sum(1 for kw in info["keywords"] if kw in query_lower)
        scores[atype] = score

    # 找到所有得分 > 0 的Agent
    active_agents = [(atype, score) for atype, score in scores.items() if score > 0]
    active_agents.sort(key=lambda x: x[1], reverse=True)

    if not active_agents:
        # 默认使用query agent
        return {
            "is_complex": False,
            "sub_tasks": [{"agent_type": "query", "task": query, "priority": 1}],
            "summary_strategy": "parallel",
        }

    if len(active_agents) == 1:
        return {
            "is_complex": False,
            "sub_tasks": [{"agent_type": active_agents[0][0], "task": query, "priority": 1}],
            "summary_strategy": "parallel",
        }

    # 多Agent场景
    sub_tasks = []
    for i, (atype, _) in enumerate(active_agents[:3]):
        agent_name = AGENT_CAPABILITIES[atype]["name"]
        sub_tasks.append({
            "agent_type": atype,
            "task": f"从{agent_name}角度分析：{query}",
            "priority": i + 1,
        })

    return {
        "is_complex": True,
        "sub_tasks": sub_tasks,
        "summary_strategy": "parallel",
    }


# ==================== 任务执行 ====================

async def _execute_sub_task(
    db: AsyncSession,
    agent_type: str,
    task: str,
    user_id: str = "",
    context: Optional[dict] = None,
) -> dict:
    """执行单个子任务"""
    from app.services.agent_service import _run_agent

    try:
        result = await _run_agent(agent_type, task, context, user_id)
        return {
            "agent_type": agent_type,
            "agent_name": AGENT_CAPABILITIES.get(agent_type, {}).get("name", agent_type),
            "task": task,
            "response": result.get("response", ""),
            "steps": result.get("steps", []),
            "elapsed_ms": result.get("elapsed_ms", 0),
            "success": True,
        }
    except Exception as e:
        logger.error(f"Sub-task execution failed ({agent_type}): {e}")
        return {
            "agent_type": agent_type,
            "agent_name": AGENT_CAPABILITIES.get(agent_type, {}).get("name", agent_type),
            "task": task,
            "response": f"任务执行失败: {str(e)}",
            "steps": [],
            "elapsed_ms": 0,
            "success": False,
        }


# ==================== 结果汇总 ====================

async def _summarize_results(
    original_query: str,
    sub_results: list[dict],
) -> str:
    """用LLM汇总各Agent的结果，生成最终回答"""
    api_key = settings.DEEPSEEK_API_KEY
    if not api_key or not api_key.startswith("sk-"):
        # 无API Key时直接拼接
        parts = []
        for r in sub_results:
            parts.append(f"【{r['agent_name']}】\n{r['response']}")
        return "\n\n".join(parts)

    try:
        llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            api_key=api_key,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=2048,
        )

        # 构建各Agent结果摘要
        agent_outputs = []
        for r in sub_results:
            status = "✓" if r["success"] else "✗"
            agent_outputs.append(
                f"[{status} {r['agent_name']}] 任务：{r['task']}\n回答：{r['response'][:1500]}"
            )

        outputs_text = "\n\n---\n\n".join(agent_outputs)

        prompt = f"""你是能源可信数据空间的智能助手。多个专业Agent已分别完成了用户需求的各个部分，请综合它们的结果，生成一份完整、专业的最终回答。

用户原始需求：{original_query}

各Agent的分析结果：
{outputs_text}

请生成最终回答：
1. 综合各Agent的分析结果，不要遗漏重要信息
2. 使用专业的能源行业术语
3. 结构清晰，使用标题和列表
4. 如果有冲突信息，说明不同观点
5. 在回答末尾标注信息来源Agent"""

        result = await llm.ainvoke([
            SystemMessage(content="你是能源数据空间的智能综合分析师。"),
            HumanMessage(content=prompt),
        ])

        return result.content

    except Exception as e:
        logger.warning(f"LLM summarization failed, using raw results: {e}")
        parts = []
        for r in sub_results:
            parts.append(f"【{r['agent_name']}】\n{r['response']}")
        return "\n\n".join(parts)


# ==================== 主编排接口 ====================

async def orchestrate(
    db: AsyncSession,
    query: str,
    context: Optional[dict] = None,
    user_id: str = "",
) -> dict:
    """
    Orchestrator 主入口

    流程：
    1. 意图分析 → 拆分子任务
    2. 任务调度 → 并行/串行执行
    3. 结果汇总 → 生成最终回答

    参数：
        query: 用户复杂需求
        context: 上下文信息
        user_id: 用户ID

    返回：
        {
            "original_query": str,
            "is_complex": bool,
            "sub_tasks": [...],
            "sub_results": [...],
            "final_response": str,
            "total_elapsed_ms": float,
            "agents_used": [...],
        }
    """
    if not query or not query.strip():
        raise DataValidationError("查询内容不能为空")

    start_time = datetime.now(timezone.utc)

    # 1. 意图分析
    intent = await _analyze_intent(query)
    sub_tasks = intent.get("sub_tasks", [])
    is_complex = intent.get("is_complex", False)
    strategy = intent.get("summary_strategy", "parallel")

    if not sub_tasks:
        sub_tasks = [{"agent_type": "query", "task": query, "priority": 1}]

    # 2. 任务调度与执行
    sub_results = []

    if strategy == "parallel" and len(sub_tasks) > 1:
        # 并行执行
        tasks_coroutines = [
            _execute_sub_task(db, st["agent_type"], st["task"], user_id, context)
            for st in sub_tasks
        ]
        sub_results = await asyncio.gather(*tasks_coroutines, return_exceptions=False)
        sub_results = list(sub_results)
    else:
        # 串行执行
        for st in sub_tasks:
            result = await _execute_sub_task(
                db, st["agent_type"], st["task"], user_id, context
            )
            sub_results.append(result)

    # 3. 结果汇总
    final_response = await _summarize_results(query, sub_results)

    elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    agents_used = list({r["agent_type"] for r in sub_results})

    logger.info(
        f"Orchestrate: query='{query[:50]}', agents={agents_used}, "
        f"complex={is_complex}, {elapsed_ms:.0f}ms"
    )

    return {
        "original_query": query,
        "is_complex": is_complex,
        "sub_tasks": [
            {"agent_type": st["agent_type"], "task": st["task"], "priority": st.get("priority", 1)}
            for st in sub_tasks
        ],
        "sub_results": sub_results,
        "final_response": final_response,
        "total_elapsed_ms": round(elapsed_ms, 1),
        "agents_used": agents_used,
        "execution_strategy": strategy,
    }
