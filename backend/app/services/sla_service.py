"""
SLA (服务等级协议) 服务
可用性监控、响应时间跟踪、吞吐量统计、SLA 报告生成
"""
import uuid
import logging
import random
from datetime import datetime, timedelta, date, timezone
from typing import Optional, Dict, List, Any

from app.schemas.sla import (
    SLAConfig, SLATarget, SLAMetricData, SLAReport,
    SLAAlertConfig, SLADashboardResponse,
)

logger = logging.getLogger(__name__)

# 内存存储
_sla_configs: Dict[str, SLAConfig] = {}
_sla_reports: Dict[str, SLAReport] = {}
_sla_alerts: Dict[str, SLAAlertConfig] = {}
_metric_history: Dict[str, List[dict]] = {}


# 初始化默认 SLA 配置
def _init_default_slas():
    """初始化默认 SLA 配置"""
    defaults = [
        SLAConfig(
            sla_id="sla_availability",
            name="系统可用性 SLA",
            service_id="system",
            service_name="系统整体",
            targets=[
                SLATarget(metric_name="uptime_percent", target_value=99.9, unit="%", operator=">="),
                SLATarget(metric_name="error_rate", target_value=0.1, unit="%", operator="<="),
            ],
        ),
        SLAConfig(
            sla_id="sla_response_time",
            name="响应时间 SLA",
            service_id="api",
            service_name="API 服务",
            targets=[
                SLATarget(metric_name="avg_response_time", target_value=200, unit="ms", operator="<="),
                SLATarget(metric_name="p95_response_time", target_value=500, unit="ms", operator="<="),
                SLATarget(metric_name="p99_response_time", target_value=1000, unit="ms", operator="<="),
            ],
        ),
        SLAConfig(
            sla_id="sla_throughput",
            name="吞吐量 SLA",
            service_id="api",
            service_name="API 服务",
            targets=[
                SLATarget(metric_name="qps", target_value=1000, unit="req/s", operator=">="),
                SLATarget(metric_name="concurrent_users", target_value=500, unit="", operator=">="),
            ],
        ),
        SLAConfig(
            sla_id="sla_data_quality",
            name="数据质量 SLA",
            service_id="data",
            service_name="数据服务",
            targets=[
                SLATarget(metric_name="data_accuracy", target_value=99.5, unit="%", operator=">="),
                SLATarget(metric_name="data_completeness", target_value=99.0, unit="%", operator=">="),
                SLATarget(metric_name="data_freshness", target_value=60, unit="min", operator="<="),
            ],
        ),
    ]
    
    for sla in defaults:
        _sla_configs[sla.sla_id] = sla


_init_default_slas()


async def list_sla_configs() -> List[SLAConfig]:
    """
    列出所有 SLA 配置

    Returns:
        SLA 配置列表
    """
    return list(_sla_configs.values())


async def get_sla_config(sla_id: str) -> Optional[SLAConfig]:
    """
    获取 SLA 配置

    Args:
        sla_id: SLA ID

    Returns:
        SLA 配置
    """
    return _sla_configs.get(sla_id)


async def create_sla_config(config: SLAConfig) -> SLAConfig:
    """
    创建 SLA 配置

    Args:
        config: SLA 配置

    Returns:
        创建的 SLA 配置
    """
    if not config.sla_id:
        config.sla_id = f"sla_{uuid.uuid4().hex[:8]}"
    
    config.created_at = datetime.now(timezone.utc)
    _sla_configs[config.sla_id] = config
    
    logger.info(f"SLA config created: {config.sla_id}")
    return config


async def update_sla_config(sla_id: str, config: SLAConfig) -> Optional[SLAConfig]:
    """
    更新 SLA 配置

    Args:
        sla_id: SLA ID
        config: 新配置

    Returns:
        更新后的 SLA 配置
    """
    if sla_id not in _sla_configs:
        return None
    
    config.sla_id = sla_id
    config.updated_at = datetime.now(timezone.utc)
    _sla_configs[sla_id] = config
    
    logger.info(f"SLA config updated: {sla_id}")
    return config


async def delete_sla_config(sla_id: str) -> bool:
    """
    删除 SLA 配置

    Args:
        sla_id: SLA ID

    Returns:
        是否成功
    """
    if sla_id in _sla_configs:
        del _sla_configs[sla_id]
        logger.info(f"SLA config deleted: {sla_id}")
        return True
    return False


async def collect_sla_metrics(sla_id: str) -> List[SLAMetricData]:
    """
    采集 SLA 指标数据

    Args:
        sla_id: SLA ID

    Returns:
        指标数据列表
    """
    config = _sla_configs.get(sla_id)
    if not config:
        return []
    
    metrics = []
    for target in config.targets:
        # 模拟指标采集
        if target.metric_name == "uptime_percent":
            current_value = random.uniform(99.5, 100.0)
        elif target.metric_name == "error_rate":
            current_value = random.uniform(0.01, 0.15)
        elif target.metric_name == "avg_response_time":
            current_value = random.uniform(50, 250)
        elif target.metric_name == "p95_response_time":
            current_value = random.uniform(200, 600)
        elif target.metric_name == "p99_response_time":
            current_value = random.uniform(500, 1200)
        elif target.metric_name == "qps":
            current_value = random.uniform(800, 1500)
        elif target.metric_name == "concurrent_users":
            current_value = random.randint(300, 800)
        elif target.metric_name == "data_accuracy":
            current_value = random.uniform(99.0, 100.0)
        elif target.metric_name == "data_completeness":
            current_value = random.uniform(98.5, 100.0)
        elif target.metric_name == "data_freshness":
            current_value = random.uniform(10, 90)
        else:
            current_value = random.uniform(0, 100)
        
        # 判断状态
        if target.operator == "<=":
            met = current_value <= target.target_value
        elif target.operator == ">=":
            met = current_value >= target.target_value
        elif target.operator == "==":
            met = abs(current_value - target.target_value) < 0.01
        else:
            met = True
        
        status = "met" if met else ("at_risk" if abs(current_value - target.target_value) / target.target_value < 0.1 else "breached")
        compliance_percent = min(100.0, (target.target_value / current_value * 100) if current_value > 0 else 100.0)
        
        if target.operator == "<=":
            compliance_percent = min(100.0, (target.target_value / current_value * 100) if current_value > 0 else 100.0)
        else:
            compliance_percent = min(100.0, (current_value / target.target_value * 100) if target.target_value > 0 else 100.0)
        
        metric = SLAMetricData(
            metric_name=target.metric_name,
            current_value=round(current_value, 2),
            target_value=target.target_value,
            unit=target.unit,
            status=status,
            compliance_percent=round(compliance_percent, 2),
            trend=random.choice(["up", "down", "stable"]),
            last_measured_at=datetime.now(timezone.utc),
        )
        metrics.append(metric)
        
        # 记录历史
        history_key = f"{sla_id}_{target.metric_name}"
        if history_key not in _metric_history:
            _metric_history[history_key] = []
        _metric_history[history_key].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": current_value,
        })
        # 保留最近 100 条
        _metric_history[history_key] = _metric_history[history_key][-100:]
    
    return metrics


async def generate_sla_report(
    sla_id: str,
    period_start: date,
    period_end: date,
) -> Optional[SLAReport]:
    """
    生成 SLA 报告

    Args:
        sla_id: SLA ID
        period_start: 开始日期
        period_end: 结束日期

    Returns:
        SLA 报告
    """
    config = _sla_configs.get(sla_id)
    if not config:
        return None
    
    metrics = await collect_sla_metrics(sla_id)
    
    # 计算总体达标率
    if metrics:
        overall_compliance = sum(m.compliance_percent for m in metrics) / len(metrics)
    else:
        overall_compliance = 100.0
    
    # 收集违规记录
    breaches = []
    for metric in metrics:
        if metric.status == "breached":
            breaches.append({
                "metric_name": metric.metric_name,
                "current_value": metric.current_value,
                "target_value": metric.target_value,
                "unit": metric.unit,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })
    
    report_id = f"sla_report_{uuid.uuid4().hex[:8]}"
    report = SLAReport(
        report_id=report_id,
        sla_id=sla_id,
        service_id=config.service_id,
        period_start=period_start,
        period_end=period_end,
        overall_compliance=round(overall_compliance, 2),
        metrics=metrics,
        breaches=breaches,
        generated_at=datetime.now(timezone.utc),
    )
    
    _sla_reports[report_id] = report
    logger.info(f"SLA report generated: {report_id}")
    return report


async def get_sla_dashboard(period: str = "30d") -> SLADashboardResponse:
    """
    获取 SLA 仪表盘数据

    Args:
        period: 统计周期

    Returns:
        SLA 仪表盘响应
    """
    all_metrics = []
    met_count = 0
    at_risk_count = 0
    breached_count = 0
    recent_breaches = []
    
    for sla_id in _sla_configs:
        metrics = await collect_sla_metrics(sla_id)
        all_metrics.extend(metrics)
        
        for metric in metrics:
            if metric.status == "met":
                met_count += 1
            elif metric.status == "at_risk":
                at_risk_count += 1
            elif metric.status == "breached":
                breached_count += 1
                recent_breaches.append({
                    "sla_id": sla_id,
                    "metric_name": metric.metric_name,
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "unit": metric.unit,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })
    
    overall_compliance = (
        sum(m.compliance_percent for m in all_metrics) / len(all_metrics)
        if all_metrics else 100.0
    )
    
    return SLADashboardResponse(
        total_slas=len(_sla_configs),
        met_count=met_count,
        at_risk_count=at_risk_count,
        breached_count=breached_count,
        overall_compliance=round(overall_compliance, 2),
        metrics=all_metrics,
        recent_breaches=recent_breaches[:10],
        period=period,
    )


async def get_metric_history(sla_id: str, metric_name: str) -> List[dict]:
    """
    获取指标历史数据

    Args:
        sla_id: SLA ID
        metric_name: 指标名称

    Returns:
        历史数据列表
    """
    history_key = f"{sla_id}_{metric_name}"
    return _metric_history.get(history_key, [])


async def create_alert_config(config: SLAAlertConfig) -> SLAAlertConfig:
    """
    创建 SLA 告警配置

    Args:
        config: 告警配置

    Returns:
        创建的告警配置
    """
    if not config.alert_id:
        config.alert_id = f"sla_alert_{uuid.uuid4().hex[:8]}"
    _sla_alerts[config.alert_id] = config
    return config


async def list_alert_configs(sla_id: Optional[str] = None) -> List[SLAAlertConfig]:
    """
    列出 SLA 告警配置

    Args:
        sla_id: SLA ID（可选过滤）

    Returns:
        告警配置列表
    """
    alerts = list(_sla_alerts.values())
    if sla_id:
        alerts = [a for a in alerts if a.sla_id == sla_id]
    return alerts
