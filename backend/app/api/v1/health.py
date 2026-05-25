"""
系统健康检查 API
提供详细的服务状态、数据库连接、缓存连接、区块链连接等健康信息
"""
import time
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 应用启动时间（模块级缓存）
_start_time: float = time.monotonic()


async def _check_database() -> dict:
    """检查 PostgreSQL 连接状态"""
    try:
        from app.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "healthy", "message": "连接正常"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"连接失败: {str(e)[:200]}"}


async def _check_redis() -> dict:
    """检查 Redis 连接状态"""
    try:
        from app.database import _get_redis_client
        client = _get_redis_client()
        if client is None:
            return {"status": "degraded", "message": "Redis 未配置或不可用（fail-open 模式）"}
        await client.ping()
        return {"status": "healthy", "message": "连接正常"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"连接失败: {str(e)[:200]}"}


async def _check_blockchain() -> dict:
    """检查区块链连接状态"""
    try:
        from app.core.fisco_client import fisco_client
        # 尝试获取区块号
        block_number = await fisco_client.get_block_number()
        return {"status": "healthy", "message": f"连接正常，最新区块: {block_number}"}
    except ImportError:
        return {"status": "degraded", "message": "区块链模块未安装"}
    except Exception as e:
        return {"status": "degraded", "message": f"连接异常: {str(e)[:200]}"}


@router.get("", summary="系统健康检查")
async def health_check():
    """
    系统健康检查端点

    返回数据库、Redis、区块链等各组件的连接状态和系统运行信息。
    """
    db_status = await _check_database()
    redis_status = await _check_redis()
    blockchain_status = await _check_blockchain()

    # 判断整体状态
    statuses = [db_status["status"], redis_status["status"], blockchain_status["status"]]
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    uptime_seconds = round(time.monotonic() - _start_time, 2)

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "blockchain": blockchain_status,
        "uptime": uptime_seconds,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
