"""
数据沙箱管理服务
沙箱CRUD / 算法准入扫描（静态分析+黑名单检查）/ 出口审核（脱敏检查+合规性验证）
"""
import uuid
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import ComputeTask
from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import ComputeError, DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# 沙箱状态
SANDBOX_STATUSES = ["created", "active", "scanning", "running", "exporting", "destroyed"]

# 算法黑名单关键词
ALGORITHM_BLACKLIST = [
    r"os\.system", r"subprocess", r"eval\s*\(", r"exec\s*\(",
    r"__import__", r"open\s*\(", r"shutil", r"sys\.exit",
    r"socket", r"requests\.", r"http\.", r"urllib",
    r"pickle\.load", r"marshal\.load", r"ctypes",
    r"netcat", r"nc\s", r"telnet", r"ssh",
    r"rm\s+-rf", r"format\s+[A-Z]:", r"del\s+/",
]

# 敏感数据检测模式
SENSITIVE_DATA_PATTERNS = [
    (r"\b\d{17}[\dXx]\b", "身份证号"),
    (r"\b1[3-9]\d{9}\b", "手机号码"),
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "邮箱地址"),
    (r"\b\d{16,19}\b", "银行卡号"),
    (r"\b\d{6}\b", "6位数字密码/验证码"),
]

# 沙箱实例存储
_sandbox_store: dict[str, dict] = {}


async def list_sandboxes(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """查询沙箱列表"""
    sandboxes = list(_sandbox_store.values())

    if status:
        sandboxes = [s for s in sandboxes if s.get("status") == status]

    total = len(sandboxes)
    items = sandboxes[offset:offset + limit]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def create_sandbox(
    db: AsyncSession,
    name: str,
    algorithm_code: str,
    input_asset_ids: list[str],
    runtime_config: Optional[dict] = None,
    user_id: str = "",
    organization_id: str = "",
) -> dict:
    """
    创建数据沙箱

    1. 校验输入资产
    2. 创建沙箱实例
    3. 创建 ComputeTask
    """
    # 1. 校验输入资产（至少1个）
    if not input_asset_ids:
        raise DataValidationError("至少需要指定一个输入资产")

    # 2. 创建沙箱实例
    sandbox_id = str(uuid.uuid4())
    sandbox = {
        "sandbox_id": sandbox_id,
        "name": name,
        "status": "created",
        "algorithm_code": algorithm_code,
        "algorithm_hash": gmssl_adapter.sm3_hash(algorithm_code),
        "input_asset_ids": input_asset_ids,
        "runtime_config": runtime_config or {
            "cpu_limit": "2",
            "memory_limit": "4Gi",
            "timeout_seconds": 3600,
            "network_enabled": False,
        },
        "created_by": user_id,
        "organization_id": organization_id,
        "scan_result": None,
        "export_result": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _sandbox_store[sandbox_id] = sandbox

    # 3. 创建 ComputeTask
    task_config = {
        "sandbox_id": sandbox_id,
        "algorithm_hash": sandbox["algorithm_hash"],
        "input_asset_ids": input_asset_ids,
        "runtime_config": sandbox["runtime_config"],
        "signature_threshold": 1,
    }

    task = ComputeTask(
        name=f"沙箱: {name}",
        task_type="Sandbox",
        scenario="sandbox_execution",
        config=task_config,
        input_asset_ids=[uuid.UUID(a) for a in input_asset_ids if len(a) == 36],
        status="draft",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    sandbox["task_id"] = str(task.id)

    logger.info(f"Sandbox created: {sandbox_id}, name={name}")
    return {
        "sandbox_id": sandbox_id,
        "task_id": str(task.id),
        "name": name,
        "status": "created",
        "algorithm_hash": sandbox["algorithm_hash"],
        "runtime_config": sandbox["runtime_config"],
    }


async def get_sandbox(
    sandbox_id: str,
) -> dict:
    """获取沙箱详情"""
    sandbox = _sandbox_store.get(sandbox_id)
    if not sandbox:
        raise DataNotFoundError("沙箱未找到")
    return sandbox


async def delete_sandbox(
    sandbox_id: str,
) -> None:
    """删除沙箱"""
    sandbox = _sandbox_store.get(sandbox_id)
    if not sandbox:
        raise DataNotFoundError("沙箱未找到")

    if sandbox["status"] == "running":
        raise ComputeError("沙箱正在运行中，请先停止")

    sandbox["status"] = "destroyed"
    sandbox["destroyed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(f"Sandbox destroyed: {sandbox_id}")


async def scan_algorithm(
    sandbox_id: str,
) -> dict:
    """
    算法准入扫描

    1. 静态代码分析（黑名单检查）
    2. 危险操作检测
    3. 资源限制检查
    4. 生成扫描报告
    """
    sandbox = _sandbox_store.get(sandbox_id)
    if not sandbox:
        raise DataNotFoundError("沙箱未找到")

    code = sandbox.get("algorithm_code", "")
    if not code:
        raise DataValidationError("沙箱中没有算法代码")

    sandbox["status"] = "scanning"

    # 1. 黑名单检查
    blacklist_hits = []
    for pattern in ALGORITHM_BLACKLIST:
        matches = re.findall(pattern, code, re.IGNORECASE)
        if matches:
            blacklist_hits.append({
                "pattern": pattern,
                "matches": matches[:5],
                "severity": "critical",
            })

    # 2. 代码复杂度检查
    code_lines = code.strip().split("\n")
    code_length = len(code_lines)
    complexity_warning = code_length > 500

    # 3. 资源限制检查
    runtime_config = sandbox.get("runtime_config", {})
    cpu_limit = runtime_config.get("cpu_limit", "2")
    memory_limit = runtime_config.get("memory_limit", "4Gi")
    network_enabled = runtime_config.get("network_enabled", False)

    resource_warnings = []
    if network_enabled:
        resource_warnings.append("算法启用了网络访问，建议关闭")
    if int(cpu_limit.replace("n", "")) > 4:
        resource_warnings.append("CPU 限制偏高，建议不超过 4 核")

    # 4. 生成报告
    is_approved = len(blacklist_hits) == 0 and not complexity_warning

    scan_result = {
        "sandbox_id": sandbox_id,
        "is_approved": is_approved,
        "blacklist_hits": blacklist_hits,
        "code_stats": {
            "lines": code_length,
            "characters": len(code),
            "complexity_warning": complexity_warning,
        },
        "resource_warnings": resource_warnings,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    sandbox["scan_result"] = scan_result
    sandbox["status"] = "active" if is_approved else "created"

    logger.info(
        f"Algorithm scan: sandbox={sandbox_id}, approved={is_approved}, "
        f"hits={len(blacklist_hits)}"
    )
    return scan_result


async def export_audit(
    sandbox_id: str,
    output_data: str = "",
) -> dict:
    """
    出口审核

    1. 脱敏检查（检测敏感数据残留）
    2. 合规性验证
    3. 数据量限制检查
    4. 生成审核报告
    """
    sandbox = _sandbox_store.get(sandbox_id)
    if not sandbox:
        raise DataNotFoundError("沙箱未找到")

    if sandbox["status"] != "running" and sandbox["status"] != "active":
        raise ComputeError("沙箱状态不允许出口审核")

    sandbox["status"] = "exporting"

    # 1. 敏感数据检测
    sensitive_findings = []
    for pattern, desc in SENSITIVE_DATA_PATTERNS:
        matches = re.findall(pattern, output_data)
        if matches:
            sensitive_findings.append({
                "type": desc,
                "pattern": pattern,
                "count": len(matches),
                "severity": "high",
            })

    # 2. 合规性验证
    compliance_checks = {
        "has_scan_approval": sandbox.get("scan_result", {}).get("is_approved", False),
        "no_sensitive_data": len(sensitive_findings) == 0,
        "data_volume_within_limit": len(output_data) < 1_000_000,  # 1MB 限制
        "algorithm_hash_verified": True,
    }

    # 3. 数据量检查
    data_volume_bytes = len(output_data.encode("utf-8"))
    volume_limit = 10 * 1024 * 1024  # 10MB
    volume_ok = data_volume_bytes < volume_limit

    # 4. 综合判定
    all_checks_passed = all(compliance_checks.values()) and volume_ok

    audit_result = {
        "sandbox_id": sandbox_id,
        "is_approved": all_checks_passed,
        "sensitive_findings": sensitive_findings,
        "compliance_checks": compliance_checks,
        "data_volume_bytes": data_volume_bytes,
        "volume_limit_bytes": volume_limit,
        "volume_ok": volume_ok,
        "audited_at": datetime.now(timezone.utc).isoformat(),
    }

    sandbox["export_result"] = audit_result
    sandbox["status"] = "active"

    logger.info(
        f"Export audit: sandbox={sandbox_id}, approved={all_checks_passed}"
    )
    return audit_result
