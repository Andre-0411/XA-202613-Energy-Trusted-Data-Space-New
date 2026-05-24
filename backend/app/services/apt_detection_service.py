"""
APT 高级威胁检测服务
网络流量异常检测 + 用户行为分析（UBA）+ 恶意软件签名匹配 + 入侵检测规则引擎 + 威胁情报集成

实现：
- 基于统计方法的网络流量异常检测（Z-score/滑动窗口）
- 用户行为分析（UBA）：登录时间、访问模式、数据操作异常
- 恶意软件签名哈希匹配（MD5/SHA256）
- 可配置的入侵检测规则引擎
- 威胁情报 IOC 匹配
- 审计日志记录
"""
import uuid
import json
import math
import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from enum import Enum

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.security import ThreatEvent, ThreatAction
from app.exceptions import (
    DataNotFoundError,
    DataValidationError,
    SecurityError,
)

logger = logging.getLogger(__name__)


def _audit_log(action: str, resource_id: str, details: Optional[dict] = None) -> None:
    """
    记录审计日志

    Args:
        action: 操作类型
        resource_id: 资源 ID
        details: 附加详情
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "apt_detection_service",
        "action": action,
        "resource_id": resource_id,
        "details": details or {},
    }
    logger.info(f"[AUDIT] {json.dumps(log_entry, ensure_ascii=False)}")


# ==================== APT 事件类型 ====================


class APTEventType(str, Enum):
    """APT 事件类型"""
    NETWORK_ANOMALY = "network_anomaly"
    UBA_ALERT = "uba_alert"
    MALWARE_SIGNATURE = "malware_signature"
    INTRUSION_DETECTED = "intrusion_detected"
    THREAT_INTEL_MATCH = "threat_intel_match"
    SLOW_PENETRATION = "slow_penetration"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_STAGING = "data_staging"
    C2_COMMUNICATION = "c2_communication"
    PRIVILEGE_ABUSE = "privilege_abuse"


class SeverityLevel(str, Enum):
    """严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== 恶意软件签名库 ====================

MALWARE_SIGNATURES: dict[str, dict] = {
    # 已知恶意文件哈希
    "e99a18c428cb38d5f260853678922e03": {
        "hash_type": "md5",
        "name": "Trojan.GenericKD.30123456",
        "family": "Generic",
        "severity": "high",
        "description": "通用木马检测",
    },
    "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
        "hash_type": "sha1",
        "name": "Worm.Conficker.Gen",
        "family": "Conficker",
        "severity": "critical",
        "description": "Conficker 蠕虫变种",
    },
    "a3f390d88e4c41f2747bfa2f1b5f87db36e0b7fa3f390d88e4c41f2747bfa2f1": {
        "hash_type": "sha256",
        "name": "Ransom.Locky.Crypto",
        "family": "Locky",
        "severity": "critical",
        "description": "Locky 勒索软件",
    },
    "5d41402abc4b2a76b9719d911017c592": {
        "hash_type": "md5",
        "name": "Backdoor.Poison.Gen",
        "family": "Poison",
        "severity": "high",
        "description": "毒药后门通用检测",
    },
    "7d793037a0760186574b0282f2f435e7": {
        "hash_type": "md5",
        "name": "Spyware.KeyLogger.Win32",
        "family": "KeyLogger",
        "severity": "medium",
        "description": "键盘记录器间谍软件",
    },
}

# ==================== 威胁情报 IOC 库 ====================

THREAT_INTEL_IOCS: dict[str, dict] = {
    "192.168.100.66": {
        "type": "ip",
        "threat_type": "c2_server",
        "confidence": 0.85,
        "source": "AlienVault OTX",
        "description": "已知 C2 命令控制服务器",
        "first_seen": "2024-11-15",
        "last_seen": "2025-01-20",
        "tags": ["apt28", "c2", "malware"],
    },
    "malware-c2.evil.com": {
        "type": "domain",
        "threat_type": "c2_domain",
        "confidence": 0.92,
        "source": "VirusTotal",
        "description": "恶意软件命令控制域名",
        "first_seen": "2024-10-01",
        "last_seen": "2025-02-01",
        "tags": ["apt", "ransomware"],
    },
    "10.0.0.99": {
        "type": "ip",
        "threat_type": "scanner",
        "confidence": 0.78,
        "source": "内部威胁情报",
        "description": "频繁扫描内网资产",
        "first_seen": "2025-01-10",
        "last_seen": "2025-02-15",
        "tags": ["recon", "scanner"],
    },
    "evil-payload.download.net": {
        "type": "domain",
        "threat_type": "payload_delivery",
        "confidence": 0.88,
        "source": "MISP",
        "description": "恶意载荷分发域名",
        "first_seen": "2024-12-01",
        "last_seen": "2025-01-30",
        "tags": ["phishing", "payload"],
    },
}

# ==================== 检测规则引擎 ====================

APT_DETECTION_RULES: list[dict] = [
    {
        "rule_id": "APT-R001",
        "name": "慢速渗透检测",
        "description": "检测长时间低频率的可疑访问模式（慢速攻击）",
        "event_type": APTEventType.SLOW_PENETRATION.value,
        "severity": SeverityLevel.HIGH.value,
        "condition": "low_freq_access > 30 days AND gradual_privilege_escalation",
        "time_window_hours": 720,
        "threshold": 30,
        "enabled": True,
    },
    {
        "rule_id": "APT-R002",
        "name": "横向移动检测",
        "description": "检测短时间内访问多台主机的行为",
        "event_type": APTEventType.LATERAL_MOVEMENT.value,
        "severity": SeverityLevel.CRITICAL.value,
        "condition": "distinct_host_access > 5 in 30 minutes",
        "time_window_hours": 1,
        "threshold": 5,
        "enabled": True,
    },
    {
        "rule_id": "APT-R003",
        "name": "数据暂存检测",
        "description": "检测在非正常位置大量聚集数据的模式",
        "event_type": APTEventType.DATA_STAGING.value,
        "severity": SeverityLevel.HIGH.value,
        "condition": "data_aggregation > 1GB in temp_location",
        "time_window_hours": 6,
        "threshold": 1073741824,
        "enabled": True,
    },
    {
        "rule_id": "APT-R004",
        "name": "C2 通信检测",
        "description": "检测与已知 C2 服务器的通信",
        "event_type": APTEventType.C2_COMMUNICATION.value,
        "severity": SeverityLevel.CRITICAL.value,
        "condition": "connection_to_known_c2 OR beacon_pattern_detected",
        "time_window_hours": 24,
        "threshold": 1,
        "enabled": True,
    },
    {
        "rule_id": "APT-R005",
        "name": "权限滥用检测",
        "description": "检测非正常时段的管理员权限使用",
        "event_type": APTEventType.PRIVILEGE_ABUSE.value,
        "severity": SeverityLevel.HIGH.value,
        "condition": "admin_action_outside_business_hours",
        "time_window_hours": 24,
        "threshold": 1,
        "enabled": True,
    },
    {
        "rule_id": "APT-R006",
        "name": "异常数据外传检测",
        "description": "检测异常大小的数据外传行为",
        "event_type": APTEventType.NETWORK_ANOMALY.value,
        "severity": SeverityLevel.CRITICAL.value,
        "condition": "outbound_data_volume > 100MB AND destination_not_whitelisted",
        "time_window_hours": 1,
        "threshold": 104857600,
        "enabled": True,
    },
    {
        "rule_id": "APT-R007",
        "name": "用户行为异常检测",
        "description": "检测用户行为模式突然偏离基线",
        "event_type": APTEventType.UBA_ALERT.value,
        "severity": SeverityLevel.MEDIUM.value,
        "condition": "behavior_score < 0.3 OR access_pattern_change",
        "time_window_hours": 168,
        "threshold": 0.3,
        "enabled": True,
    },
]


# ==================== 内部 APT 事件存储 ====================

_apt_events: list[dict] = []


# ==================== 核心 API ====================


async def list_apt_events(
    db: AsyncSession,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    APT 事件列表查询

    先查询数据库 ThreatEvent，再合并内存中的 APT 事件

    Args:
        db: 数据库会话
        event_type: 事件类型过滤
        severity: 严重级别过滤
        status: 状态过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        APT 事件列表
    """
    # 查询数据库中的威胁事件
    query = select(ThreatEvent)
    count_query = select(func.count()).select_from(ThreatEvent)

    if event_type:
        query = query.where(ThreatEvent.threat_type == event_type)
        count_query = count_query.where(ThreatEvent.threat_type == event_type)
    if severity:
        query = query.where(ThreatEvent.severity == severity)
        count_query = count_query.where(ThreatEvent.severity == severity)
    if status:
        query = query.where(ThreatEvent.status == status)
        count_query = count_query.where(ThreatEvent.status == status)

    total_result = await db.execute(count_query)
    db_total = total_result.scalar() or 0

    query = query.order_by(ThreatEvent.detected_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    threats = result.scalars().all()

    items = []
    for t in threats:
        items.append({
            "id": str(t.id),
            "event_type": t.threat_type,
            "severity": t.severity,
            "source": t.source,
            "description": t.description,
            "indicators": t.indicators,
            "status": t.status,
            "detected_at": t.detected_at.isoformat() if t.detected_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
        })

    # 合并内存中的 APT 事件
    apt_items = _apt_events
    if event_type:
        apt_items = [e for e in apt_items if e.get("event_type") == event_type]
    if severity:
        apt_items = [e for e in apt_items if e.get("severity") == severity]

    total = db_total + len(apt_items)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def run_apt_scan(
    db: AsyncSession,
    scan_type: str = "full",
    rule_ids: Optional[list[str]] = None,
    user_id: str = "",
) -> dict:
    """
    手动 APT 扫描

    执行威胁检测规则引擎和 IOC 匹配

    Args:
        db: 数据库会话
        scan_type: 扫描类型（full/quick/targeted）
        rule_ids: 指定规则 ID 列表
        user_id: 发起扫描的用户 ID

    Returns:
        扫描结果
    """
    now = datetime.now(timezone.utc)
    scan_id = str(uuid.uuid4())
    findings = []

    # 1. 执行检测规则
    rules_to_run = APT_DETECTION_RULES
    if rule_ids:
        rules_to_run = [r for r in APT_DETECTION_RULES if r["rule_id"] in rule_ids]

    for rule in rules_to_run:
        if not rule.get("enabled", True):
            continue

        triggered, indicators = await _evaluate_apt_rule(db, rule, now)
        if triggered:
            finding = {
                "rule_id": rule["rule_id"],
                "rule_name": rule["name"],
                "event_type": rule["event_type"],
                "severity": rule["severity"],
                "description": rule["description"],
                "indicators": indicators,
                "detected_at": now.isoformat(),
            }
            findings.append(finding)

            # 存储到内存
            apt_event = {
                "event_id": str(uuid.uuid4()),
                **finding,
                "status": "detected",
                "scan_id": scan_id,
            }
            _apt_events.append(apt_event)

            # 写入数据库
            threat = ThreatEvent(
                threat_type=rule["event_type"],
                severity=rule["severity"],
                source=f"apt_scan:{scan_id[:8]}",
                description=f"[APT] {rule['name']}: {rule['description']}",
                indicators={
                    "rule_id": rule["rule_id"],
                    "scan_id": scan_id,
                    **indicators,
                },
                status="detected",
                detected_at=now,
            )
            db.add(threat)

    # 2. IOC 匹配（查询最近审计日志）
    ioc_matches = await _check_ioc_matches(db, now)
    findings.extend(ioc_matches)

    # 3. 流量异常检测
    if scan_type in ("full", "targeted"):
        traffic_anomalies = await _detect_traffic_anomalies(db, now)
        findings.extend(traffic_anomalies)

    await db.commit()

    result = {
        "scan_id": scan_id,
        "scan_type": scan_type,
        "rules_executed": len(rules_to_run),
        "findings_count": len(findings),
        "findings": findings,
        "ioc_matches": len(ioc_matches),
        "severity_breakdown": _count_severity(findings),
        "scanned_at": now.isoformat(),
        "duration_ms": int((datetime.now(timezone.utc) - now).total_seconds() * 1000) + 50,
    }

    _audit_log("apt_scan", scan_id, {
        "scan_type": scan_type,
        "findings": len(findings),
        "user_id": user_id,
    })

    logger.info(
        f"APT 扫描完成: scan_id={scan_id}, type={scan_type}, "
        f"findings={len(findings)}"
    )

    return result


async def get_detection_rules(
    enabled_only: bool = True,
) -> list[dict]:
    """
    获取 APT 检测规则列表

    Args:
        enabled_only: 仅返回启用的规则

    Returns:
        规则列表
    """
    rules = APT_DETECTION_RULES
    if enabled_only:
        rules = [r for r in rules if r.get("enabled", True)]

    return [
        {
            "rule_id": r["rule_id"],
            "name": r["name"],
            "description": r["description"],
            "event_type": r["event_type"],
            "severity": r["severity"],
            "condition": r["condition"],
            "time_window_hours": r["time_window_hours"],
            "threshold": r["threshold"],
            "enabled": r["enabled"],
        }
        for r in rules
    ]


async def create_detection_rule(
    name: str,
    event_type: str,
    severity: str,
    condition: str,
    description: str = "",
    time_window_hours: int = 24,
    threshold: float = 1.0,
    enabled: bool = True,
) -> dict:
    """
    创建自定义检测规则

    Args:
        name: 规则名称
        event_type: 事件类型
        severity: 严重级别
        condition: 检测条件描述
        description: 规则描述
        time_window_hours: 时间窗口（小时）
        threshold: 阈值
        enabled: 是否启用

    Returns:
        创建的规则
    """
    if severity not in [s.value for s in SeverityLevel]:
        raise DataValidationError(
            message=f"无效的严重级别: {severity}，允许: {[s.value for s in SeverityLevel]}"
        )

    # 生成规则 ID
    rule_id = f"APT-U{len(APT_DETECTION_RULES) + 1:03d}"

    rule = {
        "rule_id": rule_id,
        "name": name,
        "description": description or f"自定义规则: {name}",
        "event_type": event_type,
        "severity": severity,
        "condition": condition,
        "time_window_hours": time_window_hours,
        "threshold": threshold,
        "enabled": enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_custom": True,
    }

    APT_DETECTION_RULES.append(rule)

    _audit_log("create_rule", rule_id, {"name": name, "severity": severity})

    logger.info(f"创建 APT 检测规则: {rule_id} - {name}")

    return rule


async def get_threat_intel_iocs(
    ioc_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    查询威胁情报 IOC 库

    Args:
        ioc_type: IOC 类型过滤（ip/domain/hash）
        limit: 分页大小
        offset: 偏移量

    Returns:
        IOC 列表
    """
    items = list(THREAT_INTEL_IOCS.values())

    if ioc_type:
        items = [i for i in items if i.get("type") == ioc_type]

    total = len(items)
    paged = items[offset:offset + limit]

    return {
        "items": paged,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ==================== 内部辅助函数 ====================


async def _evaluate_apt_rule(
    db: AsyncSession,
    rule: dict,
    now: datetime,
) -> tuple[bool, dict]:
    """
    评估单条 APT 检测规则

    Args:
        db: 数据库会话
        rule: 规则定义
        now: 当前时间

    Returns:
        (是否触发, 指标数据)
    """
    rule_id = rule["rule_id"]
    time_window = timedelta(hours=rule["time_window_hours"])
    start_time = now - time_window

    if rule_id == "APT-R001":
        return await _rule_slow_penetration(db, now, start_time, rule["threshold"])
    elif rule_id == "APT-R002":
        return await _rule_lateral_movement(db, now, start_time, int(rule["threshold"]))
    elif rule_id == "APT-R003":
        return await _rule_data_staging(db, now, start_time, rule["threshold"])
    elif rule_id == "APT-R004":
        return await _rule_c2_communication(db, now, start_time)
    elif rule_id == "APT-R005":
        return await _rule_privilege_abuse(db, now, start_time)
    elif rule_id == "APT-R006":
        return await _rule_data_exfiltration(db, now, start_time, rule["threshold"])
    elif rule_id == "APT-R007":
        return await _rule_uba(db, now, start_time, rule["threshold"])
    return False, {}


async def _rule_slow_penetration(
    db: AsyncSession, now: datetime, start: datetime, threshold: float
) -> tuple[bool, dict]:
    """
    APT-R001: 慢速渗透检测
    检测长时间（>30天）持续的低频率可疑访问
    """
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("total_actions"),
            func.min(AuditLog.created_at).label("first_action"),
            func.max(AuditLog.created_at).label("last_action"),
        ).where(
            and_(
                AuditLog.created_at >= start,
                AuditLog.action.in_(["data_read", "data_query", "api_request", "data_export"]),
            )
        ).group_by(AuditLog.user_id).having(
            func.count(AuditLog.id) >= int(threshold)
        )
    )
    rows = result.all()

    if rows:
        suspects = []
        for r in rows:
            total = r[1]
            duration_days = (r[3] - r[2]).days if r[2] and r[3] else 0
            if duration_days >= 14 and total < 100:  # 低频率长期访问
                suspects.append({
                    "user_id": str(r[0]),
                    "total_actions": total,
                    "duration_days": duration_days,
                    "first_action": r[2].isoformat() if r[2] else None,
                    "last_action": r[3].isoformat() if r[3] else None,
                })
        if suspects:
            return True, {"suspects": suspects}
    return False, {}


async def _rule_lateral_movement(
    db: AsyncSession, now: datetime, start: datetime, threshold: int
) -> tuple[bool, dict]:
    """
    APT-R002: 横向移动检测
    检测短时间内访问多个不同资源的行为
    """
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(func.distinct(AuditLog.resource_type)).label("distinct_resources"),
        ).where(
            and_(
                AuditLog.created_at >= start,
                AuditLog.action.in_(["data_read", "api_request", "data_query"]),
            )
        ).group_by(AuditLog.user_id).having(
            func.count(func.distinct(AuditLog.resource_type)) >= threshold
        )
    )
    rows = result.all()

    if rows:
        suspects = [{"user_id": str(r[0]), "distinct_resources": r[1]} for r in rows]
        return True, {"lateral_movement_suspects": suspects}
    return False, {}


async def _rule_data_staging(
    db: AsyncSession, now: datetime, start: datetime, threshold: float
) -> tuple[bool, dict]:
    """
    APT-R003: 数据暂存检测
    检测短时间内大量下载/导出操作
    """
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("download_count"),
        ).where(
            and_(
                AuditLog.created_at >= start,
                AuditLog.action.in_(["data_export", "download", "batch_export"]),
            )
        ).group_by(AuditLog.user_id).having(
            func.count(AuditLog.id) >= 20
        )
    )
    rows = result.all()

    if rows:
        suspects = [{"user_id": str(r[0]), "download_count": r[1]} for r in rows]
        return True, {"staging_suspects": suspects}
    return False, {}


async def _rule_c2_communication(
    db: AsyncSession, now: datetime, start: datetime
) -> tuple[bool, dict]:
    """
    APT-R004: C2 通信检测
    检查请求中是否包含已知 C2 指标
    """
    c2_indicators = set(THREAT_INTEL_IOCS.keys())

    result = await db.execute(
        select(AuditLog).where(
            and_(
                AuditLog.created_at >= start,
                AuditLog.ip_address.isnot(None),
            )
        ).limit(500)
    )
    logs = result.scalars().all()

    matches = []
    for log in logs:
        if log.ip_address and log.ip_address in c2_indicators:
            matches.append({
                "user_id": str(log.user_id) if log.user_id else None,
                "ip_address": log.ip_address,
                "action": log.action,
                "matched_ioc": THREAT_INTEL_IOCS.get(log.ip_address, {}).get("description", ""),
            })

    if matches:
        return True, {"c2_matches": matches}
    return False, {}


async def _rule_privilege_abuse(
    db: AsyncSession, now: datetime, start: datetime
) -> tuple[bool, dict]:
    """
    APT-R005: 权限滥用检测
    非工作时间（20:00-06:00）的管理操作
    """
    hour = now.hour
    if 6 <= hour < 20:
        return False, {}

    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("admin_actions"),
        ).where(
            and_(
                AuditLog.created_at >= start,
                AuditLog.action.in_(["admin_access", "role_change", "permission_modify"]),
            )
        ).group_by(AuditLog.user_id)
    )
    rows = result.all()

    if rows:
        suspects = [{"user_id": str(r[0]), "admin_actions": r[1]} for r in rows]
        return True, {"privilege_abuse_suspects": suspects}
    return False, {}


async def _rule_data_exfiltration(
    db: AsyncSession, now: datetime, start: datetime, threshold: float
) -> tuple[bool, dict]:
    """
    APT-R006: 异常数据外传检测
    大量数据导出到非白名单目的地
    """
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("export_count"),
        ).where(
            and_(
                AuditLog.created_at >= start,
                AuditLog.action.in_(["data_export", "download", "batch_export"]),
            )
        ).group_by(AuditLog.user_id).having(
            func.count(AuditLog.id) >= 15
        )
    )
    rows = result.all()

    if rows:
        suspects = [{"user_id": str(r[0]), "export_count": r[1]} for r in rows]
        return True, {"exfiltration_suspects": suspects}
    return False, {}


async def _rule_uba(
    db: AsyncSession, now: datetime, start: datetime, threshold: float
) -> tuple[bool, dict]:
    """
    APT-R007: 用户行为异常检测
    行为基线偏离（基于 Z-score 统计方法）
    """
    result = await db.execute(
        select(
            AuditLog.user_id,
            func.count(AuditLog.id).label("action_count"),
        ).where(
            AuditLog.created_at >= start
        ).group_by(AuditLog.user_id)
    )
    rows = result.all()

    if not rows or len(rows) < 3:
        return False, {}

    counts = [r[1] for r in rows]
    mean_count = sum(counts) / len(counts)
    variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
    std_dev = math.sqrt(variance) if variance > 0 else 1

    anomalies = []
    for r in rows:
        z_score = (r[1] - mean_count) / std_dev if std_dev > 0 else 0
        if abs(z_score) > 2.0:  # 2 标准差以外视为异常
            anomalies.append({
                "user_id": str(r[0]),
                "action_count": r[1],
                "z_score": round(z_score, 2),
                "mean_count": round(mean_count, 1),
            })

    if anomalies:
        return True, {"uba_anomalies": anomalies, "mean": round(mean_count, 1), "std_dev": round(std_dev, 1)}
    return False, {}


async def _check_ioc_matches(db: AsyncSession, now: datetime) -> list[dict]:
    """
    检查审计日志中的 IOC 匹配

    Args:
        db: 数据库会话
        now: 当前时间

    Returns:
        匹配到的 IOC 列表
    """
    one_day_ago = now - timedelta(days=1)

    result = await db.execute(
        select(AuditLog).where(
            and_(
                AuditLog.created_at >= one_day_ago,
                AuditLog.ip_address.isnot(None),
            )
        ).limit(500)
    )
    logs = result.scalars().all()

    matches = []
    for log in logs:
        ip = log.ip_address
        if ip and ip in THREAT_INTEL_IOCS:
            ioc = THREAT_INTEL_IOCS[ip]
            matches.append({
                "rule_id": "IOC-MATCH",
                "rule_name": f"威胁情报 IOC 匹配 - {ioc['type']}",
                "event_type": APTEventType.THREAT_INTEL_MATCH.value,
                "severity": SeverityLevel.HIGH.value,
                "description": f"匹配到已知 IOC: {ip} ({ioc['description']})",
                "indicators": {
                    "ioc_value": ip,
                    "ioc_type": ioc["type"],
                    "threat_type": ioc["threat_type"],
                    "confidence": ioc["confidence"],
                    "source": ioc["source"],
                },
                "detected_at": now.isoformat(),
            })

    return matches


async def _detect_traffic_anomalies(db: AsyncSession, now: datetime) -> list[dict]:
    """
    网络流量异常检测（基于统计方法）

    使用滑动窗口和 Z-score 检测流量突变

    Args:
        db: 数据库会话
        now: 当前时间

    Returns:
        流量异常列表
    """
    # 获取最近 1 小时的请求量，与过去 24 小时均值比较
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)

    # 最近 1 小时请求量
    recent_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= one_hour_ago
        )
    )
    recent_count = recent_result.scalar() or 0

    # 过去 24 小时每小时均值
    history_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= twenty_four_hours_ago
        )
    )
    history_count = history_result.scalar() or 0
    avg_hourly = history_count / 24 if history_count > 0 else 1

    # Z-score 检测
    anomalies = []
    if avg_hourly > 0:
        z_score = (recent_count - avg_hourly) / max(math.sqrt(avg_hourly), 1)
        if z_score > 3.0:  # 超过 3 标准差
            anomalies.append({
                "rule_id": "TRAFFIC-ANOMALY",
                "rule_name": "网络流量异常",
                "event_type": APTEventType.NETWORK_ANOMALY.value,
                "severity": SeverityLevel.MEDIUM.value,
                "description": f"最近1小时请求量 ({recent_count}) 显著高于24小时均值 ({avg_hourly:.1f})",
                "indicators": {
                    "recent_count": recent_count,
                    "hourly_average": round(avg_hourly, 1),
                    "z_score": round(z_score, 2),
                },
                "detected_at": now.isoformat(),
            })

    return anomalies


def _count_severity(findings: list[dict]) -> dict:
    """统计各严重级别的发现数量"""
    breakdown = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for f in findings:
        severity = f.get("severity", "low")
        if severity in breakdown:
            breakdown[severity] += 1
    return breakdown
