"""
WebSocket 实时通信端点
连接管理、频道订阅、消息推送
"""
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.websocket_manager import get_ws_manager, WSMessage, WSMessageType

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(default=None),
    token: Optional[str] = Query(default=None),
):
    """
    WebSocket 连接端点

    支持的客户端消息格式:
    {
        "type": "subscribe|unsubscribe|heartbeat",
        "channels": ["alerts", "metrics", ...],
        "data": {...}
    }
    """
    manager = get_ws_manager()
    connection_id = await manager.connect(websocket, user_id=user_id)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            if msg_type == "heartbeat":
                await manager.handle_heartbeat(connection_id)
            
            elif msg_type == "subscribe":
                channels = data.get("channels", [])
                await manager.subscribe(connection_id, channels)
            
            elif msg_type == "unsubscribe":
                channels = data.get("channels", [])
                await manager.unsubscribe(connection_id, channels)
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {msg_type}"},
                })
    
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
        logger.info(f"WebSocket client disconnected: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(connection_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    获取 WebSocket 连接统计

    Returns:
        连接统计信息，包含活跃连接数、频道订阅数、消息计数等
    """
    manager = get_ws_manager()
    stats = manager.get_all_stats()
    return stats


@router.get("/ws/connections")
async def list_connections():
    """
    列出所有活跃连接

    Returns:
        连接列表
    """
    manager = get_ws_manager()
    connections = []
    for conn_id in manager.connections:
        info = manager.get_connection_info(conn_id)
        if info:
            connections.append(info.model_dump())
    return {"connections": connections, "total": len(connections)}


@router.post("/ws/broadcast")
async def broadcast_message(channel: str, message: str):
    """
    向频道广播消息

    Args:
        channel: 频道
        message: 消息内容

    Returns:
        广播结果
    """
    manager = get_ws_manager()
    ws_message = WSMessage(
        type=WSMessageType.NOTIFICATION,
        data={"message": message},
    )
    await manager.broadcast_to_channel(channel, ws_message)
    return {"success": True, "channel": channel}


@router.get("/ws/rooms")
async def list_rooms():
    """
    列出所有房间

    Returns:
        房间列表
    """
    manager = get_ws_manager()
    rooms = []
    for room in manager.rooms.values():
        rooms.append(room.model_dump())
    return {"rooms": rooms, "total": len(rooms)}
