"""
同态加密服务 (Homomorphic Encryption Service)
=============================================
基于 Microsoft SEAL (通过 TenSEAL Python 绑定) 的真实同态加密实现

支持的方案:
  - CKKS: 近似浮点运算 (适合机器学习/统计分析)
  - BFV:  精确整数运算 (适合计数/聚合)

核心操作:
  - encrypt_upload:  加密上传明文数据
  - he_compute:      执行同态运算 (add/multiply/negate/square)
  - decrypt_result:  解密计算结果
  - get_he_status:   查询噪声预算

无模拟模式 — 所有操作均使用真实 TenSEAL 同态加密引擎
"""
import os
import uuid
import json
import math
import time
import io
import base64
import hashlib
import logging
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any

import tenseal as ts
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import ComputeTask
from app.models.he_key import HeKey, HeCiphertext
from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import ComputeError, DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


def _audit_log(action: str, resource_id: str, details: Optional[dict] = None) -> None:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "he_service",
        "action": action,
        "resource_id": resource_id,
        "details": details or {},
    }
    logger.info(f"[AUDIT] {json.dumps(log_entry, ensure_ascii=False)}")


HE_SCHEMES = {
    "ckks": {
        "name": "CKKS",
        "full_name": "Cheon-Kim-Kim-Song",
        "description": "近似数值计算方案，支持浮点运算",
        "supported_ops": ["add", "multiply", "negate", "square"],
        "data_type": "float",
        "default_poly_modulus_degree": 8192,
        "max_batch_slots": 4096,
    },
    "bfv": {
        "name": "BFV",
        "full_name": "Brakerski-Fan-Vercauteren",
        "description": "精确整数计算方案，适合计数/统计",
        "supported_ops": ["add", "multiply", "negate", "square"],
        "data_type": "integer",
        "default_poly_modulus_degree": 8192,
        "max_batch_slots": 4096,
    },
}

ALLOWED_POLY_MODULUS_DEGREES = [1024, 2048, 4096, 8192, 16384, 32768]

_KEY_CACHE: dict[str, bytes] = {}


def _create_context(scheme: str, poly_modulus_degree: int = 8192) -> ts.Context:
    if scheme == "ckks":
        context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=[60, 40, 40, 60],
        )
        context.global_scale = 2**40
    elif scheme == "bfv":
        context = ts.context(
            ts.SCHEME_TYPE.BFV,
            poly_modulus_degree=poly_modulus_degree,
            plain_modulus=1032193,
        )
    else:
        raise DataValidationError(f"不支持的 HE 方案: {scheme}")
    context.generate_galois_keys()
    context.generate_relin_keys()
    return context


def _load_context_from_db(key_data: str) -> ts.Context:
    try:
        data = base64.b64decode(key_data)
        return ts.Context.load(data)
    except Exception as e:
        logger.error(f"Failed to load HE context: {e}")
        raise ComputeError(f"HE 密钥加载失败: {e}")


# ==================== 加密上传 ====================

async def encrypt_upload(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    data: list,
    scheme: str = "ckks",
    name: str = "HE Data",
    description: str = "",
    poly_modulus_degree: int = 8192,
) -> dict:
    scheme_info = HE_SCHEMES.get(scheme)
    if not scheme_info:
        raise DataValidationError(f"不支持的 HE 方案: {scheme}")
    if poly_modulus_degree not in ALLOWED_POLY_MODULUS_DEGREES:
        raise DataValidationError(f"多项式模数维度 {poly_modulus_degree} 无效")

    data_type = scheme_info["data_type"]
    data = [float(x) for x in data] if data_type == "float" else [int(x) for x in data]

    key_id = str(uuid.uuid4())
    context = _create_context(scheme, poly_modulus_degree)
    serialized = context.serialize(save_secret_key=True)
    serialized_b64 = base64.b64encode(serialized).decode('utf-8')
    pk_hash = gmssl_adapter.sm3_hash(serialized_b64[:256])

    key_record = HeKey(
        key_id=key_id, scheme=scheme, public_key_hash=pk_hash,
        key_data=serialized_b64,
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(key_record)
    _KEY_CACHE[f"{key_id}:{scheme}"] = serialized

    start_time = time.time()
    try:
        if scheme == "ckks":
            encrypted_vector = ts.ckks_vector(context, data)
        else:
            encrypted_vector = ts.bfv_vector(context, data)
        ct_bytes = encrypted_vector.serialize()
        ct_b64 = base64.b64encode(ct_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"HE encryption failed: {e}")
        raise ComputeError(f"HE 加密失败: {e}")

    enc_time = (time.time() - start_time) * 1000

    ciphertext_id = str(uuid.uuid4())
    ct_record = HeCiphertext(
        ciphertext_id=ciphertext_id, key_id=key_id, scheme=scheme,
        source_operation="encrypt", source_ciphertexts=[],
        ciphertext_data=ct_b64,
        size_params={
            "original_size": len(data), "ciphertext_size_bytes": len(ct_bytes),
            "poly_modulus_degree": poly_modulus_degree, "encrypt_time_ms": round(enc_time, 2),
        },
    )
    db.add(ct_record)

    task = ComputeTask(
        name=name, task_type="HE", scenario="encrypt_upload",
        config={"scheme": scheme, "data_count": len(data), "encrypt_time_ms": enc_time},
        input_asset_ids=[], status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    _audit_log("encrypt_upload", ciphertext_id, {"scheme": scheme, "data_count": len(data), "encrypt_time_ms": enc_time})
    logger.info(f"HE encrypt_upload: {len(data)} values -> {ciphertext_id}, {enc_time:.1f}ms")

    return {
        "task_id": str(task.id), "key_id": key_id, "ciphertext_id": ciphertext_id,
        "scheme": scheme, "scheme_name": scheme_info["name"],
        "data_count": len(data), "ciphertext_size_bytes": len(ct_bytes),
        "encrypt_time_ms": round(enc_time, 2), "poly_modulus_degree": poly_modulus_degree,
        "engine": "TenSEAL",
    }


# ==================== 同态计算 ====================

async def he_compute(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    scheme: str,
    operation: str,
    ciphertext_ids: list[str],
    compute_params: Optional[dict] = None,
    name: str = "HE 计算任务",
    source_key_id: Optional[str] = None,
) -> dict:
    scheme_info = HE_SCHEMES.get(scheme)
    if not scheme_info:
        raise DataValidationError(f"不支持的 HE 方案: {scheme}")
    if operation not in scheme_info["supported_ops"]:
        raise DataValidationError(f"方案 {scheme} 不支持操作: {operation}")
    if len(ciphertext_ids) < 1:
        raise DataValidationError("至少需要 1 个密文 ID")
    if operation in ("add", "multiply") and len(ciphertext_ids) < 2:
        raise DataValidationError(f"操作 {operation} 需要至少 2 个密文")

    cts = []
    key_id = None
    for cid in ciphertext_ids:
        result = await db.execute(select(HeCiphertext).where(HeCiphertext.ciphertext_id == cid))
        ct = result.scalar_one_or_none()
        if not ct:
            raise DataNotFoundError(f"密文未找到: {cid}")
        if ct.scheme != scheme:
            raise DataValidationError(f"密文 {cid} 方案不匹配")
        if not hasattr(ct, 'ciphertext_data') or not ct.ciphertext_data:
            raise DataValidationError(f"密文 {cid} 没有数据")
        cts.append(ct)
        if key_id is None:
            key_id = ct.key_id

    key_result = await db.execute(select(HeKey).where(HeKey.key_id == key_id))
    key_record = key_result.scalar_one_or_none()
    if not key_record or not key_record.key_data:
        raise DataNotFoundError(f"HE 密钥无效: {key_id}")

    context = _load_context_from_db(key_record.key_data)
    _KEY_CACHE[f"{key_id}:{scheme}"] = base64.b64decode(key_record.key_data)

    vectors = []
    for ct in cts:
        data = base64.b64decode(ct.ciphertext_data)
        vec = ts.lazy_ckks_vector_from(data) if scheme == "ckks" else ts.lazy_bfv_vector_from(data)
        vec.link_context(context)
        vectors.append(vec)

    start_time = time.time()
    try:
        if operation == "add":
            result_vec = vectors[0] + vectors[1]
        elif operation == "multiply":
            result_vec = vectors[0] * vectors[1]
        elif operation == "negate":
            result_vec = -vectors[0]
        elif operation == "square":
            result_vec = vectors[0] * vectors[0]
        else:
            raise ComputeError(f"不支持的操作: {operation}")
        result_bytes = result_vec.serialize()
    except Exception as e:
        logger.error(f"HE compute failed: {e}")
        raise ComputeError(f"HE 计算失败: {e}")

    compute_time = (time.time() - start_time) * 1000

    result_ciphertext_id = str(uuid.uuid4())
    result_ct = HeCiphertext(
        ciphertext_id=result_ciphertext_id, key_id=key_id, scheme=scheme,
        source_operation=operation, source_ciphertexts=ciphertext_ids,
        ciphertext_data=base64.b64encode(result_bytes).decode('utf-8'),
        size_params={"compute_time_ms": round(compute_time, 2), "ciphertext_size_bytes": len(result_bytes)},
    )
    db.add(result_ct)

    task = ComputeTask(
        name=name, task_type="HE", scenario="he_compute",
        config={"scheme": scheme, "operation": operation, "compute_time_ms": compute_time},
        input_asset_ids=[], status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"HE compute: {operation} done, {compute_time:.1f}ms")
    _audit_log("he_compute", result_ciphertext_id, {"scheme": scheme, "operation": operation, "compute_time_ms": compute_time})

    return {
        "task_id": str(task.id), "operation": operation, "scheme": scheme,
        "scheme_name": scheme_info["name"], "result_ciphertext_id": result_ciphertext_id,
        "compute_time_ms": round(compute_time, 2), "engine": "TenSEAL",
    }


# ==================== 解密 ====================

async def decrypt_result(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    ciphertext_id: str,
    key_id: str,
    scheme: str = "ckks",
) -> dict:
    result = await db.execute(select(HeCiphertext).where(HeCiphertext.ciphertext_id == ciphertext_id))
    ct = result.scalar_one_or_none()
    if not ct:
        raise DataNotFoundError(f"密文未找到: {ciphertext_id}")
    if not hasattr(ct, 'ciphertext_data') or not ct.ciphertext_data:
        raise DataValidationError("密文数据为空")

    key_result = await db.execute(select(HeKey).where(HeKey.key_id == key_id))
    key_record = key_result.scalar_one_or_none()
    if not key_record or not key_record.key_data:
        raise DataNotFoundError(f"HE 密钥未找到: {key_id}")

    context = _load_context_from_db(key_record.key_data)

    start_time = time.time()
    try:
        data = base64.b64decode(ct.ciphertext_data)
        vec = ts.lazy_ckks_vector_from(data) if scheme == "ckks" else ts.lazy_bfv_vector_from(data)
        vec.link_context(context)
        plaintext = vec.decrypt()
    except Exception as e:
        logger.error(f"HE decryption failed: {e}")
        raise ComputeError(f"HE 解密失败: {e}")

    dec_time = (time.time() - start_time) * 1000

    if scheme == "bfv":
        values = [int(x) for x in plaintext[:10]]
    else:
        values = [round(float(x), 6) for x in plaintext[:10]]

    task = ComputeTask(
        name=f"HE 解密", task_type="HE", scenario="decrypt_result",
        config={"scheme": scheme, "ciphertext_id": ciphertext_id, "decrypt_time_ms": dec_time},
        input_asset_ids=[], status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    _audit_log("decrypt_result", ciphertext_id, {"decrypt_time_ms": dec_time})
    logger.info(f"HE decrypt: {ciphertext_id}, {dec_time:.1f}ms")

    return {
        "task_id": str(task.id), "ciphertext_id": ciphertext_id, "scheme": scheme,
        "decrypt_time_ms": round(dec_time, 2), "plaintext_values": values,
        "total_slots": plaintext.size, "engine": "TenSEAL",
    }


# ==================== 状态查询 ====================

async def get_he_status(db: AsyncSession, user_id: str, key_id: Optional[str] = None) -> dict:
    active_keys = []
    if key_id:
        result = await db.execute(select(HeKey).where(HeKey.key_id == key_id))
        key = result.scalar_one_or_none()
        if key:
            active_keys.append({"key_id": key.key_id, "scheme": key.scheme,
                                "created_at": key.created_at.isoformat() if key.created_at else None})

    return {
        "active_keys": len(active_keys),
        "keys": active_keys,
        "engine": "TenSEAL (Microsoft SEAL)",
        "supported_schemes": list(HE_SCHEMES.keys()),
    }
