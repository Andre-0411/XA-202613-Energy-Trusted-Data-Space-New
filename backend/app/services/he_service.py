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


async def run_he_benchmark(
    scheme: str = "ckks",
    poly_modulus_degree: int = 8192,
    data_size: int = 1000,
) -> dict:
    """
    同态加密性能基准测试

    测试 TenSEAL CKKS/BFV 方案的各项操作性能：
    - 密钥生成
    - 加密速度
    - 密文加法
    - 密文乘法
    - 解密速度

    Args:
        scheme: HE 方案 (ckks/bfv)
        poly_modulus_degree: 多项式模数维度
        data_size: 测试数据大小

    Returns:
        性能基准结果
    """
    if scheme not in HE_SCHEMES:
        raise DataValidationError(f"不支持的 HE 方案: {scheme}")

    results = {}

    # 1. 密钥生成
    start = time.time()
    context = _create_context(scheme, poly_modulus_degree)
    keygen_time = (time.time() - start) * 1000

    results["key_generation"] = {
        "time_ms": round(keygen_time, 2),
        "poly_modulus_degree": poly_modulus_degree,
    }

    # 准备测试数据
    if scheme == "ckks":
        data = [float(i) / data_size for i in range(data_size)]
    else:
        data = [i % 1000 for i in range(data_size)]

    # 2. 加密性能
    iterations = 10
    start = time.time()
    for _ in range(iterations):
        if scheme == "ckks":
            enc_vec = ts.ckks_vector(context, data)
        else:
            enc_vec = ts.bfv_vector(context, data)
    encrypt_time = (time.time() - start) * 1000

    results["encryption"] = {
        "iterations": iterations,
        "data_size": data_size,
        "total_time_ms": round(encrypt_time, 2),
        "avg_time_ms": round(encrypt_time / iterations, 2),
        "throughput_values_per_sec": round(data_size * iterations / (encrypt_time / 1000)),
    }

    # 3. 密文加法性能
    if scheme == "ckks":
        enc1 = ts.ckks_vector(context, data)
        enc2 = ts.ckks_vector(context, [x + 1.0 for x in data])
    else:
        enc1 = ts.bfv_vector(context, data)
        enc2 = ts.bfv_vector(context, [x + 1 for x in data])

    start = time.time()
    for _ in range(iterations):
        enc_sum = enc1 + enc2
    add_time = (time.time() - start) * 1000

    results["ciphertext_addition"] = {
        "iterations": iterations,
        "total_time_ms": round(add_time, 2),
        "avg_time_ms": round(add_time / iterations, 2),
    }

    # 4. 密文乘法性能
    start = time.time()
    for _ in range(iterations):
        enc_product = enc1 * enc2
    mul_time = (time.time() - start) * 1000

    results["ciphertext_multiplication"] = {
        "iterations": iterations,
        "total_time_ms": round(mul_time, 2),
        "avg_time_ms": round(mul_time / iterations, 2),
    }

    # 5. 解密性能
    start = time.time()
    for _ in range(iterations):
        if scheme == "ckks":
            dec_vec = ts.ckks_vector(context, data)
        else:
            dec_vec = ts.bfv_vector(context, data)
        dec_vec.decrypt()
    decrypt_time = (time.time() - start) * 1000

    results["decryption"] = {
        "iterations": iterations,
        "data_size": data_size,
        "total_time_ms": round(decrypt_time, 2),
        "avg_time_ms": round(decrypt_time / iterations, 2),
    }

    # 6. 密文大小
    enc_size = len(enc_vec.serialize())

    return {
        "benchmark": f"he_{scheme}_performance",
        "scheme": scheme,
        "scheme_name": HE_SCHEMES[scheme]["name"],
        "poly_modulus_degree": poly_modulus_degree,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "ciphertext_size_bytes": enc_size,
        "summary": {
            "encrypt_avg_ms": results["encryption"]["avg_time_ms"],
            "add_avg_ms": results["ciphertext_addition"]["avg_time_ms"],
            "multiply_avg_ms": results["ciphertext_multiplication"]["avg_time_ms"],
            "decrypt_avg_ms": results["decryption"]["avg_time_ms"],
        },
    }


async def run_he_operation_demo(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
) -> dict:
    """
    同态加密运算演示

    演示 CKKS 和 BFV 方案的密文运算：
    1. 加密两个向量
    2. 执行密文加法
    3. 执行密文乘法
    4. 解密结果
    5. 验证正确性

    Args:
        db: 数据库会话
        user_id: 用户 ID
        organization_id: 组织 ID

    Returns:
        演示结果
    """
    demo_results = {}

    for scheme in ["ckks", "bfv"]:
        scheme_info = HE_SCHEMES[scheme]
        context = _create_context(scheme)

        # 准备数据
        if scheme == "ckks":
            data_a = [1.5, 2.3, 3.7, 4.1, 5.9]
            data_b = [0.5, 1.7, 2.1, 3.3, 4.6]
        else:
            data_a = [10, 20, 30, 40, 50]
            data_b = [5, 15, 25, 35, 45]

        # 加密
        start = time.time()
        if scheme == "ckks":
            enc_a = ts.ckks_vector(context, data_a)
            enc_b = ts.ckks_vector(context, data_b)
        else:
            enc_a = ts.bfv_vector(context, data_a)
            enc_b = ts.bfv_vector(context, data_b)
        encrypt_time = (time.time() - start) * 1000

        # 密文加法
        start = time.time()
        enc_sum = enc_a + enc_b
        add_time = (time.time() - start) * 1000

        # 密文乘法
        start = time.time()
        enc_product = enc_a * enc_b
        mul_time = (time.time() - start) * 1000

        # 解密
        start = time.time()
        dec_sum = enc_sum.decrypt()
        dec_product = enc_product.decrypt()
        decrypt_time = (time.time() - start) * 1000

        # 验证
        if scheme == "ckks":
            expected_sum = [a + b for a, b in zip(data_a, data_b)]
            expected_product = [a * b for a, b in zip(data_a, data_b)]
            sum_error = sum(abs(d - e) for d, e in zip(dec_sum, expected_sum)) / len(expected_sum)
            product_error = sum(abs(d - e) for d, e in zip(dec_product, expected_product)) / len(expected_product)
        else:
            expected_sum = [a + b for a, b in zip(data_a, data_b)]
            expected_product = [a * b for a, b in zip(data_a, data_b)]
            sum_error = 0 if list(dec_sum) == expected_sum else 1
            product_error = 0 if list(dec_product) == expected_product else 1

        demo_results[scheme] = {
            "scheme_name": scheme_info["name"],
            "input_a": data_a,
            "input_b": data_b,
            "sum_result": list(dec_sum)[:5],
            "sum_expected": expected_sum,
            "sum_error": round(sum_error, 8),
            "product_result": list(dec_product)[:5],
            "product_expected": expected_product,
            "product_error": round(product_error, 8),
            "timing": {
                "encrypt_ms": round(encrypt_time, 2),
                "add_ms": round(add_time, 2),
                "multiply_ms": round(mul_time, 2),
                "decrypt_ms": round(decrypt_time, 2),
            },
        }

    # 存储演示任务
    task = ComputeTask(
        name="同态加密运算演示", task_type="HE", scenario="he_demo",
        config={"schemes": ["ckks", "bfv"]},
        input_asset_ids=[], status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    _audit_log("he_operation_demo", str(task.id))

    return {
        "task_id": str(task.id),
        "demo": "he_operation_demo",
        "engine": "TenSEAL (Microsoft SEAL)",
        "results": demo_results,
        "summary": {
            "ckks_sum_error": demo_results["ckks"]["sum_error"],
            "ckks_product_error": demo_results["ckks"]["product_error"],
            "bfv_exact_match": demo_results["bfv"]["sum_error"] == 0 and demo_results["bfv"]["product_error"] == 0,
        },
    }
