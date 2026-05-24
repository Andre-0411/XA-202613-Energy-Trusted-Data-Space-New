"""
NFT确权 API — /api/v1/blockchain/nft
NFT 铸造 / 查询 / 转移 / 授权管理 / 统计
"""
import uuid
import logging
from typing import Optional

from pydantic import BaseModel, Field

class NftMintRequest(BaseModel):
    asset_id: str = Field(..., description="资产ID")
    name: str = Field(..., description="NFT名称")
    description: str = Field(default="", description="NFT描述")
    metadata_uri: str = Field(default="", description="元数据URI")
    creator_did: str = Field(default="", description="创建者DID")


from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.blockchain import NftAsset
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.blockchain import (
    NftMintRequest, NftTransferRequest, NftResponse,
    NftAuthorizeRequest, NftRevokeRequest, NftAuthorization,
    NftStatsResponse,
)
from app.utils.deps import get_current_user
from app.services.blockchain_nft_service import (
    mint_nft, get_nft_by_token_id, get_nfts_by_owner, transfer_nft,
    authorize_nft, revoke_nft_authorization, get_nft_authorizations, get_nft_stats,
)
from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import BlockchainError, DataNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/mint", response_model=ApiResponse[NftResponse])
async def 铸造nft(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """铸造NFT — 前端发送 {asset_id, metadata_uri}"""
    user_did: str = user.get("user_id", "")
    asset_id = request.asset_id
    metadata_uri = request.metadata_uri

    if not asset_id or not metadata_uri:
        return ApiResponse(code=2003, message="asset_id 和 metadata_uri 为必填项", data=None)

    # 生成确权证据哈希
    evidence_hash: str = gmssl_adapter.sm3_hash(f"{asset_id}:{user_did}:{metadata_uri}")

    # 构造 NftMintRequest
    mint_request = NftMintRequest(
        asset_id=asset_id,
        category="dataset",
        classification_level=1,
        evidence_hash=evidence_hash,
        certificate_url=metadata_uri,
    )

    try:
        result = await mint_nft(db=db, request=mint_request, user_did=user_did)
        return ApiResponse(data=result)
    except BlockchainError as e:
        logger.error(f"NFT mint failed: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)


@router.get("/stats", response_model=ApiResponse[NftStatsResponse])
async def nft统计(
    owner: Optional[str] = Query(None, description="所有者 DID（可选）"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """NFT 资产统计 — 总量、今日铸造、活跃授权、分类分布"""
    try:
        result = await get_nft_stats(db=db, owner_did=owner)
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"NFT stats failed: {e}")
        return ApiResponse(code=4000, message=f"NFT 统计失败: {e}", data=None)


@router.get("/{token_id}", response_model=ApiResponse[NftResponse])
async def nft详情(
    token_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """NFT详情 — 按 token_id 查询"""
    try:
        result = await get_nft_by_token_id(db=db, token_id=token_id)
        return ApiResponse(data=result)
    except Exception as e:
        logger.warning(f"NFT not found: {e}")
        return ApiResponse(code=2001, message="NFT 未找到", data=None)


@router.post("/{token_id}/authorize", response_model=ApiResponse[NftAuthorization])
async def 授权nft(
    token_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """NFT 授权 — 授权其他用户使用 NFT，前端发送 {authorized_did, permission_type?, duration_seconds?}"""
    user_did: str = user.get("user_id", "")
    authorized_did: str = body.get("authorized_did", "")

    if not authorized_did:
        return ApiResponse(code=2003, message="authorized_did 为必填项", data=None)

    auth_request = NftAuthorizeRequest(
        authorized_did=authorized_did,
        permission_type=body.get("permission_type", "use"),
        duration_seconds=body.get("duration_seconds"),
    )

    try:
        result = await authorize_nft(
            db=db, token_id=token_id, request=auth_request, owner_did=user_did,
        )
        return ApiResponse(data=result)
    except DataNotFoundError:
        return ApiResponse(code=2001, message="NFT 未找到", data=None)
    except BlockchainError as e:
        logger.error(f"NFT authorize failed: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"NFT authorize failed: {e}")
        return ApiResponse(code=4000, message=f"授权失败: {e}", data=None)


@router.post("/{token_id}/revoke", response_model=ApiResponse)
async def 撤销授权(
    token_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """撤销 NFT 授权 — 前端发送 {authorized_did}"""
    user_did: str = user.get("user_id", "")
    authorized_did: str = body.get("authorized_did", "")

    if not authorized_did:
        return ApiResponse(code=2003, message="authorized_did 为必填项", data=None)

    revoke_request = NftRevokeRequest(authorized_did=authorized_did)

    try:
        result = await revoke_nft_authorization(
            db=db, token_id=token_id, request=revoke_request, owner_did=user_did,
        )
        return ApiResponse(data=result)
    except DataNotFoundError:
        return ApiResponse(code=2001, message="NFT 未找到", data=None)
    except BlockchainError as e:
        logger.error(f"NFT revoke failed: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"NFT revoke failed: {e}")
        return ApiResponse(code=4000, message=f"撤销授权失败: {e}", data=None)


@router.get("/{token_id}/authorizations", response_model=ApiResponse[list[NftAuthorization]])
async def 查询授权(
    token_id: str,
    user: dict = Depends(get_current_user),
):
    """查询 NFT 的授权列表"""
    try:
        result = await get_nft_authorizations(token_id=token_id)
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"NFT authorizations query failed: {e}")
        return ApiResponse(code=4000, message=f"授权查询失败: {e}", data=None)


@router.get("/", response_model=ApiResponse[PaginatedResponse[NftResponse]])
async def nft列表(
    owner: Optional[str] = Query(None, alias="owner", description="所有者DID"),
    asset_id: Optional[str] = Query(None, description="关联资产ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """NFT列表 — 按 owner / asset_id 筛选，分页"""
    if owner:
        nfts: list[NftResponse] = await get_nfts_by_owner(db=db, owner_did=owner)
        # 可选 asset_id 过滤
        if asset_id:
            nfts = [n for n in nfts if n.asset_id == asset_id]
    elif asset_id:
        result = await db.execute(
            select(NftAsset).where(NftAsset.asset_id == uuid.UUID(asset_id))
        )
        nfts = [NftResponse.model_validate(n) for n in result.scalars().all()]
    else:
        nfts = []

    # 手动分页
    total: int = len(nfts)
    total_pages: int = (total + page_size - 1) // page_size if page_size > 0 else 0
    start: int = (page - 1) * page_size
    end: int = start + page_size
    page_items = nfts[start:end]

    return ApiResponse(
        data=PaginatedResponse(
            items=page_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.post("/{token_id}/transfer", response_model=ApiResponse[NftResponse])
async def 转移nft(
    token_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """转移NFT — 前端发送 {to, signature?}"""
    user_did: str = user.get("user_id", "")
    to_did: str = body.get("to", "")
    signature: str = body.get("signature", "")

    if not to_did:
        return ApiResponse(code=2003, message="接收方 to 为必填项", data=None)

    transfer_request = NftTransferRequest(to_did=to_did, signature=signature)

    try:
        result = await transfer_nft(
            db=db,
            token_id=token_id,
            request=transfer_request,
            current_owner_did=user_did,
        )
        return ApiResponse(data=result)
    except BlockchainError as e:
        logger.error(f"NFT transfer failed: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"NFT transfer failed: {e}")
        return ApiResponse(code=4000, message=f"转移失败: {e}", data=None)
