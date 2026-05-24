"""
四级安全等级防护矩阵 API - /api/v1/security/levels
四级安全等级: 核心(一级/机密)、重要(二级/敏感)、一般(三级/内部)、公开(四级)
自动安全分级 / 分类标签映射 / 能源领域规则
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.security_level import (
    SecurityLevelResponse,
    SecurityLevelPolicyResponse,
    SecurityCheckRequest,
    SecurityCheckResponse,
    SetSecurityLevelRequest,
)
from app.utils.deps import get_current_user
from app.services import security_level_service

router = APIRouter()


class AutoGradeRequest(BaseModel):
    """自动安全分级请求"""
    data_name: str = Field(..., description="数据名称")
    data_description: Optional[str] = Field(None, description="数据描述")
    data_category: Optional[str] = Field(None, description="数据分类（发电/用电/调度/市场/设备状态/地理信息）")
    data_subcategory: Optional[str] = Field(None, description="数据子分类")
    has_pii: bool = Field(False, description="是否包含个人信息")
    is_realtime: bool = Field(False, description="是否实时数据")
    data_size: int = Field(0, description="数据大小（记录数）")
    existing_tags: Optional[list[str]] = Field(None, description="已有标签")


@router.get("", response_model=ApiResponse[list[SecurityLevelResponse]])
async def get_all_security_levels(
    user: dict = Depends(get_current_user),
):
    """
    获取所有安全等级

    返回四级安全等级信息，包括：
    - 核心/机密（一级）
    - 重要/敏感（二级）
    - 一般/内部（三级）
    - 公开（四级）
    """
    levels = security_level_service.get_all_levels()
    return ApiResponse(data=levels)


@router.get("/classification-mapping", response_model=ApiResponse)
async def get_classification_mapping(
    user: dict = Depends(get_current_user),
):
    """
    获取分类标签到安全等级的映射

    返回公开/内部/敏感/机密等标签到安全等级的映射关系
    """
    result = security_level_service.get_classification_mapping()
    return ApiResponse(data=result)


@router.post("/auto-grade", response_model=ApiResponse)
async def auto_grade_security(
    request: AutoGradeRequest,
    user: dict = Depends(get_current_user),
):
    """
    自动安全分级

    基于能源领域规则自动判断数据的安全等级。
    规则包括：
    - 关键词匹配（调度指令→核心，用户数据→重要等）
    - 数据分类映射（调度/指令→核心，交易/结算→重要等）
    - PII检测（含个人信息→重要）
    - 实时数据检测（实时→提升等级）
    - 数据量评估（大数据量→提升等级）
    """
    result = security_level_service.auto_grade_security(
        data_name=request.data_name,
        data_description=request.data_description,
        data_category=request.data_category,
        data_subcategory=request.data_subcategory,
        has_pii=request.has_pii,
        is_realtime=request.is_realtime,
        data_size=request.data_size,
        existing_tags=request.existing_tags,
    )
    return ApiResponse(data=result)


@router.get("/{level}/policies", response_model=ApiResponse[SecurityLevelPolicyResponse])
async def get_level_policies(
    level: int,
    user: dict = Depends(get_current_user),
):
    """获取指定等级的防护策略"""
    result = security_level_service.get_level_policies(level=level)
    return ApiResponse(data=result)


@router.post("/check", response_model=ApiResponse[SecurityCheckResponse])
async def check_resource_security(
    request: SecurityCheckRequest,
    user: dict = Depends(get_current_user),
):
    """检查资源安全等级要求"""
    result = security_level_service.check_resource_security(
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        context=request.context,
    )
    return ApiResponse(data=result)


@router.put("/{resource_id}", response_model=ApiResponse)
async def set_resource_security_level(
    resource_id: str,
    request: SetSecurityLevelRequest,
    user: dict = Depends(get_current_user),
):
    """设置资源安全等级"""
    result = security_level_service.set_resource_security_level(
        resource_id=resource_id,
        level=request.level,
        reason=request.reason,
        operator=user.get("username", ""),
    )
    return ApiResponse(data=result)
