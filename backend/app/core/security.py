"""
安全工具模块
JWT 签发验证 / SM3 密码哈希 / CSRF / 权限校验
"""
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError

from app.config import settings
from app.utils.crypto import sm3_hash


def create_access_token(
    subject: str,
    username: str = "",
    role: str = "user",
    permissions: Optional[list[str]] = None,
    expires_delta: Optional[timedelta] = None,
    organization_id: Optional[str] = None,
) -> str:
    """
    签发 JWT Access Token

    Args:
        subject: 用户 ID
        username: 用户名
        role: 角色
        permissions: 权限列表
        expires_delta: 自定义过期时间

    Returns:
        JWT Token 字符串
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    jti = str(uuid.uuid4())

    payload = {
        "sub": subject,
        "username": username,
        "role": role,
        "permissions": permissions or [],
        "organization_id": organization_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "access",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    签发 JWT Refresh Token

    Args:
        subject: 用户 ID
        expires_delta: 自定义过期时间

    Returns:
        JWT Refresh Token 字符串
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.now(timezone.utc) + expires_delta
    jti = str(uuid.uuid4())

    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "refresh",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    解码验证 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        Token payload 字典

    Raises:
        JWTError: Token 无效或过期
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    使用 SM3 哈希密码

    Args:
        password: 明文密码
        salt: 盐值（如未提供则自动生成）

    Returns:
        格式: salt$hash
    """
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = sm3_hash(salt + password)
    return f"{salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    验证密码

    Args:
        password: 明文密码
        stored_hash: 存储的哈希（格式: salt$hash）

    Returns:
        密码是否匹配
    """
    try:
        salt, hashed = stored_hash.split("$", 1)
        computed = sm3_hash(salt + password)
        return secrets.compare_digest(computed, hashed)
    except (ValueError, AttributeError):
        return False


def generate_csrf_token() -> str:
    """生成 CSRF Token"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    """验证 CSRF Token"""
    return secrets.compare_digest(token, expected)


def check_permission(
    user_role: str,
    user_permissions: list[str],
    required_permissions: list[str],
) -> bool:
    """
    检查用户是否拥有所需权限

    Args:
        user_role: 用户角色
        user_permissions: 用户权限列表
        required_permissions: 所需权限列表

    Returns:
        是否有权限
    """
    if user_role == "admin":
        return True

    user_perm_set = set(user_permissions)
    required_perm_set = set(required_permissions)

    return bool(required_perm_set & user_perm_set)
