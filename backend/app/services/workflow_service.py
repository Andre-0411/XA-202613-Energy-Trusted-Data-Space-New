"""
审批工作流服务
工作流模板管理 / 审批记录管理
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import ApprovalWorkflow, ApprovalRecord
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


# ==================== 工作流模板 ====================

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
    applicant_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出工作流模板"""
    query = select(ApprovalWorkflow)
    if workflow_type:
        query = query.where(ApprovalWorkflow.workflow_type == workflow_type)
    if organization_id:
        query = query.where(ApprovalWorkflow.organization_id == uuid.UUID(organization_id))
    if status:
        query = query.where(ApprovalWorkflow.status == status)
    query = query.order_by(ApprovalWorkflow.created_at.desc())

    from app.schemas.workflow import WorkflowResponse
    result = await paginate_query(db, query, params, WorkflowResponse)
    return result


async def list_pending_workflows(
    db: AsyncSession,
    reviewer_id: str,
    params: PaginationParams,
) -> PaginatedResponse:
    """列出待审批的工作流记录"""
    query = (
        select(ApprovalRecord)
        .where(ApprovalRecord.status.in_(["pending", "in_progress"]))
        .order_by(ApprovalRecord.created_at.desc())
    )
    from app.schemas.workflow import ApprovalRecordResponse
    result = await paginate_query(db, query, params, ApprovalRecordResponse)
    return result


async def approve_workflow(
    db: AsyncSession,
    workflow_id: str,
    reviewer_id: str,
    comment: Optional[str] = None,
) -> dict:
    """审批通过"""
    return await approve_step(db, record_id=workflow_id, approver_id=reviewer_id, action="approve", comment=comment)


async def reject_workflow(
    db: AsyncSession,
    workflow_id: str,
    reviewer_id: str,
    comment: Optional[str] = None,
) -> dict:
    """审批拒绝"""
    return await approve_step(db, record_id=workflow_id, approver_id=reviewer_id, action="reject", comment=comment)


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


# ==================== 审批记录 ====================

async def create_approval(
    db: AsyncSession,
    workflow_id: str,
    business_type: str,
    business_id: str,
    applicant_id: str,
    approval_data: Optional[dict] = None,
) -> dict:
    """发起审批"""
    wf_result = await db.execute(
        select(ApprovalWorkflow).where(ApprovalWorkflow.id == uuid.UUID(workflow_id))
    )
    wf = wf_result.scalar_one_or_none()
    if not wf:
        raise DataNotFoundError("工作流模板不存在")

    total_steps = len(wf.steps) if wf.steps else 1

    record = ApprovalRecord(
        workflow_id=uuid.UUID(workflow_id),
        business_type=business_type,
        business_id=uuid.UUID(business_id),
        applicant_id=uuid.UUID(applicant_id),
        current_step=1,
        total_steps=total_steps,
        approval_data=approval_data or {},
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info(f"Approval created: type={business_type}, id={business_id}")
    return _record_to_dict(record)


async def approve_step(
    db: AsyncSession,
    record_id: str,
    approver_id: str,
    action: str = "approve",
    comment: Optional[str] = None,
) -> dict:
    """审批操作（通过/驳回）"""
    result = await db.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == uuid.UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("审批记录不存在")
    if record.status not in ("pending", "in_progress"):
        raise DataValidationError(f"审批状态不可操作: {record.status}")

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
    logger.info(f"Approval {record_id}: {action} by {approver_id}")
    return _record_to_dict(record)


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

    from app.schemas.workflow import ApprovalRecordResponse
    result = await paginate_query(db, query, params, ApprovalRecordResponse)
    return result


async def cancel_approval(db: AsyncSession, record_id: str, user_id: str) -> dict:
    """取消审批"""
    result = await db.execute(
        select(ApprovalRecord).where(ApprovalRecord.id == uuid.UUID(record_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("审批记录不存在")
    if record.applicant_id != uuid.UUID(user_id):
        raise DataValidationError("只有申请人可以取消审批")
    if record.status not in ("pending", "in_progress"):
        raise DataValidationError(f"审批状态不可取消: {record.status}")

    record.status = "cancelled"
    await db.commit()
    await db.refresh(record)
    logger.info(f"Approval cancelled: {record_id}")
    return _record_to_dict(record)


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
