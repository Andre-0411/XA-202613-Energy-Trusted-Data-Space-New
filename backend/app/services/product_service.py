"""
数据产品服务
产品项目/数据产品/产品验收管理
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import (
    ProductProject, ProjectMember, DataProduct, ProductAcceptance,
)
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError

logger = logging.getLogger(__name__)


# ==================== 产品项目 ====================

async def create_project(
    db: AsyncSession,
    name: str,
    project_type: str,
    organization_id: str,
    owner_id: str,
    description: Optional[str] = None,
    data_sources: Optional[list] = None,
) -> dict:
    """创建产品项目"""
    project = ProductProject(
        name=name,
        description=description,
        project_type=project_type,
        organization_id=uuid.UUID(organization_id),
        owner_id=uuid.UUID(owner_id),
        data_sources=data_sources or [],
        status="active",
    )
    db.add(project)
    await db.flush()

    # 自动添加 owner 为项目成员
    owner_member = ProjectMember(
        project_id=project.id,
        user_id=uuid.UUID(owner_id),
        role="owner",
    )
    db.add(owner_member)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Product project created: {name} by {owner_id}")
    return _project_to_dict(project)


async def update_project(db: AsyncSession, project_id: str, **kwargs) -> dict:
    """更新产品项目"""
    result = await db.execute(
        select(ProductProject).where(ProductProject.id == uuid.UUID(project_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise DataNotFoundError("产品项目不存在")

    for field in ["name", "description", "project_type", "data_sources", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(project, field, kwargs[field])

    await db.commit()
    await db.refresh(project)
    logger.info(f"Product project updated: {project_id}")
    return _project_to_dict(project)


async def get_project(db: AsyncSession, project_id: str) -> dict:
    """获取产品项目详情"""
    result = await db.execute(
        select(ProductProject).where(ProductProject.id == uuid.UUID(project_id))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise DataNotFoundError("产品项目不存在")
    return _project_to_dict(project)


async def list_projects(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    project_type: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出产品项目"""
    query = select(ProductProject)
    if organization_id:
        query = query.where(ProductProject.organization_id == uuid.UUID(organization_id))
    if project_type:
        query = query.where(ProductProject.project_type == project_type)
    if status:
        query = query.where(ProductProject.status == status)
    query = query.order_by(ProductProject.created_at.desc())

    from app.schemas.product import ProductProjectResponse
    result = await paginate_query(db, query, params, ProductProjectResponse)
    return result


async def add_project_member(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    role: str = "member",
) -> dict:
    """添加项目成员"""
    existing = await db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == uuid.UUID(project_id),
                ProjectMember.user_id == uuid.UUID(user_id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("用户已是项目成员")

    member = ProjectMember(
        project_id=uuid.UUID(project_id),
        user_id=uuid.UUID(user_id),
        role=role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    logger.info(f"Project member added: project={project_id}, user={user_id}")
    return {
        "id": str(member.id),
        "project_id": str(member.project_id),
        "user_id": str(member.user_id),
        "role": member.role,
        "joined_at": member.joined_at.isoformat(),
    }


async def remove_project_member(db: AsyncSession, project_id: str, user_id: str) -> bool:
    """移除项目成员"""
    result = await db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == uuid.UUID(project_id),
                ProjectMember.user_id == uuid.UUID(user_id),
            )
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise DataNotFoundError("项目成员不存在")
    if member.role == "owner":
        raise DataValidationError("不能移除项目所有者")

    await db.delete(member)
    await db.commit()
    logger.info(f"Project member removed: project={project_id}, user={user_id}")
    return True


async def list_project_members(
    db: AsyncSession,
    params: PaginationParams,
    project_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出项目成员"""
    query = select(ProjectMember)
    if project_id:
        query = query.where(ProjectMember.project_id == uuid.UUID(project_id))
    query = query.order_by(ProjectMember.joined_at.desc())

    from app.schemas.product import ProjectMemberResponse
    result = await paginate_query(db, query, params, ProjectMemberResponse)
    return result


# ==================== 数据产品 ====================

async def create_product(
    db: AsyncSession,
    name: str,
    product_type: str,
    organization_id: str,
    owner_id: str,
    project_id: Optional[str] = None,
    description: Optional[str] = None,
    compute_engine: Optional[str] = None,
    version: str = "1.0.0",
    technical_spec: Optional[dict] = None,
    pricing: Optional[dict] = None,
    delivery_config: Optional[dict] = None,
    compliance_docs: Optional[list] = None,
    control_protocol: Optional[dict] = None,
) -> dict:
    """创建数据产品"""
    product = DataProduct(
        project_id=uuid.UUID(project_id) if project_id else None,
        name=name,
        description=description,
        product_type=product_type,
        compute_engine=compute_engine,
        version=version,
        organization_id=uuid.UUID(organization_id),
        owner_id=uuid.UUID(owner_id),
        technical_spec=technical_spec or {},
        pricing=pricing or {},
        delivery_config=delivery_config or {},
        compliance_docs=compliance_docs or [],
        control_protocol=control_protocol or {},
        status="development",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    logger.info(f"Data product created: {name} ({product_type})")
    return _product_to_dict(product)


async def update_product(db: AsyncSession, product_id: str, **kwargs) -> dict:
    """更新数据产品"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    allowed_fields = [
        "name", "description", "product_type", "compute_engine", "version",
        "technical_spec", "pricing", "delivery_config", "compliance_docs",
        "control_protocol", "status",
    ]
    for field in allowed_fields:
        if field in kwargs and kwargs[field] is not None:
            setattr(product, field, kwargs[field])

    await db.commit()
    await db.refresh(product)
    logger.info(f"Data product updated: {product_id}")
    return _product_to_dict(product)


async def get_product(db: AsyncSession, product_id: str) -> dict:
    """获取数据产品详情"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")
    return _product_to_dict(product)


async def list_products(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    product_type: Optional[str] = None,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    keyword: Optional[str] = None,
) -> PaginatedResponse:
    """列出数据产品"""
    query = select(DataProduct)
    if organization_id:
        query = query.where(DataProduct.organization_id == uuid.UUID(organization_id))
    if product_type:
        query = query.where(DataProduct.product_type == product_type)
    if status:
        query = query.where(DataProduct.status == status)
    if project_id:
        query = query.where(DataProduct.project_id == uuid.UUID(project_id))
    if keyword:
        query = query.where(DataProduct.name.ilike(f"%{keyword}%"))
    query = query.order_by(DataProduct.created_at.desc())

    from app.schemas.product import DataProductResponse
    result = await paginate_query(db, query, params, DataProductResponse)
    return result


async def delete_product(db: AsyncSession, product_id: str) -> bool:
    """删除数据产品（软删除）"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    product.status = "deleted"
    await db.commit()
    logger.info(f"Data product deleted: {product_id}")
    return True


# ==================== 产品验收 ====================

async def create_acceptance(
    db: AsyncSession,
    product_id: str,
    acceptor_id: str,
    test_result: Optional[dict] = None,
    comment: Optional[str] = None,
) -> dict:
    """创建产品验收"""
    result = await db.execute(
        select(DataProduct).where(DataProduct.id == uuid.UUID(product_id))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise DataNotFoundError("数据产品不存在")

    acceptance = ProductAcceptance(
        product_id=uuid.UUID(product_id),
        acceptor_id=uuid.UUID(acceptor_id),
        test_result=test_result or {},
        status="pending",
        comment=comment,
    )
    db.add(acceptance)
    await db.commit()
    await db.refresh(acceptance)

    logger.info(f"Product acceptance created: product={product_id}")
    return _acceptance_to_dict(acceptance)


async def review_acceptance(
    db: AsyncSession,
    acceptance_id: str,
    status: str,
    comment: Optional[str] = None,
) -> dict:
    """审核产品验收"""
    result = await db.execute(
        select(ProductAcceptance).where(ProductAcceptance.id == uuid.UUID(acceptance_id))
    )
    acceptance = result.scalar_one_or_none()
    if not acceptance:
        raise DataNotFoundError("验收记录不存在")

    acceptance.status = status
    if comment:
        acceptance.comment = comment
    if status == "accepted":
        acceptance.accepted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(acceptance)
    logger.info(f"Product acceptance {acceptance_id} reviewed: {status}")
    return _acceptance_to_dict(acceptance)


async def list_acceptances(
    db: AsyncSession,
    params: PaginationParams,
    product_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出产品验收记录"""
    query = select(ProductAcceptance)
    if product_id:
        query = query.where(ProductAcceptance.product_id == uuid.UUID(product_id))
    if status:
        query = query.where(ProductAcceptance.status == status)
    query = query.order_by(ProductAcceptance.created_at.desc())

    from app.schemas.product import ProductAcceptanceResponse
    result = await paginate_query(db, query, params, ProductAcceptanceResponse)
    return result


# ==================== Helpers ====================

def _project_to_dict(project: ProductProject) -> dict:
    """项目转字典"""
    members = []
    for m in (project.members or []):
        members.append({
            "id": str(m.id),
            "project_id": str(m.project_id),
            "user_id": str(m.user_id),
            "role": m.role,
            "joined_at": m.joined_at.isoformat(),
        })
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "project_type": project.project_type,
        "organization_id": str(project.organization_id),
        "owner_id": str(project.owner_id),
        "data_sources": project.data_sources or [],
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "members": members,
    }


def _product_to_dict(product: DataProduct) -> dict:
    """产品转字典"""
    return {
        "id": str(product.id),
        "project_id": str(product.project_id) if product.project_id else None,
        "name": product.name,
        "description": product.description,
        "product_type": product.product_type,
        "compute_engine": product.compute_engine,
        "version": product.version,
        "organization_id": str(product.organization_id),
        "owner_id": str(product.owner_id),
        "technical_spec": product.technical_spec or {},
        "pricing": product.pricing or {},
        "delivery_config": product.delivery_config or {},
        "compliance_docs": product.compliance_docs or [],
        "control_protocol": product.control_protocol or {},
        "status": product.status,
        "published_at": product.published_at.isoformat() if product.published_at else None,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
    }


def _acceptance_to_dict(a: ProductAcceptance) -> dict:
    """验收转字典"""
    return {
        "id": str(a.id),
        "product_id": str(a.product_id),
        "acceptor_id": str(a.acceptor_id),
        "test_result": a.test_result or {},
        "status": a.status,
        "comment": a.comment,
        "accepted_at": a.accepted_at.isoformat() if a.accepted_at else None,
        "created_at": a.created_at.isoformat(),
    }
