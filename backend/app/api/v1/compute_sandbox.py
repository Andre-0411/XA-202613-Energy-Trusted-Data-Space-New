"""
数据沙箱 API - /api/v1/compute/sandbox
沙箱CRUD / 算法准入扫描 / 出口审核
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import sandbox_service

router = APIRouter()


@router.get("", response_model=ApiResponse)
async def list_sandboxes(
    status: Optional[str] = Query(None, description="按状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """沙箱列表"""
    result = await sandbox_service.list_sandboxes(
        db=db, status=status, limit=limit, offset=offset,
    )
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse, status_code=201)
async def create_sandbox(
    name: str = Query(..., max_length=200, description="沙箱名称"),
    algorithm_code: str = Query(..., description="算法代码"),
    input_asset_ids: str = Query(..., description="输入资产ID（逗号分隔）"),
    cpu_limit: str = Query("2", description="CPU 限制"),
    memory_limit: str = Query("4Gi", description="内存限制"),
    timeout_seconds: int = Query(3600, description="超时秒数"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建数据沙箱

    沙箱在隔离环境中执行用户算法，网络默认关闭，资源受限
    """
    asset_ids = [a.strip() for a in input_asset_ids.split(",") if a.strip()]
    runtime_config = {
        "cpu_limit": cpu_limit,
        "memory_limit": memory_limit,
        "timeout_seconds": timeout_seconds,
        "network_enabled": False,
    }

    result = await sandbox_service.create_sandbox(
        db=db,
        name=name,
        algorithm_code=algorithm_code,
        input_asset_ids=asset_ids,
        runtime_config=runtime_config,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/{sandbox_id}", response_model=ApiResponse)
async def get_sandbox(
    sandbox_id: str,
    user: dict = Depends(get_current_user),
):
    """沙箱详情"""
    result = await sandbox_service.get_sandbox(sandbox_id=sandbox_id)
    return ApiResponse(data=result)


@router.delete("/{sandbox_id}", response_model=ApiResponse)
async def delete_sandbox(
    sandbox_id: str,
    user: dict = Depends(get_current_user),
):
    """删除沙箱（运行中的沙箱需先停止）"""
    await sandbox_service.delete_sandbox(sandbox_id=sandbox_id)
    return ApiResponse(message="沙箱已删除")


@router.post("/{sandbox_id}/scan", response_model=ApiResponse)
async def scan_algorithm(
    sandbox_id: str,
    user: dict = Depends(get_current_user),
):
    """
    算法准入扫描

    静态代码分析 + 黑名单关键词检测 + 资源限制检查
    扫描通过后沙箱状态变为 active
    """
    result = await sandbox_service.scan_algorithm(sandbox_id=sandbox_id)
    return ApiResponse(data=result)


@router.post("/{sandbox_id}/export", response_model=ApiResponse)
async def export_audit(
    sandbox_id: str,
    output_data: str = Query("", description="沙箱输出数据（用于脱敏检查）"),
    user: dict = Depends(get_current_user),
):
    """
    出口审核

    敏感数据残留检测 + 合规性验证 + 数据量限制检查
    审核通过才允许结果离开沙箱
    """
    result = await sandbox_service.export_audit(
        sandbox_id=sandbox_id, output_data=output_data,
    )
    return ApiResponse(data=result)
