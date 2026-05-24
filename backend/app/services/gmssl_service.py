"""
国密算法服务
SM2签名/验签/加密/解密 + SM3哈希 + SM4加密/解密 + SM9签名/验签 + ZUC流加密
所有操作通过 gmssl_adapter 执行
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gmssl_adapter import gmssl_adapter
from app.models.security import KeyStore, KeyUsageLog
from app.exceptions import CryptoError, DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# 支持的算法列表
SUPPORTED_SM2_OPERATIONS = {"sign", "verify", "encrypt", "decrypt"}
SUPPORTED_SM4_OPERATIONS = {"encrypt", "decrypt"}
SUPPORTED_SM9_OPERATIONS = {"sign", "verify"}


async def sm2_sign(
    db: AsyncSession,
    private_key: str,
    public_key: str,
    data: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM2 签名

    Args:
        db: 数据库会话
        private_key: SM2 私钥（十六进制）
        public_key: SM2 公钥（十六进制）
        data: 待签名数据
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        签名结果
    """
    try:
        signature = gmssl_adapter.sm2_sign(private_key, public_key, data)
    except Exception as e:
        logger.error(f"SM2 签名失败: {e}")
        raise CryptoError(message=f"SM2 签名失败: {str(e)}")

    # 记录审计日志
    if key_id:
        await _log_key_usage(db, key_id, "sm2_sign", user_id, {"data_hash": gmssl_adapter.sm3_hash(data)})

    logger.info(f"SM2 签名成功, key_id: {key_id}")
    return {
        "algorithm": "SM2",
        "operation": "sign",
        "signature": signature,
        "data_hash": gmssl_adapter.sm3_hash(data),
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm2_verify(
    db: AsyncSession,
    public_key: str,
    data: str,
    signature: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM2 验签

    Args:
        db: 数据库会话
        public_key: SM2 公钥（十六进制）
        data: 原始数据
        signature: 签名值（十六进制）
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        验签结果
    """
    try:
        is_valid = gmssl_adapter.sm2_verify(public_key, data, signature)
    except Exception as e:
        logger.error(f"SM2 验签失败: {e}")
        raise CryptoError(message=f"SM2 验签失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "sm2_verify", user_id, {"verified": is_valid})

    logger.info(f"SM2 验签结果: {is_valid}, key_id: {key_id}")
    return {
        "algorithm": "SM2",
        "operation": "verify",
        "is_valid": is_valid,
        "data_hash": gmssl_adapter.sm3_hash(data),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm2_encrypt(
    db: AsyncSession,
    public_key: str,
    plaintext: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM2 加密

    Args:
        db: 数据库会话
        public_key: SM2 公钥（十六进制）
        plaintext: 明文
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        加密结果
    """
    try:
        ciphertext = gmssl_adapter.sm2_encrypt(public_key, plaintext)
    except Exception as e:
        logger.error(f"SM2 加密失败: {e}")
        raise CryptoError(message=f"SM2 加密失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "sm2_encrypt", user_id)

    logger.info(f"SM2 加密成功, key_id: {key_id}")
    return {
        "algorithm": "SM2",
        "operation": "encrypt",
        "ciphertext": ciphertext,
        "encrypted_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm2_decrypt(
    db: AsyncSession,
    private_key: str,
    public_key: str,
    ciphertext: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM2 解密

    Args:
        db: 数据库会话
        private_key: SM2 私钥（十六进制）
        public_key: SM2 公钥（十六进制）
        ciphertext: 密文
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        解密结果
    """
    try:
        plaintext = gmssl_adapter.sm2_decrypt(private_key, public_key, ciphertext)
    except Exception as e:
        logger.error(f"SM2 解密失败: {e}")
        raise CryptoError(message=f"SM2 解密失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "sm2_decrypt", user_id)

    logger.info(f"SM2 解密成功, key_id: {key_id}")
    return {
        "algorithm": "SM2",
        "operation": "decrypt",
        "plaintext": plaintext,
        "decrypted_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm3_hash(
    data: str,
) -> dict:
    """
    SM3 哈希

    Args:
        data: 待哈希数据

    Returns:
        哈希结果
    """
    try:
        hash_value = gmssl_adapter.sm3_hash(data)
    except Exception as e:
        logger.error(f"SM3 哈希失败: {e}")
        raise CryptoError(message=f"SM3 哈希失败: {str(e)}")

    return {
        "algorithm": "SM3",
        "operation": "hash",
        "hash": hash_value,
        "hashed_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm4_encrypt(
    db: AsyncSession,
    key: str,
    plaintext: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM4 加密

    Args:
        db: 数据库会话
        key: SM4 密钥（十六进制，32字符=16字节）
        plaintext: 明文
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        加密结果
    """
    if len(key) != 32:
        raise DataValidationError(message="SM4 密钥必须为32个十六进制字符（16字节）")

    try:
        ciphertext = gmssl_adapter.sm4_encrypt(key, plaintext)
    except Exception as e:
        logger.error(f"SM4 加密失败: {e}")
        raise CryptoError(message=f"SM4 加密失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "sm4_encrypt", user_id)

    logger.info(f"SM4 加密成功, key_id: {key_id}")
    return {
        "algorithm": "SM4",
        "operation": "encrypt",
        "ciphertext": ciphertext,
        "encrypted_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm4_decrypt(
    db: AsyncSession,
    key: str,
    ciphertext: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM4 解密

    Args:
        db: 数据库会话
        key: SM4 密钥（十六进制）
        ciphertext: 密文
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        解密结果
    """
    if len(key) != 32:
        raise DataValidationError(message="SM4 密钥必须为32个十六进制字符（16字节）")

    try:
        plaintext = gmssl_adapter.sm4_decrypt(key, ciphertext)
    except Exception as e:
        logger.error(f"SM4 解密失败: {e}")
        raise CryptoError(message=f"SM4 解密失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "sm4_decrypt", user_id)

    logger.info(f"SM4 解密成功, key_id: {key_id}")
    return {
        "algorithm": "SM4",
        "operation": "decrypt",
        "plaintext": plaintext,
        "decrypted_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm9_sign(
    db: AsyncSession,
    master_private_key: str,
    data: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM9 签名

    Args:
        db: 数据库会话
        master_private_key: SM9 主私钥
        data: 待签名数据
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        签名结果
    """
    try:
        signature = gmssl_adapter.sm9_sign(master_private_key, data)
    except Exception as e:
        logger.error(f"SM9 签名失败: {e}")
        raise CryptoError(message=f"SM9 签名失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "sm9_sign", user_id)

    logger.info(f"SM9 签名成功, key_id: {key_id}")
    return {
        "algorithm": "SM9",
        "operation": "sign",
        "signature": signature,
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }


async def sm9_verify(
    db: AsyncSession,
    master_public_key: str,
    data: str,
    signature: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    SM9 验签

    Args:
        db: 数据库会话
        master_public_key: SM9 主公钥
        data: 原始数据
        signature: 签名值
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        验签结果
    """
    try:
        is_valid = gmssl_adapter.sm9_verify(master_public_key, data, signature)
    except Exception as e:
        logger.error(f"SM9 验签失败: {e}")
        raise CryptoError(message=f"SM9 验签失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "sm9_verify", user_id, {"verified": is_valid})

    logger.info(f"SM9 验签结果: {is_valid}, key_id: {key_id}")
    return {
        "algorithm": "SM9",
        "operation": "verify",
        "is_valid": is_valid,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


async def zuc_encrypt(
    db: AsyncSession,
    key: str,
    iv: str,
    plaintext: str,
    key_id: Optional[str] = None,
    user_id: str = "",
) -> dict:
    """
    ZUC 流密码加密

    Args:
        db: 数据库会话
        key: ZUC 密钥（十六进制）
        iv: 初始化向量（十六进制）
        plaintext: 明文
        key_id: 关联密钥 ID
        user_id: 操作用户

    Returns:
        加密结果
    """
    try:
        ciphertext = gmssl_adapter.zuc_encrypt(key, iv, plaintext)
    except Exception as e:
        logger.error(f"ZUC 加密失败: {e}")
        raise CryptoError(message=f"ZUC 加密失败: {str(e)}")

    if key_id:
        await _log_key_usage(db, key_id, "zuc_encrypt", user_id)

    logger.info(f"ZUC 加密成功, key_id: {key_id}")
    return {
        "algorithm": "ZUC",
        "operation": "encrypt",
        "ciphertext": ciphertext,
        "iv": iv,
        "encrypted_at": datetime.now(timezone.utc).isoformat(),
    }


async def _log_key_usage(
    db: AsyncSession,
    key_id: str,
    operation: str,
    user_id: str = "",
    details: Optional[dict] = None,
) -> None:
    """记录密钥使用审计日志"""
    log_entry = KeyUsageLog(
        key_id=key_id,
        operation=operation,
        user_id=uuid.UUID(user_id) if user_id else None,
        details=details or {},
    )
    db.add(log_entry)
    await db.commit()
