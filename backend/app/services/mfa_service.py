"""
MFA (多因素认证) 服务
TOTP 密钥管理、验证码生成/验证、备份码管理
使用 PostgreSQL 数据库持久化存储
"""
import uuid
import logging
import hashlib
import hmac
import struct
import time
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.mfa_model import MfaConfig, MfaBackupCode, MfaSession
from app.schemas.mfa import (
    MfaSetupResponse, MfaVerifyResponse, MfaStatusResponse,
    MfaBackupCodesResponse,
)

logger = logging.getLogger(__name__)

# TOTP 配置
TOTP_INTERVAL = 30  # 秒
TOTP_DIGITS = 6
TOTP_ALGORITHM = "SHA1"
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 8


def _generate_secret(length: int = 20) -> str:
    """生成 TOTP 密钥（Base32 编码）"""
    import secrets
    random_bytes = secrets.token_bytes(length)
    return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")


def _generate_otp(secret: str, counter: int, digits: int = TOTP_DIGITS) -> str:
    """生成 HOTP 值"""
    # Base32 解码
    padding = 8 - (len(secret) % 8) if len(secret) % 8 != 0 else 0
    secret_padded = secret + "=" * padding
    key = base64.b32decode(secret_padded)

    # 计数器转字节
    counter_bytes = struct.pack(">Q", counter)

    # HMAC-SHA1
    hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()

    # 动态截断
    offset = hmac_hash[-1] & 0x0F
    truncated = struct.unpack(">I", hmac_hash[offset:offset + 4])[0]
    truncated &= 0x7FFFFFFF

    # 取模得到 OTP
    otp = truncated % (10 ** digits)
    return str(otp).zfill(digits)


def _generate_totp(secret: str, timestamp: Optional[float] = None) -> str:
    """生成 TOTP 值"""
    if timestamp is None:
        timestamp = time.time()
    counter = int(timestamp) // TOTP_INTERVAL
    return _generate_otp(secret, counter)


def _verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """验证 TOTP 值（允许时间窗口偏差）"""
    current_counter = int(time.time()) // TOTP_INTERVAL

    for offset in range(-window, window + 1):
        expected = _generate_otp(secret, current_counter + offset)
        if hmac.compare_digest(expected, code):
            return True
    return False


def _generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> List[str]:
    """生成备份码"""
    import secrets
    codes = []
    for _ in range(count):
        code = secrets.token_hex(BACKUP_CODE_LENGTH // 2).upper()
        # 格式化为 XXXX-XXXX
        formatted = f"{code[:4]}-{code[4:]}"
        codes.append(formatted)
    return codes


def _generate_totp_uri(secret: str, username: str, issuer: str = "EnergyDataSpace") -> str:
    """生成 TOTP URI（用于二维码）"""
    return (
        f"otpauth://totp/{issuer}:{username}"
        f"?secret={secret}&issuer={issuer}&algorithm={TOTP_ALGORITHM}&digits={TOTP_DIGITS}&period={TOTP_INTERVAL}"
    )


def _hash_backup_code(code: str) -> str:
    """对备份码进行哈希处理"""
    return hashlib.sha256(code.encode()).hexdigest()


async def setup_mfa(user_id: str, method: str = "totp") -> MfaSetupResponse:
    """
    设置 MFA

    生成 TOTP 密钥、二维码 URL、备份码。

    Args:
        user_id: 用户 ID
        method: MFA 方法

    Returns:
        MFA 设置响应
    """
    logger.info(f"Setting up MFA for user {user_id}, method={method}")

    async with AsyncSessionLocal() as session:
        # 检查是否已存在 MFA 配置
        result = await session.execute(
            select(MfaConfig).where(MfaConfig.user_id == user_id)
        )
        existing_config = result.scalar_one_or_none()

        # 生成密钥
        secret = _generate_secret()

        # 生成备份码
        backup_codes = _generate_backup_codes()

        # 生成二维码 URL
        qr_code_url = _generate_totp_uri(secret, user_id)

        if existing_config:
            # 更新现有配置
            existing_config.secret = secret
            existing_config.method = method
            existing_config.enabled = False
            existing_config.last_verified_at = None

            # 删除旧的备份码
            await session.execute(
                delete(MfaBackupCode).where(MfaBackupCode.mfa_config_id == existing_config.id)
            )
            mfa_config_id = existing_config.id
        else:
            # 创建新的 MFA 配置
            mfa_config = MfaConfig(
                user_id=user_id,
                secret=secret,
                method=method,
                enabled=False,
            )
            session.add(mfa_config)
            await session.flush()  # 获取生成的 ID
            mfa_config_id = mfa_config.id

        # 存储备份码（哈希存储）
        for code in backup_codes:
            backup_code = MfaBackupCode(
                mfa_config_id=mfa_config_id,
                code_hash=_hash_backup_code(code),
                used=False,
            )
            session.add(backup_code)

        await session.commit()

        return MfaSetupResponse(
            secret=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes,
            method=method,
            created_at=datetime.now(timezone.utc),
        )


async def verify_mfa(user_id: str, code: str, session_id: Optional[str] = None) -> MfaVerifyResponse:
    """
    验证 MFA

    验证用户提供的 TOTP 码或备份码。

    Args:
        user_id: 用户 ID
        code: MFA 验证码
        session_id: MFA 会话 ID

    Returns:
        MFA 验证响应
    """
    logger.info(f"Verifying MFA for user {user_id}")

    async with AsyncSessionLocal() as session:
        # 获取 MFA 配置
        result = await session.execute(
            select(MfaConfig).where(MfaConfig.user_id == user_id)
        )
        mfa_config = result.scalar_one_or_none()

        if not mfa_config:
            return MfaVerifyResponse(
                verified=False,
                session_id=session_id,
                message="MFA 未设置",
            )

        secret = mfa_config.secret

        # 首先尝试 TOTP 验证
        if _verify_totp(secret, code):
            mfa_config.last_verified_at = datetime.now(timezone.utc)

            # 创建或更新会话
            if session_id:
                # 检查会话是否存在
                session_result = await session.execute(
                    select(MfaSession).where(MfaSession.session_id == session_id)
                )
                existing_session = session_result.scalar_one_or_none()

                if existing_session:
                    existing_session.verified = True
                    existing_session.verified_at = datetime.now(timezone.utc)
                    existing_session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
                else:
                    mfa_session = MfaSession(
                        mfa_config_id=mfa_config.id,
                        session_id=session_id,
                        verified=True,
                        verified_at=datetime.now(timezone.utc),
                        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                    )
                    session.add(mfa_session)

            await session.commit()

            return MfaVerifyResponse(
                verified=True,
                session_id=session_id or str(uuid.uuid4()),
                message="MFA 验证成功",
            )

        # 尝试备份码验证
        backup_result = await session.execute(
            select(MfaBackupCode).where(
                MfaBackupCode.mfa_config_id == mfa_config.id,
                MfaBackupCode.used == False,
            )
        )
        backup_codes = backup_result.scalars().all()

        code_hash = _hash_backup_code(code)
        for backup_code in backup_codes:
            if hmac.compare_digest(backup_code.code_hash, code_hash):
                # 使用后标记为已使用
                backup_code.used = True
                backup_code.used_at = datetime.now(timezone.utc)
                mfa_config.last_verified_at = datetime.now(timezone.utc)
                await session.commit()

                return MfaVerifyResponse(
                    verified=True,
                    session_id=session_id or str(uuid.uuid4()),
                    message="备份码验证成功（已消耗）",
                )

        return MfaVerifyResponse(
            verified=False,
            session_id=session_id,
            message="验证码错误",
        )


async def enable_mfa(user_id: str, code: str) -> bool:
    """
    启用 MFA

    需要提供有效的 TOTP 码以确认启用。

    Args:
        user_id: 用户 ID
        code: 验证码

    Returns:
        是否成功启用
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MfaConfig).where(MfaConfig.user_id == user_id)
        )
        mfa_config = result.scalar_one_or_none()

        if not mfa_config:
            return False

        # 验证 TOTP 码
        if not _verify_totp(mfa_config.secret, code):
            return False

        mfa_config.enabled = True
        await session.commit()

        logger.info(f"MFA enabled for user {user_id}")
        return True


async def disable_mfa(user_id: str, password: str, code: Optional[str] = None) -> bool:
    """
    禁用 MFA

    Args:
        user_id: 用户 ID
        password: 用户密码
        code: MFA 验证码（可选）

    Returns:
        是否成功禁用
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MfaConfig).where(MfaConfig.user_id == user_id)
        )
        mfa_config = result.scalar_one_or_none()

        if not mfa_config:
            return False

        # 如果提供了验证码，验证之
        if code:
            if not _verify_totp(mfa_config.secret, code):
                return False

        # 删除 MFA 配置（级联删除备份码和会话）
        await session.delete(mfa_config)
        await session.commit()

        logger.info(f"MFA disabled for user {user_id}")
        return True


async def get_mfa_status(user_id: str) -> MfaStatusResponse:
    """
    获取 MFA 状态

    Args:
        user_id: 用户 ID

    Returns:
        MFA 状态响应
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MfaConfig).where(MfaConfig.user_id == user_id)
        )
        mfa_config = result.scalar_one_or_none()

        if not mfa_config:
            return MfaStatusResponse(
                user_id=user_id,
                enabled=False,
                method=None,
                backup_codes_remaining=0,
                last_verified_at=None,
            )

        # 获取剩余备份码数量
        backup_result = await session.execute(
            select(MfaBackupCode).where(
                MfaBackupCode.mfa_config_id == mfa_config.id,
                MfaBackupCode.used == False,
            )
        )
        backup_count = len(backup_result.scalars().all())

        return MfaStatusResponse(
            user_id=user_id,
            enabled=mfa_config.enabled,
            method=mfa_config.method,
            backup_codes_remaining=backup_count,
            last_verified_at=mfa_config.last_verified_at,
        )


async def regenerate_backup_codes(user_id: str) -> MfaBackupCodesResponse:
    """
    重新生成备份码

    Args:
        user_id: 用户 ID

    Returns:
        新的备份码列表
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MfaConfig).where(MfaConfig.user_id == user_id)
        )
        mfa_config = result.scalar_one_or_none()

        if not mfa_config:
            raise ValueError("MFA 未设置")

        # 删除旧的备份码
        await session.execute(
            delete(MfaBackupCode).where(MfaBackupCode.mfa_config_id == mfa_config.id)
        )

        # 生成新的备份码
        new_codes = _generate_backup_codes()

        # 存储新的备份码
        for code in new_codes:
            backup_code = MfaBackupCode(
                mfa_config_id=mfa_config.id,
                code_hash=_hash_backup_code(code),
                used=False,
            )
            session.add(backup_code)

        await session.commit()

        logger.info(f"Backup codes regenerated for user {user_id}")

        return MfaBackupCodesResponse(
            backup_codes=new_codes,
            regenerated_at=datetime.now(timezone.utc),
        )


async def verify_backup_code(user_id: str, backup_code: str) -> MfaVerifyResponse:
    """
    验证备份码

    Args:
        user_id: 用户 ID
        backup_code: 备份码

    Returns:
        MFA 验证响应
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MfaConfig).where(MfaConfig.user_id == user_id)
        )
        mfa_config = result.scalar_one_or_none()

        if not mfa_config:
            return MfaVerifyResponse(
                verified=False,
                session_id=None,
                message="MFA 未设置",
            )

        # 获取未使用的备份码
        backup_result = await session.execute(
            select(MfaBackupCode).where(
                MfaBackupCode.mfa_config_id == mfa_config.id,
                MfaBackupCode.used == False,
            )
        )
        backup_codes = backup_result.scalars().all()

        code_hash = _hash_backup_code(backup_code)
        for code_record in backup_codes:
            if hmac.compare_digest(code_record.code_hash, code_hash):
                # 使用后标记为已使用
                code_record.used = True
                code_record.used_at = datetime.now(timezone.utc)
                await session.commit()

                return MfaVerifyResponse(
                    verified=True,
                    session_id=str(uuid.uuid4()),
                    message="备份码验证成功（已消耗）",
                )

        return MfaVerifyResponse(
            verified=False,
            session_id=None,
            message="备份码无效",
        )
