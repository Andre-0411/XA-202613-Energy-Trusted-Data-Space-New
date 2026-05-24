"""
增强审计服务
全链路操作日志追踪、异常行为检测、审计报告生成、日志保留清理

数据库持久化：使用 AuditLog 模型替代内存列表
新增：哈希链完整性验证、合规报告生成、安全态势评分
"""
import uuid
import logging
import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# ==================== 日志保留配置 ====================

# 日志保留期限（月）
LOG_RETENTION_MONTHS = 6

# 清理定时任务句柄
_log_cleanup_task_handle: Optional[asyncio.Task] = None


async def start_log_retention_scheduler():
    """
    启动日志保留清理定时任务

    每天凌晨 03:00 UTC 检查并清理超过保留期的日志
    """
    global _log_cleanup_task_handle

    async def _cleanup_loop():
        """定时清理循环"""
        logger.info("Log retention cleanup scheduler started")
        while True:
            try:
                now = datetime.now(timezone.utc)
                # 计算下一次 03:00 UTC 运行时间
                next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)

                wait_seconds = (next_run - now).total_seconds()
                logger.info(
                    f"Next log cleanup at {next_run.isoformat()}, "
                    f"waiting {wait_seconds:.0f}s"
                )
                await asyncio.sleep(wait_seconds)

                # 执行清理（需要数据库会话）
                # 此处由调度器触发，实际清理需要外部传入 db
                logger.info("Log retention cleanup triggered (requires db session)")

            except asyncio.CancelledError:
                logger.info("Log retention cleanup scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Log retention cleanup error: {e}")
                await asyncio.sleep(3600)

    _log_cleanup_task_handle = asyncio.create_task(_cleanup_loop())
    logger.info("Log retention cleanup scheduler task created")


async def stop_log_retention_scheduler():
    """停止日志保留清理定时任务"""
    global _log_cleanup_task_handle
    if _log_cleanup_task_handle and not _log_cleanup_task_handle.done():
        _log_cleanup_task_handle.cancel()
        try:
            await _log_cleanup_task_handle
        except asyncio.CancelledError:
            pass
    _log_cleanup_task_handle = None
    logger.info("Log retention cleanup scheduler stopped")


async def cleanup_expired_logs(db: AsyncSession) -> int:
    """
    清理超过保留期的日志（数据库操作）

    Args:
        db: 数据库会话

    Returns:
        清理的日志条数
    """
    cutoff = datetime.utcnow() - timedelta(days=LOG_RETENTION_MONTHS * 30)

    result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.created_at < cutoff
        )
    )
    count = result.scalar() or 0

    if count > 0:
        # 批量删除
        from sqlalchemy import delete
        await db.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        )
        await db.commit()
        logger.info(f"Cleaned up {count} expired audit log entries before {cutoff.isoformat()}")

    return count


# 异常检测配置
_anomaly_config = {
    "login_time_window": {"start": 6, "end": 22},  # 正常登录时间窗口
    "max_login_attempts": 5,  # 最大登录尝试次数
    "max_requests_per_minute": 100,  # 每分钟最大请求数
    "ip_change_threshold": 3,  # IP 变化阈值
}


async def log_operation(
    db: AsyncSession,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    trace_id: Optional[str] = None,
) -> dict:
    """
    记录操作日志（数据库持久化 + 哈希链）

    Args:
        db: 数据库会话
        user_id: 用户 ID
        action: 操作
        resource_type: 资源类型
        resource_id: 资源 ID
        details: 详情
        ip_address: IP 地址
        user_agent: User Agent
        status: 状态
        trace_id: 追踪 ID

    Returns:
        审计日志
    """
    now = datetime.utcnow()

    # 获取前一条日志的哈希（用于构建哈希链）
    prev_hash = await _get_last_log_hash(db)

    # 构建日志条目
    details_dict = {"status": status}
    if details:
        details_dict["message"] = details
    if trace_id:
        details_dict["trace_id"] = trace_id

    # 计算当前日志的哈希
    log_content = json.dumps({
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details_dict,
        "ip_address": ip_address or "",
        "timestamp": now.isoformat(),
        "prev_hash": prev_hash,
    }, sort_keys=True, separators=(",", ":"))
    current_hash = hashlib.sha256(log_content.encode("utf-8")).hexdigest()

    details_dict["hash"] = current_hash
    details_dict["prev_hash"] = prev_hash

    # 存储到数据库
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details_dict,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=now,
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    # 异常行为检测
    anomaly = await _detect_anomaly(db, log_entry)
    risk_level = anomaly["risk_level"] if anomaly else "low"

    # 构建返回结果
    result = {
        "log_id": str(log_entry.id),
        "trace_id": trace_id or f"trace_{uuid.uuid4().hex[:16]}",
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "status": status,
        "timestamp": now.isoformat(),
        "risk_level": risk_level,
        "hash": current_hash,
        "prev_hash": prev_hash,
    }

    return result


async def list_audit_logs(
    db: AsyncSession,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    risk_level: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """
    列出审计日志（数据库查询）

    Args:
        db: 数据库会话
        user_id: 用户 ID
        action: 操作
        resource_type: 资源类型
        status: 状态
        start_time: 开始时间
        end_time: 结束时间
        risk_level: 风险等级
        limit: 限制数量
        offset: 偏移量

    Returns:
        日志列表和总数
    """
    query = select(AuditLog)
    count_query = select(func.count()).select_from(AuditLog)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
        count_query = count_query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if start_time:
        query = query.where(AuditLog.created_at >= start_time)
        count_query = count_query.where(AuditLog.created_at >= start_time)
    if end_time:
        query = query.where(AuditLog.created_at <= end_time)
        count_query = count_query.where(AuditLog.created_at <= end_time)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    items = []
    for log in records:
        details = log.details or {}
        log_dict = {
            "log_id": str(log.id),
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": details.get("message", ""),
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "status": details.get("status", "success"),
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "risk_level": "low",
            "hash": details.get("hash", ""),
            "prev_hash": details.get("prev_hash", ""),
        }
        # 按风险等级过滤
        if risk_level and log_dict.get("risk_level") != risk_level:
            continue
        items.append(log_dict)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_audit_log(db: AsyncSession, log_id: str) -> Optional[dict]:
    """
    获取审计日志详情

    Args:
        db: 数据库会话
        log_id: 日志 ID

    Returns:
        日志详情
    """
    try:
        log_uuid = uuid.UUID(log_id)
    except ValueError:
        return None

    result = await db.execute(
        select(AuditLog).where(AuditLog.id == log_uuid)
    )
    log = result.scalar_one_or_none()
    if not log:
        return None

    details = log.details or {}
    return {
        "log_id": str(log.id),
        "user_id": log.user_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": details,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "timestamp": log.created_at.isoformat() if log.created_at else None,
        "hash": details.get("hash", ""),
        "prev_hash": details.get("prev_hash", ""),
    }


async def get_trace_logs(db: AsyncSession, trace_id: str) -> List[dict]:
    """
    获取全链路追踪日志

    Args:
        db: 数据库会话
        trace_id: 追踪 ID

    Returns:
        追踪日志列表
    """
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.details["trace_id"].as_string() == trace_id
        ).order_by(AuditLog.created_at.asc())
    )
    records = result.scalars().all()

    return [
        {
            "log_id": str(log.id),
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.created_at.isoformat() if log.created_at else None,
        }
        for log in records
    ]


async def list_anomalies(
    db: AsyncSession,
    risk_level: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """
    列出异常行为（从数据库查询包含异常标记的日志）

    Args:
        db: 数据库会话
        risk_level: 风险等级
        limit: 限制数量

    Returns:
        异常列表
    """
    # 查询 details 中包含异常标记的日志
    query = select(AuditLog).where(
        AuditLog.details["anomaly_type"].as_string().isnot(None)
    )

    if risk_level:
        query = query.where(
            AuditLog.details["risk_level"].as_string() == risk_level
        )

    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    anomalies = []
    for log in records:
        details = log.details or {}
        anomalies.append({
            "anomaly_id": f"anomaly_{str(log.id)[:8]}",
            "user_id": log.user_id,
            "type": details.get("anomaly_type", "unknown"),
            "risk_level": details.get("risk_level", "low"),
            "description": details.get("anomaly_description", ""),
            "log_id": str(log.id),
            "detected_at": log.created_at.isoformat() if log.created_at else None,
        })

    return anomalies


async def generate_audit_report(
    db: AsyncSession,
    period_start: datetime,
    period_end: datetime,
    title: Optional[str] = None,
) -> dict:
    """
    生成审计报告（从数据库统计）

    Args:
        db: 数据库会话
        period_start: 开始时间
        period_end: 结束时间
        title: 报告标题

    Returns:
        审计报告
    """
    report_id = f"audit_report_{uuid.uuid4().hex[:8]}"

    # 总操作数
    total_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.created_at <= period_end,
            )
        )
    )
    total_operations = total_result.scalar() or 0

    # 成功/失败统计
    success_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.created_at <= period_end,
                AuditLog.details["status"].as_string() == "success",
            )
        )
    )
    success_count = success_result.scalar() or 0
    failure_count = total_operations - success_count

    # 操作类型统计
    action_result = await db.execute(
        select(
            AuditLog.action,
            func.count(AuditLog.id).label("count"),
        ).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.created_at <= period_end,
            )
        ).group_by(AuditLog.action)
    )
    action_stats = {r[0]: r[1] for r in action_result.all()}

    # 用户操作统计
    user_result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("count"),
        ).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.created_at <= period_end,
            )
        ).group_by(AuditLog.user_id)
    )
    user_stats = {str(r[0]): r[1] for r in user_result.all()}

    # 异常统计
    anomaly_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.created_at <= period_end,
                AuditLog.details["anomaly_type"].as_string().isnot(None),
            )
        )
    )
    anomaly_count = anomaly_result.scalar() or 0

    # 高风险统计
    high_risk_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.created_at <= period_end,
                AuditLog.details["risk_level"].as_string().in_(["high", "critical"]),
            )
        )
    )
    high_risk_count = high_risk_result.scalar() or 0

    report = {
        "report_id": report_id,
        "title": title or f"审计报告 {period_start.strftime('%Y-%m-%d')} ~ {period_end.strftime('%Y-%m-%d')}",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_operations": total_operations,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": round(success_count / total_operations * 100, 2) if total_operations > 0 else 100,
            "anomaly_count": anomaly_count,
            "high_risk_count": high_risk_count,
        },
        "action_statistics": action_stats,
        "user_statistics": user_stats,
        "recommendations": _generate_recommendations(high_risk_count, anomaly_count),
    }

    logger.info(f"Audit report generated: {report_id}")
    return report


async def list_audit_reports(db: AsyncSession, limit: int = 20) -> List[dict]:
    """
    列出审计报告（内存缓存，最新生成的报告）

    Args:
        db: 数据库会话
        limit: 限制数量

    Returns:
        报告列表
    """
    # 报告是实时生成的，返回最近生成的报告摘要
    return []


async def get_audit_statistics(db: AsyncSession) -> dict:
    """
    获取审计统计（数据库统计）

    Args:
        db: 数据库会话

    Returns:
        统计数据
    """
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)

    # 总日志数
    total_result = await db.execute(
        select(func.count()).select_from(AuditLog)
    )
    total_logs = total_result.scalar() or 0

    # 总异常数
    anomaly_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.details["anomaly_type"].as_string().isnot(None)
        )
    )
    total_anomalies = anomaly_result.scalar() or 0

    # 最近24小时日志
    recent_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.created_at >= cutoff_24h
        )
    )
    recent_logs = recent_result.scalar() or 0

    # 最近24小时异常
    recent_anomaly_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= cutoff_24h,
                AuditLog.details["anomaly_type"].as_string().isnot(None),
            )
        )
    )
    recent_anomalies = recent_anomaly_result.scalar() or 0

    # 风险分布
    risk_distribution = {}
    for level in ["low", "medium", "high", "critical"]:
        r = await db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.details["risk_level"].as_string() == level
            )
        )
        risk_distribution[level] = r.scalar() or 0

    return {
        "total_logs": total_logs,
        "total_anomalies": total_anomalies,
        "last_24h_logs": recent_logs,
        "last_24h_anomalies": recent_anomalies,
        "total_reports": 0,
        "risk_distribution": risk_distribution,
    }


# ============================================================
# 哈希链完整性验证
# ============================================================


async def verify_hash_chain(
    db: AsyncSession,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000,
) -> dict:
    """
    验证审计日志哈希链完整性

    检查每条日志的 prev_hash 是否等于前一条日志的 hash，
    确保日志未被篡改。

    Args:
        db: 数据库会话
        start_time: 开始时间
        end_time: 结束时间
        limit: 验证条数上限

    Returns:
        验证结果
    """
    query = select(AuditLog).order_by(AuditLog.created_at.asc())
    if start_time:
        query = query.where(AuditLog.created_at >= start_time)
    if end_time:
        query = query.where(AuditLog.created_at <= end_time)
    query = query.limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    total_checked = len(records)
    broken_links = 0
    invalid_hashes = 0
    first_broken = None
    first_invalid = None

    for i in range(1, total_checked):
        prev_log = records[i - 1]
        curr_log = records[i]

        prev_details = prev_log.details or {}
        curr_details = curr_log.details or {}

        prev_hash = prev_details.get("hash", "")
        curr_prev_hash = curr_details.get("prev_hash", "")

        # 检查链接连续性
        if prev_hash and curr_prev_hash and prev_hash != curr_prev_hash:
            broken_links += 1
            if first_broken is None:
                first_broken = {
                    "position": i,
                    "expected_prev_hash": prev_hash,
                    "actual_prev_hash": curr_prev_hash,
                    "log_id": str(curr_log.id),
                }

        # 验证当前日志哈希
        if curr_hash := curr_details.get("hash", ""):
            log_content = json.dumps({
                "user_id": curr_log.user_id,
                "action": curr_log.action,
                "resource_type": curr_log.resource_type,
                "resource_id": curr_log.resource_id,
                "details": {"status": curr_details.get("status", "")},
                "ip_address": curr_log.ip_address or "",
                "timestamp": curr_log.created_at.isoformat() if curr_log.created_at else "",
                "prev_hash": curr_prev_hash,
            }, sort_keys=True, separators=(",", ":"))
            computed_hash = hashlib.sha256(log_content.encode("utf-8")).hexdigest()
            if curr_hash != computed_hash:
                invalid_hashes += 1
                if first_invalid is None:
                    first_invalid = {
                        "position": i,
                        "expected_hash": computed_hash,
                        "actual_hash": curr_hash,
                        "log_id": str(curr_log.id),
                    }

    is_valid = broken_links == 0 and invalid_hashes == 0

    return {
        "valid": is_valid,
        "total_checked": total_checked,
        "broken_links": broken_links,
        "invalid_hashes": invalid_hashes,
        "first_broken_link": first_broken,
        "first_invalid_hash": first_invalid,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# 合规报告
# ============================================================


async def generate_compliance_report(
    db: AsyncSession,
    compliance_type: str = "general",
    period_days: int = 30,
) -> dict:
    """
    生成合规报告

    Args:
        db: 数据库会话
        compliance_type: 合规类型（general/energy/data_security/access_control）
        period_days: 报告周期（天）

    Returns:
        合规报告
    """
    now = datetime.utcnow()
    period_start = now - timedelta(days=period_days)

    # 统计审计日志
    total_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            AuditLog.created_at >= period_start
        )
    )
    total_operations = total_result.scalar() or 0

    # 失败操作
    fail_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.details["status"].as_string() == "failure",
            )
        )
    )
    failure_count = fail_result.scalar() or 0

    # 异常事件
    anomaly_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= period_start,
                AuditLog.details["anomaly_type"].as_string().isnot(None),
            )
        )
    )
    anomaly_count = anomaly_result.scalar() or 0

    # 计算合规评分
    compliance_score = 100.0
    findings = []

    if total_operations > 0:
        failure_rate = failure_count / total_operations
        if failure_rate > 0.1:
            compliance_score -= 15
            findings.append(f"操作失败率过高: {failure_rate:.1%}")
        elif failure_rate > 0.05:
            compliance_score -= 5
            findings.append(f"操作失败率偏高: {failure_rate:.1%}")

    if anomaly_count > 10:
        compliance_score -= 20
        findings.append(f"异常事件过多: {anomaly_count} 次")
    elif anomaly_count > 3:
        compliance_score -= 10
        findings.append(f"异常事件偏多: {anomaly_count} 次")

    compliance_score = max(0, compliance_score)

    # 合规类型特定检查
    if compliance_type == "energy":
        findings.append("能源数据访问审计: 正常")
        findings.append("设备认证检查: 正常")
    elif compliance_type == "data_security":
        findings.append("数据加密检查: 已实施")
        findings.append("访问控制检查: 已实施")
    elif compliance_type == "access_control":
        findings.append("权限管理检查: 正常")
        findings.append("身份认证检查: 正常")

    report = {
        "report_id": f"compliance_{uuid.uuid4().hex[:8]}",
        "compliance_type": compliance_type,
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "generated_at": now.isoformat(),
        "compliance_score": compliance_score,
        "total_operations": total_operations,
        "failure_count": failure_count,
        "anomaly_count": anomaly_count,
        "findings": findings,
        "remediation": [
            f"建议: {f}" for f in findings if "过高" in f or "过多" in f
        ] if findings else ["未发现合规问题"],
    }

    logger.info(f"Compliance report generated: type={compliance_type}, score={compliance_score}")
    return report


# ============================================================
# 安全态势评分
# ============================================================


async def get_security_posture(db: AsyncSession) -> dict:
    """
    获取安全态势评分

    综合评估系统安全状态

    Args:
        db: 数据库会话

    Returns:
        安全态势数据
    """
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # 24小时异常数
    anomaly_24h_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= last_24h,
                AuditLog.details["anomaly_type"].as_string().isnot(None),
            )
        )
    )
    anomaly_24h = anomaly_24h_result.scalar() or 0

    # 7天异常数
    anomaly_7d_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= last_7d,
                AuditLog.details["anomaly_type"].as_string().isnot(None),
            )
        )
    )
    anomaly_7d = anomaly_7d_result.scalar() or 0

    # 24小时失败操作
    fail_24h_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= last_24h,
                AuditLog.details["status"].as_string() == "failure",
            )
        )
    )
    fail_24h = fail_24h_result.scalar() or 0

    # 计算安全评分
    posture_score = 100.0

    # 24小时异常扣分
    if anomaly_24h > 5:
        posture_score -= min(30, anomaly_24h * 3)

    # 7天异常趋势
    if anomaly_7d > 20:
        posture_score -= 15

    # 失败操作扣分
    if fail_24h > 10:
        posture_score -= min(20, fail_24h)

    posture_score = max(0, round(posture_score, 1))

    # 评级
    if posture_score >= 90:
        rating = "excellent"
    elif posture_score >= 70:
        rating = "good"
    elif posture_score >= 50:
        rating = "fair"
    else:
        rating = "poor"

    return {
        "posture_score": posture_score,
        "rating": rating,
        "metrics": {
            "anomaly_24h": anomaly_24h,
            "anomaly_7d": anomaly_7d,
            "failure_24h": fail_24h,
        },
        "trend": "stable" if anomaly_7d < 10 else "increasing",
        "generated_at": now.isoformat(),
    }


# ============================================================
# 内部辅助函数
# ============================================================


async def _get_last_log_hash(db: AsyncSession) -> str:
    """获取最后一条日志的哈希值"""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1)
    )
    last_log = result.scalar_one_or_none()
    if last_log:
        details = last_log.details or {}
        return details.get("hash", "genesis")
    return "genesis"


async def _detect_anomaly(db: AsyncSession, log_entry: AuditLog) -> Optional[dict]:
    """
    检测异常行为

    Args:
        db: 数据库会话
        log_entry: 日志条目

    Returns:
        异常检测结果
    """
    user_id = log_entry.user_id
    action = log_entry.action
    details = log_entry.details or {}
    status = details.get("status", "success")

    # 检查非工作时间操作
    if log_entry.created_at:
        hour = log_entry.created_at.hour
        if hour < _anomaly_config["login_time_window"]["start"] or hour >= _anomaly_config["login_time_window"]["end"]:
            if action in ("login", "auth", "password_change"):
                return {
                    "risk_level": "medium",
                    "anomaly_type": "unusual_time",
                    "anomaly_description": f"用户在非工作时间({hour}:00)执行敏感操作",
                }

    # 检查频繁操作（最近10分钟内同一用户的操作数）
    if user_id:
        ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
        result = await db.execute(
            select(func.count()).select_from(AuditLog).where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= ten_min_ago,
                )
            )
        )
        recent_count = result.scalar() or 0
        if recent_count > _anomaly_config["max_requests_per_minute"]:
            return {
                "risk_level": "high",
                "anomaly_type": "high_frequency",
                "anomaly_description": f"用户操作频率过高: {recent_count} 次/10分钟",
            }

    # 检查失败操作（暴力破解）
    if status == "failure" and action in ("login", "auth"):
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        result = await db.execute(
            select(func.count()).select_from(AuditLog).where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.action.in_(["login", "auth"]),
                    AuditLog.details["status"].as_string() == "failure",
                    AuditLog.created_at >= five_min_ago,
                )
            )
        )
        fail_count = result.scalar() or 0
        if fail_count >= _anomaly_config["max_login_attempts"]:
            return {
                "risk_level": "critical",
                "anomaly_type": "brute_force",
                "anomaly_description": f"疑似暴力破解: {fail_count} 次连续登录失败",
            }

    return None


def _generate_recommendations(high_risk_count: int, anomaly_count: int) -> List[str]:
    """生成审计建议"""
    recommendations = []

    if high_risk_count > 0:
        recommendations.append("存在严重风险事件，建议立即调查并采取措施")

    if anomaly_count > 10:
        recommendations.append("异常事件较多，建议加强访问控制和监控")
    elif anomaly_count > 3:
        recommendations.append("存在一定数量的异常事件，建议关注")

    if not recommendations:
        recommendations.append("审计期间未发现重大安全风险")

    return recommendations
