"""
WebSocket 连接管理器
实时推送、频道订阅、心跳检测、连接池管理
支持JWT认证、通知广播、离线消息队列
"""
import uuid
import logging
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Set, Any
from fastapi import WebSocket

from app.schemas.websocket import (
    WSMessage, WSMessageType, WSChannel, WSConnectionInfo,
    WSConnectionStats, WSRoomInfo,
)

logger = logging.getLogger(__name__)

# 离线消息队列大小限制
MAX_OFFLINE_QUEUE_SIZE = 100

# 连接管理
_connections: Dict[str, WebSocket] = {}
_connection_info: Dict[str, dict] = {}
_channel_subscribers: Dict[str, Set[str]] = {}
_rooms: Dict[str, WSRoomInfo] = {}

# 统计
_start_time = datetime.now(timezone.utc)
_total_connections = 0


class WebSocketManager:
    """WebSocket 连接管理器

    支持功能:
    - 频道订阅/取消订阅
    - 心跳检测和超时清理
    - 向特定用户/频道/全部广播
    - 离线消息队列（用户上线后推送）
    - JWT认证支持
    - 通知实时推送
    """

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, dict] = {}
        self.channel_subscribers: Dict[str, Set[str]] = {}
        self.rooms: Dict[str, WSRoomInfo] = {}
        self.start_time = datetime.now(timezone.utc)
        self.total_connections = 0
        self._heartbeat_task: Optional[asyncio.Task] = None
        # 用户 -> 连接ID列表映射（支持同一用户多端登录）
        self._user_connections: Dict[str, Set[str]] = {}
        # 离线消息队列: user_id -> [messages]
        self._offline_queue: Dict[str, List[dict]] = {}
        # 统计计数
        self._messages_sent = 0
        self._messages_failed = 0
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """
        接受 WebSocket 连接

        Args:
            websocket: WebSocket 连接
            user_id: 用户 ID（从JWT token解析）

        Returns:
            连接 ID
        """
        await websocket.accept()

        connection_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        self.connections[connection_id] = websocket
        self.connection_info[connection_id] = {
            "connection_id": connection_id,
            "user_id": user_id,
            "channels": [],
            "connected_at": now,
            "last_heartbeat": now,
            "ip_address": None,
            "user_agent": None,
        }
        self.total_connections += 1

        # 维护用户 -> 连接映射
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        # 发送连接确认
        await self._send_to_connection(connection_id, WSMessage(
            type=WSMessageType.CONNECT,
            data={"connection_id": connection_id, "message": "连接成功"},
        ))

        # 推送离线消息
        if user_id and user_id in self._offline_queue:
            queued = self._offline_queue.pop(user_id)
            for msg in queued:
                await self._send_to_connection(connection_id, WSMessage(
                    type=WSMessageType.NOTIFICATION,
                    data=msg,
                ))
            logger.info(f"Pushed {len(queued)} offline messages to user {user_id}")

        logger.info(f"WebSocket connected: {connection_id}, user={user_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        断开 WebSocket 连接

        Args:
            connection_id: 连接 ID
        """
        # 取消所有频道订阅
        info = self.connection_info.get(connection_id)
        if info:
            for channel in info.get("channels", []):
                if channel in self.channel_subscribers:
                    self.channel_subscribers[channel].discard(connection_id)
            # 清理用户连接映射
            user_id = info.get("user_id")
            if user_id and user_id in self._user_connections:
                self._user_connections[user_id].discard(connection_id)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]

        # 移除连接
        self.connections.pop(connection_id, None)
        self.connection_info.pop(connection_id, None)

        # 移除房间成员
        for room in self.rooms.values():
            if connection_id in room.members:
                room.members.remove(connection_id)

        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def subscribe(self, connection_id: str, channels: List[str]) -> bool:
        """
        订阅频道

        Args:
            connection_id: 连接 ID
            channels: 频道列表

        Returns:
            是否成功
        """
        if connection_id not in self.connections:
            return False
        
        info = self.connection_info[connection_id]
        
        for channel in channels:
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = set()
            self.channel_subscribers[channel].add(connection_id)
            
            if channel not in info["channels"]:
                info["channels"].append(channel)
        
        await self._send_to_connection(connection_id, WSMessage(
            type=WSMessageType.SUBSCRIBE,
            data={"channels": channels, "message": "订阅成功"},
        ))
        
        logger.info(f"WebSocket {connection_id} subscribed to {channels}")
        return True
    
    async def unsubscribe(self, connection_id: str, channels: List[str]) -> bool:
        """
        取消订阅频道

        Args:
            connection_id: 连接 ID
            channels: 频道列表

        Returns:
            是否成功
        """
        if connection_id not in self.connections:
            return False
        
        info = self.connection_info[connection_id]
        
        for channel in channels:
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].discard(connection_id)
            
            if channel in info["channels"]:
                info["channels"].remove(channel)
        
        await self._send_to_connection(connection_id, WSMessage(
            type=WSMessageType.UNSUBSCRIBE,
            data={"channels": channels, "message": "取消订阅成功"},
        ))
        
        return True
    
    async def broadcast_to_channel(self, channel: str, message: WSMessage):
        """
        向频道广播消息

        Args:
            channel: 频道
            message: 消息
        """
        subscribers = self.channel_subscribers.get(channel, set()).copy()
        disconnected = []

        for conn_id in subscribers:
            try:
                await self._send_to_connection(conn_id, message)
                self._messages_sent += 1
            except Exception:
                self._messages_failed += 1
                disconnected.append(conn_id)

        # 清理断开的连接
        for conn_id in disconnected:
            await self.disconnect(conn_id)
    
    async def send_to_user(self, user_id: str, message: WSMessage, queue_if_offline: bool = True):
        """
        向特定用户发送消息

        Args:
            user_id: 用户 ID
            message: 消息
            queue_if_offline: 用户离线时是否缓存消息
        """
        sent = False
        conn_ids = self._user_connections.get(user_id, set()).copy()
        for conn_id in conn_ids:
            try:
                await self._send_to_connection(conn_id, message)
                sent = True
            except Exception:
                await self.disconnect(conn_id)

        # 用户离线且启用离线队列时缓存
        if not sent and queue_if_offline:
            if user_id not in self._offline_queue:
                self._offline_queue[user_id] = []
            queue = self._offline_queue[user_id]
            if len(queue) < MAX_OFFLINE_QUEUE_SIZE:
                data = message.model_dump()
                if "timestamp" in data and isinstance(data["timestamp"], datetime):
                    data["timestamp"] = data["timestamp"].isoformat()
                queue.append(data)
                logger.info(f"Queued offline message for user {user_id}")
    
    async def broadcast_all(self, message: WSMessage):
        """
        向所有连接广播消息

        Args:
            message: 消息
        """
        disconnected = []
        for conn_id in list(self.connections.keys()):
            try:
                await self._send_to_connection(conn_id, message)
                self._messages_sent += 1
            except Exception:
                self._messages_failed += 1
                disconnected.append(conn_id)

        for conn_id in disconnected:
            await self.disconnect(conn_id)
    
    async def handle_heartbeat(self, connection_id: str):
        """
        处理心跳

        Args:
            connection_id: 连接 ID
        """
        if connection_id in self.connection_info:
            self.connection_info[connection_id]["last_heartbeat"] = datetime.now(timezone.utc)
            await self._send_to_connection(connection_id, WSMessage(
                type=WSMessageType.HEARTBEAT,
                data={"timestamp": datetime.now(timezone.utc).isoformat()},
            ))
    
    async def check_stale_connections(self, timeout_seconds: int = 60):
        """
        检查并清理超时连接

        Args:
            timeout_seconds: 超时秒数
        """
        now = datetime.now(timezone.utc)
        stale = []
        
        for conn_id, info in self.connection_info.items():
            last_hb = info.get("last_heartbeat", info.get("connected_at", now))
            if (now - last_hb).total_seconds() > timeout_seconds:
                stale.append(conn_id)
        
        for conn_id in stale:
            logger.warning(f"Closing stale WebSocket connection: {conn_id}")
            await self.disconnect(conn_id)
    
    def get_connection_info(self, connection_id: str) -> Optional[WSConnectionInfo]:
        """获取连接信息"""
        info = self.connection_info.get(connection_id)
        if info:
            return WSConnectionInfo(**info)
        return None
    
    def get_connection_stats(self) -> WSConnectionStats:
        """获取连接统计"""
        channel_stats = {}
        for channel, subscribers in self.channel_subscribers.items():
            channel_stats[channel] = len(subscribers)

        return WSConnectionStats(
            total_connections=self.total_connections,
            active_connections=len(self.connections),
            channels=channel_stats,
            uptime_seconds=(datetime.now(timezone.utc) - self.start_time).total_seconds(),
        )

    def get_user_connection_count(self, user_id: str) -> int:
        """获取指定用户的活跃连接数"""
        return len(self._user_connections.get(user_id, set()))

    def get_offline_queue_size(self, user_id: str) -> int:
        """获取用户离线消息队列大小"""
        return len(self._offline_queue.get(user_id, []))

    def get_all_stats(self) -> dict:
        """获取完整统计信息"""
        stats = self.get_connection_stats()
        return {
            **stats.model_dump(),
            "unique_users": len(self._user_connections),
            "offline_queue_users": len(self._offline_queue),
            "messages_sent": self._messages_sent,
            "messages_failed": self._messages_failed,
        }
    
    def get_room_info(self, room_id: str) -> Optional[WSRoomInfo]:
        """获取房间信息"""
        return self.rooms.get(room_id)
    
    async def create_room(self, room_id: str, channel: str, metadata: Optional[dict] = None) -> WSRoomInfo:
        """创建房间"""
        room = WSRoomInfo(
            room_id=room_id,
            channel=channel,
            members=[],
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        self.rooms[room_id] = room
        return room
    
    async def join_room(self, room_id: str, connection_id: str) -> bool:
        """加入房间"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        if connection_id not in room.members:
            room.members.append(connection_id)
        return True
    
    async def leave_room(self, room_id: str, connection_id: str) -> bool:
        """离开房间"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        if connection_id in room.members:
            room.members.remove(connection_id)
        return True
    
    async def _send_to_connection(self, connection_id: str, message: WSMessage):
        """向连接发送消息"""
        websocket = self.connections.get(connection_id)
        if websocket:
            data = message.model_dump()
            # 序列化 datetime
            if "timestamp" in data and isinstance(data["timestamp"], datetime):
                data["timestamp"] = data["timestamp"].isoformat()
            await websocket.send_json(data)


# 全局单例
_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """获取 WebSocket 管理器单例"""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager


# ==================== 便捷函数 ====================

async def notify_alert(alert_data: dict):
    """发送告警通知"""
    manager = get_ws_manager()
    await manager.broadcast_to_channel("alerts", WSMessage(
        type=WSMessageType.ALERT,
        channel=WSChannel.ALERTS,
        data=alert_data,
    ))


async def notify_metric_update(metric_data: dict):
    """发送指标更新"""
    manager = get_ws_manager()
    await manager.broadcast_to_channel("metrics", WSMessage(
        type=WSMessageType.METRIC_UPDATE,
        channel=WSChannel.METRICS,
        data=metric_data,
    ))


async def notify_audit_event(audit_data: dict):
    """发送审计事件"""
    manager = get_ws_manager()
    await manager.broadcast_to_channel("audit", WSMessage(
        type=WSMessageType.AUDIT_EVENT,
        channel=WSChannel.AUDIT,
        data=audit_data,
    ))


async def notify_task_update(task_data: dict):
    """发送任务更新"""
    manager = get_ws_manager()
    await manager.broadcast_to_channel("tasks", WSMessage(
        type=WSMessageType.TASK_UPDATE,
        channel=WSChannel.TASKS,
        data=task_data,
    ))


async def notify_user_notification(user_id: str, notification_data: dict):
    """
    向特定用户推送通知

    Args:
        user_id: 用户ID
        notification_data: 通知数据
    """
    manager = get_ws_manager()
    await manager.send_to_user(user_id, WSMessage(
        type=WSMessageType.NOTIFICATION,
        channel=WSChannel.NOTIFICATIONS,
        data=notification_data,
    ))


async def notify_system_broadcast(notification_data: dict):
    """
    系统全员广播通知

    Args:
        notification_data: 通知数据
    """
    manager = get_ws_manager()
    await manager.broadcast_to_channel("notifications", WSMessage(
        type=WSMessageType.NOTIFICATION,
        channel=WSChannel.NOTIFICATIONS,
        data=notification_data,
    ))


async def notify_notification_read(user_id: str, notification_id: str):
    """
    通知已读状态同步

    Args:
        user_id: 用户ID
        notification_id: 通知ID
    """
    manager = get_ws_manager()
    await manager.send_to_user(user_id, WSMessage(
        type=WSMessageType.NOTIFICATION,
        data={
            "action": "read",
            "notification_id": notification_id,
        },
    ))
