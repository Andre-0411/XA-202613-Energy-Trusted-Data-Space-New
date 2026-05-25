"""
AI Agent 统一对话 API - /api/v1/agent
======================================
POST /chat              — 统一 Agent 对话（根据 agent_type 路由）
GET  /agents            — 列出可用 Agent
POST /execute           — 执行 Agent 任务（自动选择 Agent）
GET  /history           — 对话历史
POST /orchestrate       — Orchestrator 多Agent协作编排
GET  /recommendations   — 数据产品智能推荐
POST /privacy-compute   — 通过Agent发起隐私计算任务
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Body, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import agent_service
from app.exceptions import DataValidationError

router = APIRouter()


# ==================== Request/Response 模型 ====================


class AgentChatRequest(BaseModel):
    """统一 Agent 对话请求"""
    agent_type: str = Field(
        description="Agent 类型: query/trade/security/dispatch",
        examples=["query"],
    )
    query: str = Field(description="用户查询内容")
    context: Optional[dict] = Field(default=None, description="上下文信息")
    stream: bool = Field(default=False, description="是否启用 SSE 流式输出")


class AgentExecuteRequest(BaseModel):
    """Agent 任务执行请求"""
    agent_type: Optional[str] = Field(
        default=None,
        description="Agent 类型（不传则自动推断）: query/trade/security/dispatch",
    )
    task: str = Field(description="任务描述")
    context: Optional[dict] = Field(default=None, description="上下文信息")


class OrchestrateRequest(BaseModel):
    """Orchestrator 多Agent协作请求"""
    query: str = Field(description="复杂需求描述，系统自动拆分为多Agent子任务")
    context: Optional[dict] = Field(default=None, description="上下文信息")


class PrivacyComputeRequest(BaseModel):
    """隐私计算任务请求"""
    compute_type: str = Field(
        description="计算类型: fl(联邦学习)/mpc(安全多方计算)/he(同态加密)/dp(差分隐私)",
        examples=["fl"],
    )
    task_name: str = Field(description="任务名称")
    description: str = Field(default="", description="任务描述")
    config: Optional[dict] = Field(default=None, description="计算配置参数")


# ==================== API 端点 ====================


@router.get("/agents", response_model=ApiResponse)
async def list_agents(
    user: dict = Depends(get_current_user),
):
    """列出所有可用的 Agent 类型及其描述"""
    agents = agent_service.get_available_agents()
    return ApiResponse(data={
        "agents": agents,
        "total": len(agents),
        "supported_types": [a["type"] for a in agents],
    })


@router.post("/chat", response_model=ApiResponse)
async def agent_chat(
    body: AgentChatRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    统一 Agent 对话接口

    根据 agent_type 路由到对应的 Agent：
    - query: 数据查询 Agent（自然语言→数据检索）
    - trade: 交易结算 Agent（价格分析+报价策略）
    - security: 安全巡检 Agent（异常检测+安全报告）
    - dispatch: 调度优化 Agent（负荷预测+调度建议）
    """
    if body.stream:
        async def event_generator():
            async for chunk in agent_service.chat_stream(
                db=db,
                agent_type=body.agent_type,
                query=body.query,
                context=body.context,
                user_id=user.get("user_id", ""),
            ):
                yield f"data: {chunk}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await agent_service.chat(
            db=db,
            agent_type=body.agent_type,
            query=body.query,
            context=body.context,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        return ApiResponse(code=4000, message=f"Agent 对话失败: {e}", data=None)


@router.post("/execute", response_model=ApiResponse)
async def execute_task(
    body: AgentExecuteRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    执行 Agent 任务

    如果不指定 agent_type，系统会根据任务内容自动选择最合适的 Agent。
    """
    try:
        result = await agent_service.execute_task(
            db=db,
            agent_type=body.agent_type or "query",
            task=body.task,
            context=body.context,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        return ApiResponse(code=4000, message=f"Agent 任务执行失败: {e}", data=None)


@router.get("/history", response_model=ApiResponse)
async def get_history(
    agent_type: Optional[str] = Query(None, description="按 Agent 类型筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    user: dict = Depends(get_current_user),
):
    """获取用户的 Agent 对话历史"""
    result = await agent_service.get_conversation_history(
        user_id=user.get("user_id", ""),
        agent_type=agent_type,
        limit=limit,
    )
    return ApiResponse(data={"conversations": result, "total": len(result)})


@router.get("/recommendations", response_model=ApiResponse)
async def get_recommendations(
    industry: Optional[str] = Query(None, description="偏好行业: 新能源/电力/燃气"),
    data_type: Optional[str] = Query(None, description="偏好数据类型: 发电量/负荷/气象"),
    security_level: Optional[str] = Query(None, description="偏好安全等级: public/internal/confidential"),
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    数据产品智能推荐

    基于多种策略为用户推荐数据产品：
    - 基于内容的推荐：分析用户历史订阅，推荐同类产品
    - 协同过滤：相似用户订阅的产品
    - 热度推荐：近期热门产品

    每个推荐结果附带推荐理由。
    """
    from app.services.recommendation_service import get_personalized_recommendations

    try:
        result = await get_personalized_recommendations(
            db=db,
            user_id=user.get("user_id", ""),
            industry=industry or "",
            data_type=data_type or "",
            security_level=security_level or "",
            limit=limit,
        )
        return ApiResponse(data=result)
    except Exception as e:
        return ApiResponse(code=4000, message=f"推荐服务异常: {e}", data=None)


# ==================== 隐私计算端点 ====================


@router.get("/conversations/{conversation_id}", response_model=ApiResponse)
async def get_conversation_detail(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """获取指定对话的消息详情"""
    messages = await agent_service.get_conversation(conversation_id)
    return ApiResponse(data={
        "conversation_id": conversation_id,
        "messages": messages,
        "message_count": len(messages),
    })


@router.delete("/conversations/{conversation_id}", response_model=ApiResponse)
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """删除指定对话"""
    deleted = await agent_service.delete_conversation(conversation_id)
    if deleted:
        return ApiResponse(message="对话已删除")
    return ApiResponse(code=2001, message="对话不存在", data=None)


# ==================== Orchestrator 端点 ====================


@router.post("/orchestrate", response_model=ApiResponse)
async def orchestrate_task(
    body: OrchestrateRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Orchestrator 多Agent协作编排端点

    处理复杂多Agent任务，系统会：
    1. 用LLM分析需求，拆分为多个子任务
    2. 将子任务分配给对应的Agent（Query/Trade/Security/Dispatch）
    3. 并行或串行执行子任务
    4. 汇总各Agent结果，生成最终综合回答

    典型场景：
    - "评估山东新能源消纳方案" → DispatchAgent + SecurityAgent + TradeAgent
    - "分析昨天安全事件并生成报告" → SecurityAgent + QueryAgent
    - "查看市场行情并评估交易风险" → TradeAgent + QueryAgent
    """
    from app.services.orchestrator_service import orchestrate

    try:
        result = await orchestrate(
            db=db,
            query=body.query,
            context=body.context,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        return ApiResponse(code=4000, message=f"Orchestrator 执行失败: {e}", data=None)


# ==================== 推荐端点 ====================


@router.post("/privacy-compute", response_model=ApiResponse)
async def privacy_compute(
    body: PrivacyComputeRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    通过Agent发起隐私计算任务

    支持的计算类型：
    - fl: 联邦学习训练（FATE框架，支持lr/secureboost/nn等算法）
    - mpc: 安全多方计算（MP-SPDZ框架，支持spdz/aby3等协议）
    - he: 同态加密计算（SEAL框架，支持CKKS/BFV方案）
    - dp: 差分隐私查询（Laplace/Gaussian/Exponential机制）

    Agent会根据计算类型自动选择合适的工具执行任务。
    """
    from app.services.agent_service import _run_agent

    # 构建Agent查询
    compute_type_map = {
        "fl": "联邦学习",
        "mpc": "安全多方计算",
        "he": "同态加密",
        "dp": "差分隐私",
    }
    compute_name = compute_type_map.get(body.compute_type, body.compute_type)

    agent_query = (
        f"请为我创建一个{compute_name}计算任务。\n"
        f"任务名称：{body.task_name}\n"
        f"任务描述：{body.description}"
    )
    if body.config:
        agent_query += f"\n配置参数：{json.dumps(body.config, ensure_ascii=False)}"

    # 选择合适的Agent
    agent_type = "dispatch"  # dispatch agent 负责计算任务

    try:
        result = await _run_agent(
            agent_type=agent_type,
            query=agent_query,
            context={
                "user_id": user.get("user_id", ""),
                "organization_id": user.get("organization_id", ""),
                "permissions": user.get("permissions", []),
            },
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data={
            "compute_type": body.compute_type,
            "task_name": body.task_name,
            "agent_result": result,
        })
    except DataValidationError as e:
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        return ApiResponse(code=4000, message=f"隐私计算任务创建失败: {e}", data=None)
