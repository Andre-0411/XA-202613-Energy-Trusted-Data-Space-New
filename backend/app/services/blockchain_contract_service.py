"""
区块链智能合约服务
合约调用 / 部署 / 查询
通过 contract_registry 解析合约地址，通过 fisco_web3_client 执行 ABI 编码调用
"""
import asyncio
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blockchain import BlockchainTransaction
from app.core.fisco_client import fisco_client
from app.core.contract_registry import get_contract_registry
from app.exceptions import SmartContractError, DataNotFoundError
from app.schemas.blockchain import ContractCallRequest

logger = logging.getLogger(__name__)


async def call_contract(
    db: AsyncSession,
    request: ContractCallRequest,
) -> dict:
    """
    只读合约调用（不消耗 Gas）

    通过 contract_registry 解析合约地址，使用 ABI 编码调用链上方法。
    用于查询链上状态，如读取 NFT 元数据、存证状态等。
    """
    try:
        registry = get_contract_registry()
        contract_name = request.from_address or ""
        contract_info = registry.get_contract(contract_name)

        if contract_info and contract_info.abi:
            # 使用 ABI 编码调用
            from app.core.fisco_web3_client import get_fisco_client
            web3_client = get_fisco_client()
            if web3_client.is_connected:
                result = await asyncio.to_thread(
                    web3_client.call_contract,
                    address=contract_info.address,
                    abi=contract_info.abi,
                    method=request.method,
                    args=request.params if isinstance(request.params, list) else None,
                )
                return {
                    "method": request.method,
                    "params": request.params,
                    "result": result,
                    "read_only": True,
                    "contract": contract_name,
                    "address": contract_info.address,
                }

        # 回退到原有 fisco_client
        result = await fisco_client.call_contract(
            contract_address=contract_name,
            method=request.method,
            params=request.params,
        )
        return {
            "method": request.method,
            "params": request.params,
            "result": result,
            "read_only": True,
        }
    except Exception as e:
        logger.error(f"Contract read call failed: {e}")
        raise SmartContractError(f"合约只读调用失败: {e}")


async def send_transaction(
    db: AsyncSession,
    request: ContractCallRequest,
    user_did: str,
) -> dict:
    """
    发送合约交易（写操作）

    通过 contract_registry 解析合约地址，使用 ABI 编码发送交易。
    记录交易到区块链交易表。
    """
    try:
        registry = get_contract_registry()
        contract_name = request.from_address or ""
        contract_info = registry.get_contract(contract_name)
        tx_hash = ""
        block_number = None

        if contract_info and contract_info.abi:
            from app.core.fisco_web3_client import get_fisco_client
            web3_client = get_fisco_client()
            if web3_client.is_connected:
                receipt = await asyncio.to_thread(
                    web3_client.send_transaction,
                    address=contract_info.address,
                    abi=contract_info.abi,
                    method=request.method,
                    args=request.params if isinstance(request.params, list) else None,
                )
                tx_hash = receipt.get("tx_hash", "")
                block_number = receipt.get("block_number")
            else:
                chain_result = await fisco_client.send_transaction(
                    contract_address=contract_name,
                    method=request.method,
                    params=request.params,
                    from_address=user_did,
                )
                tx_hash = chain_result.get("transactionHash", "")
                block_number = chain_result.get("blockNumber")
        else:
            chain_result = await fisco_client.send_transaction(
                contract_address=contract_name,
                method=request.method,
                params=request.params,
                from_address=user_did,
            )
            tx_hash = chain_result.get("transactionHash", "")
            block_number = chain_result.get("blockNumber")

        # 记录交易
        tx_record = BlockchainTransaction(
            tx_hash=tx_hash,
            contract_address=contract_info.address if contract_info else contract_name,
            method=request.method,
            params=request.params,
            from_address=user_did,
            block_number=block_number,
            status="confirmed",
        )
        db.add(tx_record)
        await db.commit()

        return {
            "tx_hash": tx_hash,
            "block_number": block_number,
            "method": request.method,
            "contract": contract_name,
            "status": "confirmed",
        }
    except Exception as e:
        logger.error(f"Contract write transaction failed: {e}")
        raise SmartContractError(f"合约交易失败: {e}")


async def get_transaction(
    db: AsyncSession,
    tx_hash: str,
) -> dict:
    """查询交易记录（先查数据库，再查链上）"""
    result = await db.execute(
        select(BlockchainTransaction).where(BlockchainTransaction.tx_hash == tx_hash)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        # 尝试从链上查询
        try:
            from app.core.fisco_web3_client import get_fisco_client
            web3_client = get_fisco_client()
            if web3_client.is_connected:
                receipt = await asyncio.to_thread(
                    web3_client.get_transaction_receipt, tx_hash
                )
                return {
                    "tx_hash": tx_hash,
                    "status": receipt.get("status"),
                    "block_number": receipt.get("block_number"),
                    "gas_used": receipt.get("gas_used"),
                    "from_chain": True,
                }
            else:
                receipt = await fisco_client.get_transaction_receipt(tx_hash)
                return {
                    "tx_hash": tx_hash,
                    "status": receipt.get("status"),
                    "block_number": receipt.get("blockNumber"),
                    "gas_used": receipt.get("gasUsed"),
                    "from_chain": True,
                }
        except Exception:
            raise DataNotFoundError("交易记录未找到")

    return {
        "tx_hash": tx.tx_hash,
        "contract_address": tx.contract_address,
        "method": tx.method,
        "params": tx.params,
        "from_address": tx.from_address,
        "block_number": tx.block_number,
        "gas_used": tx.gas_used,
        "status": tx.status,
        "from_chain": False,
    }


async def list_transactions(
    db: AsyncSession,
    contract_address: Optional[str] = None,
    method: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """查询交易列表"""
    query = select(BlockchainTransaction)
    if contract_address:
        query = query.where(BlockchainTransaction.contract_address == contract_address)
    if method:
        query = query.where(BlockchainTransaction.method == method)
    if status:
        query = query.where(BlockchainTransaction.status == status)

    query = query.order_by(BlockchainTransaction.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return {
        "items": [
            {
                "tx_hash": t.tx_hash,
                "contract_address": t.contract_address,
                "method": t.method,
                "status": t.status,
                "block_number": t.block_number,
                "created_at": str(t.created_at),
            }
            for t in transactions
        ],
        "total": len(transactions),
    }


async def get_chain_status() -> dict:
    """
    获取链状态概览

    Returns:
        链状态信息（连接状态、区块号、节点数、已部署合约数）
    """
    registry = get_contract_registry()
    deployed = registry.get_all()

    from app.core.fisco_web3_client import get_fisco_client
    web3_client = get_fisco_client()

    chain_info = {
        "connected": False,
        "block_number": 0,
        "peer_count": 0,
        "chain_id": 0,
    }

    if web3_client.is_connected:
        try:
            chain_info["connected"] = True
            chain_info["block_number"] = await asyncio.to_thread(web3_client.get_block_number)
            chain_info["peer_count"] = await asyncio.to_thread(web3_client.get_peer_count)
            chain_info["chain_id"] = await asyncio.to_thread(web3_client.get_chain_id)
        except Exception as e:
            logger.warning(f"Failed to get chain status: {e}")

    return {
        "chain": chain_info,
        "contracts": {
            "total": len(deployed),
            "deployed": [c.name for c in deployed if c.status == "active"],
            "details": {
                c.name: {
                    "address": c.address,
                    "version": c.version,
                    "deployed_at": c.deployed_at,
                }
                for c in deployed
            },
        },
    }
