"""
AI Agent API - /api/v1/compute/agents
QueryAgent / TradeAgent / SecurityAgent / DispatchAgent / 对话历史
支持 SSE 流式输出
"""
from typing import Optional

from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.compute import (
    AgentQueryRequest,
    AgentTradeRequest,
    AgentSecurityRequest,
    AgentDispatchRequest,
)
from app.utils.deps import get_current_user
from app.services import agent_service

router = APIRouter()


@router.post("/query", response_model=ApiResponse)
async def query_agent(
    body: AgentQueryRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    QueryAgent — 数据查询智能助手

    解析自然语言查询，转化为结构化数据检索。
    支持: 发电量查询/用电分析/市场价格/趋势预测/对比分析
    """
    result = await agent_service.query_agent(
        db=db, query=body.query, context=body.context, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.post("/query/stream")
async def query_agent_stream(
    body: AgentQueryRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    QueryAgent — 数据查询智能助手 (SSE 流式输出)
    """
    async def event_generator():
        async for chunk in agent_service.query_agent_stream(
            db=db, query=body.query, context=body.context, user_id=user["user_id"],
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


@router.post("/trade", response_model=ApiResponse)
async def trade_agent(
    body: AgentTradeRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    TradeAgent — 交易撮合助手

    分析市场供需，提供交易建议和风险评估。
    支持: 供需匹配/价格建议/交易策略/风险评估
    """
    result = await agent_service.trade_agent(
        db=db, query=body.request, context=body.context, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.post("/trade/stream")
async def trade_agent_stream(
    body: AgentTradeRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    TradeAgent — 交易撮合助手 (SSE 流式输出)
    """
    async def event_generator():
        async for chunk in agent_service.trade_agent_stream(
            db=db, query=body.request, context=body.context, user_id=user["user_id"],
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


@router.post("/security", response_model=ApiResponse)
async def security_agent(
    body: AgentSecurityRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    SecurityAgent — 安全分析助手

    识别安全威胁，检查合规性，提供安全策略建议。
    支持: 威胁分析/合规检查/安全评估/策略建议
    """
    result = await agent_service.security_agent(
        db=db, query=body.query, context=body.context, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.post("/security/stream")
async def security_agent_stream(
    body: AgentSecurityRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    SecurityAgent — 安全分析助手 (SSE 流式输出)
    """
    async def event_generator():
        async for chunk in agent_service.security_agent_stream(
            db=db, query=body.query, context=body.context, user_id=user["user_id"],
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


@router.post("/dispatch", response_model=ApiResponse)
async def dispatch_agent(
    body: AgentDispatchRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    DispatchAgent — 调度优化助手

    分析负荷数据，优化调度策略，提高新能源消纳率。
    支持: 负荷预测/调度建议/新能源消纳/峰谷分析
    """
    result = await agent_service.dispatch_agent(
        db=db, query=body.task, context=body.context, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.post("/dispatch/stream")
async def dispatch_agent_stream(
    body: AgentDispatchRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    DispatchAgent — 调度优化助手 (SSE 流式输出)
    """
    async def event_generator():
        async for chunk in agent_service.dispatch_agent_stream(
            db=db, query=body.task, context=body.context, user_id=user["user_id"],
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


@router.get("/history", response_model=ApiResponse)
async def get_history(
    agent_type: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """对话历史记录"""
    result = await agent_service.get_conversation_history(
        user_id=user["user_id"],
        agent_type=agent_type,
        limit=limit,
    )
    return ApiResponse(data=result)
