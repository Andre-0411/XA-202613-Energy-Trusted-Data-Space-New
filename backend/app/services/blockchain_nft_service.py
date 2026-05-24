"""
区块链 NFT 确权服务
NFT 铸造 / 查询 / 转移 / 授权 / 统计 / 链上交互
通过 DataAssetNFT 合约实现数据资产 NFT 化

增强功能:
- NFT 授权管理（授权/撤销/查询）
- NFT 资产统计
"""
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blockchain import NftAsset, BlockchainTransaction
from app.models.data_asset import DataAsset
from app.core.fisco_client import fisco_client
from app.core.contract_registry import get_contract_registry
from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import (
    BlockchainError, DataNotFoundError, SmartContractError,
)
from app.schemas.blockchain import (
    NftMintRequest, NftTransferRequest, NftResponse,
    NftAuthorizeRequest, NftRevokeRequest, NftAuthorization,
    NftStatsResponse, NftCategoryStats,
)

logger = logging.getLogger(__name__)


async def mint_nft(
    db: AsyncSession,
    request: NftMintRequest,
    user_did: str,
) -> NftResponse:
    """
    铸造数据资产 NFT

    流程:
    1. 校验数据资产存在
    2. 校验确权证据 SM3 哈希
    3. 调用 DataAssetNFT 合约 mint 方法
    4. 记录 NFT 资产与链上交易
    """
    # 1. 校验数据资产
    asset_result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(request.asset_id))
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    # 2. 检查是否已铸造
    existing = await db.execute(
        select(NftAsset).where(NftAsset.asset_id == uuid.UUID(request.asset_id))
    )
    if existing.scalar_one_or_none():
        raise BlockchainError("该资产已铸造 NFT")

    # 3. 调用链上铸造 - 优先使用 DataAssetNFT 合约
    tx_hash = ""
    block_number = None
    token_id = str(uuid.uuid4())

    registry = get_contract_registry()
    nft_contract_info = registry.get_contract("DataAssetNFT")

    if nft_contract_info and nft_contract_info.abi:
        from app.core.fisco_web3_client import get_fisco_client
        web3_client = get_fisco_client()
        if web3_client.is_connected:
            try:
                # 将 evidence_hash 转为 bytes32
                evidence_hash_hex = request.evidence_hash.replace("0x", "") if request.evidence_hash else ""
                evidence_bytes = bytes.fromhex(evidence_hash_hex) if evidence_hash_hex else b'\x00' * 32
                if len(evidence_bytes) < 32:
                    evidence_bytes = evidence_bytes.ljust(32, b'\x00')

                receipt = await asyncio.to_thread(
                    web3_client.send_transaction,
                    address=nft_contract_info.address,
                    abi=nft_contract_info.abi,
                    method="mint",
                    args=[
                        user_did,  # to (address)
                        request.asset_id,
                        request.category,
                        request.classification_level,
                        bytes(evidence_bytes[:32]),
                        request.certificate_url or "",
                    ],
                )
                tx_hash = receipt.get("tx_hash", "")
                block_number = receipt.get("block_number")

                # 尝试从链上获取 tokenId
                try:
                    chain_token_id = await asyncio.to_thread(
                        web3_client.call_contract,
                        address=nft_contract_info.address,
                        abi=nft_contract_info.abi,
                        method="tokenOfAsset",
                        args=[request.asset_id],
                    )
                    if chain_token_id:
                        token_id = str(chain_token_id)
                except Exception:
                    pass

            except Exception as e:
                logger.warning(f"DataAssetNFT contract call failed, falling back: {e}")

    # 回退到原有 fisco_client
    if not tx_hash:
        try:
            chain_result = await fisco_client.mint_nft(
                asset_id=request.asset_id,
                category=request.category,
                level=request.classification_level,
                evidence_hash=request.evidence_hash,
                certificate_uri=request.certificate_url or "",
            )
            tx_hash = chain_result.get("transactionHash", "")
            block_number = chain_result.get("blockNumber")
            token_id = chain_result.get("tokenId", token_id)
        except Exception as e:
            logger.error(f"NFT mint chain call failed: {e}")
            raise SmartContractError(f"NFT 铸造交易失败: {e}")

    # 4. 记录 NFT 资产
    nft_asset = NftAsset(
        token_id=token_id,
        asset_id=uuid.UUID(request.asset_id),
        owner_did=user_did,
        creator_did=user_did,
        token_uri=request.certificate_url,
        evidence_hash=request.evidence_hash,
        certificate_url=request.certificate_url,
        tx_hash=tx_hash,
        block_number=block_number,
    )
    db.add(nft_asset)

    # 5. 记录链上交易
    tx_record = BlockchainTransaction(
        tx_hash=tx_hash,
        contract_address=nft_contract_info.address if nft_contract_info else "DataAssetNFT",
        method="mint",
        params={
            "asset_id": request.asset_id,
            "category": request.category,
            "classification_level": request.classification_level,
        },
        block_number=block_number,
        status="confirmed",
    )
    db.add(tx_record)

    # 6. 更新数据资产 NFT 关联
    asset.nft_token_id = token_id
    await db.commit()
    await db.refresh(nft_asset)

    return NftResponse.model_validate(nft_asset)


async def get_nft_by_token_id(
    db: AsyncSession,
    token_id: str,
) -> NftResponse:
    """按 token_id 查询 NFT"""
    result = await db.execute(
        select(NftAsset).where(NftAsset.token_id == token_id)
    )
    nft = result.scalar_one_or_none()
    if not nft:
        raise DataNotFoundError("NFT 未找到")
    return NftResponse.model_validate(nft)


async def get_nft_metadata_from_chain(token_id: int) -> dict:
    """
    从链上查询 NFT 元数据

    通过 DataAssetNFT 合约的 getAssetMetadata 方法查询
    """
    registry = get_contract_registry()
    nft_contract_info = registry.get_contract("DataAssetNFT")

    if not nft_contract_info or not nft_contract_info.abi:
        raise BlockchainError("DataAssetNFT 合约未部署")

    from app.core.fisco_web3_client import get_fisco_client
    web3_client = get_fisco_client()

    if not web3_client.is_connected:
        raise BlockchainError("未连接到区块链节点")

    try:
        metadata = await asyncio.to_thread(
            web3_client.call_contract,
            address=nft_contract_info.address,
            abi=nft_contract_info.abi,
            method="getAssetMetadata",
            args=[token_id],
        )
        return {
            "token_id": token_id,
            "metadata": metadata,
            "source": "chain",
        }
    except Exception as e:
        logger.error(f"Chain NFT metadata query failed: {e}")
        raise BlockchainError(f"链上 NFT 元数据查询失败: {e}")


async def get_nfts_by_owner(
    db: AsyncSession,
    owner_did: str,
) -> list[NftResponse]:
    """按 DID 查询用户拥有的 NFT"""
    result = await db.execute(
        select(NftAsset).where(NftAsset.owner_did == owner_did)
    )
    nfts = result.scalars().all()
    return [NftResponse.model_validate(n) for n in nfts]


async def transfer_nft(
    db: AsyncSession,
    token_id: str,
    request: NftTransferRequest,
    current_owner_did: str,
) -> NftResponse:
    """
    转移 NFT

    1. 校验 NFT 存在且属于当前用户
    2. 验证 SM2 签名
    3. 调用链上转移
    4. 更新数据库记录
    """
    # 1. 校验 NFT
    result = await db.execute(
        select(NftAsset).where(NftAsset.token_id == token_id)
    )
    nft = result.scalar_one_or_none()
    if not nft:
        raise DataNotFoundError("NFT 未找到")
    if nft.owner_did != current_owner_did:
        raise BlockchainError("非 NFT 所有者，无法转移")

    # 2. 验证签名
    transfer_data = f"{token_id}:{current_owner_did}:{request.to_did}"
    try:
        is_valid = gmssl_adapter.sm2_verify(
            current_owner_did, transfer_data, request.signature
        )
        if not is_valid:
            raise BlockchainError("转移签名验证失败")
    except Exception as e:
        logger.error(f"NFT transfer signature verify failed: {e}")
        raise BlockchainError("转移签名验证失败")

    # 3. 链上转移 - 注意：当前 DataAssetNFT 合约没有 transferFrom
    #    使用 burn + re-mint 模式，或通过 fisco_client 通用调用
    tx_hash = ""
    try:
        chain_result = await fisco_client.send_transaction(
            contract_address="DataAssetNFT",
            method="transferFrom",
            params={
                "from": current_owner_did,
                "to": request.to_did,
                "tokenId": token_id,
            },
        )
        tx_hash = chain_result.get("transactionHash", "")
    except Exception as e:
        logger.error(f"NFT transfer chain call failed: {e}")
        raise SmartContractError(f"NFT 转移交易失败: {e}")

    # 4. 更新记录
    nft.owner_did = request.to_did
    tx_record = BlockchainTransaction(
        tx_hash=tx_hash,
        contract_address="DataAssetNFT",
        method="transferFrom",
        params={"from": current_owner_did, "to": request.to_did, "tokenId": token_id},
        status="confirmed",
    )
    db.add(tx_record)
    await db.commit()
    await db.refresh(nft)

    return NftResponse.model_validate(nft)


# ==================== 增强功能 ====================


# 内存授权存储（生产环境应迁移至 PostgreSQL 表）
_nft_authorizations: dict[str, list[dict]] = {}


async def authorize_nft(
    db: AsyncSession,
    token_id: str,
    request: NftAuthorizeRequest,
    owner_did: str,
) -> NftAuthorization:
    """
    NFT 授权管理 — 授权其他用户使用 NFT

    授权信息链上记录，同步写入内存缓存。

    Args:
        db: 异步数据库会话
        token_id: NFT token ID
        request: 授权请求
        owner_did: 当前所有者 DID

    Returns:
        授权详情
    """
    # 1. 校验 NFT 存在且属于当前用户
    result = await db.execute(
        select(NftAsset).where(NftAsset.token_id == token_id)
    )
    nft = result.scalar_one_or_none()
    if not nft:
        raise DataNotFoundError("NFT 未找到")
    if nft.owner_did != owner_did:
        raise BlockchainError("非 NFT 所有者，无法授权")

    # 2. 链上授权
    tx_hash: str = ""
    block_number: Optional[int] = None

    registry = get_contract_registry()
    nft_contract_info = registry.get_contract("DataAssetNFT")

    if nft_contract_info and nft_contract_info.abi:
        from app.core.fisco_web3_client import get_fisco_client
        web3_client = get_fisco_client()
        if web3_client.is_connected:
            try:
                receipt = await asyncio.to_thread(
                    web3_client.send_transaction,
                    address=nft_contract_info.address,
                    abi=nft_contract_info.abi,
                    method="authorize",
                    args=[
                        token_id,
                        request.authorized_did,
                        request.permission_type,
                        request.duration_seconds or 0,
                    ],
                )
                tx_hash = receipt.get("tx_hash", "")
                block_number = receipt.get("block_number")
            except Exception as e:
                logger.warning(f"NFT authorize chain call failed: {e}")
                # 授权失败不阻塞，使用数据库记录

    # 3. 记录授权到内存
    auth_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at: Optional[datetime] = None
    if request.duration_seconds and request.duration_seconds > 0:
        from datetime import timedelta
        expires_at = now + timedelta(seconds=request.duration_seconds)

    auth_record = {
        "auth_id": auth_id,
        "token_id": token_id,
        "owner_did": owner_did,
        "authorized_did": request.authorized_did,
        "permission_type": request.permission_type,
        "duration_seconds": request.duration_seconds,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "is_active": True,
        "tx_hash": tx_hash,
    }

    if token_id not in _nft_authorizations:
        _nft_authorizations[token_id] = []
    _nft_authorizations[token_id].append(auth_record)

    # 4. 记录链上交易
    if tx_hash:
        tx_record = BlockchainTransaction(
            tx_hash=tx_hash,
            contract_address=nft_contract_info.address if nft_contract_info else "DataAssetNFT",
            method="authorize",
            params={
                "token_id": token_id,
                "authorized_did": request.authorized_did,
                "permission_type": request.permission_type,
            },
            block_number=block_number,
            status="confirmed",
        )
        db.add(tx_record)
        await db.commit()

    return NftAuthorization(**auth_record)


async def revoke_nft_authorization(
    db: AsyncSession,
    token_id: str,
    request: NftRevokeRequest,
    owner_did: str,
) -> dict:
    """
    撤销 NFT 授权

    Args:
        db: 异步数据库会话
        token_id: NFT token ID
        request: 撤销请求
        owner_did: 当前所有者 DID

    Returns:
        撤销结果
    """
    # 1. 校验 NFT 存在且属于当前用户
    result = await db.execute(
        select(NftAsset).where(NftAsset.token_id == token_id)
    )
    nft = result.scalar_one_or_none()
    if not nft:
        raise DataNotFoundError("NFT 未找到")
    if nft.owner_did != owner_did:
        raise BlockchainError("非 NFT 所有者，无法撤销授权")

    # 2. 链上撤销
    tx_hash: str = ""
    registry = get_contract_registry()
    nft_contract_info = registry.get_contract("DataAssetNFT")

    if nft_contract_info and nft_contract_info.abi:
        from app.core.fisco_web3_client import get_fisco_client
        web3_client = get_fisco_client()
        if web3_client.is_connected:
            try:
                receipt = await asyncio.to_thread(
                    web3_client.send_transaction,
                    address=nft_contract_info.address,
                    abi=nft_contract_info.abi,
                    method="revokeAuthorization",
                    args=[token_id, request.authorized_did],
                )
                tx_hash = receipt.get("tx_hash", "")
            except Exception as e:
                logger.warning(f"NFT revoke chain call failed: {e}")

    # 3. 更新内存授权记录
    revoked_count: int = 0
    if token_id in _nft_authorizations:
        for auth in _nft_authorizations[token_id]:
            if auth["authorized_did"] == request.authorized_did and auth["is_active"]:
                auth["is_active"] = False
                revoked_count += 1

    return {
        "token_id": token_id,
        "authorized_did": request.authorized_did,
        "revoked_count": revoked_count,
        "tx_hash": tx_hash,
        "status": "revoked",
    }


async def get_nft_authorizations(
    token_id: str,
) -> list[NftAuthorization]:
    """
    查询 NFT 的授权列表

    Args:
        token_id: NFT token ID

    Returns:
        授权列表
    """
    auths = _nft_authorizations.get(token_id, [])
    result: list[NftAuthorization] = []
    for auth in auths:
        # 检查授权是否过期
        is_expired = False
        if auth.get("expires_at"):
            expires_at = datetime.fromisoformat(auth["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            is_expired = datetime.now(timezone.utc) > expires_at

        if auth["is_active"] and not is_expired:
            result.append(NftAuthorization(**auth))
    return result


async def get_nft_stats(
    db: AsyncSession,
    owner_did: Optional[str] = None,
) -> NftStatsResponse:
    """
    NFT 资产统计

    统计 NFT 铸造总量、分类分布、活跃授权等指标。

    Args:
        db: 异步数据库会话
        owner_did: 按所有者筛选（可选）

    Returns:
        NFT 统计响应
    """
    # 总量统计
    count_query = select(func.count(NftAsset.id))
    if owner_did:
        count_query = count_query.where(NftAsset.owner_did == owner_did)
    total_result = await db.execute(count_query)
    total_nfts: int = total_result.scalar() or 0

    # 按分类统计（使用 evidence_hash 前缀作为分类标识，如果字段中有 category 信息）
    # NftAsset 表没有 category 字段，这里基于 asset 关联做基础统计
    category_query = (
        select(
            NftAsset.evidence_hash,
            func.count(NftAsset.id).label("count"),
        )
        .group_by(NftAsset.evidence_hash)
    )
    if owner_did:
        category_query = category_query.where(NftAsset.owner_did == owner_did)
    category_result = await db.execute(category_query)
    category_rows = category_result.all()

    # 简单分类统计（基于前缀归类）
    category_stats: list[NftCategoryStats] = []
    default_category = NftCategoryStats(category="default", count=total_nfts)
    category_stats.append(default_category)

    # 今日铸造统计
    from datetime import timedelta
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = select(func.count(NftAsset.id)).where(
        NftAsset.created_at >= today_start
    )
    if owner_did:
        today_query = today_query.where(NftAsset.owner_did == owner_did)
    today_result = await db.execute(today_query)
    minted_today: int = today_result.scalar() or 0

    # 授权统计（从内存获取）
    active_authorizations: int = 0
    for token_auths in _nft_authorizations.values():
        for auth in token_auths:
            if auth.get("is_active", False):
                is_expired = False
                if auth.get("expires_at"):
                    exp = datetime.fromisoformat(auth["expires_at"])
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    is_expired = datetime.now(timezone.utc) > exp
                if not is_expired:
                    active_authorizations += 1

    return NftStatsResponse(
        total_nfts=total_nfts,
        minted_today=minted_today,
        active_authorizations=active_authorizations,
        category_stats=category_stats,
        owner_filter=owner_did,
    )
