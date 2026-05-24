"""
DID 身份 API - /api/v1/security/did
创建DID + 解析DID Document + 更新DID Document + 停用DID
支持 did:tds 和 did:fisco 两种方法
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


class FiscoDidCreateRequest(BaseModel):
    """创建 did:fisco 请求"""
    public_key: str = Field(description="SM2 公钥（十六进制）")
    controller: Optional[str] = Field(default=None, description="控制者 DID")
    chain_id: Optional[str] = Field(default=None, description="FISCO BCOS 链 ID")
    node_url: Optional[str] = Field(default=None, description="FISCO BCOS 节点 URL")


@router.post("/create", response_model=ApiResponse)
async def create_did(
    request: DidCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """创建DID（生成 did:tds:{hash} 格式，关联 SM2 公钥）"""
    result = await did_service.create_did(
        db=db,
        request=request,
        user_id=user.get("user_id", ""),
    )
    return ApiResponse(data=result)


@router.post("/create-fisco", response_model=ApiResponse)
async def create_fisco_did(
    request: FiscoDidCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    创建 did:fisco 方法的 DID

    符合 W3C DID v1.0 规范，使用 FISCO BCOS 区块链地址作为标识
    格式: did:fisco:0x{40位十六进制地址}
    """
    result = await did_service.create_fisco_did(
        db=db,
        public_key=request.public_key,
        controller=request.controller,
        chain_id=request.chain_id,
        node_url=request.node_url,
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
