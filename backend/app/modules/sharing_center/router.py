"""可信共享中心 - API路由"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.models import User
from app.schemas.compute import TaskCreate, TaskResponse, TaskWithCreator, TaskResult
from app.schemas import PaginatedResponse, MessageResponse
from app.utils.deps import get_current_user
from .service import (
    create_task,
    start_task,
    cancel_task,
    retry_task,
    get_task_result,
    get_task_list,
    get_task_detail,
)
from .privacy import get_task_estimate

router = APIRouter(prefix="/api/sharing-center", tags=["可信共享中心"])


@router.post("/task", response_model=TaskResponse, summary="创建计算任务")
def create_compute_task(
    task_in: TaskCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """创建隐私计算任务（联邦学习/安全多方计算/可信执行环境/同态加密）"""
    try:
        task = create_task(db, user.id, task_in)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/task/list", response_model=PaginatedResponse[TaskWithCreator], summary="获取任务列表")
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="任务状态筛选"),
    type: Optional[str] = Query(None, description="任务类型筛选(FL/MPC/TEE/HE)"),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """分页查询计算任务列表"""
    tasks, total = get_task_list(
        db, page=page, page_size=page_size,
        status=status, task_type=type, created_by=user.id,
    )

    # 为每个任务附加创建者名称
    items = []
    for task in tasks:
        detail = get_task_detail(db, task.id)
        items.append(TaskWithCreator(
            id=task.id,
            name=task.name,
            description=task.description,
            task_type=task.task_type,
            status=task.status,
            config=task.config,
            result=task.result,
            error_message=task.error_message,
            progress=task.progress,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_by=task.created_by,
            created_at=task.created_at,
            updated_at=task.updated_at,
            creator_name=detail["creator_name"] if detail else None,
        ))

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/task/{task_id}", response_model=TaskWithCreator, summary="获取任务详情")
def get_task(
    task_id: int,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """获取指定任务的详细信息"""
    detail = get_task_detail(db, task_id)
    if not detail:
        raise HTTPException(status_code=404, detail="任务不存在")
    if detail["created_by"] != user.id:
        raise HTTPException(status_code=403, detail="无权查看此任务")
    return detail


@router.post("/task/{task_id}/start", response_model=TaskResponse, summary="启动任务")
def start_compute_task(
    task_id: int,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """启动计算任务（Demo模式：立即模拟完成）"""
    try:
        task = start_task(db, task_id, user.id)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/task/{task_id}/cancel", response_model=TaskResponse, summary="取消任务")
def cancel_compute_task(
    task_id: int,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """取消计算任务（仅 created/queued 状态可取消）"""
    try:
        task = cancel_task(db, task_id, user.id)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/task/{task_id}/retry", response_model=TaskResponse, summary="重试任务")
def retry_compute_task(
    task_id: int,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """重试失败的计算任务"""
    try:
        task = retry_task(db, task_id, user.id)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/task/{task_id}/result", response_model=TaskResult, summary="获取任务结果")
def get_result(
    task_id: int,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """获取计算任务的详细结果和摘要"""
    try:
        result = get_task_result(db, task_id, user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/task/estimate", summary="估算任务资源")
def estimate_task(
    task_type: str = Query(..., description="任务类型(FL/MPC/TEE/HE)"),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """估算指定类型任务的执行时间、资源使用和成本"""
    estimate = get_task_estimate(task_type.upper(), {})
    return {
        "task_type": task_type.upper(),
        "estimate": estimate,
    }
