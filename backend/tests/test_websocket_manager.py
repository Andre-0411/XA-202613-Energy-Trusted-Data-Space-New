"""
WebSocket 管理器单元测试
测试 websocket_manager.py 中的消息广播、用户订阅、通知类型路由等功能
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone


class TestWebSocketManagerInit:
    """测试 WebSocket 管理器初始化"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        assert manager.connections == {}
        assert manager.connection_info == {}
        assert manager.channel_subscribers == {}
        assert manager.rooms == {}
        assert manager.total_connections == 0

    def test_get_ws_manager_singleton(self):
        """测试获取全局单例"""
        from app.services.websocket_manager import get_ws_manager, _manager

        # 重置全局单例
        import app.services.websocket_manager as ws_module
        ws_module._manager = None

        manager1 = get_ws_manager()
        manager2 = get_ws_manager()

        assert manager1 is manager2


class TestWebSocketConnection:
    """测试 WebSocket 连接管理"""

    @pytest.mark.asyncio
    async def test_connect(self, mock_websocket):
        """测试建立连接"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket, user_id="user_001")

        assert connection_id is not None
        assert connection_id in manager.connections
        assert manager.connections[connection_id] == mock_websocket
        assert manager.connection_info[connection_id]["user_id"] == "user_001"
        assert manager.total_connections == 1

        # 验证发送了连接确认消息
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_without_user_id(self, mock_websocket):
        """测试不带用户 ID 的连接"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        assert connection_id is not None
        assert manager.connection_info[connection_id]["user_id"] is None

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_websocket):
        """测试断开连接"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket, user_id="user_001")

        await manager.disconnect(connection_id)

        assert connection_id not in manager.connections
        assert connection_id not in manager.connection_info

    @pytest.mark.asyncio
    async def test_disconnect_cleans_subscriptions(self, mock_websocket):
        """测试断开连接时清理订阅"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        # 订阅频道
        await manager.subscribe(connection_id, ["alerts", "metrics"])

        # 断开连接
        await manager.disconnect(connection_id)

        # 验证订阅已清理
        assert connection_id not in manager.channel_subscribers.get("alerts", set())
        assert connection_id not in manager.channel_subscribers.get("metrics", set())

    @pytest.mark.asyncio
    async def test_disconnect_cleans_room_membership(self, mock_websocket):
        """测试断开连接时清理房间成员"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        # 创建房间并加入
        await manager.create_room("room_001", "test_channel")
        await manager.join_room("room_001", connection_id)

        # 断开连接
        await manager.disconnect(connection_id)

        # 验证已从房间移除
        room = manager.get_room_info("room_001")
        assert connection_id not in room.members


class TestWebSocketSubscription:
    """测试 WebSocket 频道订阅"""

    @pytest.mark.asyncio
    async def test_subscribe(self, mock_websocket):
        """测试订阅频道"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        result = await manager.subscribe(connection_id, ["alerts", "metrics"])

        assert result is True
        assert "alerts" in manager.channel_subscribers
        assert "metrics" in manager.channel_subscribers
        assert connection_id in manager.channel_subscribers["alerts"]
        assert connection_id in manager.channel_subscribers["metrics"]

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_connection(self, mock_websocket):
        """测试订阅不存在的连接"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        result = await manager.subscribe("nonexistent", ["alerts"])

        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe(self, mock_websocket):
        """测试取消订阅"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        await manager.subscribe(connection_id, ["alerts", "metrics"])
        result = await manager.unsubscribe(connection_id, ["alerts"])

        assert result is True
        assert connection_id not in manager.channel_subscribers.get("alerts", set())
        assert connection_id in manager.channel_subscribers["metrics"]

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_connection(self):
        """测试取消订阅不存在的连接"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        result = await manager.unsubscribe("nonexistent", ["alerts"])

        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe_duplicate_channels(self, mock_websocket):
        """测试重复订阅"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        await manager.subscribe(connection_id, ["alerts"])
        await manager.subscribe(connection_id, ["alerts"])  # 重复订阅

        # 应该不会出错，且订阅列表中只有一个
        subscribers = manager.channel_subscribers["alerts"]
        assert list(subscribers).count(connection_id) == 1


class TestWebSocketBroadcast:
    """测试 WebSocket 消息广播"""

    @pytest.mark.asyncio
    async def test_broadcast_to_channel(self, mock_websocket):
        """测试向频道广播消息"""
        from app.services.websocket_manager import WebSocketManager, WSMessage, WSMessageType

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(connection_id, ["alerts"])

        message = WSMessage(
            type=WSMessageType.ALERT,
            data={"message": "Test alert"}
        )

        await manager.broadcast_to_channel("alerts", message)

        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_to_channel_no_subscribers(self, mock_websocket):
        """测试向无订阅者的频道广播"""
        from app.services.websocket_manager import WebSocketManager, WSMessage, WSMessageType

        manager = WebSocketManager()

        message = WSMessage(
            type=WSMessageType.ALERT,
            data={"message": "Test alert"}
        )

        # 不应抛出异常
        await manager.broadcast_to_channel("empty_channel", message)

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_subscribers(self):
        """测试向多个订阅者广播"""
        from app.services.websocket_manager import WebSocketManager, WSMessage, WSMessageType

        manager = WebSocketManager()

        # 创建多个连接
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        conn1 = await manager.connect(ws1, user_id="user_001")
        conn2 = await manager.connect(ws2, user_id="user_002")

        await manager.subscribe(conn1, ["alerts"])
        await manager.subscribe(conn2, ["alerts"])

        # 重置 mock 以忽略 connect/subscribe 时的 send_json 调用
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        message = WSMessage(
            type=WSMessageType.ALERT,
            data={"message": "Broadcast test"}
        )

        await manager.broadcast_to_channel("alerts", message)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_user(self):
        """测试向特定用户发送消息"""
        from app.services.websocket_manager import WebSocketManager, WSMessage, WSMessageType

        manager = WebSocketManager()

        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, user_id="user_001")
        await manager.connect(ws2, user_id="user_002")

        # 重置 mock 以忽略 connect 时的 send_json 调用
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        message = WSMessage(
            type=WSMessageType.NOTIFICATION,
            data={"message": "User specific message"}
        )

        await manager.send_to_user("user_001", message)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_all(self):
        """测试向所有连接广播"""
        from app.services.websocket_manager import WebSocketManager, WSMessage, WSMessageType

        manager = WebSocketManager()

        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, user_id="user_001")
        await manager.connect(ws2, user_id="user_002")

        # 重置 mock 以忽略 connect 时的 send_json 调用
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()

        message = WSMessage(
            type=WSMessageType.NOTIFICATION,
            data={"message": "Broadcast to all"}
        )

        await manager.broadcast_all(message)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()


class TestWebSocketHeartbeat:
    """测试 WebSocket 心跳"""

    @pytest.mark.asyncio
    async def test_handle_heartbeat(self, mock_websocket):
        """测试处理心跳"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        # 记录原始心跳时间
        original_heartbeat = manager.connection_info[connection_id]["last_heartbeat"]

        # 等待一小段时间
        await asyncio.sleep(0.1)

        # 处理心跳
        await manager.handle_heartbeat(connection_id)

        # 验证心跳时间已更新
        new_heartbeat = manager.connection_info[connection_id]["last_heartbeat"]
        assert new_heartbeat > original_heartbeat

    @pytest.mark.asyncio
    async def test_handle_heartbeat_nonexistent_connection(self):
        """测试处理不存在连接的心跳"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        # 不应抛出异常
        await manager.handle_heartbeat("nonexistent")

    @pytest.mark.asyncio
    async def test_check_stale_connections(self, mock_websocket):
        """测试检查超时连接"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        # 模拟超时
        manager.connection_info[connection_id]["last_heartbeat"] = (
            datetime.now(timezone.utc) - timedelta(seconds=120)
        )

        await manager.check_stale_connections(timeout_seconds=60)

        # 连接应该被清理
        assert connection_id not in manager.connections


class TestWebSocketRooms:
    """测试 WebSocket 房间管理"""

    @pytest.mark.asyncio
    async def test_create_room(self):
        """测试创建房间"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        room = await manager.create_room("room_001", "test_channel", {"name": "Test Room"})

        assert room is not None
        assert room.room_id == "room_001"
        assert room.channel == "test_channel"
        assert room.metadata == {"name": "Test Room"}

    @pytest.mark.asyncio
    async def test_join_room(self, mock_websocket):
        """测试加入房间"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        await manager.create_room("room_001", "test_channel")
        result = await manager.join_room("room_001", connection_id)

        assert result is True
        room = manager.get_room_info("room_001")
        assert connection_id in room.members

    @pytest.mark.asyncio
    async def test_join_nonexistent_room(self, mock_websocket):
        """测试加入不存在的房间"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        result = await manager.join_room("nonexistent", connection_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_leave_room(self, mock_websocket):
        """测试离开房间"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        await manager.create_room("room_001", "test_channel")
        await manager.join_room("room_001", connection_id)

        result = await manager.leave_room("room_001", connection_id)

        assert result is True
        room = manager.get_room_info("room_001")
        assert connection_id not in room.members

    @pytest.mark.asyncio
    async def test_leave_nonexistent_room(self, mock_websocket):
        """测试离开不存在的房间"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)

        result = await manager.leave_room("nonexistent", connection_id)

        assert result is False


class TestWebSocketStats:
    """测试 WebSocket 统计"""

    @pytest.mark.asyncio
    async def test_get_connection_info(self, mock_websocket):
        """测试获取连接信息"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket, user_id="user_001")

        info = manager.get_connection_info(connection_id)

        assert info is not None
        assert info.connection_id == connection_id
        assert info.user_id == "user_001"

    @pytest.mark.asyncio
    async def test_get_connection_info_nonexistent(self):
        """测试获取不存在连接的信息"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()

        info = manager.get_connection_info("nonexistent")

        assert info is None

    @pytest.mark.asyncio
    async def test_get_connection_stats(self, mock_websocket):
        """测试获取连接统计"""
        from app.services.websocket_manager import WebSocketManager

        manager = WebSocketManager()
        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(connection_id, ["alerts", "metrics"])

        stats = manager.get_connection_stats()

        assert stats.total_connections == 1
        assert stats.active_connections == 1
        assert stats.channels["alerts"] == 1
        assert stats.channels["metrics"] == 1
        assert stats.uptime_seconds >= 0


class TestConvenienceFunctions:
    """测试便捷函数"""

    @pytest.mark.asyncio
    async def test_notify_alert(self, mock_websocket):
        """测试发送告警通知"""
        from app.services.websocket_manager import get_ws_manager, notify_alert

        manager = get_ws_manager()
        # 重置管理器
        manager.connections.clear()
        manager.connection_info.clear()
        manager.channel_subscribers.clear()

        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(connection_id, ["alerts"])

        await notify_alert({"level": "warning", "message": "Test alert"})

        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_notify_metric_update(self, mock_websocket):
        """测试发送指标更新"""
        from app.services.websocket_manager import get_ws_manager, notify_metric_update

        manager = get_ws_manager()
        manager.connections.clear()
        manager.connection_info.clear()
        manager.channel_subscribers.clear()

        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(connection_id, ["metrics"])

        await notify_metric_update({"cpu": 75, "memory": 60})

        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_notify_audit_event(self, mock_websocket):
        """测试发送审计事件"""
        from app.services.websocket_manager import get_ws_manager, notify_audit_event

        manager = get_ws_manager()
        manager.connections.clear()
        manager.connection_info.clear()
        manager.channel_subscribers.clear()

        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(connection_id, ["audit"])

        await notify_audit_event({"action": "login", "user": "test"})

        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_notify_task_update(self, mock_websocket):
        """测试发送任务更新"""
        from app.services.websocket_manager import get_ws_manager, notify_task_update

        manager = get_ws_manager()
        manager.connections.clear()
        manager.connection_info.clear()
        manager.channel_subscribers.clear()

        connection_id = await manager.connect(mock_websocket)
        await manager.subscribe(connection_id, ["tasks"])

        await notify_task_update({"task_id": "001", "status": "completed"})

        mock_websocket.send_json.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
