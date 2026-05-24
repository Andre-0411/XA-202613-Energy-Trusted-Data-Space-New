"""
分页工具
分页参数解析 + 分页查询构造
"""
import uuid
from typing import Optional, TypeVar, Any
from fastapi import Query
from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    sort_by: Optional[str] = Field(default="created_at", description="排序字段")
    sort_order: Optional[str] = Field(default="desc", description="排序方向")


def get_pagination_params(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向 asc/desc"),
) -> PaginationParams:
    """FastAPI 依赖注入 - 分页参数"""
    return PaginationParams(
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order
    )


async def paginate_query(
    db: AsyncSession,
    query: Select,
    params: PaginationParams,
    response_model: Any = None,
) -> PaginatedResponse:
    """
    执行分页查询

    Args:
        db: 数据库会话
        query: SQLAlchemy 查询
        params: 分页参数
        response_model: 响应模型（用于序列化）

    Returns:
        分页响应
    """
    # 计算总数
    count_query = query.with_only_columns(func.count()).order_by(None)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 计算偏移
    offset = (params.page - 1) * params.page_size

    # 应用排序
    if params.sort_by:
        try:
            model_class = query.column_descriptions[0]["type"]
            if hasattr(model_class, params.sort_by):
                sort_column = getattr(model_class, params.sort_by)
                if params.sort_order == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
        except (IndexError, KeyError, AttributeError):
            pass  # 排序字段无效时跳过排序

    # 应用分页
    query = query.offset(offset).limit(params.page_size)

    # 执行查询
    result = await db.execute(query)
    items = result.scalars().all()

    # 序列化
    if response_model:
        # 将 SQLAlchemy 模型转为 dict，UUID 转为字符串
        def _model_to_dict(obj):
            if hasattr(obj, "__table__"):
                d = {}
                for col in obj.__table__.columns:
                    val = getattr(obj, col.name)
                    if isinstance(val, uuid.UUID):
                        val = str(val)
                    d[col.name] = val
                return d
            return obj
        items = [response_model.model_validate(_model_to_dict(item)) for item in items]
    else:
        items = [dict(item) if hasattr(item, "__dict__") else item for item in items]

    total_pages = (total + params.page_size - 1) // params.page_size if params.page_size > 0 else 0

    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )
