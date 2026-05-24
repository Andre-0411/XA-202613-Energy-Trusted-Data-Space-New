"""
区块链交易查询 API — /api/v1/blockchain/transactions
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.blockchain import BlockchainTransaction
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user

router = APIRouter()


@router.get("/transactions", response_model=ApiResponse)
async def list_transactions(
    status: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """列出链上交易记录"""
    query = select(BlockchainTransaction).order_by(desc(BlockchainTransaction.created_at))
    if status:
        query = query.where(BlockchainTransaction.status == status)
    if method:
        query = query.where(BlockchainTransaction.method == method)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    txs = result.scalars().all()
    data = [{
        "tx_hash": tx.tx_hash,
        "contract_address": tx.contract_address,
        "method": tx.method,
        "params": tx.params,
        "block_number": tx.block_number,
        "status": tx.status,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "gas_used": tx.gas_used,
    } for tx in txs]

    count_result = await db.execute(select(func.count(BlockchainTransaction.id)))
    total = count_result.scalar()

    return ApiResponse(data={"items": data, "total": total, "limit": limit, "offset": offset})


@router.get("/overview", response_model=ApiResponse)
async def blockchain_overview(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """区块链概览 - 交易统计 + 合约信息"""
    # Total transactions
    total = await db.execute(select(func.count(BlockchainTransaction.id)))
    total_count = total.scalar()

    # Confirmed
    confirmed = await db.execute(
        select(func.count(BlockchainTransaction.id)).where(BlockchainTransaction.status == "confirmed")
    )
    confirmed_count = confirmed.scalar()

    # Method distribution
    dist = await db.execute(
        select(BlockchainTransaction.method, func.count(BlockchainTransaction.id))
        .group_by(BlockchainTransaction.method)
    )
    methods = {row[0]: row[1] for row in dist.all()}

    # Latest block
    latest = await db.execute(
        select(BlockchainTransaction).order_by(desc(BlockchainTransaction.block_number)).limit(1)
    )
    latest_tx = latest.scalar_one_or_none()

    return ApiResponse(data={
        "total_transactions": total_count,
        "confirmed": confirmed_count,
        "method_distribution": methods,
        "latest_block": latest_tx.block_number if latest_tx else 0,
        "chain_name": "FISCO BCOS v3.x",
        "consensus": "PBFT",
        "contracts_deployed": 15,
        "nodes": 4,
    })
