"""
第三方审计只读接口 API - /api/v1/ops/audit-external
提供只读 Token 认证的审计数据访问
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.schemas.common import ApiResponse
from app.services import audit_third_party
from app.services import audit_enhanced
from app.services import compliance_service
from app.utils.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# 第三方 Token 安全方案
_external_security = HTTPBearer(auto_error=False, scheme_name="AuditToken")


async def _get_external_audit_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_external_security),
) -> dict:
    """
    验证第三方审计 Token 并返回 Token 信息

    使用方式:
    - Header: Authorization: Bearer audit_read_xxxx
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={"code": 3001, "message": "未提供第三方审计 Token"},
        )

    token = credentials.credentials
    token_info = audit_third_party.verify_audit_token(token)

    if not token_info:
        raise HTTPException(
            status_code=401,
            detail={"code": 3002, "message": "Token 无效、已过期或已达每日限额"},
        )

    return token_info


# ==================== Token 管理（需要系统认证） ====================


@router.post(
    "/tokens",
    response_model=ApiResponse,
    status_code=201,
    summary="创建第三方审计 Token",
)
async def create_audit_token(
    name: str = Query(description="审计方名称"),
    organization: str = Query(description="审计方组织"),
    contact_email: str = Query(description="联系邮箱"),
    scope: str = Query(
        default="audit_logs,compliance_reports,security_events",
        description="数据范围，逗号分隔: audit_logs,compliance_reports,security_events,all",
    ),
    expiry_days: int = Query(default=90, description="过期天数 (1-365)"),
    max_requests_per_day: int = Query(default=10000, description="每日最大请求数"),
    user: dict = Depends(get_current_user),
):
    """
    创建第三方审计只读 Token

    需要系统管理员权限。

    - **name**: 审计方名称
    - **organization**: 审计方组织
    - **contact_email**: 联系邮箱
    - **scope**: 数据范围（逗号分隔），可选值: audit_logs, compliance_reports, security_events, all
    - **expiry_days**: 过期天数
    - **max_requests_per_day**: 每日请求限额

    ⚠️ Token 明文仅在创建时返回一次，请妥善保存。
    """
    # 检查权限
    if user.get("role") not in ("admin", "operator"):
        raise HTTPException(
            status_code=403,
            detail={"code": 1006, "message": "仅管理员可创建审计 Token"},
        )

    scope_list = [s.strip() for s in scope.split(",") if s.strip()]

    result = audit_third_party.generate_audit_token(
        name=name,
        organization=organization,
        contact_email=contact_email,
        scope=scope_list,
        expiry_days=expiry_days,
        created_by=user.get("user_id", ""),
        max_requests_per_day=max_requests_per_day,
    )

    return ApiResponse(data=result)


@router.get(
    "/tokens",
    response_model=ApiResponse,
    summary="列出第三方审计 Token",
)
async def list_audit_tokens(
    status: Optional[str] = Query(None, description="状态: active/expired/revoked"),
    organization: Optional[str] = Query(None, description="组织过滤"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
):
    """列出所有第三方审计 Token（管理员）"""
    if user.get("role") not in ("admin", "operator"):
        raise HTTPException(
            status_code=403,
            detail={"code": 1006, "message": "仅管理员可查看审计 Token 列表"},
        )

    result = audit_third_party.list_audit_tokens(
        status=status,
        organization=organization,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.get(
    "/tokens/{token_id}",
    response_model=ApiResponse,
    summary="获取 Token 详情",
)
async def get_audit_token(
    token_id: str,
    user: dict = Depends(get_current_user),
):
    """获取第三方审计 Token 详情（管理员）"""
    if user.get("role") not in ("admin", "operator"):
        raise HTTPException(
            status_code=403,
            detail={"code": 1006, "message": "仅管理员可查看审计 Token 详情"},
        )

    result = audit_third_party.get_audit_token(token_id=token_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"code": 2001, "message": "Token 不存在"},
        )
    return ApiResponse(data=result)


@router.post(
    "/tokens/{token_id}/revoke",
    response_model=ApiResponse,
    summary="撤销 Token",
)
async def revoke_audit_token(
    token_id: str,
    user: dict = Depends(get_current_user),
):
    """撤销第三方审计 Token（管理员）"""
    if user.get("role") not in ("admin", "operator"):
        raise HTTPException(
            status_code=403,
            detail={"code": 1006, "message": "仅管理员可撤销审计 Token"},
        )

    success = audit_third_party.revoke_audit_token(token_id=token_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"code": 2001, "message": "Token 不存在"},
        )
    return ApiResponse(data={"message": "Token 已撤销", "token_id": token_id})


@router.post(
    "/tokens/{token_id}/refresh",
    response_model=ApiResponse,
    summary="刷新 Token 过期时间",
)
async def refresh_audit_token(
    token_id: str,
    extend_days: int = Query(default=90, description="延长天数"),
    user: dict = Depends(get_current_user),
):
    """刷新第三方审计 Token 过期时间（管理员）"""
    if user.get("role") not in ("admin", "operator"):
        raise HTTPException(
            status_code=403,
            detail={"code": 1006, "message": "仅管理员可刷新审计 Token"},
        )

    result = audit_third_party.refresh_audit_token(
        token_id=token_id,
        extend_days=extend_days,
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"code": 2001, "message": "Token 不存在或状态不是 active"},
        )
    return ApiResponse(data=result)


@router.get(
    "/tokens/logs/access",
    response_model=ApiResponse,
    summary="Token 访问日志",
)
async def get_token_access_logs(
    token_id: Optional[str] = Query(None, description="Token ID 过滤"),
    limit: int = Query(default=100, le=1000),
    user: dict = Depends(get_current_user),
):
    """获取 Token 访问日志（管理员）"""
    if user.get("role") not in ("admin", "operator"):
        raise HTTPException(
            status_code=403,
            detail={"code": 1006, "message": "仅管理员可查看 Token 访问日志"},
        )

    logs = audit_third_party.get_token_access_logs(token_id=token_id, limit=limit)
    return ApiResponse(data={"items": logs, "total": len(logs)})


# ==================== 第三方只读审计数据接口 ====================


@router.get(
    "/audit/logs",
    response_model=ApiResponse,
    summary="[只读] 审计日志",
)
async def external_list_audit_logs(
    token_info: dict = Depends(_get_external_audit_user),
    user_id: Optional[str] = Query(None, description="用户 ID"),
    action: Optional[str] = Query(None, description="操作类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    risk_level: Optional[str] = Query(None, description="风险等级"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO"),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    [第三方只读] 查询审计日志

    使用第三方审计 Token 认证（Authorization: Bearer audit_read_xxxx）。

    数据范围要求: audit_logs 或 all
    """
    # 检查权限范围
    if not audit_third_party.check_scope(token_info, "audit_logs"):
        raise HTTPException(
            status_code=403,
            detail={"code": 3003, "message": "Token 无权访问审计日志数据"},
        )

    from datetime import datetime
    start_dt = datetime.fromisoformat(start_time) if start_time else None
    end_dt = datetime.fromisoformat(end_time) if end_time else None

    result = await audit_enhanced.list_audit_logs(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        risk_level=risk_level,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.get(
    "/audit/logs/{log_id}",
    response_model=ApiResponse,
    summary="[只读] 审计日志详情",
)
async def external_get_audit_log(
    log_id: str,
    token_info: dict = Depends(_get_external_audit_user),
):
    """
    [第三方只读] 获取审计日志详情

    数据范围要求: audit_logs 或 all
    """
    if not audit_third_party.check_scope(token_info, "audit_logs"):
        raise HTTPException(
            status_code=403,
            detail={"code": 3003, "message": "Token 无权访问审计日志数据"},
        )

    log = await audit_enhanced.get_audit_log(log_id)
    if not log:
        raise HTTPException(
            status_code=404,
            detail={"code": 2001, "message": "审计日志未找到"},
        )
    return ApiResponse(data=log)


@router.get(
    "/audit/anomalies",
    response_model=ApiResponse,
    summary="[只读] 异常行为检测",
)
async def external_list_anomalies(
    token_info: dict = Depends(_get_external_audit_user),
    risk_level: Optional[str] = Query(None, description="风险等级: low/medium/high/critical"),
    limit: int = Query(default=50, le=500),
):
    """
    [第三方只读] 查询异常行为检测结果

    数据范围要求: security_events 或 all
    """
    if not audit_third_party.check_scope(token_info, "security_events"):
        raise HTTPException(
            status_code=403,
            detail={"code": 3003, "message": "Token 无权访问安全事件数据"},
        )

    anomalies = await audit_enhanced.list_anomalies(
        risk_level=risk_level,
        limit=limit,
    )
    return ApiResponse(data={"anomalies": anomalies, "total": len(anomalies)})


@router.get(
    "/audit/statistics",
    response_model=ApiResponse,
    summary="[只读] 审计统计",
)
async def external_get_statistics(
    token_info: dict = Depends(_get_external_audit_user),
):
    """
    [第三方只读] 获取审计统计数据

    数据范围要求: audit_logs 或 all
    """
    if not audit_third_party.check_scope(token_info, "audit_logs"):
        raise HTTPException(
            status_code=403,
            detail={"code": 3003, "message": "Token 无权访问审计数据"},
        )

    stats = await audit_enhanced.get_audit_statistics()
    return ApiResponse(data=stats)


@router.get(
    "/audit/reports",
    response_model=ApiResponse,
    summary="[只读] 审计报告列表",
)
async def external_list_reports(
    token_info: dict = Depends(_get_external_audit_user),
    limit: int = Query(default=20, le=100),
):
    """
    [第三方只读] 查询审计报告列表

    数据范围要求: audit_logs 或 all
    """
    if not audit_third_party.check_scope(token_info, "audit_logs"):
        raise HTTPException(
            status_code=403,
            detail={"code": 3003, "message": "Token 无权访问审计报告数据"},
        )

    reports = await audit_enhanced.list_audit_reports(limit)
    return ApiResponse(data={"reports": reports, "total": len(reports)})


@router.get(
    "/compliance/reports",
    response_model=ApiResponse,
    summary="[只读] 合规报告列表",
)
async def external_list_compliance_reports(
    token_info: dict = Depends(_get_external_audit_user),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(default=20, le=100),
):
    """
    [第三方只读] 查询合规报告列表

    数据范围要求: compliance_reports 或 all
    """
    if not audit_third_party.check_scope(token_info, "compliance_reports"):
        raise HTTPException(
            status_code=403,
            detail={"code": 3003, "message": "Token 无权访问合规报告数据"},
        )

    from sqlalchemy.ext.asyncio import AsyncSession
    from app.database import get_db

    # 使用内部 DB session
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        reports = await compliance_service.list_reports(
            db=db,
            status=status,
            limit=limit,
            offset=0,
        )


    return ApiResponse(data=reports)


@router.get(
    "/compliance/statistics",
    response_model=ApiResponse,
    summary="[只读] 合规统计",
)
async def external_get_compliance_statistics(
    token_info: dict = Depends(_get_external_audit_user),
):
    """
    [第三方只读] 获取合规统计数据

    数据范围要求: compliance_reports 或 all
    """
    if not audit_third_party.check_scope(token_info, "compliance_reports"):
        raise HTTPException(
            status_code=403,
            detail={"code": 3003, "message": "Token 无权访问合规统计数据"},
        )

    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        stats = await compliance_service.get_statistics(db=db)

    return ApiResponse(data=stats)
