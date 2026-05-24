"""
分页工具
分页参数解析 + 分页查询构造
"""
import uuid
import logging
from typing import Optional, TypeVar, Any
from fastapi import Query
from sqlalchemy import Select, func, MetaData as SAMetaData
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")

# SQLAlchemy DeclarativeBase 内部属性名，与 DB 列名冲突时需特殊处理
_DELEGATE_BASE_ATTRS = {"metadata", "registry"}


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=1000, description="每页大小")
    sort_by: Optional[str] = Field(default="created_at", description="排序字段")
    sort_order: Optional[str] = Field(default="desc", description="排序方向")


def get_pagination_params(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=1000, description="每页大小"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向 asc/desc"),
) -> PaginationParams:
    """FastAPI 依赖注入 - 分页参数"""
    return PaginationParams(
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order
    )


def _model_to_dict(obj) -> dict:
    """
    将 SQLAlchemy 模型实例转为字典。

    特殊处理：
    - UUID 字段转为字符串
    - 列名与 DeclarativeBase 内部属性冲突（如 'metadata'）时，
      优先使用 ORM 映射的 Python 属性名（如 'metadata_'）获取实际值。

    Args:
        obj: SQLAlchemy 模型实例

    Returns:
        列名 → 值 的字典
    """
    if not hasattr(obj, "__table__"):
        return obj

    d = {}
    # 构建 DB 列名 → Python 属性名 的映射（处理 metadata_ → metadata 等情况）
    mapper = obj.__mapper__
    col_to_attr: dict[str, str] = {}
    for attr_name, col_prop in mapper.column_attrs.items():
        for col in col_prop.columns:
            col_to_attr[col.name] = attr_name

    for col in obj.__table__.columns:
        # 如果列名与 DeclarativeBase 内部属性冲突，使用 ORM 映射的属性名
        if col.name in _DELEGATE_BASE_ATTRS and col.name in col_to_attr:
            attr_name = col_to_attr[col.name]
            val = getattr(obj, attr_name)
        else:
            val = getattr(obj, col.name)

        # UUID 转字符串
        if isinstance(val, uuid.UUID):
            val = str(val)
        # 兜底：如果仍拿到 SQLAlchemy MetaData 对象，替换为空字典
        elif isinstance(val, SAMetaData):
            logger.warning(f"_model_to_dict: column '{col.name}' returned SAMetaData, using fallback")
            val = getattr(obj, col_to_attr.get(col.name, col.name), None)
            if isinstance(val, SAMetaData):
                val = {}

        d[col.name] = val
    return d


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
        items = [response_model.model_validate(_model_to_dict(item)) for item in items]
    else:
        items = [_model_to_dict(item) if hasattr(item, "__table__") else item for item in items]

    total_pages = (total + params.page_size - 1) // params.page_size if params.page_size > 0 else 0

    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )
