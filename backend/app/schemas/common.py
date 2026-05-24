"""
通用响应/请求 Schema
ApiResponse / PaginatedResponse / PaginatedRequest / ErrorResponse
"""
from typing import Any, Optional, Generic, TypeVar
from datetime import datetime, timezone

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应"""
    code: int = Field(default=0, description="错误码，0=成功")
    message: str = Field(default="success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="时间戳",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应数据"""
    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    total_pages: int = Field(default=0, description="总页数")


class PaginatedRequest(BaseModel):
    """分页请求参数"""
    page: int = Field(default=1, ge=1, description="页码，1-based")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    sort_by: Optional[str] = Field(default="created_at", description="排序字段")
    sort_order: Optional[str] = Field(default="desc", description="排序方向 asc/desc")


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    data: Any = Field(default=None, description="附加数据")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IdResponse(BaseModel):
    """ID 响应"""
    id: str = Field(description="资源 ID")
