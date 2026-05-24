"""
AI Agent 统一对话 API - /api/v1/agent
======================================
POST /chat       — 统一 Agent 对话（根据 agent_type 路由）
GET  /agents     — 列出可用 Agent
POST /execute    — 执行 Agent 任务（自动选择 Agent）
GET  /history    — 对话历史
"""
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
