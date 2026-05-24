"""合约管理 API - /api/v1/contracts"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.contract import (
    ContractCreate, ContractResponse, ContractUpdate,
    ContractApproval, ContractSign, PricingConfig,
    ContractAmendment, AmendmentReview,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import contract_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R042/R043: 合约管理 ====================

@router.post("/", response_model=ApiResponse[ContractResponse], status_code=201)
async def create_contract(
    request: ContractCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建合约"""
    data = request.dict() if hasattr(request, 'dict') else request.model_dump()
    result = await contract_service.create_contract(
        db=db,
        title=data.get("title", ""),
        contract_type=data.get("contract_type", "electronic"),
        party_a_org_id=data.get("party_a_org_id", user.get("organization_id", "")),
        party_a_user_id=data.get("party_a_user_id", user["user_id"]),
        party_b_org_id=data.get("party_b_org_id", ""),
        content=data.get("content", ""),
        created_by=user["user_id"],
        party_b_user_id=data.get("party_b_user_id"),
        terms=data.get("terms"),
        pricing=data.get("pricing"),
        effective_date=data.get("effective_date"),
        expiration_date=data.get("expiration_date"),
    )
    return ApiResponse(data=result)


@router.get("/", response_model=ApiResponse[PaginatedResponse[ContractResponse]])
async def list_contracts(
    pagination: PaginationParams = Depends(get_pagination_params),
    contract_type: str = Query(None, description="合约类型: paper/electronic"),
    status: str = Query(None, description="状态"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取合约列表"""
    result = await contract_service.list_contracts(
        db=db, params=pagination,
        contract_type=contract_type, status=status,
        party_a_org_id=user.get("organization_id"),
    )
    return ApiResponse(data=result)


@router.get("/{contract_id}", response_model=ApiResponse[ContractResponse])
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取合约详情"""
    result = await contract_service.get_contract(db=db, contract_id=contract_id)
    return ApiResponse(data=result)


@router.put("/{contract_id}", response_model=ApiResponse[ContractResponse])
async def update_contract(
    contract_id: str,
    request: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新合约"""
    result = await contract_service.update_contract(
        db=db, contract_id=contract_id, **request.dict(exclude_unset=True),
    )
    return ApiResponse(data=result)


@router.post("/{contract_id}/approve", response_model=ApiResponse)
async def approve_contract(
    contract_id: str,
    request: ContractApproval,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批合约 — 通过则签署激活，拒绝则更新状态"""
    if request.action == "approve":
        result = await contract_service.sign_contract(
            db=db, contract_id=contract_id,
            signer_id=user["user_id"],
            blockchain_enabled=False,
        )
    else:
        result = await contract_service.update_contract(
            db=db, contract_id=contract_id,
            status="rejected",
        )
    return ApiResponse(data=result)


# ==================== R043: 电子签名 ====================

@router.post("/{contract_id}/sign", response_model=ApiResponse)
async def sign_contract(
    contract_id: str,
    request: ContractSign,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """电子签名（SM2）"""
    result = await contract_service.sign_contract(
        db=db, contract_id=contract_id,
        signer_id=user["user_id"],
        blockchain_enabled=request.blockchain_enabled,
    )
    return ApiResponse(data=result)


# ==================== R044: 合约定价 ====================

@router.post("/{contract_id}/pricing", response_model=ApiResponse)
async def configure_pricing(
    contract_id: str,
    request: PricingConfig,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """配置定价 — 通过 update_contract 更新 pricing 字段"""
    result = await contract_service.update_contract(
        db=db, contract_id=contract_id,
        pricing=request.dict(),
    )
    return ApiResponse(data=result)


# ==================== R045: 合约变更 ====================

@router.post("/{contract_id}/amend", response_model=ApiResponse)
async def amend_contract(
    contract_id: str,
    request: ContractAmendment,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """合约变更"""
    result = await contract_service.create_amendment(
        db=db, contract_id=contract_id,
        reason=request.reason,
        created_by=user["user_id"],
        changes=request.changes,
    )
    return ApiResponse(data=result)


@router.post("/{contract_id}/terminate", response_model=ApiResponse)
async def terminate_contract(
    contract_id: str,
    request: ContractAmendment,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """合约终止"""
    result = await contract_service.terminate_contract(
        db=db, contract_id=contract_id,
        user_id=user["user_id"],
    )
    return ApiResponse(data=result)


@router.put("/amendments/{amendment_id}/review", response_model=ApiResponse)
async def review_amendment(
    amendment_id: str,
    request: AmendmentReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批变更/终止"""
    result = await contract_service.review_amendment(
        db=db, amendment_id=amendment_id,
        reviewer_id=user["user_id"],
        status=request.action,
    )
    return ApiResponse(data=result)
