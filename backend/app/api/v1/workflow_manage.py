"""审批工作流 API - /api/v1/workflows"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.workflow import (
    WorkflowResponse, WorkflowApproval, WorkflowRejection,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import workflow_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 审批工作流引擎 ====================

@router.get("/", response_model=ApiResponse[PaginatedResponse[WorkflowResponse]])
async def list_workflows(
    pagination: PaginationParams = Depends(get_pagination_params),
    workflow_type: str = Query(None, description="工作流类型"),
    status: str = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取审批工单列表"""
    result = await workflow_service.list_workflows(
        db=db, applicant_id=user["user_id"],
        workflow_type=workflow_type, status=status, params=pagination,
    )
    return ApiResponse(data=result)


@router.get("/pending", response_model=ApiResponse[PaginatedResponse[WorkflowResponse]])
async def list_pending_workflows(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取待审批列表"""
    result = await workflow_service.list_pending_workflows(
        db=db, reviewer_id=user["user_id"], params=pagination,
    )
    return ApiResponse(data=result)


@router.get("/{workflow_id}", response_model=ApiResponse[WorkflowResponse])
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取审批详情"""
    result = await workflow_service.get_workflow(
        db=db, workflow_id=workflow_id,
    )
    return ApiResponse(data=result)


@router.post("/{workflow_id}/approve", response_model=ApiResponse)
async def approve_workflow(
    workflow_id: str,
    request: WorkflowApproval,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批通过"""
    result = await workflow_service.approve_workflow(
        db=db, workflow_id=workflow_id,
        reviewer_id=user["user_id"],
        comment=request.comment,
    )
    return ApiResponse(data=result)


@router.post("/{workflow_id}/reject", response_model=ApiResponse)
async def reject_workflow(
    workflow_id: str,
    request: WorkflowRejection,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批拒绝"""
    result = await workflow_service.reject_workflow(
        db=db, workflow_id=workflow_id,
        reviewer_id=user["user_id"],
        comment=request.comment,
    )
    return ApiResponse(data=result)
