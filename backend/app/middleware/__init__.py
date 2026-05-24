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
            from app.database import get_redis
            redis = await get_redis()
            if not redis:
                return False
            key = f"ratelimit:{client_ip}"
            pipe = redis.pipeline()
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


class XSSFilterMiddleware:
    """
    XSS 内容过滤中间件

    检测请求体中的 XSS 攻击模式：
    - <script> 标签注入
    - 事件处理器注入 (onclick, onerror 等)
    - javascript: 协议注入
    - HTML 标签注入（img, iframe, object 等）
    - data: URI 注入
    """

    import re as _re

    XSS_PATTERNS = [
        _re.compile(r"<\s*script[^>]*>", _re.IGNORECASE),
        _re.compile(r"<\s*/\s*script\s*>", _re.IGNORECASE),
        _re.compile(r"\bon\w+\s*=", _re.IGNORECASE),
        _re.compile(r"javascript\s*:", _re.IGNORECASE),
        _re.compile(r"vbscript\s*:", _re.IGNORECASE),
        _re.compile(r"data\s*:\s*text/html", _re.IGNORECASE),
        _re.compile(r"<\s*img[^>]+onerror\s*=", _re.IGNORECASE),
        _re.compile(r"<\s*iframe[^>]*>", _re.IGNORECASE),
        _re.compile(r"<\s*(object|embed)[^>]*>", _re.IGNORECASE),
        _re.compile(r"\beval\s*\(", _re.IGNORECASE),
        _re.compile(r"expression\s*\(", _re.IGNORECASE),
        _re.compile(r"<\s*svg[^>]+onload\s*=", _re.IGNORECASE),
    ]

    SKIP_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json", "/"})

    async def __call__(self, request: Request, call_next) -> Response:
        from starlette.responses import JSONResponse

        path = request.url.path
        if path in self.SKIP_PATHS:
            return await call_next(request)

        # 只检查 POST/PUT/PATCH 请求
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # 检查查询参数
        query_string = str(request.query_params)
        if self._contains_xss(query_string):
            logger.warning(f"XSS detected in query: {query_string[:200]}")
            return self._blocked_response()

        # 检查请求体
        try:
            body = await request.body()
            if body:
                body_text = body.decode("utf-8", errors="ignore")
                if self._contains_xss(body_text):
                    logger.warning(f"XSS detected in body: {body_text[:200]}")
                    return self._blocked_response()
        except Exception:
            pass

        return await call_next(request)

    def _contains_xss(self, text: str) -> bool:
        for pattern in self.XSS_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def _blocked_response() -> "JSONResponse":
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={
                "code": 6060,
                "message": "检测到潜在的 XSS 攻击，请求已被阻止",
                "data": None,
            },
        )


__all__ = [
    "SQLInjectionGuardMiddleware",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "AuditLogMiddleware",
    "CSRFMiddleware",
    "XSSFilterMiddleware",
]
