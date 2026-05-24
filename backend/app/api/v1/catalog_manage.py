"""数据目录管理 API - /api/v1/catalog-manage"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, PaginatedRequest
from app.schemas.catalog_registration import (
    CatalogRegistrationCreate, CatalogRegistrationResponse,
    CatalogRegistrationUpdate, SupplyChannelConfig, ControlProtocolConfig,
    AccessScopeConfig, ComplianceDocUpload, CatalogReview,
    ControlTemplateCreate, ControlTemplateUpdate, ControlTemplateResponse,
    AccessScopeRuleCreate, AccessScopeRuleResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import catalog_service_v2, catalog_registration_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== R012: 目录登记 ====================

@router.post("/", response_model=ApiResponse[CatalogRegistrationResponse], status_code=201)
async def create_catalog(
    request: CatalogRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建目录登记"""
    data = request.dict() if hasattr(request, 'dict') else request.model_dump()
    result = await catalog_registration_service.create_catalog_registration(
        db=db,
        created_by=user["user_id"],
        organization_id=user["organization_id"],
        **data,
    )
    return ApiResponse(data=result)


@router.get("/", response_model=ApiResponse[PaginatedResponse[CatalogRegistrationResponse]])
async def list_catalogs(
    pagination: PaginationParams = Depends(get_pagination_params),
    catalog_type: str = Query(None, description="目录类型: dataset/service"),
    security_level: str = Query(None, description="安全等级"),
    status: str = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取目录列表"""
    result = await catalog_registration_service.list_catalog_registrations(
        db=db, params=pagination,
        organization_id=user.get("organization_id"),
        status=status,
        catalog_type=catalog_type,
        security_level=security_level,
    )
    return ApiResponse(data=result)


@router.get("/{catalog_id}", response_model=ApiResponse[CatalogRegistrationResponse])
async def get_catalog(
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取目录详情"""
    result = await catalog_registration_service.get_catalog_registration(db, catalog_id)
    return ApiResponse(data=result)


@router.put("/{catalog_id}", response_model=ApiResponse[CatalogRegistrationResponse])
async def update_catalog(
    catalog_id: str,
    request: CatalogRegistrationUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新目录"""
    data = request.dict(exclude_unset=True) if hasattr(request, 'dict') else request.model_dump(exclude_unset=True)
    result = await catalog_registration_service.update_catalog_registration(db, catalog_id, **data)
    return ApiResponse(data=result)


# ==================== R013: 供给渠道配置 ====================

@router.post("/{catalog_id}/supply-channels", response_model=ApiResponse)
async def configure_supply_channels(
    catalog_id: str,
    request: SupplyChannelConfig,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """配置供给渠道 — 存储到目录的 metadata_extra"""
    result = await catalog_registration_service.update_catalog_registration(
        db, catalog_id, metadata_extra={"supply_channels": request.channels if hasattr(request, 'channels') else []},
    )
    return ApiResponse(data=result)


# ==================== R014: 管控协议配置 ====================

@router.post("/{catalog_id}/control-protocol", response_model=ApiResponse)
async def configure_control_protocol(
    catalog_id: str,
    request: ControlProtocolConfig,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """配置管控协议 — 存储到目录的 security_policy"""
    data = request.dict() if hasattr(request, 'dict') else request.model_dump()
    result = await catalog_registration_service.update_catalog_registration(
        db, catalog_id, security_policy=data,
    )
    return ApiResponse(data=result)


@router.get("/control-templates", response_model=ApiResponse)
async def list_control_templates(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取管控模板列表"""
    result = await catalog_registration_service.list_control_templates(db, pagination)
    return ApiResponse(data=result)


@router.post("/{catalog_id}/access-scope", response_model=ApiResponse)
async def configure_access_scope(
    catalog_id: str,
    request: AccessScopeConfig,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """配置开放范围 — 存储到目录的 access_control"""
    data = request.dict() if hasattr(request, 'dict') else request.model_dump()
    result = await catalog_registration_service.update_catalog_registration(
        db, catalog_id, access_control=data,
    )
    return ApiResponse(data=result)


# ==================== R015: 审批流程 ====================

@router.post("/{catalog_id}/submit", response_model=ApiResponse)
async def submit_catalog(
    catalog_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """提交目录审批"""
    result = await catalog_registration_service.update_catalog_registration(
        db, catalog_id, status="pending",
    )
    return ApiResponse(data=result)


@router.put("/{catalog_id}/review", response_model=ApiResponse)
async def review_catalog(
    catalog_id: str,
    request: CatalogReview,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批目录（二级审批）"""
    result = await catalog_service_v2.review_catalog_entry(
        db=db, catalog_id=catalog_id, reviewer_id=user["user_id"],
        status=request.action, review_comment=request.comment,
    )
    return ApiResponse(data=result)


@router.post("/{catalog_id}/compliance-docs", response_model=ApiResponse)
async def upload_compliance_docs(
    catalog_id: str,
    request: ComplianceDocUpload,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """上传合规材料 — 存储到目录的 metadata_extra"""
    result = await catalog_registration_service.update_catalog_registration(
        db, catalog_id, metadata_extra={"compliance_docs": request.docs if hasattr(request, 'docs') else []},
    )
    return ApiResponse(data=result)


# ==================== 目录发布/取消发布 ====================

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


# ==================== 管控模板 CRUD（目录级） ====================

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
async def list_control_templates_by_catalog(
    catalog_id: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    status: str = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出目录下的管控模板"""
    result = await catalog_registration_service.list_control_templates(db, pagination, catalog_id, status)
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
