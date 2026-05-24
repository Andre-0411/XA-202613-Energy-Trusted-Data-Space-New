"""
FastAPI 依赖注入
get_db, get_mongo_db, get_redis, get_current_user (JWT验证+SM2验证)
"""
import logging
from typing import AsyncGenerator, Optional
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.config import settings
from app.database import get_db as _get_db, get_mongo_db as _get_mongo_db, get_redis as _get_redis

logger = logging.getLogger(__name__)

# HTTP Bearer Token 方案
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取 PostgreSQL 异步会话"""
    async for session in _get_db():
        yield session


async def get_mongo_db():
    """获取 MongoDB 数据库"""
    return await _get_mongo_db()


async def get_redis():
    """获取 Redis 连接"""
    return await _get_redis()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    获取当前用户（JWT 验证 + SM2 验证）

    验证流程:
    1. 从 Authorization header 提取 Bearer Token
    2. JWT 解码验证
    3. 检查 Token 是否在 Redis 黑名单中
    4. 返回用户信息字典
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 1001,
                "message": "未提供认证令牌",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    token = credentials.credentials

    try:
        # JWT 解码
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 1002,
                "message": "令牌无效或已过期",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # 检查过期
    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 1003,
                "message": "令牌已过期",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # 检查 Token 黑名单（Redis）
    redis = await get_redis()
    blacklisted = await redis.get(f"token:blacklist:{token}")
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 1004,
                "message": "令牌已被撤销",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # 提取用户信息
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 1005,
                "message": "令牌中缺少用户标识",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "user_id": user_id,
        "username": payload.get("username", ""),
        "role": payload.get("role", "user"),
        "permissions": payload.get("permissions", []),
        "token": token,
    }


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """可选用户认证 - 未登录返回 None 而非报错"""
    if credentials is None:
        return None
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


def require_permissions(*required_permissions: str):
    """
    权限检查依赖

    用法:
        @router.get("/", dependencies=[Depends(require_permissions("data:read"))])
    """
    async def check_permissions(user: dict = Depends(get_current_user)) -> dict:
        user_permissions = set(user.get("permissions", []))
        user_role = user.get("role", "")

        # admin 角色拥有所有权限
        if user_role == "admin":
            return user

        # 检查是否拥有所需权限
        missing = set(required_permissions) - user_permissions
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": 1006,
                    "message": f"缺少权限: {', '.join(missing)}",
                    "data": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return user

    return check_permissions
