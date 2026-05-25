"""
通用审批工作流引擎
审批类型 / 审批层级 / 审批动作 / 审批记录 / 超时处理 / 通知机制
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import ApprovalWorkflow, ApprovalRecord
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    DataNotFoundError, DataValidationError, PermissionDeniedError,
)

logger = logging.getLogger(__name__)

# 审批类型
VALID_BUSINESS_TYPES = (
    "data_subscription",    # 数据订阅审批
    "product_publish",      # 产品上架审批
    "product_unpublish",    # 产品下架审批
    "org_certification",    # 机构认证审批
    "demand_claim",         # 需求承接审批
    "contract",             # 合约审批
    "custom",               # 自定义审批
)

# 审批层级类型
VALID_LEVEL_TYPES = ("single", "dual", "countersign")

# 审批动作
VALID_ACTIONS = ("approve", "reject", "transfer", "countersign")

# 审批记录状态
VALID_RECORD_STATUSES = ("pending", "in_progress", "approved", "rejected", "cancelled", "transferred", "timeout")

# 默认超时时间（小时）
DEFAULT_TIMEOUT_HOURS = 72


# ==================== 工作流模板管理 ====================

async def create_workflow(
    db: AsyncSession,
    name: str,
    workflow_type: str,
    created_by: str,
    description: Optional[str] = None,
    steps: Optional[list] = None,
    organization_id: Optional[str] = None,
) -> dict:
    """创建工作流模板"""
    if workflow_type not in VALID_BUSINESS_TYPES:
        raise DataValidationError(f"无效的工作流类型: {workflow_type}, 可选: {VALID_BUSINESS_TYPES}")

    wf = ApprovalWorkflow(
        name=name,
        description=description,
        workflow_type=workflow_type,
        organization_id=uuid.UUID(organization_id) if organization_id else None,
        steps=steps or [],
        is_system=False,
        status="active",
        created_by=uuid.UUID(created_by),
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)

    logger.info(f"Workflow created: {name}, type={workflow_type}")
    return _workflow_to_dict(wf)


async def update_workflow(db: AsyncSession, workflow_id: str, **kwargs) -> dict:
    """更新工作流模板"""
    result = await db.execute(
        select(ApprovalWorkflow).where(ApprovalWorkflow.id == uuid.UUID(workflow_id))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise DataNotFoundError("工作流模板不存在")
    if wf.is_system:
        raise DataValidationError("系统内置工作流不可修改")

    for field in ["name", "description", "steps", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(wf, field, kwargs[field])

    await db.commit()
    await db.refresh(wf)
    logger.info(f"Workflow updated: {workflow_id}")
    return _workflow_to_dict(wf)


async def get_workflow(db: AsyncSession, workflow_id: str) -> dict:
    """获取工作流模板详情"""
    result = await db.execute(
        select(ApprovalWorkflow).where(ApprovalWorkflow.id == uuid.UUID(workflow_id))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise DataNotFoundError("工作流模板不存在")
    return _workflow_to_dict(wf)


async def list_workflows(
    db: AsyncSession,
    params: PaginationParams,
    workflow_type: Optional[str] = None,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出工作流模板"""
    query = select(ApprovalWorkflow)
    if workflow_type:
        query = query.where(ApprovalWorkflow.workflow_type == workflow_type)
    if organization_id:
        query = query.where(ApprovalWorkflow.organization_id == uuid.UUID(organization_id))
    if status:
        query = query.where(ApprovalWorkflow.status == status)
    else:
        query = query.where(ApprovalWorkflow.status == "active")
    query = query.order_by(ApprovalWorkflow.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def delete_workflow(db: AsyncSession, workflow_id: str) -> bool:
    """删除工作流模板（软删除）"""
    result = await db.execute(
        select(ApprovalWorkflow).where(ApprovalWorkflow.id == uuid.UUID(workflow_id))
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise DataNotFoundError("工作流模板不存在")
    if wf.is_system:
        raise DataValidationError("系统内置工作流不可删除")

    wf.status = "deleted"
    await db.commit()
    logger.info(f"Workflow deleted: {workflow_id}")
    return True


# ==================== 发起审批 ====================

async def create_approval(
    db: AsyncSession,
    workflow_id: str,
    business_type: str,
    business_id: str,
    applicant_id: str,
    approval_data: Optional[dict] = None,
    timeout_hours: Optional[int] = None,
) -> dict:
    """发起审批"""
    wf_result = await db.execute(
        select(ApprovalWorkflow).where(ApprovalWorkflow.id == uuid.UUID(workflow_id))
    )
    wf = wf_result.scalar_one_or_none()
    if not wf:
        raise DataNotFoundError("工作流模板不存在")
    if wf.status != "active":
        raise DataValidationError(f"工作流状态不允许发起审批: {wf.status}")

    total_steps = len(wf.steps) if wf.steps else 1
    timeout_at = None
    if timeout_hours:
        timeout_at = datetime.now(timezone.utc) + timedelta(hours=timeout_hours)

    record = ApprovalRecord(
        workflow_id=uuid.UUID(workflow_id),
        business_type=business_type,
        business_id=uuid.UUID(business_id),
        applicant_id=uuid.UUID(applicant_id),
        current_step=1,
        total_steps=total_steps,
        approval_data={
            **(approval_data or {}),
            "timeout_at": timeout_at.isoformat() if timeout_at else None,
        },
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info(f"Approval created: type={business_type}, id={business_id}, workflow={workflow_id}")
    return _record_to_dict(record)


# ==================== 审批动作 ====================

async def approve(
    db: AsyncSession,
    record_id: str,
    approver_id: str,
    comment: Optional[str] = None,
) -> dict:
    """审批通过"""
    return await _execute_action(db, record_id, approver_id, "approve", comment)


async def reject(
    db: AsyncSession,
    record_id: str,
    approver_id: str,
    comment: Optional[str] = None,
) -> dict:
    """审批驳回"""
    return await _execute_action(db, record_id, approver_id, "reject", comment)


async def transfer(
    db: AsyncSession,
    record_id: str,
    approver_id: str,
    target_approver_id: str,
    comment: Optional[str] = None,
) -> dict:
    """转交给其他人审批"""
    result = await db.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == uuid.UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("审批记录不存在")
    if record.status not in ("pending", "in_progress"):
        raise DataValidationError(f"审批状态不允许转交: {record.status}")

    # 更新审批数据，记录转交信息
    transfer_info = {
        "action": "transfer",
        "from_approver": approver_id,
        "to_approver": target_approver_id,
        "comment": comment,
        "transferred_at": datetime.now(timezone.utc).isoformat(),
    }
    data = record.approval_data or {}
    transfers = data.get("transfers", [])
    transfers.append(transfer_info)
    data["transfers"] = transfers
    data["current_approver"] = target_approver_id
    record.approval_data = data
    record.status = "transferred"

    await db.commit()
    await db.refresh(record)
    logger.info(f"Approval {record_id} transferred from {approver_id} to {target_approver_id}")
    return _record_to_dict(record)


async def add_countersigner(
    db: AsyncSession,
    record_id: str,
    approver_id: str,
    countersigner_id: str,
    comment: Optional[str] = None,
) -> dict:
    """加签（增加审批人）"""
    result = await db.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == uuid.UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("审批记录不存在")
    if record.status not in ("pending", "in_progress"):
        raise DataValidationError(f"审批状态不允许加签: {record.status}")

    data = record.approval_data or {}
    countersigners = data.get("countersigners", [])
    countersigners.append({
        "approver_id": countersigner_id,
        "added_by": approver_id,
        "comment": comment,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    data["countersigners"] = countersigners
    record.approval_data = data
    record.total_steps += 1

    await db.commit()
    await db.refresh(record)
    logger.info(f"Approval {record_id}: countersigner {countersigner_id} added by {approver_id}")
    return _record_to_dict(record)


async def _execute_action(
    db: AsyncSession,
    record_id: str,
    approver_id: str,
    action: str,
    comment: Optional[str] = None,
) -> dict:
    """执行审批动作（内部）"""
    result = await db.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == uuid.UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("审批记录不存在")
    if record.status not in ("pending", "in_progress", "transferred"):
        raise DataValidationError(f"审批状态不可操作: {record.status}")

    # 记录审批历史
    data = record.approval_data or {}
    history = data.get("history", [])
    history.append({
        "action": action,
        "approver_id": approver_id,
        "step": record.current_step,
        "comment": comment,
        "acted_at": datetime.now(timezone.utc).isoformat(),
    })
    data["history"] = history
    record.approval_data = data

    if action == "reject":
        record.status = "rejected"
        record.reject_reason = comment
        record.approved_by = uuid.UUID(approver_id)
        record.approved_at = datetime.now(timezone.utc)
    elif action == "approve":
        if record.current_step >= record.total_steps:
            record.status = "approved"
            record.approved_by = uuid.UUID(approver_id)
            record.approved_at = datetime.now(timezone.utc)
        else:
            record.current_step += 1
            record.status = "in_progress"

    await db.commit()
    await db.refresh(record)
    logger.info(f"Approval {record_id}: {action} by {approver_id} at step {record.current_step}")
    return _record_to_dict(record)


# ==================== 审批查询 ====================

async def get_approval(db: AsyncSession, record_id: str) -> dict:
    """获取审批记录详情"""
    result = await db.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == uuid.UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("审批记录不存在")
    return _record_to_dict(record)


async def list_approvals(
    db: AsyncSession,
    params: PaginationParams,
    business_type: Optional[str] = None,
    business_id: Optional[str] = None,
    applicant_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出审批记录"""
    query = select(ApprovalRecord)
    if business_type:
        query = query.where(ApprovalRecord.business_type == business_type)
    if business_id:
        query = query.where(ApprovalRecord.business_id == uuid.UUID(business_id))
    if applicant_id:
        query = query.where(ApprovalRecord.applicant_id == uuid.UUID(applicant_id))
    if status:
        query = query.where(ApprovalRecord.status == status)
    query = query.order_by(ApprovalRecord.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def list_pending_approvals(
    db: AsyncSession,
    params: PaginationParams,
    business_type: Optional[str] = None,
) -> PaginatedResponse:
    """列出待审批记录"""
    query = select(ApprovalRecord).where(
        ApprovalRecord.status.in_(["pending", "in_progress", "transferred"])
    )
    if business_type:
        query = query.where(ApprovalRecord.business_type == business_type)
    query = query.order_by(ApprovalRecord.created_at.asc())

    result = await paginate_query(db, query, params)
    return result


async def cancel_approval(db: AsyncSession, record_id: str, user_id: str) -> dict:
    """取消审批"""
    result = await db.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == uuid.UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("审批记录不存在")
    if str(record.applicant_id) != user_id:
        raise PermissionDeniedError("只有申请人可以取消审批")
    if record.status not in ("pending", "in_progress", "transferred"):
        raise DataValidationError(f"审批状态不可取消: {record.status}")

    record.status = "cancelled"
    await db.commit()
    await db.refresh(record)
    logger.info(f"Approval cancelled: {record_id}")
    return _record_to_dict(record)


# ==================== 超时处理 ====================

async def check_timeout_approvals(db: AsyncSession) -> dict:
    """检查超时审批，返回超时列表"""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ApprovalRecord).where(
            ApprovalRecord.status.in_(["pending", "in_progress", "transferred"]),
        )
    )
    records = list(result.scalars().all())

    timeout_records = []
    for record in records:
        data = record.approval_data or {}
        timeout_at_str = data.get("timeout_at")
        if timeout_at_str:
            timeout_at = datetime.fromisoformat(timeout_at_str)
            if now > timeout_at:
                timeout_records.append({
                    "record_id": str(record.id),
                    "business_type": record.business_type,
                    "business_id": str(record.business_id),
                    "applicant_id": str(record.applicant_id),
                    "current_step": record.current_step,
                    "total_steps": record.total_steps,
                    "timeout_at": timeout_at_str,
                    "overdue_hours": round((now - timeout_at).total_seconds() / 3600, 1),
                })

    return {
        "total_pending": len(records),
        "timeout_count": len(timeout_records),
        "timeout_records": timeout_records,
        "checked_at": now.isoformat(),
    }


async def auto_approve_timeout(
    db: AsyncSession,
    timeout_hours: int = DEFAULT_TIMEOUT_HOURS,
    action: str = "reject",
) -> int:
    """自动处理超时审批（通过或驳回）"""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=timeout_hours)

    result = await db.execute(
        select(ApprovalRecord).where(
            ApprovalRecord.status.in_(["pending", "in_progress", "transferred"]),
            ApprovalRecord.created_at < cutoff,
        )
    )
    records = list(result.scalars().all())
    count = 0

    for record in records:
        if action == "approve":
            record.status = "approved"
            record.approved_at = now
        else:
            record.status = "timeout"
            record.reject_reason = f"审批超时({timeout_hours}小时)，系统自动处理"

        # 记录历史
        data = record.approval_data or {}
        history = data.get("history", [])
        history.append({
            "action": f"auto_{action}",
            "approver_id": "system",
            "step": record.current_step,
            "comment": f"审批超时{timeout_hours}小时，系统自动{('通过' if action == 'approve' else '驳回')}",
            "acted_at": now.isoformat(),
        })
        data["history"] = history
        record.approval_data = data
        count += 1

    if count > 0:
        await db.commit()
        logger.info(f"Auto-{action} {count} timeout approvals (older than {timeout_hours}h)")
    return count


# ==================== 通知机制 ====================

async def get_approval_notifications(
    db: AsyncSession,
    user_id: str,
    params: PaginationParams,
) -> PaginatedResponse:
    """获取用户的审批通知（待审批 + 已审批结果）"""
    # 待审批通知
    pending_query = (
        select(ApprovalRecord)
        .where(
            ApprovalRecord.status.in_(["pending", "in_progress", "transferred"]),
        )
        .order_by(ApprovalRecord.created_at.desc())
    )
    result = await paginate_query(db, pending_query, params)
    return result


async def get_approval_summary(db: AsyncSession, user_id: str) -> dict:
    """获取用户审批概览"""
    # 待处理
    pending_result = await db.execute(
        select(ApprovalRecord).where(
            ApprovalRecord.status.in_(["pending", "in_progress", "transferred"]),
        )
    )
    pending_count = len(list(pending_result.scalars().all()))

    # 已完成
    completed_result = await db.execute(
        select(ApprovalRecord).where(
            ApprovalRecord.status.in_(["approved", "rejected", "cancelled", "timeout"]),
        )
    )
    completed_records = list(completed_result.scalars().all())

    approved_count = sum(1 for r in completed_records if r.status == "approved")
    rejected_count = sum(1 for r in completed_records if r.status == "rejected")

    return {
        "pending_count": pending_count,
        "completed_count": len(completed_records),
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== 审批统计 ====================

async def get_approval_statistics(db: AsyncSession) -> dict:
    """获取审批统计"""
    result = await db.execute(select(ApprovalRecord))
    records = list(result.scalars().all())

    by_type = {}
    by_status = {}
    for r in records:
        by_type[r.business_type] = by_type.get(r.business_type, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1

    # 计算平均审批时长（已审批的记录）
    approved_records = [r for r in records if r.approved_at and r.created_at]
    avg_hours = 0
    if approved_records:
        total_hours = sum(
            (r.approved_at - r.created_at).total_seconds() / 3600
            for r in approved_records
        )
        avg_hours = round(total_hours / len(approved_records), 1)

    return {
        "total_records": len(records),
        "by_type": by_type,
        "by_status": by_status,
        "average_approval_hours": avg_hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== Helpers ====================

def _workflow_to_dict(wf: ApprovalWorkflow) -> dict:
    """工作流转字典"""
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "workflow_type": wf.workflow_type,
        "organization_id": str(wf.organization_id) if wf.organization_id else None,
        "steps": wf.steps,
        "is_system": wf.is_system,
        "status": wf.status,
        "created_by": str(wf.created_by),
        "created_at": wf.created_at.isoformat(),
        "updated_at": wf.updated_at.isoformat(),
    }


def _record_to_dict(record: ApprovalRecord) -> dict:
    """审批记录转字典"""
    return {
        "id": str(record.id),
        "workflow_id": str(record.workflow_id),
        "business_type": record.business_type,
        "business_id": str(record.business_id),
        "applicant_id": str(record.applicant_id),
        "current_step": record.current_step,
        "total_steps": record.total_steps,
        "approval_data": record.approval_data,
        "status": record.status,
        "approved_by": str(record.approved_by) if record.approved_by else None,
        "approved_at": record.approved_at.isoformat() if record.approved_at else None,
        "reject_reason": record.reject_reason,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
