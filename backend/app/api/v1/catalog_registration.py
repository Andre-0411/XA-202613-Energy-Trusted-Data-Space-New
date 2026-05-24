"""数据目录注册 API - /api/v1/catalog-registrations"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.catalog_registration import (
    CatalogRegistrationCreate, CatalogRegistrationUpdate, CatalogRegistrationResponse,
    ControlTemplateCreate, ControlTemplateUpdate, ControlTemplateResponse,
    AccessScopeRuleCreate, AccessScopeRuleResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import catalog_registration_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 数据目录注册 CRUD ====================

@router.post("", response_model=ApiResponse[CatalogRegistrationResponse], status_code=201)
async def create_catalog_registration(
    request: CatalogRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建数据目录注册"""
    result = await catalog_registration_service.create_catalog_registration(
        db=db,
        owner_id=user["user_id"],
        organization_id=user.get("organization_id", ""),
        catalog_type=request.catalog_type,
        name=request.name,
        security_level=request.security_level,
        visibility=request.visibility,
        supply_channels=request.supply_channels,
        control_protocol=request.control_protocol,
        compliance_docs=request.compliance_docs,
        api_config=request.api_config,
        description=request.description,
        tags=request.tags,
    )
    return ApiResponse(data=result)


@router.get("", response_model=ApiResponse[PaginatedResponse[CatalogRegistrationResponse]])
async def list_catalog_registrations(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    catalog_type: Optional[str] = Query(None, description="目录类型"),
    security_level: Optional[str] = Query(None, description="安全等级"),
    visibility: Optional[str] = Query(None, description="可见性"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出数据目录"""
    result = await catalog_registration_service.list_catalog_registrations(
        db, pagination, user.get("organization_id"), status, catalog_type, security_level, visibility
    )
    return ApiResponse(data=result)


@router.get("/{catalog_id}", response_model=ApiResponse[CatalogRegistrationResponse])
async def get_catalog_registration(
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取目录详情"""
    result = await catalog_registration_service.get_catalog_registration(db, catalog_id)
    return ApiResponse(data=result)


@router.put("/{catalog_id}", response_model=ApiResponse[CatalogRegistrationResponse])
async def update_catalog_registration(
    catalog_id: str,
    request: CatalogRegistrationUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新目录"""
    result = await catalog_registration_service.update_catalog_registration(
        db, catalog_id,
        name=request.name,
        description=request.description,
        security_level=request.security_level,
        visibility=request.visibility,
        control_protocol=request.control_protocol,
        compliance_docs=request.compliance_docs,
        api_config=request.api_config,
        tags=request.tags,
    )
    return ApiResponse(data=result)


@router.delete("/{catalog_id}", response_model=ApiResponse)
async def delete_catalog_registration(
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除目录"""
    await catalog_registration_service.delete_catalog_registration(db, catalog_id)
    return ApiResponse(message="目录已删除")


@router.post("/{catalog_id}/publish", response_model=ApiResponse)
async def publish_catalog(
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """发布目录"""
    result = await catalog_registration_service.publish_catalog_registration(db, catalog_id)
    return ApiResponse(data=result)


@router.post("/{catalog_id}/unpublish", response_model=ApiResponse)
async def unpublish_catalog(
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """取消发布目录"""
    result = await catalog_registration_service.unpublish_catalog_registration(db, catalog_id)
    return ApiResponse(data=result)


# ==================== 管控模板 ====================

@router.post("/{catalog_id}/control-templates", response_model=ApiResponse[ControlTemplateResponse], status_code=201)
async def create_control_template(
    catalog_id: str,
    request: ControlTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建管控模板"""
    result = await catalog_registration_service.create_control_template(
        db=db,
        catalog_id=catalog_id,
        name=request.name,
        template_type=request.template_type,
        rules=request.rules,
        description=request.description,
    )
    return ApiResponse(data=result)


@router.get("/{catalog_id}/control-templates", response_model=ApiResponse[PaginatedResponse[ControlTemplateResponse]])
async def list_control_templates(
    catalog_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出管控模板"""
    result = await catalog_registration_service.list_control_templates(db, pagination, catalog_id, status)
    return ApiResponse(data=result)


@router.get("/{catalog_id}/control-templates/{template_id}", response_model=ApiResponse[ControlTemplateResponse])
async def get_control_template(
    catalog_id: str,
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取管控模板详情"""
    result = await catalog_registration_service.get_control_template(db, template_id)
    return ApiResponse(data=result)


@router.put("/{catalog_id}/control-templates/{template_id}", response_model=ApiResponse[ControlTemplateResponse])
async def update_control_template(
    catalog_id: str,
    template_id: str,
    request: ControlTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新管控模板"""
    result = await catalog_registration_service.update_control_template(
        db, template_id,
        name=request.name,
        template_type=request.template_type,
        rules=request.rules,
        description=request.description,
        status=request.status,
    )
    return ApiResponse(data=result)


@router.delete("/{catalog_id}/control-templates/{template_id}", response_model=ApiResponse)
async def delete_control_template(
    catalog_id: str,
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除管控模板"""
    await catalog_registration_service.delete_control_template(db, template_id)
    return ApiResponse(message="管控模板已删除")


# ==================== 访问范围规则 ====================

@router.post("/{catalog_id}/access-rules", response_model=ApiResponse[AccessScopeRuleResponse], status_code=201)
async def create_access_scope_rule(
    catalog_id: str,
    request: AccessScopeRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建访问范围规则"""
    result = await catalog_registration_service.create_access_scope_rule(
        db=db,
        catalog_id=catalog_id,
        rule_type=request.rule_type,
        target_id=request.target_id,
        permissions=request.permissions,
        conditions=request.conditions,
    )
    return ApiResponse(data=result)


@router.get("/{catalog_id}/access-rules", response_model=ApiResponse[PaginatedResponse[AccessScopeRuleResponse]])
async def list_access_scope_rules(
    catalog_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出访问范围规则"""
    result = await catalog_registration_service.list_access_scope_rules(db, pagination, catalog_id)
    return ApiResponse(data=result)


@router.delete("/{catalog_id}/access-rules/{rule_id}", response_model=ApiResponse)
async def delete_access_scope_rule(
    catalog_id: str,
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """删除访问范围规则"""
    await catalog_registration_service.delete_access_scope_rule(db, rule_id)
    return ApiResponse(message="访问范围规则已删除")
