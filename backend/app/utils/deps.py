"""
依赖注入工具
get_db / get_current_user / require_permissions / require_roles / get_pagination_params
"""
import logging
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.config import settings
from app.database import get_db as _get_db, get_redis as _get_redis
from app.utils.pagination import PaginationParams, get_pagination_params

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

__all__ = [
    "get_db", "get_redis", "get_current_user",
    "require_permissions", "require_roles",
    "PaginationParams", "get_pagination_params",
]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取 PostgreSQL 异步会话"""
    async for session in _get_db():
        yield session


async def get_redis():
    """获取 Redis 连接"""
    return await _get_redis()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    获取当前用户

    Returns:
        用户信息字典: {user_id, username, role, permissions, token}
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 1001, "message": "未提供认证令牌"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 1002, "message": "令牌无效或已过期"},
        )

    # 检查黑名单（Redis 不可用时跳过）
    try:
        redis = await get_redis()
        blacklisted = await redis.get(f"token:blacklist:{token}")
        if blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": 1004, "message": "令牌已被撤销"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.debug(f"Redis 不可用，跳过黑名单检查: {e}")

    return {
        "user_id": payload.get("sub", ""),
        "username": payload.get("username", ""),
        "role": payload.get("role", "user"),
        "permissions": payload.get("permissions", []),
        "token": token,
    }


def require_permissions(*required_permissions: str):
    """权限检查依赖"""
    async def check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") == "admin":
            return user
        user_perms = set(user.get("permissions", []))
        missing = set(required_permissions) - user_perms
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 1006, "message": f"缺少权限: {', '.join(missing)}"},
            )
        return user
    return check


def require_roles(*required_roles: str):
    """角色检查依赖"""
    async def check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in required_roles and user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": 1006, "message": f"需要角色: {', '.join(required_roles)}"},
            )
        return user
    return check
