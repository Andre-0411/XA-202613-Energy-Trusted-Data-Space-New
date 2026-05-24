"""
计算集群节点管理服务
节点注册/心跳/任务派发/集群状态 - 基于内存状态管理
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.schemas.compute import (
    ClusterNodeCreate, ClusterNodeUpdate, ClusterNodeResponse,
    ClusterStatus, ClusterDispatchRequest, ClusterDispatchResponse,
    NodeHeartbeat, NodeCapabilities,
)
from app.exceptions import DataNotFoundError, DataValidationError, ComputeError

logger = logging.getLogger(__name__)

# 内存存储: node_id -> node_data
_nodes: dict[str, dict] = {}

# 心跳超时时间(秒)
HEARTBEAT_TIMEOUT = 60

# 派发记录: dispatch_id -> dispatch_data
_dispatches: dict[str, dict] = {}


def _node_to_response(node: dict) -> ClusterNodeResponse:
    return ClusterNodeResponse(
        node_id=node["node_id"],
        name=node["name"],
        node_type=node["node_type"],
        endpoint=node["endpoint"],
        region=node.get("region"),
        organization_id=node.get("organization_id"),
        status=node["status"],
        capabilities=NodeCapabilities(**node["capabilities"]),
        active_tasks=node["active_tasks"],
        last_heartbeat=node.get("last_heartbeat"),
        registered_at=node["registered_at"],
        metadata=node.get("metadata", {}),
    )


def _check_heartbeat_timeout(node: dict) -> None:
    """检查心跳超时，将超时节点标记为离线"""
    if node["status"] == "online" and node.get("last_heartbeat"):
        timeout = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT)
        if node["last_heartbeat"] < timeout:
            node["status"] = "offline"
            logger.warning(f"Node {node['node_id']} heartbeat timeout, marked offline")


async def register_node(request: ClusterNodeCreate) -> ClusterNodeResponse:
    """
    注册新集群节点

    1. 检查 endpoint 是否已注册
    2. 生成 node_id
    3. 保存节点信息
    """
    # 检查 endpoint 唯一性
    for node in _nodes.values():
        if node["endpoint"] == request.endpoint and node["status"] != "disabled":
            raise DataValidationError(f"节点地址 {request.endpoint} 已被注册")

    node_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    node = {
        "node_id": node_id,
        "name": request.name,
        "node_type": request.node_type,
        "endpoint": request.endpoint,
        "region": request.region,
        "organization_id": request.organization_id,
        "status": "online",
        "capabilities": request.capabilities.model_dump(),
        "active_tasks": 0,
        "last_heartbeat": now,
        "registered_at": now,
        "metadata": request.metadata,
    }
    _nodes[node_id] = node

    logger.info(f"Cluster node registered: {node_id} ({request.name}), type={request.node_type}")
    return _node_to_response(node)


async def list_nodes(
    node_type: Optional[str] = None,
    status: Optional[str] = None,
    region: Optional[str] = None,
) -> list[ClusterNodeResponse]:
    """列出所有集群节点"""
    # 先检查心跳超时
    for node in _nodes.values():
        _check_heartbeat_timeout(node)

    results = []
    for node in _nodes.values():
        if node_type and node["node_type"] != node_type:
            continue
        if status and node["status"] != status:
            continue
        if region and node.get("region") != region:
            continue
        results.append(_node_to_response(node))
    return results


async def get_node(node_id: str) -> ClusterNodeResponse:
    """获取节点详情"""
    node = _nodes.get(node_id)
    if not node:
        raise DataNotFoundError(f"集群节点未找到: {node_id}")
    _check_heartbeat_timeout(node)
    return _node_to_response(node)


async def update_node(node_id: str, request: ClusterNodeUpdate) -> ClusterNodeResponse:
    """更新节点信息"""
    node = _nodes.get(node_id)
    if not node:
        raise DataNotFoundError(f"集群节点未找到: {node_id}")

    if node["status"] == "disabled":
        raise DataValidationError("已禁用的节点不可修改")

    if request.name is not None:
        node["name"] = request.name
    if request.node_type is not None:
        node["node_type"] = request.node_type
    if request.endpoint is not None:
        # 检查新 endpoint 唯一性
        for other in _nodes.values():
            if other["node_id"] != node_id and other["endpoint"] == request.endpoint and other["status"] != "disabled":
                raise DataValidationError(f"节点地址 {request.endpoint} 已被注册")
        node["endpoint"] = request.endpoint
    if request.region is not None:
        node["region"] = request.region
    if request.capabilities is not None:
        node["capabilities"] = request.capabilities.model_dump()
    if request.metadata is not None:
        node["metadata"] = request.metadata

    logger.info(f"Cluster node updated: {node_id}")
    return _node_to_response(node)


async def delete_node(node_id: str) -> None:
    """移除节点 (标记为 disabled)"""
    node = _nodes.get(node_id)
    if not node:
        raise DataNotFoundError(f"集群节点未找到: {node_id}")

    if node["active_tasks"] > 0:
        raise DataValidationError(f"节点 {node_id} 仍有 {node['active_tasks']} 个活跃任务，无法移除")

    node["status"] = "disabled"
    logger.info(f"Cluster node disabled: {node_id}")


async def heartbeat(node_id: str, hb: NodeHeartbeat) -> ClusterNodeResponse:
    """
    处理节点心跳

    1. 更新节点状态和心跳时间
    2. 更新活跃任务数
    """
    node = _nodes.get(node_id)
    if not node:
        raise DataNotFoundError(f"集群节点未找到: {node_id}")

    if node["status"] == "disabled":
        raise DataValidationError("已禁用的节点不可发送心跳")

    now = datetime.now(timezone.utc)
    node["status"] = hb.status
    node["active_tasks"] = hb.active_tasks
    node["last_heartbeat"] = now
    node["metadata"]["cpu_usage"] = hb.cpu_usage
    node["metadata"]["memory_usage"] = hb.memory_usage
    node["metadata"]["gpu_usage"] = hb.gpu_usage

    return _node_to_response(node)


async def get_cluster_status() -> ClusterStatus:
    """获取集群整体状态"""
    # 先更新心跳状态
    for node in _nodes.values():
        _check_heartbeat_timeout(node)

    total = len(_nodes)
    online = sum(1 for n in _nodes.values() if n["status"] == "online")
    offline = sum(1 for n in _nodes.values() if n["status"] == "offline")
    disabled = sum(1 for n in _nodes.values() if n["status"] == "disabled")
    total_active = sum(n["active_tasks"] for n in _nodes.values() if n["status"] != "disabled")

    # 汇总可用容量
    available_cpu = 0
    available_memory = 0
    available_gpu = 0
    for n in _nodes.values():
        if n["status"] == "online":
            caps = n["capabilities"]
            available_cpu += caps.get("cpu_cores", 0)
            available_memory += caps.get("memory_mb", 0)
            available_gpu += caps.get("gpu_count", 0)

    return ClusterStatus(
        total_nodes=total,
        online_nodes=online,
        offline_nodes=offline,
        disabled_nodes=disabled,
        total_active_tasks=total_active,
        available_capacity={
            "cpu_cores": available_cpu,
            "memory_mb": available_memory,
            "gpu_count": available_gpu,
        },
        nodes=[_node_to_response(n) for n in _nodes.values()],
    )


async def dispatch_task(request: ClusterDispatchRequest) -> ClusterDispatchResponse:
    """
    派发任务到可用节点

    1. 如指定首选节点，优先使用
    2. 否则按能力匹配 + 负载均衡选择节点
    3. 记录派发结果
    """
    dispatch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 先更新心跳状态
    for node in _nodes.values():
        _check_heartbeat_timeout(node)

    target_node = None

    # 1. 指定首选节点
    if request.preferred_node_id:
        node = _nodes.get(request.preferred_node_id)
        if not node:
            raise DataNotFoundError(f"首选节点未找到: {request.preferred_node_id}")
        if node["status"] != "online":
            raise ComputeError(f"首选节点 {request.preferred_node_id} 不在线")
        caps = node["capabilities"]
        max_concurrent = caps.get("max_concurrent_tasks", 1)
        if node["active_tasks"] >= max_concurrent:
            raise ComputeError(f"首选节点 {request.preferred_node_id} 已达最大并发数")
        target_node = node

    # 2. 自动选择节点 (能力匹配 + 最少任务优先)
    if not target_node:
        candidates = []
        for node in _nodes.values():
            if node["status"] != "online":
                continue
            caps = node["capabilities"]
            max_concurrent = caps.get("max_concurrent_tasks", 1)
            if node["active_tasks"] >= max_concurrent:
                continue
            # 检查是否支持任务类型
            supported = caps.get("supported_types", [])
            if supported and request.task_type not in supported:
                continue
            candidates.append(node)

        if not candidates:
            # 派发失败，记录并返回
            dispatch = {
                "dispatch_id": dispatch_id,
                "task_id": request.task_id,
                "node_id": None,
                "node_endpoint": None,
                "status": "failed",
                "dispatched_at": now,
            }
            _dispatches[dispatch_id] = dispatch
            raise ComputeError("没有可用的节点来派发任务")

        # 最少任务优先
        candidates.sort(key=lambda n: n["active_tasks"])
        target_node = candidates[0]

    # 3. 记录派发
    target_node["active_tasks"] += 1
    dispatch = {
        "dispatch_id": dispatch_id,
        "task_id": request.task_id,
        "node_id": target_node["node_id"],
        "node_endpoint": target_node["endpoint"],
        "status": "dispatched",
        "dispatched_at": now,
    }
    _dispatches[dispatch_id] = dispatch

    logger.info(
        f"Task dispatched: {request.task_id} -> node {target_node['node_id']} "
        f"({target_node['name']}), dispatch_id={dispatch_id}"
    )
    return ClusterDispatchResponse(
        dispatch_id=dispatch_id,
        task_id=request.task_id,
        node_id=target_node["node_id"],
        node_endpoint=target_node["endpoint"],
        status="dispatched",
        dispatched_at=now,
    )
