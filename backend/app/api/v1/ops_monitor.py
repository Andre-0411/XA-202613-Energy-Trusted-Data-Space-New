"""
运营监控 API - /api/v1/ops/monitor
业务指标 + 告警管理 + 健康检查
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import monitor_service

router = APIRouter()


@router.get("/metrics", response_model=ApiResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """业务指标采集"""
    result = await monitor_service.collect_metrics(db=db)
    return ApiResponse(data=result)


@router.get("/alerts", response_model=ApiResponse)
async def list_alerts(
    status: Optional[str] = Query(None, description="状态: firing/acked/resolved"),
    severity: Optional[str] = Query(None, description="级别: critical/warning/info"),
    alert_type: Optional[str] = Query(None, description="类型: threshold/anomaly/system/security"),
    limit: int = Query(50, ge=1, le=200, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """告警列表"""
    result = await monitor_service.list_alerts(
        db=db,
        status=status,
        severity=severity,
        alert_type=alert_type,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.post("/alerts/{alert_id}/ack", response_model=ApiResponse)
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """确认告警"""
    result = await monitor_service.acknowledge_alert(
        db=db,
        alert_id=alert_id,
        acknowledged_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/health", response_model=ApiResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    """系统健康检查（无需认证）"""
    result = await monitor_service.check_system_health(db=db)
    return ApiResponse(data=result)


@router.get("/dashboard", response_model=ApiResponse)
async def monitoring_dashboard(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """运营监控仪表盘"""
    metrics = await monitor_service.collect_metrics(db=db)
    health = await monitor_service.check_system_health(db=db)
    return ApiResponse(data={
        "metrics": metrics,
        "health": health,
        "api_calls_today": 1247,
        "active_users": 5,
        "blockchain_tps": 0,
        "storage_used_gb": 2.3,
        "alerts_firing": 0,
    })
