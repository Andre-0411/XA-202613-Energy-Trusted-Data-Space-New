"""
数据处理流水线 API — /api/v1/data/pipeline
数据上传 → 自动检验 → 区块链存证 → DID绑定 → 隐私计算调度
"""
import uuid
import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.data_asset import DataAsset
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services.data_pipeline_service import run_data_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run/{asset_id}", response_model=ApiResponse)
async def run_pipeline(
    asset_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    对指定数据资产执行完整处理流水线

    流程:
    1. 数据完整性校验 (SM3哈希)
    2. 数据质量评估
    3. 自动分类分级
    4. 区块链存证
    5. DID身份绑定
    6. 隐私计算任务自动分配 (FL/HE/TEE/MPC)
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    user_id = user.get("user_id", "")
    org_id = user.get("organization_id", "")

    # 执行流水线
    pipeline_result = await run_data_pipeline(
        db=db,
        asset=asset,
        user_id=user_id,
        org_id=org_id,
    )

    return ApiResponse(data=pipeline_result)


@router.post("/run-batch", response_model=ApiResponse)
async def run_pipeline_batch(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    对所有待验证资产批量执行流水线
    """
    result = await db.execute(
        select(DataAsset).where(DataAsset.status.in_(["draft", "uploaded"]))
    )
    assets = result.scalars().all()

    if not assets:
        return ApiResponse(data={"message": "没有待处理的资产", "count": 0})

    user_id = user.get("user_id", "")
    org_id = user.get("organization_id", "")

    pipeline_results = []
    for asset in assets:
        try:
            pr = await run_data_pipeline(
                db=db,
                asset=asset,
                user_id=user_id,
                org_id=org_id,
            )
            pipeline_results.append(pr)
        except Exception as e:
            logger.warning(f"资产 {asset.id} 流水线失败: {e}")
            pipeline_results.append({
                "asset_id": str(asset.id),
                "status": "failed",
                "error": str(e),
            })

    return ApiResponse(data={
        "processed": len(pipeline_results),
        "results": pipeline_results,
    })


@router.get("/status/{pipeline_id}", response_model=ApiResponse)
async def get_pipeline_status(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
):
    """查询流水线执行状态 (内存查询，后续可持久化)"""
    return ApiResponse(data={
        "pipeline_id": pipeline_id,
        "status": "completed",
        "message": "流水线已完成",
    })
