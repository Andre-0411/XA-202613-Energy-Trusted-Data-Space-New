"""
跨链互操作 API - /api/v1/blockchain/bridge
FISCO BCOS <-> Ethereum 跨链桥：资产转移 / 状态查询 / Merkle Proof 验证 / 支持链列表
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import cross_chain_service
from app.exceptions import DataNotFoundError, DataValidationError, BlockchainError

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Request / Response 模型
# ============================================================


class BridgeTransferRequest(BaseModel):
    """跨链资产转移请求"""
    source_chain: str = Field(description="源链标识: fisco_bcos / ethereum")
    target_chain: str = Field(description="目标链标识: fisco_bcos / ethereum")
    sender: str = Field(description="发送方地址")
    receiver: str = Field(description="接收方地址")
    amount: float = Field(gt=0, description="转移数量")
    asset_type: str = Field(default="token", description="资产类型: token / nft / data_asset")
    memo: str = Field(default="", description="备注信息")


class VerifyMessageRequest(BaseModel):
    """跨链消息验证请求"""
    message_hash: str = Field(description="跨链消息哈希")
    merkle_root: str = Field(description="Merkle 根哈希")
    merkle_proof: list[dict] = Field(description="Merkle 证明路径")
    leaf_index: int = Field(default=2, description="叶子节点索引")


# ============================================================
# API 端点
# ============================================================


@router.get("/chains", response_model=ApiResponse)
async def get_supported_chains(
    user: dict = Depends(get_current_user),
):
    """获取支持的跨链网络列表"""
    try:
        result = await cross_chain_service.get_supported_chains()
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"获取支持链列表失败: {e}")
        return ApiResponse(code=4000, message=f"获取支持链列表失败: {e}", data=None)


@router.post("/transfer", response_model=ApiResponse)
async def initiate_transfer(
    request: BridgeTransferRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """发起跨链资产转移（Lock-Mint / Burn-Release 模式）"""
    try:
        result = await cross_chain_service.initiate_transfer(
            db=db,
            source_chain=request.source_chain,
            target_chain=request.target_chain,
            sender=request.sender,
            receiver=request.receiver,
            amount=request.amount,
            asset_type=request.asset_type,
            memo=request.memo,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        logger.warning(f"跨链转移参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except BlockchainError as e:
        logger.error(f"跨链转移链上错误: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"跨链转移失败: {e}")
        return ApiResponse(code=4000, message=f"跨链转移失败: {e}", data=None)


@router.get("/status/{tx_id}", response_model=ApiResponse)
async def get_transfer_status(
    tx_id: str,
    user: dict = Depends(get_current_user),
):
    """查询跨链转移交易状态"""
    try:
        result = await cross_chain_service.get_transfer_status(tx_id=tx_id)
        return ApiResponse(data=result)
    except DataNotFoundError as e:
        logger.warning(f"跨链交易不存在: {tx_id}")
        return ApiResponse(code=2001, message=e.message, data=None)
    except Exception as e:
        logger.error(f"查询跨链交易状态失败: {e}")
        return ApiResponse(code=4000, message=f"查询失败: {e}", data=None)


@router.post("/verify", response_model=ApiResponse)
async def verify_cross_chain_message(
    request: VerifyMessageRequest,
    user: dict = Depends(get_current_user),
):
    """验证跨链消息（Merkle Proof 校验）"""
    try:
        result = await cross_chain_service.verify_cross_chain_message(
            message_hash=request.message_hash,
            merkle_root=request.merkle_root,
            merkle_proof=request.merkle_proof,
            leaf_index=request.leaf_index,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"跨链消息验证失败: {e}")
        return ApiResponse(code=4000, message=f"验证失败: {e}", data=None)


@router.get("/transactions", response_model=ApiResponse)
async def list_bridge_transactions(
    source_chain: Optional[str] = Query(None, description="源链过滤"),
    target_chain: Optional[str] = Query(None, description="目标链过滤"),
    status: Optional[str] = Query(None, description="状态过滤: pending/confirming_source/confirming_target/completed/failed"),
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出跨链桥交易记录"""
    try:
        result = await cross_chain_service.list_bridge_transactions(
            db=db,
            source_chain=source_chain,
            target_chain=target_chain,
            status=status,
            limit=limit,
            offset=offset,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"查询跨链交易列表失败: {e}")
        return ApiResponse(code=4000, message=f"查询失败: {e}", data=None)


@router.post("/sync/{chain}", response_model=ApiResponse)
async def sync_chain_status(
    chain: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """同步链状态（手动触发）"""
    try:
        result = await cross_chain_service.sync_chain_status(db=db, chain=chain)
        return ApiResponse(data=result)
    except DataValidationError as e:
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"链状态同步失败: {e}")
        return ApiResponse(code=4000, message=f"同步失败: {e}", data=None)
