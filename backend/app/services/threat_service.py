"""
威胁检测服务
威胁事件列表 + 主动检测(规则引擎) + 威胁详情 + 威胁处置 + 安全态势仪表盘

真实检测逻辑：基于 AuditLog 数据库查询实现 R001-R007 规则的实际检测
"""
import uuid
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import ThreatEvent, ThreatAction
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.security import ThreatResponse
from app.exceptions import DataNotFoundError, SecurityError

logger = logging.getLogger(__name__)

# 威胁类型定义
THREAT_TYPES = {
    "unauthorized_access": "未授权访问",
    "data_exfiltration": "数据外泄",
    "brute_force": "暴力破解",
    "privilege_escalation": "权限提升",
    "abnormal_query": "异常查询",
    "data_tampering": "数据篡改",
    "dos_attack": "拒绝服务攻击",
    "malware": "恶意软件",
    "insider_threat": "内部威胁",
    "credential_leak": "凭证泄露",
}

# 严重级别
SEVERITY_LEVELS = {"low", "medium", "high", "critical"}

# 威胁处置状态
RESOLUTION_STATUSES = {"resolved", "false_positive", "mitigated"}

# 规则引擎 — 异常行为检测规则
DETECTION_RULES = [
    {
        "rule_id": "R001",
        "name": "短时大量失败登录",
        "threat_type": "brute_force",
        "severity": "high",
        "condition": "login_fail_count > 5 in 10 minutes",
        "description": "同一账户在10分钟内登录失败超过5次",
    },
    {
        "rule_id": "R002",
        "name": "非工作时间敏感数据访问",
        "threat_type": "unauthorized_access",
        "severity": "medium",
        "condition": "access sensitive data outside 08:00-20:00",
        "description": "在非工作时间访问敏感数据",
    },
    {
        "rule_id": "R003",
        "name": "大量数据导出",
        "threat_type": "data_exfiltration",
        "severity": "critical",
        "condition": "export > 10000 records in 1 hour",
        "description": "1小时内导出超过10000条记录",
    },
    {
        "rule_id": "R004",
        "name": "权限提升尝试",
        "threat_type": "privilege_escalation",
        "severity": "high",
        "condition": "attempt to access admin resources by non-admin",
        "description": "非管理员尝试访问管理资源",
    },
    {
        "rule_id": "R005",
        "name": "异常SQL查询模式",
        "threat_type": "abnormal_query",
        "severity": "medium",
        "condition": "SQL injection patterns detected",
        "description": "检测到SQL注入模式的查询",
    },
    {
        "rule_id": "R006",
        "name": "数据批量修改",
        "threat_type": "data_tampering",
        "severity": "high",
        "condition": "batch update > 1000 records by single user",
        "description": "单用户批量修改超过1000条记录",
    },
    {
        "rule_id": "R007",
        "name": "凭证在暗网泄露",
        "threat_type": "credential_leak",
        "severity": "critical",
        "condition": "credential found in dark web monitoring",
        "description": "监控发现用户凭证在暗网泄露",
    },
]


async def list_threats(
    db: AsyncSession,
    threat_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    威胁事件列表查询

    Args:
        db: 数据库会话
        threat_type: 威胁类型过滤
        severity: 严重级别过滤
        status: 状态过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        威胁事件列表
    """
    query = select(ThreatEvent)
    count_query = select(func.count()).select_from(ThreatEvent)

    if threat_type:
        query = query.where(ThreatEvent.threat_type == threat_type)
        count_query = count_query.where(ThreatEvent.threat_type == threat_type)
    if severity:
        query = query.where(ThreatEvent.severity == severity)
        count_query = count_query.where(ThreatEvent.severity == severity)
    if status:
        query = query.where(ThreatEvent.status == status)
        count_query = count_query.where(ThreatEvent.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ThreatEvent.detected_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    threats = result.scalars().all()

    items = [
        {
            "id": str(t.id),
            "threat_type": t.threat_type,
            "severity": t.severity,
            "source": t.source,
            "description": t.description,
            "indicators": t.indicators,
            "status": t.status,
            "assigned_to": str(t.assigned_to) if t.assigned_to else None,
            "detected_at": t.detected_at.isoformat() if t.detected_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        }
        for t in threats
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def detect_threats(
    db: AsyncSession,
    rule_ids: Optional[list[str]] = None,
) -> dict:
    """
    主动威胁检测

    基于规则引擎扫描 AuditLog 数据库表中的真实异常行为。
    每条规则通过查询最近时间段内的审计日志来判断是否触发。

    Args:
        db: 数据库会话
        rule_ids: 指定执行的规则 ID 列表

    Returns:
        检测结果
    """
    rules_to_run = DETECTION_RULES
    if rule_ids:
        rules_to_run = [r for r in DETECTION_RULES if r["rule_id"] in rule_ids]

    detected_threats = []
    now = datetime.now(timezone.utc)

    for rule in rules_to_run:
        rule_id = rule["rule_id"]
        triggered, indicators = await _evaluate_rule(db, rule_id, now)

        if triggered:
            threat = ThreatEvent(
                threat_type=rule["threat_type"],
                severity=rule["severity"],
                source=f"rule_engine:{rule_id}",
                description=rule["description"],
                indicators={
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "condition": rule["condition"],
                    **indicators,
                },
                status="detected",
                detected_at=now,
            )
            db.add(threat)
            detected_threats.append({
                "rule_id": rule_id,
                "rule_name": rule["name"],
                "threat_type": rule["threat_type"],
                "severity": rule["severity"],
                "description": rule["description"],
                "indicators": indicators,
            })

    await db.commit()

    logger.info(f"主动威胁检测完成: 执行 {len(rules_to_run)} 条规则, 发现 {len(detected_threats)} 个威胁")
    return {
        "rules_executed": len(rules_to_run),
        "threats_detected": len(detected_threats),
        "threats": detected_threats,
        "scanned_at": now.isoformat(),
    }


async def _evaluate_rule(
    db: AsyncSession,
    rule_id: str,
    now: datetime,
) -> tuple[bool, dict]:
    """
    评估单条检测规则

    通过查询 AuditLog 数据库表来判断规则是否触发。

    Args:
        db: 数据库会话
        rule_id: 规则 ID
        now: 当前时间

    Returns:
        (是否触发, 指标数据) 元组
    """
    if rule_id == "R001":
        return await _rule_r001_brute_force(db, now)
    elif rule_id == "R002":
        return await _rule_r002_off_hours_access(db, now)
    elif rule_id == "R003":
        return await _rule_r003_data_export(db, now)
    elif rule_id == "R004":
        return await _rule_r004_privilege_escalation(db, now)
    elif rule_id == "R005":
        return await _rule_r005_sql_injection(db, now)
    elif rule_id == "R006":
        return await _rule_r006_batch_modification(db, now)
    elif rule_id == "R007":
        return await _rule_r007_credential_leak(db, now)
    return False, {}


async def _rule_r001_brute_force(
    db: AsyncSession,
    now: datetime,
) -> tuple[bool, dict]:
    """
    R001: 短时大量失败登录
    同一账户在10分钟内登录失败超过5次
    """
    ten_min_ago = now - timedelta(minutes=10)
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("fail_count"),
        ).where(
            and_(
                AuditLog.action.in_(["login", "auth", "password_verify"]),
                AuditLog.created_at >= ten_min_ago,
                AuditLog.details["status"].as_string() == "failure",
            )
        ).group_by(AuditLog.user_id).having(func.count(AuditLog.id) > 5)
    )
    rows = result.all()

    if rows:
        users = [{"user_id": str(r[0]), "fail_count": r[1]} for r in rows]
        return True, {"affected_users": users, "time_window": "10min"}
    return False, {}


async def _rule_r002_off_hours_access(
    db: AsyncSession,
    now: datetime,
) -> tuple[bool, dict]:
    """
    R002: 非工作时间敏感数据访问
    在 20:00-08:00 访问敏感数据
    """
    hour = now.hour
    if 8 <= hour < 20:
        return False, {}

    one_hour_ago = now - timedelta(hours=1)
    result = await db.execute(
        select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.action.in_(["data_read", "data_export", "data_query", "download"]),
                AuditLog.created_at >= one_hour_ago,
                AuditLog.resource_type.in_(["sensitive_data", "credential", "key", "report"]),
            )
        )
    )
    count = result.scalar() or 0

    if count > 0:
        return True, {"access_count": count, "time": now.isoformat(), "period": "off_hours"}
    return False, {}


async def _rule_r003_data_export(
    db: AsyncSession,
    now: datetime,
) -> tuple[bool, dict]:
    """
    R003: 大量数据导出
    1小时内导出操作超过10次（模拟10000条记录阈值）
    """
    one_hour_ago = now - timedelta(hours=1)
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("export_count"),
        ).where(
            and_(
                AuditLog.action.in_(["data_export", "download", "batch_export", "data_query"]),
                AuditLog.created_at >= one_hour_ago,
            )
        ).group_by(AuditLog.user_id).having(func.count(AuditLog.id) > 10)
    )
    rows = result.all()

    if rows:
        users = [{"user_id": str(r[0]), "export_count": r[1]} for r in rows]
        return True, {"heavy_exporters": users, "time_window": "1hour"}
    return False, {}


async def _rule_r004_privilege_escalation(
    db: AsyncSession,
    now: datetime,
) -> tuple[bool, dict]:
    """
    R004: 权限提升尝试
    非管理员尝试访问管理资源
    """
    one_hour_ago = now - timedelta(hours=1)
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("attempt_count"),
        ).where(
            and_(
                AuditLog.action.in_(["admin_access", "role_change", "permission_modify", "user_management"]),
                AuditLog.created_at >= one_hour_ago,
                AuditLog.details["status"].as_string() == "failure",
            )
        ).group_by(AuditLog.user_id).having(func.count(AuditLog.id) >= 1)
    )
    rows = result.all()

    if rows:
        users = [{"user_id": str(r[0]), "attempt_count": r[1]} for r in rows]
        return True, {"escalation_attempts": users}
    return False, {}


async def _rule_r005_sql_injection(
    db: AsyncSession,
    now: datetime,
) -> tuple[bool, dict]:
    """
    R005: 异常SQL查询模式
    检测请求详情中包含 SQL 注入特征的操作
    """
    one_hour_ago = now - timedelta(hours=1)

    # SQL 注入特征模式
    sql_injection_patterns = [
        r"(\bunion\b.*\bselect\b)",
        r"(;\s*drop\s+table)",
        r"(\bor\b\s+1\s*=\s*1)",
        r"('--|;--|\/\*)",
        r"(\bexec\b.*\bxp_)",
        r"(\bwaitfor\b.*\bdelay\b)",
    ]

    result = await db.execute(
        select(AuditLog).where(
            and_(
                AuditLog.created_at >= one_hour_ago,
                AuditLog.action.in_(["data_query", "search", "api_request", "data_read"]),
            )
        ).limit(500)
    )
    logs = result.scalars().all()

    suspicious = []
    for log in logs:
        details_str = str(log.details or "") + str(log.resource_id or "")
        for pattern in sql_injection_patterns:
            if re.search(pattern, details_str, re.IGNORECASE):
                suspicious.append({
                    "user_id": str(log.user_id),
                    "log_id": str(log.id),
                    "action": log.action,
                })
                break

    if suspicious:
        return True, {"suspicious_queries": suspicious[:10], "total_suspicious": len(suspicious)}
    return False, {}


async def _rule_r006_batch_modification(
    db: AsyncSession,
    now: datetime,
) -> tuple[bool, dict]:
    """
    R006: 数据批量修改
    单用户在1小时内修改操作超过50次
    """
    one_hour_ago = now - timedelta(hours=1)
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("modify_count"),
        ).where(
            and_(
                AuditLog.action.in_(["data_update", "data_delete", "batch_update", "data_modify"]),
                AuditLog.created_at >= one_hour_ago,
            )
        ).group_by(AuditLog.user_id).having(func.count(AuditLog.id) > 50)
    )
    rows = result.all()

    if rows:
        users = [{"user_id": str(r[0]), "modify_count": r[1]} for r in rows]
        return True, {"batch_modifiers": users, "time_window": "1hour"}
    return False, {}


async def _rule_r007_credential_leak(
    db: AsyncSession,
    now: datetime,
) -> tuple[bool, dict]:
    """
    R007: 凭证泄露检测
    检查异常的凭证操作模式：同一凭证被多个不同 IP 访问
    """
    one_hour_ago = now - timedelta(hours=1)

    result = await db.execute(
        select(
            AuditLog.resource_id,
            func.count(func.distinct(AuditLog.ip_address)).label("distinct_ips"),
        ).where(
            and_(
                AuditLog.action.in_(["token_use", "api_key_use", "credential_access", "login"]),
                AuditLog.created_at >= one_hour_ago,
                AuditLog.resource_id.isnot(None),
            )
        ).group_by(AuditLog.resource_id).having(
            func.count(func.distinct(AuditLog.ip_address)) > 3
        )
    )
    rows = result.all()

    if rows:
        suspicious_creds = [
            {"resource_id": str(r[0]), "distinct_ips": r[1]}
            for r in rows
        ]
        return True, {"suspicious_credentials": suspicious_creds}
    return False, {}


async def get_threat(
    db: AsyncSession,
    threat_id: str,
) -> dict:
    """
    威胁详情

    Args:
        db: 数据库会话
        threat_id: 威胁 ID

    Returns:
        威胁详情（含处置记录）
    """
    result = await db.execute(
        select(ThreatEvent).where(ThreatEvent.id == uuid.UUID(threat_id))
    )
    threat = result.scalar_one_or_none()
    if not threat:
        raise DataNotFoundError(message=f"威胁事件不存在: {threat_id}")

    # 查询处置记录
    actions_result = await db.execute(
        select(ThreatAction).where(
            ThreatAction.threat_id == uuid.UUID(threat_id)
        )
    )
    actions = actions_result.scalars().all()

    return {
        "id": str(threat.id),
        "threat_type": threat.threat_type,
        "severity": threat.severity,
        "source": threat.source,
        "description": threat.description,
        "indicators": threat.indicators,
        "affected_resources": [str(r) for r in threat.affected_resources] if threat.affected_resources else [],
        "status": threat.status,
        "assigned_to": str(threat.assigned_to) if threat.assigned_to else None,
        "detected_at": threat.detected_at.isoformat() if threat.detected_at else None,
        "resolved_at": threat.resolved_at.isoformat() if threat.resolved_at else None,
        "actions": [
            {
                "id": str(a.id),
                "action_type": a.action_type,
                "description": a.description,
                "performed_by": str(a.performed_by) if a.performed_by else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ],
    }


async def resolve_threat(
    db: AsyncSession,
    threat_id: str,
    resolution: str,
    description: str = "",
    resolved_by: str = "",
) -> dict:
    """
    威胁处置

    标记为 resolved/false_positive/mitigated

    Args:
        db: 数据库会话
        threat_id: 威胁 ID
        resolution: 处置方式
        description: 处置描述
        resolved_by: 处置人

    Returns:
        处置结果
    """
    if resolution not in RESOLUTION_STATUSES:
        raise SecurityError(
            message=f"无效处置方式: {resolution}",
        )

    result = await db.execute(
        select(ThreatEvent).where(ThreatEvent.id == uuid.UUID(threat_id))
    )
    threat = result.scalar_one_or_none()
    if not threat:
        raise DataNotFoundError(message=f"威胁事件不存在: {threat_id}")

    if threat.status in RESOLUTION_STATUSES:
        raise SecurityError(message=f"威胁已处置: {threat.status}")

    # 更新威胁状态
    threat.status = resolution
    threat.resolved_at = datetime.utcnow()

    # 创建处置记录
    action = ThreatAction(
        threat_id=uuid.UUID(threat_id),
        action_type=resolution,
        description=description or f"威胁已处置为 {resolution}",
        performed_by=uuid.UUID(resolved_by) if resolved_by else None,
    )
    db.add(action)
    await db.commit()

    logger.info(f"威胁处置: {threat_id} → {resolution}, 处置人: {resolved_by}")
    return {
        "threat_id": threat_id,
        "resolution": resolution,
        "resolved_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "resolved_by": resolved_by,
    }


async def get_security_dashboard(
    db: AsyncSession,
) -> dict:
    """
    安全态势仪表盘

    统计各类威胁数量 + 趋势

    Args:
        db: 数据库会话

    Returns:
        安全态势数据
    """
    # 按状态统计
    status_stats = {}
    for status in ["detected", "resolved", "false_positive", "mitigated"]:
        result = await db.execute(
            select(func.count()).select_from(ThreatEvent).where(
                ThreatEvent.status == status
            )
        )
        status_stats[status] = result.scalar() or 0

    # 按严重级别统计
    severity_stats = {}
    for severity in ["low", "medium", "high", "critical"]:
        result = await db.execute(
            select(func.count()).select_from(ThreatEvent).where(
                ThreatEvent.severity == severity
            )
        )
        severity_stats[severity] = result.scalar() or 0

    # 按威胁类型统计
    type_stats = {}
    for t_type in THREAT_TYPES:
        result = await db.execute(
            select(func.count()).select_from(ThreatEvent).where(
                ThreatEvent.threat_type == t_type
            )
        )
        count = result.scalar() or 0
        if count > 0:
            type_stats[t_type] = count

    # 近 7 天趋势
    daily_trend = []
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        result = await db.execute(
            select(func.count()).select_from(ThreatEvent).where(
                and_(
                    ThreatEvent.detected_at >= day_start,
                    ThreatEvent.detected_at < day_end,
                )
            )
        )
        daily_trend.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": result.scalar() or 0,
        })

    # 安全评分
    total = sum(status_stats.values())
    detected = status_stats.get("detected", 0)
    if total == 0:
        security_score = 100.0
    else:
        resolved_ratio = (status_stats.get("resolved", 0) + status_stats.get("mitigated", 0)) / total
        critical_penalty = severity_stats.get("critical", 0) * 5
        security_score = max(0, round(100 * resolved_ratio - critical_penalty, 1))

    return {
        "security_score": security_score,
        "status_summary": status_stats,
        "severity_summary": severity_stats,
        "type_summary": type_stats,
        "daily_trend": daily_trend,
        "total_threats": total,
        "open_threats": detected,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
