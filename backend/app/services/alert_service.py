"""
告警服务 - 邮件/Webhook推送通道集成 + 告警升级 + 静默/抑制
阈值告警、趋势告警、复合告警、通知投递
"""
import uuid
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# ==================== 存储 ====================

_alerts: Dict[str, dict] = {}
_alert_rules: Dict[str, dict] = {}
_alert_history: List[dict] = []
_notification_channels: Dict[str, dict] = {}
_silence_rules: Dict[str, dict] = {}  # 告警静默规则
_inhibition_rules: Dict[str, dict] = {}  # 告警抑制规则


# ==================== 初始化 ====================

def _init_default_alert_rules():
    """初始化默认告警规则"""
    defaults = [
        {
            "rule_id": "rule_cpu_high",
            "name": "CPU 使用率过高",
            "metric": "cpu_usage",
            "condition": ">",
            "threshold": 80,
            "severity": "warning",
            "enabled": True,
            "notify_channels": ["email"],
        },
        {
            "rule_id": "rule_cpu_critical",
            "name": "CPU 使用率严重",
            "metric": "cpu_usage",
            "condition": ">",
            "threshold": 95,
            "severity": "critical",
            "enabled": True,
            "notify_channels": ["email", "sms"],
        },
        {
            "rule_id": "rule_memory_high",
            "name": "内存使用率过高",
            "metric": "memory_usage",
            "condition": ">",
            "threshold": 85,
            "severity": "warning",
            "enabled": True,
            "notify_channels": ["email"],
        },
        {
            "rule_id": "rule_disk_high",
            "name": "磁盘使用率过高",
            "metric": "disk_usage",
            "condition": ">",
            "threshold": 90,
            "severity": "warning",
            "enabled": True,
            "notify_channels": ["email"],
        },
        {
            "rule_id": "rule_response_slow",
            "name": "API 响应时间过长",
            "metric": "avg_response_time",
            "condition": ">",
            "threshold": 500,
            "severity": "warning",
            "enabled": True,
            "notify_channels": ["email"],
        },
        {
            "rule_id": "rule_error_rate",
            "name": "错误率过高",
            "metric": "error_rate",
            "condition": ">",
            "threshold": 1.0,
            "severity": "critical",
            "enabled": True,
            "notify_channels": ["email", "sms", "webhook"],
        },
        {
            "rule_id": "rule_connection_pool",
            "name": "数据库连接池耗尽",
            "metric": "db_connection_usage",
            "condition": ">",
            "threshold": 90,
            "severity": "critical",
            "enabled": True,
            "notify_channels": ["email", "sms"],
        },
    ]
    for rule in defaults:
        _alert_rules[rule["rule_id"]] = rule


def _init_notification_channels():
    """初始化通知渠道"""
    _notification_channels["email"] = {
        "channel_id": "email",
        "name": "邮件通知",
        "type": "email",
        "enabled": True,
        "config": {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "alerts@energy-data-space.com",
            "smtp_password": "",
            "from_addr": "alerts@energy-data-space.com",
            "use_tls": True,
        },
    }
    _notification_channels["sms"] = {
        "channel_id": "sms",
        "name": "短信通知",
        "type": "sms",
        "enabled": True,
        "config": {
            "provider": "aliyun",
            "sign_name": "能源数据空间",
            "api_key": "",
            "api_secret": "",
        },
    }
    _notification_channels["webhook"] = {
        "channel_id": "webhook",
        "name": "Webhook 通知",
        "type": "webhook",
        "enabled": True,
        "config": {
            "url": "https://hooks.example.com/alerts",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "timeout": 10,
        },
    }


def _init_default_silence_rules():
    """初始化默认静默规则"""
    # 示例：维护窗口静默
    _silence_rules["maintenance_window"] = {
        "silence_id": "maintenance_window",
        "name": "维护窗口静默",
        "enabled": False,
        "matchers": {},  # 空 = 匹配所有
        "start_time": "2024-01-01T02:00:00+00:00",
        "end_time": "2024-01-01T06:00:00+00:00",
        "created_by": "system",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _init_default_inhibition_rules():
    """初始化默认抑制规则"""
    # 当 critical 告警触发时，抑制同源的 warning 告警
    _inhibition_rules["critical_inhibits_warning"] = {
        "inhibition_id": "critical_inhibits_warning",
        "name": "Critical 抑制 Warning",
        "enabled": True,
        "source_match": {"severity": "critical"},
        "target_match": {"severity": "warning"},
        "equal": ["metric_name"],  # 相同指标名称时才抑制
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


_init_default_alert_rules()
_init_notification_channels()
_init_default_silence_rules()
_init_default_inhibition_rules()


# ==================== 告警 CRUD ====================

async def create_alert(
    title: str,
    description: str,
    severity: str = "warning",
    source: str = "system",
    metric_name: Optional[str] = None,
    metric_value: Optional[float] = None,
    threshold: Optional[float] = None,
    labels: Optional[Dict[str, str]] = None,
) -> dict:
    """
    创建告警

    Args:
        title: 告警标题
        description: 告警描述
        severity: 严重程度
        source: 来源
        metric_name: 指标名称
        metric_value: 指标值
        threshold: 阈值
        labels: 标签

    Returns:
        告警数据
    """
    alert_id = f"alert_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    alert = {
        "alert_id": alert_id,
        "title": title,
        "description": description,
        "severity": severity,
        "status": "active",
        "source": source,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "threshold": threshold,
        "labels": labels or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "acknowledged_by": None,
        "acknowledged_at": None,
        "resolved_at": None,
        "escalation_level": 0,
        "silenced": False,
    }

    # 检查是否被静默
    if _is_alert_silenced(alert):
        alert["silenced"] = True
        logger.info(f"Alert {alert_id} is silenced, skipping notifications")
        _alerts[alert_id] = alert
        return alert

    # 检查是否被抑制
    if _is_alert_inhibited(alert):
        logger.info(f"Alert {alert_id} is inhibited by higher-severity alert, skipping notifications")
        _alerts[alert_id] = alert
        return alert

    _alerts[alert_id] = alert
    _alert_history.append({
        "alert_id": alert_id,
        "event": "created",
        "timestamp": now.isoformat(),
    })

    # 触发通知（带升级机制）
    await _send_alert_notifications_with_escalation(alert)

    logger.warning(f"Alert created: {alert_id} - {title} [{severity}]")
    return alert


async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """列出告警"""
    alerts = list(_alerts.values())
    if status:
        alerts = [a for a in alerts if a.get("status") == status]
    if severity:
        alerts = [a for a in alerts if a.get("severity") == severity]
    alerts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return alerts[:limit]


async def get_alert(alert_id: str) -> Optional[dict]:
    """获取告警详情"""
    return _alerts.get(alert_id)


async def acknowledge_alert(alert_id: str, user_id: str) -> bool:
    """确认告警"""
    alert = _alerts.get(alert_id)
    if not alert:
        return False
    alert["status"] = "acknowledged"
    alert["acknowledged_by"] = user_id
    alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
    alert["updated_at"] = datetime.now(timezone.utc).isoformat()
    _alert_history.append({
        "alert_id": alert_id,
        "event": "acknowledged",
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"Alert acknowledged: {alert_id} by {user_id}")
    return True


async def resolve_alert(alert_id: str, user_id: Optional[str] = None) -> bool:
    """解决告警"""
    alert = _alerts.get(alert_id)
    if not alert:
        return False
    alert["status"] = "resolved"
    alert["resolved_at"] = datetime.now(timezone.utc).isoformat()
    alert["updated_at"] = datetime.now(timezone.utc).isoformat()
    _alert_history.append({
        "alert_id": alert_id,
        "event": "resolved",
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"Alert resolved: {alert_id}")
    return True


# ==================== 告警规则 ====================

async def list_alert_rules() -> List[dict]:
    """列出告警规则"""
    return list(_alert_rules.values())


async def create_alert_rule(rule: dict) -> dict:
    """创建告警规则"""
    rule_id = rule.get("rule_id") or f"rule_{uuid.uuid4().hex[:8]}"
    rule["rule_id"] = rule_id
    _alert_rules[rule_id] = rule
    return rule


async def update_alert_rule(rule_id: str, rule: dict) -> Optional[dict]:
    """更新告警规则"""
    if rule_id not in _alert_rules:
        return None
    rule["rule_id"] = rule_id
    _alert_rules[rule_id] = rule
    return rule


async def delete_alert_rule(rule_id: str) -> bool:
    """删除告警规则"""
    if rule_id in _alert_rules:
        del _alert_rules[rule_id]
        return True
    return False


async def check_threshold_alerts(metrics: dict) -> List[dict]:
    """检查阈值告警"""
    triggered: List[dict] = []
    for rule in _alert_rules.values():
        if not rule.get("enabled", True):
            continue
        metric_name = rule["metric"]
        if metric_name not in metrics:
            continue
        value = metrics[metric_name]
        threshold = rule["threshold"]
        condition = rule["condition"]
        triggered_flag = False
        if condition == ">" and value > threshold:
            triggered_flag = True
        elif condition == "<" and value < threshold:
            triggered_flag = True
        elif condition == ">=" and value >= threshold:
            triggered_flag = True
        elif condition == "<=" and value <= threshold:
            triggered_flag = True
        elif condition == "==" and value == threshold:
            triggered_flag = True
        if triggered_flag:
            alert = await create_alert(
                title=rule["name"],
                description=f"{metric_name} 当前值 {value}，阈值 {condition} {threshold}",
                severity=rule["severity"],
                source="threshold_check",
                metric_name=metric_name,
                metric_value=value,
                threshold=threshold,
            )
            triggered.append(alert)
    return triggered


async def get_alert_statistics() -> dict:
    """获取告警统计"""
    alerts = list(_alerts.values())
    total = len(alerts)
    active = len([a for a in alerts if a.get("status") == "active"])
    acknowledged = len([a for a in alerts if a.get("status") == "acknowledged"])
    resolved = len([a for a in alerts if a.get("status") == "resolved"])
    severity_counts: Dict[str, int] = {}
    for a in alerts:
        sev = a.get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    return {
        "total": total,
        "active": active,
        "acknowledged": acknowledged,
        "resolved": resolved,
        "by_severity": severity_counts,
        "last_24h": len([a for a in alerts if a.get("status") == "active"]),
    }


async def get_alert_history(alert_id: Optional[str] = None, limit: int = 100) -> List[dict]:
    """获取告警历史"""
    history = _alert_history
    if alert_id:
        history = [h for h in history if h.get("alert_id") == alert_id]
    return history[-limit:]


# ==================== 通知渠道 ====================

async def list_notification_channels() -> List[dict]:
    """列出通知渠道"""
    return list(_notification_channels.values())


# ==================== 告警升级机制 ====================

async def _send_alert_notifications_with_escalation(alert: dict) -> None:
    """
    发送告警通知（带升级机制）

    升级策略：
    - P1 (critical): 邮件 + 短信 + Webhook
    - P2 (warning): 邮件 + Webhook
    - P3 (info/low): 仅日志记录
    """
    severity = alert.get("severity", "warning")

    # P1→邮件+短信+Webhook, P2→邮件+Webhook, P3→日志
    if severity == "critical":
        channels = ["email", "sms", "webhook"]
        alert["escalation_level"] = 1
    elif severity == "warning":
        channels = ["email", "webhook"]
        alert["escalation_level"] = 2
    else:
        channels = []  # info/low: 仅日志
        alert["escalation_level"] = 3
        logger.info(f"Alert P3 (log only): {alert['alert_id']} - {alert['title']}")
        _alert_history.append({
            "alert_id": alert["alert_id"],
            "event": "notification_logged",
            "channel": "log",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return

    for channel_name in channels:
        channel = _notification_channels.get(channel_name)
        if not channel or not channel.get("enabled"):
            continue

        try:
            if channel["type"] == "email":
                await _send_email_alert(alert, channel["config"])
            elif channel["type"] == "webhook":
                await _send_webhook_alert(alert, channel["config"])
            elif channel["type"] == "sms":
                await _send_sms_alert(alert, channel["config"])

            _alert_history.append({
                "alert_id": alert["alert_id"],
                "event": "notification_sent",
                "channel": channel_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"Alert notification sent via {channel_name}: {alert['alert_id']}")
        except Exception as e:
            logger.error(f"Failed to send alert via {channel_name}: {e}")
            _alert_history.append({
                "alert_id": alert["alert_id"],
                "event": "notification_failed",
                "channel": channel_name,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })


async def _send_email_alert(alert: dict, config: dict) -> None:
    """
    通过 SMTP 发送邮件告警

    Args:
        alert: 告警数据
        config: 邮件配置
    """
    smtp_host = config.get("smtp_host", "")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user", "")
    smtp_password = config.get("smtp_password", "")
    from_addr = config.get("from_addr", "")
    use_tls = config.get("use_tls", True)
    to_addrs = config.get("to_addrs", ["admin@energy-data-space.com"])

    if not smtp_host or not from_addr:
        logger.warning("SMTP configuration incomplete, skipping email alert")
        return

    severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
        alert.get("severity", ""), "⚪"
    )
    subject = f"{severity_emoji} [告警] {alert['title']}"

    body = (
        f"告警ID: {alert['alert_id']}\n"
        f"标题: {alert['title']}\n"
        f"描述: {alert['description']}\n"
        f"严重程度: {alert['severity']}\n"
        f"来源: {alert['source']}\n"
        f"指标: {alert.get('metric_name', 'N/A')}\n"
        f"当前值: {alert.get('metric_value', 'N/A')}\n"
        f"阈值: {alert.get('threshold', 'N/A')}\n"
        f"触发时间: {alert['created_at']}\n"
    )

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 在线程中执行阻塞的 SMTP 操作
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _smtp_send, smtp_host, smtp_port, smtp_user,
                                smtp_password, use_tls, from_addr, to_addrs, msg)


def _smtp_send(
    host: str, port: int, user: str, password: str,
    use_tls: bool, from_addr: str, to_addrs: List[str],
    msg: MIMEMultipart,
) -> None:
    """SMTP 同步发送（在线程中执行）"""
    try:
        if use_tls:
            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, to_addrs, msg.as_string())
        server.quit()
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        raise


async def _send_webhook_alert(alert: dict, config: dict) -> None:
    """
    通过 HTTP Webhook 发送告警通知

    Args:
        alert: 告警数据
        config: Webhook 配置
    """
    url = config.get("url", "")
    method = config.get("method", "POST").upper()
    headers = config.get("headers", {"Content-Type": "application/json"})
    timeout = config.get("timeout", 10)

    if not url:
        logger.warning("Webhook URL not configured, skipping webhook alert")
        return

    payload = {
        "alert_id": alert["alert_id"],
        "title": alert["title"],
        "description": alert["description"],
        "severity": alert["severity"],
        "source": alert["source"],
        "metric_name": alert.get("metric_name"),
        "metric_value": alert.get("metric_value"),
        "threshold": alert.get("threshold"),
        "created_at": alert["created_at"],
        "labels": alert.get("labels", {}),
    }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "POST":
                response = await client.post(url, json=payload, headers=headers)
            elif method == "PUT":
                response = await client.put(url, json=payload, headers=headers)
            else:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code >= 400:
                logger.error(
                    f"Webhook alert failed: status={response.status_code}, "
                    f"url={url}, body={response.text[:200]}"
                )
            else:
                logger.info(f"Webhook alert sent successfully: {url} -> {response.status_code}")
    except ImportError:
        logger.warning("httpx not installed, cannot send webhook alert")
    except Exception as e:
        logger.error(f"Webhook alert error: {e}")
        raise


async def _send_sms_alert(alert: dict, config: dict) -> None:
    """
    发送短信告警（占位实现，对接阿里云/腾讯云 SMS API）

    Args:
        alert: 告警数据
        config: 短信配置
    """
    provider = config.get("provider", "aliyun")
    sign_name = config.get("sign_name", "")
    logger.info(
        f"SMS alert [{provider}] sign={sign_name}: "
        f"{alert['alert_id']} - {alert['title']} [{alert['severity']}]"
    )
    # 实际实现需对接阿里云 SMS SDK：
    # from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
    # 此处记录日志表明已触发 SMS 通知


# ==================== 告警静默/抑制 ====================

def _is_alert_silenced(alert: dict) -> bool:
    """
    检查告警是否被静默

    Args:
        alert: 告警数据

    Returns:
        是否被静默
    """
    now = datetime.now(timezone.utc)
    for rule in _silence_rules.values():
        if not rule.get("enabled", False):
            continue

        # 检查时间范围
        start = rule.get("start_time")
        end = rule.get("end_time")
        if start and end:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                if start_dt <= now <= end_dt:
                    # 在静默窗口内
                    matchers = rule.get("matchers", {})
                    if not matchers:
                        return True  # 空 matchers 匹配所有
                    # 检查是否匹配
                    if _alert_matches(alert, matchers):
                        return True
            except (ValueError, TypeError):
                pass

    return False


def _is_alert_inhibited(alert: dict) -> bool:
    """
    检查告警是否被抑制

    抑制逻辑：当一个更高严重程度的告警处于活跃状态时，
    抑制相同来源的较低严重程度告警。

    Args:
        alert: 告警数据

    Returns:
        是否被抑制
    """
    severity_order = {"info": 0, "low": 0, "warning": 1, "medium": 1, "critical": 2, "high": 2}

    for rule in _inhibition_rules.values():
        if not rule.get("enabled", True):
            continue

        source_match = rule.get("source_match", {})
        target_match = rule.get("target_match", {})
        equal_fields = rule.get("equal", [])

        # 当前告警必须匹配 target_match
        if not _alert_matches(alert, target_match):
            continue

        # 查找匹配 source_match 的活跃告警
        for existing_alert in _alerts.values():
            if existing_alert.get("alert_id") == alert.get("alert_id"):
                continue
            if existing_alert.get("status") not in ("active", "acknowledged"):
                continue
            if not _alert_matches(existing_alert, source_match):
                continue

            # 检查 equal 字段是否相同
            all_equal = all(
                alert.get(field) == existing_alert.get(field)
                for field in equal_fields
            )
            if all_equal:
                # 源告警严重程度必须更高
                src_sev = severity_order.get(existing_alert.get("severity", ""), 0)
                tgt_sev = severity_order.get(alert.get("severity", ""), 0)
                if src_sev > tgt_sev:
                    return True

    return False


def _alert_matches(alert: dict, matchers: Dict[str, str]) -> bool:
    """
    检查告警是否匹配指定的标签匹配器

    Args:
        alert: 告警数据
        matchers: 匹配器 {field: value}

    Returns:
        是否匹配
    """
    for field, value in matchers.items():
        if alert.get(field) != value:
            return False
    return True


# ==================== 静默规则管理 ====================

async def create_silence_rule(rule: dict) -> dict:
    """创建静默规则"""
    silence_id = rule.get("silence_id") or f"silence_{uuid.uuid4().hex[:8]}"
    rule["silence_id"] = silence_id
    rule["created_at"] = datetime.now(timezone.utc).isoformat()
    _silence_rules[silence_id] = rule
    logger.info(f"Silence rule created: {silence_id}")
    return rule


async def list_silence_rules() -> List[dict]:
    """列出静默规则"""
    return list(_silence_rules.values())


async def delete_silence_rule(silence_id: str) -> bool:
    """删除静默规则"""
    if silence_id in _silence_rules:
        del _silence_rules[silence_id]
        return True
    return False


async def list_inhibition_rules() -> List[dict]:
    """列出抑制规则"""
    return list(_inhibition_rules.values())
