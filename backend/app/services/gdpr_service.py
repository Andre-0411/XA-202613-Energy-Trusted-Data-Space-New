"""
GDPR / 数据安全法合规服务
数据主体请求处理（访问权、删除权、可携带权、更正权）
数据导出、数据删除、请求管理
"""
import uuid
import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gdpr import DataSubjectRequest
from app.models.user import User, Organization
from app.models.access_log import AccessLog
from app.models.audit_log import AuditLog
from app.schemas.gdpr import (
    DataSubjectRequestCreate, DataSubjectRequestUpdate,
    DataSubjectRequestResponse, DataExportRequest, DataExportResponse,
    DataDeletionRequest, DataDeletionResponse,
)
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# GDPR 法定响应期限（天）
GDPR_DEADLINE_DAYS = 30

# 支持的请求类型
VALID_REQUEST_TYPES = {
    "access", "erasure", "portability", "rectification", "restrict_processing",
}


async def create_request(
    db: AsyncSession,
    request: DataSubjectRequestCreate,
) -> DataSubjectRequestResponse:
    """
    创建数据主体请求

    Args:
        db: 数据库会话
        request: 创建请求

    Returns:
        请求详情
    """
    if request.request_type not in VALID_REQUEST_TYPES:
        raise DataValidationError(
            message=f"不支持的请求类型: {request.request_type}",
            data={"valid_types": list(VALID_REQUEST_TYPES)},
        )

    # 验证用户存在（如果有）
    subject_user_id = None
    if request.subject_user_id:
        user_result = await db.execute(
            select(User).where(User.id == uuid.UUID(request.subject_user_id))
        )
        if not user_result.scalar_one_or_none():
            raise DataNotFoundError(message=f"用户不存在: {request.subject_user_id}")
        subject_user_id = uuid.UUID(request.subject_user_id)

    organization_id = None
    if request.organization_id:
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == uuid.UUID(request.organization_id)
            )
        )
        if not org_result.scalar_one_or_none():
            raise DataNotFoundError(message=f"组织不存在: {request.organization_id}")
        organization_id = uuid.UUID(request.organization_id)

    # 计算截止日期（GDPR 要求 30 天内响应）
    due_date = datetime.now(timezone.utc) + timedelta(days=GDPR_DEADLINE_DAYS)

    dsr = DataSubjectRequest(
        request_type=request.request_type,
        subject_user_id=subject_user_id,
        subject_email=request.subject_email,
        subject_name=request.subject_name,
        organization_id=organization_id,
        description=request.description,
        status="pending",
        priority=request.priority,
        due_date=due_date,
    )
    db.add(dsr)
    await db.commit()
    await db.refresh(dsr)

    logger.info(
        f"数据主体请求创建: type={request.request_type}, "
        f"subject={request.subject_user_id or request.subject_email}, "
        f"due={due_date.isoformat()}"
    )
    return _dsr_to_response(dsr)


async def get_request(
    db: AsyncSession,
    request_id: str,
) -> DataSubjectRequestResponse:
    """获取请求详情"""
    result = await db.execute(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == uuid.UUID(request_id)
        )
    )
    dsr = result.scalar_one_or_none()
    if not dsr:
        raise DataNotFoundError(message=f"请求不存在: {request_id}")
    return _dsr_to_response(dsr)


async def list_requests(
    db: AsyncSession,
    params: PaginationParams,
    request_type: Optional[str] = None,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PaginatedResponse:
    """查询请求列表"""
    query = select(DataSubjectRequest)
    if request_type:
        query = query.where(DataSubjectRequest.request_type == request_type)
    if status:
        query = query.where(DataSubjectRequest.status == status)
    if organization_id:
        query = query.where(
            DataSubjectRequest.organization_id == uuid.UUID(organization_id)
        )
    query = query.order_by(DataSubjectRequest.created_at.desc())
    result = await paginate_query(db, query, params, DataSubjectRequestResponse)
    return result


async def update_request(
    db: AsyncSession,
    request_id: str,
    update: DataSubjectRequestUpdate,
    operator_id: Optional[str] = None,
) -> DataSubjectRequestResponse:
    """
    更新请求状态

    Args:
        db: 数据库会话
        request_id: 请求 ID
        update: 更新内容
        operator_id: 操作人 ID

    Returns:
        更新后的请求
    """
    result = await db.execute(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == uuid.UUID(request_id)
        )
    )
    dsr = result.scalar_one_or_none()
    if not dsr:
        raise DataNotFoundError(message=f"请求不存在: {request_id}")

    if update.status is not None:
        dsr.status = update.status
        if update.status == "completed":
            dsr.completed_at = datetime.now(timezone.utc)
    if update.assigned_to is not None:
        dsr.assigned_to = uuid.UUID(update.assigned_to)
    if update.rejection_reason is not None:
        dsr.rejection_reason = update.rejection_reason
    if update.response_data is not None:
        dsr.response_data = update.response_data

    await db.commit()
    await db.refresh(dsr)
    logger.info(f"请求更新: {request_id}, status={dsr.status}")
    return _dsr_to_response(dsr)


async def process_access_request(
    db: AsyncSession,
    request_id: str,
) -> DataSubjectRequestResponse:
    """
    处理数据访问请求 - 收集用户所有数据

    Args:
        db: 数据库会话
        request_id: 请求 ID

    Returns:
        更新后的请求（含导出数据引用）
    """
    result = await db.execute(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == uuid.UUID(request_id)
        )
    )
    dsr = result.scalar_one_or_none()
    if not dsr:
        raise DataNotFoundError(message=f"请求不存在: {request_id}")

    if dsr.request_type not in ("access", "portability"):
        raise DataValidationError(
            message=f"请求类型 {dsr.request_type} 不支持数据访问处理"
        )

    user_id = dsr.subject_user_id
    collected_data: dict = {}

    if user_id:
        # 收集用户基础信息
        user_result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            collected_data["user_profile"] = {
                "id": str(user.id),
                "username": getattr(user, "username", ""),
                "email": getattr(user, "email", ""),
                "phone": getattr(user, "phone", ""),
                "created_at": user.created_at.isoformat() if hasattr(user, "created_at") and user.created_at else "",
            }

        # 收集审计日志
        audit_result = await db.execute(
            select(AuditLog).where(AuditLog.user_id == user_id).limit(1000)
        )
        audit_logs = audit_result.scalars().all()
        collected_data["audit_logs"] = [
            {
                "action": log.action,
                "resource_type": getattr(log, "resource_type", ""),
                "timestamp": log.created_at.isoformat() if hasattr(log, "created_at") and log.created_at else "",
            }
            for log in audit_logs
        ]

        # 收集访问日志
        access_result = await db.execute(
            select(AccessLog).where(AccessLog.user_id == user_id).limit(1000)
        )
        access_logs = access_result.scalars().all()
        collected_data["access_logs"] = [
            {
                "resource_id": str(log.resource_id) if hasattr(log, "resource_id") else "",
                "accessed_at": log.created_at.isoformat() if hasattr(log, "created_at") and log.created_at else "",
            }
            for log in access_logs
        ]

    dsr.status = "completed"
    dsr.completed_at = datetime.now(timezone.utc)
    dsr.response_data = {
        "collected_data": collected_data,
        "record_counts": {
            "audit_logs": len(collected_data.get("audit_logs", [])),
            "access_logs": len(collected_data.get("access_logs", [])),
        },
        "export_format": "json",
    }

    await db.commit()
    await db.refresh(dsr)
    logger.info(f"数据访问请求处理完成: {request_id}")
    return _dsr_to_response(dsr)


async def process_erasure_request(
    db: AsyncSession,
    request_id: str,
    retain_anonymized: bool = True,
) -> DataSubjectRequestResponse:
    """
    处理数据删除请求

    Args:
        db: 数据库会话
        request_id: 请求 ID
        retain_anonymized: 是否保留匿名化数据

    Returns:
        更新后的请求
    """
    result = await db.execute(
        select(DataSubjectRequest).where(
            DataSubjectRequest.id == uuid.UUID(request_id)
        )
    )
    dsr = result.scalar_one_or_none()
    if not dsr:
        raise DataNotFoundError(message=f"请求不存在: {request_id}")

    if dsr.request_type != "erasure":
        raise DataValidationError(
            message=f"请求类型 {dsr.request_type} 不支持数据删除处理"
        )

    user_id = dsr.subject_user_id
    deletion_summary: dict = {}

    if user_id:
        # 删除审计日志中的个人标识信息（匿名化或删除）
        if retain_anonymized:
            # 匿名化：保留记录但清除用户 ID
            audit_result = await db.execute(
                select(AuditLog).where(AuditLog.user_id == user_id)
            )
            audit_logs = audit_result.scalars().all()
            for log in audit_logs:
                log.user_id = None  # type: ignore
            deletion_summary["audit_logs_anonymized"] = len(audit_logs)
        else:
            # 硬删除
            del_result = await db.execute(
                delete(AuditLog).where(AuditLog.user_id == user_id)
            )
            deletion_summary["audit_logs_deleted"] = del_result.rowcount

        # 匿名化访问日志
        access_result = await db.execute(
            select(AccessLog).where(AccessLog.user_id == user_id)
        )
        access_logs = access_result.scalars().all()
        for log in access_logs:
            log.user_id = None  # type: ignore
        deletion_summary["access_logs_anonymized"] = len(access_logs)

    dsr.status = "completed"
    dsr.completed_at = datetime.now(timezone.utc)
    dsr.response_data = {
        "deletion_summary": deletion_summary,
        "anonymized": retain_anonymized,
    }

    await db.commit()
    await db.refresh(dsr)
    logger.info(f"数据删除请求处理完成: {request_id}, summary={deletion_summary}")
    return _dsr_to_response(dsr)


async def export_user_data(
    db: AsyncSession,
    request: DataExportRequest,
) -> DataExportResponse:
    """
    导出用户数据

    Args:
        db: 数据库会话
        request: 导出请求

    Returns:
        导出结果
    """
    user_result = await db.execute(
        select(User).where(User.id == uuid.UUID(request.user_id))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise DataNotFoundError(message=f"用户不存在: {request.user_id}")

    collected: dict = {
        "user_profile": {
            "id": str(user.id),
            "username": getattr(user, "username", ""),
            "email": getattr(user, "email", ""),
            "phone": getattr(user, "phone", ""),
        },
    }

    # 收集审计日志
    audit_result = await db.execute(
        select(AuditLog).where(AuditLog.user_id == user.id).limit(5000)
    )
    audit_logs = audit_result.scalars().all()
    collected["audit_logs"] = [
        {
            "action": log.action,
            "resource_type": getattr(log, "resource_type", ""),
            "timestamp": log.created_at.isoformat() if hasattr(log, "created_at") and log.created_at else "",
        }
        for log in audit_logs
    ]

    if request.format == "csv":
        # 转换为 CSV 格式
        output = io.StringIO()
        if collected["audit_logs"]:
            writer = csv.DictWriter(output, fieldnames=collected["audit_logs"][0].keys())
            writer.writeheader()
            writer.writerows(collected["audit_logs"])
        collected["csv_data"] = output.getvalue()

    return DataExportResponse(
        user_id=request.user_id,
        format=request.format,
        data=collected,
        exported_at=datetime.now(timezone.utc),
    )


async def delete_user_data(
    db: AsyncSession,
    request: DataDeletionRequest,
) -> DataDeletionResponse:
    """
    删除用户数据

    Args:
        db: 数据库会话
        request: 删除请求

    Returns:
        删除结果
    """
    if not request.confirm:
        raise DataValidationError(message="必须确认删除（confirm=true）")

    user_result = await db.execute(
        select(User).where(User.id == uuid.UUID(request.user_id))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise DataNotFoundError(message=f"用户不存在: {request.user_id}")

    records_deleted: dict = {}

    if request.retain_anonymized:
        # 匿名化
        audit_result = await db.execute(
            select(AuditLog).where(AuditLog.user_id == user.id)
        )
        audit_logs = audit_result.scalars().all()
        for log in audit_logs:
            log.user_id = None  # type: ignore
        records_deleted["audit_logs_anonymized"] = len(audit_logs)

        access_result = await db.execute(
            select(AccessLog).where(AccessLog.user_id == user.id)
        )
        access_logs = access_result.scalars().all()
        for log in access_logs:
            log.user_id = None  # type: ignore
        records_deleted["access_logs_anonymized"] = len(access_logs)
    else:
        # 硬删除
        audit_del = await db.execute(
            delete(AuditLog).where(AuditLog.user_id == user.id)
        )
        records_deleted["audit_logs_deleted"] = audit_del.rowcount

        access_del = await db.execute(
            delete(AccessLog).where(AccessLog.user_id == user.id)
        )
        records_deleted["access_logs_deleted"] = access_del.rowcount

    await db.commit()

    logger.info(
        f"用户数据删除: user={request.user_id}, "
        f"anonymized={request.retain_anonymized}, summary={records_deleted}"
    )
    return DataDeletionResponse(
        user_id=request.user_id,
        records_deleted=records_deleted,
        anonymized=request.retain_anonymized,
        processed_at=datetime.now(timezone.utc),
    )


async def get_gdpr_statistics(
    db: AsyncSession,
) -> dict:
    """
    获取 GDPR 请求统计

    Returns:
        统计数据
    """
    # 按类型统计
    type_result = await db.execute(
        select(
            DataSubjectRequest.request_type,
            func.count(DataSubjectRequest.id),
        ).group_by(DataSubjectRequest.request_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # 按状态统计
    status_result = await db.execute(
        select(
            DataSubjectRequest.status,
            func.count(DataSubjectRequest.id),
        ).group_by(DataSubjectRequest.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # 总数
    total_result = await db.execute(
        select(func.count(DataSubjectRequest.id))
    )
    total = total_result.scalar() or 0

    # 逾期请求（未完成且超过截止日期）
    now = datetime.now(timezone.utc)
    overdue_result = await db.execute(
        select(func.count(DataSubjectRequest.id)).where(
            and_(
                DataSubjectRequest.status.in_(["pending", "in_progress"]),
                DataSubjectRequest.due_date < now,
            )
        )
    )
    overdue_count = overdue_result.scalar() or 0

    return {
        "total_requests": total,
        "by_type": by_type,
        "by_status": by_status,
        "overdue_count": overdue_count,
        "deadline_days": GDPR_DEADLINE_DAYS,
        "generated_at": now.isoformat(),
    }


# ==================== 辅助函数 ====================

def _dsr_to_response(dsr: DataSubjectRequest) -> DataSubjectRequestResponse:
    """将 DataSubjectRequest 模型转换为响应"""
    return DataSubjectRequestResponse(
        id=str(dsr.id),
        request_type=dsr.request_type,
        subject_user_id=str(dsr.subject_user_id) if dsr.subject_user_id else None,
        subject_email=dsr.subject_email,
        subject_name=dsr.subject_name,
        organization_id=str(dsr.organization_id) if dsr.organization_id else None,
        description=dsr.description,
        status=dsr.status,
        priority=dsr.priority,
        assigned_to=str(dsr.assigned_to) if dsr.assigned_to else None,
        response_data=dsr.response_data,
        rejection_reason=dsr.rejection_reason,
        due_date=dsr.due_date,
        completed_at=dsr.completed_at,
        created_at=dsr.created_at,
        updated_at=dsr.updated_at,
    )
