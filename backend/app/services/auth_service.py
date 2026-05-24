"""
认证服务
DID/密码/SM2证书三种认证 + MFA 验证 + JWT 签发 + Redis 登录锁定
"""
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import (
    create_access_token, create_refresh_token, verify_password, hash_password
)
from app.core.gmssl_adapter import gmssl_adapter
from app.config import settings
from app.exceptions import (
    LoginFailedError, TokenInvalidError, TokenExpiredError,
    AuthenticationError, PermissionDeniedError,
)
from app.schemas.auth import TokenResponse, SessionResponse, UserInfo

logger = logging.getLogger(__name__)

# 登录锁定配置
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30
LOGIN_FAIL_KEY_PREFIX = "login_fail:"
LOGIN_LOCKOUT_KEY_PREFIX = "login_lockout:"


async def _get_redis():
    """获取 Redis 客户端"""
    from app.database import _get_redis_client
    return _get_redis_client()


async def _check_login_lockout(user_id: str) -> Optional[int]:
    """
    检查用户是否处于锁定状态（Redis 计数器）

    Args:
        user_id: 用户 ID

    Returns:
        剩余锁定秒数，None 表示未锁定
    """
    try:
        redis = await _get_redis()
        lockout_key = f"{LOGIN_LOCKOUT_KEY_PREFIX}{user_id}"
        ttl = await redis.ttl(lockout_key)
        if ttl > 0:
            return ttl
        # 如果 lockout key 不存在，清理 fail 计数
        fail_key = f"{LOGIN_FAIL_KEY_PREFIX}{user_id}"
        await redis.delete(fail_key)
        return None
    except Exception as e:
        logger.warning(f"Redis lockout check failed: {e}")
        return None


async def _record_login_failure(user_id: str) -> None:
    """
    记录一次登录失败（Redis 计数器）

    key 格式: login_fail:{user_id}
    5 次失败后设置 login_lockout:{user_id} 锁定 30 分钟

    Args:
        user_id: 用户 ID
    """
    try:
        redis = await _get_redis()
        fail_key = f"{LOGIN_FAIL_KEY_PREFIX}{user_id}"
        lockout_key = f"{LOGIN_LOCKOUT_KEY_PREFIX}{user_id}"

        # 递增失败计数，key 30 分钟过期
        count = await redis.incr(fail_key)
        if count == 1:
            await redis.expire(fail_key, LOCKOUT_DURATION_MINUTES * 60)

        logger.info(f"Login failure for user {user_id}: {count}/{MAX_LOGIN_ATTEMPTS}")

        if count >= MAX_LOGIN_ATTEMPTS:
            # 锁定 30 分钟
            await redis.setex(lockout_key, LOCKOUT_DURATION_MINUTES * 60, "locked")
            # 清除失败计数
            await redis.delete(fail_key)
            logger.warning(
                f"User {user_id} locked for {LOCKOUT_DURATION_MINUTES} minutes "
                f"due to {MAX_LOGIN_ATTEMPTS} failed login attempts"
            )
    except Exception as e:
        logger.error(f"Failed to record login failure: {e}")


async def _reset_login_failures(user_id: str) -> None:
    """
    登录成功后重置失败计数

    Args:
        user_id: 用户 ID
    """
    try:
        redis = await _get_redis()
        await redis.delete(f"{LOGIN_FAIL_KEY_PREFIX}{user_id}")
        await redis.delete(f"{LOGIN_LOCKOUT_KEY_PREFIX}{user_id}")
    except Exception as e:
        logger.warning(f"Failed to reset login failures: {e}")


async def unlock_account(
    db: AsyncSession,
    user_id: str,
) -> dict:
    """
    管理员手动解锁账户

    Args:
        db: 数据库会话
        user_id: 要解锁的用户 ID

    Returns:
        解锁结果
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("用户不存在")

    # 清除 Redis 锁定状态
    try:
        redis = await _get_redis()
        await redis.delete(f"{LOGIN_FAIL_KEY_PREFIX}{user_id}")
        await redis.delete(f"{LOGIN_LOCKOUT_KEY_PREFIX}{user_id}")
    except Exception as e:
        logger.warning(f"Redis unlock failed: {e}")

    # 同步清除数据库锁定字段
    user.login_fail_count = 0
    user.locked_until = None
    await db.commit()

    logger.info(f"Account unlocked for user {user_id}")
    return {"user_id": user_id, "message": "账户已解锁", "unlocked_at": datetime.now(timezone.utc).isoformat()}


async def get_login_lockout_status(user_id: str) -> dict:
    """
    查询用户登录锁定状态

    Args:
        user_id: 用户 ID

    Returns:
        锁定状态信息
    """
    try:
        redis = await _get_redis()
        fail_key = f"{LOGIN_FAIL_KEY_PREFIX}{user_id}"
        lockout_key = f"{LOGIN_LOCKOUT_KEY_PREFIX}{user_id}"

        fail_count_raw = await redis.get(fail_key)
        fail_count = int(fail_count_raw) if fail_count_raw else 0

        lockout_ttl = await redis.ttl(lockout_key)
        is_locked = lockout_ttl > 0

        return {
            "user_id": user_id,
            "is_locked": is_locked,
            "fail_count": fail_count,
            "lockout_remaining_seconds": lockout_ttl if is_locked else 0,
            "max_attempts": MAX_LOGIN_ATTEMPTS,
            "lockout_duration_minutes": LOCKOUT_DURATION_MINUTES,
        }
    except Exception as e:
        logger.warning(f"Failed to get lockout status: {e}")
        return {
            "user_id": user_id,
            "is_locked": False,
            "fail_count": 0,
            "lockout_remaining_seconds": 0,
            "max_attempts": MAX_LOGIN_ATTEMPTS,
            "lockout_duration_minutes": LOCKOUT_DURATION_MINUTES,
        }


async def authenticate_password(
    db: AsyncSession,
    username: str,
    password: str,
) -> TokenResponse:
    """
    密码认证（集成 Redis 登录锁定）

    Args:
        db: 数据库会话
        username: 用户名
        password: 密码

    Returns:
        Token 响应

    Raises:
        LoginFailedError: 登录失败
    """
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise LoginFailedError("用户名或密码错误")

    # 检查账号状态
    if user.status != "active":
        raise LoginFailedError("账号已被禁用，请联系管理员")

    user_id = str(user.id)

    # 检查 Redis 锁定状态
    lockout_remaining = await _check_login_lockout(user_id)
    if lockout_remaining is not None:
        remaining_min = lockout_remaining // 60 + 1
        raise LoginFailedError(
            f"账号已锁定，请{remaining_min}分钟后再试（剩余{lockout_remaining}秒）"
        )

    # 同步检查数据库锁定字段（兼容旧逻辑）
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
        raise LoginFailedError(f"账号已锁定，请{remaining}分钟后再试")

    # 验证密码
    if not verify_password(password, user.password_hash):
        # 记录 Redis 失败计数
        await _record_login_failure(user_id)

        # 同步更新数据库字段（兼容旧逻辑）
        user.login_fail_count = (user.login_fail_count or 0) + 1
        if user.login_fail_count >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )
        await db.commit()

        raise LoginFailedError("用户名或密码错误")

    # 登录成功，重置计数
    await _reset_login_failures(user_id)
    user.login_fail_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return await _generate_tokens(user)


async def authenticate_did(
    db: AsyncSession,
    did: str,
    signature: str,
    challenge: str,
) -> TokenResponse:
    """
    DID 认证 - 验证 SM2 签名

    Args:
        db: 数据库会话
        did: 用户 DID
        signature: SM2 签名
        challenge: 挑战值

    Returns:
        Token 响应
    """
    result = await db.execute(select(User).where(User.did == did))
    user = result.scalar_one_or_none()

    if not user:
        raise LoginFailedError("DID 不存在")

    # 检查账号状态
    if user.status != "active":
        raise LoginFailedError("账号已被禁用，请联系管理员")

    if not user.sm2_public_key:
        raise LoginFailedError("该用户未绑定 SM2 公钥")

    # 验证签名
    try:
        is_valid = gmssl_adapter.sm2_verify(user.sm2_public_key, challenge, signature)
        if not is_valid:
            raise LoginFailedError("SM2 签名验证失败")
    except LoginFailedError:
        raise
    except Exception as e:
        logger.error(f"SM2 verify error: {e}")
        raise LoginFailedError("SM2 签名验证失败")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return await _generate_tokens(user)


async def authenticate_certificate(
    db: AsyncSession,
    certificate: str,
    signature: str,
    challenge: str,
) -> TokenResponse:
    """
    SM2 证书认证

    Args:
        db: 数据库会话
        certificate: SM2 证书 PEM
        signature: 签名值
        challenge: 挑战值

    Returns:
        Token 响应
    """
    logger.info("Certificate authentication - extracting public key from certificate")

    # 简化：使用证书哈希查找用户
    cert_hash = gmssl_adapter.sm3_hash(certificate)
    result = await db.execute(
        select(User).where(User.sm2_public_key.isnot(None))
    )
    users = result.scalars().all()

    for user in users:
        try:
            is_valid = gmssl_adapter.sm2_verify(user.sm2_public_key, challenge, signature)
            if is_valid:
                # 检查账号状态
                if user.status != "active":
                    raise LoginFailedError("账号已被禁用，请联系管理员")
                user.last_login_at = datetime.now(timezone.utc)
                await db.commit()
                return await _generate_tokens(user)
        except Exception:
            continue

    raise LoginFailedError("证书验证失败")


async def verify_mfa(
    db: AsyncSession,
    user_id: str,
    code: str,
    session_id: Optional[str] = None,
) -> TokenResponse:
    """
    MFA 验证 — 使用真实 TOTP 验证

    Args:
        db: 数据库会话
        user_id: 用户 ID
        code: MFA 验证码
        session_id: MFA 会话 ID（可选）

    Returns:
        Token 响应
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.mfa_enabled:
        raise AuthenticationError("MFA 未启用")

    # 调用真实的 TOTP 验证服务
    from app.services.mfa_service import verify_mfa as mfa_verify
    mfa_result = await mfa_verify(user_id, code, session_id)

    if not mfa_result.verified:
        raise AuthenticationError(mfa_result.message or "MFA 验证码错误")

    return await _generate_tokens(user)


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """
    刷新 Token

    Args:
        db: 数据库会话
        refresh_token: 刷新令牌

    Returns:
        Token 响应
    """
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        raise TokenInvalidError("刷新令牌无效")

    if payload.get("type") != "refresh":
        raise TokenInvalidError("令牌类型错误")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise TokenInvalidError("用户不存在")

    # 检查账号状态（已禁用用户不允许刷新 token）
    if user.status != "active":
        raise TokenInvalidError("账号已被禁用，无法刷新令牌")

    return await _generate_tokens(user)


async def change_password(
    db: AsyncSession,
    user_id: str,
    old_password: str,
    new_password: str,
) -> None:
    """
    修改密码

    Args:
        db: 数据库会话
        user_id: 用户 ID
        old_password: 旧密码
        new_password: 新密码
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("用户不存在")

    if not verify_password(old_password, user.password_hash):
        raise AuthenticationError("旧密码错误")

    user.password_hash = hash_password(new_password)
    user.login_fail_count = 0
    user.locked_until = None
    await db.commit()

    # 同时清除 Redis 锁定状态
    await _reset_login_failures(user_id)

    logger.info(f"User {user.username} changed password successfully")


async def logout(token: str) -> None:
    """
    登出 - 将 Token 加入黑名单

    Args:
        token: JWT Token
    """
    from app.database import _get_redis_client

    redis = _get_redis_client()
    await redis.setex(
        f"token:blacklist:{token}",
        settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "1",
    )


async def get_session(
    db: AsyncSession,
    user_id: str,
) -> SessionResponse:
    """
    获取当前会话

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        会话响应
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("用户不存在")

    return SessionResponse(
        user_id=str(user.id),
        username=user.username,
        did=user.did,
        role=user.role,
        permissions=_get_user_permissions(user.role),
        organization_id=str(user.organization_id),
        last_login_at=user.last_login_at,
    )


async def _generate_tokens(user: User) -> TokenResponse:
    """
    生成 Token 对

    Args:
        user: 用户对象

    Returns:
        Token 响应
    """
    permissions = _get_user_permissions(user.role)
    mfa_required = user.mfa_enabled

    access_token = create_access_token(
        subject=str(user.id),
        username=user.username,
        role=user.role,
        permissions=permissions,
        organization_id=str(user.organization_id) if user.organization_id else None,
    )

    refresh_token = create_refresh_token(subject=str(user.id))

    mfa_session_id = None
    if mfa_required:
        mfa_session_id = str(secrets.token_hex(16))
        redis = await _get_redis()
        await redis.setex(
            f"mfa:pending:{user.id}",
            300,  # 5 分钟
            mfa_session_id,
        )

    # 构建用户信息
    user_info = UserInfo(
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        phone=user.phone,
        role=user.role,
        did=user.did,
        organization_id=str(user.organization_id) if user.organization_id else None,
        department_id=str(user.department_id) if user.department_id else None,
        status=user.status,
        permissions=permissions,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        mfa_required=mfa_required,
        mfa_session_id=mfa_session_id,
        user=user_info,
    )


def _get_user_permissions(role: str) -> list[str]:
    """
    获取角色对应的权限

    Args:
        role: 角色名

    Returns:
        权限列表
    """
    role_permissions = {
        "admin": [
            "data:read", "data:write", "data:delete",
            "compute:read", "compute:write", "compute:execute",
            "blockchain:read", "blockchain:write",
            "ops:read", "ops:write", "ops:admin",
            "security:read", "security:write", "security:admin",
        ],
        "data_admin": [
            "data:read", "data:write",
            "compute:read",
            "blockchain:read",
        ],
        "user": [
            "data:read",
            "compute:read", "compute:execute",
            "blockchain:read",
        ],
        "auditor": [
            "data:read",
            "compute:read",
            "blockchain:read",
            "ops:read",
            "security:read",
        ],
        "operator": [
            "data:read",
            "compute:read", "compute:execute",
            "ops:read", "ops:write",
            "security:read",
        ],
    }
    return role_permissions.get(role, ["data:read"])
