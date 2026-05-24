"""
安全策略 API - /api/v1/security/policies
策略CRUD + 权限评估
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.security import PolicyCreate, PolicyEvaluateRequest
from app.utils.deps import get_current_user
from app.services import security_policy_service

router = APIRouter()


@router.get("", response_model=ApiResponse)
async def list_policies(
    policy_type: Optional[str] = Query(None, description="策略类型: RBAC/ABAC"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """策略列表"""
    result = await security_policy_service.list_policies(
        db=db,
        policy_type=policy_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse, status_code=201)
async def create_policy(
    request: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建策略"""
    result = await security_policy_service.create_policy(
        db=db,
        request=request,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/{policy_id}", response_model=ApiResponse)
async def get_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """策略详情"""
    result = await security_policy_service.get_policy(db=db, policy_id=policy_id)
    return ApiResponse(data=result)


@router.put("/{policy_id}", response_model=ApiResponse)
async def update_policy(
    policy_id: str,
    request: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新策略"""
    result = await security_policy_service.update_policy(
        db=db, policy_id=policy_id, request=request,
    )
    return ApiResponse(data=result)


@router.delete("/{policy_id}", response_model=ApiResponse)
async def delete_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除策略"""
    await security_policy_service.delete_policy(db=db, policy_id=policy_id)
    return ApiResponse(data={"policy_id": policy_id, "status": "deleted"})


@router.post("/evaluate", response_model=ApiResponse)
async def evaluate_permission(
    request: PolicyEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """评估权限"""
    result = await security_policy_service.evaluate_permission(
        db=db, request=request,
    )
    return ApiResponse(data=result)
