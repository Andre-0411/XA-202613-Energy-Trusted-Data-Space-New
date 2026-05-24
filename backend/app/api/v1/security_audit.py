"""
增强审计 API 端点 - /api/v1/security/audit
全链路操作日志、异常行为检测、审计报告、哈希链验证、合规报告、安全态势评分
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.services import audit_enhanced

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# 新增请求 Schema
# ============================================================


class VerifyHashChainRequest(BaseModel):
    """哈希链验证请求"""
    start_time: Optional[str] = Field(default=None, description="开始时间（ISO 8601）")
    end_time: Optional[str] = Field(default=None, description="结束时间（ISO 8601）")
    limit: int = Field(default=1000, description="验证条数上限")


class ComplianceReportRequest(BaseModel):
    """合规报告请求"""
    compliance_type: str = Field(default="general", description="合规类型: general/energy/data_security/access_control")
    period_days: int = Field(default=30, description="报告周期（天）")


# ============================================================
# 审计日志端点
# ============================================================


@router.get("/logs", summary="列出审计日志")
async def list_audit_logs(
    user_id: Optional[str] = Query(default=None, description="用户 ID"),
    action: Optional[str] = Query(default=None, description="操作类型"),
    resource_type: Optional[str] = Query(default=None, description="资源类型"),
    status: Optional[str] = Query(default=None, description="状态"),
    risk_level: Optional[str] = Query(default=None, description="风险等级"),
    start_time: Optional[str] = Query(default=None, description="开始时间"),
    end_time: Optional[str] = Query(default=None, description="结束时间"),
    limit: int = Query(default=100, description="限制数量"),
    offset: int = Query(default=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
):
    """
    列出审计日志（数据库查询）
    """
    start_dt = datetime.fromisoformat(start_time) if start_time else None
    end_dt = datetime.fromisoformat(end_time) if end_time else None
    
    result = await audit_enhanced.list_audit_logs(
        db=db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        status=status,
        risk_level=risk_level,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.get("/logs/{log_id}", summary="获取审计日志详情")
async def get_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取审计日志详情（数据库查询）
    """
    log = await audit_enhanced.get_audit_log(db=db, log_id=log_id)
    if not log:
        raise HTTPException(status_code=404, detail="审计日志未找到")
    return ApiResponse(data=log)


@router.get("/trace/{trace_id}", summary="获取全链路追踪日志")
async def get_trace_logs(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取全链路追踪日志（数据库查询）
    """
    logs = await audit_enhanced.get_trace_logs(db=db, trace_id=trace_id)
    return ApiResponse(data={"trace_id": trace_id, "logs": logs, "total": len(logs)})


@router.get("/anomalies", summary="列出异常行为")
async def list_anomalies(
    risk_level: Optional[str] = Query(default=None, description="风险等级"),
    limit: int = Query(default=50, description="限制数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    列出异常行为检测结果（数据库查询）
    """
    anomalies = await audit_enhanced.list_anomalies(
        db=db,
        risk_level=risk_level,
        limit=limit,
    )
    return ApiResponse(data={"anomalies": anomalies, "total": len(anomalies)})


# ============================================================
# 审计报告端点
# ============================================================


@router.post("/reports", summary="生成审计报告")
async def generate_audit_report(
    period_start: str = Query(description="开始时间"),
    period_end: str = Query(description="结束时间"),
    title: Optional[str] = Query(default=None, description="报告标题"),
    db: AsyncSession = Depends(get_db),
):
    """
    生成审计报告（数据库统计）
    """
    try:
        start_dt = datetime.fromisoformat(period_start)
        end_dt = datetime.fromisoformat(period_end)
    except ValueError:
        raise HTTPException(status_code=400, detail="时间格式无效")
    
    report = await audit_enhanced.generate_audit_report(
        db=db,
        period_start=start_dt,
        period_end=end_dt,
        title=title,
    )
    return ApiResponse(data=report)


@router.get("/reports", summary="列出审计报告")
async def list_audit_reports(
    limit: int = Query(default=20),
    db: AsyncSession = Depends(get_db),
):
    """
    列出审计报告
    """
    reports = await audit_enhanced.list_audit_reports(db=db, limit=limit)
    return ApiResponse(data={"reports": reports, "total": len(reports)})


# ============================================================
# 统计端点
# ============================================================


@router.get("/statistics", summary="获取审计统计")
async def get_audit_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    获取审计统计数据（数据库统计）
    """
    stats = await audit_enhanced.get_audit_statistics(db=db)
    return ApiResponse(data=stats)


# ============================================================
# 操作日志记录端点
# ============================================================


@router.post("/log", summary="记录操作日志")
async def log_operation(
    user_id: str = Query(description="用户 ID"),
    action: str = Query(description="操作"),
    resource_type: str = Query(description="资源类型"),
    resource_id: Optional[str] = Query(default=None, description="资源 ID"),
    details: Optional[str] = Query(default=None, description="详情"),
    ip_address: Optional[str] = Query(default=None, description="IP 地址"),
    db: AsyncSession = Depends(get_db),
):
    """
    记录操作日志（数据库持久化 + 哈希链）
    """
    log = await audit_enhanced.log_operation(
        db=db,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    return ApiResponse(data=log)


# ============================================================
# 哈希链验证端点（新增）
# ============================================================


@router.post("/verify-hash-chain", summary="验证审计日志哈希链完整性")
async def verify_hash_chain(
    request: VerifyHashChainRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    验证审计日志哈希链完整性

    检查每条日志的 prev_hash 是否等于前一条日志的 hash，
    确保日志未被篡改。
    """
    start_dt = datetime.fromisoformat(request.start_time) if request.start_time else None
    end_dt = datetime.fromisoformat(request.end_time) if request.end_time else None

    result = await audit_enhanced.verify_hash_chain(
        db=db,
        start_time=start_dt,
        end_time=end_dt,
        limit=request.limit,
    )
    return ApiResponse(data=result)


# ============================================================
# 合规报告端点（新增）
# ============================================================


@router.post("/compliance-report", summary="生成合规报告")
async def generate_compliance_report(
    request: ComplianceReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    生成合规报告

    综合评估系统在指定周期内的合规状态，包括操作失败率、异常事件统计、
    合规评分和整改建议。
    """
    result = await audit_enhanced.generate_compliance_report(
        db=db,
        compliance_type=request.compliance_type,
        period_days=request.period_days,
    )
    return ApiResponse(data=result)


# ============================================================
# 安全态势评分端点（新增）
# ============================================================


@router.get("/security-posture", summary="获取安全态势评分")
async def get_security_posture(
    db: AsyncSession = Depends(get_db),
):
    """
    获取安全态势评分

    综合评估系统安全状态，基于 24 小时和 7 天内的异常事件数量、
    失败操作次数计算安全评分并给出评级。
    """
    result = await audit_enhanced.get_security_posture(db=db)
    return ApiResponse(data=result)
