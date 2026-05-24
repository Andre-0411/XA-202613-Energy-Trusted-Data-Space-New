"""
WebSocket Schema
实时推送、连接管理、频道订阅
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WSMessageType(str, Enum):
    """WebSocket 消息类型"""
    # 系统消息
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    # 订阅管理
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    # 数据推送
    NOTIFICATION = "notification"
    ALERT = "alert"
    METRIC_UPDATE = "metric_update"
    AUDIT_EVENT = "audit_event"
    TASK_UPDATE = "task_update"
    DATA_UPDATE = "data_update"
    BLOCKCHAIN_EVENT = "blockchain_event"


class WSChannel(str, Enum):
    """WebSocket 频道"""
    SYSTEM = "system"
    ALERTS = "alerts"
    METRICS = "metrics"
    AUDIT = "audit"
    TASKS = "tasks"
    DATA = "data"
    BLOCKCHAIN = "blockchain"
    NOTIFICATIONS = "notifications"


class WSMessage(BaseModel):
    """WebSocket 消息"""
    type: WSMessageType = Field(description="消息类型")
    channel: Optional[WSChannel] = Field(default=None, description="频道")
    data: Dict[str, Any] = Field(default_factory=dict, description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    message_id: Optional[str] = Field(default=None, description="消息 ID")


class WSSubscriptionRequest(BaseModel):
    """WebSocket 订阅请求"""
    channels: List[WSChannel] = Field(description="订阅频道列表")


class WSConnectionInfo(BaseModel):
    """WebSocket 连接信息"""
    connection_id: str = Field(description="连接 ID")
    user_id: Optional[str] = Field(default=None, description="用户 ID")
    channels: List[str] = Field(default_factory=list, description="订阅频道")
    connected_at: datetime = Field(description="连接时间")
    last_heartbeat: datetime = Field(description="最后心跳时间")
    ip_address: Optional[str] = Field(default=None, description="IP 地址")
    user_agent: Optional[str] = Field(default=None, description="User Agent")


class WSConnectionStats(BaseModel):
    """WebSocket 连接统计"""
    total_connections: int = Field(description="总连接数")
    active_connections: int = Field(description="活跃连接数")
    channels: Dict[str, int] = Field(default_factory=dict, description="各频道连接数")
    uptime_seconds: float = Field(description="服务运行时间(秒)")


class WSBroadcastRequest(BaseModel):
    """WebSocket 广播请求"""
    channel: WSChannel = Field(description="目标频道")
    type: WSMessageType = Field(default=WSMessageType.NOTIFICATION, description="消息类型")
    data: Dict[str, Any] = Field(description="消息数据")


class WSRoomInfo(BaseModel):
    """WebSocket 房间信息"""
    room_id: str = Field(description="房间 ID")
    channel: str = Field(description="频道")
    members: List[str] = Field(default_factory=list, description="成员连接 ID 列表")
    created_at: datetime = Field(description="创建时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
