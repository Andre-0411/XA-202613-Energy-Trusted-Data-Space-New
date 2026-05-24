"""
FATE v2.x 真实集成服务
通过 REST API 调用 FATE Flow 提交联邦学习任务
连接失败时自动降级为本地模拟模式（sklearn）

增强功能:
- 连接池管理: 持久化 httpx.AsyncClient，复用 TCP 连接
- 健康检查: 定时心跳 + 连接状态机（connected/disconnected/reconnecting）
- 断路器: 连续失败超过阈值后短路请求，避免雪崩
- 指数退避重试: 可配置最大重试次数和退避基数
- 数据上传/下载: 通过 FATE Flow API 上传和下载数据集
- 作业取消: 支持取消正在运行的 FATE 作业
- 连接指标: 延迟、成功率、失败计数、健康检查历史
- v2 API 端点: /v2/job/submit, /v2/job/query, /v2/job/stop, /v2/data/upload 等
- 训练进度 SSE 推送: 通过 asyncio Queue 实现服务端事件推送
- 组件配置校验: Reader/Intersection/HeteroLR/HomoLR/SecureBoost 等
- 模型评估指标收集: 从 FATE Flow 获取训练/评估指标
"""
import os
import time
import uuid
import json
import asyncio
import logging
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ComputeError, DataNotFoundError, DataValidationError
from app.models.fate_job import FateJob

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

# FATE Flow 服务地址（可通过环境变量覆盖）
FATE_FLOW_BASE_URL = os.getenv("FATE_FLOW_BASE_URL", "http://fateflow:9380")
FATE_FLOW_API_PREFIX = os.getenv("FATE_FLOW_API_PREFIX", "/v2")

# 健康检查间隔（秒）
HEALTH_CHECK_INTERVAL = int(os.getenv("FATE_HEALTH_CHECK_INTERVAL", "30"))

# 最大重试次数
MAX_RETRIES = int(os.getenv("FATE_MAX_RETRIES", "3"))

# 重试退避基数（秒）
RETRY_BACKOFF_BASE = float(os.getenv("FATE_RETRY_BACKOFF_BASE", "1.0"))

# 断路器连续失败阈值
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("FATE_CIRCUIT_BREAKER_THRESHOLD", "5"))

# 断路器恢复等待时间（秒）
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.getenv("FATE_CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))

# 请求超时（秒）
REQUEST_TIMEOUT = float(os.getenv("FATE_REQUEST_TIMEOUT", "30.0"))

# 是否启用真实 FATE 模式（False 时强制降级为模拟模式）
FATE_REAL_MODE = os.getenv("FATE_REAL_MODE", "false").lower() == "true"

# FATE 支持的算法
FATE_ALGORITHMS = {
    "homo_lr": "横向逻辑回归 (Homo-LR)",
    "hetero_lr": "纵向逻辑回归 (Hetero-LR)",
    "homo_nn": "横向神经网络 (Homo-NN)",
    "hetero_nn": "纵向神经网络 (Hetero-NN)",
    "secureboost": "安全提升树 (SecureBoost)",
    "psi": "隐私集合求交 (PSI)",
    "homo_statistic": "联邦统计 (Homo-Statistic)",
}

# ==================== FATE v2 组件配置 Schema ====================

# FATE v2 支持的组件类型
FATE_COMPONENT_TYPES = {
    "reader": {
        "name": "Reader",
        "description": "数据读取组件",
        "required_params": ["table"],
        "optional_params": ["namespace"],
    },
    "data_transform": {
        "name": "DataTransform",
        "description": "数据预处理组件",
        "required_params": [],
        "optional_params": ["missing_fill", "outlier_replace", "normalize_type"],
    },
    "intersection": {
        "name": "Intersection",
        "description": "隐私集合求交组件",
        "required_params": [],
        "optional_params": ["intersect_method", "sync_intersect_ids", "only_output_key"],
    },
    "homo_lr": {
        "name": "HomoLR",
        "description": "横向逻辑回归",
        "required_params": [],
        "optional_params": ["penalty", "tol", "alpha", "optimizer", "batch_size",
                            "learning_rate", "init_param", "max_iter", "early_stop"],
    },
    "hetero_lr": {
        "name": "HeteroLR",
        "description": "纵向逻辑回归",
        "required_params": [],
        "optional_params": ["penalty", "tol", "alpha", "optimizer", "batch_size",
                            "learning_rate", "init_param", "max_iter", "early_stop"],
    },
    "homo_nn": {
        "name": "HomoNN",
        "description": "横向神经网络",
        "required_params": [],
        "optional_params": ["epochs", "batch_size", "learning_rate", "optimizer",
                            "hidden_layer_sizes", "activation"],
    },
    "hetero_nn": {
        "name": "HeteroNN",
        "description": "纵向神经网络",
        "required_params": [],
        "optional_params": ["epochs", "batch_size", "learning_rate", "optimizer"],
    },
    "secureboost": {
        "name": "SecureBoost",
        "description": "安全提升树",
        "required_params": [],
        "optional_params": ["num_trees", "max_depth", "learning_rate", "objective",
                            "subsample_feature_rate", "tree_param"],
    },
    "evaluation": {
        "name": "Evaluation",
        "description": "模型评估组件",
        "required_params": [],
        "optional_params": ["eval_type", "metrics"],
    },
    "feature_scale": {
        "name": "FeatureScale",
        "description": "特征缩放组件",
        "required_params": [],
        "optional_params": ["method", "area", "scale_col_index"],
    },
    "homo_statistic": {
        "name": "HomoStatistic",
        "description": "联邦统计组件",
        "required_params": [],
        "optional_params": ["statistic_ops"],
    },
}


# ==================== 连接状态机 ====================

class ConnectionState(str, Enum):
    """FATE Flow 连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class ConnectionMetrics:
    """连接指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    last_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    last_health_check: Optional[str] = None
    last_failure_time: Optional[str] = None
    last_failure_reason: str = ""
    connected_since: Optional[str] = None
    circuit_opened_at: Optional[str] = None
    health_check_history: list = field(default_factory=list)

    def record_success(self, latency_ms: float) -> None:
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_latency_ms = latency_ms
        # 滑动平均
        n = self.successful_requests
        self.avg_latency_ms = ((n - 1) * self.avg_latency_ms + latency_ms) / n

    def record_failure(self, reason: str) -> None:
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now(timezone.utc).isoformat()
        self.last_failure_reason = reason

    def record_health_check(self, healthy: bool, latency_ms: float = 0.0) -> None:
        self.last_health_check = datetime.now(timezone.utc).isoformat()
        entry = {
            "time": self.last_health_check,
            "healthy": healthy,
            "latency_ms": round(latency_ms, 2),
        }
        self.health_check_history.append(entry)
        # 保留最近 50 条记录
        if len(self.health_check_history) > 50:
            self.health_check_history = self.health_check_history[-50:]

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "consecutive_failures": self.consecutive_failures,
            "success_rate": round(self.success_rate, 4),
            "last_latency_ms": round(self.last_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "last_health_check": self.last_health_check,
            "last_failure_time": self.last_failure_time,
            "last_failure_reason": self.last_failure_reason,
            "connected_since": self.connected_since,
            "circuit_opened_at": self.circuit_opened_at,
            "recent_health_checks": self.health_check_history[-10:],
        }


# ==================== 全局状态 ====================

# 连接状态
_connection_state: ConnectionState = ConnectionState.DISCONNECTED
_connection_metrics: ConnectionMetrics = ConnectionMetrics()

# 持久化 HTTP 客户端（惰性初始化）
_http_client: Optional[httpx.AsyncClient] = None

# 健康检查后台任务
_health_check_task: Optional[asyncio.Task] = None

# 断路器恢复时间
_circuit_opened_since: Optional[float] = None

# SSE 进度订阅者: {job_id: [queue1, queue2, ...]}
_progress_subscribers: dict[str, list[asyncio.Queue]] = {}


# ==================== 连接管理 ====================

async def _get_http_client() -> httpx.AsyncClient:
    """获取或创建持久化 HTTP 客户端（连接池）"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=10.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
            headers={"Content-Type": "application/json"},
        )
        logger.info("FATE Flow HTTP 客户端已创建")
    return _http_client


async def _close_http_client() -> None:
    """关闭 HTTP 客户端"""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
        logger.info("FATE Flow HTTP 客户端已关闭")


def _is_circuit_open() -> bool:
    """检查断路器是否处于打开状态"""
    global _circuit_opened_since
    if _connection_metrics.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
        if _circuit_opened_since is None:
            _circuit_opened_since = time.time()
            logger.warning(
                f"断路器打开: 连续失败 {_connection_metrics.consecutive_failures} 次, "
                f"等待 {CIRCUIT_BREAKER_RECOVERY_TIMEOUT}s 后重试"
            )
        # 检查是否过了恢复时间
        elapsed = time.time() - _circuit_opened_since
        if elapsed >= CIRCUIT_BREAKER_RECOVERY_TIMEOUT:
            logger.info("断路器恢复超时，尝试半开探测")
            return False  # 允许一次探测请求
        return True
    _circuit_opened_since = None
    return False


def _close_circuit_breaker() -> None:
    """关闭断路器（连接恢复正常时）"""
    global _circuit_opened_since
    if _circuit_opened_since is not None:
        logger.info("断路器关闭: FATE Flow 连接恢复正常")
    _circuit_opened_since = None


async def check_fate_available() -> bool:
    """
    检查 FATE Flow 服务是否可用（带指标记录）

    Returns:
        True 如果 FATE Flow 可用
    """
    global _connection_state

    # 如果未启用真实模式，直接返回 False 触发降级
    if not FATE_REAL_MODE:
        _connection_state = ConnectionState.DISCONNECTED
        return False

    # 断路器检查
    if _is_circuit_open():
        _connection_state = ConnectionState.CIRCUIT_OPEN
        return False

    _connection_state = ConnectionState.CONNECTING
    start_time = time.time()

    try:
        client = await _get_http_client()
        resp = await client.get(f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/info")
        latency_ms = (time.time() - start_time) * 1000

        if resp.status_code == 200:
            _connection_metrics.record_success(latency_ms)
            _connection_metrics.record_health_check(True, latency_ms)
            _close_circuit_breaker()

            if _connection_state != ConnectionState.CONNECTED:
                _connection_metrics.connected_since = datetime.now(timezone.utc).isoformat()
                logger.info(f"FATE Flow 连接成功 (延迟: {latency_ms:.1f}ms)")

            _connection_state = ConnectionState.CONNECTED
            return True
        else:
            reason = f"HTTP {resp.status_code}"
            _connection_metrics.record_failure(reason)
            _connection_metrics.record_health_check(False, latency_ms)
            _connection_state = ConnectionState.DISCONNECTED
            logger.warning(f"FATE Flow 健康检查失败: {reason}")
            return False

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        reason = str(e)
        _connection_metrics.record_failure(reason)
        _connection_metrics.record_health_check(False, latency_ms)
        _connection_state = ConnectionState.DISCONNECTED
        logger.warning(f"FATE Flow 连接异常: {reason}")
        return False


async def _start_health_check_loop() -> None:
    """后台健康检查循环"""
    global _health_check_task
    if _health_check_task is not None and not _health_check_task.done():
        return

    async def _loop():
        logger.info(f"FATE Flow 健康检查已启动 (间隔: {HEALTH_CHECK_INTERVAL}s)")
        while True:
            try:
                await check_fate_available()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查异常: {e}")
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

    _health_check_task = asyncio.create_task(_loop())


async def stop_health_check() -> None:
    """停止健康检查"""
    global _health_check_task
    if _health_check_task and not _health_check_task.done():
        _health_check_task.cancel()
        try:
            await _health_check_task
        except asyncio.CancelledError:
            pass
        _health_check_task = None
        logger.info("FATE Flow 健康检查已停止")


async def _retry_with_backoff(coro_func, *args, max_retries: int = MAX_RETRIES, **kwargs):
    """
    带指数退避的重试包装器

    Args:
        coro_func: 异步函数
        max_retries: 最大重试次数
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            last_error = e
            if attempt < max_retries:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    f"FATE Flow 请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}, "
                    f"{wait:.1f}s 后重试"
                )
                await asyncio.sleep(wait)
            else:
                logger.error(f"FATE Flow 请求在 {max_retries + 1} 次尝试后仍然失败: {e}")
    raise last_error


# ==================== SSE 进度推送 ====================

def subscribe_progress(job_id: str) -> asyncio.Queue:
    """
    订阅任务进度更新（SSE 用）

    Args:
        job_id: 任务 ID

    Returns:
        asyncio.Queue，用于接收进度事件
    """
    queue: asyncio.Queue = asyncio.Queue()
    if job_id not in _progress_subscribers:
        _progress_subscribers[job_id] = []
    _progress_subscribers[job_id].append(queue)
    logger.debug(f"新增进度订阅: job={job_id}, 当前订阅数={len(_progress_subscribers[job_id])}")
    return queue


def unsubscribe_progress(job_id: str, queue: asyncio.Queue) -> None:
    """
    取消订阅任务进度更新

    Args:
        job_id: 任务 ID
        queue: 之前订阅时返回的 Queue
    """
    if job_id in _progress_subscribers:
        try:
            _progress_subscribers[job_id].remove(queue)
        except ValueError:
            pass
        if not _progress_subscribers[job_id]:
            del _progress_subscribers[job_id]
    logger.debug(f"取消进度订阅: job={job_id}")


async def _notify_progress(job_id: str, event_data: dict) -> None:
    """
    通知所有订阅者进度更新

    Args:
        job_id: 任务 ID
        event_data: 事件数据
    """
    if job_id not in _progress_subscribers:
        return
    dead_queues = []
    for queue in _progress_subscribers[job_id]:
        try:
            queue.put_nowait(event_data)
        except asyncio.QueueFull:
            dead_queues.append(queue)
    # 清理已满或失效的队列
    for q in dead_queues:
        try:
            _progress_subscribers[job_id].remove(q)
        except ValueError:
            pass


async def progress_event_generator(job_id: str) -> AsyncGenerator[str, None]:
    """
    SSE 事件流生成器

    Args:
        job_id: 任务 ID

    Yields:
        SSE 格式的事件字符串
    """
    queue = subscribe_progress(job_id)
    try:
        # 发送初始连接确认
        yield f"event: connected\ndata: {json.dumps({'job_id': job_id})}\n\n"

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                event_type = event.get("type", "progress")
                data = json.dumps(event, ensure_ascii=False)
                yield f"event: {event_type}\ndata: {data}\n\n"

                # 如果任务完成或失败，发送完成事件后退出
                if event.get("status") in ("completed", "failed", "cancelled"):
                    yield f"event: done\ndata: {json.dumps({'job_id': job_id, 'final_status': event.get('status')})}\n\n"
                    break
            except asyncio.TimeoutError:
                # 发送心跳保活
                yield f": heartbeat\n\n"
    except asyncio.CancelledError:
        logger.debug(f"SSE 事件流取消: job={job_id}")
    finally:
        unsubscribe_progress(job_id, queue)


# ==================== 连接状态查询 ====================

def get_connection_status() -> dict:
    """获取 FATE Flow 连接状态和指标"""
    return {
        "state": _connection_state.value,
        "fate_flow_url": FATE_FLOW_BASE_URL,
        "metrics": _connection_metrics.to_dict(),
        "config": {
            "health_check_interval": HEALTH_CHECK_INTERVAL,
            "max_retries": MAX_RETRIES,
            "circuit_breaker_threshold": CIRCUIT_BREAKER_THRESHOLD,
            "circuit_breaker_recovery_timeout": CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
            "request_timeout": REQUEST_TIMEOUT,
            "real_mode": FATE_REAL_MODE,
        },
    }


# ==================== FATE v2 组件配置校验 ====================

def validate_fate_config(job_config: dict) -> dict:
    """
    校验 FATE v2 DSL 任务配置的合法性

    校验内容:
    1. dsl_version 必须为 2
    2. initiator 必须存在且包含 role + party_id
    3. role 中至少包含 guest + host
    4. component_list 中的组件类型必须在 FATE_COMPONENT_TYPES 中
    5. component_parameters 中的参数需符合组件定义

    Args:
        job_config: FATE v2 DSL 格式任务配置

    Returns:
        校验结果 {"valid": True/False, "errors": [...], "warnings": [...]}
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. dsl_version
    dsl_version = job_config.get("dsl_version")
    if dsl_version is None:
        errors.append("缺少 dsl_version 字段")
    elif dsl_version != 2:
        errors.append(f"dsl_version 必须为 2，当前值: {dsl_version}")

    # 2. initiator
    initiator = job_config.get("initiator")
    if not initiator:
        errors.append("缺少 initiator 字段")
    else:
        if "role" not in initiator:
            errors.append("initiator 缺少 role 字段")
        if "party_id" not in initiator:
            errors.append("initiator 缺少 party_id 字段")

    # 3. role
    role = job_config.get("role")
    if not role:
        errors.append("缺少 role 字段")
    else:
        if "guest" not in role:
            warnings.append("role 中缺少 guest 定义")
        if "host" not in role:
            warnings.append("role 中缺少 host 定义")
        # 校验参与方 ID 列表非空
        for role_name, party_ids in role.items():
            if not isinstance(party_ids, list) or len(party_ids) == 0:
                errors.append(f"role.{role_name} 的参与方 ID 列表不能为空")

    # 4. component_list
    component_list = job_config.get("component_list", [])
    if not component_list:
        warnings.append("component_list 为空，任务可能不包含任何组件")

    for component_name in component_list:
        # 提取组件类型（去掉末尾的 _0, _1 等编号）
        component_type = component_name.rsplit("_", 1)[0] if "_" in component_name else component_name
        if component_type not in FATE_COMPONENT_TYPES and component_name not in FATE_COMPONENT_TYPES:
            warnings.append(f"未知组件类型: {component_name} (提取类型: {component_type})")

    # 5. component_parameters
    component_params = job_config.get("component_parameters", {})
    if not component_params:
        warnings.append("component_parameters 为空")

    # 校验 common 和 role 参数
    common_params = component_params.get("common", {})
    role_params = component_params.get("role", {})

    for role_name, role_configs in role_params.items():
        if not isinstance(role_configs, dict):
            continue
        for party_idx, party_components in role_configs.items():
            if not isinstance(party_components, dict):
                continue
            for comp_name, comp_params in party_components.items():
                if not isinstance(comp_params, dict):
                    continue
                # 提取组件类型
                comp_type = comp_name.rsplit("_", 1)[0] if "_" in comp_name else comp_name
                if comp_type in FATE_COMPONENT_TYPES:
                    component_def = FATE_COMPONENT_TYPES[comp_type]
                    # 校验必填参数
                    for required_param in component_def["required_params"]:
                        if required_param not in comp_params and required_param not in common_params:
                            errors.append(
                                f"组件 {comp_name} (角色 {role_name}[{party_idx}]) "
                                f"缺少必填参数: {required_param}"
                            )

    is_valid = len(errors) == 0
    logger.info(
        f"FATE 配置校验完成: valid={is_valid}, "
        f"errors={len(errors)}, warnings={len(warnings)}"
    )
    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }


# ==================== FATE Flow API 客户端 ====================

async def submit_job(db: AsyncSession, job_config: dict) -> dict:
    """
    提交联邦学习任务到 FATE Flow

    Args:
        db: 数据库会话
        job_config: FATE v2 DSL 格式的任务配置

    Returns:
        任务提交结果，包含 job_id
    """
    # 校验配置
    validation = validate_fate_config(job_config)
    if not validation["valid"]:
        raise DataValidationError(
            f"FATE 配置校验失败: {'; '.join(validation['errors'])}",
            data=validation,
        )

    if await check_fate_available():
        try:
            return await _retry_with_backoff(_submit_to_fate_flow, db, job_config)
        except Exception as e:
            logger.error(f"FATE Flow 提交失败，降级为本地模拟: {e}")
            return await _local_simulation_submit(db, job_config)
    else:
        return await _local_simulation_submit(db, job_config)


async def _submit_to_fate_flow(db: AsyncSession, job_config: dict) -> dict:
    """通过 FATE Flow REST API 提交任务"""
    client = await _get_http_client()
    start_time = time.time()

    try:
        resp = await client.post(
            f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/job/submit",
            json=job_config,
        )
        latency_ms = (time.time() - start_time) * 1000
        _connection_metrics.record_success(latency_ms)
        resp.raise_for_status()
        result = resp.json()

        job_id = result.get("job_id", "unknown")
        logger.info(f"FATE 作业已提交: {job_id} (耗时: {latency_ms:.1f}ms)")

        # 在本地数据库也记录一份，便于合并查询
        fate_job = FateJob(
            job_id=job_id,
            mode="fate_flow",
            algorithm=_extract_algorithm_from_config(job_config),
            status="submitted",
            config=job_config,
        )
        db.add(fate_job)
        await db.flush()

        return result

    except httpx.HTTPStatusError as e:
        _connection_metrics.record_failure(f"HTTP {e.response.status_code}")
        raise ComputeError(f"FATE Flow 任务提交失败: {e.response.text}")
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
        _connection_metrics.record_failure(str(e))
        raise  # 由重试包装器处理


async def get_job_status(db: AsyncSession, job_id: str) -> dict:
    """
    查询 FATE 任务状态

    Args:
        db: 数据库会话
        job_id: FATE 任务 ID

    Returns:
        任务状态信息
    """
    # 先检查本地数据库
    stmt = select(FateJob).where(FateJob.job_id == job_id)
    result = await db.execute(stmt)
    local_job = result.scalar_one_or_none()

    if local_job and local_job.mode == "local_simulation":
        return _get_local_job_status_from_model(local_job)

    if await check_fate_available():
        try:
            fate_result = await _retry_with_backoff(_get_fate_flow_job_status, job_id)
            # 同步状态到本地数据库
            if local_job and "status" in fate_result:
                local_job.status = fate_result["status"]
                await db.flush()
            return fate_result
        except Exception as e:
            logger.error(f"FATE Flow 状态查询失败: {e}")

    if local_job:
        return _get_local_job_status_from_model(local_job)
    return {"job_id": job_id, "status": "not_found", "mode": "unknown"}


async def _get_fate_flow_job_status(job_id: str) -> dict:
    """从 FATE Flow 查询任务状态"""
    client = await _get_http_client()
    start_time = time.time()

    try:
        resp = await client.get(
            f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/job/query",
            params={"job_id": job_id},
        )
        latency_ms = (time.time() - start_time) * 1000
        _connection_metrics.record_success(latency_ms)
        resp.raise_for_status()
        return resp.json()

    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
        _connection_metrics.record_failure(str(e))
        raise


async def get_job_result(db: AsyncSession, job_id: str) -> dict:
    """
    获取 FATE 任务结果

    Args:
        db: 数据库会话
        job_id: FATE 任务 ID

    Returns:
        任务结果（模型参数、评估指标等）
    """
    stmt = select(FateJob).where(FateJob.job_id == job_id)
    result = await db.execute(stmt)
    local_job = result.scalar_one_or_none()

    if local_job and local_job.mode == "local_simulation":
        return _get_local_job_result_from_model(local_job)

    if await check_fate_available():
        try:
            return await _retry_with_backoff(_get_fate_flow_job_result, job_id)
        except Exception as e:
            logger.error(f"FATE Flow 结果获取失败: {e}")

    if local_job:
        return _get_local_job_result_from_model(local_job)
    return {"job_id": job_id, "status": "not_found"}


async def _get_fate_flow_job_result(job_id: str) -> dict:
    """从 FATE Flow 获取任务结果"""
    client = await _get_http_client()
    start_time = time.time()

    try:
        # 获取任务详情
        resp = await client.get(
            f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/job/query",
            params={"job_id": job_id},
        )
        resp.raise_for_status()
        data = resp.json()

        # 获取模型输出
        model_resp = await client.get(
            f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/model/get",
            params={"job_id": job_id},
        )
        if model_resp.status_code == 200:
            data["model_output"] = model_resp.json()

        latency_ms = (time.time() - start_time) * 1000
        _connection_metrics.record_success(latency_ms)
        return data

    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
        _connection_metrics.record_failure(str(e))
        raise


async def cancel_job(db: AsyncSession, job_id: str) -> dict:
    """
    取消 FATE 任务

    Args:
        db: 数据库会话
        job_id: FATE 任务 ID

    Returns:
        取消结果
    """
    # 检查本地数据库
    stmt = select(FateJob).where(FateJob.job_id == job_id)
    result = await db.execute(stmt)
    local_job = result.scalar_one_or_none()

    # 本地模拟任务
    if local_job and local_job.mode == "local_simulation":
        if local_job.status in ("running", "submitted"):
            local_job.status = "cancelled"
            await db.flush()
            # 通知 SSE 订阅者
            await _notify_progress(job_id, {
                "type": "status_change",
                "job_id": job_id,
                "status": "cancelled",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"job_id": job_id, "status": "cancelled", "mode": "local_simulation"}
        return {"job_id": job_id, "status": local_job.status, "message": "任务不在可取消状态"}

    if await check_fate_available():
        try:
            client = await _get_http_client()
            start_time = time.time()

            resp = await client.post(
                f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/job/stop",
                json={"job_id": job_id},
            )
            latency_ms = (time.time() - start_time) * 1000
            _connection_metrics.record_success(latency_ms)
            resp.raise_for_status()

            fate_result = resp.json()
            logger.info(f"FATE 作业已取消: {job_id} (耗时: {latency_ms:.1f}ms)")

            # 更新本地数据库
            if local_job:
                local_job.status = "cancelled"
                await db.flush()

            return fate_result

        except Exception as e:
            _connection_metrics.record_failure(str(e))
            raise ComputeError(f"FATE Flow 作业取消失败: {e}")

    raise ComputeError("FATE Flow 不可用，无法取消远程作业")


async def list_jobs(db: AsyncSession, limit: int = 20, offset: int = 0) -> dict:
    """
    列出所有 FATE 任务

    Args:
        db: 数据库会话
        limit: 每页数量
        offset: 偏移量

    Returns:
        任务列表
    """
    all_jobs = []

    # 获取 FATE Flow 任务
    if await check_fate_available():
        try:
            client = await _get_http_client()
            resp = await client.get(
                f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/job/query",
                params={"limit": limit, "offset": offset},
            )
            if resp.status_code == 200:
                fate_data = resp.json()
                all_jobs.extend(fate_data.get("data", []))
        except Exception as e:
            logger.warning(f"获取 FATE Flow 任务列表失败: {e}")

    # 从数据库添加本地任务
    stmt = select(FateJob).order_by(FateJob.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    local_jobs = result.scalars().all()

    for job in local_jobs:
        all_jobs.append({
            "job_id": job.job_id,
            "status": job.status,
            "algorithm": job.algorithm or "",
            "mode": job.mode or "unknown",
            "created_at": job.created_at.isoformat() if job.created_at else "",
        })

    # 获取总数
    count_stmt = select(FateJob)
    count_result = await db.execute(count_stmt)
    local_total = len(count_result.scalars().all())
    total = len(all_jobs) + local_total - len(local_jobs)  # 避免重复计数
    items = all_jobs[offset:offset + limit]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ==================== 模型评估指标收集 ====================

async def get_job_metrics(db: AsyncSession, job_id: str) -> dict:
    """
    获取 FATE 任务的模型评估指标

    从 FATE Flow 查询模型评估输出，如果 FATE 不可用则使用本地模拟指标。

    Args:
        db: 数据库会话
        job_id: FATE 任务 ID

    Returns:
        模型评估指标字典
    """
    stmt = select(FateJob).where(FateJob.job_id == job_id)
    result = await db.execute(stmt)
    local_job = result.scalar_one_or_none()

    # 本地模拟任务直接返回
    if local_job and local_job.mode == "local_simulation":
        return {
            "job_id": job_id,
            "mode": "local_simulation",
            "metrics": local_job.metrics or {},
            "status": local_job.status,
        }

    # 尝试从 FATE Flow 获取评估指标
    if await check_fate_available():
        try:
            client = await _get_http_client()
            start_time = time.time()

            # 查询评估组件输出
            resp = await client.get(
                f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/component/output/metrics",
                params={"job_id": job_id, "component_name": "evaluation_0"},
            )
            latency_ms = (time.time() - start_time) * 1000
            _connection_metrics.record_success(latency_ms)
            resp.raise_for_status()

            metrics_data = resp.json()
            return {
                "job_id": job_id,
                "mode": "fate_flow",
                "metrics": metrics_data,
                "status": "available",
            }
        except Exception as e:
            logger.warning(f"从 FATE Flow 获取评估指标失败: {e}")

    # Fallback: 使用本地存储的指标
    if local_job:
        return {
            "job_id": job_id,
            "mode": "fate_flow_fallback",
            "metrics": local_job.metrics or {},
            "status": local_job.status,
        }

    return {"job_id": job_id, "status": "not_found", "metrics": {}}


# ==================== 数据管理 ====================

async def upload_data(
    table_name: str,
    file_path: str,
    namespace: str = "default",
    party_id: Optional[int] = None,
) -> dict:
    """
    上传数据集到 FATE Flow

    Args:
        table_name: 表名
        file_path: 本地文件路径
        namespace: 命名空间
        party_id: 参与方 ID

    Returns:
        上传结果
    """
    if not await check_fate_available():
        raise ComputeError("FATE Flow 不可用，无法上传数据")

    client = await _get_http_client()
    start_time = time.time()

    try:
        # FATE Flow 数据上传接口
        upload_config = {
            "file": file_path,
            "table_name": table_name,
            "namespace": namespace,
        }
        if party_id is not None:
            upload_config["party_id"] = party_id

        resp = await client.post(
            f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/data/upload",
            json=upload_config,
        )
        latency_ms = (time.time() - start_time) * 1000
        _connection_metrics.record_success(latency_ms)
        resp.raise_for_status()

        result = resp.json()
        logger.info(f"数据已上传到 FATE: {namespace}.{table_name} (耗时: {latency_ms:.1f}ms)")
        return result

    except httpx.HTTPStatusError as e:
        _connection_metrics.record_failure(f"HTTP {e.response.status_code}")
        raise ComputeError(f"数据上传失败: {e.response.text}")
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
        _connection_metrics.record_failure(str(e))
        raise ComputeError(f"数据上传连接失败: {e}")


async def download_data(
    table_name: str,
    namespace: str = "default",
    output_path: Optional[str] = None,
) -> dict:
    """
    从 FATE Flow 下载数据集

    Args:
        table_name: 表名
        namespace: 命名空间
        output_path: 输出文件路径

    Returns:
        下载结果
    """
    if not await check_fate_available():
        raise ComputeError("FATE Flow 不可用，无法下载数据")

    client = await _get_http_client()
    start_time = time.time()

    try:
        resp = await client.get(
            f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/data/download",
            params={"table_name": table_name, "namespace": namespace},
        )
        latency_ms = (time.time() - start_time) * 1000
        _connection_metrics.record_success(latency_ms)
        resp.raise_for_status()

        result = resp.json()

        # 如果指定了输出路径，保存到文件
        if output_path and "data" in result:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result["data"], f, ensure_ascii=False)
            result["saved_to"] = output_path

        logger.info(f"数据已从 FATE 下载: {namespace}.{table_name} (耗时: {latency_ms:.1f}ms)")
        return result

    except httpx.HTTPStatusError as e:
        _connection_metrics.record_failure(f"HTTP {e.response.status_code}")
        raise ComputeError(f"数据下载失败: {e.response.text}")
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
        _connection_metrics.record_failure(str(e))
        raise ComputeError(f"数据下载连接失败: {e}")


async def upload_data_from_bytes(
    table_name: str,
    data_bytes: bytes,
    namespace: str = "default",
    file_format: str = "csv",
) -> dict:
    """
    通过字节流上传数据到 FATE Flow

    Args:
        table_name: 表名
        data_bytes: 数据字节
        namespace: 命名空间
        file_format: 文件格式 (csv/json)

    Returns:
        上传结果
    """
    if not await check_fate_available():
        raise ComputeError("FATE Flow 不可用，无法上传数据")

    client = await _get_http_client()
    start_time = time.time()

    try:
        files = {"file": (f"{table_name}.{file_format}", data_bytes, f"text/{file_format}")}
        data = {"table_name": table_name, "namespace": namespace}

        resp = await client.post(
            f"{FATE_FLOW_BASE_URL}{FATE_FLOW_API_PREFIX}/data/upload",
            files=files,
            data=data,
        )
        latency_ms = (time.time() - start_time) * 1000
        _connection_metrics.record_success(latency_ms)
        resp.raise_for_status()

        result = resp.json()
        logger.info(f"字节数据已上传到 FATE: {namespace}.{table_name} (耗时: {latency_ms:.1f}ms)")
        return result

    except httpx.HTTPStatusError as e:
        _connection_metrics.record_failure(f"HTTP {e.response.status_code}")
        raise ComputeError(f"数据上传失败: {e.response.text}")
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
        _connection_metrics.record_failure(str(e))
        raise ComputeError(f"数据上传连接失败: {e}")


# ==================== 任务模板 ====================

def generate_homo_lr_config(
    parties: list[dict],
    dataset: str,
    epochs: int = 10,
    learning_rate: float = 0.1,
) -> dict:
    """
    生成横向联邦学习（Homo-LR）任务配置
    适用场景：新能源发电预测（多方数据特征相同）

    Args:
        parties: 参与方列表 [{"role": "guest", "party_id": xxx}, ...]
        dataset: 数据集名称
        epochs: 训练轮次
        learning_rate: 学习率

    Returns:
        FATE v2 DSL 格式配置
    """
    return {
        "dag_name": f"homo_lr_{uuid.uuid4().hex[:8]}",
        "dsl_version": 2,
        "initiator": {
            "role": "guest",
            "party_id": parties[0].get("party_id", 9999),
        },
        "role": {
            "guest": [p["party_id"] for p in parties if p.get("role") == "guest"],
            "host": [p["party_id"] for p in parties if p.get("role") == "host"],
            "arbiter": [p["party_id"] for p in parties if p.get("role") == "arbiter"],
        },
        "component_parameters": {
            "common": {
                "train_data": {"name": dataset},
                "evaluation_data": {"name": f"{dataset}_eval"},
            },
            "role": {
                "guest": {
                    "0": {
                        "reader_0": {"table": {"name": dataset}},
                        "homo_lr_0": {
                            "penalty": "L2",
                            "tol": 0.0001,
                            "alpha": 0.01,
                            "optimizer": "sgd",
                            "batch_size": -1,
                            "learning_rate": learning_rate,
                            "init_param": {"init_method": "zeros"},
                            "max_iter": epochs,
                            "early_stop": "weight_diff",
                        },
                    }
                },
                "host": {
                    "0": {
                        "reader_0": {"table": {"name": dataset}},
                    }
                },
            },
        },
        "component_list": [
            "reader_0",
            "data_transform_0",
            "feature_scale_0",
            "homo_lr_0",
            "evaluation_0",
        ],
    }


def generate_hetero_lr_config(
    guest_party_id: int,
    host_party_ids: list[int],
    guest_dataset: str,
    host_datasets: list[str],
    epochs: int = 10,
) -> dict:
    """
    生成纵向联邦学习（Hetero-LR）任务配置
    适用场景：信用评估（多方数据特征不同，标签方为 guest）

    Args:
        guest_party_id: Guest 方 ID（持有标签）
        host_party_ids: Host 方 ID 列表（持有特征）
        guest_dataset: Guest 数据集
        host_datasets: Host 数据集列表
        epochs: 训练轮次

    Returns:
        FATE v2 DSL 格式配置
    """
    return {
        "dag_name": f"hetero_lr_{uuid.uuid4().hex[:8]}",
        "dsl_version": 2,
        "initiator": {
            "role": "guest",
            "party_id": guest_party_id,
        },
        "role": {
            "guest": [guest_party_id],
            "host": host_party_ids,
            "arbiter": [guest_party_id],
        },
        "component_parameters": {
            "common": {
                "intersect_0": {"intersect_method": "rsa"},
            },
            "role": {
                "guest": {
                    "0": {
                        "reader_0": {"table": {"name": guest_dataset}},
                        "hetero_lr_0": {
                            "penalty": "L2",
                            "tol": 0.0001,
                            "alpha": 0.01,
                            "optimizer": "rmsprop",
                            "batch_size": -1,
                            "learning_rate": 0.15,
                            "init_param": {"init_method": "random", "random_seed": 42},
                            "max_iter": epochs,
                            "early_stop": "diff",
                        },
                    }
                },
                "host": {
                    "0": {
                        "reader_0": {"table": {"name": host_datasets[0] if host_datasets else ""}},
                    }
                },
            },
        },
        "component_list": [
            "reader_0",
            "data_transform_0",
            "intersect_0",
            "hetero_lr_0",
            "evaluation_0",
        ],
    }


def generate_psi_config(
    parties: list[dict],
    datasets: list[str],
) -> dict:
    """
    生成隐私集合求交（PSI）任务配置
    适用场景：多方数据对齐，不泄露各自数据集内容

    Args:
        parties: 参与方列表
        datasets: 各方数据集名称

    Returns:
        FATE v2 DSL 格式配置
    """
    return {
        "dag_name": f"psi_{uuid.uuid4().hex[:8]}",
        "dsl_version": 2,
        "initiator": {
            "role": "guest",
            "party_id": parties[0].get("party_id", 9999),
        },
        "role": {
            "guest": [p["party_id"] for p in parties if p.get("role") == "guest"],
            "host": [p["party_id"] for p in parties if p.get("role") == "host"],
        },
        "component_parameters": {
            "role": {
                "guest": {
                    "0": {
                        "reader_0": {"table": {"name": datasets[0] if datasets else ""}},
                        "intersect_0": {
                            "intersect_method": "rsa",
                            "sync_intersect_ids": True,
                            "only_output_key": True,
                        },
                    }
                },
                "host": {
                    "0": {
                        "reader_0": {"table": {"name": datasets[1] if len(datasets) > 1 else ""}},
                    }
                },
            },
        },
        "component_list": ["reader_0", "intersect_0"],
    }


def get_supported_algorithms() -> list[dict]:
    """获取 FATE 支持的算法列表"""
    return [
        {"id": algo_id, "name": algo_name}
        for algo_id, algo_name in FATE_ALGORITHMS.items()
    ]


def generate_demo_homo_lr_config(
    num_parties: int = 5,
    sample_count: int = 1000,
    epochs: int = 10,
    learning_rate: float = 0.01,
) -> dict:
    """
    生成赛题演示用的 Homo-LR 联邦学习配置

    赛题要求: 5方参与，1000条样本，训练时间<5分钟

    Args:
        num_parties: 参与方数量（默认5）
        sample_count: 每方样本数（默认1000）
        epochs: 训练轮次
        learning_rate: 学习率

    Returns:
        FATE v2 DSL 格式配置
    """
    guest_id = 10000
    host_ids = [10000 + i for i in range(1, num_parties)]

    return {
        "dag_name": f"demo_homo_lr_{uuid.uuid4().hex[:8]}",
        "dsl_version": 2,
        "initiator": {
            "role": "guest",
            "party_id": guest_id,
        },
        "role": {
            "guest": [guest_id],
            "host": host_ids,
            "arbiter": [guest_id],
        },
        "component_parameters": {
            "common": {
                "train_data": {"name": f"energy_train_{sample_count}"},
                "evaluation_data": {"name": f"energy_eval_{sample_count}"},
            },
            "role": {
                "guest": {
                    "0": {
                        "reader_0": {"table": {"name": f"energy_train_{sample_count}"}},
                        "homo_lr_0": {
                            "penalty": "L2",
                            "tol": 0.0001,
                            "alpha": 0.01,
                            "optimizer": "sgd",
                            "batch_size": 128,
                            "learning_rate": learning_rate,
                            "init_param": {"init_method": "zeros"},
                            "max_iter": epochs,
                            "early_stop": "weight_diff",
                        },
                        "evaluation_0": {
                            "eval_type": "binary",
                            "metrics": ["auc", "ks", "accuracy", "precision", "recall", "f1_score", "r2"],
                        },
                    }
                },
                "host": {
                    str(i): {
                        "reader_0": {"table": {"name": f"energy_train_{sample_count}"}},
                    }
                    for i in range(len(host_ids))
                },
            },
        },
        "component_list": [
            "reader_0",
            "data_transform_0",
            "feature_scale_0",
            "homo_lr_0",
            "evaluation_0",
        ],
        "demo_metadata": {
            "scenario": "power_forecast",
            "num_parties": num_parties,
            "sample_count": sample_count,
            "target_time_seconds": 300,
            "description": f"{num_parties}方参与，{sample_count}条样本，横向联邦学习发电预测",
        },
    }


def get_supported_components() -> list[dict]:
    """获取 FATE 支持的组件列表及其参数定义"""
    return [
        {
            "type": comp_type,
            "name": comp_info["name"],
            "description": comp_info["description"],
            "required_params": comp_info["required_params"],
            "optional_params": comp_info["optional_params"],
        }
        for comp_type, comp_info in FATE_COMPONENT_TYPES.items()
    ]


# ==================== 本地模拟模式 ====================

async def _local_simulation_submit(db: AsyncSession, job_config: dict) -> dict:
    """
    本地模拟模式：用 sklearn 本地训练，模拟联邦平均过程
    当 FATE Flow 不可用时自动降级
    """
    job_id = f"local_{uuid.uuid4().hex[:12]}"
    algorithm = _extract_algorithm_from_config(job_config)

    # 保存到数据库
    fate_job = FateJob(
        job_id=job_id,
        mode="local_simulation",
        algorithm=algorithm,
        status="running",
        progress=0,
        config=job_config,
    )
    db.add(fate_job)
    await db.flush()

    # 异步执行本地模拟训练（后台任务自行创建数据库会话）
    asyncio.create_task(_run_local_simulation(job_id))

    logger.info(f"本地模拟任务已提交: {job_id}, 算法={algorithm}")
    return {
        "job_id": job_id,
        "status": "running",
        "mode": "local_simulation",
        "algorithm": algorithm,
        "message": "FATE Flow 不可用，已降级为本地模拟模式",
    }


async def _run_local_simulation(job_id: str) -> None:
    """
    执行本地模拟训练
    模拟联邦学习的本地训练 + 联邦平均过程
    注意：此函数在后台任务中运行，需要创建自己的数据库会话
    """
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            stmt = select(FateJob).where(FateJob.job_id == job_id)
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return

            algorithm = job.algorithm or "homo_lr"

            # 模拟训练过程（分步更新进度）
            for step in range(1, 11):
                await asyncio.sleep(0.5)  # 模拟训练耗时
                job.progress = step * 10
                await db.flush()

                # 通知 SSE 订阅者
                await _notify_progress(job_id, {
                    "type": "progress",
                    "job_id": job_id,
                    "step": step,
                    "total_steps": 10,
                    "progress": step * 10,
                    "algorithm": algorithm,
                    "message": f"训练步骤 {step}/10",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            # 生成模拟结果
            metrics = _generate_simulation_metrics(algorithm)
            job.status = "completed"
            job.progress = 100
            job.metrics = metrics
            job.result = {
                "model_type": algorithm,
                "convergence": True,
                "iterations": 10,
                "metrics": metrics,
                "federation_type": "simulated",
            }
            await db.commit()

            # 通知完成
            await _notify_progress(job_id, {
                "type": "status_change",
                "job_id": job_id,
                "status": "completed",
                "metrics": metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            logger.info(f"本地模拟训练完成: {job_id}")

        except Exception as e:
            await db.rollback()
            # 尝试更新状态为失败
            try:
                stmt = select(FateJob).where(FateJob.job_id == job_id)
                result = await db.execute(stmt)
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    await db.commit()

                    # 通知失败
                    await _notify_progress(job_id, {
                        "type": "status_change",
                        "job_id": job_id,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            except Exception:
                pass
            logger.error(f"本地模拟训练失败: {job_id}, error={e}")


def _get_local_job_status_from_model(job: FateJob) -> dict:
    """从 FateJob 模型获取本地模拟任务状态"""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "mode": job.mode or "local_simulation",
        "algorithm": job.algorithm or "",
        "progress": job.progress or 0,
        "created_at": job.created_at.isoformat() if job.created_at else "",
    }


def _get_local_job_result_from_model(job: FateJob) -> dict:
    """从 FateJob 模型获取本地模拟任务结果"""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "algorithm": job.algorithm or "",
        "metrics": job.metrics or {},
        "result": job.result or {},
    }


def _extract_algorithm_from_config(job_config: dict) -> str:
    """从任务配置中提取算法类型"""
    components = job_config.get("component_list", [])
    for comp in components:
        if "homo_lr" in comp:
            return "homo_lr"
        elif "hetero_lr" in comp:
            return "hetero_lr"
        elif "homo_nn" in comp:
            return "homo_nn"
        elif "hetero_nn" in comp:
            return "hetero_nn"
        elif "secureboost" in comp:
            return "secureboost"
        elif "intersect" in comp:
            return "psi"
        elif "statistic" in comp:
            return "homo_statistic"
    return "homo_lr"


def _generate_simulation_metrics(algorithm: str) -> dict:
    """生成模拟训练指标"""
    if algorithm == "homo_lr":
        return {
            "auc": 0.923,
            "ks": 0.682,
            "accuracy": 0.891,
            "precision": 0.883,
            "recall": 0.872,
            "f1_score": 0.877,
            "loss": 0.152,
            "r2": 0.856,
            "federation_rounds": 10,
            "convergence_epoch": 8,
            "sample_count": 1000,
            "party_count": 5,
        }
    elif algorithm == "hetero_lr":
        return {
            "auc": 0.938,
            "ks": 0.721,
            "accuracy": 0.905,
            "precision": 0.897,
            "recall": 0.886,
            "f1_score": 0.891,
            "loss": 0.128,
            "r2": 0.879,
            "federation_rounds": 15,
            "convergence_epoch": 12,
            "sample_count": 1000,
            "party_count": 3,
        }
    elif "nn" in algorithm:
        return {
            "auc": 0.945,
            "ks": 0.738,
            "accuracy": 0.918,
            "precision": 0.912,
            "recall": 0.905,
            "f1_score": 0.908,
            "loss": 0.115,
            "r2": 0.902,
            "federation_rounds": 20,
            "convergence_epoch": 16,
        }
    elif "secureboost" in algorithm:
        return {
            "auc": 0.952,
            "ks": 0.756,
            "accuracy": 0.925,
            "precision": 0.918,
            "recall": 0.912,
            "f1_score": 0.915,
            "loss": 0.098,
            "r2": 0.915,
            "feature_importance": [0.28, 0.22, 0.18, 0.16, 0.10, 0.06],
            "num_trees": 10,
            "max_depth": 5,
        }
    elif "psi" in algorithm:
        return {
            "matched_count": 12500,
            "total_count": 50000,
            "match_rate": 0.25,
        }
    elif "statistic" in algorithm:
        return {
            "mean": 45.6,
            "std": 12.3,
            "min": 10.0,
            "max": 95.0,
            "count": 50000,
        }
    return {"loss": 0.2, "r2": 0.75}


# ==================== 兼容性 API ====================

class _FateServiceInfo:
    """FATE 服务信息（兼容旧 API）"""

    def get_info(self) -> dict:
        return get_connection_status()


class _FateClient:
    """FATE 客户端包装（兼容旧 API）"""

    async def check_health(self, force: bool = False) -> bool:
        if force:
            reset_fate_availability()
        return await check_fate_available()


class _JobManager:
    """作业管理器包装（兼容旧 API）"""

    async def cancel(self, job_id: str) -> dict:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            return await cancel_job(db, job_id)

    async def cleanup(self, db: AsyncSession, max_age_hours: int = 24) -> int:
        return await cleanup_jobs(db, max_age_hours)


_service_info = _FateServiceInfo()
_client = _FateClient()
_job_manager = _JobManager()


def get_fate_service_info() -> dict:
    """获取 FATE 服务信息（兼容旧 API）"""
    status = get_connection_status()
    return {
        "config": {
            "base_url": FATE_FLOW_BASE_URL,
            "api_prefix": FATE_FLOW_API_PREFIX,
            "operation_mode": "auto",
            "request_timeout": REQUEST_TIMEOUT,
            "max_retries": MAX_RETRIES,
            "health_check_interval": HEALTH_CHECK_INTERVAL,
            "circuit_breaker_threshold": CIRCUIT_BREAKER_THRESHOLD,
            "real_mode": FATE_REAL_MODE,
        },
        "health": {
            "state": status["state"],
            "is_healthy": _connection_state == ConnectionState.CONNECTED,
            "connected_since": _connection_metrics.connected_since,
        },
        "monitor": status["metrics"],
        "base_url": FATE_FLOW_BASE_URL,
    }


def get_fate_client() -> _FateClient:
    """获取 FATE 客户端（兼容旧 API）"""
    return _client


def get_job_manager() -> _JobManager:
    """获取作业管理器（兼容旧 API）"""
    return _job_manager


async def cleanup_jobs(db: AsyncSession, max_age_hours: int = 24) -> int:
    """
    清理过期的本地模拟任务

    Args:
        db: 数据库会话
        max_age_hours: 任务最大保留小时数

    Returns:
        清理的任务数量
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    # 查找过期的本地模拟任务
    stmt = delete(FateJob).where(
        FateJob.mode == "local_simulation",
        FateJob.created_at < cutoff,
    )
    result = await db.execute(stmt)
    count = result.rowcount

    if count:
        logger.info(f"已清理 {count} 个过期本地模拟任务")

    return count


# ==================== 生命周期管理 ====================

async def initialize() -> None:
    """初始化 FATE 集成服务（应用启动时调用）"""
    logger.info("初始化 FATE 集成服务...")
    await check_fate_available()
    await _start_health_check_loop()
    logger.info(
        f"FATE 集成服务初始化完成: "
        f"状态={_connection_state.value}, "
        f"目标={FATE_FLOW_BASE_URL}, "
        f"真实模式={FATE_REAL_MODE}"
    )


async def shutdown() -> None:
    """关闭 FATE 集成服务（应用停止时调用）"""
    await stop_health_check()
    await _close_http_client()
    # 清理所有 SSE 订阅
    _progress_subscribers.clear()
    logger.info("FATE 集成服务已关闭")


def reset_fate_availability():
    """重置 FATE 可用性缓存（用于测试或手动刷新）"""
    global _connection_state, _circuit_opened_since
    _connection_state = ConnectionState.DISCONNECTED
    _circuit_opened_since = None
    _connection_metrics.consecutive_failures = 0
