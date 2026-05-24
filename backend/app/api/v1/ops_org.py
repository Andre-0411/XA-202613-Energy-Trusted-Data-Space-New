"""
组织管理 API - /api/v1/ops/orgs
组织CRUD + 组织树
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.user import OrganizationCreate, OrganizationResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.services import org_service

router = APIRouter()


@router.get("", response_model=ApiResponse[PaginatedResponse[OrganizationResponse]])
async def list_organizations(
    status: Optional[str] = Query(None, description="状态过滤"),
    parent_id: Optional[str] = Query(None, description="父组织 ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """组织列表"""
    result = await org_service.list_organizations(
        db=db,
        params=pagination,
        status=status,
        parent_id=parent_id,
        keyword=keyword,
    )
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[OrganizationResponse], status_code=201)
async def create_organization(
    request: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建组织"""
    result = await org_service.create_organization(db=db, request=request)
    return ApiResponse(data=result)


@router.get("/{org_id}", response_model=ApiResponse[OrganizationResponse])
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """组织详情"""
    result = await org_service.get_organization(db=db, org_id=org_id)
    return ApiResponse(data=result)


@router.put("/{org_id}", response_model=ApiResponse[OrganizationResponse])
async def update_organization(
    org_id: str,
    request: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新组织"""
    result = await org_service.update_organization(
        db=db, org_id=org_id, request=request,
    )
    return ApiResponse(data=result)


@router.get("/{org_id}/tree", response_model=ApiResponse)
async def get_organization_tree(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取组织树（递归子组织）"""
    result = await org_service.get_organization_tree(db=db, org_id=org_id)
    return ApiResponse(data=result)
