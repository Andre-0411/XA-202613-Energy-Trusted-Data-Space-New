"""
AI Agent module for Analytics Center.

This module provides AI-powered chat functionality for the Energy Trusted Data Space.
Integrates with DeepSeek LLM API for real AI responses, with predefined Q&A as fallback.
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime

from app.config import settings
from app.schemas.analytics import AIChatMessage, AIChatRequest, AIChatResponse

logger = logging.getLogger(__name__)

# LLM 系统提示词
ANALYTICS_SYSTEM_PROMPT = (
    "你是能源可信数据空间分析中心的 AI 助手。你的专长领域包括：\n"
    "1. 新能源发电预测（联邦学习技术）\n"
    "2. 电力市场交易机制（MPC 隐私计算）\n"
    "3. 虚拟电厂调度（TEE 可信执行环境）\n"
    "4. 数据安全合规（DID、区块链存证）\n"
    "5. 隐私计算技术（联邦学习、MPC、TEE、同态加密）\n"
    "6. 数据共享流程与数据治理\n"
    "7. 能源可信数据空间平台功能\n\n"
    "请用专业、准确的中文回答用户问题。如果问题涉及具体数据，请说明需要查询实际数据才能给出精确结果。"
)


# Predefined Q&A pairs for energy domain questions
PREDEFINED_QA = [
    {
        "keywords": ["新能源", "发电预测", "新能源发电", "风光预测", "可再生能源预测"],
        "answer": """新能源发电预测是基于联邦学习（Federated Learning）技术的智能预测方法。

**核心技术：**
- 利用联邦学习整合多个发电企业的数据，无需数据出境
- 各参与方在本地训练模型，仅交换模型参数更新
- 保护数据隐私的同时提升预测精度

**应用场景：**
- 风电功率预测（短期、超短期）
- 光伏发电预测（考虑天气、季节因素）
- 多能源协同预测

**优势：**
- 预测精度提升15-25%
- 数据不出域，符合隐私保护要求
- 支持小样本学习，适应新能源波动性

系统支持接入气象数据、历史发电数据等多源数据，通过安全多方计算实现协同预测。""",
        "sources": ["联邦学习技术白皮书", "新能源预测最佳实践"],
        "confidence": 0.92
    },
    {
        "keywords": ["电力市场", "市场交易", "电力交易", "市场化交易", "结算"],
        "answer": """电力市场交易基于多方安全计算（MPC）技术实现隐私保护的交易结算。

**核心功能：**
- 实时电价预测与发布
- 隐私保护的双向竞价匹配
- 基于智能合约的自动结算
- 交易数据存证与审计

**技术架构：**
- 采用MPC协议，确保报价信息不泄露
- 区块链技术保证交易不可篡改
- 可信执行环境（TEE）保护核心算法

**交易类型：**
- 中长期交易（年月季度）
- 现货交易（日前、日内、实时）
- 辅助服务交易（调频、备用）

**优势：**
- 交易透明度提升，防止市场操纵
- 结算效率提升80%
- 全流程可追溯，符合监管要求""",
        "sources": ["电力市场运营规则", "MPC技术应用指南"],
        "confidence": 0.89
    },
    {
        "keywords": ["虚拟电厂", "调度", "负荷调度", "需求响应", "VPP"],
        "answer": """虚拟电厂调度基于可信执行环境（TEE）技术实现安全高效的资源调度。

**核心能力：**
- 分布式能源聚合（储能、可调节负荷、电动汽车）
- 实时负荷预测与调度优化
- 需求响应自动触发与执行
- 与电网调度系统互联互通

**TEE技术应用：**
- 调度策略在可信环境中计算，防止策略泄露
- 用户负荷数据加密处理，保护隐私
- 调度指令签名验证，防止恶意操控

**调度模式：**
- 日前调度计划编制
- 日内滚动优化
- 实时紧急调度

**效益：**
- 提升可再生能源消纳能力20-30%
- 降低用户用电成本10-15%
- 增强电网灵活调节能力""",
        "sources": ["虚拟电厂技术标准", "TEE安全调度规范"],
        "confidence": 0.87
    },
    {
        "keywords": ["数据安全", "合规", "隐私保护", "数据合规", "安全合规", "DID", "区块链"],
        "answer": """数据安全合规体系基于DID（去中心化身份）和区块链技术构建。

**合规框架：**
- 符合国家数据安全法、个人信息保护法要求
- 通过等保三级、可信数据空间认证
- 遵循能源行业数据分类分级规范

**DID身份体系：**
- 每个参与方拥有独立的去中心化标识符
- 支持跨域身份认证与授权
- 身份凭证可验证、可撤销

**区块链存证：**
- 所有数据访问、使用行为上链存证
- 智能合约自动执行合规规则
- 提供完整的审计追踪能力

**隐私计算技术：**
- 联邦学习：数据不动模型动
- 多方安全计算：数据可用不可见
- 可信执行环境：硬件级安全防护
- 同态加密：密文直接计算

**合规工具：**
- 数据分类分级自动化工具
- 合规风险评估系统
- 数据出境安全评估""",
        "sources": ["数据安全法", "个人信息保护法", "可信数据空间标准"],
        "confidence": 0.94
    },
    {
        "keywords": ["系统功能", "功能介绍", "系统介绍", "平台功能", "五大中心"],
        "answer": """能源可信数据空间平台包含五大中心，构建完整的能源数据流通生态：

**1. 数据中心（Data Center）**
- 数据资产管理与目录服务
- 数据上链存证与溯源
- 数据质量评估与治理
- 支持结构化、非结构化数据

**2. 计算中心（Computation Center）**
- 隐私计算任务编排
- 联邦学习模型训练
- 多方安全计算协议执行
- 可信执行环境管理

**3. 运营中心（Operations Center）**
- 用户与组织管理
- 认证与授权服务
- 审计日志与合规监控
- 系统配置与维护

**4. 分析中心（Analytics Center）**
- 系统运行数据统计
- 趋势分析与预测
- AI智能问答服务
- 可视化报表生成

**5. 交易中心（Exchange Center）**
- 数据产品发布与交易
- 计价与结算服务
- 交易合同管理
- 收益分配机制

**技术特色：**
- 自主可控的隐私计算技术栈
- 支持多种信任框架（DID、VC、区块链）
- 提供SDK和API，支持快速集成""",
        "sources": ["能源可信数据空间产品手册"],
        "confidence": 0.91
    },
    {
        "keywords": ["数据共享", "共享流程", "数据流转", "共享机制", "数据交换"],
        "answer": """数据共享流程基于可信数据空间标准，确保数据"可用不可见"：

**流程步骤：**

**1. 数据注册**
- 数据提供方在数据中心注册数据资产
- 填写数据元数据（格式、更新频率、质量等）
- 系统自动进行数据分类分级
- 生成数据目录并上链存证

**2. 需求发布**
- 数据需求方浏览数据目录
- 提交数据使用申请，说明用途和范围
- 系统自动匹配或人工审核

**3. 合约签订**
- 双方协商数据使用条款（期限、费用、用途限制）
- 生成智能合约，明确各方权责
- 数字签名确认，上链存储

**4. 授权访问**
- 需求方获得授权凭证（VC）
- 通过DID身份验证
- 获取受限的数据访问权限

**5. 隐私计算**
- 数据不离开提供方本地
- 通过联邦学习或MPC进行计算
- 仅返回计算结果，不返回原始数据

**6. 结算与审计**
- 按智能合约自动结算费用
- 所有操作上链存证
- 提供合规审计报告

**安全保障：**
- 数据不出域，仅输出计算结果
- 全链路可追溯、可审计
- 支持使用控制（Use Control），防止数据滥用""",
        "sources": ["可信数据空间架构", "数据共享最佳实践"],
        "confidence": 0.88
    },
    {
        "keywords": ["隐私计算", "联邦学习", "多方安全计算", "MPC", "TEE", "同态加密", "HE", "安全计算"],
        "answer": """隐私计算是实现"数据可用不可见"的关键技术体系：

**1. 联邦学习（Federated Learning）**
- **原理**：各方在本地训练模型，仅交换梯度或参数更新
- **应用**：新能源发电预测、负荷预测、设备健康管理
- **优势**：数据不离开本地，保护隐私；支持异构数据
- **类型**：横向联邦、纵向联邦、联邦迁移学习

**2. 多方安全计算（MPC）**
- **原理**：多个参与方协同计算，各自输入保密
- **协议**：秘密分享、不经意传输、混淆电路
- **应用**：电力市场交易结算、碳排放核算
- **优势**：数学可证明的安全性

**3. 可信执行环境（TEE）**
- **原理**：硬件级安全隔离区域，保护代码和数据
- **技术**：Intel SGX、ARM TrustZone
- **应用**：虚拟电厂调度、密钥管理
- **优势**：高性能，适合复杂计算

**4. 同态加密（Homomorphic Encryption）**
- **原理**：支持密文直接计算，结果解密后正确
- **类型**：部分同态、浅同态、全同态
- **应用**：统计查询、简单计算
- **优势**：最强的数据保护，但计算开销较大

**技术选型建议：**
- 大数据量、复杂模型 → 联邦学习
- 精确计算、多方协作 → MPC
- 高性能要求 → TEE
- 简单统计、高安全等级 → 同态加密

**平台支持：**
本平台完整支持上述四种技术，提供统一的计算任务编排和资源管理。""",
        "sources": ["隐私计算技术白皮书", "联邦学习应用场景"],
        "confidence": 0.95
    }
]


def match_question(user_message: str) -> Optional[Dict]:
    """
    Match user message against predefined Q&A pairs using keyword matching.
    Used as fallback when LLM API is unavailable.

    Args:
        user_message: User's input message

    Returns:
        Matched Q&A item or None if no match found
    """
    user_message_lower = user_message.lower()

    for qa_item in PREDEFINED_QA:
        for keyword in qa_item["keywords"]:
            if keyword.lower() in user_message_lower:
                return qa_item

    return None


def _is_api_key_configured() -> bool:
    """检查 DeepSeek API Key 是否已配置"""
    key = settings.DEEPSEEK_API_KEY
    return bool(key) and key.startswith("sk-") and key != "sk-your-api-key-here"


def _call_llm_sync(message: str, context: dict = None) -> Optional[str]:
    """
    同步调用 DeepSeek LLM API（用于非异步场景）

    Args:
        message: 用户消息
        context: 上下文信息

    Returns:
        LLM 回复内容，失败返回 None
    """
    if not _is_api_key_configured():
        return None

    try:
        import httpx

        system_prompt = ANALYTICS_SYSTEM_PROMPT
        if context:
            system_prompt += f"\n\n用户上下文: 角色={context.get('role', '未知')}, 组织={context.get('organization', '未知')}"

        payload = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"LLM API 调用失败: {e}")
        return None


async def _call_llm_async(message: str, context: dict = None) -> Optional[str]:
    """
    异步调用 DeepSeek LLM API

    Args:
        message: 用户消息
        context: 上下文信息

    Returns:
        LLM 回复内容，失败返回 None
    """
    if not _is_api_key_configured():
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )

        system_prompt = ANALYTICS_SYSTEM_PROMPT
        if context:
            system_prompt += f"\n\n用户上下文: 角色={context.get('role', '未知')}, 组织={context.get('organization', '未知')}"

        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"LLM API 异步调用失败: {e}")
        return None


def chat(
    message: str,
    session_id: str = None,
    context: dict = None
) -> AIChatResponse:
    """
    Chat with AI agent — 优先使用真实 LLM，回退到预定义 Q&A。

    Args:
        message: User's input message
        session_id: Optional session ID for conversation tracking
        context: Optional context information (user role, organization, etc.)

    Returns:
        AIChatResponse with reply, session_id, sources, and confidence
    """
    import uuid

    if session_id is None:
        session_id = str(uuid.uuid4())

    # 优先尝试 LLM API
    llm_response = _call_llm_sync(message, context)
    if llm_response:
        return AIChatResponse(
            message=AIChatMessage(
                role="assistant",
                content=llm_response,
                timestamp=datetime.utcnow()
            ),
            session_id=session_id,
            sources=["DeepSeek AI"],
            confidence=0.9
        )

    # LLM 不可用，回退到预定义 Q&A
    matched_qa = match_question(message)
    if matched_qa:
        return AIChatResponse(
            message=AIChatMessage(
                role="assistant",
                content=matched_qa["answer"],
                timestamp=datetime.utcnow()
            ),
            session_id=session_id,
            sources=matched_qa.get("sources", []),
            confidence=matched_qa.get("confidence", 0.8)
        )

    # 最终回退
    fallback_answer = """感谢您的提问。我是能源可信数据空间的AI助手，可以为您解答以下类型的问题：

**我可以帮您解答：**
- 新能源发电预测技术
- 电力市场交易机制
- 虚拟电厂调度策略
- 数据安全合规要求
- 系统功能介绍（五大中心）
- 数据共享流程
- 隐私计算技术（联邦学习、MPC、TEE、同态加密）

**建议：**
请尝试使用更准确的关键词，例如"新能源发电预测"、"数据安全合规"等。

如需更深入的技术支持，请联系我们的技术团队。"""

    return AIChatResponse(
        message=AIChatMessage(
            role="assistant",
            content=fallback_answer,
            timestamp=datetime.utcnow()
        ),
        session_id=session_id,
        sources=[],
        confidence=0.5
    )


async def chat_async(
    message: str,
    session_id: str = None,
    context: dict = None
) -> AIChatResponse:
    """
    异步 Chat — 优先使用真实 LLM API。

    Args:
        message: 用户消息
        session_id: 会话 ID
        context: 上下文

    Returns:
        AIChatResponse
    """
    import uuid

    if session_id is None:
        session_id = str(uuid.uuid4())

    # 优先尝试 LLM API
    llm_response = await _call_llm_async(message, context)
    if llm_response:
        return AIChatResponse(
            message=AIChatMessage(
                role="assistant",
                content=llm_response,
                timestamp=datetime.utcnow()
            ),
            session_id=session_id,
            sources=["DeepSeek AI"],
            confidence=0.9
        )

    # 回退到同步 chat
    return chat(message, session_id, context)


def llm_chat_sync(message: str, context: dict = None) -> str:
    """
    同步 LLM 对话接口 — 优先使用真实 API。

    Args:
        message: 用户消息
        context: 上下文信息

    Returns:
        LLM 回复文本
    """
    # 优先尝试真实 LLM
    llm_response = _call_llm_sync(message, context)
    if llm_response:
        return llm_response

    # 回退到预定义 Q&A
    response = chat(message, context=context)
    return response.message.content


# In-memory session storage for chat history
_chat_history: Dict[str, List[AIChatMessage]] = {}


def get_chat_history(session_id: str, limit: int = 10) -> List[AIChatMessage]:
    """
    Get chat history for a session.

    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return (default: 10)

    Returns:
        List of AIChatMessage objects, most recent first
    """
    if session_id not in _chat_history:
        return []

    # Return last 'limit' messages
    history = _chat_history[session_id]
    return history[-limit:] if len(history) > limit else history


def save_chat_message(session_id: str, message: AIChatMessage):
    """
    Save a chat message to session history.

    Args:
        session_id: Session identifier
        message: AIChatMessage to save
    """
    if session_id not in _chat_history:
        _chat_history[session_id] = []

    _chat_history[session_id].append(message)

    # Limit history size to prevent memory issues
    if len(_chat_history[session_id]) > 100:
        _chat_history[session_id] = _chat_history[session_id][-100:]
