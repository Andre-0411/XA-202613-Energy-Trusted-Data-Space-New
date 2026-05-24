"""
运营监控服务
业务指标采集 + 告警生成与管理（阈值/异常告警） + 告警确认 + 系统健康检查
"""
import time
import sys
import shutil
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import psutil
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Organization
from app.models.data_asset import DataSource, DataAsset
from app.models.compute_task import ComputeTask
from app.models.audit_log import AuditLog
from app.models.monitor_alert import MonitorAlert
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, OpsError

logger = logging.getLogger(__name__)

# 告警级别
ALERT_SEVERITIES = {"critical", "warning", "info"}

# 告警类型
ALERT_TYPES = {"threshold", "anomaly", "system", "security"}

# 阈值配置
THRESHOLD_CONFIG = {
    "cpu_usage": {"warning": 80, "critical": 95},
    "memory_usage": {"warning": 85, "critical": 95},
    "disk_usage": {"warning": 80, "critical": 90},
    "response_time_ms": {"warning": 2000, "critical": 5000},
    "error_rate": {"warning": 5, "critical": 10},
    "active_tasks": {"warning": 50, "critical": 100},
}

# 系统组件健康检查配置
HEALTH_CHECK_COMPONENTS = ["database", "redis", "mqtt", "fisco_blockchain"]


async def collect_metrics(
    db: AsyncSession,
) -> dict:
    """
    采集业务指标

    汇总数据源数、资产数、任务数、活跃用户数、组织数、审计日志数等

    Args:
        db: 数据库会话

    Returns:
        业务指标数据
    """
    # 数据源数量
    ds_count_result = await db.execute(
        select(func.count()).select_from(DataSource)
    )
    data_source_count = ds_count_result.scalar() or 0

    # 数据资产数量
    asset_count_result = await db.execute(
        select(func.count()).select_from(DataAsset)
    )
    asset_count = asset_count_result.scalar() or 0

    # 计算任务数量（按状态分组）
    task_total_result = await db.execute(
        select(func.count()).select_from(ComputeTask)
    )
    task_total = task_total_result.scalar() or 0

    task_running_result = await db.execute(
        select(func.count()).select_from(ComputeTask).where(
            ComputeTask.status == "running"
        )
    )
    task_running = task_running_result.scalar() or 0

    # 活跃用户数（最近 7 天登录过）
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_users_result = await db.execute(
        select(func.count()).select_from(User).where(
            and_(
                User.status == "active",
                User.last_login_at >= seven_days_ago,
            )
        )
    )
    active_users = active_users_result.scalar() or 0

    # 总用户数
    total_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.status == "active")
    )
    total_users = total_users_result.scalar() or 0

    # 组织数量
    org_count_result = await db.execute(
        select(func.count()).select_from(Organization).where(
            Organization.status == "active"
        )
    )
    org_count = org_count_result.scalar() or 0

    # 审计日志数量（今日）— 使用 naive datetime 适配 TIMESTAMP WITHOUT TIME ZONE
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    audit_today_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.created_at >= today_start
        )
    )
    audit_today = audit_today_result.scalar() or 0

    # 系统资源指标（通过 psutil 实时采集）
    mem = psutil.virtual_memory()
    # psutil.disk_usage 在某些 Windows 环境下有 C 扩展 bug，用 shutil 兜底
    try:
        disk = psutil.disk_usage("C:\\" if sys.platform == "win32" else "/")
        disk_percent = disk.percent
    except (SystemError, OSError):
        disk = shutil.disk_usage("C:\\" if sys.platform == "win32" else "/")
        disk_percent = round(disk.used / disk.total * 100, 1) if disk.total > 0 else 0.0

    # 平均响应时间：最近 100 条已完成任务的平均耗时
    avg_resp_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", ComputeTask.completed_at - ComputeTask.started_at) * 1000
            )
        ).where(
            and_(
                ComputeTask.completed_at.isnot(None),
                ComputeTask.started_at.isnot(None),
            )
        )
    )
    avg_response_time_ms = round(avg_resp_result.scalar() or 0, 1)

    # 错误率：最近 24 小时告警数 / 总任务数（百分比）
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_alerts_result = await db.execute(
        select(func.count()).select_from(MonitorAlert).where(
            and_(
                MonitorAlert.fired_at >= twenty_four_hours_ago,
                MonitorAlert.severity.in_(["critical", "warning"]),
            )
        )
    )
    recent_alerts = recent_alerts_result.scalar() or 0
    error_rate = round((recent_alerts / max(task_total, 1)) * 100, 2)

    # 系统运行时间
    uptime_seconds = int(time.time() - psutil.boot_time())

    system_metrics = {
        "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
        "memory_usage_percent": round(mem.percent, 1),
        "disk_usage_percent": round(disk_percent, 1),
        "avg_response_time_ms": avg_response_time_ms,
        "error_rate_percent": error_rate,
        "uptime_seconds": uptime_seconds,
    }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "business_metrics": {
            "data_source_count": data_source_count,
            "data_asset_count": asset_count,
            "compute_task_total": task_total,
            "compute_task_running": task_running,
            "active_users": active_users,
            "total_users": total_users,
            "organization_count": org_count,
            "audit_logs_today": audit_today,
        },
        "system_metrics": system_metrics,
        "thresholds": THRESHOLD_CONFIG,
    }


async def generate_alert(
    db: AsyncSession,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    source: str = "system",
    metadata: Optional[dict] = None,
) -> dict:
    """
    生成告警（持久化到数据库）

    Args:
        db: 数据库会话
        alert_type: 告警类型 (threshold/anomaly/system/security)
        severity: 严重级别 (critical/warning/info)
        title: 告警标题
        message: 告警消息
        source: 告警来源
        metadata: 附加信息

    Returns:
        告警信息
    """
    if alert_type not in ALERT_TYPES:
        raise OpsError(message=f"无效告警类型: {alert_type}")
    if severity not in ALERT_SEVERITIES:
        raise OpsError(message=f"无效告警级别: {severity}")

    alert = MonitorAlert(
        type=alert_type,
        severity=severity,
        title=title,
        message=message,
        source=source,
        status="firing",
        alert_metadata=metadata or {},
        # fired_at 字段为 DateTime(timezone=True)，必须传入 timezone-aware datetime
        fired_at=datetime.now(timezone.utc),
    )
    db.add(alert)
    await db.flush()

    logger.warning(f"告警生成: [{severity.upper()}] {title} - {message}")
    return alert.to_dict()


async def list_alerts(
    db: AsyncSession,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    查询告警列表

    Args:
        db: 数据库会话
        status: 状态过滤 (firing/acked/resolved)
        severity: 级别过滤
        alert_type: 类型过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        告警列表
    """
    query = select(MonitorAlert)
    count_query = select(func.count()).select_from(MonitorAlert)

    if status:
        query = query.where(MonitorAlert.status == status)
        count_query = count_query.where(MonitorAlert.status == status)
    if severity:
        query = query.where(MonitorAlert.severity == severity)
        count_query = count_query.where(MonitorAlert.severity == severity)
    if alert_type:
        query = query.where(MonitorAlert.type == alert_type)
        count_query = count_query.where(MonitorAlert.type == alert_type)

    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询，按触发时间倒序
    query = query.order_by(desc(MonitorAlert.fired_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    alerts = [row.to_dict() for row in result.scalars().all()]

    return {
        "items": alerts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def acknowledge_alert(
    db: AsyncSession,
    alert_id: str,
    acknowledged_by: str = "",
) -> dict:
    """
    确认告警

    Args:
        db: 数据库会话
        alert_id: 告警 ID
        acknowledged_by: 确认人 ID

    Returns:
        更新后的告警信息
    """
    result = await db.execute(
        select(MonitorAlert).where(MonitorAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise DataNotFoundError(message=f"告警不存在: {alert_id}")

    alert.status = "acked"
    alert.acknowledged_by = acknowledged_by
    # acknowledged_at 字段为 DateTime(timezone=True)，必须传入 timezone-aware datetime
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(f"告警已确认: {alert_id}, 确认人: {acknowledged_by}")
    return alert.to_dict()


async def check_system_health(
    db: AsyncSession,
) -> dict:
    """
    系统健康检查

    检查数据库、Redis、MQTT、FISCO区块链连接状态

    Args:
        db: 数据库会话

    Returns:
        各组件健康状态
    """
    components = {}

    # 1. 数据库健康检查（真实计时）
    try:
        t0 = time.time()
        await db.execute(select(1))
        latency = round((time.time() - t0) * 1000, 1)
        components["database"] = {
            "status": "healthy",
            "latency_ms": latency,
            "details": "PostgreSQL 连接正常",
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "latency_ms": None,
            "details": f"PostgreSQL 连接异常: {str(e)}",
        }

    # 2. Redis 健康检查（真实计时）
    try:
        from app.database import get_redis
        redis = await get_redis()
        t0 = time.time()
        await redis.ping()
        latency = round((time.time() - t0) * 1000, 1)
        components["redis"] = {
            "status": "healthy",
            "latency_ms": latency,
            "details": "Redis 连接正常",
        }
    except Exception as e:
        components["redis"] = {
            "status": "unhealthy",
            "latency_ms": None,
            "details": f"Redis 连接异常: {str(e)}",
        }

    # 3. MQTT 健康检查
    try:
        from app.services.mqtt_client import mqtt_client
        mqtt_connected = mqtt_client.is_connected() if hasattr(mqtt_client, "is_connected") else True
        components["mqtt"] = {
            "status": "healthy" if mqtt_connected else "degraded",
            "latency_ms": None,  # MQTT 无简单 ping 机制，延迟不可测
            "details": "MQTT 连接正常" if mqtt_connected else "MQTT 连接不稳定",
        }
    except Exception as e:
        components["mqtt"] = {
            "status": "degraded",
            "latency_ms": None,
            "details": f"MQTT 状态未知: {str(e)}",
        }

    # 4. FISCO 区块链健康检查（真实计时）
    try:
        from app.core.fisco_client import fisco_client
        if hasattr(fisco_client, "get_block_number"):
            t0 = time.time()
            block_number = await fisco_client.get_block_number()
            latency = round((time.time() - t0) * 1000, 1)
        else:
            block_number = "N/A"
            latency = None
        components["fisco_blockchain"] = {
            "status": "healthy",
            "latency_ms": latency,
            "details": f"FISCO BCOS 连接正常, 区块高度: {block_number}",
        }
    except Exception as e:
        components["fisco_blockchain"] = {
            "status": "unhealthy",
            "latency_ms": None,
            "details": f"FISCO BCOS 连接异常: {str(e)}",
        }

    # 总体状态
    all_statuses = [c["status"] for c in components.values()]
    if all(s == "healthy" for s in all_statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in all_statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "overall_status": overall_status,
        "components": components,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def check_threshold_alerts(
    db: AsyncSession,
) -> list[dict]:
    """
    检查阈值并生成告警

    比较当前指标与配置的阈值，超限则自动生成告警

    Args:
        db: 数据库会话

    Returns:
        新生成的告警列表
    """
    metrics = await collect_metrics(db)
    system_metrics = metrics.get("system_metrics", {})
    new_alerts = []

    # CPU 使用率检查
    cpu = system_metrics.get("cpu_usage_percent", 0)
    if cpu >= THRESHOLD_CONFIG["cpu_usage"]["critical"]:
        alert = await generate_alert(
            db=db,
            alert_type="threshold",
            severity="critical",
            title="CPU 使用率过高",
            message=f"当前 CPU 使用率 {cpu}%，超过临界阈值 {THRESHOLD_CONFIG['cpu_usage']['critical']}%",
            source="system_monitor",
            metadata={"metric": "cpu_usage", "value": cpu},
        )
        new_alerts.append(alert)
    elif cpu >= THRESHOLD_CONFIG["cpu_usage"]["warning"]:
        alert = await generate_alert(
            db=db,
            alert_type="threshold",
            severity="warning",
            title="CPU 使用率偏高",
            message=f"当前 CPU 使用率 {cpu}%，超过警告阈值 {THRESHOLD_CONFIG['cpu_usage']['warning']}%",
            source="system_monitor",
            metadata={"metric": "cpu_usage", "value": cpu},
        )
        new_alerts.append(alert)

    # 内存使用率检查
    memory = system_metrics.get("memory_usage_percent", 0)
    if memory >= THRESHOLD_CONFIG["memory_usage"]["critical"]:
        alert = await generate_alert(
            db=db,
            alert_type="threshold",
            severity="critical",
            title="内存使用率过高",
            message=f"当前内存使用率 {memory}%，超过临界阈值 {THRESHOLD_CONFIG['memory_usage']['critical']}%",
            source="system_monitor",
            metadata={"metric": "memory_usage", "value": memory},
        )
        new_alerts.append(alert)
    elif memory >= THRESHOLD_CONFIG["memory_usage"]["warning"]:
        alert = await generate_alert(
            db=db,
            alert_type="threshold",
            severity="warning",
            title="内存使用率偏高",
            message=f"当前内存使用率 {memory}%，超过警告阈值 {THRESHOLD_CONFIG['memory_usage']['warning']}%",
            source="system_monitor",
            metadata={"metric": "memory_usage", "value": memory},
        )
        new_alerts.append(alert)

    # 错误率检查
    error_rate = system_metrics.get("error_rate_percent", 0)
    if error_rate >= THRESHOLD_CONFIG["error_rate"]["critical"]:
        alert = await generate_alert(
            db=db,
            alert_type="anomaly",
            severity="critical",
            title="系统错误率过高",
            message=f"当前错误率 {error_rate}%，超过临界阈值 {THRESHOLD_CONFIG['error_rate']['critical']}%",
            source="system_monitor",
            metadata={"metric": "error_rate", "value": error_rate},
        )
        new_alerts.append(alert)

    return new_alerts
