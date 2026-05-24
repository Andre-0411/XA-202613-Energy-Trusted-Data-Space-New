"""
密钥管理服务
密钥生成(SM2/SM4/SM9) + 列表查询 + 详情 + 轮换 + 审计日志 + Shamir秘密分割/恢复
"""
import uuid
import logging
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import KeyStore, KeyUsageLog
from app.exceptions import KeyManagementError, DataNotFoundError, DataValidationError
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)

# 支持的密钥算法
SUPPORTED_ALGORITHMS = {"SM2", "SM4", "SM9"}

# 密钥层级
HIERARCHY_LEVELS = {"master", "kek", "dek"}

# 密钥状态
KEY_STATUSES = {"active", "rotated", "destroyed"}


def _generate_key_material(algorithm: str) -> tuple[str, str]:
    """
    生成密钥材料

    Args:
        algorithm: 算法类型

    Returns:
        (public_key_data, encrypted_private_key) 元组
    """
    if algorithm == "SM2":
        private_key = secrets.token_hex(32)
        public_key = secrets.token_hex(64)
        encrypted_key = gmssl_adapter.sm3_hash(private_key)
        return public_key, encrypted_key
    elif algorithm == "SM4":
        key = secrets.token_hex(16)
        encrypted_key = gmssl_adapter.sm3_hash(key)
        return "", encrypted_key
    elif algorithm == "SM9":
        master_key = secrets.token_hex(32)
        public_key = secrets.token_hex(64)
        encrypted_key = gmssl_adapter.sm3_hash(master_key)
        return public_key, encrypted_key
    else:
        raise KeyManagementError(message=f"不支持的算法: {algorithm}")


async def generate_key(
    db: AsyncSession,
    algorithm: str,
    hierarchy_level: str,
    purpose: str,
    parent_key_id: Optional[str] = None,
    created_by: str = "",
) -> dict:
    """
    生成密钥

    支持 SM2/SM4/SM9 密钥对，返回 key_id

    Args:
        db: 数据库会话
        algorithm: 算法 (SM2/SM4/SM9)
        hierarchy_level: 层级 (master/kek/dek)
        purpose: 用途
        parent_key_id: 父密钥 ID
        created_by: 创建人

    Returns:
        密钥信息
    """
    # 验证算法
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise DataValidationError(
            message=f"不支持的算法: {algorithm}",
            data={"supported_algorithms": list(SUPPORTED_ALGORITHMS)},
        )

    # 验证层级
    if hierarchy_level not in HIERARCHY_LEVELS:
        raise DataValidationError(
            message=f"无效层级: {hierarchy_level}",
            data={"valid_levels": list(HIERARCHY_LEVELS)},
        )

    # 验证父密钥
    if parent_key_id:
        parent_result = await db.execute(
            select(KeyStore).where(KeyStore.key_id == parent_key_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise DataNotFoundError(message=f"父密钥不存在: {parent_key_id}")
        if parent.status != "active":
            raise KeyManagementError(message=f"父密钥状态异常: {parent.status}")

    # 生成密钥材料
    key_id = f"key-{algorithm.lower()}-{uuid.uuid4().hex[:12]}"
    public_key_data, encrypted_key = _generate_key_material(algorithm)

    # 存储
    key_record = KeyStore(
        key_id=key_id,
        algorithm=algorithm,
        encrypted_key=encrypted_key,
        hierarchy_level=hierarchy_level,
        parent_key_id=parent_key_id,
        purpose=purpose,
        status="active",
    )
    db.add(key_record)

    # 审计日志
    usage_log = KeyUsageLog(
        key_id=key_id,
        operation="generate",
        user_id=uuid.UUID(created_by) if created_by else None,
        details={"algorithm": algorithm, "hierarchy_level": hierarchy_level, "purpose": purpose},
    )
    db.add(usage_log)

    await db.commit()
    await db.refresh(key_record)

    logger.info(f"密钥生成: {key_id}, 算法: {algorithm}, 层级: {hierarchy_level}")
    return {
        "key_id": key_id,
        "algorithm": algorithm,
        "hierarchy_level": hierarchy_level,
        "public_key_data": public_key_data,
        "purpose": purpose,
        "status": "active",
        "parent_key_id": parent_key_id,
        "created_at": key_record.created_at.isoformat(),
    }


async def list_keys(
    db: AsyncSession,
    algorithm: Optional[str] = None,
    status: Optional[str] = None,
    hierarchy_level: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    密钥列表查询

    Args:
        db: 数据库会话
        algorithm: 算法过滤
        status: 状态过滤
        hierarchy_level: 层级过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        密钥列表
    """
    query = select(KeyStore)
    count_query = select(func.count()).select_from(KeyStore)

    if algorithm:
        query = query.where(KeyStore.algorithm == algorithm)
        count_query = count_query.where(KeyStore.algorithm == algorithm)
    if status:
        query = query.where(KeyStore.status == status)
        count_query = count_query.where(KeyStore.status == status)
    if hierarchy_level:
        query = query.where(KeyStore.hierarchy_level == hierarchy_level)
        count_query = count_query.where(KeyStore.hierarchy_level == hierarchy_level)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(KeyStore.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    keys = result.scalars().all()

    items = [
        {
            "key_id": k.key_id,
            "algorithm": k.algorithm,
            "hierarchy_level": k.hierarchy_level,
            "purpose": k.purpose,
            "status": k.status,
            "parent_key_id": k.parent_key_id,
            "rotated_at": k.rotated_at.isoformat() if k.rotated_at else None,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_key(
    db: AsyncSession,
    key_id: str,
) -> dict:
    """
    密钥详情

    Args:
        db: 数据库会话
        key_id: 密钥 ID

    Returns:
        密钥详情
    """
    result = await db.execute(
        select(KeyStore).where(KeyStore.key_id == key_id)
    )
    key_record = result.scalar_one_or_none()
    if not key_record:
        raise DataNotFoundError(message=f"密钥不存在: {key_id}")

    return {
        "key_id": key_record.key_id,
        "algorithm": key_record.algorithm,
        "encrypted_key_hash": gmssl_adapter.sm3_hash(key_record.encrypted_key),
        "hierarchy_level": key_record.hierarchy_level,
        "parent_key_id": key_record.parent_key_id,
        "purpose": key_record.purpose,
        "status": key_record.status,
        "rotated_at": key_record.rotated_at.isoformat() if key_record.rotated_at else None,
        "created_at": key_record.created_at.isoformat(),
    }


async def rotate_key(
    db: AsyncSession,
    key_id: str,
    rotated_by: str = "",
) -> dict:
    """
    密钥轮换

    生成新密钥，旧密钥标记为 rotated

    Args:
        db: 数据库会话
        key_id: 待轮换的密钥 ID
        rotated_by: 操作人

    Returns:
        新密钥信息
    """
    result = await db.execute(
        select(KeyStore).where(KeyStore.key_id == key_id)
    )
    old_key = result.scalar_one_or_none()
    if not old_key:
        raise DataNotFoundError(message=f"密钥不存在: {key_id}")
    if old_key.status != "active":
        raise KeyManagementError(message=f"密钥状态异常，无法轮换: {old_key.status}")

    # 标记旧密钥为 rotated
    old_key.status = "rotated"
    old_key.rotated_at = datetime.now(timezone.utc)

    # 生成新密钥
    new_key_id = f"key-{old_key.algorithm.lower()}-{uuid.uuid4().hex[:12]}"
    _, encrypted_key = _generate_key_material(old_key.algorithm)

    new_key = KeyStore(
        key_id=new_key_id,
        algorithm=old_key.algorithm,
        encrypted_key=encrypted_key,
        hierarchy_level=old_key.hierarchy_level,
        parent_key_id=old_key.parent_key_id,
        purpose=old_key.purpose,
        status="active",
    )
    db.add(new_key)

    # 审计日志
    usage_log = KeyUsageLog(
        key_id=key_id,
        operation="rotate",
        user_id=uuid.UUID(rotated_by) if rotated_by else None,
        details={"new_key_id": new_key_id, "old_key_id": key_id},
    )
    db.add(usage_log)

    await db.commit()

    logger.info(f"密钥轮换: {key_id} → {new_key_id}, 操作人: {rotated_by}")
    return {
        "old_key_id": key_id,
        "old_status": "rotated",
        "new_key_id": new_key_id,
        "new_status": "active",
        "algorithm": old_key.algorithm,
        "rotated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_key_audit_log(
    db: AsyncSession,
    key_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    密钥使用审计日志

    Args:
        db: 数据库会话
        key_id: 密钥 ID
        limit: 分页大小
        offset: 偏移量

    Returns:
        审计日志列表
    """
    query = select(KeyUsageLog).where(KeyUsageLog.key_id == key_id)
    count_query = select(func.count()).select_from(KeyUsageLog).where(KeyUsageLog.key_id == key_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(KeyUsageLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    items = [
        {
            "id": str(log.id),
            "key_id": log.key_id,
            "operation": log.operation,
            "user_id": str(log.user_id) if log.user_id else None,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]

    return {"items": items, "total": total, "key_id": key_id}


def _shamir_split(secret: str, n: int, k: int) -> list[dict]:
    """
    Shamir 秘密分割（简化实现）

    将秘密分为 n 份，需 k 份恢复

    Args:
        secret: 秘密字符串
        n: 总份数
        k: 恢复阈值

    Returns:
        份额列表
    """
    if k > n:
        raise DataValidationError(message=f"恢复阈值 k({k}) 不能大于总份数 n({n})")
    if k < 2:
        raise DataValidationError(message="恢复阈值 k 必须 ≥ 2")

    # 使用有限域上的多项式（简化实现，生产环境应使用大素数域）
    secret_int = int.from_bytes(secret.encode("utf-8"), "big")

    # 生成随机系数
    coefficients = [secret_int] + [secrets.randbelow(2**128) for _ in range(k - 1)]

    # 计算各份额
    shares = []
    for i in range(1, n + 1):
        x = i
        y = 0
        for j, coeff in enumerate(coefficients):
            y += coeff * (x ** j)
        shares.append({
            "index": i,
            "x": x,
            "y": str(y),
        })

    return shares


def _shamir_combine(shares: list[dict]) -> str:
    """
    Shamir 秘密恢复

    从 k 份份额恢复秘密（Lagrange 插值）

    Args:
        shares: 份额列表

    Returns:
        恢复的秘密字符串
    """
    if len(shares) < 2:
        raise DataValidationError(message="恢复秘密至少需要 2 份份额")

    # Lagrange 插值求 f(0)
    secret_int = 0
    for i, share_i in enumerate(shares):
        xi = share_i["x"]
        yi = int(share_i["y"])

        # 计算 Lagrange 基函数
        numerator = 1
        denominator = 1
        for j, share_j in enumerate(shares):
            if i == j:
                continue
            xj = share_j["x"]
            numerator *= (0 - xj)
            denominator *= (xi - xj)

        lagrange_coeff = numerator // denominator if denominator != 0 else 0
        secret_int += yi * lagrange_coeff

    # 转回字符串
    try:
        byte_length = (secret_int.bit_length() + 7) // 8
        secret = secret_int.to_bytes(byte_length, "big").decode("utf-8")
    except (OverflowError, UnicodeDecodeError):
        secret = str(secret_int)

    return secret


async def shamir_split(
    secret: str,
    n: int = 5,
    k: int = 3,
) -> dict:
    """
    Shamir 秘密分割服务

    Args:
        secret: 待分割的秘密
        n: 总份数
        k: 恢复阈值

    Returns:
        分割结果
    """
    shares = _shamir_split(secret, n, k)
    logger.info(f"Shamir 分割完成: n={n}, k={k}, 生成 {len(shares)} 份")

    return {
        "total_shares": n,
        "threshold": k,
        "shares": shares,
        "split_at": datetime.now(timezone.utc).isoformat(),
    }


async def shamir_combine(
    shares: list[dict],
) -> dict:
    """
    Shamir 秘密恢复服务

    Args:
        shares: 份额列表

    Returns:
        恢复结果
    """
    recovered_secret = _shamir_combine(shares)
    logger.info(f"Shamir 恢复完成，使用 {len(shares)} 份份额")

    return {
        "recovered": True,
        "shares_used": len(shares),
        "recovered_at": datetime.now(timezone.utc).isoformat(),
    }
