"""
角色管理服务
自定义角色 / 用户角色分配
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certification import CustomRole, UserRole
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError, PermissionDeniedError

logger = logging.getLogger(__name__)


async def create_custom_role(
    db: AsyncSession,
    organization_id: str,
    name: str,
    description: Optional[str] = None,
    permissions: Optional[dict] = None,
    created_by: Optional[str] = None,
) -> dict:
    """创建自定义角色"""
    existing = await db.execute(
        select(CustomRole).where(
            and_(
                CustomRole.organization_id == uuid.UUID(organization_id),
                CustomRole.name == name,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError(f"角色名称 '{name}' 已存在")

    role = CustomRole(
        name=name,
        description=description,
        organization_id=uuid.UUID(organization_id),
        permissions=permissions or {},
        is_system=False,
        status="active",
        created_by=uuid.UUID(created_by) if created_by else None,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    logger.info(f"Custom role created: {name} in org {organization_id}")
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "organization_id": str(role.organization_id),
        "permissions": role.permissions,
        "is_system": role.is_system,
        "status": role.status,
        "created_by": str(role.created_by) if role.created_by else None,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
    }


async def update_custom_role(db: AsyncSession, role_id: str, **kwargs) -> dict:
    """更新角色"""
    result = await db.execute(select(CustomRole).where(CustomRole.id == uuid.UUID(role_id)))
    role = result.scalar_one_or_none()
    if not role:
        raise DataNotFoundError("角色不存在")
    if role.is_system:
        raise PermissionDeniedError("系统角色不可修改")

    for field in ["name", "description", "permissions", "status"]:
        if field in kwargs and kwargs[field] is not None:
            setattr(role, field, kwargs[field])

    await db.commit()
    await db.refresh(role)
    logger.info(f"Role updated: {role_id}")
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "organization_id": str(role.organization_id),
        "permissions": role.permissions,
        "is_system": role.is_system,
        "status": role.status,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
    }


async def delete_custom_role(db: AsyncSession, role_id: str) -> bool:
    """删除角色（软删除）"""
    result = await db.execute(select(CustomRole).where(CustomRole.id == uuid.UUID(role_id)))
    role = result.scalar_one_or_none()
    if not role:
        raise DataNotFoundError("角色不存在")
    if role.is_system:
        raise PermissionDeniedError("系统角色不可删除")

    role.status = "deleted"
    await db.commit()
    logger.info(f"Role deleted: {role_id}")
    return True


async def get_role_detail(db: AsyncSession, role_id: str) -> dict:
    """获取角色详情"""
    result = await db.execute(select(CustomRole).where(CustomRole.id == uuid.UUID(role_id)))
    role = result.scalar_one_or_none()
    if not role:
        raise DataNotFoundError("角色不存在")

    # 查看已分配用户数
    users_result = await db.execute(
        select(UserRole).where(UserRole.role_id == uuid.UUID(role_id))
    )
    assigned_users = users_result.scalars().all()

    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "organization_id": str(role.organization_id),
        "permissions": role.permissions,
        "is_system": role.is_system,
        "status": role.status,
        "created_by": str(role.created_by) if role.created_by else None,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
        "assigned_user_count": len(assigned_users),
    }


async def list_roles(
    db: AsyncSession,
    params: PaginationParams,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出自定义角色"""
    query = select(CustomRole)
    if organization_id:
        query = query.where(CustomRole.organization_id == uuid.UUID(organization_id))
    if status:
        query = query.where(CustomRole.status == status)
    query = query.order_by(CustomRole.created_at.desc())

    from app.schemas.registration import CustomRoleResponse
    result = await paginate_query(db, query, params, CustomRoleResponse)
    return result


async def assign_role_to_user(
    db: AsyncSession,
    user_id: str,
    role_id: str,
    assigned_by: Optional[str] = None,
) -> dict:
    """分配角色给用户"""
    existing = await db.execute(
        select(UserRole).where(
            and_(
                UserRole.user_id == uuid.UUID(user_id),
                UserRole.role_id == uuid.UUID(role_id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("用户已拥有该角色")

    user_role = UserRole(
        user_id=uuid.UUID(user_id),
        role_id=uuid.UUID(role_id),
        assigned_by=uuid.UUID(assigned_by) if assigned_by else None,
    )
    db.add(user_role)
    await db.commit()
    await db.refresh(user_role)

    logger.info(f"User role assigned: user={user_id}, role={role_id}")
    return {
        "id": str(user_role.id),
        "user_id": str(user_role.user_id),
        "role_id": str(user_role.role_id),
        "assigned_by": str(user_role.assigned_by) if user_role.assigned_by else None,
        "assigned_at": user_role.assigned_at.isoformat(),
    }


async def revoke_role_from_user(db: AsyncSession, user_id: str, role_id: str) -> bool:
    """撤销用户角色"""
    result = await db.execute(
        select(UserRole).where(
            and_(
                UserRole.user_id == uuid.UUID(user_id),
                UserRole.role_id == uuid.UUID(role_id),
            )
        )
    )
    user_role = result.scalar_one_or_none()
    if not user_role:
        raise DataNotFoundError("用户角色关联不存在")

    await db.delete(user_role)
    await db.commit()
    logger.info(f"User role revoked: user={user_id}, role={role_id}")
    return True


async def list_user_roles(
    db: AsyncSession,
    params: PaginationParams,
    user_id: Optional[str] = None,
    role_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出用户角色"""
    query = select(UserRole)
    if user_id:
        query = query.where(UserRole.user_id == uuid.UUID(user_id))
    if role_id:
        query = query.where(UserRole.role_id == uuid.UUID(role_id))
    query = query.order_by(UserRole.assigned_at.desc())

    from app.schemas.registration import UserRoleResponse
    result = await paginate_query(db, query, params, UserRoleResponse)
    return result
