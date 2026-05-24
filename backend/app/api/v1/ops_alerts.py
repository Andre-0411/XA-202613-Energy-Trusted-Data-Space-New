"""
告警管理 API 端点
告警 CRUD、告警规则管理、通知渠道管理

⚠️ 路由顺序关键: 所有固定路径 (如 /statistics, /rules) 必须在 /{alert_id} 之前定义,
   否则 FastAPI 会将 "statistics" 等字符串匹配为 alert_id。
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

from app.services import alert_service
from app.utils.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 固定路径路由 (必须在 /{alert_id} 之前) ====================

@router.get("", summary="列出告警")
async def list_alerts(
    user: dict = Depends(get_current_user),
    severity: Optional[str] = Query(default=None, description="严重程度: info/warning/critical"),
    status: Optional[str] = Query(default=None, description="状态: active/resolved"),
    limit: int = Query(default=50, description="限制数量"),
):
    """
    列出告警
    """
    alerts = await alert_service.list_alerts(
        status=status,
        severity=severity,
        limit=limit,
    )
    return {"alerts": alerts, "total": len(alerts)}


@router.post("", summary="创建告警")
async def create_alert(
    user: dict = Depends(get_current_user),
    title: str = Query(description="告警标题"),
    description: str = Query(description="告警描述"),
    severity: str = Query(default="warning", description="严重程度"),
    source: str = Query(default="system", description="来源"),
):
    """
    创建告警
    """
    alert = await alert_service.create_alert(
        title=title,
        description=description,
        severity=severity,
        source=source,
    )
    return alert


@router.get("/statistics", summary="获取告警统计")
async def get_alert_statistics(
    user: dict = Depends(get_current_user),
):
    """
    获取告警统计
    """
    stats = await alert_service.get_alert_statistics()
    return stats


@router.get("/history", summary="获取告警历史")
async def get_alert_history(
    user: dict = Depends(get_current_user),
    alert_id: Optional[str] = Query(default=None, description="告警 ID 过滤"),
    limit: int = Query(default=100),
):
    """
    获取告警历史
    """
    history = await alert_service.get_alert_history(alert_id, limit)
    return {"history": history, "total": len(history)}


@router.get("/notification-channels", summary="列出通知渠道")
async def list_notification_channels(
    user: dict = Depends(get_current_user),
):
    """
    列出通知渠道
    """
    channels = await alert_service.list_notification_channels()
    return {"channels": channels, "total": len(channels)}


@router.post("/check-thresholds", summary="检查阈值告警")
async def check_threshold_alerts(
    user: dict = Depends(get_current_user),
    metrics: dict = None,
):
    """
    检查阈值告警
    """
    triggered = await alert_service.check_threshold_alerts(metrics)
    return {"triggered": triggered, "total": len(triggered)}


# ==================== 告警规则 (固定路径) ====================

@router.get("/rules", summary="列出告警规则")
async def list_alert_rules(
    user: dict = Depends(get_current_user),
):
    """
    列出告警规则
    """
    rules = await alert_service.list_alert_rules()
    return {"rules": rules, "total": len(rules)}


@router.post("/rules", summary="创建告警规则")
async def create_alert_rule(
    user: dict = Depends(get_current_user),
    rule: dict = None,
):
    """
    创建告警规则
    """
    result = await alert_service.create_alert_rule(rule)
    return result


@router.put("/rules/{rule_id}", summary="更新告警规则")
async def update_alert_rule(
    user: dict = Depends(get_current_user),
    rule_id: str = None,
    rule: dict = None,
):
    """
    更新告警规则
    """
    result = await alert_service.update_alert_rule(rule_id, rule)
    if not result:
        raise HTTPException(status_code=404, detail="告警规则未找到")
    return result


@router.delete("/rules/{rule_id}", summary="删除告警规则")
async def delete_alert_rule(
    user: dict = Depends(get_current_user),
    rule_id: str = None,
):
    """
    删除告警规则
    """
    success = await alert_service.delete_alert_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="告警规则未找到")
    return {"success": True, "message": "告警规则已删除"}


# ==================== 告警静默规则 (固定路径) ====================

@router.post("/silence-rules", summary="创建静默规则")
async def create_silence_rule(
    user: dict = Depends(get_current_user),
    rule: dict = None,
):
    """
    创建告警静默规则

    规则字段:
    - name: 规则名称
    - enabled: 是否启用（默认 false）
    - matchers: 匹配条件 {field: value}，空字典匹配所有
    - start_time: 静默开始时间 (ISO 8601)
    - end_time: 静默结束时间 (ISO 8601)
    """
    result = await alert_service.create_silence_rule(rule)
    return result


@router.get("/silence-rules", summary="列出静默规则")
async def list_silence_rules(
    user: dict = Depends(get_current_user),
):
    """
    列出静默规则
    """
    rules = await alert_service.list_silence_rules()
    return {"rules": rules, "total": len(rules)}


@router.delete("/silence-rules/{silence_id}", summary="删除静默规则")
async def delete_silence_rule(
    user: dict = Depends(get_current_user),
    silence_id: str = None,
):
    """
    删除静默规则
    """
    success = await alert_service.delete_silence_rule(silence_id)
    if not success:
        raise HTTPException(status_code=404, detail="静默规则未找到")
    return {"success": True, "message": "静默规则已删除"}


# ==================== 告警抑制规则 (固定路径) ====================

@router.get("/inhibition-rules", summary="列出抑制规则")
async def list_inhibition_rules(
    user: dict = Depends(get_current_user),
):
    """
    列出所有告警抑制规则

    抑制规则说明：当一个更高严重程度的告警处于活跃状态时，
    抑制相同来源的较低严重程度告警。
    """
    rules = await alert_service.list_inhibition_rules()
    return {"rules": rules, "total": len(rules)}


# ==================== 动态路径路由 (必须在固定路径之后) ====================

@router.get("/{alert_id}", summary="获取告警详情")
async def get_alert(
    user: dict = Depends(get_current_user),
    alert_id: str = None,
):
    """
    获取告警详情
    """
    alert = await alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警未找到")
    return alert


@router.post("/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(
    user: dict = Depends(get_current_user),
    alert_id: str = None,
    user_id: str = Query(description="用户 ID"),
):
    """
    确认告警
    """
    success = await alert_service.acknowledge_alert(alert_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="告警未找到")
    return {"success": True, "message": "告警已确认"}


@router.post("/{alert_id}/resolve", summary="解决告警")
async def resolve_alert(
    user: dict = Depends(get_current_user),
    alert_id: str = None,
    user_id: Optional[str] = Query(default=None),
):
    """
    解决告警
    """
    success = await alert_service.resolve_alert(alert_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="告警未找到")
    return {"success": True, "message": "告警已解决"}