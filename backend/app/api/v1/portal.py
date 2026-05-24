"""
统一门户 API 端点
仪表盘数据、快速入口、通知管理、布局配置
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.portal import (
    PortalDashboardRequest, PortalDashboardResponse,
    QuickLinkItem, PortalLayoutConfig,
)
from app.services import portal_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard", response_model=PortalDashboardResponse, summary="获取门户仪表盘")
async def get_dashboard(
    user_id: str = Query(description="用户 ID"),
    role: Optional[str] = Query(default=None, description="用户角色"),
    time_range: str = Query(default="7d", description="时间范围"),
    db: AsyncSession = Depends(get_db),
):
    """获取门户仪表盘数据"""
    return await portal_service.get_dashboard_data(
        db=db,
        user_id=user_id,
        role=role,
        time_range=time_range,
    )


@router.get("/quick-links", summary="获取快速链接")
async def get_quick_links(db: AsyncSession = Depends(get_db)):
    """获取快速链接列表"""
    links = await portal_service.get_quick_links(db)
    return {"links": [l.model_dump() for l in links]}


@router.post("/quick-links", summary="添加快速链接")
async def add_quick_link(link: QuickLinkItem, db: AsyncSession = Depends(get_db)):
    """添加快速链接"""
    result = await portal_service.add_quick_link(db, link)
    return result.model_dump()


@router.delete("/quick-links/{link_id}", summary="删除快速链接")
async def remove_quick_link(link_id: str, db: AsyncSession = Depends(get_db)):
    """删除快速链接"""
    success = await portal_service.remove_quick_link(db, link_id)
    if not success:
        raise HTTPException(status_code=404, detail="链接未找到")
    return {"success": True, "message": "链接已删除"}


@router.get("/overview", summary="获取数据概览")
async def get_data_overview(
    time_range: str = Query(default="7d"),
    db: AsyncSession = Depends(get_db),
):
    """获取数据概览"""
    overview = await portal_service.get_data_overview(db, time_range)
    return {"overview": [o.model_dump() for o in overview]}


@router.get("/notifications", summary="获取通知")
async def get_notifications(
    user_id: str = Query(description="用户 ID"),
    unread_only: bool = Query(default=False, description="仅未读"),
    limit: int = Query(default=20, description="限制数量"),
    db: AsyncSession = Depends(get_db),
):
    """获取用户通知"""
    notifications = await portal_service.get_notifications(
        db=db,
        user_id=user_id,
        unread_only=unread_only,
        limit=limit,
    )
    return {"notifications": [n.model_dump() for n in notifications]}


@router.put("/notifications/{notification_id}/read", summary="标记通知已读")
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    """标记通知为已读"""
    success = await portal_service.mark_notification_read(db, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="通知未找到")
    return {"success": True, "message": "已标记为已读"}


@router.get("/layout", summary="获取布局配置")
async def get_layout(
    user_id: str = Query(description="用户 ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取用户布局配置"""
    layout = await portal_service.get_layout_config(db, user_id)
    return layout.model_dump()


@router.put("/layout", summary="保存布局配置")
async def save_layout(config: PortalLayoutConfig, db: AsyncSession = Depends(get_db)):
    """保存用户布局配置"""
    result = await portal_service.save_layout_config(db, config)
    return result.model_dump()


@router.get("/activities", summary="获取活动日志")
async def get_activities(
    user_id: Optional[str] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
    db: AsyncSession = Depends(get_db),
):
    """获取活动日志"""
    activities = await portal_service.get_activity_logs(
        db=db,
        user_id=user_id,
        resource_type=resource_type,
        limit=limit,
    )
    return {"activities": [a.model_dump() for a in activities]}
