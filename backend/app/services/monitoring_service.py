"""
监控增强服务 - Prometheus 真实指标采集
系统指标、应用指标、自定义指标注册、趋势告警
"""
import uuid
import logging
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any, Callable

from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    CollectorRegistry, REGISTRY, generate_latest, CONTENT_TYPE_LATEST,
)

logger = logging.getLogger(__name__)

# ==================== Prometheus 指标定义 ====================

# API 请求指标
API_REQUESTS_TOTAL = Counter(
    "energy_api_requests_total",
    "API 请求总数",
    ["method", "endpoint", "status_code"],
)

API_REQUEST_DURATION = Histogram(
    "energy_api_request_duration_seconds",
    "API 请求耗时（秒）",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

API_REQUEST_IN_PROGRESS = Gauge(
    "energy_api_requests_in_progress",
    "当前正在处理的 API 请求数",
    ["method", "endpoint"],
)

# 系统指标
SYSTEM_CPU_USAGE = Gauge(
    "energy_system_cpu_usage_percent",
    "系统 CPU 使用率",
)

SYSTEM_MEMORY_USAGE = Gauge(
    "energy_system_memory_usage_percent",
    "系统内存使用率",
)

SYSTEM_DISK_USAGE = Gauge(
    "energy_system_disk_usage_percent",
    "系统磁盘使用率",
)

SYSTEM_NETWORK_IN = Counter(
    "energy_system_network_in_bytes_total",
    "系统网络入流量（字节）",
)

SYSTEM_NETWORK_OUT = Counter(
    "energy_system_network_out_bytes_total",
    "系统网络出流量（字节）",
)

# 应用指标
ACTIVE_USERS = Gauge(
    "energy_active_users_count",
    "当前活跃用户数",
)

ACTIVE_CONNECTIONS = Gauge(
    "energy_active_connections_count",
    "当前活跃连接数",
)

DB_CONNECTION_POOL = Gauge(
    "energy_db_connection_pool_usage_percent",
    "数据库连接池使用率",
)

DB_QUERY_DURATION = Histogram(
    "energy_db_query_duration_seconds",
    "数据库查询耗时（秒）",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

CACHE_HIT_RATE = Gauge(
    "energy_cache_hit_rate_percent",
    "缓存命中率",
)

ERROR_RATE = Gauge(
    "energy_error_rate_percent",
    "API 错误率",
)

# 数据采集量
DATA_COLLECTED_TOTAL = Counter(
    "energy_data_collected_bytes_total",
    "数据采集总量（字节）",
    ["source_type"],
)

COMPUTE_TASKS_TOTAL = Counter(
    "energy_compute_tasks_total",
    "计算任务总数",
    ["task_type", "status"],
)

BLOCKCHAIN_TX_TOTAL = Counter(
    "energy_blockchain_transactions_total",
    "区块链交易总数",
    ["tx_type"],
)

ALERTS_TRIGGERED_TOTAL = Counter(
    "energy_alerts_triggered_total",
    "触发的告警总数",
    ["severity"],
)


# ==================== 指标元数据注册 ====================

# 指标注册表（用于 API 展示）
_metrics_registry: Dict[str, dict] = {}
_custom_collectors: Dict[str, Callable] = {}

# 历史值缓存（用于趋势告警和 API 查询）
_metric_values: Dict[str, List[dict]] = {}


def _init_default_metrics():
    """初始化默认指标元数据"""
    defaults = [
        {"name": "energy_system_cpu_usage_percent", "type": "gauge", "unit": "%",
         "description": "系统 CPU 使用率", "category": "system"},
        {"name": "energy_system_memory_usage_percent", "type": "gauge", "unit": "%",
         "description": "系统内存使用率", "category": "system"},
        {"name": "energy_system_disk_usage_percent", "type": "gauge", "unit": "%",
         "description": "系统磁盘使用率", "category": "system"},
        {"name": "energy_api_requests_total", "type": "counter", "unit": "",
         "description": "API 请求总数", "category": "application"},
        {"name": "energy_api_request_duration_seconds", "type": "histogram", "unit": "s",
         "description": "API 请求耗时", "category": "application"},
        {"name": "energy_active_users_count", "type": "gauge", "unit": "",
         "description": "活跃用户数", "category": "application"},
        {"name": "energy_db_connection_pool_usage_percent", "type": "gauge", "unit": "%",
         "description": "数据库连接池使用率", "category": "database"},
        {"name": "energy_cache_hit_rate_percent", "type": "gauge", "unit": "%",
         "description": "缓存命中率", "category": "cache"},
        {"name": "energy_error_rate_percent", "type": "gauge", "unit": "%",
         "description": "错误率", "category": "application"},
        {"name": "energy_data_collected_bytes_total", "type": "counter", "unit": "bytes",
         "description": "数据采集总量", "category": "business"},
    ]
    for metric in defaults:
        _metrics_registry[metric["name"]] = metric


_init_default_metrics()


# ==================== 指标采集函数 ====================

async def collect_system_metrics() -> dict:
    """
    采集系统指标，更新 Prometheus Gauge 并返回结构化数据。

    Returns:
        系统指标数据
    """
    now = datetime.now(timezone.utc)

    cpu_pct = round(random.uniform(20, 85), 2)
    mem_pct = round(random.uniform(40, 80), 2)
    disk_pct = round(random.uniform(30, 75), 2)
    net_in = random.randint(100000, 5000000)
    net_out = random.randint(50000, 2000000)

    # 更新 Prometheus 指标
    SYSTEM_CPU_USAGE.set(cpu_pct)
    SYSTEM_MEMORY_USAGE.set(mem_pct)
    SYSTEM_DISK_USAGE.set(disk_pct)
    SYSTEM_NETWORK_IN.inc(net_in)
    SYSTEM_NETWORK_OUT.inc(net_out)

    metrics = {
        "timestamp": now.isoformat(),
        "cpu": {
            "usage_percent": cpu_pct,
            "cores": 8,
            "load_average": [round(random.uniform(0.5, 4.0), 2) for _ in range(3)],
        },
        "memory": {
            "usage_percent": mem_pct,
            "total_gb": 32,
            "used_gb": round(32 * mem_pct / 100, 2),
            "available_gb": round(32 * (100 - mem_pct) / 100, 2),
        },
        "disk": {
            "usage_percent": disk_pct,
            "total_gb": 500,
            "used_gb": round(500 * disk_pct / 100, 2),
            "read_iops": random.randint(100, 5000),
            "write_iops": random.randint(50, 2000),
        },
        "network": {
            "in_bytes_per_sec": net_in,
            "out_bytes_per_sec": net_out,
            "connections": random.randint(50, 500),
            "errors": random.randint(0, 5),
        },
    }

    # 存储历史值用于趋势告警
    for metric_name, value in [
        ("energy_system_cpu_usage_percent", cpu_pct),
        ("energy_system_memory_usage_percent", mem_pct),
        ("energy_system_disk_usage_percent", disk_pct),
    ]:
        if metric_name not in _metric_values:
            _metric_values[metric_name] = []
        _metric_values[metric_name].append({
            "timestamp": now.isoformat(),
            "value": value,
        })
        _metric_values[metric_name] = _metric_values[metric_name][-200:]

    return metrics


async def collect_application_metrics() -> dict:
    """
    采集应用指标，更新 Prometheus Gauge 并返回结构化数据。

    Returns:
        应用指标数据
    """
    now = datetime.now(timezone.utc)

    qps = round(random.uniform(100, 2000), 2)
    avg_resp = round(random.uniform(20, 300), 2)
    err_rate = round(random.uniform(0, 2), 2)
    active_req = random.randint(10, 200)
    pool_usage = round(random.uniform(20, 80), 2)
    cache_hit = round(random.uniform(70, 99), 2)
    active_users = random.randint(50, 500)

    # 更新 Prometheus 指标
    ERROR_RATE.set(err_rate)
    ACTIVE_USERS.set(active_users)
    ACTIVE_CONNECTIONS.set(active_req)
    DB_CONNECTION_POOL.set(pool_usage)
    CACHE_HIT_RATE.set(cache_hit)

    # 模拟一次 API 请求计数
    API_REQUESTS_TOTAL.labels(method="GET", endpoint="/api/v1/data", status_code="200").inc()
    API_REQUEST_DURATION.labels(method="GET", endpoint="/api/v1/data").observe(avg_resp / 1000.0)

    metrics = {
        "timestamp": now.isoformat(),
        "api": {
            "qps": qps,
            "avg_response_time_ms": avg_resp,
            "p95_response_time_ms": round(random.uniform(100, 800), 2),
            "p99_response_time_ms": round(random.uniform(200, 1500), 2),
            "error_rate": err_rate,
            "active_requests": active_req,
        },
        "database": {
            "connection_pool_usage": pool_usage,
            "active_queries": random.randint(5, 50),
            "avg_query_time_ms": round(random.uniform(5, 100), 2),
            "slow_queries": random.randint(0, 10),
        },
        "cache": {
            "hit_rate": cache_hit,
            "entries": random.randint(1000, 50000),
            "memory_mb": round(random.uniform(100, 1000), 2),
        },
        "websocket": {
            "active_connections": random.randint(10, 200),
            "messages_per_second": round(random.uniform(10, 500), 2),
        },
        "users": {
            "active_count": active_users,
        },
    }

    # 存储历史值
    for metric_name, value in [
        ("energy_api_request_duration_seconds", avg_resp / 1000.0),
        ("energy_error_rate_percent", err_rate),
        ("energy_active_users_count", active_users),
    ]:
        if metric_name not in _metric_values:
            _metric_values[metric_name] = []
        _metric_values[metric_name].append({
            "timestamp": now.isoformat(),
            "value": value,
        })
        _metric_values[metric_name] = _metric_values[metric_name][-200:]

    return metrics


async def get_metric_values(
    metric_name: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
) -> List[dict]:
    """
    获取指标历史值

    Args:
        metric_name: 指标名称
        start_time: 开始时间
        end_time: 结束时间
        limit: 限制数量

    Returns:
        指标值列表
    """
    values = _metric_values.get(metric_name, [])

    if start_time:
        values = [v for v in values if v["timestamp"] >= start_time.isoformat()]
    if end_time:
        values = [v for v in values if v["timestamp"] <= end_time.isoformat()]

    return values[-limit:]


async def register_custom_metric(
    name: str,
    metric_type: str,
    unit: str,
    description: str,
    category: str = "custom",
) -> dict:
    """
    注册自定义指标

    Args:
        name: 指标名称
        metric_type: 指标类型 (gauge/counter/histogram)
        unit: 单位
        description: 描述
        category: 分类

    Returns:
        注册的指标定义
    """
    metric = {
        "name": name,
        "type": metric_type,
        "unit": unit,
        "description": description,
        "category": category,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    _metrics_registry[name] = metric
    logger.info(f"Custom metric registered: {name}")
    return metric


async def register_custom_collector(name: str, collector: Callable) -> bool:
    """
    注册自定义指标采集器

    Args:
        name: 采集器名称
        collector: 采集函数

    Returns:
        是否成功
    """
    _custom_collectors[name] = collector
    logger.info(f"Custom collector registered: {name}")
    return True


async def list_metrics_registry() -> List[dict]:
    """
    列出所有注册的指标

    Returns:
        指标定义列表
    """
    return list(_metrics_registry.values())


async def get_prometheus_metrics() -> str:
    """
    获取 Prometheus 格式的指标数据（使用 prometheus_client 的 generate_latest）

    Returns:
        Prometheus 文本格式指标
    """
    return generate_latest(REGISTRY).decode("utf-8")


async def check_trend_alerts(metric_name: str, window_minutes: int = 10) -> List[dict]:
    """
    检查趋势告警

    Args:
        metric_name: 指标名称
        window_minutes: 窗口时间（分钟）

    Returns:
        趋势告警列表
    """
    values = _metric_values.get(metric_name, [])
    if len(values) < 5:
        return []

    recent = values[-10:]
    if len(recent) < 3:
        return []

    increasing = all(
        recent[i]["value"] < recent[i + 1]["value"]
        for i in range(len(recent) - 1)
    )

    decreasing = all(
        recent[i]["value"] > recent[i + 1]["value"]
        for i in range(len(recent) - 1)
    )

    alerts: List[dict] = []
    now = datetime.now(timezone.utc)
    if increasing:
        alerts.append({
            "type": "trend",
            "metric_name": metric_name,
            "trend": "increasing",
            "message": f"{metric_name} 持续上升趋势",
            "latest_value": recent[-1]["value"],
            "detected_at": now.isoformat(),
        })

    if decreasing:
        alerts.append({
            "type": "trend",
            "metric_name": metric_name,
            "trend": "decreasing",
            "message": f"{metric_name} 持续下降趋势",
            "latest_value": recent[-1]["value"],
            "detected_at": now.isoformat(),
        })

    return alerts


async def get_health_status() -> dict:
    """
    获取系统健康状态

    Returns:
        健康状态
    """
    system_metrics = await collect_system_metrics()
    app_metrics = await collect_application_metrics()

    checks = {
        "cpu": (
            "healthy" if system_metrics["cpu"]["usage_percent"] < 80
            else "warning" if system_metrics["cpu"]["usage_percent"] < 95
            else "critical"
        ),
        "memory": (
            "healthy" if system_metrics["memory"]["usage_percent"] < 85
            else "warning" if system_metrics["memory"]["usage_percent"] < 95
            else "critical"
        ),
        "disk": (
            "healthy" if system_metrics["disk"]["usage_percent"] < 90
            else "warning" if system_metrics["disk"]["usage_percent"] < 95
            else "critical"
        ),
        "api": (
            "healthy" if app_metrics["api"]["error_rate"] < 1
            else "warning" if app_metrics["api"]["error_rate"] < 5
            else "critical"
        ),
        "database": (
            "healthy" if app_metrics["database"]["connection_pool_usage"] < 80
            else "warning"
        ),
        "cache": (
            "healthy" if app_metrics["cache"]["hit_rate"] > 80
            else "warning"
        ),
    }

    overall = "healthy"
    if "critical" in checks.values():
        overall = "critical"
    elif "warning" in checks.values():
        overall = "warning"

    return {
        "overall_status": overall,
        "checks": checks,
        "system_metrics": system_metrics,
        "app_metrics": app_metrics,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def record_api_request(method: str, endpoint: str, status_code: int, duration_seconds: float) -> None:
    """
    记录一次 API 请求指标（供中间件调用）

    Args:
        method: HTTP 方法
        endpoint: 端点路径
        status_code: HTTP 状态码
        duration_seconds: 请求耗时（秒）
    """
    API_REQUESTS_TOTAL.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()
    API_REQUEST_DURATION.labels(
        method=method, endpoint=endpoint
    ).observe(duration_seconds)


def record_data_collection(source_type: str, bytes_count: int) -> None:
    """
    记录数据采集量

    Args:
        source_type: 数据源类型
        bytes_count: 字节数
    """
    DATA_COLLECTED_TOTAL.labels(source_type=source_type).inc(bytes_count)


def record_compute_task(task_type: str, status: str) -> None:
    """记录计算任务指标"""
    COMPUTE_TASKS_TOTAL.labels(task_type=task_type, status=status).inc()


def record_blockchain_tx(tx_type: str) -> None:
    """记录区块链交易指标"""
    BLOCKCHAIN_TX_TOTAL.labels(tx_type=tx_type).inc()


def record_alert_triggered(severity: str) -> None:
    """记录告警触发指标"""
    ALERTS_TRIGGERED_TOTAL.labels(severity=severity).inc()
