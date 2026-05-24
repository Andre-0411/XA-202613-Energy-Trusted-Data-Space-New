"""
中间件包
"""
import logging
from starlette.requests import Request
from starlette.responses import Response
from app.middleware.sql_injection_guard import SQLInjectionGuardMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """安全响应头中间件"""

    async def __call__(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # docs/redoc 需要加载外部 CDN 资源, 放宽 CSP
        path = request.url.path
        if path in ("/docs", "/redoc", "/docs/oauth2-redirect"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self' https://cdn.jsdelivr.net"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RateLimitMiddleware:
    """速率限制中间件（Redis 持久化实现 + 内存回退）"""
    _requests: dict[str, list[float]] = {}
    _max_requests: int = 100
    _window_seconds: float = 60.0
    _redis_available: bool = False

    async def _try_redis_check(self, client_ip: str, now: float) -> bool:
        """通过 Redis 检查限流"""
        try:
            from app.database import redis_client
            if not redis_client or not hasattr(redis_client, 'zadd'):
                return False
            key = f"ratelimit:{client_ip}"
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, now - self._window_seconds)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, int(self._window_seconds) + 10)
            _, count, *_ = await pipe.execute()
            return int(count or 0) >= self._max_requests
        except Exception:
            return False

    async def __call__(self, request: Request, call_next) -> Response:
        import time
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # 尝试 Redis
        if self._redis_available:
            try:
                if await self._try_redis_check(client_ip, now):
                    from starlette.responses import JSONResponse
                    return JSONResponse(status_code=429, content={"code": 429, "message": "请求过于频繁，请稍后再试", "data": None})
                return await call_next(request)
            except Exception:
                self._redis_available = False

        # 内存回退
        if client_ip in self._requests:
            self._requests[client_ip] = [t for t in self._requests[client_ip] if now - t < self._window_seconds]
        else:
            self._requests[client_ip] = []

        if len(self._requests[client_ip]) >= self._max_requests:
            from starlette.responses import JSONResponse
            return JSONResponse(status_code=429, content={"code": 429, "message": "请求过于频繁，请稍后再试", "data": None})

        self._requests[client_ip].append(now)
        return await call_next(request)


class AuditLogMiddleware:
    """审计日志中间件"""

    async def __call__(self, request: Request, call_next) -> Response:
        import time
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        # 仅记录 API 请求
        if request.url.path.startswith("/api/"):
            logger.info(
                f"[AUDIT] {request.method} {request.url.path} "
                f"-> {response.status_code} ({duration:.3f}s) "
                f"client={request.client.host if request.client else 'unknown'}"
            )
        return response


class CSRFMiddleware:
    """CSRF 防护中间件（API 使用 JWT 认证，仅前端页面做 CSRF 检查）"""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    # API 路径前缀（使用 JWT 认证，无需 CSRF）
    SKIP_API = ("/api/", "/health", "/docs", "/redoc", "/openapi.json", "/ws/", "/metrics")

    async def __call__(self, request: Request, call_next) -> Response:
        from starlette.responses import JSONResponse

        # 安全方法不需要 CSRF 检查
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # API 路径使用 JWT 认证，跳过 CSRF
        if any(request.url.path.startswith(p) for p in self.SKIP_API):
            return await call_next(request)

        # 非 API 路径检查 Referer/Origin
        origin = request.headers.get("origin", "")
        host = request.headers.get("host", "")

        if origin and host and host not in origin:
            return JSONResponse(
                status_code=403,
                content={"code": 403, "message": "CSRF 校验失败", "data": None},
            )

        return await call_next(request)


__all__ = [
    "SQLInjectionGuardMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "AuditLogMiddleware",
    "CSRFMiddleware",
]
