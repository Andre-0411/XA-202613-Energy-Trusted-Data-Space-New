"""
操作日志审计 API
提供操作日志记录、查询、导出等功能
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.dependencies import get_current_user

router = APIRouter()

# ===== 数据模型 =====

class AuditLogResponse(BaseModel):
    id: str
    timestamp: datetime
    user_id: Optional[str] = None
    username: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "success"
    module: str

    class Config:
        from_attributes = True

class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int

class AuditLogCreate(BaseModel):
    action: str = Field(..., description="操作类型")
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    resource_name: Optional[str] = Field(None, description="资源名称")
    details: Optional[str] = Field(None, description="详细信息")
    module: str = Field(default="system", description="所属模块")

class AuditLogStatsResponse(BaseModel):
    total_logs: int
    today_count: int
    success_count: int
    failed_count: int
    action_stats: dict
    module_stats: dict


# ===== API 端点 =====

@router.get("/", response_model=AuditLogListResponse, summary="获取审计日志列表")
async def list_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    action: Optional[str] = Query(None, description="操作类型筛选"),
    resource_type: Optional[str] = Query(None, description="资源类型筛选"),
    user_id: Optional[str] = Query(None, description="用户ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    module: Optional[str] = Query(None, description="模块筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取审计日志列表（真实数据库查询）"""
    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    # 应用筛选条件
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.where(AuditLog.user_id == uuid.UUID(user_id))
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.where(AuditLog.created_at >= start)
        except:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.where(AuditLog.created_at <= end)
        except:
            pass

    # 获取总数
    count_query = select(func.count()).select_from(AuditLog)
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if user_id:
        count_query = count_query.where(AuditLog.user_id == uuid.UUID(user_id))
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            count_query = count_query.where(AuditLog.created_at >= start)
        except:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            count_query = count_query.where(AuditLog.created_at <= end)
        except:
            pass

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    # 获取用户名映射
    items = []
    for log in logs:
        username = None
        if log.user_id:
            user_result = await db.execute(select(User.username).where(User.id == log.user_id))
            user = user_result.scalar_one_or_none()
            username = user or "未知用户"

        items.append(AuditLogResponse(
            id=str(log.id),
            timestamp=log.created_at,
            user_id=str(log.user_id) if log.user_id else None,
            username=username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=str(log.resource_id),
            resource_name=log.details.get("resource_name") if log.details else None,
            details=log.details.get("description") if log.details else None,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            status="success",
            module=log.resource_type,
        ))

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", summary="创建审计日志")
async def create_audit_log(
    request: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建审计日志记录"""
    user_id = current_user.get("sub") or current_user.get("user_id")

    log = AuditLog(
        user_id=uuid.UUID(user_id) if user_id else None,
        action=request.action,
        resource_type=request.resource_type,
        resource_id=uuid.UUID(request.resource_id) if request.resource_id else uuid.uuid4(),
        details={
            "resource_name": request.resource_name,
            "description": request.details,
            "module": request.module,
        },
    )

    db.add(log)
    await db.commit()

    return {"message": "审计日志已记录", "id": str(log.id)}


@router.get("/stats", response_model=AuditLogStatsResponse, summary="获取审计日志统计")
async def get_audit_log_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取审计日志统计数据"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 总数
    total_result = await db.execute(select(func.count()).select_from(AuditLog))
    total_logs = total_result.scalar() or 0

    # 今日数量
    today_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= today)
    )
    today_count = today_result.scalar() or 0

    # 按操作类型统计
    action_result = await db.execute(
        select(AuditLog.action, func.count()).group_by(AuditLog.action)
    )
    action_stats = {row[0]: row[1] for row in action_result.all()}

    # 按资源类型统计
    module_result = await db.execute(
        select(AuditLog.resource_type, func.count()).group_by(AuditLog.resource_type)
    )
    module_stats = {row[0]: row[1] for row in module_result.all()}

    return AuditLogStatsResponse(
        total_logs=total_logs,
        today_count=today_count,
        success_count=total_logs,  # 简化：假设所有记录都是成功的
        failed_count=0,
        action_stats=action_stats,
        module_stats=module_stats,
    )


@router.get("/export", summary="导出审计日志")
async def export_audit_logs(
    format: str = Query("csv", description="导出格式"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """导出审计日志"""
    from fastapi.responses import StreamingResponse
    import csv
    import io

    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.where(AuditLog.created_at >= start)
        except:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.where(AuditLog.created_at <= end)
        except:
            pass

    result = await db.execute(query)
    logs = result.scalars().all()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["时间", "用户ID", "操作", "资源类型", "资源ID", "详情", "IP地址"])

        for log in logs:
            writer.writerow([
                log.created_at.isoformat(),
                str(log.user_id) if log.user_id else "",
                log.action,
                log.resource_type,
                str(log.resource_id),
                log.details.get("description", "") if log.details else "",
                log.ip_address or "",
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )

    return {"message": "仅支持CSV格式导出"}


@router.delete("/{log_id}", summary="删除审计日志")
async def delete_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除审计日志（仅管理员）"""
    user_role = current_user.get("role", "")
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除审计日志")

    result = await db.execute(select(AuditLog).where(AuditLog.id == uuid.UUID(log_id)))
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=404, detail="审计日志不存在")

    await db.delete(log)
    await db.commit()

    return {"message": "审计日志已删除"}
