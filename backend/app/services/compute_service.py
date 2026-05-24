"""
计算任务编排服务（增强版）
任务CRUD + 状态机(draft→pending→running→completed/failed/cancelled) + 多方签名收集与验证 + 结果查询
+ DID签名验证（通过 did_service 解析公钥）+ 区块链双节点存证（启动/完成）
+ 优先级队列 + 任务依赖管理 + 自动重试 + 任务取消 + 资源预估/预分配
"""
import uuid
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import ComputeTask, TaskSignature, DagDefinition
from app.models.data_asset import DataAsset
from app.core.gmssl_adapter import gmssl_adapter
from app.schemas.compute import ComputeTaskCreate, ComputeTaskResponse, TaskSignatureRequest
from app.schemas.blockchain import EvidenceCreate
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    ComputeError, ComputeTaskNotFoundError, DataNotFoundError,
    DataValidationError, PermissionDeniedError, DIDError,
)

logger = logging.getLogger(__name__)

# 任务状态机
VALID_TRANSITIONS = {
    "draft": {"pending"},
    "pending": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": set(),   # terminal
    "failed": {"pending"},  # 可重试
    "cancelled": {"pending"},  # 可重试
}

# 有效任务类型
VALID_TASK_TYPES = {"FL", "MPC", "TEE", "HE", "DP", "Sandbox"}

# 签名阈值（默认需要所有参与方签名）
DEFAULT_SIGNATURE_THRESHOLD = 2

# 默认优先级
DEFAULT_PRIORITY = 5
MAX_PRIORITY = 1
MIN_PRIORITY = 10

# 默认重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0   # 秒
DEFAULT_RETRY_MAX_DELAY = 60.0   # 秒
DEFAULT_RETRY_FACTOR = 2.0       # 指数因子

# 资源估算默认值（CPU/内存/存储/时长，单位: core·h, GB·h, GB, h）
DEFAULT_RESOURCE_ESTIMATE = {
    "cpu_hours": 0.5,
    "memory_gb_hours": 1.0,
    "storage_gb": 0.5,
    "estimated_duration_minutes": 30,
}


# ==================== 辅助函数 ====================


def _get_task_priority(task: ComputeTask) -> int:
    """从任务 config 中提取优先级，范围 1-10，1 最高"""
    config = task.config or {}
    priority = config.get("priority", DEFAULT_PRIORITY)
    return max(MAX_PRIORITY, min(MIN_PRIORITY, int(priority)))


def _get_task_dependencies(task: ComputeTask) -> list[str]:
    """从任务 config 中提取依赖任务 ID 列表"""
    config = task.config or {}
    deps = config.get("dependencies", [])
    return [str(d) for d in deps]


def _get_task_retry_config(task: ComputeTask) -> dict:
    """从任务 config 中提取重试配置"""
    config = task.config or {}
    retry_cfg = config.get("retry", {})
    return {
        "max_retries": retry_cfg.get("max_retries", DEFAULT_MAX_RETRIES),
        "base_delay": retry_cfg.get("base_delay", DEFAULT_RETRY_BASE_DELAY),
        "max_delay": retry_cfg.get("max_delay", DEFAULT_RETRY_MAX_DELAY),
        "factor": retry_cfg.get("factor", DEFAULT_RETRY_FACTOR),
    }


def _get_resource_estimate(task: ComputeTask) -> dict:
    """从任务 config 中提取资源估算"""
    config = task.config or {}
    estimate = config.get("resource_estimate", {})
    result = dict(DEFAULT_RESOURCE_ESTIMATE)
    result.update(estimate)
    return result


def _compute_retry_delay(attempt: int, base_delay: float, factor: float, max_delay: float) -> float:
    """
    计算指数退避延迟

    Args:
        attempt: 第几次重试 (0-based)
        base_delay: 基础延迟（秒）
        factor: 指数因子
        max_delay: 最大延迟（秒）

    Returns:
        延迟秒数
    """
    delay = base_delay * (factor ** attempt)
    return min(delay, max_delay)


# ==================== 任务列表查询（增强版） ====================


async def list_tasks(
    db: AsyncSession,
    params: PaginationParams,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    scenario: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PaginatedResponse:
    """查询计算任务列表"""
    query = select(ComputeTask)
    if task_type:
        query = query.where(ComputeTask.task_type == task_type)
    if status:
        query = query.where(ComputeTask.status == status)
    if scenario:
        query = query.where(ComputeTask.scenario == scenario)
    if organization_id:
        query = query.where(ComputeTask.organization_id == uuid.UUID(organization_id))

    result = await paginate_query(db, query, params, ComputeTaskResponse)
    return result


async def get_task(
    db: AsyncSession,
    task_id: str,
) -> ComputeTaskResponse:
    """获取计算任务详情"""
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")
    return ComputeTaskResponse.model_validate(task)


async def create_task(
    db: AsyncSession,
    request: ComputeTaskCreate,
    user_id: str,
    organization_id: str,
) -> ComputeTaskResponse:
    """
    创建计算任务

    1. 校验任务类型
    2. 校验输入资产存在且可访问
    3. 校验 DAG（如关联）
    4. 校验依赖任务（如配置）
    5. 估算资源用量
    6. 创建任务
    """
    # 1. 校验任务类型
    if request.task_type not in VALID_TASK_TYPES:
        raise DataValidationError(
            f"无效的任务类型: {request.task_type}，允许值: {VALID_TASK_TYPES}"
        )

    # 2. 校验输入资产
    for asset_id_str in request.input_asset_ids:
        asset_result = await db.execute(
            select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id_str))
        )
        asset = asset_result.scalar_one_or_none()
        if not asset:
            raise DataNotFoundError(f"输入资产未找到: {asset_id_str}")
        if asset.status not in ("published", "classified"):
            raise DataValidationError(f"资产 {asset.name} 状态不允许用于计算")

    # 3. 校验 DAG
    if request.dag_id:
        dag_result = await db.execute(
            select(DagDefinition).where(DagDefinition.id == uuid.UUID(request.dag_id))
        )
        if not dag_result.scalar_one_or_none():
            raise DataNotFoundError("关联的 DAG 未找到")

    # 4. 校验依赖任务
    config = request.config or {}
    dependency_ids = config.get("dependencies", [])
    for dep_id in dependency_ids:
        dep_result = await db.execute(
            select(ComputeTask).where(ComputeTask.id == uuid.UUID(str(dep_id)))
        )
        dep_task = dep_result.scalar_one_or_none()
        if not dep_task:
            raise DataNotFoundError(f"依赖任务不存在: {dep_id}")
        if dep_task.status in ("failed", "cancelled"):
            raise DataValidationError(
                f"依赖任务 {dep_id} 状态为 {dep_task.status}，无法创建"
            )

    # 5. 资源估算
    resource_estimate = _get_resource_estimate_from_config(config)
    config["resource_estimate"] = resource_estimate

    # 6. 创建任务
    task = ComputeTask(
        name=request.name,
        task_type=request.task_type,
        scenario=request.scenario,
        dag_id=uuid.UUID(request.dag_id) if request.dag_id else None,
        config=config,
        input_asset_ids=[uuid.UUID(a) for a in request.input_asset_ids],
        status="draft",
        created_by=uuid.UUID(user_id),
        organization_id=uuid.UUID(organization_id),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(
        f"Compute task created: {task.id} ({task.name}), type={task.task_type}, "
        f"priority={_get_task_priority(task)}"
    )
    return ComputeTaskResponse.model_validate(task)


async def update_task(
    db: AsyncSession,
    task_id: str,
    request: ComputeTaskCreate,
) -> ComputeTaskResponse:
    """更新计算任务（仅 draft 状态可修改）"""
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    if task.status not in ("draft", "pending"):
        raise DataValidationError("仅 draft/pending 状态的任务可以修改")

    if request.task_type not in VALID_TASK_TYPES:
        raise DataValidationError(f"无效的任务类型: {request.task_type}")

    task.name = request.name
    task.task_type = request.task_type
    task.scenario = request.scenario
    task.config = request.config
    task.input_asset_ids = [uuid.UUID(a) for a in request.input_asset_ids]
    if request.dag_id:
        task.dag_id = uuid.UUID(request.dag_id)

    await db.commit()
    await db.refresh(task)

    logger.info(f"Compute task updated: {task.id}")
    return ComputeTaskResponse.model_validate(task)


async def start_task(
    db: AsyncSession,
    task_id: str,
    user_id: str,
) -> dict:
    """
    启动计算任务

    1. 校验状态转换
    2. 检查签名是否达到阈值
    3. 检查依赖任务是否完成
    4. 预估资源配额
    5. 更新状态为 running
    6. 记录启动时间
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    # 状态转换校验
    if task.status not in ("draft", "pending"):
        valid = VALID_TRANSITIONS.get(task.status, set())
        if "running" not in valid:
            raise ComputeError(f"任务状态 {task.status} 不允许启动，需先提交")

    # 检查签名阈值
    sig_result = await db.execute(
        select(TaskSignature).where(TaskSignature.task_id == uuid.UUID(task_id))
    )
    signatures = sig_result.scalars().all()
    config = task.config or {}
    threshold = config.get("signature_threshold", DEFAULT_SIGNATURE_THRESHOLD)

    if len(signatures) < threshold:
        raise ComputeError(
            f"签名不足: 当前 {len(signatures)}/{threshold}，需达到阈值才能启动"
        )

    # 检查依赖任务是否完成
    dependency_ids = _get_task_dependencies(task)
    if dependency_ids:
        for dep_id in dependency_ids:
            dep_result = await db.execute(
                select(ComputeTask).where(ComputeTask.id == uuid.UUID(dep_id))
            )
            dep_task = dep_result.scalar_one_or_none()
            if not dep_task:
                raise ComputeError(f"依赖任务不存在: {dep_id}")
            if dep_task.status != "completed":
                raise ComputeError(
                    f"依赖任务 {dep_id} 未完成（当前状态: {dep_task.status}），无法启动"
                )

    # 状态转换
    old_status = task.status
    task.status = "running"
    # started_at 列为 TIMESTAMP WITHOUT TIME ZONE，必须使用 naive datetime
    task.started_at = datetime.utcnow()
    task.progress = 0
    await db.commit()

    # 区块链存证：任务启动 (node_type=compute)
    try:
        from app.services.blockchain_evidence_service import submit_evidence
        param_hash = gmssl_adapter.sm3_hash(str(task.config))
        await submit_evidence(
            db,
            EvidenceCreate(
                node_type="compute",
                resource_id=task_id,
                resource_type="compute_task",
                data_hash=param_hash,
                evidence_data={
                    "task_id": task_id,
                    "task_type": task.task_type,
                    "task_name": task.name,
                    "submitter_did": str(task.created_by),
                    "param_hash": param_hash,
                    "started_at": task.started_at.isoformat(),
                    "signature_count": len(signatures),
                    "threshold": threshold,
                    "priority": _get_task_priority(task),
                    "dependencies": dependency_ids,
                },
            ),
        )
        logger.info(f"Blockchain evidence recorded: compute submitted for task {task_id}")
    except Exception as e:
        # 存证失败不阻断任务启动，记录警告
        logger.warning(f"Blockchain evidence failed for task start {task_id}: {e}")

    logger.info(f"Compute task started: {task_id}, {old_status} -> running")
    return {
        "task_id": task_id,
        "status": "running",
        "previous_status": old_status,
        "started_at": task.started_at.isoformat(),
        "signature_count": len(signatures),
        "threshold": threshold,
        "priority": _get_task_priority(task),
        "dependencies": dependency_ids,
    }


async def stop_task(
    db: AsyncSession,
    task_id: str,
    user_id: str,
) -> dict:
    """停止计算任务（取消）"""
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    if task.status not in ("running", "pending", "draft"):
        raise ComputeError(f"任务状态 {task.status} 不允许取消")

    old_status = task.status
    task.status = "cancelled"
    await db.commit()

    # 检查是否有依赖此任务的等待任务，级联通知
    await _notify_dependents_cancelled(db, task_id)

    logger.info(f"Compute task stopped: {task_id}, {old_status} -> cancelled")
    return {
        "task_id": task_id,
        "status": "cancelled",
        "previous_status": old_status,
        "stopped_at": datetime.now(timezone.utc).isoformat(),
    }


async def cancel_task(
    db: AsyncSession,
    task_id: str,
    user_id: str,
    reason: Optional[str] = None,
) -> dict:
    """
    取消计算任务（带原因）

    支持取消处于 draft/pending/running 状态的任务。
    会级联检查依赖任务并记录取消原因。
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    if task.status in ("completed", "failed", "cancelled"):
        raise ComputeError(f"任务已处于终态 {task.status}，无法取消")

    old_status = task.status
    task.status = "cancelled"
    task.error_message = reason or "用户取消"
    # completed_at 列为 TIMESTAMP WITHOUT TIME ZONE，使用 naive datetime
    task.completed_at = datetime.utcnow()
    await db.commit()

    # 释放已预分配的资源
    await _release_task_resources(db, task)

    # 级联通知依赖任务
    await _notify_dependents_cancelled(db, task_id)

    logger.info(
        f"Compute task cancelled: {task_id}, {old_status} -> cancelled, reason={reason}"
    )
    return {
        "task_id": task_id,
        "status": "cancelled",
        "previous_status": old_status,
        "reason": reason or "用户取消",
        "cancelled_at": task.completed_at.isoformat(),
    }


async def complete_task(
    db: AsyncSession,
    task_id: str,
    result_ref: str = "",
    result_hash: str = "",
    progress: int = 100,
    error_message: str = "",
) -> dict:
    """
    完成计算任务

    1. 校验状态为 running
    2. 更新状态为 completed 或 failed
    3. 记录结果引用和哈希
    4. 区块链存证：计算结果 (node_type=result)
    5. 检查是否需要自动重试
    6. 释放预分配资源
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    if task.status != "running":
        raise ComputeError("只有运行中的任务可以标记完成")

    # 计算耗时（两个字段都是 TIMESTAMP WITHOUT TIME ZONE，使用 naive datetime 避免时区冲突）
    now = datetime.utcnow()
    duration_seconds = 0.0
    if task.started_at:
        duration_seconds = (now - task.started_at).total_seconds()

    # 状态转换
    is_success = not error_message
    task.status = "completed" if is_success else "failed"
    task.completed_at = now
    task.progress = progress
    task.result_ref = result_ref
    task.result_hash = result_hash
    task.error_message = error_message
    await db.commit()

    # 失败时检查自动重试
    if not is_success:
        retry_attempted = await _auto_retry_if_configured(db, task)
        if retry_attempted:
            logger.info(f"Auto-retry triggered for failed task {task_id}")
        else:
            # 释放预分配资源
            await _release_task_resources(db, task)
    else:
        # 成功：释放预分配资源
        await _release_task_resources(db, task)

    # 区块链存证：任务完成 (node_type=result)
    try:
        from app.services.blockchain_evidence_service import submit_evidence
        evidence_hash = gmssl_adapter.sm3_hash(
            f"{task_id}:{result_hash}:{task.status}"
        )
        await submit_evidence(
            db,
            EvidenceCreate(
                node_type="result",
                resource_id=task_id,
                resource_type="compute_task",
                data_hash=result_hash or evidence_hash,
                evidence_data={
                    "task_id": task_id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "result_ref": result_ref,
                    "result_hash": result_hash,
                    "duration_seconds": round(duration_seconds, 3),
                    "completed_at": now.isoformat(),
                    "error_message": error_message,
                    "priority": _get_task_priority(task),
                },
            ),
        )
        logger.info(f"Blockchain evidence recorded: result for task {task_id}")
    except Exception as e:
        logger.warning(f"Blockchain evidence failed for task completion {task_id}: {e}")

    logger.info(
        f"Compute task completed: {task_id}, status={task.status}, "
        f"duration={duration_seconds:.1f}s"
    )
    return {
        "task_id": task_id,
        "status": task.status,
        "result_ref": result_ref,
        "result_hash": result_hash,
        "duration_seconds": round(duration_seconds, 3),
        "completed_at": now.isoformat(),
    }


async def get_task_result(
    db: AsyncSession,
    task_id: str,
) -> dict:
    """获取计算任务结果"""
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    return {
        "task_id": str(task.id),
        "status": task.status,
        "progress": task.progress,
        "result_ref": task.result_ref,
        "result_hash": task.result_hash,
        "error_message": task.error_message,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


async def sign_task(
    db: AsyncSession,
    task_id: str,
    request: TaskSignatureRequest,
) -> dict:
    """
    多方签名

    1. 校验任务存在
    2. 校验签名方未重复签名
    3. 验证 SM2 签名
    4. 记录签名
    """
    # 1. 校验任务
    task_result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    if task.status not in ("draft", "pending"):
        raise DataValidationError("仅 draft/pending 状态的任务可以签名")

    # 2. 校验不重复签名
    existing = await db.execute(
        select(TaskSignature).where(
            and_(
                TaskSignature.task_id == uuid.UUID(task_id),
                TaskSignature.signer_did == request.signer_did,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataValidationError(f"签名方 {request.signer_did} 已签名")

    # 3. 通过 DID 解析公钥并验证 SM2 签名
    from app.services.did_service import resolve, extract_public_key
    config_hash = gmssl_adapter.sm3_hash(str(task.config))
    sign_data = f"{task_id}:{config_hash}"
    try:
        did_document = await resolve(db, request.signer_did)
        public_key = extract_public_key(did_document, purpose="authentication")
        is_valid = gmssl_adapter.sm2_verify(public_key, sign_data, request.signature)
        if not is_valid:
            raise DataValidationError("SM2 签名验证失败")
    except DIDError as e:
        logger.error(f"DID resolution failed for {request.signer_did}: {e}")
        raise DataValidationError(f"DID 解析失败: {e}")
    except DataValidationError:
        raise
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        raise DataValidationError("SM2 签名验证失败")

    # 4. 记录签名
    signature = TaskSignature(
        task_id=uuid.UUID(task_id),
        signer_did=request.signer_did,
        signature=request.signature,
    )
    db.add(signature)
    await db.flush()  # 先 flush 使签名记录可见，再查询计数

    sig_result = await db.execute(
        select(TaskSignature).where(TaskSignature.task_id == uuid.UUID(task_id))
    )
    all_sigs = sig_result.scalars().all()
    config = task.config or {}
    threshold = config.get("signature_threshold", DEFAULT_SIGNATURE_THRESHOLD)

    if len(all_sigs) >= threshold and task.status == "draft":
        task.status = "pending"

    await db.commit()

    logger.info(f"Task signed: {task_id} by {request.signer_did}")
    return {
        "task_id": task_id,
        "signer_did": request.signer_did,
        "signature_count": len(all_sigs),
        "threshold": threshold,
        "auto_submitted": len(all_sigs) >= threshold,
    }


async def get_task_signatures(
    db: AsyncSession,
    task_id: str,
) -> dict:
    """查询任务签名状态"""
    task_result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    sig_result = await db.execute(
        select(TaskSignature).where(TaskSignature.task_id == uuid.UUID(task_id))
    )
    signatures = sig_result.scalars().all()

    config = task.config or {}
    threshold = config.get("signature_threshold", DEFAULT_SIGNATURE_THRESHOLD)

    participants = config.get("participants", [])
    signed_dids = {s.signer_did for s in signatures}
    unsigned = [p for p in participants if p not in signed_dids]

    return {
        "task_id": task_id,
        "threshold": threshold,
        "total_signatures": len(signatures),
        "is_complete": len(signatures) >= threshold,
        "signed": [
            {"signer_did": s.signer_did, "signed_at": s.signed_at.isoformat()}
            for s in signatures
        ],
        "unsigned": unsigned,
    }


async def delete_task(
    db: AsyncSession,
    task_id: str,
) -> None:
    """删除计算任务（仅 draft/cancelled 状态可删除）"""
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    if task.status not in ("draft", "cancelled"):
        raise DataValidationError("仅 draft/cancelled 状态的任务可以删除")

    task.status = "deleted"
    await db.commit()
    logger.info(f"Compute task deleted: {task_id}")


# ==================== 优先级队列 ====================


async def get_pending_tasks_by_priority(
    db: AsyncSession,
    organization_id: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 20,
) -> list[ComputeTaskResponse]:
    """
    按优先级获取待执行任务队列

    按 config.priority 升序排列（1=最高优先级），
    同优先级按创建时间升序排列。

    Args:
        db: 异步数据库会话
        organization_id: 组织 ID 过滤
        task_type: 任务类型过滤
        limit: 返回数量上限

    Returns:
        按优先级排序的任务列表
    """
    conditions = [ComputeTask.status == "pending"]
    if organization_id:
        conditions.append(ComputeTask.organization_id == uuid.UUID(organization_id))
    if task_type:
        conditions.append(ComputeTask.task_type == task_type)

    result = await db.execute(
        select(ComputeTask)
        .where(and_(*conditions))
        .order_by(ComputeTask.created_at.asc())
        .limit(limit * 3)  # 多取一些以便排序
    )
    tasks = list(result.scalars().all())

    # 按优先级排序（config 中的 priority）
    tasks.sort(key=lambda t: (_get_task_priority(t), t.created_at))

    # 截取 limit
    tasks = tasks[:limit]

    return [ComputeTaskResponse.model_validate(t) for t in tasks]


# ==================== 任务依赖管理 ====================


async def get_task_dependencies(
    db: AsyncSession,
    task_id: str,
) -> dict:
    """
    获取任务的依赖关系

    Returns:
        包含 dependencies（上游）和 dependents（下游）的信息
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    # 上游依赖
    dep_ids = _get_task_dependencies(task)
    dependencies = []
    for dep_id in dep_ids:
        dep_result = await db.execute(
            select(ComputeTask).where(ComputeTask.id == uuid.UUID(dep_id))
        )
        dep_task = dep_result.scalar_one_or_none()
        if dep_task:
            dependencies.append({
                "task_id": dep_id,
                "name": dep_task.name,
                "status": dep_task.status,
            })

    # 下游依赖（查找 config.dependencies 中引用此任务的其他任务）
    # PostgreSQL JSONB 包含查询
    result = await db.execute(
        select(ComputeTask).where(
            and_(
                ComputeTask.status.in_(["draft", "pending"]),
                ComputeTask.config["dependencies"].astext.contains(task_id),
            )
        )
    )
    dependents = []
    for dep_task in result.scalars().all():
        dependents.append({
            "task_id": str(dep_task.id),
            "name": dep_task.name,
            "status": dep_task.status,
        })

    return {
        "task_id": task_id,
        "dependencies": dependencies,
        "dependents": dependents,
        "all_dependencies_met": all(
            d["status"] == "completed" for d in dependencies
        ),
    }


async def check_dependencies_met(
    db: AsyncSession,
    task_id: str,
) -> bool:
    """
    检查任务的所有依赖是否已满足

    Args:
        db: 异步数据库会话
        task_id: 任务 ID

    Returns:
        True 如果所有依赖任务已完成
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        return False

    dep_ids = _get_task_dependencies(task)
    if not dep_ids:
        return True

    for dep_id in dep_ids:
        dep_result = await db.execute(
            select(ComputeTask).where(ComputeTask.id == uuid.UUID(dep_id))
        )
        dep_task = dep_result.scalar_one_or_none()
        if not dep_task or dep_task.status != "completed":
            return False

    return True


# ==================== 自动重试 ====================


async def _auto_retry_if_configured(
    db: AsyncSession,
    task: ComputeTask,
) -> bool:
    """
    自动重试失败的任务

    使用指数退避策略。重试次数记录在 config.retry_count 中。

    Args:
        db: 异步数据库会话
        task: 失败的任务

    Returns:
        True 如果触发了重试
    """
    config = task.config or {}
    retry_cfg = _get_task_retry_config(task)
    max_retries = retry_cfg["max_retries"]

    current_retry_count = config.get("retry_count", 0)
    if current_retry_count >= max_retries:
        logger.info(
            f"Task {task.id} exhausted retries ({current_retry_count}/{max_retries})"
        )
        return False

    # 计算退避延迟
    delay = _compute_retry_delay(
        current_retry_count,
        retry_cfg["base_delay"],
        retry_cfg["factor"],
        retry_cfg["max_delay"],
    )

    # 更新重试计数
    config["retry_count"] = current_retry_count + 1
    config["last_retry_at"] = datetime.now(timezone.utc).isoformat()
    config["retry_delay_seconds"] = delay
    task.config = config

    # 重置任务状态为 pending
    task.status = "pending"
    task.error_message = None
    task.progress = 0
    await db.commit()

    logger.info(
        f"Task {task.id} auto-retry #{config['retry_count']}/{max_retries}, "
        f"delay={delay:.1f}s"
    )

    # 延迟后启动（异步，不阻塞）
    # 注：在生产环境中应使用消息队列或定时任务调度器
    # 此处使用 asyncio.create_task 模拟
    asyncio.create_task(_delayed_retry_start(task.id, delay))

    return True


async def _delayed_retry_start(task_id: uuid.UUID, delay_seconds: float) -> None:
    """
    延迟后尝试重新启动任务

    注意：此函数需要独立的数据库会话，因为调用方的会话可能已关闭。
    在生产环境中应使用消息队列调度。
    """
    await asyncio.sleep(delay_seconds)
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ComputeTask).where(ComputeTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task and task.status == "pending":
                # 重新启动（started_at 为 TIMESTAMP WITHOUT TIME ZONE，使用 naive datetime）
                task.status = "running"
                task.started_at = datetime.utcnow()
                task.progress = 0
                await db.commit()
                logger.info(f"Auto-retry: Task {task_id} restarted after {delay_seconds:.1f}s delay")
    except Exception as e:
        logger.error(f"Auto-retry failed for task {task_id}: {e}")


async def get_retry_info(
    db: AsyncSession,
    task_id: str,
) -> dict:
    """
    获取任务的重试信息

    Returns:
        重试配置和历史
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    retry_cfg = _get_task_retry_config(task)
    config = task.config or {}
    retry_count = config.get("retry_count", 0)

    return {
        "task_id": task_id,
        "max_retries": retry_cfg["max_retries"],
        "current_retry_count": retry_count,
        "remaining_retries": max(0, retry_cfg["max_retries"] - retry_count),
        "last_retry_at": config.get("last_retry_at"),
        "retry_delay_seconds": config.get("retry_delay_seconds"),
        "base_delay": retry_cfg["base_delay"],
        "factor": retry_cfg["factor"],
        "max_delay": retry_cfg["max_delay"],
    }


# ==================== 资源估算 ====================


def _get_resource_estimate_from_config(config: dict) -> dict:
    """
    从任务配置中估算资源需求

    根据任务类型和输入资产规模估算 CPU/内存/存储/时长需求。

    Args:
        config: 任务配置

    Returns:
        资源估算字典
    """
    # 基础估算
    estimate = dict(DEFAULT_RESOURCE_ESTIMATE)

    # 根据任务类型调整
    task_type_multiplier = {
        "FL": {"cpu": 2.0, "memory": 2.0, "duration": 2.0},
        "MPC": {"cpu": 3.0, "memory": 1.5, "duration": 3.0},
        "TEE": {"cpu": 1.5, "memory": 1.5, "duration": 1.5},
        "HE": {"cpu": 4.0, "memory": 3.0, "duration": 4.0},
        "DP": {"cpu": 1.2, "memory": 1.0, "duration": 1.0},
        "Sandbox": {"cpu": 1.0, "memory": 1.0, "duration": 1.0},
    }

    task_type = config.get("task_type", "Sandbox")
    multipliers = task_type_multiplier.get(task_type, {"cpu": 1.0, "memory": 1.0, "duration": 1.0})

    # 数据量估算（如果配置了 data_size_gb）
    data_size_gb = config.get("data_size_gb", 1.0)
    data_factor = max(1.0, data_size_gb / 10.0)  # 10GB 基准

    # 并发度估算
    num_workers = config.get("num_workers", 1)

    estimate["cpu_hours"] = round(
        estimate["cpu_hours"] * multipliers["cpu"] * data_factor * num_workers, 2
    )
    estimate["memory_gb_hours"] = round(
        estimate["memory_gb_hours"] * multipliers["memory"] * data_factor, 2
    )
    estimate["storage_gb"] = round(
        data_size_gb * 0.5 + 1.0, 2  # 50% 数据量 + 1GB 基础
    )
    estimate["estimated_duration_minutes"] = int(
        estimate["estimated_duration_minutes"] * multipliers["duration"] * data_factor
    )

    # 用户可覆盖
    user_estimate = config.get("resource_estimate", {})
    estimate.update(user_estimate)

    return estimate


async def estimate_task_resources(
    db: AsyncSession,
    task_id: str,
) -> dict:
    """
    估算任务所需资源

    Args:
        db: 异步数据库会话
        task_id: 任务 ID

    Returns:
        资源估算结果
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    config = task.config or {}
    estimate = _get_resource_estimate_from_config(config)

    return {
        "task_id": task_id,
        "task_type": task.task_type,
        "resource_estimate": estimate,
        "input_asset_count": len(task.input_asset_ids),
    }


async def pre_allocate_resources(
    db: AsyncSession,
    task_id: str,
    organization_id: str,
    user_id: Optional[str] = None,
) -> dict:
    """
    为任务预分配资源配额

    在任务提交时调用，从配额中预留资源。
    任务完成后（成功或失败）释放。

    Args:
        db: 异步数据库会话
        task_id: 任务 ID
        organization_id: 组织 ID
        user_id: 用户 ID

    Returns:
        预分配结果
    """
    result = await db.execute(
        select(ComputeTask).where(ComputeTask.id == uuid.UUID(task_id))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise ComputeTaskNotFoundError("计算任务未找到")

    config = task.config or {}
    estimate = config.get("resource_estimate", DEFAULT_RESOURCE_ESTIMATE)

    allocated: dict[str, float] = {}
    errors: list[str] = []

    # 尝试消耗各资源类型的配额
    from app.services.compute_quota_service import check_quota_available, consume_quota

    resource_map = {
        "cpu_hours": estimate.get("cpu_hours", 0.5),
        "memory_gb_hours": estimate.get("memory_gb_hours", 1.0),
        "compute_tasks": 1.0,  # 每个任务消耗 1 个任务配额
    }

    for resource_type, amount in resource_map.items():
        check_result = await check_quota_available(
            db, organization_id, resource_type, amount, user_id
        )
        if not check_result["allowed"]:
            errors.append(
                f"{resource_type}: 需要 {amount}，可用 {check_result['available']}"
            )
            continue

        await consume_quota(
            db, organization_id, resource_type, amount,
            user_id=user_id, task_id=task_id,
            reason=f"任务 {task_id} 资源预分配",
        )
        allocated[resource_type] = amount

    if errors:
        raise ComputeError(
            f"资源预分配失败（部分资源不足）: {'; '.join(errors)}"
        )

    # 记录预分配信息到 config
    config["pre_allocated_resources"] = allocated
    config["pre_allocated_at"] = datetime.now(timezone.utc).isoformat()
    task.config = config
    await db.commit()

    logger.info(f"Pre-allocated resources for task {task_id}: {allocated}")
    return {
        "task_id": task_id,
        "allocated": allocated,
        "pre_allocated_at": config["pre_allocated_at"],
    }


async def _release_task_resources(
    db: AsyncSession,
    task: ComputeTask,
) -> None:
    """释放任务的预分配资源配额"""
    config = task.config or {}
    pre_allocated = config.get("pre_allocated_resources", {})
    if not pre_allocated:
        return

    try:
        from app.services.compute_quota_service import release_quota
        for resource_type, amount in pre_allocated.items():
            try:
                await release_quota(
                    db, str(task.organization_id), resource_type, amount,
                    user_id=str(task.created_by) if task.created_by else None,
                    task_id=str(task.id),
                    reason=f"任务 {task.id} 完成/取消，释放预分配资源",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to release {resource_type} for task {task.id}: {e}"
                )
    except Exception as e:
        logger.error(f"Resource release failed for task {task.id}: {e}")


async def _notify_dependents_cancelled(
    db: AsyncSession,
    task_id: str,
) -> None:
    """当任务取消时，通知所有依赖此任务的下游任务"""
    try:
        # 查找依赖此任务的 pending 任务
        result = await db.execute(
            select(ComputeTask).where(
                and_(
                    ComputeTask.status == "pending",
                    ComputeTask.config["dependencies"].astext.contains(task_id),
                )
            )
        )
        for dep_task in result.scalars().all():
            dep_config = dep_task.config or {}
            dep_config["dependency_cancelled"] = task_id
            dep_task.config = dep_config
            dep_task.error_message = f"上游任务 {task_id} 已取消"
            logger.warning(
                f"Task {dep_task.id} affected: upstream task {task_id} cancelled"
            )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to notify dependents of cancelled task {task_id}: {e}")
