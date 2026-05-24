"""
用户管理 API - /api/v1/ops/users
用户CRUD + 批量导入 + 密码重置
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.utils.deps import require_roles, get_pagination_params, PaginationParams
from app.services import user_service

router = APIRouter()


class ResetPasswordBody(BaseModel):
    """重置密码请求体"""
    new_password: Optional[str] = Field(default=None, description="新密码（留空则自动生成）", min_length=6)


@router.get("", response_model=ApiResponse[PaginatedResponse[UserResponse]])
async def list_users(
    role: Optional[str] = Query(None, description="角色: admin/data_admin/user/auditor"),
    status: Optional[str] = Query(None, description="状态: active/inactive/locked"),
    organization_id: Optional[str] = Query(None, description="组织 ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles("admin")),
):
    """用户列表"""
    result = await user_service.list_users(
        db=db,
        params=pagination,
        role=role,
        status=status,
        organization_id=organization_id,
        keyword=keyword,
    )
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[UserResponse], status_code=201)
async def create_user(
    request: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles("admin")),
):
    """创建用户"""
    result = await user_service.create_user(
        db=db,
        request=request,
        created_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles("admin")),
):
    """用户详情"""
    result = await user_service.get_user(db=db, user_id=user_id)
    return ApiResponse(data=result)


@router.put("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(
    user_id: str,
    request: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles("admin")),
):
    """更新用户"""
    result = await user_service.update_user(
        db=db, user_id=user_id, request=request,
    )
    return ApiResponse(data=result)


@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles("admin")),
):
    """删除用户（软删除）"""
    result = await user_service.delete_user(db=db, user_id=user_id)
    return ApiResponse(data=result)


@router.post("/import", response_model=ApiResponse)
async def batch_import_users(
    file: UploadFile = File(..., description="Excel 文件"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles("admin")),
):
    """批量 Excel 导入用户"""
    file_content = await file.read()
    result = await user_service.batch_import_users(
        db=db,
        file_content=file_content,
        filename=file.filename or "users.xlsx",
        created_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/{user_id}/reset-password", response_model=ApiResponse)
async def reset_password(
    user_id: str,
    request: ResetPasswordBody = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles("admin")),
):
    """重置密码（仅管理员可操作，新密码通过请求体传递）"""
    new_password = request.new_password if request else None
    result = await user_service.reset_password(
        db=db,
        user_id=user_id,
        new_password=new_password,
        reset_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)
