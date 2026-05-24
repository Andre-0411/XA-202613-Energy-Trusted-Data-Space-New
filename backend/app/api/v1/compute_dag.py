"""
DAG 编排 API - /api/v1/compute/dag
DAG CRUD + 执行
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.compute import DagCreate, DagResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import dag_engine

router = APIRouter()


@router.get("", response_model=ApiResponse[PaginatedResponse[DagResponse]])
async def list_dags(
    status: Optional[str] = Query(None, description="DAG 状态筛选"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """DAG 列表"""
    result = await dag_engine.list_dags(db=db, params=pagination, status=status)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[DagResponse], status_code=201)
async def create_dag(
    request: DagCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建 DAG（含环检测和类型兼容性验证）

    节点类型: FL/MPC/TEE/HE/DP/Sandbox/Input/Output
    """
    result = await dag_engine.create_dag(
        db=db, request=request, user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.get("/{dag_id}", response_model=ApiResponse[DagResponse])
async def get_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """DAG 详情"""
    result = await dag_engine.get_dag(db=db, dag_id=dag_id)
    return ApiResponse(data=result)


@router.put("/{dag_id}", response_model=ApiResponse[DagResponse])
async def update_dag(
    dag_id: str,
    request: DagCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新 DAG（自动递增版本号）"""
    result = await dag_engine.update_dag(db=db, dag_id=dag_id, request=request)
    return ApiResponse(data=result)


@router.post("/{dag_id}/execute", response_model=ApiResponse)
async def execute_dag(
    dag_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    执行 DAG（拓扑排序 + 按序调度计算任务）

    为每个计算节点创建 ComputeTask，按依赖关系顺序执行
    """
    result = await dag_engine.execute_dag(
        db=db, dag_id=dag_id, user_id=user["user_id"],
    )
    return ApiResponse(data=result)
