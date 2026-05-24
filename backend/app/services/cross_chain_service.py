"""
跨链互操作服务
跨链桥接协议（FISCO BCOS ↔ Ethereum）+ 跨链消息验证（Merkle Proof）+ 跨链资产转移 + 状态同步

实现：
- 跨链桥接协议管理（多链支持）
- Merkle Proof 验证跨链消息
- 锁定-铸造/销毁-释放 资产转移流程
- 跨链交易状态追踪与同步
- 审计日志记录
"""
import uuid
import json
import hashlib
import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blockchain import BlockchainTransaction
from app.exceptions import (
    BlockchainError,
    DataNotFoundError,
    DataValidationError,
    DataAlreadyExistsError,
)

logger = logging.getLogger(__name__)


def _audit_log(action: str, resource_id: str, details: Optional[dict] = None) -> None:
    """
    记录审计日志

    Args:
        action: 操作类型
        resource_id: 资源 ID
        details: 附加详情
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "cross_chain_service",
        "action": action,
        "resource_id": resource_id,
        "details": details or {},
    }
    logger.info(f"[AUDIT] {json.dumps(log_entry, ensure_ascii=False)}")


# ==================== 链配置 ====================

class ChainType(str, Enum):
    """支持的区块链类型"""
    FISCO_BCOS = "fisco_bcos"
    ETHEREUM = "ethereum"


SUPPORTED_CHAINS: dict[str, dict] = {
    ChainType.FISCO_BCOS: {
        "name": "FISCO BCOS",
        "chain_id": "fisco_bcos_main",
        "consensus": "PBFT",
        "block_time_seconds": 3,
        "native_token": "FISCO",
        "bridge_contract": "0x0000000000000000000000000000000000001001",
        "endpoint": "http://fisco-node:8545",
        "explorer_url": "https://fisco-explorer.example.com",
    },
    ChainType.ETHEREUM: {
        "name": "Ethereum",
        "chain_id": "ethereum_sepolia",
        "consensus": "PoS",
        "block_time_seconds": 12,
        "native_token": "ETH",
        "bridge_contract": "0x0000000000000000000000000000000000002001",
        "endpoint": "https://sepolia.infura.io/v3/bridge",
        "explorer_url": "https://sepolia.etherscan.io",
    },
}

# ==================== 跨链交易内存存储 ====================

# 跨链桥接交易记录（内存缓存，生产环境应用数据库）
_bridge_transactions: dict[str, dict] = {}

# 跨链消息队列
_pending_messages: dict[str, dict] = {}


# ==================== Merkle Proof 工具 ====================


def _compute_merkle_root(leaves: list[str]) -> str:
    """
    计算 Merkle 树根节点

    Args:
        leaves: 叶子节点哈希列表

    Returns:
        Merkle 根哈希
    """
    if not leaves:
        return hashlib.sha256(b"empty").hexdigest()

    # 对叶子节点哈希
    current_level = [hashlib.sha256(leaf.encode()).hexdigest() for leaf in leaves]

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = hashlib.sha256(
                (left + right).encode()
            ).hexdigest()
            next_level.append(combined)
        current_level = next_level

    return current_level[0]


def _generate_merkle_proof(leaves: list[str], leaf_index: int) -> list[dict]:
    """
    生成 Merkle 证明路径

    Args:
        leaves: 叶子节点列表
        leaf_index: 目标叶子索引

    Returns:
        证明路径（兄弟哈希列表）
    """
    if leaf_index < 0 or leaf_index >= len(leaves):
        return []

    proof = []
    current_level = [hashlib.sha256(leaf.encode()).hexdigest() for leaf in leaves]
    index = leaf_index

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = hashlib.sha256(
                (left + right).encode()
            ).hexdigest()
            next_level.append(combined)

        # 记录兄弟节点
        is_right_node = index % 2 == 1
        sibling_index = index - 1 if is_right_node else index + 1
        if sibling_index < len(current_level):
            proof.append({
                "hash": current_level[sibling_index],
                "position": "left" if is_right_node else "right",
            })
        else:
            proof.append({
                "hash": current_level[index],
                "position": "right" if is_right_node else "left",
            })

        current_level = next_level
        index = index // 2

    return proof


def _verify_merkle_proof(leaf: str, proof: list[dict], root: str) -> bool:
    """
    验证 Merkle 证明

    Args:
        leaf: 叶子数据
        proof: 证明路径
        root: 根哈希

    Returns:
        验证结果
    """
    current_hash = hashlib.sha256(leaf.encode()).hexdigest()

    for step in proof:
        sibling_hash = step.get("hash", "")
        position = step.get("position", "right")

        if position == "left":
            combined = hashlib.sha256(
                (sibling_hash + current_hash).encode()
            ).hexdigest()
        else:
            combined = hashlib.sha256(
                (current_hash + sibling_hash).encode()
            ).hexdigest()

        current_hash = combined

    return current_hash == root


# ==================== 跨链桥接协议 ====================


async def get_supported_chains() -> list[dict]:
    """
    获取支持的链列表

    Returns:
        支持的链信息列表
    """
    chains = []
    for chain_type, info in SUPPORTED_CHAINS.items():
        chains.append({
            "chain_type": chain_type.value,
            "name": info["name"],
            "chain_id": info["chain_id"],
            "consensus": info["consensus"],
            "block_time_seconds": info["block_time_seconds"],
            "native_token": info["native_token"],
            "bridge_contract": info["bridge_contract"],
            "explorer_url": info["explorer_url"],
            "status": "active",
        })
    return chains


async def initiate_transfer(
    db: AsyncSession,
    source_chain: str,
    target_chain: str,
    sender: str,
    receiver: str,
    amount: float,
    asset_type: str = "token",
    memo: str = "",
    user_id: str = "",
) -> dict:
    """
    发起跨链资产转移

    流程：
    1. 验证源链和目标链支持
    2. 锁定源链资产
    3. 生成跨链消息和 Merkle Proof
    4. 创建中继交易
    5. 等待目标链接收（异步）

    Args:
        db: 数据库会话
        source_chain: 源链
        target_chain: 目标链
        sender: 发送方地址
        receiver: 接收方地址
        amount: 转移数量
        asset_type: 资产类型
        memo: 备注
        user_id: 发起用户 ID

    Returns:
        转移交易信息
    """
    # 1. 验证链支持
    if source_chain not in SUPPORTED_CHAINS:
        raise DataValidationError(
            message=f"不支持的源链: {source_chain}，支持: {list(SUPPORTED_CHAINS.keys())}"
        )
    if target_chain not in SUPPORTED_CHAINS:
        raise DataValidationError(
            message=f"不支持的目标链: {target_chain}，支持: {list(SUPPORTED_CHAINS.keys())}"
        )
    if source_chain == target_chain:
        raise DataValidationError(message="源链和目标链不能相同")

    if amount <= 0:
        raise DataValidationError(message="转移数量必须大于 0")

    # 2. 生成交易 ID
    tx_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 3. 构建跨链消息
    message = {
        "tx_id": tx_id,
        "source_chain": source_chain,
        "target_chain": target_chain,
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "asset_type": asset_type,
        "memo": memo,
        "timestamp": int(now.timestamp()),
        "nonce": secrets.token_hex(8),
    }
    message_str = json.dumps(message, sort_keys=True, separators=(",", ":"))
    message_hash = hashlib.sha256(message_str.encode()).hexdigest()

    # 4. 生成 Merkle Proof
    merkle_leaves = [
        f"{tx_id}:{source_chain}:{target_chain}",
        f"{sender}:{receiver}:{amount}",
        message_hash,
        f"timestamp:{int(now.timestamp())}",
    ]
    merkle_root = _compute_merkle_root(merkle_leaves)
    merkle_proof = _generate_merkle_proof(merkle_leaves, 2)  # 第三个叶子是 message_hash

    # 5. 构建中继交易
    source_info = SUPPORTED_CHAINS[source_chain]
    target_info = SUPPORTED_CHAINS[target_chain]

    # 锁定交易（源链）
    lock_tx = {
        "tx_hash": f"0x{hashlib.sha256(f'lock:{tx_id}'.encode()).hexdigest()}",
        "chain": source_chain,
        "from": sender,
        "to": source_info["bridge_contract"],
        "amount": amount,
        "action": "lock",
        "block_number": int(time.time()) % 1000000,
        "gas_used": 21000 + int(amount * 100),
    }

    # 铸造交易（目标链）
    mint_tx = {
        "tx_hash": f"0x{hashlib.sha256(f'mint:{tx_id}'.encode()).hexdigest()}",
        "chain": target_chain,
        "from": target_info["bridge_contract"],
        "to": receiver,
        "amount": amount,
        "action": "mint",
        "block_number": int(time.time()) % 1000000,
        "gas_used": 45000 + int(amount * 100),
    }

    # 6. 创建数据库记录
    bridge_record = BlockchainTransaction(
        tx_hash=lock_tx["tx_hash"],
        contract_address=source_info["bridge_contract"],
        method="cross_chain_transfer",
        params={
            "bridge_type": "lock_mint",
            "source_chain": source_chain,
            "target_chain": target_chain,
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "asset_type": asset_type,
            "memo": memo,
            "message_hash": message_hash,
            "merkle_root": merkle_root,
            "target_tx_hash": mint_tx["tx_hash"],
        },
        from_address=sender,
        block_number=lock_tx["block_number"],
        gas_used=lock_tx["gas_used"],
        status="pending",
    )
    db.add(bridge_record)
    await db.commit()
    await db.refresh(bridge_record)

    # 7. 缓存交易状态
    bridge_info = {
        "tx_id": tx_id,
        "status": "pending",
        "source_chain": source_chain,
        "target_chain": target_chain,
        "source_tx": lock_tx,
        "target_tx": mint_tx,
        "message_hash": message_hash,
        "merkle_root": merkle_root,
        "merkle_proof": merkle_proof,
        "confirmations": {"source": 0, "target": 0},
        "required_confirmations": {"source": 12, "target": 6},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _bridge_transactions[tx_id] = bridge_info

    _audit_log("cross_chain_transfer", tx_id, {
        "source_chain": source_chain,
        "target_chain": target_chain,
        "amount": amount,
        "asset_type": asset_type,
    })

    logger.info(
        f"跨链转移发起: tx_id={tx_id}, {source_chain} -> {target_chain}, "
        f"amount={amount}, sender={sender}"
    )

    return {
        "tx_id": tx_id,
        "status": "pending",
        "source_chain": source_chain,
        "target_chain": target_chain,
        "source_tx_hash": lock_tx["tx_hash"],
        "target_tx_hash": mint_tx["tx_hash"],
        "message_hash": message_hash,
        "merkle_root": merkle_root,
        "amount": amount,
        "asset_type": asset_type,
        "sender": sender,
        "receiver": receiver,
        "created_at": now.isoformat(),
    }


async def get_transfer_status(tx_id: str) -> dict:
    """
    查询跨链转移状态

    Args:
        tx_id: 跨链交易 ID

    Returns:
        转移状态详情
    """
    if tx_id not in _bridge_transactions:
        raise DataNotFoundError(message=f"跨链交易不存在: {tx_id}")

    record = _bridge_transactions[tx_id]

    # 模拟确认数递增
    now = int(time.time())
    created_ts = int(datetime.fromisoformat(record["created_at"]).timestamp())
    elapsed = now - created_ts

    source_confirmations = min(
        elapsed // 2,
        record["required_confirmations"]["source"]
    )
    target_confirmations = max(
        0,
        min(
            (elapsed - 15) // 2,
            record["required_confirmations"]["target"]
        )
    )

    record["confirmations"]["source"] = source_confirmations
    record["confirmations"]["target"] = target_confirmations

    # 状态机
    if source_confirmations >= record["required_confirmations"]["source"]:
        if target_confirmations >= record["required_confirmations"]["target"]:
            record["status"] = "completed"
        else:
            record["status"] = "confirming_target"
    elif source_confirmations > 0:
        record["status"] = "confirming_source"

    record["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "tx_id": tx_id,
        "status": record["status"],
        "source_chain": record["source_chain"],
        "target_chain": record["target_chain"],
        "source_tx_hash": record["source_tx"]["tx_hash"],
        "target_tx_hash": record["target_tx"]["tx_hash"],
        "confirmations": record["confirmations"],
        "required_confirmations": record["required_confirmations"],
        "merkle_root": record["merkle_root"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
    }


async def verify_cross_chain_message(
    message_hash: str,
    merkle_root: str,
    merkle_proof: list[dict],
    leaf_index: int = 2,
) -> dict:
    """
    验证跨链消息（Merkle Proof）

    Args:
        message_hash: 跨链消息哈希
        merkle_root: Merkle 根
        merkle_proof: Merkle 证明路径
        leaf_index: 叶子索引

    Returns:
        验证结果
    """
    is_valid = _verify_merkle_proof(message_hash, merkle_proof, merkle_root)

    result = {
        "message_hash": message_hash,
        "merkle_root": merkle_root,
        "is_valid": is_valid,
        "proof_depth": len(merkle_proof),
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }

    _audit_log("verify_cross_chain_message", message_hash[:16], {
        "is_valid": is_valid,
        "proof_depth": len(merkle_proof),
    })

    logger.info(f"跨链消息验证: hash={message_hash[:16]}..., valid={is_valid}")
    return result


async def list_bridge_transactions(
    db: AsyncSession,
    source_chain: Optional[str] = None,
    target_chain: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    列出跨链桥接交易

    Args:
        db: 数据库会话
        source_chain: 源链过滤
        target_chain: 目标链过滤
        status: 状态过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        跨链交易列表
    """
    # 查询数据库中的跨链交易
    query = select(BlockchainTransaction).where(
        BlockchainTransaction.method == "cross_chain_transfer"
    )
    count_query = select(func.count()).select_from(BlockchainTransaction).where(
        BlockchainTransaction.method == "cross_chain_transfer"
    )

    if status:
        query = query.where(BlockchainTransaction.status == status)
        count_query = count_query.where(BlockchainTransaction.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(
        BlockchainTransaction.created_at.desc()
    ).offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    items = []
    for r in records:
        params = r.params or {}
        items.append({
            "tx_id": params.get("tx_id", str(r.id)),
            "tx_hash": r.tx_hash,
            "source_chain": params.get("source_chain", ""),
            "target_chain": params.get("target_chain", ""),
            "sender": params.get("sender", ""),
            "receiver": params.get("receiver", ""),
            "amount": params.get("amount", 0),
            "asset_type": params.get("asset_type", "token"),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def sync_chain_status(db: AsyncSession, chain: str) -> dict:
    """
    同步指定链的状态

    Args:
        db: 数据库会话
        chain: 链类型

    Returns:
        链同步状态
    """
    if chain not in SUPPORTED_CHAINS:
        raise DataValidationError(message=f"不支持的链: {chain}")

    chain_info = SUPPORTED_CHAINS[chain]
    now = datetime.now(timezone.utc)

    # 统计该链上的跨链交易数
    result = await db.execute(
        select(func.count()).select_from(BlockchainTransaction).where(
            BlockchainTransaction.method == "cross_chain_transfer"
        )
    )
    total_tx = result.scalar() or 0

    # 模拟区块信息
    latest_block = int(time.time()) % 1000000 + 500000

    sync_result = {
        "chain": chain,
        "name": chain_info["name"],
        "chain_id": chain_info["chain_id"],
        "latest_block_number": latest_block,
        "peer_count": 4 if chain == ChainType.FISCO_BCOS else 8,
        "consensus": chain_info["consensus"],
        "block_time_seconds": chain_info["block_time_seconds"],
        "total_bridge_transactions": total_tx,
        "sync_status": "synced",
        "last_sync_at": now.isoformat(),
    }

    _audit_log("sync_chain_status", chain, {
        "latest_block": latest_block,
        "total_tx": total_tx,
    })

    return sync_result
