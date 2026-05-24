"""
LLM 大模型集成 API - /api/v1/llm
DeepSeek-V3 / ChatGLM-4 / Qwen-Max 对话 + SSE 流式 + 报告生成 + 对话历史
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import llm_service
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Request 模型
# ============================================================


class ChatMessage(BaseModel):
    """单条对话消息"""
    role: str = Field(description="角色: user / assistant / system")
    content: str = Field(description="消息内容")


class ChatRequest(BaseModel):
    """LLM 对话请求"""
    messages: list[ChatMessage] = Field(description="对话消息列表")
    model_id: str = Field(default="deepseek-chat", description="模型 ID: deepseek-chat / chatglm-4 / qwen-max")
    conversation_id: Optional[str] = Field(default=None, description="对话 ID（续接对话时传入）")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=2048, ge=1, le=32768, description="最大生成 token 数")
    system_prompt: Optional[str] = Field(default=None, description="自定义系统提示词")
    stream: bool = Field(default=False, description="是否启用 SSE 流式输出")


class ReportGenerateRequest(BaseModel):
    """智能报告生成请求"""
    report_type: str = Field(description="报告类型: security / data_quality / compliance / asset_usage")
    title: str = Field(description="报告标题")
    additional_context: Optional[str] = Field(default=None, description="额外上下文信息")
    model_id: str = Field(default="deepseek-chat", description="使用的 LLM 模型 ID")


# ============================================================
# API 端点
# ============================================================


@router.get("/models", response_model=ApiResponse)
async def get_available_models(
    user: dict = Depends(get_current_user),
):
    """获取可用 LLM 模型列表"""
    try:
        result = await llm_service.get_available_models()
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return ApiResponse(code=4000, message=f"获取模型列表失败: {e}", data=None)


@router.post("/chat", response_model=ApiResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """LLM 对话接口（支持流式与非流式）

    当 stream=true 时返回 SSE（text/event-stream）格式响应。
    """
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if request.stream:
        # SSE 流式响应
        async def event_generator():
            async for chunk in llm_service.chat_stream(
                db=db,
                messages=messages,
                model_id=request.model_id,
                conversation_id=request.conversation_id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                system_prompt=request.system_prompt,
                user_id=user.get("user_id", ""),
            ):
                yield chunk

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # 非流式响应
    try:
        result = await llm_service.chat(
            db=db,
            messages=messages,
            model_id=request.model_id,
            conversation_id=request.conversation_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        logger.warning(f"对话参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"LLM 对话失败: {e}")
        return ApiResponse(code=4000, message=f"对话失败: {e}", data=None)


@router.post("/report/generate", response_model=ApiResponse)
async def generate_report(
    request: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """智能报告生成

    基于数据空间数据和 LLM 自动生成安全 / 数据质量 / 合规 / 资产使用分析报告。
    """
    try:
        result = await llm_service.generate_report(
            db=db,
            report_type=request.report_type,
            title=request.title,
            additional_context=request.additional_context,
            model_id=request.model_id,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        logger.warning(f"报告生成参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        return ApiResponse(code=4000, message=f"报告生成失败: {e}", data=None)


@router.get("/history", response_model=ApiResponse)
async def get_conversation_history(
    conversation_id: Optional[str] = Query(None, description="对话 ID（不传则列出所有对话）"),
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: dict = Depends(get_current_user),
):
    """获取对话历史"""
    try:
        result = await llm_service.get_conversation_history(
            conversation_id=conversation_id,
            user_id=user.get("user_id", ""),
            limit=limit,
            offset=offset,
        )
        return ApiResponse(data=result)
    except DataNotFoundError as e:
        logger.warning(f"对话不存在: {conversation_id}")
        return ApiResponse(code=2001, message=e.message, data=None)
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        return ApiResponse(code=4000, message=f"获取历史失败: {e}", data=None)
