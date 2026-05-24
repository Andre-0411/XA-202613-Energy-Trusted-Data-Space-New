"""
第三方审计只读接口服务
提供只读 API Token 生成、验证和审计数据访问功能
"""
import uuid
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# ==================== Token 存储 ====================

# 第三方审计 Token 存储: token_hash -> token_info
_audit_tokens: Dict[str, dict] = {}

# Token 访问日志
_token_access_logs: List[dict] = []

# Token 配置
TOKEN_DEFAULT_EXPIRY_DAYS = 90  # 默认 90 天过期
TOKEN_MAX_EXPIRY_DAYS = 365  # 最大 365 天
TOKEN_REFRESH_WINDOW_DAYS = 30  # 过期前 30 天可刷新


# ==================== Token 生成与验证 ====================

def _hash_token(token: str) -> str:
    """对 token 进行 SHA-256 哈希（存储时不保存明文）"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_audit_token(
    name: str,
    organization: str,
    contact_email: str,
    scope: List[str],
    expiry_days: int = TOKEN_DEFAULT_EXPIRY_DAYS,
    created_by: str = "",
    max_requests_per_day: int = 10000,
) -> dict:
    """
    生成第三方审计只读 Token

    Args:
        name: 审计方名称
        organization: 审计方组织
        contact_email: 联系邮箱
        scope: 允许访问的数据范围列表，如 ["audit_logs", "compliance_reports", "security_events"]
        expiry_days: 过期天数
        created_by: 创建者 ID
        max_requests_per_day: 每日最大请求数

    Returns:
        包含 token 明文和元数据的字典（token 明文仅在创建时返回一次）
    """
    # 验证参数
    if not name or not organization:
        raise ValueError("name 和 organization 不能为空")
    if expiry_days < 1 or expiry_days > TOKEN_MAX_EXPIRY_DAYS:
        raise ValueError(f"expiry_days 必须在 1 到 {TOKEN_MAX_EXPIRY_DAYS} 之间")

    # 生成 token 明文（格式: audit_read_xxxx）
    token_plaintext = f"audit_read_{secrets.token_urlsafe(48)}"
    token_hash = _hash_token(token_plaintext)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=expiry_days)

    token_info = {
        "token_id": f"at_{uuid.uuid4().hex[:12]}",
        "token_hash": token_hash,
        "name": name,
        "organization": organization,
        "contact_email": contact_email,
        "scope": scope,
        "status": "active",
        "created_by": created_by,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "last_used_at": None,
        "usage_count": 0,
        "max_requests_per_day": max_requests_per_day,
        "daily_request_count": 0,
        "daily_request_date": now.strftime("%Y-%m-%d"),
    }

    _audit_tokens[token_hash] = token_info

    logger.info(
        f"Audit token created: token_id={token_info['token_id']}, "
        f"name={name}, organization={organization}, "
        f"scope={scope}, expires_at={expires_at.isoformat()}"
    )

    # 返回时包含明文 token（仅此一次）
    return {
        "token": token_plaintext,
        "token_id": token_info["token_id"],
        "name": name,
        "organization": organization,
        "scope": scope,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat(),
    }


def verify_audit_token(token: str) -> Optional[dict]:
    """
    验证第三方审计 Token

    Args:
        token: Token 明文

    Returns:
        Token 信息字典（不含敏感字段），无效则返回 None
    """
    token_hash = _hash_token(token)
    token_info = _audit_tokens.get(token_hash)

    if not token_info:
        logger.warning(f"Audit token verification failed: token not found")
        return None

    # 检查状态
    if token_info["status"] != "active":
        logger.warning(
            f"Audit token verification failed: token status={token_info['status']}"
        )
        return None

    # 检查过期
    now = datetime.now(timezone.utc)
    expires_at = datetime.fromisoformat(token_info["expires_at"])
    if now > expires_at:
        token_info["status"] = "expired"
        logger.warning(f"Audit token expired: token_id={token_info['token_id']}")
        return None

    # 检查每日限额
    today = now.strftime("%Y-%m-%d")
    if token_info.get("daily_request_date") != today:
        token_info["daily_request_count"] = 0
        token_info["daily_request_date"] = today

    if token_info["daily_request_count"] >= token_info["max_requests_per_day"]:
        logger.warning(
            f"Audit token daily limit exceeded: "
            f"token_id={token_info['token_id']}, "
            f"count={token_info['daily_request_count']}"
        )
        return None

    # 更新使用信息
    token_info["last_used_at"] = now.isoformat()
    token_info["usage_count"] += 1
    token_info["daily_request_count"] += 1

    # 记录访问日志
    _token_access_logs.append({
        "token_id": token_info["token_id"],
        "accessed_at": now.isoformat(),
        "scope": token_info["scope"],
    })
    # 保留最近 10000 条
    if len(_token_access_logs) > 10000:
        _token_access_logs[:] = _token_access_logs[-10000:]

    # 返回不包含 token_hash 的信息
    return {
        "token_id": token_info["token_id"],
        "name": token_info["name"],
        "organization": token_info["organization"],
        "scope": token_info["scope"],
        "status": token_info["status"],
        "expires_at": token_info["expires_at"],
        "max_requests_per_day": token_info["max_requests_per_day"],
        "daily_request_count": token_info["daily_request_count"],
    }


# ==================== Token 管理 ====================

def list_audit_tokens(
    status: Optional[str] = None,
    organization: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    列出所有审计 Token

    Args:
        status: 状态过滤
        organization: 组织过滤
        limit: 限制数量
        offset: 偏移量

    Returns:
        Token 列表和总数
    """
    tokens = list(_audit_tokens.values())

    if status:
        tokens = [t for t in tokens if t.get("status") == status]
    if organization:
        tokens = [t for t in tokens if t.get("organization") == organization]

    total = len(tokens)
    tokens.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # 移除敏感字段
    safe_tokens = []
    for t in tokens[offset:offset + limit]:
        safe_tokens.append({
            "token_id": t["token_id"],
            "name": t["name"],
            "organization": t["organization"],
            "contact_email": t["contact_email"],
            "scope": t["scope"],
            "status": t["status"],
            "created_at": t["created_at"],
            "expires_at": t["expires_at"],
            "last_used_at": t["last_used_at"],
            "usage_count": t["usage_count"],
            "max_requests_per_day": t["max_requests_per_day"],
        })

    return {
        "items": safe_tokens,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_audit_token(token_id: str) -> Optional[dict]:
    """
    获取审计 Token 详情

    Args:
        token_id: Token ID

    Returns:
        Token 信息
    """
    for t in _audit_tokens.values():
        if t["token_id"] == token_id:
            return {
                "token_id": t["token_id"],
                "name": t["name"],
                "organization": t["organization"],
                "contact_email": t["contact_email"],
                "scope": t["scope"],
                "status": t["status"],
                "created_at": t["created_at"],
                "expires_at": t["expires_at"],
                "last_used_at": t["last_used_at"],
                "usage_count": t["usage_count"],
                "max_requests_per_day": t["max_requests_per_day"],
                "daily_request_count": t["daily_request_count"],
            }
    return None


def revoke_audit_token(token_id: str) -> bool:
    """
    撤销审计 Token

    Args:
        token_id: Token ID

    Returns:
        是否成功
    """
    for t in _audit_tokens.values():
        if t["token_id"] == token_id:
            t["status"] = "revoked"
            logger.info(f"Audit token revoked: token_id={token_id}")
            return True
    return False


def refresh_audit_token(token_id: str, extend_days: int = TOKEN_DEFAULT_EXPIRY_DAYS) -> Optional[dict]:
    """
    刷新审计 Token 过期时间

    Args:
        token_id: Token ID
        extend_days: 延长天数

    Returns:
        更新后的 Token 信息
    """
    for t in _audit_tokens.values():
        if t["token_id"] == token_id:
            if t["status"] != "active":
                logger.warning(f"Cannot refresh non-active token: {token_id}")
                return None

            now = datetime.now(timezone.utc)
            new_expiry = now + timedelta(days=extend_days)
            t["expires_at"] = new_expiry.isoformat()

            logger.info(f"Audit token refreshed: token_id={token_id}, new_expiry={new_expiry.isoformat()}")
            return {
                "token_id": t["token_id"],
                "name": t["name"],
                "expires_at": t["expires_at"],
                "status": t["status"],
            }
    return None


def get_token_access_logs(
    token_id: Optional[str] = None,
    limit: int = 100,
) -> List[dict]:
    """
    获取 Token 访问日志

    Args:
        token_id: Token ID 过滤
        limit: 限制数量

    Returns:
        访问日志列表
    """
    logs = _token_access_logs
    if token_id:
        logs = [l for l in logs if l.get("token_id") == token_id]

    return logs[-limit:]


# ==================== 第三方审计数据访问 ====================

def check_scope(token_info: dict, required_scope: str) -> bool:
    """
    检查 token 是否有指定的数据访问权限

    Args:
        token_info: Token 信息
        required_scope: 需要的权限范围

    Returns:
        是否有权限
    """
    return required_scope in token_info.get("scope", []) or "all" in token_info.get("scope", [])
