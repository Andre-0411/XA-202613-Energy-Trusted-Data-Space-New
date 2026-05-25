"""
WebSocket 连接管理器
4 个端点: notifications / compute / monitor / threats
"""
import logging
from typing import Dict, List, Set
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器 - 按端点分组管理连接"""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {
            "notifications": set(),
            "compute": set(),
            "monitor": set(),
            "threats": set(),
        }

    async def connect(self, websocket: WebSocket, endpoint: str = "notifications") -> None:
        """
        接受 WebSocket 连接

        Args:
            websocket: WebSocket 实例
            endpoint: 端点名称
        """
        await websocket.accept()
        if endpoint in self._connections:
            self._connections[endpoint].add(websocket)
            logger.info(f"WebSocket connected to {endpoint}, total: {len(self._connections[endpoint])}")

    def disconnect(self, websocket: WebSocket, endpoint: str = "notifications") -> None:
        """
        断开 WebSocket 连接

        Args:
            websocket: WebSocket 实例
            endpoint: 端点名称
        """
        if endpoint in self._connections:
            self._connections[endpoint].discard(websocket)
            logger.info(f"WebSocket disconnected from {endpoint}")

    async def broadcast(self, endpoint: str, message: dict) -> None:
        """
        向指定端点的所有连接广播消息

        Args:
            endpoint: 端点名称
            message: 消息字典
        """
        if endpoint not in self._connections:
            return

        message["timestamp"] = datetime.now(timezone.utc).isoformat()
        disconnected = set()

        for ws in self._connections[endpoint]:
            try:
                await ws.send_json(message)
            except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                logger.warning(f"WebSocket send failed: {e}")
                disconnected.add(ws)

        for ws in disconnected:
            self._connections[endpoint].discard(ws)

    async def send_to_user(self, user_id: str, endpoint: str, message: dict) -> None:
        """
        向特定用户发送消息（需要 WebSocket 关联 user_id）

        Note: 实际实现需要在连接时存储 user_id 映射
        """
        # 简化实现：广播到该端点所有连接
        await self.broadcast(endpoint, message)

    def get_connection_count(self, endpoint: str = None) -> int:
        """获取连接数"""
        if endpoint:
            return len(self._connections.get(endpoint, set()))
        return sum(len(conns) for conns in self._connections.values())

    async def send_compute_status(self, task_id: str, status: str, progress: int) -> None:
        """发送计算任务状态更新"""
        await self.broadcast("compute", {
            "type": "task_status",
            "task_id": task_id,
            "status": status,
            "progress": progress,
        })

    async def send_notification(self, notification_type: str, title: str, content: str) -> None:
        """发送通知"""
        await self.broadcast("notifications", {
            "type": notification_type,
            "title": title,
            "content": content,
        })

    async def send_monitor_data(self, metric_name: str, value: float, labels: dict = None) -> None:
        """发送监控数据"""
        await self.broadcast("monitor", {
            "type": "metric",
            "metric_name": metric_name,
            "value": value,
            "labels": labels or {},
        })

    async def send_threat_alert(self, threat_type: str, severity: str, description: str) -> None:
        """发送威胁告警"""
        await self.broadcast("threats", {
            "type": "threat_alert",
            "threat_type": threat_type,
            "severity": severity,
            "description": description,
        })


# 全局 WebSocket 管理器
ws_manager = WebSocketManager()
