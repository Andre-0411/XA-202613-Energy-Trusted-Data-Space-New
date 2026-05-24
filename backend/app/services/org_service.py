"""
组织管理服务
组织CRUD + 组织树构建（递归parent_id） + 成员查询 + 组织统计（用户数/资产数）
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Organization
from app.models.data_asset import DataAsset
from app.schemas.user import OrganizationCreate, OrganizationResponse
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    DataNotFoundError, DataAlreadyExistsError, DataValidationError, OpsError,
)

logger = logging.getLogger(__name__)

# 组织状态
VALID_ORG_STATUSES = {"active", "inactive", "suspended"}

# 最大层级深度
MAX_ORG_LEVEL = 4


async def list_organizations(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    parent_id: Optional[str] = None,
    keyword: Optional[str] = None,
) -> PaginatedResponse:
    """
    组织列表（分页 + 过滤）

    Args:
        db: 数据库会话
        params: 分页参数
        status: 状态过滤
        parent_id: 父组织 ID 过滤
        keyword: 关键词搜索（name/code）

    Returns:
        分页组织列表
    """
    query = select(Organization)

    if status:
        query = query.where(Organization.status == status)
    if parent_id:
        query = query.where(Organization.parent_id == uuid.UUID(parent_id))
    if keyword:
        keyword_pattern = f"%{keyword}%"
        query = query.where(
            (Organization.name.ilike(keyword_pattern))
            | (Organization.code.ilike(keyword_pattern))
        )

    result = await paginate_query(db, query, params, OrganizationResponse)
    return result


async def create_organization(
    db: AsyncSession,
    request: OrganizationCreate,
) -> OrganizationResponse:
    """
    创建组织

    Args:
        db: 数据库会话
        request: 创建请求

    Returns:
        创建后的组织信息
    """
    # 检查名称唯一性
    existing_name = await db.execute(
        select(Organization).where(Organization.name == request.name)
    )
    if existing_name.scalar_one_or_none():
        raise DataAlreadyExistsError(message=f"组织名称已存在: {request.name}")

    # 检查编码唯一性
    existing_code = await db.execute(
        select(Organization).where(Organization.code == request.code)
    )
    if existing_code.scalar_one_or_none():
        raise DataAlreadyExistsError(message=f"组织编码已存在: {request.code}")

    # 验证层级
    level = request.level
    if request.parent_id:
        parent_result = await db.execute(
            select(Organization).where(
                Organization.id == uuid.UUID(request.parent_id)
            )
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise DataNotFoundError(message=f"父组织不存在: {request.parent_id}")
        level = parent.level + 1

    if level > MAX_ORG_LEVEL:
        raise DataValidationError(
            message=f"组织层级不能超过 {MAX_ORG_LEVEL} 级",
            data={"max_level": MAX_ORG_LEVEL},
        )

    # 创建组织
    org = Organization(
        name=request.name,
        code=request.code,
        parent_id=uuid.UUID(request.parent_id) if request.parent_id else None,
        level=level,
        status="active",
        did=request.did,
        metadata_=request.metadata or {},
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)

    logger.info(f"组织创建成功: {org.name} (ID: {org.id}), 层级: {level}")
    return OrganizationResponse.model_validate(org)


async def get_organization(
    db: AsyncSession,
    org_id: str,
) -> OrganizationResponse:
    """
    获取组织详情

    Args:
        db: 数据库会话
        org_id: 组织 ID

    Returns:
        组织信息
    """
    result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    org = result.scalar_one_or_none()
    if not org:
        raise DataNotFoundError(message=f"组织不存在: {org_id}")
    return OrganizationResponse.model_validate(org)


async def update_organization(
    db: AsyncSession,
    org_id: str,
    request: OrganizationCreate,
) -> OrganizationResponse:
    """
    更新组织信息

    Args:
        db: 数据库会话
        org_id: 组织 ID
        request: 更新请求

    Returns:
        更新后的组织信息
    """
    result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    org = result.scalar_one_or_none()
    if not org:
        raise DataNotFoundError(message=f"组织不存在: {org_id}")

    # 检查名称唯一性
    if request.name != org.name:
        existing = await db.execute(
            select(Organization).where(Organization.name == request.name)
        )
        if existing.scalar_one_or_none():
            raise DataAlreadyExistsError(message=f"组织名称已存在: {request.name}")

    # 检查编码唯一性
    if request.code != org.code:
        existing = await db.execute(
            select(Organization).where(Organization.code == request.code)
        )
        if existing.scalar_one_or_none():
            raise DataAlreadyExistsError(message=f"组织编码已存在: {request.code}")

    # 更新字段
    org.name = request.name
    org.code = request.code
    org.parent_id = uuid.UUID(request.parent_id) if request.parent_id else None
    org.level = request.level
    org.did = request.did
    org.metadata_ = request.metadata or {}

    await db.commit()
    await db.refresh(org)

    logger.info(f"组织更新成功: {org.name} (ID: {org.id})")
    return OrganizationResponse.model_validate(org)


async def get_organization_tree(
    db: AsyncSession,
    org_id: str,
) -> dict:
    """
    获取组织树（递归构建子组织树形结构）

    Args:
        db: 数据库会话
        org_id: 根组织 ID

    Returns:
        组织树形结构
    """
    # 验证根组织存在
    root_result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    root = root_result.scalar_one_or_none()
    if not root:
        raise DataNotFoundError(message=f"组织不存在: {org_id}")

    # 查询所有组织
    all_orgs_result = await db.execute(select(Organization))
    all_orgs = all_orgs_result.scalars().all()

    # 构建 ID → 组织映射
    org_map: dict[str, dict] = {}
    for org in all_orgs:
        org_map[str(org.id)] = {
            "id": str(org.id),
            "name": org.name,
            "code": org.code,
            "parent_id": str(org.parent_id) if org.parent_id else None,
            "level": org.level,
            "status": org.status,
            "did": org.did,
            "children": [],
        }

    # 构建树形结构
    root_node = None
    for org_id_key, org_node in org_map.items():
        parent_id = org_node["parent_id"]
        if parent_id and parent_id in org_map:
            org_map[parent_id]["children"].append(org_node)
        if org_id_key == str(root.id):
            root_node = org_node

    # 统计根组织下总用户数和资产数
    user_count = await _count_org_users(db, root.id)
    asset_count = await _count_org_assets(db, root.id)

    if root_node:
        root_node["user_count"] = user_count
        root_node["asset_count"] = asset_count

    return root_node or {}


async def get_org_members(
    db: AsyncSession,
    org_id: str,
    params: PaginationParams,
) -> PaginatedResponse:
    """
    查询组织成员

    Args:
        db: 数据库会话
        org_id: 组织 ID
        params: 分页参数

    Returns:
        分页用户列表
    """
    from app.schemas.user import UserResponse

    # 验证组织存在
    org_result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    if not org_result.scalar_one_or_none():
        raise DataNotFoundError(message=f"组织不存在: {org_id}")

    query = select(User).where(User.organization_id == uuid.UUID(org_id))
    result = await paginate_query(db, query, params, UserResponse)
    return result


async def get_org_statistics(
    db: AsyncSession,
    org_id: str,
) -> dict:
    """
    获取组织统计信息（用户数/资产数）

    Args:
        db: 数据库会话
        org_id: 组织 ID

    Returns:
        组织统计数据
    """
    # 验证组织存在
    org_result = await db.execute(
        select(Organization).where(Organization.id == uuid.UUID(org_id))
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise DataNotFoundError(message=f"组织不存在: {org_id}")

    user_count = await _count_org_users(db, org.id)
    asset_count = await _count_org_assets(db, org.id)

    # 统计子组织数
    child_count_result = await db.execute(
        select(func.count()).select_from(Organization).where(
            Organization.parent_id == org.id
        )
    )
    child_count = child_count_result.scalar() or 0

    # 统计各角色用户数
    role_counts = {}
    for role in ["admin", "data_admin", "user", "auditor"]:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                and_(
                    User.organization_id == org.id,
                    User.role == role,
                )
            )
        )
        role_counts[role] = count_result.scalar() or 0

    return {
        "org_id": str(org.id),
        "org_name": org.name,
        "org_code": org.code,
        "user_count": user_count,
        "asset_count": asset_count,
        "child_org_count": child_count,
        "role_distribution": role_counts,
        "status": org.status,
    }


async def _count_org_users(db: AsyncSession, org_id: uuid.UUID) -> int:
    """统计组织下用户数"""
    result = await db.execute(
        select(func.count()).select_from(User).where(
            User.organization_id == org_id
        )
    )
    return result.scalar() or 0


async def _count_org_assets(db: AsyncSession, org_id: uuid.UUID) -> int:
    """统计组织下资产数"""
    result = await db.execute(
        select(func.count()).select_from(DataAsset).where(
            DataAsset.owner_org_id == org_id
        )
    )
    return result.scalar() or 0
