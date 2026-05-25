"""
FastAPI 应用入口

功能:
- CORS 中间件
- 安全头中间件
- 限流中间件
- /health 端点
- /api/v1 路由聚合
- lifespan 事件（启动时连接 MQTT/初始化）
- WebSocket 端点 /ws/notifications
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db, close_db
from app.middleware import SecurityHeadersMiddleware, RateLimitMiddleware, AuditLogMiddleware, CSRFMiddleware, SQLInjectionGuardMiddleware, XSSFilterMiddleware
from app.exceptions import AppException, app_exception_handler, unhandled_exception_handler


@asynccontextmanager
async def lifespan(application: FastAPI):
    """应用生命周期管理"""
    # ---- 启动 ----
    application.state.start_time = datetime.now(timezone.utc)

    # 初始化数据库连接
    await init_db()

    # 初始化 MQTT 连接
    try:
        from app.services.mqtt_client import mqtt_manager
        await mqtt_manager.connect()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"MQTT connection failed: {e}")

    import logging
    logger_main = logging.getLogger(__name__)

    # 初始化 AI Agent 工具注册表（自动扫描 API 路由生成工具）
    try:
        from app.services.tool_registry import initialize_tools
        initialize_tools(app=application)
        logger_main.info("AI Agent tool registry initialized")
    except Exception as e:
        logger_main.warning(f"Tool registry initialization failed: {e}")

    logger_main.info("Application started successfully")

    # 启动月度账单自动生成定时任务
    try:
        from app.services.billing_service import start_monthly_billing_scheduler
        await start_monthly_billing_scheduler()
        logger_main.info("Monthly billing scheduler started")
    except Exception as e:
        logger_main.warning(f"Failed to start monthly billing scheduler: {e}")

    # 启动日志保留清理定时任务
    try:
        from app.services.audit_enhanced import start_log_retention_scheduler
        await start_log_retention_scheduler()
        logger_main.info("Log retention scheduler started")
    except Exception as e:
        logger_main.warning(f"Failed to start log retention scheduler: {e}")

    yield

    # ---- 关闭 ----
    # 停止日志清理定时任务
    try:
        from app.services.audit_enhanced import stop_log_retention_scheduler
        await stop_log_retention_scheduler()
    except Exception:
        pass

    # 停止月度账单定时任务
    try:
        from app.services.billing_service import stop_monthly_billing_scheduler
        await stop_monthly_billing_scheduler()
    except Exception:
        pass

    try:
        from app.services.mqtt_client import mqtt_manager
        await mqtt_manager.disconnect()
    except Exception:
        pass

    await close_db()
    logging.getLogger(__name__).info("Application shutdown complete")


# 创建 FastAPI 实例
app = FastAPI(
    title=settings.APP_NAME,
    description="面向能源可信数据空间的'一门户五中心'系统 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    redirect_slashes=False,
)

# ==================== 中间件 ====================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全头
app.add_middleware(BaseHTTPMiddleware, dispatch=SecurityHeadersMiddleware())

# CSRF 防护（双重提交 Cookie 模式）
app.add_middleware(BaseHTTPMiddleware, dispatch=CSRFMiddleware())

# 限流
app.add_middleware(BaseHTTPMiddleware, dispatch=RateLimitMiddleware())

# 审计日志
app.add_middleware(BaseHTTPMiddleware, dispatch=AuditLogMiddleware())

# SQL 注入防护
app.add_middleware(BaseHTTPMiddleware, dispatch=SQLInjectionGuardMiddleware())

# XSS 内容过滤
app.add_middleware(BaseHTTPMiddleware, dispatch=XSSFilterMiddleware())

# ==================== 异常处理 ====================

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ==================== 路由聚合 ====================
from app.api.v1.router import router as v1_router
app.include_router(v1_router)


# ==================== 健康检查 ====================

@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点"""
    start_time = app.state.start_time
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds() if start_time else 0

    return {
        "code": 0,
        "message": "success",
        "data": {
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": round(uptime, 2),
            "environment": settings.APP_ENV,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["系统"])
async def root():
    """根路径 - API 信息"""
    return {
        "code": 0,
        "message": "success",
        "data": {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics", tags=["系统"], include_in_schema=False)
async def prometheus_metrics():
    """
    Prometheus 指标端点

    返回 prometheus_client 采集的所有指标（纯文本格式）。
    供 Prometheus 服务器抓取。
    """
    from fastapi.responses import PlainTextResponse
    from app.services.monitoring_service import get_prometheus_metrics

    metrics_text = await get_prometheus_metrics()
    return PlainTextResponse(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ==================== WebSocket 通知 ====================

from app.services.websocket_manager import get_ws_manager, WSMessage, WSMessageType, WSChannel


@app.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None),
):
    """
    WebSocket 通知端点

    支持的客户端消息格式:
    {
        "type": "subscribe|unsubscribe|heartbeat|ping",
        "channels": ["notifications", "alerts", "tasks", ...],
        "data": {...}
    }

    连接时通过query参数传递token进行认证:
    ws://host/ws/notifications?token=xxx
    """
    import logging
    logger = logging.getLogger(__name__)

    # 尝试从token解析用户ID
    user_id = None
    if token:
        try:
            from app.services.auth_service import AuthService
            auth_service = AuthService()
            payload = auth_service.verify_token(token)
            user_id = payload.get("sub") or payload.get("user_id")
        except Exception as e:
            logger.warning(f"WebSocket token verification failed: {e}")

    manager = get_ws_manager()
    connection_id = await manager.connect(websocket, user_id=user_id)

    # 自动订阅通知频道
    await manager.subscribe(connection_id, ["notifications"])

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "heartbeat" or msg_type == "ping":
                await manager.handle_heartbeat(connection_id)

            elif msg_type == "subscribe":
                channels = data.get("channels", [])
                await manager.subscribe(connection_id, channels)

            elif msg_type == "unsubscribe":
                channels = data.get("channels", [])
                await manager.unsubscribe(connection_id, channels)

            else:
                logger.warning(f"Unknown WebSocket message type: {msg_type}")
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
