"""
响应格式化工具
统一 API 响应格式: {code, message, data, timestamp}
"""
from datetime import datetime, timezone
from typing import Any, Optional


def success_response(
    data: Any = None,
    message: str = "success",
    code: int = 0,
) -> dict:
    """
    成功响应

    Args:
        data: 响应数据
        message: 响应消息
        code: 错误码（0=成功）

    Returns:
        统一响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def error_response(
    message: str,
    code: int = 9000,
    data: Any = None,
) -> dict:
    """
    错误响应

    Args:
        message: 错误消息
        code: 错误码
        data: 附加数据

    Returns:
        统一响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def paginated_response(
    items: list,
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "success",
) -> dict:
    """
    分页响应

    Args:
        items: 当前页数据
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        message: 响应消息

    Returns:
        统一分页响应字典
    """
    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
        message=message,
    )
