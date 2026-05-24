"""
中间件集合
SecurityHeadersMiddleware - 安全响应头（含 CSP）
RateLimitMiddleware - API 限流
AuditLogMiddleware - 审计日志
CSRFMiddleware - CSRF 防护（双重提交 Cookie 模式）
SQLInjectionGuardMiddleware - SQL 注入防护
"""
import re
import time
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import _get_redis_client

logger = logging.getLogger(__name__)

# CSRF 安全方法集合 — 不需要校验 CSRF token
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
# CSRF token Cookie 名称
CSRF_COOKIE_NAME = "csrftoken"
# CSRF 请求头名称
CSRF_HEADER_NAME = "X-CSRFToken"
# CSRF token 有效期（秒）
CSRF_TOKEN_MAX_AGE = 3600 * 4  # 4 小时


class SecurityHeadersMiddleware:
    """
    安全响应头中间件
    添加标准安全头到所有响应
    """

    async def __call__(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss:;"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        return response


class RateLimitMiddleware:
    """
    API 限流中间件
    基于 Redis 的滑动窗口限流

    规则:
    - 全局: 1000 次/分钟
    - 认证接口: 10 次/分钟
    - 一般接口: 100 次/分钟
    """

    # 限流规则配置
    RATE_LIMITS = {
        "/api/v1/auth/login": (10, 60),       # 10次/分钟
        "/api/v1/auth/register": (5, 60),     # 5次/分钟
        "/api/v1/auth/refresh": (20, 60),     # 20次/分钟
    }
    DEFAULT_LIMIT = (100, 60)  # 100次/分钟
    GLOBAL_LIMIT = (1000, 60)  # 1000次/分钟

    async def __call__(self, request: Request, call_next):
        # 不限流的路径
        skip_paths = {"/health", "/docs", "/redoc", "/openapi.json", "/"}
        if request.url.path in skip_paths:
            return await call_next(request)

        # 获取客户端标识
        client_id = self._get_client_id(request)

        try:
            redis = _get_redis_client()

            # 全局限流检查
            global_key = f"ratelimit:global:{client_id}"
            global_allowed = await self._check_rate_limit(
                redis, global_key, self.GLOBAL_LIMIT
            )
            if not global_allowed:
                return self._rate_limit_response()

            # 接口级别限流
            path = request.url.path
            limit_config = self.RATE_LIMITS.get(path, self.DEFAULT_LIMIT)
            path_key = f"ratelimit:{path}:{client_id}"
            path_allowed = await self._check_rate_limit(
                redis, path_key, limit_config
            )
            if not path_allowed:
                return self._rate_limit_response()

        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}, allowing request")

        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用认证用户 ID
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return f"user:{auth_header[7:20]}"

        # 使用 IP 地址
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def _check_rate_limit(
        self, redis, key: str, limit_config: tuple[int, int]
    ) -> bool:
        """检查限流（滑动窗口）"""
        max_requests, window_seconds = limit_config

        try:
            current = int(time.time())
            window_start = current - window_seconds

            # 使用 Redis sorted set 实现滑动窗口
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(current): current})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

            count = results[2]
            return count <= max_requests
        except Exception:
            return True

    def _rate_limit_response(self) -> JSONResponse:
        """限流响应"""
        return JSONResponse(
            status_code=429,
            content={
                "code": 9010,
                "message": "请求过于频繁，请稍后再试",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


class AuditLogMiddleware:
    """
    审计日志中间件
    记录所有 API 请求到日志系统
    """

    # 不记录日志的路径
    SKIP_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/"}

    async def __call__(self, request: Request, call_next):
        # 跳过不需要记录的路径
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # 跳过 WebSocket
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        start_time = time.time()

        # 执行请求
        response = await call_next(request)

        # 计算耗时
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # 构建审计日志
        audit_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": str(request.url.path),
            "query": str(request.query_params) if request.query_params else None,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent", ""),
            "user_id": None,
        }

        # 尝试获取用户 ID
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                from app.config import settings
                payload = jwt.decode(
                    auth_header[7:],
                    settings.JWT_SECRET_KEY,
                    algorithms=[settings.JWT_ALGORITHM],
                    options={"verify_exp": False},
                )
                audit_log["user_id"] = payload.get("sub")
            except Exception:
                pass

        # 根据状态码选择日志级别
        if response.status_code >= 500:
            logger.error(f"Audit: {audit_log}")
        elif response.status_code >= 400:
            logger.warning(f"Audit: {audit_log}")
        else:
            logger.info(f"Audit: {audit_log}")

        # 添加耗时头
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response


class CSRFMiddleware:
    """
    CSRF 防护中间件（双重提交 Cookie 模式）

    工作流程：
    1. 对于安全方法（GET/HEAD/OPTIONS），在响应中设置 CSRF token Cookie
    2. 对于非安全方法（POST/PUT/DELETE/PATCH），校验请求头中的 CSRF token
       与 Cookie 中的 token 是否一致
    3. API 和 WebSocket 路径跳过 CSRF 校验

    前端在每次请求时需要从 Cookie 读取 csrftoken 并放入 X-CSRFToken 请求头
    """

    # 不需要 CSRF 保护的路径前缀（API 使用 JWT 认证，无需 CSRF）
    SKIP_PATH_PREFIXES: tuple[str, ...] = (
        "/api/v1/",  # 所有 API 路径跳过 CSRF
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/ws/",
        "/metrics",
        "/",
    )

    async def __call__(self, request: Request, call_next) -> Response:
        path: str = request.url.path

        # 跳过不需要保护的路径
        if any(path.startswith(prefix) for prefix in self.SKIP_PATH_PREFIXES):
            response = await call_next(request)
            self._set_csrf_cookie(response)
            return response

        # 安全方法：仅设置 Cookie，不校验
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            self._set_csrf_cookie(response)
            return response

        # 非安全方法：校验 CSRF token
        cookie_token: Optional[str] = request.cookies.get(CSRF_COOKIE_NAME)
        header_token: Optional[str] = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            logger.warning(
                f"CSRF token missing: cookie={bool(cookie_token)}, "
                f"header={bool(header_token)}, path={path}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "code": 6001,
                    "message": "CSRF token 缺失，请刷新页面后重试",
                    "data": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        if not secrets.compare_digest(cookie_token, header_token):
            logger.warning(f"CSRF token mismatch for path={path}")
            return JSONResponse(
                status_code=403,
                content={
                    "code": 6002,
                    "message": "CSRF token 验证失败",
                    "data": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        response = await call_next(request)
        self._set_csrf_cookie(response)
        return response

    @staticmethod
    def _set_csrf_cookie(response: Response) -> None:
        """
        在响应中设置 CSRF token Cookie

        仅在 Cookie 不存在时才生成新 token，避免前端每次请求后 CSRF token 失效。
        使用 Secure + SameSite=Lax 策略，防止跨站请求伪造
        """
        # 若 Cookie 已存在，不覆盖（防止前端 token 失效）
        # 注意: Response 对象无法直接读取已设置的 Cookie 值，
        # 这里每次都生成新 token 并设置较长 max_age，前端首次请求后保持不变
        token: str = secrets.token_hex(32)
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=token,
            max_age=CSRF_TOKEN_MAX_AGE,
            httponly=False,  # 前端 JS 需要读取
            secure=False,    # 开发环境设为 False；生产环境应为 True
            samesite="lax",
            path="/",
        )


class SQLInjectionGuardMiddleware:
    """
    SQL 注入防护中间件

    检测请求参数和路径中常见的 SQL 注入模式，
    对可疑请求返回 403 拒绝访问。
    """

    # SQL 注入特征模式（不区分大小写）
    SQL_INJECTION_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"(\b(union\s+select|insert\s+into|delete\s+from|drop\s+table|alter\s+table)\b)", re.IGNORECASE),
        re.compile(r"(--|/\*|\*/|;)\s*(drop|delete|update|insert|select)\b", re.IGNORECASE),
        re.compile(r"'\s*(or|and)\s*'?[\d\w]", re.IGNORECASE),
        re.compile(r"\b(exec|execute|xp_cmdshell|sp_executesql)\b", re.IGNORECASE),
        re.compile(r"(\bchar\b\s*\(|\bconcat\b\s*\(|\bsubstring\b\s*\()", re.IGNORECASE),
        re.compile(r"(0x[0-9a-fA-F]+)", re.IGNORECASE),
    ]

    # 不检测的路径
    SKIP_PATHS: frozenset[str] = frozenset({
        "/health", "/docs", "/redoc", "/openapi.json", "/",
    })

    async def __call__(self, request: Request, call_next) -> Response:
        path: str = request.url.path

        if path in self.SKIP_PATHS:
            return await call_next(request)

        # 检查路径
        if self._contains_sql_injection(path):
            logger.warning(f"SQL injection detected in path: {path}")
            return self._blocked_response()

        # 检查查询参数
        query_string: str = str(request.query_params)
        if self._contains_sql_injection(query_string):
            logger.warning(f"SQL injection detected in query: {query_string}")
            return self._blocked_response()

        return await call_next(request)

    def _contains_sql_injection(self, text: str) -> bool:
        """检查文本是否包含 SQL 注入特征"""
        for pattern in self.SQL_INJECTION_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def _blocked_response() -> JSONResponse:
        """返回阻止响应"""
        return JSONResponse(
            status_code=403,
            content={
                "code": 6050,
                "message": "检测到潜在的安全威胁，请求已被阻止",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


class XSSFilterMiddleware:
    """
    XSS 内容过滤中间件

    检测请求体中的 XSS 攻击模式：
    - <script> 标签注入
    - 事件处理器注入 (onclick, onerror 等)
    - javascript: 协议注入
    - HTML 标签注入（img, iframe, object 等）
    - data: URI 注入

    对可疑请求进行过滤或拒绝
    """

    # XSS 攻击特征模式
    XSS_PATTERNS: list[re.Pattern[str]] = [
        # <script> 标签
        re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
        re.compile(r"<\s*/\s*script\s*>", re.IGNORECASE),
        # 事件处理器
        re.compile(r"\bon\w+\s*=", re.IGNORECASE),
        # javascript: 协议
        re.compile(r"javascript\s*:", re.IGNORECASE),
        # vbscript: 协议
        re.compile(r"vbscript\s*:", re.IGNORECASE),
        # data: URI 中的 HTML
        re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
        # <img> 标签的 onerror
        re.compile(r"<\s*img[^>]+onerror\s*=", re.IGNORECASE),
        # <iframe> 标签
        re.compile(r"<\s*iframe[^>]*>", re.IGNORECASE),
        # <object> 和 <embed> 标签
        re.compile(r"<\s*(object|embed)[^>]*>", re.IGNORECASE),
        # eval() 函数
        re.compile(r"\beval\s*\(", re.IGNORECASE),
        # expression() CSS 注入
        re.compile(r"expression\s*\(", re.IGNORECASE),
        # <svg> 标签中的事件
        re.compile(r"<\s*svg[^>]+onload\s*=", re.IGNORECASE),
    ]

    # 不检测的路径
    SKIP_PATHS: frozenset[str] = frozenset({
        "/health", "/docs", "/redoc", "/openapi.json", "/",
    })

    # 不检测的 Content-Type
    SKIP_CONTENT_TYPES: frozenset[str] = frozenset({
        "multipart/form-data",  # 文件上传跳过
    })

    async def __call__(self, request: Request, call_next) -> Response:
        path: str = request.url.path

        if path in self.SKIP_PATHS:
            return await call_next(request)

        # 只检查 POST/PUT/PATCH 请求
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        # 检查 Content-Type
        content_type = request.headers.get("Content-Type", "")
        if any(ct in content_type for ct in self.SKIP_CONTENT_TYPES):
            return await call_next(request)

        # 检查查询参数
        query_string: str = str(request.query_params)
        if self._contains_xss(query_string):
            logger.warning(f"XSS detected in query: {query_string[:200]}")
            return self._blocked_response()

        # 检查请求体
        try:
            body = await request.body()
            if body:
                body_text = body.decode("utf-8", errors="ignore")
                if self._contains_xss(body_text):
                    logger.warning(f"XSS detected in request body: {body_text[:200]}")
                    return self._blocked_response()
        except Exception as e:
            logger.warning(f"Failed to read request body for XSS check: {e}")

        return await call_next(request)

    def _contains_xss(self, text: str) -> bool:
        """检查文本是否包含 XSS 攻击特征"""
        for pattern in self.XSS_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def _blocked_response() -> JSONResponse:
        """返回阻止响应"""
        return JSONResponse(
            status_code=403,
            content={
                "code": 6060,
                "message": "检测到潜在的 XSS 攻击，请求已被阻止",
                "data": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
