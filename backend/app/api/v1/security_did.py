"""
DID 身份 API - /api/v1/security/did
创建DID + 解析DID Document + 更新DID Document + 停用DID
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.security import DidCreate
from app.utils.deps import get_current_user
from app.services import did_service

router = APIRouter()


class DidUpdateRequest(BaseModel):
    """更新 DID Document 请求"""
    service_endpoints: Optional[list[dict]] = Field(default=None, description="服务端点列表")
    add_authentication: Optional[list[dict]] = Field(default=None, description="添加的认证方法")
    remove_authentication: Optional[list[str]] = Field(default=None, description="移除的认证方法 ID")


@router.post("/create", response_model=ApiResponse)
async def create_did(
    request: DidCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建DID（生成 did:fisco:{address} 格式，关联 SM2 公钥）"""
    result = await did_service.create_did(
        db=db,
        request=request,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.get("/{did}", response_model=ApiResponse)
async def resolve_did(
    did: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """解析DID Document（返回公钥、服务端点、认证方法）"""
    result = await did_service.resolve_did(db=db, did=did)
    return ApiResponse(data=result)


@router.put("/{did}", response_model=ApiResponse)
async def update_did_document(
    did: str,
    request: DidUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """更新DID Document（添加/移除认证方法、服务端点）"""
    result = await did_service.update_did_document(
        db=db,
        did=did,
        service_endpoints=request.service_endpoints,
        add_authentication=request.add_authentication,
        remove_authentication=request.remove_authentication,
    )
    return ApiResponse(data=result)


@router.post("/{did}/deactivate", response_model=ApiResponse)
async def deactivate_did(
    did: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """停用DID（标记为deactivated，不可逆）"""
    result = await did_service.deactivate_did(
        db=db,
        did=did,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)
