"""
监控增强 API 端点
系统指标、应用指标、自定义指标、Prometheus 集成、健康检查
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response

from app.services import monitoring_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/system", summary="获取系统指标")
async def get_system_metrics():
    """
    获取系统指标（CPU、内存、磁盘、网络）
    """
    metrics = await monitoring_service.collect_system_metrics()
    return metrics


@router.get("/application", summary="获取应用指标")
async def get_application_metrics():
    """
    获取应用指标（API、数据库、缓存、WebSocket）
    """
    metrics = await monitoring_service.collect_application_metrics()
    return metrics


@router.get("/metrics/{metric_name}/values", summary="获取指标历史值")
async def get_metric_values(
    metric_name: str,
    limit: int = Query(default=100, description="限制数量"),
):
    """
    获取指定指标的历史值
    """
    values = await monitoring_service.get_metric_values(metric_name, limit=limit)
    return {"metric_name": metric_name, "values": values}


@router.post("/metrics/register", summary="注册自定义指标")
async def register_metric(
    name: str = Query(description="指标名称"),
    metric_type: str = Query(description="类型: gauge/counter/histogram"),
    unit: str = Query(description="单位"),
    description: str = Query(description="描述"),
    category: str = Query(default="custom", description="分类"),
):
    """
    注册自定义指标
    """
    result = await monitoring_service.register_custom_metric(
        name=name,
        metric_type=metric_type,
        unit=unit,
        description=description,
        category=category,
    )
    return result


@router.get("/metrics/registry", summary="列出注册指标")
async def list_metrics_registry():
    """
    列出所有注册的指标
    """
    metrics = await monitoring_service.list_metrics_registry()
    return {"metrics": metrics, "total": len(metrics)}


@router.get("/prometheus", summary="Prometheus 指标")
async def get_prometheus_metrics():
    """
    获取 Prometheus 格式的指标数据
    """
    metrics_text = await monitoring_service.get_prometheus_metrics()
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/health", summary="系统健康检查")
async def get_health_status():
    """
    获取系统健康状态
    """
    status = await monitoring_service.get_health_status()
    return status


@router.get("/trend-alerts", summary="趋势告警检查")
async def check_trend_alerts(
    metric_name: str = Query(description="指标名称"),
    window_minutes: int = Query(default=10, description="窗口时间(分钟)"),
):
    """
    检查趋势告警
    """
    alerts = await monitoring_service.check_trend_alerts(
        metric_name=metric_name,
        window_minutes=window_minutes,
    )
    return {"alerts": alerts, "total": len(alerts)}
