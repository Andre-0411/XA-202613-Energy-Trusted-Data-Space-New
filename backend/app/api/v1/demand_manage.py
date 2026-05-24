"""需求管理 API - /api/v1/demands"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.demand import (
    DemandCreate, DemandResponse, DemandUpdate,
    DemandStatusUpdate, RiskAssessment,
    DemandClaimCreate, DemandClaimResponse, DemandClaimReview,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import demand_service, risk_assessment_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R037: 需求发布 ====================

@router.post("/", response_model=ApiResponse[DemandResponse], status_code=201)
async def create_demand(
    request: DemandCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """发布需求"""
    result = await demand_service.create_demand(
        db=db,
        publisher_id=user["user_id"],
        organization_id=user["organization_id"],
        data=request.dict(),
    )
    return ApiResponse(data=result)


@router.get("/", response_model=ApiResponse[PaginatedResponse[DemandResponse]])
async def list_demands(
    pagination: PaginationParams = Depends(get_pagination_params),
    demand_type: str = Query(None, description="需求类型"),
    status: str = Query(None, description="状态"),
    keyword: str = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取需求列表（需求大厅）"""
    result = await demand_service.list_demands(
        db=db, demand_type=demand_type, status=status,
        keyword=keyword, params=pagination,
    )
    return ApiResponse(data=result)


@router.get("/{demand_id}", response_model=ApiResponse[DemandResponse])
async def get_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取需求详情"""
    result = await demand_service.get_demand(db=db, demand_id=demand_id)
    return ApiResponse(data=result)


@router.put("/{demand_id}", response_model=ApiResponse[DemandResponse])
async def update_demand(
    demand_id: str,
    request: DemandUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新需求"""
    result = await demand_service.update_demand(
        db=db, demand_id=demand_id, data=request.dict(exclude_unset=True),
    )
    return ApiResponse(data=result)


# ==================== R038: 安全风险评估 ====================

@router.post("/{demand_id}/risk-assessment", response_model=ApiResponse)
async def assess_risk(
    demand_id: str,
    request: RiskAssessment,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """安全风险评估"""
    result = await risk_assessment_service.assess_demand_risk(
        db=db, demand_id=demand_id, assessment_data=request.dict(),
    )
    return ApiResponse(data=result)


# ==================== R039: 需求状态管理 ====================

@router.put("/{demand_id}/status", response_model=ApiResponse)
async def update_demand_status(
    demand_id: str,
    request: DemandStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新需求状态"""
    result = await demand_service.update_status(
        db=db, demand_id=demand_id, status=request.status,
    )
    return ApiResponse(data=result)


# ==================== R040: 需求认领 ====================

@router.post("/{demand_id}/claim", response_model=ApiResponse[DemandClaimResponse], status_code=201)
async def claim_demand(
    demand_id: str,
    request: DemandClaimCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """认领需求"""
    result = await demand_service.claim_demand(
        db=db,
        demand_id=demand_id,
        claimer_id=user["user_id"],
        claimer_org_id=user["organization_id"],
        proposal=request.proposal,
    )
    return ApiResponse(data=result)


@router.get("/{demand_id}/claims", response_model=ApiResponse)
async def list_claims(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取认领列表"""
    result = await demand_service.list_claims(db=db, demand_id=demand_id)
    return ApiResponse(data=result)


@router.put("/{demand_id}/claims/{claim_id}/review", response_model=ApiResponse)
async def review_claim(
    demand_id: str,
    claim_id: str,
    request: DemandClaimReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批认领"""
    result = await demand_service.review_claim(
        db=db, demand_id=demand_id, claim_id=claim_id,
        reviewer_id=user["user_id"],
        action=request.action,
        comment=request.comment,
    )
    return ApiResponse(data=result)


# ==================== R041: 运营方干预 ====================

@router.post("/{demand_id}/intervene", response_model=ApiResponse)
async def intervene_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """运营方干预（超7天）"""
    result = await demand_service.intervene_demand(
        db=db, demand_id=demand_id, operator_id=user["user_id"],
    )
    return ApiResponse(data=result)
