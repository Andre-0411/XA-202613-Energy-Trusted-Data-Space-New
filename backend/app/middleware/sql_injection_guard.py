"""
SQL 注入防护中间件

功能:
- 请求参数扫描中间件
- 检测常见 SQL 注入模式（UNION SELECT、OR 1=1、DROP TABLE 等）
- 自动拦截并返回 403
- 记录攻击日志
"""
import re
import logging
import json
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote

from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)


# SQL 注入检测模式列表
# 每个模式包含 (正则表达式, 描述)
SQL_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # UNION SELECT 攻击
    (
        re.compile(r"\bunion\b\s+(all\s+)?select\b", re.IGNORECASE),
        "UNION SELECT 注入",
    ),
    # OR/AND 永真/永假条件
    (
        re.compile(r"\b(or|and)\b\s+[\d'\"]+\s*=\s*[\d'\"]+", re.IGNORECASE),
        "OR/AND 永真条件注入",
    ),
    (
        re.compile(r"\b(or|and)\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?", re.IGNORECASE),
        "OR/AND 条件注入",
    ),
    # OR 1=1 / AND 1=1
    (
        re.compile(r"\bor\b\s+1\s*=\s*1\b", re.IGNORECASE),
        "OR 1=1 永真注入",
    ),
    (
        re.compile(r"\band\b\s+1\s*=\s*1\b", re.IGNORECASE),
        "AND 1=1 条件注入",
    ),
    # DROP TABLE/DATABASE
    (
        re.compile(r"\bdrop\s+(table|database|schema)\b", re.IGNORECASE),
        "DROP 语句注入",
    ),
    # DELETE FROM
    (
        re.compile(r"\bdelete\s+from\b", re.IGNORECASE),
        "DELETE 语句注入",
    ),
    # INSERT INTO
    (
        re.compile(r"\binsert\s+into\b", re.IGNORECASE),
        "INSERT 语句注入",
    ),
    # UPDATE SET
    (
        re.compile(r"\bupdate\b\s+\w+\s+set\b", re.IGNORECASE),
        "UPDATE 语句注入",
    ),
    # SELECT * FROM
    (
        re.compile(r"\bselect\b\s+(\*|\w+)\s+from\b", re.IGNORECASE),
        "SELECT 语句注入",
    ),
    # 注释符号注入
    (
        re.compile(r"(--|#|/\*)", re.IGNORECASE),
        "SQL 注释注入",
    ),
    # 分号多语句
    (
        re.compile(r";\s*(select|insert|update|delete|drop|alter|create|exec)\b", re.IGNORECASE),
        "多语句注入",
    ),
    # EXEC/EXECUTE
    (
        re.compile(r"\b(exec|execute)\b\s*\(?", re.IGNORECASE),
        "EXEC 执行注入",
    ),
    # 信息函数注入
    (
        re.compile(r"\b(version|database|user|schema_name|table_name|column_name)\s*\(\s*\)", re.IGNORECASE),
        "信息函数注入",
    ),
    # WAITFOR DELAY (时间盲注)
    (
        re.compile(r"\bwaitfor\b\s+delay\b", re.IGNORECASE),
        "时间盲注 WAITFOR DELAY",
    ),
    # SLEEP() (时间盲注)
    (
        re.compile(r"\bsleep\s*\(\s*\d+\s*\)", re.IGNORECASE),
        "时间盲注 SLEEP()",
    ),
    # BENCHMARK() (时间盲注)
    (
        re.compile(r"\bbenchmark\s*\(", re.IGNORECASE),
        "时间盲注 BENCHMARK()",
    ),
    # LOAD_FILE/INTO OUTFILE (文件操作注入)
    (
        re.compile(r"\b(load_file|into\s+(outfile|dumpfile))\b", re.IGNORECASE),
        "文件操作注入",
    ),
    # CHAR() 函数绕过
    (
        re.compile(r"\bchar\s*\(\s*\d+", re.IGNORECASE),
        "CHAR 编码绕过注入",
    ),
    # HAVING 错误注入
    (
        re.compile(r"\bhaving\b\s+\d+\s*=\s*\d+", re.IGNORECASE),
        "HAVING 错误注入",
    ),
    # 空白字符绕过 (使用/**/代替空格)
    (
        re.compile(r"/\*\*/", re.IGNORECASE),
        "注释绕过注入",
    ),
    # 十六进制编码绕过
    (
        re.compile(r"0x[0-9a-fA-F]{8,}", re.IGNORECASE),
        "十六进制编码注入",
    ),
    # 堆叠查询
    (
        re.compile(r";\s*shutdown\b", re.IGNORECASE),
        "堆叠查询攻击",
    ),
    # TRUNCATE TABLE
    (
        re.compile(r"\btruncate\s+(table)\b", re.IGNORECASE),
        "TRUNCATE 语句注入",
    ),
    # ALTER TABLE
    (
        re.compile(r"\balter\s+table\b", re.IGNORECASE),
        "ALTER TABLE 注入",
    ),
    # CREATE TABLE
    (
        re.compile(r"\bcreate\s+table\b", re.IGNORECASE),
        "CREATE TABLE 注入",
    ),
    # GRANT/REVOKE
    (
        re.compile(r"\b(grant|revoke)\b", re.IGNORECASE),
        "权限操作注入",
    ),
]


# 跳过检查的路径
SKIP_PATHS: set[str] = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
}

# 跳过检查的方法
SKIP_METHODS: set[str] = {"OPTIONS", "HEAD"}


class SQLInjectionGuardMiddleware:
    """
    SQL 注入防护中间件

    扫描所有请求参数（query params、path params、body），
    检测并拦截 SQL 注入攻击。
    """

    async def __call__(self, request: Request, call_next) -> Response:
        """中间件主流程"""

        # 跳过不需要检查的路径和方法
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        if request.method in SKIP_METHODS:
            return await call_next(request)

        # 获取客户端信息（用于日志）
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # 1. 检查查询参数
        for param_name, param_value in request.query_params.items():
            attack_type = _detect_sql_injection(param_value)
            if attack_type:
                _log_attack(
                    request_url=str(request.url),
                    client_ip=client_ip,
                    user_agent=user_agent,
                    param_name=f"query:{param_name}",
                    param_value=param_value,
                    attack_type=attack_type,
                    method=request.method,
                )
                return _blocked_response(attack_type)

        # 2. 检查路径参数（解码 URL 路径）
        decoded_path = unquote(str(request.url.path))
        attack_type = _detect_sql_injection(decoded_path)
        if attack_type:
            _log_attack(
                request_url=str(request.url),
                client_ip=client_ip,
                user_agent=user_agent,
                param_name="path",
                param_value=decoded_path,
                attack_type=attack_type,
                method=request.method,
            )
            return _blocked_response(attack_type)

        # 3. 检查请求体（仅对有 body 的方法）
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                body = await request.body()
                if body:
                    content_type = request.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        try:
                            body_json = json.loads(body)
                            attack_type = _check_json_body(body_json)
                            if attack_type:
                                _log_attack(
                                    request_url=str(request.url),
                                    client_ip=client_ip,
                                    user_agent=user_agent,
                                    param_name="body",
                                    param_value=str(body_json)[:500],
                                    attack_type=attack_type,
                                    method=request.method,
                                )
                                return _blocked_response(attack_type)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass
                    elif "application/x-www-form-urlencoded" in content_type:
                        form_text = body.decode("utf-8", errors="ignore")
                        attack_type = _detect_sql_injection(form_text)
                        if attack_type:
                            _log_attack(
                                request_url=str(request.url),
                                client_ip=client_ip,
                                user_agent=user_agent,
                                param_name="body:form",
                                param_value=form_text[:500],
                                attack_type=attack_type,
                                method=request.method,
                            )
                            return _blocked_response(attack_type)
            except (RuntimeError, IOError, UnicodeDecodeError):
                # 读取 body 失败不阻断请求
                pass

        # 4. 检查特殊请求头
        referer = request.headers.get("Referer", "")
        if referer:
            decoded_referer = unquote(referer)
            attack_type = _detect_sql_injection(decoded_referer)
            if attack_type:
                _log_attack(
                    request_url=str(request.url),
                    client_ip=client_ip,
                    user_agent=user_agent,
                    param_name="header:Referer",
                    param_value=decoded_referer[:500],
                    attack_type=attack_type,
                    method=request.method,
                )
                return _blocked_response(attack_type)

        # 通过检查，继续处理请求
        return await call_next(request)


def _detect_sql_injection(value: str) -> Optional[str]:
    """
    检测单个字符串值是否包含 SQL 注入模式

    Args:
        value: 待检测的字符串

    Returns:
        检测到的攻击类型描述，如果安全则返回 None
    """
    if not value or not isinstance(value, str):
        return None

    # 对输入进行 URL 解码（处理双重编码）
    decoded_value = unquote(value)

    # 检查所有模式
    for pattern, description in SQL_INJECTION_PATTERNS:
        if pattern.search(decoded_value):
            return description

    return None


def _check_json_body(body_json: dict | list) -> Optional[str]:
    """
    递归检查 JSON 请求体

    Args:
        body_json: JSON 请求体（dict 或 list）

    Returns:
        检测到的攻击类型描述，如果安全则返回 None
    """
    if isinstance(body_json, dict):
        for key, value in body_json.items():
            # 检查键名
            attack_type = _detect_sql_injection(str(key))
            if attack_type:
                return attack_type
            # 递归检查值
            attack_type = _check_value(value)
            if attack_type:
                return attack_type

    elif isinstance(body_json, list):
        for item in body_json:
            attack_type = _check_value(item)
            if attack_type:
                return attack_type

    return None


def _check_value(value) -> Optional[str]:
    """
    检查单个值

    Args:
        value: 待检查的值

    Returns:
        检测到的攻击类型描述，如果安全则返回 None
    """
    if isinstance(value, str):
        return _detect_sql_injection(value)
    elif isinstance(value, dict):
        return _check_json_body(value)
    elif isinstance(value, list):
        for item in value:
            attack_type = _check_value(item)
            if attack_type:
                return attack_type
    return None


def _log_attack(
    request_url: str,
    client_ip: str,
    user_agent: str,
    param_name: str,
    param_value: str,
    attack_type: str,
    method: str,
) -> None:
    """
    记录 SQL 注入攻击日志

    Args:
        request_url: 请求 URL
        client_ip: 客户端 IP
        user_agent: User-Agent
        param_name: 注入参数名
        param_value: 注入参数值
        attack_type: 攻击类型
        method: HTTP 方法
    """
    attack_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "sql_injection_detected",
        "attack_type": attack_type,
        "method": method,
        "url": request_url,
        "client_ip": client_ip,
        "user_agent": user_agent[:200] if user_agent else "",
        "injected_param": param_name,
        "injected_value": param_value[:500],
    }
    logger.warning(f"SQL注入攻击拦截: {json.dumps(attack_log, ensure_ascii=False)}")


def _blocked_response(attack_type: str) -> JSONResponse:
    """
    返回拦截响应（403 Forbidden）

    Args:
        attack_type: 攻击类型描述

    Returns:
        403 JSON 响应
    """
    return JSONResponse(
        status_code=403,
        content={
            "code": 6061,
            "message": f"请求被安全策略拦截: 检测到潜在的 {attack_type} 攻击",
            "data": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
