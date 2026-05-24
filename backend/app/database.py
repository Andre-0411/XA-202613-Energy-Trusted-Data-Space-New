"""
数据库连接管理
PostgreSQL 异步引擎 + 会话
MongoDB 异步客户端
Redis 连接池 + 异步连接
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    AsyncIOMotorClient = None
    logger.warning("motor (MongoDB driver) not installed - MongoDB features disabled")

from app.config import settings


# ==================== SQLAlchemy Base ====================

class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


# ==================== PostgreSQL ====================

async_engine: AsyncEngine = create_async_engine(
    settings.postgres_url,
    echo=settings.APP_DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取 PostgreSQL 异步会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==================== MongoDB ====================

mongo_client: AsyncIOMotorClient | None = None


def _get_mongo_client():
    """获取 MongoDB 客户端实例"""
    global mongo_client
    if AsyncIOMotorClient is None:
        raise RuntimeError("motor (MongoDB driver) not installed - cannot use MongoDB features")
    if mongo_client is None:
        mongo_client = AsyncIOMotorClient(
            settings.mongo_url,
            maxPoolSize=50,
            minPoolSize=5,
        )
    return mongo_client


async def get_mongo_db():
    """获取 MongoDB 数据库实例"""
    if AsyncIOMotorClient is None:
        return None
    client = _get_mongo_client()
    return client[settings.MONGO_DB]


# ==================== Redis ====================

redis_pool: aioredis.Redis | None = None


def _get_redis_client() -> aioredis.Redis:
    """获取 Redis 客户端实例（带连接池）"""
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry_on_timeout=False,
            health_check_interval=30,
        )
    return redis_pool


async def get_redis() -> aioredis.Redis:
    """获取 Redis 连接"""
    return _get_redis_client()


# ==================== Redis 会话管理 ====================

class RedisSessionManager:
    """Redis 会话管理器"""

    def __init__(self):
        self._client: aioredis.Redis | None = None

    async def get_client(self) -> aioredis.Redis:
        """获取 Redis 客户端"""
        if self._client is None:
            self._client = _get_redis_client()
        return self._client

    async def set_session(
        self,
        session_id: str,
        user_id: int,
        ttl: int = 3600,
    ) -> None:
        """设置用户会话"""
        client = await self.get_client()
        await client.setex(f"session:{session_id}", ttl, str(user_id))

    async def get_session(self, session_id: str) -> str | None:
        """获取用户会话"""
        client = await self.get_client()
        return await client.get(f"session:{session_id}")

    async def delete_session(self, session_id: str) -> None:
        """删除用户会话"""
        client = await self.get_client()
        await client.delete(f"session:{session_id}")

    async def set_cache(
        self,
        key: str,
        value: str,
        ttl: int = 300,
    ) -> None:
        """设置缓存"""
        client = await self.get_client()
        await client.setex(key, ttl, value)

    async def get_cache(self, key: str) -> str | None:
        """获取缓存"""
        client = await self.get_client()
        return await client.get(key)

    async def delete_cache(self, key: str) -> None:
        """删除缓存"""
        client = await self.get_client()
        await client.delete(key)

    async def increment_counter(self, key: str, ttl: int = 3600) -> int:
        """递增计数器"""
        client = await self.get_client()
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, ttl)
        return count


# 全局 Redis 会话管理器
redis_session = RedisSessionManager()


# ==================== 生命周期管理 ====================

async def init_db():
    """初始化所有数据库连接"""
    # 确保所有模型被导入注册到 Base.metadata
    import app.models  # noqa: F401

    # PostgreSQL
    try:
        async with async_engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        logger.info("PostgreSQL connected successfully")
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e} - running in demo mode")

    # MongoDB
    if AsyncIOMotorClient is not None:
        try:
            client = _get_mongo_client()
            await client.admin.command("ping")
            logger.info("MongoDB connected successfully")
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}")
    else:
        logger.info("MongoDB skipped (motor not installed)")

    # Redis
    try:
        r = _get_redis_client()
        await r.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")


async def close_db():
    """关闭所有数据库连接"""
    # PostgreSQL
    await async_engine.dispose()
    logger.info("PostgreSQL connection pool closed")

    # MongoDB
    if mongo_client is not None and AsyncIOMotorClient is not None:
        mongo_client.close()
        logger.info("MongoDB connection closed")

    # Redis
    if redis_pool is not None:
        await redis_pool.close()
        logger.info("Redis connection closed")
