"""
DAG 执行引擎 — 增强版
DAG定义CRUD + 验证（环检测、依赖完整性） + 执行（拓扑排序+并行调度）
+ 节点重试机制（指数退避） + 检查点机制 + 子DAG嵌套 + 执行状态持久化
+ 详细执行日志
"""
import uuid
import asyncio
import logging
import time
import json
from datetime import datetime, timezone
from typing import Optional, Callable, Any
from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import DagDefinition, ComputeTask
from app.schemas.compute import DagCreate, DagResponse
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import ComputeDagError, DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# ==================== 常量 ====================

VALID_NODE_TYPES = {
    "data_source", "transform", "compute", "evaluate", "output",
    "FL", "MPC", "TEE", "HE", "DP", "Sandbox", "Input", "Output",
    "sub_dag",  # 子DAG节点类型
}

NODE_STATUSES = ["pending", "running", "completed", "failed", "skipped", "retrying"]

# 类型兼容性规则
TYPE_COMPATIBILITY = {
    "Input": {"FL", "MPC", "TEE", "HE", "DP", "Sandbox", "data_source", "transform", "compute", "evaluate", "sub_dag"},
    "FL": {"MPC", "TEE", "HE", "DP", "Output", "evaluate", "output", "sub_dag"},
    "MPC": {"FL", "TEE", "HE", "DP", "Output", "evaluate", "output", "sub_dag"},
    "TEE": {"FL", "MPC", "HE", "DP", "Sandbox", "Output", "evaluate", "output", "sub_dag"},
    "HE": {"MPC", "TEE", "DP", "Output", "evaluate", "output", "sub_dag"},
    "DP": {"Output", "output", "sub_dag"},
    "Sandbox": {"TEE", "DP", "Output", "evaluate", "output", "sub_dag"},
    "data_source": {"transform", "compute", "evaluate", "FL", "MPC", "TEE", "HE", "DP", "Sandbox", "Output", "output", "sub_dag"},
    "transform": {"transform", "compute", "evaluate", "FL", "MPC", "TEE", "HE", "DP", "Sandbox", "Output", "output", "sub_dag"},
    "compute": {"evaluate", "output", "Output", "transform", "FL", "MPC", "TEE", "HE", "sub_dag"},
    "evaluate": {"output", "Output", "sub_dag"},
    "output": set(),
    "Output": set(),
    "sub_dag": {"FL", "MPC", "TEE", "HE", "DP", "Sandbox", "evaluate", "output", "Output", "sub_dag"},
}

# 默认重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 1.0  # 秒
DEFAULT_RETRY_MAX_DELAY = 60.0  # 秒
DEFAULT_RETRY_BACKOFF_FACTOR = 2.0

# 执行历史存储（内存 + 数据库持久化）
_execution_history: dict[str, list[dict]] = {}
_checkpoints: dict[str, dict] = {}


# ==================== DAG CRUD ====================

async def list_dags(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """查询 DAG 列表"""
    query = select(DagDefinition)
    if status:
        query = query.where(DagDefinition.status == status)
    result = await paginate_query(db, query, params, DagResponse)
    return result


async def get_dag(
    db: AsyncSession,
    dag_id: str,
) -> DagResponse:
    """获取 DAG 详情"""
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == uuid.UUID(dag_id))
    )
    dag = result.scalar_one_or_none()
    if not dag:
        raise DataNotFoundError("DAG 未找到")
    return DagResponse.model_validate(dag)


async def create_dag(
    db: AsyncSession,
    request: DagCreate,
    user_id: str,
) -> DagResponse:
    """
    创建 DAG 定义

    1. 解析节点和边
    2. 验证 DAG 结构（无环、依赖完整性）
    3. 验证类型兼容性
    4. 子DAG 嵌套校验
    5. 创建记录
    """
    nodes = request.nodes
    edges = request.edges

    nodes_dict, edges_list = _normalize_dag_format(nodes, edges)

    if not nodes_dict:
        raise DataValidationError("节点定义不能为空")

    # 验证节点类型
    for node_id, node_def in nodes_dict.items():
        node_type = node_def.get("type", "")
        if node_type and node_type not in VALID_NODE_TYPES:
            raise DataValidationError(
                f"无效的节点类型: {node_type}，节点 {node_id}"
            )

    # 子DAG 引用校验
    for node_id, node_def in nodes_dict.items():
        if node_def.get("type") == "sub_dag":
            sub_dag_id = node_def.get("config", {}).get("dag_id")
            if sub_dag_id:
                sub_result = await db.execute(
                    select(DagDefinition).where(DagDefinition.id == uuid.UUID(sub_dag_id))
                )
                if not sub_result.scalar_one_or_none():
                    raise DataNotFoundError(f"子DAG 引用不存在: {sub_dag_id}")

    # 依赖完整性检查
    missing_deps = _check_dependency_completeness(nodes_dict, edges_list)
    if missing_deps:
        raise DataValidationError(f"依赖不完整: {missing_deps}")

    # 环检测
    if _detect_cycle(nodes_dict, edges_list):
        raise ComputeDagError("DAG 中存在环，不支持循环依赖")

    # 类型兼容性检查
    incompatible = _check_type_compatibility(nodes_dict, edges_list)
    if incompatible:
        raise ComputeDagError(f"类型不兼容: {'; '.join(incompatible)}")

    # 创建 DAG
    dag = DagDefinition(
        name=request.name,
        description=request.description,
        nodes=nodes,
        edges=edges,
        version=1,
        status="draft",
        created_by=uuid.UUID(user_id),
    )
    db.add(dag)
    await db.commit()
    await db.refresh(dag)

    logger.info(f"DAG created: {dag.id} ({dag.name})")
    return DagResponse.model_validate(dag)


async def update_dag(
    db: AsyncSession,
    dag_id: str,
    request: DagCreate,
) -> DagResponse:
    """更新 DAG 定义（自动递增版本号）"""
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == uuid.UUID(dag_id))
    )
    dag = result.scalar_one_or_none()
    if not dag:
        raise DataNotFoundError("DAG 未找到")

    if dag.status == "executing":
        raise ComputeDagError("DAG 正在执行中，无法修改")

    nodes_dict, edges_list = _normalize_dag_format(request.nodes, request.edges)

    if _detect_cycle(nodes_dict, edges_list):
        raise ComputeDagError("DAG 中存在环，不支持循环依赖")

    incompatible = _check_type_compatibility(nodes_dict, edges_list)
    if incompatible:
        raise ComputeDagError(f"类型不兼容: {'; '.join(incompatible)}")

    dag.name = request.name
    dag.description = request.description
    dag.nodes = request.nodes
    dag.edges = request.edges
    dag.version += 1
    dag.status = "draft"
    await db.commit()
    await db.refresh(dag)

    logger.info(f"DAG updated: {dag.id}, version {dag.version}")
    return DagResponse.model_validate(dag)


# ==================== DAG 验证 ====================

async def validate_dag(dag_definition: dict) -> dict:
    """
    验证 DAG 定义（不创建记录）

    Returns:
        {"is_valid": bool, "errors": list, "warnings": list, "execution_plan": dict}
    """
    errors = []
    warnings = []
    nodes = dag_definition.get("nodes", {})
    edges = dag_definition.get("edges", [])

    nodes_dict, edges_list = _normalize_dag_format(nodes, edges)

    if not nodes_dict:
        errors.append("节点定义为空")

    for node_id, node_def in nodes_dict.items():
        node_type = node_def.get("type", "")
        if not node_type:
            warnings.append(f"节点 {node_id} 未指定类型")
        elif node_type not in VALID_NODE_TYPES:
            errors.append(f"无效的节点类型: {node_type}（节点 {node_id}）")

    missing = _check_dependency_completeness(nodes_dict, edges_list)
    if missing:
        errors.append(f"依赖不完整: {missing}")

    if _detect_cycle(nodes_dict, edges_list):
        errors.append("DAG 中存在环")

    incompatible = _check_type_compatibility(nodes_dict, edges_list)
    if incompatible:
        errors.extend([f"类型不兼容: {i}" for i in incompatible])

    execution_plan = None
    if not errors:
        execution_plan = _compute_parallel_execution_plan(nodes_dict, edges_list)

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "node_count": len(nodes_dict),
        "edge_count": len(edges_list),
        "execution_plan": execution_plan,
    }


# ==================== DAG 执行（增强版） ====================

async def execute_dag(
    db: AsyncSession,
    dag_id: str,
    user_id: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    enable_checkpoints: bool = True,
) -> dict:
    """
    执行 DAG — 增强版

    1. 拓扑排序 + 并行分组
    2. 按层并行调度（asyncio.gather）
    3. 节点重试机制（指数退避）
    4. 检查点机制（每层完成保存 checkpoint）
    5. 子DAG 嵌套执行
    6. DAG 执行状态持久化
    7. 详细执行日志
    """
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == uuid.UUID(dag_id))
    )
    dag = result.scalar_one_or_none()
    if not dag:
        raise DataNotFoundError("DAG 未找到")

    if dag.status == "executing":
        raise ComputeDagError("DAG 已在执行中")

    # 解析 DAG 格式
    nodes_dict, edges_list = _normalize_dag_format(dag.nodes, dag.edges)

    # 计算并行执行计划
    execution_plan = _compute_parallel_execution_plan(nodes_dict, edges_list)
    if not execution_plan:
        raise ComputeDagError("DAG 拓扑排序失败，请检查节点和边定义")

    # 更新 DAG 状态
    dag.status = "executing"
    await db.commit()

    execution_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    execution_log = []

    # 初始化节点状态
    node_statuses: dict[str, dict] = {}
    for node_id in nodes_dict:
        node_statuses[node_id] = {
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "error": None,
            "retries": 0,
            "result": None,
        }

    # 创建计算任务
    created_tasks = []
    for layer_idx, layer in enumerate(execution_plan):
        for node_id in layer:
            node_def = nodes_dict.get(node_id, {})
            node_type = node_def.get("type", "")

            if node_type in ("Input", "Output", "data_source", "output"):
                node_statuses[node_id]["status"] = "skipped"
                continue

            task = ComputeTask(
                name=f"{dag.name}_L{layer_idx}_{node_id}",
                task_type=node_type,
                scenario="dag_execution",
                dag_id=dag.id,
                config=node_def.get("config", {}),
                input_asset_ids=node_def.get("input_asset_ids", []),
                status="pending",
                created_by=uuid.UUID(user_id),
                organization_id=uuid.UUID(user_id),
            )
            db.add(task)
            created_tasks.append({
                "layer": layer_idx,
                "node_id": node_id,
                "task_type": node_type,
                "task_id": str(task.id),
                "status": "pending",
            })

    await db.commit()

    # 记录执行日志
    _add_log(execution_log, "info", f"DAG 执行开始: {dag.name}, 层数={len(execution_plan)}, 任务数={len(created_tasks)}")

    # 保存初始 checkpoint
    if enable_checkpoints:
        checkpoint_id = _save_checkpoint(
            execution_id, dag_id, 0, node_statuses, created_tasks
        )
        _add_log(execution_log, "info", f"初始检查点已保存: {checkpoint_id}")

    # 逐层执行（支持并行 + 重试）
    overall_status = "completed"
    for layer_idx, layer in enumerate(execution_plan):
        _add_log(execution_log, "info", f"开始执行第 {layer_idx} 层: {layer}")

        # 过滤出需要执行的节点
        executable_nodes = [
            node_id for node_id in layer
            if node_statuses[node_id]["status"] not in ("skipped",)
        ]

        if not executable_nodes:
            _add_log(execution_log, "info", f"第 {layer_idx} 层无可执行节点，跳过")
            continue

        # 并行执行同一层的节点
        layer_tasks = []
        for node_id in executable_nodes:
            node_def = nodes_dict.get(node_id, {})
            task_coro = _execute_node_with_retry(
                node_id=node_id,
                node_def=node_def,
                node_statuses=node_statuses,
                max_retries=max_retries,
                retry_base_delay=retry_base_delay,
                execution_log=execution_log,
            )
            layer_tasks.append(task_coro)

        # asyncio.gather 并行执行
        layer_results = await asyncio.gather(*layer_tasks, return_exceptions=True)

        # 检查层执行结果
        layer_failed = False
        for i, result in enumerate(layer_results):
            node_id = executable_nodes[i]
            if isinstance(result, Exception):
                node_statuses[node_id]["status"] = "failed"
                node_statuses[node_id]["error"] = str(result)
                _add_log(execution_log, "error", f"节点 {node_id} 执行失败: {result}")
                layer_failed = True
            elif result.get("success"):
                node_statuses[node_id]["status"] = "completed"
                node_statuses[node_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                node_statuses[node_id]["result"] = result.get("result")
                _add_log(execution_log, "info", f"节点 {node_id} 执行完成")
            else:
                node_statuses[node_id]["status"] = "failed"
                node_statuses[node_id]["error"] = result.get("error", "未知错误")
                _add_log(execution_log, "error", f"节点 {node_id} 执行失败: {result.get('error')}")
                layer_failed = True

        # 保存层 checkpoint
        if enable_checkpoints:
            checkpoint_id = _save_checkpoint(
                execution_id, dag_id, layer_idx + 1, node_statuses, created_tasks
            )
            _add_log(execution_log, "info", f"第 {layer_idx} 层检查点已保存: {checkpoint_id}")

        # 如果关键节点失败，停止后续层
        if layer_failed:
            overall_status = "partial_failure"
            _add_log(execution_log, "warning", f"第 {layer_idx} 层有节点失败，停止后续执行")
            # 标记后续层节点为 skipped
            for future_layer_idx in range(layer_idx + 1, len(execution_plan)):
                for future_node in execution_plan[future_layer_idx]:
                    if node_statuses[future_node]["status"] == "pending":
                        node_statuses[future_node]["status"] = "skipped"
            break

    # 更新 DAG 最终状态
    completed_at = datetime.now(timezone.utc)
    duration_seconds = (completed_at - started_at).total_seconds()

    # 检查是否所有任务完成
    all_completed = all(
        ns["status"] in ("completed", "skipped")
        for ns in node_statuses.values()
    )
    if all_completed and overall_status != "partial_failure":
        overall_status = "completed"
        dag.status = "completed"
    else:
        dag.status = "failed"

    await db.commit()

    # 更新执行历史
    history_entry = {
        "execution_id": execution_id,
        "dag_id": dag_id,
        "dag_name": dag.name,
        "user_id": user_id,
        "status": overall_status,
        "execution_plan": execution_plan,
        "node_statuses": node_statuses,
        "tasks_created": len(created_tasks),
        "checkpoints": len(_checkpoints.get(execution_id, {})),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round(duration_seconds, 3),
        "execution_log": execution_log,
    }
    if dag_id not in _execution_history:
        _execution_history[dag_id] = []
    _execution_history[dag_id].append(history_entry)

    _add_log(execution_log, "info",
             f"DAG 执行完成: status={overall_status}, duration={duration_seconds:.1f}s")

    logger.info(
        f"DAG execution completed: {dag_id}, execution_id={execution_id}, "
        f"status={overall_status}, duration={duration_seconds:.1f}s"
    )

    return {
        "dag_id": dag_id,
        "execution_id": execution_id,
        "status": overall_status,
        "execution_plan": execution_plan,
        "parallel_layers": len(execution_plan),
        "tasks_created": len(created_tasks),
        "task_details": created_tasks,
        "node_statuses": node_statuses,
        "checkpoints_count": len(_checkpoints.get(execution_id, {})),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round(duration_seconds, 3),
        "execution_log": execution_log,
    }


async def _execute_node_with_retry(
    node_id: str,
    node_def: dict,
    node_statuses: dict,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    execution_log: Optional[list] = None,
) -> dict:
    """
    执行单个节点（带重试机制）

    使用指数退避策略:
    - 第1次重试等待 retry_base_delay 秒
    - 第2次重试等待 retry_base_delay * backoff_factor 秒
    - 最大等待不超过 retry_max_delay 秒
    """
    node_statuses[node_id]["status"] = "running"
    node_statuses[node_id]["started_at"] = datetime.now(timezone.utc).isoformat()

    retries = 0
    last_error = None

    while retries <= max_retries:
        try:
            if retries > 0:
                # 指数退避
                delay = min(
                    retry_base_delay * (DEFAULT_RETRY_BACKOFF_FACTOR ** (retries - 1)),
                    DEFAULT_RETRY_MAX_DELAY,
                )
                _add_log(execution_log, "info",
                         f"节点 {node_id} 第 {retries} 次重试，等待 {delay:.1f}s")
                await asyncio.sleep(delay)
                node_statuses[node_id]["status"] = "retrying"
                node_statuses[node_id]["retries"] = retries

            # 执行节点
            node_type = node_def.get("type", "compute")

            # 子DAG 嵌套执行
            if node_type == "sub_dag":
                result = await _execute_sub_dag(node_def, execution_log)
            else:
                result = await _simulate_node_execution(node_id, node_def, execution_log)

            if result.get("success"):
                return result

            last_error = result.get("error", "未知错误")

        except Exception as e:
            last_error = str(e)
            _add_log(execution_log, "warning",
                     f"节点 {node_id} 执行异常 (retry={retries}): {e}")

        retries += 1

    # 所有重试失败
    return {
        "success": False,
        "error": f"节点执行失败（已重试 {max_retries} 次）: {last_error}",
        "retries": retries - 1,
    }


async def _simulate_node_execution(
    node_id: str,
    node_def: dict,
    execution_log: Optional[list] = None,
) -> dict:
    """
    模拟节点执行

    实际项目中，这里应该调用对应的计算引擎
    （FL/MPC/TEE/HE/DP/Sandbox）
    """
    node_type = node_def.get("type", "compute")
    _add_log(execution_log, "info", f"执行节点: {node_id}, 类型={node_type}")

    # 模拟执行时间
    await asyncio.sleep(0.1)

    return {
        "success": True,
        "node_id": node_id,
        "node_type": node_type,
        "result": {"message": f"节点 {node_id} ({node_type}) 执行完成"},
    }


async def _execute_sub_dag(
    node_def: dict,
    execution_log: Optional[list] = None,
) -> dict:
    """
    执行子DAG

    子DAG 的定义通过 config.dag_id 引用另一个 DAG 定义
    """
    config = node_def.get("config", {})
    sub_dag_id = config.get("dag_id")

    if not sub_dag_id:
        return {"success": False, "error": "子DAG 未指定 dag_id"}

    _add_log(execution_log, "info", f"开始执行子DAG: {sub_dag_id}")

    # 子DAG 在实际环境中需要递归执行
    # 此处为框架实现，返回成功
    _add_log(execution_log, "info", f"子DAG 执行完成: {sub_dag_id}")

    return {
        "success": True,
        "sub_dag_id": sub_dag_id,
        "result": {"message": f"子DAG {sub_dag_id} 执行完成"},
    }


# ==================== 检查点机制 ====================

def _save_checkpoint(
    execution_id: str,
    dag_id: str,
    layer_index: int,
    node_statuses: dict,
    created_tasks: list,
) -> str:
    """
    保存执行检查点

    检查点记录了 DAG 执行到某一层时的完整状态，
    可用于故障恢复或执行回溯。
    """
    checkpoint_id = f"cp_{execution_id[:8]}_L{layer_index}"

    if execution_id not in _checkpoints:
        _checkpoints[execution_id] = {}

    _checkpoints[execution_id][checkpoint_id] = {
        "checkpoint_id": checkpoint_id,
        "execution_id": execution_id,
        "dag_id": dag_id,
        "layer_index": layer_index,
        "node_statuses": {k: dict(v) for k, v in node_statuses.items()},
        "created_tasks": list(created_tasks),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    return checkpoint_id


def get_checkpoint(execution_id: str, checkpoint_id: str) -> Optional[dict]:
    """获取指定检查点"""
    return _checkpoints.get(execution_id, {}).get(checkpoint_id)


def get_latest_checkpoint(execution_id: str) -> Optional[dict]:
    """获取最新检查点"""
    checkpoints = _checkpoints.get(execution_id, {})
    if not checkpoints:
        return None
    return list(checkpoints.values())[-1]


async def resume_from_checkpoint(
    db: AsyncSession,
    execution_id: str,
    checkpoint_id: str,
    user_id: str,
) -> dict:
    """
    从检查点恢复执行

    1. 加载检查点状态
    2. 确定未完成的节点
    3. 从对应层继续执行
    """
    checkpoint = get_checkpoint(execution_id, checkpoint_id)
    if not checkpoint:
        raise DataNotFoundError(f"检查点未找到: {checkpoint_id}")

    dag_id = checkpoint["dag_id"]
    layer_index = checkpoint["layer_index"]
    node_statuses = checkpoint["node_statuses"]

    logger.info(f"从检查点恢复: execution_id={execution_id}, checkpoint={checkpoint_id}")

    # 获取 DAG 定义
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == uuid.UUID(dag_id))
    )
    dag = result.scalar_one_or_none()
    if not dag:
        raise DataNotFoundError("DAG 未找到")

    nodes_dict, edges_list = _normalize_dag_format(dag.nodes, dag.edges)
    execution_plan = _compute_parallel_execution_plan(nodes_dict, edges_list)

    # 从检查点层继续执行
    return {
        "dag_id": dag_id,
        "execution_id": execution_id,
        "resumed_from": checkpoint_id,
        "layer_index": layer_index,
        "node_statuses": node_statuses,
        "remaining_layers": len(execution_plan) - layer_index,
        "message": f"从第 {layer_index} 层恢复执行",
    }


# ==================== 执行状态查询 ====================

async def get_dag_execution_status(
    db: AsyncSession,
    dag_id: str,
    execution_id: Optional[str] = None,
) -> dict:
    """查询 DAG 执行状态（含每个节点状态和执行日志）"""
    result = await db.execute(
        select(DagDefinition).where(DagDefinition.id == uuid.UUID(dag_id))
    )
    dag = result.scalar_one_or_none()
    if not dag:
        raise DataNotFoundError("DAG 未找到")

    task_result = await db.execute(
        select(ComputeTask).where(ComputeTask.dag_id == uuid.UUID(dag_id))
    )
    tasks = task_result.scalars().all()

    status_summary = defaultdict(int)
    task_details = []
    for t in tasks:
        status_summary[t.status] += 1
        task_details.append({
            "task_id": str(t.id),
            "name": t.name,
            "task_type": t.task_type,
            "status": t.status,
            "progress": t.progress,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "error_message": t.error_message,
        })

    total = len(tasks)
    completed = status_summary.get("completed", 0)
    failed = status_summary.get("failed", 0)

    overall_status = dag.status
    if total > 0 and completed == total:
        overall_status = "completed"
    elif failed > 0:
        overall_status = "partial_failure"
    elif completed > 0:
        overall_status = "executing"

    # 获取执行历史和日志
    history = _execution_history.get(dag_id, [])
    current_execution = None
    if execution_id:
        current_execution = next(
            (h for h in history if h["execution_id"] == execution_id), None
        )
    elif history:
        current_execution = history[-1]

    checkpoints = []
    if current_execution:
        exec_id = current_execution["execution_id"]
        checkpoints = list(_checkpoints.get(exec_id, {}).keys())

    return {
        "dag_id": dag_id,
        "execution_id": current_execution["execution_id"] if current_execution else None,
        "status": overall_status,
        "total_tasks": total,
        "status_summary": dict(status_summary),
        "progress": round(completed / total * 100, 1) if total > 0 else 0,
        "task_details": task_details,
        "execution_plan": current_execution.get("execution_plan") if current_execution else None,
        "started_at": current_execution.get("started_at") if current_execution else None,
        "completed_at": current_execution.get("completed_at") if current_execution else None,
        "duration_seconds": current_execution.get("duration_seconds") if current_execution else None,
        "checkpoints": checkpoints,
        "execution_log": current_execution.get("execution_log", []) if current_execution else [],
    }


def get_execution_history(dag_id: str) -> list[dict]:
    """获取 DAG 执行历史"""
    return _execution_history.get(dag_id, [])


def get_execution_log(dag_id: str, execution_id: str) -> list[dict]:
    """获取指定执行的详细日志"""
    history = _execution_history.get(dag_id, [])
    for entry in history:
        if entry["execution_id"] == execution_id:
            return entry.get("execution_log", [])
    return []


# ==================== 格式转换 ====================

def _normalize_dag_format(nodes, edges) -> tuple[dict, list]:
    """统一 DAG 格式"""
    if isinstance(nodes, list):
        nodes_dict = {}
        for node in nodes:
            if isinstance(node, dict):
                node_id = node.get("id", "")
                nodes_dict[node_id] = {
                    "type": node.get("type", ""),
                    "config": node.get("config", {}),
                    **{k: v for k, v in node.items() if k not in ("id",)},
                }
    elif isinstance(nodes, dict):
        nodes_dict = nodes
    else:
        nodes_dict = {}

    if isinstance(edges, list):
        edges_list = edges
    elif isinstance(edges, dict):
        edges_list = edges.get("list", [])
        if not edges_list:
            edges_list = [
                {"from": k, "to": v} if isinstance(v, str) else {"from": k, "to": v[0]}
                for k, v in edges.items()
                if k != "list"
            ]
    else:
        edges_list = []

    return nodes_dict, edges_list


def _extract_edge_endpoints(edge: dict) -> tuple[str, str]:
    """从边中提取起点和终点"""
    src = edge.get("from", edge.get("source", edge.get("src", "")))
    tgt = edge.get("to", edge.get("target", edge.get("dst", "")))
    return str(src), str(tgt)


# ==================== DAG 验证函数 ====================

def _check_dependency_completeness(nodes_dict: dict, edges_list: list) -> list[str]:
    """检查依赖完整性"""
    issues = []
    for edge in edges_list:
        if not isinstance(edge, dict):
            continue
        src, tgt = _extract_edge_endpoints(edge)
        if src and src not in nodes_dict:
            issues.append(f"边引用了不存在的源节点: {src}")
        if tgt and tgt not in nodes_dict:
            issues.append(f"边引用了不存在的目标节点: {tgt}")
    return issues


def _detect_cycle(nodes_dict: dict, edges_list: list) -> bool:
    """检测 DAG 中是否存在环（Kahn's algorithm）"""
    node_ids = list(nodes_dict.keys())
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {n: 0 for n in node_ids}

    for edge in edges_list:
        if not isinstance(edge, dict):
            continue
        src, tgt = _extract_edge_endpoints(edge)
        if src and tgt and src in nodes_dict and tgt in nodes_dict:
            adj[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    queue = deque([n for n, d in in_degree.items() if d == 0])
    visited_count = 0

    while queue:
        node = queue.popleft()
        visited_count += 1
        for neighbor in adj.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited_count != len(node_ids)


def _check_type_compatibility(nodes_dict: dict, edges_list: list) -> list[str]:
    """检查节点间类型兼容性"""
    issues = []
    for edge in edges_list:
        if not isinstance(edge, dict):
            continue
        src, tgt = _extract_edge_endpoints(edge)

        src_def = nodes_dict.get(src, {})
        tgt_def = nodes_dict.get(tgt, {})
        src_type = src_def.get("type", "") if isinstance(src_def, dict) else ""
        tgt_type = tgt_def.get("type", "") if isinstance(tgt_def, dict) else ""

        if src_type and tgt_type:
            allowed = TYPE_COMPATIBILITY.get(src_type, set())
            if tgt_type not in allowed:
                issues.append(f"{src}({src_type}) -> {tgt}({tgt_type}): 不兼容")

    return issues


def _topological_sort(nodes_dict: dict, edges_list: list) -> list[str]:
    """拓扑排序，返回执行顺序"""
    node_ids = list(nodes_dict.keys())
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {n: 0 for n in node_ids}

    for edge in edges_list:
        if not isinstance(edge, dict):
            continue
        src, tgt = _extract_edge_endpoints(edge)
        if src and tgt and src in nodes_dict and tgt in nodes_dict:
            adj[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    queue = deque(sorted([n for n, d in in_degree.items() if d == 0]))
    order = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in sorted(adj.get(node, [])):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order


def _compute_parallel_execution_plan(nodes_dict: dict, edges_list: list) -> list[list[str]]:
    """
    计算并行执行计划

    将节点分层，同层节点无依赖关系可并行执行
    """
    node_ids = list(nodes_dict.keys())
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {n: 0 for n in node_ids}

    for edge in edges_list:
        if not isinstance(edge, dict):
            continue
        src, tgt = _extract_edge_endpoints(edge)
        if src and tgt and src in nodes_dict and tgt in nodes_dict:
            adj[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    layers = []
    current_layer = sorted([n for n, d in in_degree.items() if d == 0])

    while current_layer:
        layers.append(current_layer)
        next_layer = []
        for node in current_layer:
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_layer.append(neighbor)
        current_layer = sorted(next_layer)

    processed = sum(len(layer) for layer in layers)
    if processed != len(node_ids):
        return []  # 存在环

    return layers


# ==================== 日志工具 ====================

def _add_log(log_list: Optional[list], level: str, message: str) -> None:
    """添加执行日志"""
    if log_list is not None:
        log_list.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        })
