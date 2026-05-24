"""
数据目录登记服务
目录登记管理 / 管控协议模板 / 开放范围管控
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import CatalogRegistration, ControlTemplate, AccessScopeRule
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


# ==================== 数据目录登记 ====================

async def create_catalog_registration(
    db: AsyncSession,
    organization_id: str,
    created_by: Optional[str] = None,
    **kwargs,
) -> dict:
    """创建数据目录登记"""
    reg = CatalogRegistration(
        catalog_type=kwargs.get("catalog_type", "api"),
        name=kwargs.get("name", ""),
        description=kwargs.get("description"),
        connector_id=uuid.UUID(kwargs["connector_id"]) if kwargs.get("connector_id") else None,
        data_source_id=uuid.UUID(kwargs["data_source_id"]) if kwargs.get("data_source_id") else None,
        metadata_discovery_id=uuid.UUID(kwargs["metadata_discovery_id"]) if kwargs.get("metadata_discovery_id") else None,
        organization_id=uuid.UUID(organization_id),
        security_level=kwargs.get("security_level", "public"),
        visibility=kwargs.get("visibility", "public"),
        supply_channels=kwargs.get("supply_channels", []),
        control_protocol=kwargs.get("control_protocol", {}),
        compliance_docs=kwargs.get("compliance_docs", []),
        api_config=kwargs.get("api_config", {}),
        status="draft",
        created_by=uuid.UUID(created_by) if created_by else None,
    )
    db.add(reg)
    await db.commit()
    await db.refresh(reg)

    logger.info(f"Catalog registration created: {reg.name} in org {organization_id}")
    return _registration_to_dict(reg)


async def list_catalog_registrations(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
    catalog_type: Optional[str] = None,
    security_level: Optional[str] = None,
    visibility: Optional[str] = None,
) -> PaginatedResponse:
    """列出数据目录登记"""
    query = select(CatalogRegistration).options(
        selectinload(CatalogRegistration.access_rules)
    )
    if organization_id:
        query = query.where(CatalogRegistration.organization_id == uuid.UUID(organization_id))
    if status:
        query = query.where(CatalogRegistration.status == status)
    if catalog_type:
        query = query.where(CatalogRegistration.catalog_type == catalog_type)
    if security_level:
        query = query.where(CatalogRegistration.security_level == security_level)
    if visibility:
        query = query.where(CatalogRegistration.visibility == visibility)
    query = query.order_by(CatalogRegistration.created_at.desc())

    from app.schemas.catalog_registration import CatalogRegistrationResponse
    result = await paginate_query(db, query, params, CatalogRegistrationResponse)
    return result


async def get_catalog_registration(db: AsyncSession, reg_id: str) -> dict:
    """获取目录登记详情"""
    result = await db.execute(
        select(CatalogRegistration)
        .options(selectinload(CatalogRegistration.access_rules))
        .where(CatalogRegistration.id == uuid.UUID(reg_id))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise DataNotFoundError("目录登记不存在")
    return _registration_to_dict(reg, include_rules=True)


async def update_catalog_registration(db: AsyncSession, reg_id: str, **kwargs) -> dict:
    """更新目录登记"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(reg_id))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise DataNotFoundError("目录登记不存在")

    updatable_fields = [
        "catalog_type", "name", "description", "security_level", "visibility",
        "supply_channels", "control_protocol", "compliance_docs", "api_config", "status",
    ]
    for field in updatable_fields:
        if field in kwargs and kwargs[field] is not None:
            setattr(reg, field, kwargs[field])

    await db.commit()
    await db.refresh(reg)
    logger.info(f"Catalog registration updated: {reg_id}")
    return _registration_to_dict(reg)


async def delete_catalog_registration(db: AsyncSession, reg_id: str) -> bool:
    """删除目录登记"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(reg_id))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise DataNotFoundError("目录登记不存在")
    if reg.status == "published":
        raise DataValidationError("已发布的目录不可删除")

    await db.delete(reg)
    await db.commit()
    logger.info(f"Catalog registration deleted: {reg_id}")
    return True


async def publish_catalog_registration(db: AsyncSession, reg_id: str) -> dict:
    """发布目录登记"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(reg_id))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise DataNotFoundError("目录登记不存在")
    if reg.status == "published":
        raise DataValidationError("目录已发布")

    reg.status = "published"
    await db.commit()
    logger.info(f"Catalog registration published: {reg_id}")
    return {"id": str(reg.id), "status": reg.status}


async def unpublish_catalog_registration(db: AsyncSession, reg_id: str) -> dict:
    """下架目录登记"""
    result = await db.execute(
        select(CatalogRegistration).where(CatalogRegistration.id == uuid.UUID(reg_id))
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise DataNotFoundError("目录登记不存在")

    reg.status = "draft"
    await db.commit()
    logger.info(f"Catalog registration unpublished: {reg_id}")
    return {"id": str(reg.id), "status": reg.status}


# ==================== 管控协议模板 ====================

async def create_control_template(
    db: AsyncSession,
    organization_id: Optional[str] = None,
    created_by: Optional[str] = None,
    **kwargs,
) -> dict:
    """创建管控协议模板"""
    template = ControlTemplate(
        name=kwargs.get("name", ""),
        description=kwargs.get("description"),
        template_content=kwargs.get("template_content", {}),
        organization_id=uuid.UUID(organization_id) if organization_id else None,
        is_system=kwargs.get("is_system", False),
        status="active",
        created_by=uuid.UUID(created_by) if created_by else None,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(f"Control template created: {template.name}")
    return _template_to_dict(template)


async def list_control_templates(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出管控协议模板"""
    query = select(ControlTemplate)
    if organization_id:
        query = query.where(
            (ControlTemplate.organization_id == uuid.UUID(organization_id))
            | (ControlTemplate.is_system == True)
        )
    if status:
        query = query.where(ControlTemplate.status == status)
    query = query.order_by(ControlTemplate.created_at.desc())

    from app.schemas.catalog_registration import ControlTemplateResponse
    result = await paginate_query(db, query, params, ControlTemplateResponse)
    return result


async def get_control_template(db: AsyncSession, template_id: str) -> dict:
    """获取模板详情"""
    result = await db.execute(
        select(ControlTemplate).where(ControlTemplate.id == uuid.UUID(template_id))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise DataNotFoundError("管控协议模板不存在")
    return _template_to_dict(template)


async def update_control_template(db: AsyncSession, template_id: str, **kwargs) -> dict:
    """更新模板"""
    result = await db.execute(
        select(ControlTemplate).where(ControlTemplate.id == uuid.UUID(template_id))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise DataNotFoundError("管控协议模板不存在")
    if template.is_system:
        raise DataValidationError("系统模板不可修改")

    for field in ["name", "description", "template_content", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(template, field, kwargs[field])

    await db.commit()
    await db.refresh(template)
    logger.info(f"Control template updated: {template_id}")
    return _template_to_dict(template)


async def delete_control_template(db: AsyncSession, template_id: str) -> bool:
    """删除模板"""
    result = await db.execute(
        select(ControlTemplate).where(ControlTemplate.id == uuid.UUID(template_id))
    )
    template = result.scalar_one_or_none()
    if not template:
        raise DataNotFoundError("管控协议模板不存在")
    if template.is_system:
        raise DataValidationError("系统模板不可删除")

    await db.delete(template)
    await db.commit()
    logger.info(f"Control template deleted: {template_id}")
    return True


# ==================== 开放范围管控 ====================

async def create_access_scope_rule(
    db: AsyncSession,
    created_by: Optional[str] = None,
    **kwargs,
) -> dict:
    """创建开放范围管控规则"""
    rule = AccessScopeRule(
        catalog_id=uuid.UUID(kwargs["catalog_id"]),
        scope_type=kwargs.get("scope_type", "whitelist"),
        target_type=kwargs.get("target_type", "organization"),
        target_id=uuid.UUID(kwargs["target_id"]),
        reason=kwargs.get("reason"),
        created_by=uuid.UUID(created_by) if created_by else None,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    logger.info(f"Access scope rule created: catalog={kwargs['catalog_id']}")
    return _rule_to_dict(rule)


async def list_access_scope_rules(
    db: AsyncSession,
    params: PaginationParams,
    catalog_id: Optional[str] = None,
    scope_type: Optional[str] = None,
    target_type: Optional[str] = None,
) -> PaginatedResponse:
    """列出开放范围管控规则"""
    query = select(AccessScopeRule)
    if catalog_id:
        query = query.where(AccessScopeRule.catalog_id == uuid.UUID(catalog_id))
    if scope_type:
        query = query.where(AccessScopeRule.scope_type == scope_type)
    if target_type:
        query = query.where(AccessScopeRule.target_type == target_type)
    query = query.order_by(AccessScopeRule.created_at.desc())

    from app.schemas.catalog_registration import AccessScopeRuleResponse
    result = await paginate_query(db, query, params, AccessScopeRuleResponse)
    return result


async def delete_access_scope_rule(db: AsyncSession, rule_id: str) -> bool:
    """删除开放范围管控规则"""
    result = await db.execute(
        select(AccessScopeRule).where(AccessScopeRule.id == uuid.UUID(rule_id))
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise DataNotFoundError("管控规则不存在")

    await db.delete(rule)
    await db.commit()
    logger.info(f"Access scope rule deleted: {rule_id}")
    return True


# ==================== 辅助函数 ====================

def _registration_to_dict(reg: CatalogRegistration, include_rules: bool = False) -> dict:
    """目录登记转字典"""
    data = {
        "id": str(reg.id),
        "catalog_type": reg.catalog_type,
        "name": reg.name,
        "description": reg.description,
        "connector_id": str(reg.connector_id) if reg.connector_id else None,
        "data_source_id": str(reg.data_source_id) if reg.data_source_id else None,
        "metadata_discovery_id": str(reg.metadata_discovery_id) if reg.metadata_discovery_id else None,
        "organization_id": str(reg.organization_id),
        "security_level": reg.security_level,
        "visibility": reg.visibility,
        "supply_channels": reg.supply_channels,
        "control_protocol": reg.control_protocol,
        "compliance_docs": reg.compliance_docs,
        "api_config": reg.api_config,
        "status": reg.status,
        "created_by": str(reg.created_by) if reg.created_by else None,
        "created_at": reg.created_at.isoformat(),
        "updated_at": reg.updated_at.isoformat(),
    }
    if include_rules and hasattr(reg, "access_rules"):
        data["access_rules"] = [_rule_to_dict(r) for r in (reg.access_rules or [])]
    else:
        data["access_rules"] = []
    return data


def _template_to_dict(template: ControlTemplate) -> dict:
    """模板转字典"""
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "template_content": template.template_content,
        "organization_id": str(template.organization_id) if template.organization_id else None,
        "is_system": template.is_system,
        "status": template.status,
        "created_by": str(template.created_by) if template.created_by else None,
        "created_at": template.created_at.isoformat(),
    }


def _rule_to_dict(rule: AccessScopeRule) -> dict:
    """规则转字典"""
    return {
        "id": str(rule.id),
        "catalog_id": str(rule.catalog_id),
        "scope_type": rule.scope_type,
        "target_type": rule.target_type,
        "target_id": str(rule.target_id),
        "reason": rule.reason,
        "created_by": str(rule.created_by) if rule.created_by else None,
        "created_at": rule.created_at.isoformat(),
    }
