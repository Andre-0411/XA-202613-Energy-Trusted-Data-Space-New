"""
测试配置和夹具
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, INET, ARRAY

from app.models.base import Base


# ============ SQLite 兼容: 让 PostgreSQL 专有类型能在 SQLite 中渲染 DDL ============

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"

@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(50)"

@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "TEXT"


# 使用 SQLite 内存数据库进行测试（异步兼容）
# StaticPool 确保所有连接共享同一个内存数据库
TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """会话级夹具：创建所有测试表（只执行一次）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def app_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    创建应用级别的测试数据库会话，并自动 patch AsyncSessionLocal。
    用于集成测试中需要调用真实 service 函数的场景。
    """
    session = TestSessionLocal()
    with patch("app.database.AsyncSessionLocal", return_value=_async_context_manager(session)):
        yield session
    await session.close()


class _async_context_manager:
    """辅助类：让普通 session 可以作为 async context manager 使用"""
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.fixture
def sample_user_id() -> str:
    """示例用户 ID"""
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_device_did() -> str:
    """示例设备 DID"""
    return f"device_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_websocket():
    """模拟 WebSocket 连接"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_sm2_keypair():
    """示例 SM2 密钥对（回退模式）"""
    from app.services.gmssl_real import SM2Engine
    engine = SM2Engine()
    private_key, public_key = engine.generate_keypair()
    return {"private_key": private_key, "public_key": public_key}


@pytest.fixture
def sample_fate_job_config():
    """示例 FATE 任务配置"""
    return {
        "dag_name": "test_energy_federated",
        "component_list": ["reader_0", "homo_lr_0"],
        "role": {
            "guest": [9999],
            "host": [10000],
        },
    }


@pytest.fixture
def mock_redis():
    """模拟 Redis 客户端"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    redis.ping = AsyncMock(return_value=True)
    return redis
