"""
ABAC 策略管理 API - /api/v1/security/abac
策略 CRUD + 属性管理 + 策略评估 + 策略模板 + 策略模拟
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.abac import (
    AbacPolicyCreateRequest,
    AbacPolicyEvaluateRequest,
)
from app.utils.deps import get_current_user
from app.services import abac_service

router = APIRouter()


# ==================== 属性管理 ====================

@router.get("/attributes", response_model=ApiResponse)
async def list_attributes(
    user: dict = Depends(get_current_user),
):
    """列出所有内置属性定义"""
    result = await abac_service.list_attributes()
    return ApiResponse(data=result)


@router.get("/attributes/{name}", response_model=ApiResponse)
async def get_attribute(
    name: str = Path(description="属性名称"),
    user: dict = Depends(get_current_user),
):
    """获取单个属性定义"""
    result = await abac_service.get_attribute(name)
    if result is None:
        return ApiResponse(code=2001, message=f"属性未找到: {name}", data=None)
    return ApiResponse(data=result)


# ==================== 策略模板 ====================

@router.get("/templates", response_model=ApiResponse)
async def list_policy_templates(
    user: dict = Depends(get_current_user),
):
    """列出所有策略模板"""
    result = await abac_service.list_policy_templates()
    return ApiResponse(data=result)


@router.get("/templates/{template_key}", response_model=ApiResponse)
async def get_policy_template(
    template_key: str = Path(description="模板键名"),
    user: dict = Depends(get_current_user),
):
    """获取策略模板详情"""
    result = await abac_service.get_policy_template(template_key)
    if result is None:
        return ApiResponse(code=2001, message=f"策略模板未找到: {template_key}", data=None)
    return ApiResponse(data=result)


@router.post("/templates/{template_key}/create", response_model=ApiResponse, status_code=201)
async def create_policy_from_template(
    template_key: str = Path(description="模板键名"),
    name: Optional[str] = Query(default=None, description="策略名称（可选）"),
    priority: int = Query(default=0, description="优先级"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """从模板创建策略"""
    result = await abac_service.create_policy_from_template(
        db=db,
        template_key=template_key,
        name=name,
        priority=priority,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


# ==================== 策略 CRUD ====================

@router.get("/policies", response_model=ApiResponse)
async def list_policies(
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出 ABAC 策略"""
    result = await abac_service.list_policies(
        db=db,
        policy_type="ABAC",
        status=status,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.post("/policies", response_model=ApiResponse, status_code=201)
async def create_policy(
    request: AbacPolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建 ABAC 策略"""
    result = await abac_service.create_policy(
        db=db,
        request=request,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/policies/{policy_id}", response_model=ApiResponse)
async def get_policy(
    policy_id: str = Path(description="策略 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取策略详情"""
    result = await abac_service.get_policy(db=db, policy_id=policy_id)
    return ApiResponse(data=result)


@router.put("/policies/{policy_id}", response_model=ApiResponse)
async def update_policy(
    policy_id: str = Path(description="策略 ID"),
    request: AbacPolicyCreateRequest = ...,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新策略"""
    result = await abac_service.update_policy(
        db=db,
        policy_id=policy_id,
        request=request,
    )
    return ApiResponse(data=result)


@router.delete("/policies/{policy_id}", response_model=ApiResponse)
async def delete_policy(
    policy_id: str = Path(description="策略 ID"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除策略（软删除）"""
    await abac_service.delete_policy(db=db, policy_id=policy_id)
    return ApiResponse(data={"policy_id": policy_id, "status": "deleted"})


# ==================== 策略评估 ====================

@router.post("/evaluate", response_model=ApiResponse)
async def evaluate_access(
    request: AbacPolicyEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """评估访问请求"""
    result = await abac_service.evaluate_access(db=db, request=request)
    return ApiResponse(data=result.model_dump())


@router.post("/simulate", response_model=ApiResponse)
async def simulate_evaluation(
    request: AbacPolicyEvaluateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """模拟策略评估（不影响实际授权）"""
    result = await abac_service.simulate_evaluation(db=db, request=request)
    return ApiResponse(data=result)
