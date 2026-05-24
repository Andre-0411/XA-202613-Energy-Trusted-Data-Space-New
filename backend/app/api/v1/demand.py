"""需求管理 API - /api/v1/demands"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.demand import (
    DemandCreate, DemandUpdate, DemandResponse,
    DemandClaimCreate, DemandClaimReview, DemandClaimResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import demand_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 需求 CRUD ====================

@router.post("", response_model=ApiResponse[DemandResponse], status_code=201)
async def create_demand(
    request: DemandCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建需求"""
    result = await demand_service.create_demand(
        db=db,
        publisher_id=user["user_id"],
        organization_id=user.get("organization_id", ""),
        demand_type=request.demand_type,
        title=request.title,
        description=request.description,
        technical_requirements=request.technical_requirements,
        budget_range=request.budget_range,
        deadline=request.deadline,
        security_risk_assessment=request.security_risk_assessment,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[DemandResponse]])
async def list_demands(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    demand_type: Optional[str] = Query(None, description="需求类型"),
    publisher_id: Optional[str] = Query(None, description="发布者 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出需求"""
    result = await demand_service.list_demands(
        db, pagination, status, demand_type, user.get("organization_id"), publisher_id
    )
    return ApiResponse(data=result)


@router.get("/{demand_id}", response_model=ApiResponse[DemandResponse])
async def get_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取需求详情"""
    result = await demand_service.get_demand(db, demand_id)
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
        db, demand_id,
        demand_type=request.demand_type,
        title=request.title,
        description=request.description,
        technical_requirements=request.technical_requirements,
        budget_range=request.budget_range,
        deadline=request.deadline,
        security_risk_assessment=request.security_risk_assessment,
        status=request.status,
    )
    return ApiResponse(data=result)


@router.delete("/{demand_id}", response_model=ApiResponse)
async def delete_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除需求"""
    await demand_service.delete_demand(db, demand_id)
    return ApiResponse(message="需求已删除")


@router.post("/{demand_id}/publish", response_model=ApiResponse[DemandResponse])
async def publish_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """发布需求"""
    result = await demand_service.publish_demand(db, demand_id)
    return ApiResponse(data=result)


@router.post("/{demand_id}/close", response_model=ApiResponse[DemandResponse])
async def close_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """关闭需求"""
    result = await demand_service.close_demand(db, demand_id)
    return ApiResponse(data=result)


# ==================== 需求认领 ====================

@router.post("/{demand_id}/claims", response_model=ApiResponse[DemandClaimResponse], status_code=201)
async def create_claim(
    demand_id: str,
    request: DemandClaimCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建需求认领"""
    result = await demand_service.create_claim(
        db=db,
        demand_id=demand_id,
        claimer_id=user["user_id"],
        claimer_org_id=user.get("organization_id", ""),
        proposal=request.proposal,
    )
    return ApiResponse(data=result)


@router.get("/{demand_id}/claims", response_model=ApiResponse[PaginatedResponse[DemandClaimResponse]])
async def list_claims(
    demand_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出需求认领"""
    result = await demand_service.list_claims(db, pagination, demand_id, status=status)
    return ApiResponse(data=result)


@router.post("/claims/{claim_id}/review", response_model=ApiResponse[DemandClaimResponse])
async def review_claim(
    claim_id: str,
    request: DemandClaimReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审核需求认领"""
    result = await demand_service.review_claim(db, claim_id, user["user_id"], request.status)
    return ApiResponse(data=result)
