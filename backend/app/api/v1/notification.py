"""
通知公告管理 API
提供通知的CRUD、已读状态管理、批量操作等端点
集成WebSocket实时推送
数据持久化至 portal_notifications 表
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.portal_model import PortalNotification
from app.services.websocket_manager import (
    get_ws_manager, WSMessage, WSMessageType, WSChannel,
    notify_user_notification, notify_system_broadcast,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ===== Pydantic 数据模型 =====

class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="通知标题")
    content: str = Field(..., min_length=1, description="通知内容")
    type: str = Field(default="info", description="通知类型: info/warning/error/success")
    priority: str = Field(default="normal", description="优先级: low/normal/high/urgent")
    category: str = Field(default="system", description="分类: system/task/security/billing")
    target_users: Optional[List[str]] = Field(default=None, description="目标用户ID列表，None表示全员")
    sender: str = Field(default="system", description="发送者")

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    type: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    target_users: Optional[List[str]] = None
    sender: Optional[str] = None

class NotificationResponse(BaseModel):
    id: str
    title: str
    content: str
    type: str
    priority: str
    category: str
    target_users: Optional[List[str]] = None
    sender: str
    created_at: datetime
    updated_at: datetime
    is_read: bool = False
    read_at: Optional[datetime] = None

class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


def _model_to_response(n: PortalNotification) -> dict:
    """将 DB 模型转换为 API 响应字典"""
    return {
        "id": str(n.id),
        "title": n.title,
        "content": n.content,
        "type": n.notification_type,
        "priority": n.priority,
        "category": n.category,
        "target_users": n.target_users,
        "sender": n.sender,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        "is_read": n.read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
    }


# ===== API端点 =====

@router.get("/", summary="获取通知列表")
async def get_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    type: Optional[str] = Query(None, description="通知类型筛选"),
    category: Optional[str] = Query(None, description="分类筛选"),
    is_read: Optional[bool] = Query(None, description="已读状态筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取通知列表，支持分页和筛选"""
    # 构建查询条件
    conditions = []
    if type:
        conditions.append(PortalNotification.notification_type == type)
    if category:
        conditions.append(PortalNotification.category == category)
    if is_read is not None:
        conditions.append(PortalNotification.read == is_read)
    if priority:
        conditions.append(PortalNotification.priority == priority)

    where_clause = and_(*conditions) if conditions else True

    # 查询总数
    total_stmt = select(func.count()).select_from(PortalNotification).where(where_clause)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    # 查询未读数
    unread_stmt = select(func.count()).select_from(PortalNotification).where(
        PortalNotification.read == False
    )
    unread_result = await db.execute(unread_stmt)
    unread_count = unread_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    stmt = (
        select(PortalNotification)
        .where(where_clause)
        .order_by(PortalNotification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = [_model_to_response(n) for n in result.scalars().all()]

    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "unread_count": unread_count,
        }
    }


@router.get("/unread-count", summary="获取未读通知数量")
async def get_unread_count(db: AsyncSession = Depends(get_db)):
    """获取未读通知数量"""
    stmt = select(func.count()).select_from(PortalNotification).where(
        PortalNotification.read == False
    )
    result = await db.execute(stmt)
    unread_count = result.scalar() or 0
    return {
        "code": 0,
        "message": "success",
        "data": {"unread_count": unread_count}
    }


@router.get("/{notification_id}", summary="获取通知详情")
async def get_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个通知详情"""
    stmt = select(PortalNotification).where(PortalNotification.id == uuid.UUID(notification_id))
    result = await db.execute(stmt)
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"code": 0, "message": "success", "data": _model_to_response(n)}


@router.post("/", summary="创建通知")
async def create_notification(data: NotificationCreate, db: AsyncSession = Depends(get_db)):
    """创建新通知并实时推送"""
    notification = PortalNotification(
        title=data.title,
        content=data.content,
        notification_type=data.type,
        priority=data.priority,
        category=data.category,
        target_users=data.target_users,
        sender=data.sender,
        read=False,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    notif_data = _model_to_response(notification)

    # WebSocket实时推送
    notification_ws_data = {
        "action": "created",
        "notification": notif_data,
    }
    try:
        if data.target_users:
            for user_id in data.target_users:
                await notify_user_notification(user_id, notification_ws_data)
        else:
            await notify_system_broadcast(notification_ws_data)
    except Exception as e:
        logger.warning(f"WebSocket notification push failed: {e}")

    return {"code": 0, "message": "创建成功", "data": notif_data}


@router.put("/{notification_id}", summary="更新通知")
async def update_notification(
    notification_id: str,
    data: NotificationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新通知信息"""
    stmt = select(PortalNotification).where(PortalNotification.id == uuid.UUID(notification_id))
    result = await db.execute(stmt)
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")

    update_data = data.model_dump(exclude_unset=True)
    # 字段映射: type -> notification_type
    if "type" in update_data:
        update_data["notification_type"] = update_data.pop("type")

    for key, value in update_data.items():
        if hasattr(n, key):
            setattr(n, key, value)

    await db.commit()
    await db.refresh(n)
    return {"code": 0, "message": "更新成功", "data": _model_to_response(n)}


@router.delete("/{notification_id}", summary="删除通知")
async def delete_notification(notification_id: str, db: AsyncSession = Depends(get_db)):
    """删除通知"""
    stmt = select(PortalNotification).where(PortalNotification.id == uuid.UUID(notification_id))
    result = await db.execute(stmt)
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")

    await db.delete(n)
    await db.commit()
    return {"code": 0, "message": "删除成功"}


@router.post("/{notification_id}/read", summary="标记通知为已读")
async def mark_as_read(notification_id: str, db: AsyncSession = Depends(get_db)):
    """标记单个通知为已读并同步状态"""
    stmt = select(PortalNotification).where(PortalNotification.id == uuid.UUID(notification_id))
    result = await db.execute(stmt)
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")

    n.read = True
    n.read_at = datetime.now(timezone.utc)
    await db.commit()

    # WebSocket状态同步
    try:
        target_users = n.target_users
        if target_users:
            for user_id in target_users:
                manager = get_ws_manager()
                await manager.send_to_user(user_id, WSMessage(
                    type=WSMessageType.NOTIFICATION,
                    data={
                        "action": "read",
                        "notification_id": notification_id,
                    },
                ))
    except Exception as e:
        logger.warning(f"WebSocket read status sync failed: {e}")

    return {"code": 0, "message": "已标记为已读"}


@router.post("/read-all", summary="标记所有通知为已读")
async def mark_all_as_read(db: AsyncSession = Depends(get_db)):
    """标记所有通知为已读"""
    now = datetime.now(timezone.utc)
    stmt = (
        select(PortalNotification)
        .where(PortalNotification.read == False)
    )
    result = await db.execute(stmt)
    unread = result.scalars().all()
    for n in unread:
        n.read = True
        n.read_at = now
    await db.commit()
    return {"code": 0, "message": f"已全部标记为已读 ({len(unread)} 条)"}


@router.post("/batch-delete", summary="批量删除通知")
async def batch_delete_notifications(
    notification_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """批量删除通知"""
    uuids = [uuid.UUID(nid) for nid in notification_ids]
    stmt = delete(PortalNotification).where(PortalNotification.id.in_(uuids))
    result = await db.execute(stmt)
    await db.commit()
    return {"code": 0, "message": f"成功删除 {result.rowcount} 条通知"}


@router.post("/batch-read", summary="批量标记已读")
async def batch_mark_as_read(
    notification_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """批量标记通知为已读"""
    now = datetime.now(timezone.utc)
    uuids = [uuid.UUID(nid) for nid in notification_ids]
    stmt = select(PortalNotification).where(
        and_(
            PortalNotification.id.in_(uuids),
            PortalNotification.read == False,
        )
    )
    result = await db.execute(stmt)
    unread = result.scalars().all()
    for n in unread:
        n.read = True
        n.read_at = now
    await db.commit()
    return {"code": 0, "message": f"已标记 {len(unread)} 条通知为已读"}
