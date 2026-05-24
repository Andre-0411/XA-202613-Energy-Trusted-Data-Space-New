"""
SLA (服务等级协议) API 端点
SLA 配置管理、指标采集、报告生成、仪表盘
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.sla import (
    SLAConfig, SLATarget, SLAMetricData, SLAReport,
    SLAAlertConfig, SLADashboardResponse,
)
from app.services import sla_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/configs", summary="列出 SLA 配置")
async def list_configs():
    """
    列出所有 SLA 配置
    """
    configs = await sla_service.list_sla_configs()
    return {"configs": [c.model_dump() for c in configs]}


@router.get("/configs/{sla_id}", summary="获取 SLA 配置")
async def get_config(sla_id: str):
    """
    获取指定 SLA 配置
    """
    config = await sla_service.get_sla_config(sla_id)
    if not config:
        raise HTTPException(status_code=404, detail="SLA 配置未找到")
    return config.model_dump()


@router.post("/configs", summary="创建 SLA 配置")
async def create_config(config: SLAConfig):
    """
    创建 SLA 配置
    """
    result = await sla_service.create_sla_config(config)
    return result.model_dump()


@router.put("/configs/{sla_id}", summary="更新 SLA 配置")
async def update_config(sla_id: str, config: SLAConfig):
    """
    更新 SLA 配置
    """
    result = await sla_service.update_sla_config(sla_id, config)
    if not result:
        raise HTTPException(status_code=404, detail="SLA 配置未找到")
    return result.model_dump()


@router.delete("/configs/{sla_id}", summary="删除 SLA 配置")
async def delete_config(sla_id: str):
    """
    删除 SLA 配置
    """
    success = await sla_service.delete_sla_config(sla_id)
    if not success:
        raise HTTPException(status_code=404, detail="SLA 配置未找到")
    return {"success": True, "message": "SLA 配置已删除"}


@router.get("/metrics/{sla_id}", summary="采集 SLA 指标")
async def collect_metrics(sla_id: str):
    """
    采集指定 SLA 的指标数据
    """
    metrics = await sla_service.collect_sla_metrics(sla_id)
    return {"sla_id": sla_id, "metrics": [m.model_dump() for m in metrics]}


@router.post("/reports", summary="生成 SLA 报告")
async def generate_report(
    sla_id: str = Query(description="SLA ID"),
    period_start: date = Query(description="开始日期"),
    period_end: date = Query(description="结束日期"),
):
    """
    生成 SLA 报告
    """
    report = await sla_service.generate_sla_report(
        sla_id=sla_id,
        period_start=period_start,
        period_end=period_end,
    )
    if not report:
        raise HTTPException(status_code=404, detail="SLA 配置未找到")
    return report.model_dump()


@router.get("/dashboard", response_model=SLADashboardResponse, summary="SLA 仪表盘")
async def get_dashboard(period: str = Query(default="30d")):
    """
    获取 SLA 仪表盘数据
    """
    return await sla_service.get_sla_dashboard(period)


@router.get("/metrics/{sla_id}/history", summary="获取指标历史")
async def get_metric_history(
    sla_id: str,
    metric_name: str = Query(description="指标名称"),
):
    """
    获取指标历史数据
    """
    history = await sla_service.get_metric_history(sla_id, metric_name)
    return {"sla_id": sla_id, "metric_name": metric_name, "history": history}


@router.post("/alerts", summary="创建 SLA 告警配置")
async def create_alert_config(config: SLAAlertConfig):
    """
    创建 SLA 告警配置
    """
    result = await sla_service.create_alert_config(config)
    return result.model_dump()


@router.get("/alerts", summary="列出 SLA 告警配置")
async def list_alert_configs(sla_id: Optional[str] = Query(default=None)):
    """
    列出 SLA 告警配置
    """
    configs = await sla_service.list_alert_configs(sla_id)
    return {"configs": [c.model_dump() for c in configs]}
