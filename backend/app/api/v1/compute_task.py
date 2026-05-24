"""
计算任务 API - /api/v1/compute/tasks
任务CRUD + 启动/停止 + 结果查询 + 多方签名
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.compute import (
    ComputeTaskCreate, ComputeTaskResponse, TaskSignatureRequest,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import compute_service

router = APIRouter()


@router.get("", response_model=ApiResponse[PaginatedResponse[ComputeTaskResponse]])
async def list_tasks(
    task_type: Optional[str] = Query(None, description="任务类型: FL/MPC/TEE/HE/DP/Sandbox"),
    status: Optional[str] = Query(None, description="任务状态"),
    scenario: Optional[str] = Query(None, description="业务场景"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """计算任务列表"""
    result = await compute_service.list_tasks(
        db=db,
        params=pagination,
        task_type=task_type,
        status=status,
        scenario=scenario,
    )
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[ComputeTaskResponse], status_code=201)
async def create_task(
    request: ComputeTaskCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建计算任务"""
    result = await compute_service.create_task(
        db=db,
        request=request,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/{task_id}", response_model=ApiResponse[ComputeTaskResponse])
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """计算任务详情"""
    result = await compute_service.get_task(db=db, task_id=task_id)
    return ApiResponse(data=result)


@router.put("/{task_id}", response_model=ApiResponse[ComputeTaskResponse])
async def update_task(
    task_id: str,
    request: ComputeTaskCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新计算任务（仅 draft/pending 状态可修改）"""
    result = await compute_service.update_task(
        db=db, task_id=task_id, request=request,
    )
    return ApiResponse(data=result)


@router.post("/{task_id}/start", response_model=ApiResponse)
async def start_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """启动计算任务（需达到签名阈值）"""
    result = await compute_service.start_task(
        db=db, task_id=task_id, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.post("/{task_id}/stop", response_model=ApiResponse)
async def stop_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """停止计算任务"""
    result = await compute_service.stop_task(
        db=db, task_id=task_id, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.post("/{task_id}/complete", response_model=ApiResponse)
async def complete_task(
    task_id: str,
    result_ref: str = Query("", description="结果引用"),
    result_hash: str = Query("", description="结果哈希"),
    progress: int = Query(100, description="进度百分比"),
    error_message: str = Query("", description="错误信息（非空则标记为失败）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """完成计算任务（自动记录区块链存证）"""
    result = await compute_service.complete_task(
        db=db,
        task_id=task_id,
        result_ref=result_ref,
        result_hash=result_hash,
        progress=progress,
        error_message=error_message,
    )
    return ApiResponse(data=result)


@router.get("/{task_id}/result", response_model=ApiResponse)
async def get_task_result(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取计算任务结果"""
    result = await compute_service.get_task_result(db=db, task_id=task_id)
    return ApiResponse(data=result)


@router.post("/{task_id}/sign", response_model=ApiResponse)
async def sign_task(
    task_id: str,
    request: TaskSignatureRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """多方签名（SM2 签名验证）"""
    result = await compute_service.sign_task(
        db=db, task_id=task_id, request=request,
    )
    return ApiResponse(data=result)


@router.get("/{task_id}/signatures", response_model=ApiResponse)
async def get_task_signatures(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """查询任务签名状态"""
    result = await compute_service.get_task_signatures(db=db, task_id=task_id)
    return ApiResponse(data=result)
