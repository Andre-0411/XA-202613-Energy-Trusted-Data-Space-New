"""
差分隐私 API - /api/v1/compute/dp
应用差分隐私 / DP配置查询
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import dp_service

router = APIRouter()


@router.post("/apply", response_model=ApiResponse)
async def apply_differential_privacy(
    name: str = Query(..., max_length=200, description="任务名称"),
    asset_id: str = Query(..., description="数据资产 ID"),
    mechanism: str = Query(..., description="DP机制: laplace/gaussian/exponential/report_noisy_max"),
    epsilon: float = Query(..., gt=0, description="隐私预算 epsilon"),
    delta: float = Query(1e-5, ge=0, lt=1, description="隐私参数 delta"),
    sensitivity: float = Query(1.0, gt=0, description="全局敏感度"),
    query_type: str = Query("count", description="查询类型: count/sum/avg/numeric"),
    config_template: Optional[str] = Query(None, description="配置模板: strict/balanced/relaxed/statistical"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    应用差分隐私

    机制说明:
    - laplace: Laplace 噪声机制（数值型查询）
    - gaussian: 高斯噪声机制（(ε,δ)-DP）
    - exponential: 指数机制（非数值型选择）
    - report_noisy_max: 噪声最大值报告（Top-K）

    可使用配置模板替代手动参数:
    - strict: ε=0.1, δ=1e-6 (隐私最强)
    - balanced: ε=1.0, δ=1e-5 (平衡)
    - relaxed: ε=10.0, δ=1e-4 (数据可用性优先)
    - statistical: ε=2.0, δ=1e-5 (统计分析)
    """
    result = await dp_service.apply_differential_privacy(
        db=db,
        name=name,
        asset_id=asset_id,
        mechanism=mechanism,
        epsilon=epsilon,
        delta=delta,
        sensitivity=sensitivity,
        query_type=query_type,
        config_template=config_template,
        user_id=user["user_id"],
        organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000"),
    )
    return ApiResponse(data=result)


@router.get("/configs", response_model=ApiResponse)
async def list_dp_configs():
    """DP 配置列表（机制 + 模板）"""
    result = await dp_service.list_dp_configs()
    return ApiResponse(data=result)
