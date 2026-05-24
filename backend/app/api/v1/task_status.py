"""
任务状态追踪 API - /api/v1/compute/task-status
任务状态汇总 + 运行中任务查询
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services.task_status_service import (
    get_task_status_summary,
    get_running_tasks,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", response_model=ApiResponse)
async def status_summary(
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取任务状态汇总统计"""
    result = await get_task_status_summary(
        db=db,
        organization_id=organization_id,
    )
    return ApiResponse(data=result)


@router.get("/running", response_model=ApiResponse)
async def running_tasks(
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取正在运行的任务列表"""
    result = await get_running_tasks(
        db=db,
        organization_id=organization_id,
        limit=limit,
    )
    return ApiResponse(data={
        "tasks": result,
        "total": len(result),
    })
