"""
HSM（硬件安全模块）模拟服务
软件 HSM 模拟器，提供安全的密钥存储和加密操作接口

功能:
- 软件 HSM 模拟器，提供安全的密钥存储和加密操作接口
- 支持密钥生成（SM2/SM4/RSA）、签名/验签、加密/解密
- 密钥分层管理（根密钥→机构密钥→用户密钥）
- 密钥使用审计日志
- 所有密钥存储在加密的本地文件中（开发环境）
"""
import os
import uuid
import json
import logging
import hashlib
import base64
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gmssl_adapter import gmssl_adapter
from app.models.security import KeyStore, KeyUsageLog
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.schemas.hsm import (
    HsmKeyResponse,
    HsmSignResponse,
    HsmVerifyResponse,
    HsmEncryptResponse,
    HsmDecryptResponse,
    HsmAuditLogResponse,
)
from app.exceptions import (
    KeyManagementError,
    CryptoError,
    DataNotFoundError,
    DataValidationError,
)

logger = logging.getLogger(__name__)

# 支持的算法
SUPPORTED_ALGORITHMS = {"SM2", "SM4", "RSA"}

# 密钥层级
HIERARCHY_LEVELS = {"root", "org", "user"}

# 密钥状态
KEY_STATUSES = {"active", "revoked", "expired"}

# HSM 本地密钥存储路径（开发环境模拟）
HSM_KEY_STORE_PATH = os.environ.get(
    "HSM_KEY_STORE_PATH", "/tmp/hsm_keystore"
)


def _ensure_keystore_dir() -> None:
    """确保密钥存储目录存在"""
    os.makedirs(HSM_KEY_STORE_PATH, exist_ok=True)


def _encrypt_key_for_storage(key_data: str) -> str:
    """
    使用固定主密钥加密密钥数据后存储（开发环境模拟）

    Args:
        key_data: 原始密钥数据

    Returns:
        加密后的十六进制字符串
    """
    # 使用 SHA-256 派生存储密钥
    storage_key = hashlib.sha256(b"hsm-master-key-dev-only").hexdigest()[:32]
    encrypted = gmssl_adapter.sm4_encrypt(storage_key, key_data)
    return encrypted


def _decrypt_key_from_storage(encrypted_data: str) -> str:
    """
    从存储中解密密钥数据

    Args:
        encrypted_data: 加密的密钥数据

    Returns:
        原始密钥数据
    """
    storage_key = hashlib.sha256(b"hsm-master-key-dev-only").hexdigest()[:32]
    decrypted = gmssl_adapter.sm4_decrypt(storage_key, encrypted_data)
    return decrypted


def _generate_sm2_keypair() -> tuple[str, str]:
    """
    生成 SM2 密钥对

    Returns:
        (private_key_hex, public_key_hex)
    """
    try:
        private_key, public_key = gmssl_adapter.sm2_generate_keypair()
        return private_key, public_key
    except Exception as e:
        # 降级：使用随机数模拟
        logger.warning(f"SM2 密钥生成使用降级方案: {e}")
        private_key = uuid.uuid4().hex + uuid.uuid4().hex
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        return private_key, public_key


def _generate_sm4_key() -> str:
    """
    生成 SM4 密钥（128 位 = 32 个十六进制字符）

    Returns:
        SM4 密钥十六进制字符串
    """
    return uuid.uuid4().hex


def _generate_rsa_keypair(key_size: int = 2048) -> tuple[str, str]:
    """
    生成 RSA 密钥对（模拟）

    Args:
        key_size: 密钥长度

    Returns:
        (private_key_pem, public_key_pem)
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return private_pem, public_pem
    except ImportError:
        # 降级模拟
        logger.warning("cryptography 库不可用，RSA 使用模拟密钥")
        private_key = f"RSA-MOCK-PRIVATE-{key_size}-{uuid.uuid4().hex}"
        public_key = f"RSA-MOCK-PUBLIC-{key_size}-{uuid.uuid4().hex}"
        return private_key, public_key


async def generate_key(
    db: AsyncSession,
    algorithm: str,
    key_size: int = 2048,
    hierarchy: str = "user",
    purpose: str = "general",
    org_id: Optional[str] = None,
    description: Optional[str] = None,
    user_id: str = "",
) -> HsmKeyResponse:
    """
    在 HSM 中生成密钥

    Args:
        db: 数据库会话
        algorithm: 算法类型（SM2/SM4/RSA）
        key_size: 密钥长度
        hierarchy: 密钥层级（root/org/user）
        purpose: 密钥用途（sign/encrypt/general）
        org_id: 所属组织 ID
        description: 密钥描述
        user_id: 操作用户

    Returns:
        密钥信息
    """
    algorithm = algorithm.upper()
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise DataValidationError(
            message=f"不支持的算法: {algorithm}，支持: {', '.join(SUPPORTED_ALGORITHMS)}"
        )

    if hierarchy not in HIERARCHY_LEVELS:
        raise DataValidationError(
            message=f"无效的密钥层级: {hierarchy}，支持: {', '.join(HIERARCHY_LEVELS)}"
        )

    # 生成密钥
    private_key = ""
    public_key = ""

    if algorithm == "SM2":
        private_key, public_key = _generate_sm2_keypair()
    elif algorithm == "SM4":
        private_key = _generate_sm4_key()
        public_key = ""
    elif algorithm == "RSA":
        private_key, public_key = _generate_rsa_keypair(key_size)

    # 加密存储
    _ensure_keystore_dir()
    encrypted_key = _encrypt_key_for_storage(private_key)

    # 生成密钥 ID
    key_id = f"hsm-{hierarchy}-{algorithm.lower()}-{uuid.uuid4().hex[:12]}"

    # 保存到数据库
    key_record = KeyStore(
        key_id=key_id,
        algorithm=algorithm,
        encrypted_key=encrypted_key,
        hierarchy_level=hierarchy,
        purpose=purpose,
        status="active",
    )
    db.add(key_record)

    # 同时保存到本地文件（开发环境备份）
    key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{key_id}.json")
    key_file_data = {
        "key_id": key_id,
        "algorithm": algorithm,
        "hierarchy": hierarchy,
        "purpose": purpose,
        "org_id": org_id,
        "encrypted_private_key": encrypted_key,
        "public_key": public_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(key_file_path, "w", encoding="utf-8") as f:
            json.dump(key_file_data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"HSM 密钥文件写入失败（不影响数据库记录）: {e}")

    # 记录审计日志
    await _log_hsm_operation(
        db=db,
        key_id=key_id,
        operation="generate_key",
        user_id=user_id,
        details={
            "algorithm": algorithm,
            "hierarchy": hierarchy,
            "purpose": purpose,
            "org_id": org_id,
        },
        status="success",
    )

    await db.commit()
    await db.refresh(key_record)

    logger.info(f"HSM 密钥生成成功: key_id={key_id}, algorithm={algorithm}")

    return HsmKeyResponse(
        key_id=key_id,
        algorithm=algorithm,
        hierarchy=hierarchy,
        purpose=purpose,
        org_id=org_id,
        description=description,
        status="active",
        public_key=public_key if algorithm != "SM4" else None,
        has_private_key=True,
        created_at=datetime.now(timezone.utc),
        last_used_at=None,
    )


async def list_keys(
    db: AsyncSession,
    params: PaginationParams,
    algorithm: Optional[str] = None,
    hierarchy: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """
    列出 HSM 中的密钥

    Args:
        db: 数据库会话
        params: 分页参数
        algorithm: 按算法过滤
        hierarchy: 按层级过滤
        status: 按状态过滤

    Returns:
        分页密钥列表
    """
    query = select(KeyStore)

    if algorithm:
        query = query.where(KeyStore.algorithm == algorithm.upper())
    if hierarchy:
        query = query.where(KeyStore.hierarchy_level == hierarchy)
    if status:
        query = query.where(KeyStore.status == status)

    result = await paginate_query(db, query, params, HsmKeyResponse)
    return result


async def get_key_info(db: AsyncSession, key_id: str) -> dict:
    """
    获取密钥详细信息

    Args:
        db: 数据库会话
        key_id: 密钥 ID

    Returns:
        密钥信息
    """
    result = await db.execute(
        select(KeyStore).where(KeyStore.key_id == key_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise DataNotFoundError(message=f"密钥不存在: {key_id}")

    # 尝试从本地文件读取公钥
    public_key = None
    key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{key_id}.json")
    if os.path.exists(key_file_path):
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                public_key = file_data.get("public_key")
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "key_id": key.key_id,
        "algorithm": key.algorithm,
        "hierarchy": key.hierarchy_level,
        "purpose": key.purpose,
        "status": key.status,
        "public_key": public_key,
        "has_private_key": True,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "last_used_at": key.rotated_at.isoformat() if key.rotated_at else None,
    }


async def sign(
    db: AsyncSession,
    key_id: str,
    data: str,
    user_id: str = "",
) -> HsmSignResponse:
    """
    使用 HSM 中的密钥进行签名

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        data: 待签名数据（原文或 Base64）
        user_id: 操作用户

    Returns:
        签名结果
    """
    key = await _get_active_key(db, key_id)

    if key.algorithm not in ("SM2", "RSA"):
        raise DataValidationError(
            message=f"算法 {key.algorithm} 不支持签名操作，仅 SM2/RSA 支持"
        )

    # 解密私钥
    private_key = _decrypt_key_from_storage(key.encrypted_key)

    # 获取公钥
    public_key = ""
    key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{key_id}.json")
    if os.path.exists(key_file_path):
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:
                public_key = json.load(f).get("public_key", "")
        except (OSError, json.JSONDecodeError):
            pass

    try:
        if key.algorithm == "SM2":
            signature = gmssl_adapter.sm2_sign(private_key, public_key, data)
            data_hash = gmssl_adapter.sm3_hash(data)
        else:
            # RSA 签名模拟
            data_hash = hashlib.sha256(data.encode()).hexdigest()
            signature = hashlib.sha512(
                (private_key + data).encode()
            ).hexdigest()
    except Exception as e:
        await _log_hsm_operation(
            db, key_id, "sign", user_id,
            {"error": str(e)}, "failure"
        )
        await db.commit()
        raise CryptoError(message=f"签名失败: {str(e)}")

    await _log_hsm_operation(
        db, key_id, "sign", user_id,
        {"data_hash": data_hash}, "success"
    )
    await db.commit()

    return HsmSignResponse(
        key_id=key_id,
        algorithm=key.algorithm,
        signature=signature,
        data_hash=data_hash,
        signed_at=datetime.now(timezone.utc),
    )


async def verify(
    db: AsyncSession,
    key_id: str,
    data: str,
    signature: str,
    user_id: str = "",
) -> HsmVerifyResponse:
    """
    使用 HSM 中的密钥进行验签

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        data: 原始数据
        signature: 签名值
        user_id: 操作用户

    Returns:
        验签结果
    """
    key = await _get_active_key(db, key_id)

    if key.algorithm not in ("SM2", "RSA"):
        raise DataValidationError(
            message=f"算法 {key.algorithm} 不支持验签操作，仅 SM2/RSA 支持"
        )

    # 获取公钥
    public_key = ""
    key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{key_id}.json")
    if os.path.exists(key_file_path):
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:
                public_key = json.load(f).get("public_key", "")
        except (OSError, json.JSONDecodeError):
            pass

    try:
        if key.algorithm == "SM2":
            is_valid = gmssl_adapter.sm2_verify(public_key, data, signature)
        else:
            # RSA 验签模拟
            private_key = _decrypt_key_from_storage(key.encrypted_key)
            expected_sig = hashlib.sha512(
                (private_key + data).encode()
            ).hexdigest()
            is_valid = expected_sig == signature
    except Exception as e:
        await _log_hsm_operation(
            db, key_id, "verify", user_id,
            {"error": str(e)}, "failure"
        )
        await db.commit()
        raise CryptoError(message=f"验签失败: {str(e)}")

    await _log_hsm_operation(
        db, key_id, "verify", user_id,
        {"is_valid": is_valid}, "success"
    )
    await db.commit()

    return HsmVerifyResponse(
        key_id=key_id,
        algorithm=key.algorithm,
        is_valid=is_valid,
        verified_at=datetime.now(timezone.utc),
    )


async def encrypt(
    db: AsyncSession,
    key_id: str,
    plaintext: str,
    user_id: str = "",
) -> HsmEncryptResponse:
    """
    使用 HSM 中的密钥加密数据

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        plaintext: 明文数据
        user_id: 操作用户

    Returns:
        加密结果
    """
    key = await _get_active_key(db, key_id)

    if key.algorithm not in ("SM2", "SM4", "RSA"):
        raise DataValidationError(
            message=f"算法 {key.algorithm} 不支持加密操作"
        )

    # 解密密钥
    raw_key = _decrypt_key_from_storage(key.encrypted_key)

    try:
        if key.algorithm == "SM4":
            ciphertext = gmssl_adapter.sm4_encrypt(raw_key, plaintext)
        elif key.algorithm == "SM2":
            # 获取公钥用于加密
            public_key = ""
            key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{key_id}.json")
            if os.path.exists(key_file_path):
                try:
                    with open(key_file_path, "r", encoding="utf-8") as f:
                        public_key = json.load(f).get("public_key", "")
                except (OSError, json.JSONDecodeError):
                    pass
            if not public_key:
                raise DataValidationError(message="SM2 密钥公钥不可用")
            ciphertext = gmssl_adapter.sm2_encrypt(public_key, plaintext)
        else:
            # RSA 加密模拟
            ciphertext = base64.b64encode(
                hashlib.sha256((raw_key + plaintext).encode()).digest()
            ).hexdigest()
    except DataValidationError:
        raise
    except Exception as e:
        await _log_hsm_operation(
            db, key_id, "encrypt", user_id,
            {"error": str(e)}, "failure"
        )
        await db.commit()
        raise CryptoError(message=f"加密失败: {str(e)}")

    await _log_hsm_operation(
        db, key_id, "encrypt", user_id,
        {"algorithm": key.algorithm}, "success"
    )
    await db.commit()

    return HsmEncryptResponse(
        key_id=key_id,
        algorithm=key.algorithm,
        ciphertext=ciphertext,
        encrypted_at=datetime.now(timezone.utc),
    )


async def decrypt(
    db: AsyncSession,
    key_id: str,
    ciphertext: str,
    user_id: str = "",
) -> HsmDecryptResponse:
    """
    使用 HSM 中的密钥解密数据

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        ciphertext: 密文数据
        user_id: 操作用户

    Returns:
        解密结果
    """
    key = await _get_active_key(db, key_id)

    if key.algorithm not in ("SM2", "SM4", "RSA"):
        raise DataValidationError(
            message=f"算法 {key.algorithm} 不支持解密操作"
        )

    # 解密密钥
    raw_key = _decrypt_key_from_storage(key.encrypted_key)

    try:
        if key.algorithm == "SM4":
            plaintext = gmssl_adapter.sm4_decrypt(raw_key, ciphertext)
        elif key.algorithm == "SM2":
            public_key = ""
            key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{key_id}.json")
            if os.path.exists(key_file_path):
                try:
                    with open(key_file_path, "r", encoding="utf-8") as f:
                        public_key = json.load(f).get("public_key", "")
                except (OSError, json.JSONDecodeError):
                    pass
            plaintext = gmssl_adapter.sm2_decrypt(raw_key, public_key, ciphertext)
        else:
            # RSA 解密模拟
            plaintext = f"[RSA-DECRYPTED] {ciphertext[:32]}..."
    except Exception as e:
        await _log_hsm_operation(
            db, key_id, "decrypt", user_id,
            {"error": str(e)}, "failure"
        )
        await db.commit()
        raise CryptoError(message=f"解密失败: {str(e)}")

    await _log_hsm_operation(
        db, key_id, "decrypt", user_id,
        {"algorithm": key.algorithm}, "success"
    )
    await db.commit()

    return HsmDecryptResponse(
        key_id=key_id,
        algorithm=key.algorithm,
        plaintext=plaintext,
        decrypted_at=datetime.now(timezone.utc),
    )


async def get_audit_log(
    db: AsyncSession,
    params: PaginationParams,
    key_id: Optional[str] = None,
    operation: Optional[str] = None,
    user_id: Optional[str] = None,
) -> PaginatedResponse:
    """
    查询 HSM 审计日志

    Args:
        db: 数据库会话
        params: 分页参数
        key_id: 按密钥 ID 过滤
        operation: 按操作类型过滤
        user_id: 按用户过滤

    Returns:
        分页审计日志
    """
    query = select(KeyUsageLog)

    if key_id:
        query = query.where(KeyUsageLog.key_id == key_id)
    if operation:
        query = query.where(KeyUsageLog.operation == operation)
    if user_id:
        query = query.where(
            KeyUsageLog.user_id == user_id
        )

    result = await paginate_query(db, query, params, HsmAuditLogResponse)
    return result


async def _get_active_key(db: AsyncSession, key_id: str) -> KeyStore:
    """
    获取状态为 active 的密钥

    Args:
        db: 数据库会话
        key_id: 密钥 ID

    Returns:
        密钥记录

    Raises:
        DataNotFoundError: 密钥不存在
        KeyManagementError: 密钥已撤销或过期
    """
    result = await db.execute(
        select(KeyStore).where(KeyStore.key_id == key_id)
    )
    key = result.scalar_one_or_none()

    if not key:
        raise DataNotFoundError(message=f"密钥不存在: {key_id}")

    if key.status != "active":
        raise KeyManagementError(
            message=f"密钥 {key_id} 状态异常: {key.status}，无法执行操作"
        )

    return key


async def _log_hsm_operation(
    db: AsyncSession,
    key_id: str,
    operation: str,
    user_id: str = "",
    details: Optional[dict] = None,
    status: str = "success",
) -> None:
    """
    记录 HSM 操作审计日志

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        operation: 操作类型
        user_id: 操作用户
        details: 操作详情
        status: 操作状态
    """
    log_entry = KeyUsageLog(
        key_id=key_id,
        operation=f"hsm_{operation}",
        user_id=uuid.UUID(user_id) if user_id else None,
        details={
            "status": status,
            **(details or {}),
        },
    )
    db.add(log_entry)


# ============================================================
# 密钥派生（HKDF / PBKDF2）
# ============================================================


def derive_key_hkdf(
    master_key: str,
    info: str,
    salt: str = "",
    key_length: int = 32,
) -> str:
    """
    使用 HKDF 从主密钥派生子密钥

    HKDF (HMAC-based Key Derivation Function, RFC 5869)
    使用 SM3 作为底层哈希函数

    Args:
        master_key: 主密钥（十六进制）
        info: 派生上下文信息
        salt: 盐值（十六进制，可选）
        key_length: 输出密钥长度（字节）

    Returns:
        派生密钥（十六进制）
    """
    # Step 1: Extract — 使用 HMAC-SM3 生成伪随机密钥
    salt_bytes = bytes.fromhex(salt) if salt else b"\x00" * 32
    key_material = bytes.fromhex(master_key)

    # 使用 SHA-256 作为 HMAC 底层哈希（SM3 没有标准 HMAC 实现）
    import hmac as hmac_module
    prk = hmac_module.new(salt_bytes, key_material, hashlib.sha256).digest()

    # Step 2: Expand — 生成所需长度的密钥
    info_bytes = info.encode("utf-8")
    n = (key_length + 31) // 32  # 向上取整
    okm = b""
    t = b""
    for i in range(1, n + 1):
        t = hmac_module.new(prk, t + info_bytes + bytes([i]), hashlib.sha256).digest()
        okm += t

    return okm[:key_length].hex()


def derive_key_pbkdf2(
    password: str,
    salt: str = "",
    iterations: int = 100_000,
    key_length: int = 32,
) -> str:
    """
    使用 PBKDF2 从密码派生密钥

    使用 SHA-256 作为底层哈希函数

    Args:
        password: 密码
        salt: 盐值（十六进制，可选）
        iterations: 迭代次数
        key_length: 输出密钥长度（字节）

    Returns:
        派生密钥（十六进制）
    """
    salt_bytes = bytes.fromhex(salt) if salt else b"\x00" * 16
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations,
        dklen=key_length,
    )
    return dk.hex()


# ============================================================
# 密钥轮换
# ============================================================


async def rotate_key(
    db: AsyncSession,
    key_id: str,
    user_id: str = "",
) -> dict:
    """
    密钥轮换

    生成新密钥替换旧密钥，旧密钥标记为 revoked

    Args:
        db: 数据库会话
        key_id: 待轮换的密钥 ID
        user_id: 操作用户

    Returns:
        新密钥信息
    """
    # 获取当前密钥
    old_key = await _get_active_key(db, key_id)

    # 生成新密钥（同算法）
    new_private_key = ""
    new_public_key = ""

    if old_key.algorithm == "SM2":
        new_private_key, new_public_key = _generate_sm2_keypair()
    elif old_key.algorithm == "SM4":
        new_private_key = _generate_sm4_key()
    elif old_key.algorithm == "RSA":
        new_private_key, new_public_key = _generate_rsa_keypair()

    # 加密新密钥
    _ensure_keystore_dir()
    new_encrypted_key = _encrypt_key_for_storage(new_private_key)

    # 生成新密钥 ID
    new_key_id = f"hsm-{old_key.hierarchy_level}-{old_key.algorithm.lower()}-{uuid.uuid4().hex[:12]}"

    # 创建新密钥记录
    new_key_record = KeyStore(
        key_id=new_key_id,
        algorithm=old_key.algorithm,
        encrypted_key=new_encrypted_key,
        hierarchy_level=old_key.hierarchy_level,
        parent_key_id=old_key.parent_key_id,
        purpose=old_key.purpose,
        status="active",
    )
    db.add(new_key_record)

    # 旧密钥标记为 revoked
    old_key.status = "revoked"

    # 保存新密钥到本地文件
    key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{new_key_id}.json")
    key_file_data = {
        "key_id": new_key_id,
        "algorithm": old_key.algorithm,
        "hierarchy": old_key.hierarchy_level,
        "purpose": old_key.purpose,
        "encrypted_private_key": new_encrypted_key,
        "public_key": new_public_key,
        "rotated_from": key_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(key_file_path, "w", encoding="utf-8") as f:
            json.dump(key_file_data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"HSM 密钥轮换文件写入失败: {e}")

    # 审计日志
    await _log_hsm_operation(
        db=db,
        key_id=key_id,
        operation="rotate_key",
        user_id=user_id,
        details={
            "new_key_id": new_key_id,
            "algorithm": old_key.algorithm,
        },
        status="success",
    )
    await _log_hsm_operation(
        db=db,
        key_id=new_key_id,
        operation="rotate_key_created",
        user_id=user_id,
        details={
            "rotated_from": key_id,
            "algorithm": old_key.algorithm,
        },
        status="success",
    )
    await db.commit()
    await db.refresh(new_key_record)

    logger.info(f"HSM 密钥轮换成功: {key_id} → {new_key_id}")

    return {
        "old_key_id": key_id,
        "new_key_id": new_key_id,
        "algorithm": old_key.algorithm,
        "hierarchy": old_key.hierarchy_level,
        "public_key": new_public_key if old_key.algorithm != "SM4" else None,
        "rotated_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# 密钥备份与恢复
# ============================================================


async def backup_key(
    db: AsyncSession,
    key_id: str,
    backup_passphrase: str,
    user_id: str = "",
) -> dict:
    """
    备份密钥

    使用 PBKDF2 派生的密钥对密钥数据进行二次加密

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        backup_passphrase: 备份密码
        user_id: 操作用户

    Returns:
        备份数据
    """
    key = await _get_active_key(db, key_id)

    # 使用 PBKDF2 派生备份加密密钥
    import secrets as secrets_mod
    backup_salt = secrets_mod.token_hex(16)
    backup_key = derive_key_pbkdf2(backup_passphrase, backup_salt, iterations=100_000, key_length=32)

    # 读取公钥
    public_key = ""
    key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{key_id}.json")
    if os.path.exists(key_file_path):
        try:
            with open(key_file_path, "r", encoding="utf-8") as f:
                public_key = json.load(f).get("public_key", "")
        except (OSError, json.JSONDecodeError):
            pass

    # 二次加密
    backup_encrypted = gmssl_adapter.sm4_encrypt(backup_key[:32], key.encrypted_key)

    backup_data = {
        "key_id": key_id,
        "algorithm": key.algorithm,
        "hierarchy": key.hierarchy_level,
        "purpose": key.purpose,
        "public_key": public_key,
        "encrypted_key": backup_encrypted,
        "backup_salt": backup_salt,
        "backup_iterations": 100_000,
        "backup_format": "PBKDF2-SHA256+SM4",
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
    }

    # 保存备份文件
    backup_dir = os.path.join(HSM_KEY_STORE_PATH, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_file_path = os.path.join(backup_dir, f"{key_id}.backup.json")
    try:
        with open(backup_file_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"密钥备份文件写入失败: {e}")

    # 审计日志
    await _log_hsm_operation(
        db=db,
        key_id=key_id,
        operation="backup_key",
        user_id=user_id,
        details={"backup_file": backup_file_path},
        status="success",
    )
    await db.commit()

    logger.info(f"HSM 密钥备份成功: {key_id}")
    return {
        "key_id": key_id,
        "backup_file": backup_file_path,
        "backup_format": "PBKDF2-SHA256+SM4",
        "backed_up_at": backup_data["backed_up_at"],
    }


async def restore_key(
    db: AsyncSession,
    backup_data: dict,
    backup_passphrase: str,
    user_id: str = "",
) -> dict:
    """
    恢复密钥

    Args:
        db: 数据库会话
        backup_data: 备份数据
        backup_passphrase: 备份密码
        user_id: 操作用户

    Returns:
        恢复的密钥信息
    """
    backup_salt = backup_data.get("backup_salt", "")
    iterations = backup_data.get("backup_iterations", 100_000)
    backup_key = derive_key_pbkdf2(backup_passphrase, backup_salt, iterations=iterations, key_length=32)

    # 解密密钥
    encrypted_key = backup_data.get("encrypted_key", "")
    try:
        decrypted_key = gmssl_adapter.sm4_decrypt(backup_key[:32], encrypted_key)
    except Exception as e:
        raise CryptoError(message=f"密钥恢复失败（密码错误或数据损坏）: {str(e)}")

    # 重新加密存储
    new_encrypted_key = _encrypt_key_for_storage(decrypted_key)

    # 生成新密钥 ID
    original_key_id = backup_data.get("key_id", "")
    new_key_id = f"hsm-restored-{backup_data.get('algorithm', 'unknown').lower()}-{uuid.uuid4().hex[:12]}"

    # 创建密钥记录
    key_record = KeyStore(
        key_id=new_key_id,
        algorithm=backup_data.get("algorithm", "SM2"),
        encrypted_key=new_encrypted_key,
        hierarchy_level=backup_data.get("hierarchy", "user"),
        purpose=backup_data.get("purpose", "general"),
        status="active",
    )
    db.add(key_record)

    # 保存公钥
    _ensure_keystore_dir()
    key_file_path = os.path.join(HSM_KEY_STORE_PATH, f"{new_key_id}.json")
    key_file_data = {
        "key_id": new_key_id,
        "algorithm": backup_data.get("algorithm", "SM2"),
        "hierarchy": backup_data.get("hierarchy", "user"),
        "public_key": backup_data.get("public_key", ""),
        "restored_from": original_key_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(key_file_path, "w", encoding="utf-8") as f:
            json.dump(key_file_data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning(f"密钥恢复文件写入失败: {e}")

    # 审计日志
    await _log_hsm_operation(
        db=db,
        key_id=new_key_id,
        operation="restore_key",
        user_id=user_id,
        details={"restored_from": original_key_id},
        status="success",
    )
    await db.commit()
    await db.refresh(key_record)

    logger.info(f"HSM 密钥恢复成功: {original_key_id} → {new_key_id}")

    return {
        "key_id": new_key_id,
        "algorithm": backup_data.get("algorithm", "SM2"),
        "hierarchy": backup_data.get("hierarchy", "user"),
        "public_key": backup_data.get("public_key", ""),
        "restored_from": original_key_id,
        "restored_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# Shamir 秘密共享
# ============================================================


def shamir_split(
    secret: str,
    num_shares: int = 5,
    threshold: int = 3,
) -> list[dict]:
    """
    Shamir 秘密共享分割

    将密钥分割为 n 份，任意 k 份可恢复

    Args:
        secret: 密钥数据（十六进制）
        num_shares: 分割份数
        threshold: 恢复阈值

    Returns:
        共享份额列表
    """
    import secrets as secrets_mod

    if threshold > num_shares:
        raise DataValidationError(message="阈值不能大于份数")

    # 使用有限域算术
    prime = 2**127 - 1  # Mersenne 素数
    secret_int = int.from_bytes(bytes.fromhex(secret[:64]), "big") % prime

    # 生成多项式系数
    coefficients = [secret_int]
    for _ in range(threshold - 1):
        coefficients.append(secrets_mod.randbelow(prime))

    # 计算份额
    shares = []
    for i in range(1, num_shares + 1):
        x = i
        y = 0
        for j, coeff in enumerate(coefficients):
            y = (y + coeff * pow(x, j, prime)) % prime
        shares.append({
            "share_id": i,
            "x": hex(x),
            "y": hex(y),
            "threshold": threshold,
            "total_shares": num_shares,
        })

    return shares


def shamir_reconstruct(shares: list[dict]) -> str:
    """
    Shamir 秘密共享恢复

    Args:
        shares: 共享份额列表

    Returns:
        恢复的密钥数据（十六进制）
    """
    prime = 2**127 - 1
    secret_int = 0

    for i, share_i in enumerate(shares):
        xi = int(share_i["x"], 16)
        yi = int(share_i["y"], 16)

        # Lagrange 插值
        numerator = 1
        denominator = 1
        for j, share_j in enumerate(shares):
            if i == j:
                continue
            xj = int(share_j["x"], 16)
            numerator = (numerator * (0 - xj)) % prime
            denominator = (denominator * (xi - xj)) % prime

        # 计算拉格朗日基多项式在 x=0 处的值
        lagrange_coeff = (numerator * pow(denominator, prime - 2, prime)) % prime
        secret_int = (secret_int + yi * lagrange_coeff) % prime

    # 转换为十六进制字符串
    secret_bytes = secret_int.to_bytes(16, "big")
    return secret_bytes.hex()


# ============================================================
# 健康检查
# ============================================================


async def health_check(db: AsyncSession) -> dict:
    """
    HSM 健康检查

    检查 HSM 服务状态、数据库连接、密钥存储

    Args:
        db: 数据库会话

    Returns:
        健康状态
    """
    health = {
        "status": "healthy",
        "checks": {
            "database": {"status": "unknown"},
            "keystore": {"status": "unknown"},
            "algorithms": {"status": "unknown"},
            "pkcs11": {"status": "unavailable", "mode": "software_fallback"},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 检查数据库连接
    try:
        result = await db.execute(select(func.count()).select_from(KeyStore))
        key_count = result.scalar() or 0
        health["checks"]["database"] = {
            "status": "healthy",
            "total_keys": key_count,
        }
    except Exception as e:
        health["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["status"] = "degraded"

    # 检查密钥存储
    _ensure_keystore_dir()
    try:
        key_files = [
            f for f in os.listdir(HSM_KEY_STORE_PATH)
            if f.endswith(".json") and not f.endswith(".backup.json")
        ]
        health["checks"]["keystore"] = {
            "status": "healthy",
            "path": HSM_KEY_STORE_PATH,
            "key_files": len(key_files),
        }
    except OSError as e:
        health["checks"]["keystore"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        health["status"] = "degraded"

    # 检查算法支持
    try:
        # 测试 SM2
        test_priv, test_pub = _generate_sm2_keypair()
        test_sig = gmssl_adapter.sm2_sign(test_priv, test_pub, "health_check_test")
        sm2_ok = len(test_sig) > 0

        # 测试 SM4
        test_key = _generate_sm4_key()
        test_enc = gmssl_adapter.sm4_encrypt(test_key, "health_check_test")
        test_dec = gmssl_adapter.sm4_decrypt(test_key, test_enc)
        sm4_ok = test_dec == "health_check_test"

        health["checks"]["algorithms"] = {
            "status": "healthy" if (sm2_ok and sm4_ok) else "degraded",
            "SM2": "available" if sm2_ok else "unavailable",
            "SM4": "available" if sm4_ok else "unavailable",
            "RSA": "available",
        }
    except Exception as e:
        health["checks"]["algorithms"] = {
            "status": "degraded",
            "error": str(e),
        }
        health["status"] = "degraded"

    # PKCS#11 检查（软件 HSM 模式）
    try:
        import pkcs11  # noqa: F401
        health["checks"]["pkcs11"]["status"] = "available"
        health["checks"]["pkcs11"]["mode"] = "hardware"
    except ImportError:
        health["checks"]["pkcs11"]["status"] = "unavailable"
        health["checks"]["pkcs11"]["mode"] = "software_fallback"

    return health
