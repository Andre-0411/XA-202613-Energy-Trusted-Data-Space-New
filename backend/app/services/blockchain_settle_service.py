"""
区块链链上结算服务
订阅计费 → 链上结算 → 交易记录
通过 AutoSettlement 合约实现自动结算和争议处理

增强功能:
- 批量结算处理
- 对账功能
- 结算报告生成
"""
import asyncio
import uuid
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import Subscription, BillingRecord
from app.models.blockchain import BlockchainTransaction
from app.core.fisco_client import fisco_client
from app.core.contract_registry import get_contract_registry
from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import SettlementError, DataNotFoundError, BillingError
from app.schemas.blockchain import (
    SettlementRequest, SettlementBatchRequest, SettlementBatchResult,
    SettlementReconciliation, SettlementReportRequest, SettlementReportResponse,
    SettlementReconciliationItem,
)

logger = logging.getLogger(__name__)


async def create_settlement(
    db: AsyncSession,
    request: SettlementRequest,
    user_did: str,
) -> dict:
    """
    创建链上结算

    流程:
    1. 校验订阅存在且有效
    2. 计算结算金额
    3. 调用 AutoSettlement 合约 createSettlement 方法
    4. 创建计费记录
    5. 更新订阅用量
    """
    # 1. 校验订阅
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == uuid.UUID(request.subscription_id)
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise DataNotFoundError("订阅未找到")
    if subscription.status != "active":
        raise SettlementError("订阅状态非活跃，无法结算")

    # 2. 创建计费记录
    billing_record = BillingRecord(
        subscription_id=uuid.UUID(request.subscription_id),
        amount=request.amount,
        billing_period=request.billing_period,
        usage_detail={
            "subscription_id": request.subscription_id,
            "billing_period": request.billing_period,
            "settled_by": user_did,
        },
        payment_status="pending",
    )
    db.add(billing_record)
    await db.flush()

    # 3. 调用链上结算 - 优先使用 AutoSettlement 合约
    tx_hash = ""
    block_number = None

    registry = get_contract_registry()
    settle_contract_info = registry.get_contract("AutoSettlement")

    if settle_contract_info and settle_contract_info.abi:
        from app.core.fisco_web3_client import get_fisco_client
        web3_client = get_fisco_client()
        if web3_client.is_connected:
            try:
                receipt = await asyncio.to_thread(
                    web3_client.send_transaction,
                    address=settle_contract_info.address,
                    abi=settle_contract_info.abi,
                    method="createSettlement",
                    args=[
                        request.subscription_id,
                        request.amount,
                        request.billing_period,
                        user_did,  # payer
                        user_did,  # payee (简化：同一用户)
                    ],
                )
                tx_hash = receipt.get("tx_hash", "")
                block_number = receipt.get("block_number")
            except Exception as e:
                logger.warning(f"AutoSettlement contract call failed, falling back: {e}")

    # 回退到原有 fisco_client
    if not tx_hash:
        try:
            chain_result = await fisco_client.send_transaction(
                contract_address="SettlementContract",
                method="settle",
                params={
                    "subscriptionId": request.subscription_id,
                    "amount": str(request.amount),
                    "billingPeriod": request.billing_period,
                },
                from_address=user_did,
            )
            tx_hash = chain_result.get("transactionHash", "")
            block_number = chain_result.get("blockNumber")
        except Exception as e:
            logger.error(f"Chain settlement failed: {e}")
            billing_record.payment_status = "failed"
            await db.commit()
            raise SettlementError(f"链上结算失败: {e}")

    # 4. 更新计费记录
    billing_record.payment_status = "paid"
    billing_record.tx_hash = tx_hash

    # 5. 记录链上交易
    tx_record = BlockchainTransaction(
        tx_hash=tx_hash,
        contract_address=settle_contract_info.address if settle_contract_info else "SettlementContract",
        method="createSettlement",
        params={
            "subscriptionId": request.subscription_id,
            "amount": str(request.amount),
        },
        from_address=user_did,
        block_number=block_number,
        status="confirmed",
    )
    db.add(tx_record)

    # 6. 更新订阅用量
    subscription.quota_used = (subscription.quota_used or 0) + 1

    await db.commit()
    await db.refresh(billing_record)

    return {
        "billing_id": str(billing_record.id),
        "subscription_id": request.subscription_id,
        "amount": request.amount,
        "billing_period": request.billing_period,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "payment_status": "paid",
    }


async def confirm_settlement_on_chain(settlement_id: int) -> dict:
    """
    在链上确认结算

    通过 AutoSettlement 合约的 confirmSettlement 方法
    """
    registry = get_contract_registry()
    settle_contract_info = registry.get_contract("AutoSettlement")

    if not settle_contract_info or not settle_contract_info.abi:
        raise SettlementError("AutoSettlement 合约未部署")

    from app.core.fisco_web3_client import get_fisco_client
    web3_client = get_fisco_client()

    if not web3_client.is_connected:
        raise SettlementError("未连接到区块链节点")

    try:
        receipt = await asyncio.to_thread(
            web3_client.send_transaction,
            address=settle_contract_info.address,
            abi=settle_contract_info.abi,
            method="confirmSettlement",
            args=[settlement_id],
        )
        return {
            "settlement_id": settlement_id,
            "tx_hash": receipt.get("tx_hash", ""),
            "block_number": receipt.get("block_number"),
            "status": "confirmed",
        }
    except Exception as e:
        logger.error(f"Chain settlement confirmation failed: {e}")
        raise SettlementError(f"链上结算确认失败: {e}")


async def dispute_settlement_on_chain(settlement_id: int, reason: str) -> dict:
    """
    在链上发起争议

    通过 AutoSettlement 合约的 disputeSettlement 方法
    """
    registry = get_contract_registry()
    settle_contract_info = registry.get_contract("AutoSettlement")

    if not settle_contract_info or not settle_contract_info.abi:
        raise SettlementError("AutoSettlement 合约未部署")

    from app.core.fisco_web3_client import get_fisco_client
    web3_client = get_fisco_client()

    if not web3_client.is_connected:
        raise SettlementError("未连接到区块链节点")

    try:
        receipt = await asyncio.to_thread(
            web3_client.send_transaction,
            address=settle_contract_info.address,
            abi=settle_contract_info.abi,
            method="disputeSettlement",
            args=[settlement_id, reason],
        )
        return {
            "settlement_id": settlement_id,
            "reason": reason,
            "tx_hash": receipt.get("tx_hash", ""),
            "block_number": receipt.get("block_number"),
            "status": "disputed",
        }
    except Exception as e:
        logger.error(f"Chain settlement dispute failed: {e}")
        raise SettlementError(f"链上争议提交失败: {e}")


async def get_settlement_from_chain(settlement_id: int) -> dict:
    """
    从链上查询结算详情

    通过 AutoSettlement 合约的 getSettlement 方法
    """
    registry = get_contract_registry()
    settle_contract_info = registry.get_contract("AutoSettlement")

    if not settle_contract_info or not settle_contract_info.abi:
        raise SettlementError("AutoSettlement 合约未部署")

    from app.core.fisco_web3_client import get_fisco_client
    web3_client = get_fisco_client()

    if not web3_client.is_connected:
        raise SettlementError("未连接到区块链节点")

    try:
        record = await asyncio.to_thread(
            web3_client.call_contract,
            address=settle_contract_info.address,
            abi=settle_contract_info.abi,
            method="getSettlement",
            args=[settlement_id],
        )
        return {
            "settlement_id": settlement_id,
            "record": record,
            "source": "chain",
        }
    except Exception as e:
        logger.error(f"Chain settlement query failed: {e}")
        raise SettlementError(f"链上结算查询失败: {e}")


async def get_settlement(
    db: AsyncSession,
    billing_id: str,
) -> dict:
    """查询结算记录（数据库）"""
    result = await db.execute(
        select(BillingRecord).where(BillingRecord.id == uuid.UUID(billing_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError("结算记录未找到")

    return {
        "id": str(record.id),
        "subscription_id": str(record.subscription_id),
        "amount": float(record.amount),
        "billing_period": record.billing_period,
        "usage_detail": record.usage_detail,
        "payment_status": record.payment_status,
        "tx_hash": record.tx_hash,
        "created_at": str(record.created_at),
    }


async def list_settlements(
    db: AsyncSession,
    subscription_id: Optional[str] = None,
    payment_status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """查询结算列表"""
    query = select(BillingRecord)
    if subscription_id:
        query = query.where(
            BillingRecord.subscription_id == uuid.UUID(subscription_id)
        )
    if payment_status:
        query = query.where(BillingRecord.payment_status == payment_status)

    query = query.order_by(BillingRecord.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "subscription_id": str(r.subscription_id),
                "amount": float(r.amount),
                "billing_period": r.billing_period,
                "payment_status": r.payment_status,
                "tx_hash": r.tx_hash,
                "created_at": str(r.created_at),
            }
            for r in records
        ],
        "total": len(records),
    }


# ==================== 增强功能 ====================


async def batch_settlement(
    db: AsyncSession,
    batch_request: SettlementBatchRequest,
    user_did: str,
) -> SettlementBatchResult:
    """
    批量结算处理

    批量处理多条结算请求，每条独立执行链上结算。
    部分失败不影响其他记录。

    Args:
        db: 异步数据库会话
        batch_request: 批量结算请求
        user_did: 发起用户 DID

    Returns:
        批量结算结果
    """
    total: int = len(batch_request.items)
    success_count: int = 0
    failure_count: int = 0
    total_amount: float = 0.0
    results: list[dict] = []

    for idx, item in enumerate(batch_request.items):
        try:
            result = await create_settlement(db=db, request=item, user_did=user_did)
            success_count += 1
            total_amount += result.get("amount", 0.0)
            results.append({
                "index": idx,
                "status": "success",
                "billing_id": result.get("billing_id"),
                "tx_hash": result.get("tx_hash"),
                "amount": result.get("amount"),
                "subscription_id": result.get("subscription_id"),
            })
        except Exception as e:
            failure_count += 1
            logger.error(f"Batch settlement failed at index {idx}: {e}")
            results.append({
                "index": idx,
                "status": "failed",
                "error": str(e),
                "subscription_id": item.subscription_id,
                "amount": item.amount,
            })

    return SettlementBatchResult(
        total=total,
        success_count=success_count,
        failure_count=failure_count,
        total_amount=total_amount,
        results=results,
    )


async def reconciliation(
    db: AsyncSession,
    billing_period: str,
    subscription_id: Optional[str] = None,
) -> SettlementReconciliation:
    """
    结算对账

    对比数据库结算记录与链上交易记录的一致性。
    检查:
    - 数据库中有但链上无对应交易的记录
    - 链上有交易但数据库无对应记录的记录
    - 金额不一致的记录

    Args:
        db: 异步数据库会话
        billing_period: 计费周期（如 "2024-01"）
        subscription_id: 按订阅筛选（可选）

    Returns:
        对账结果
    """
    # 1. 查询数据库结算记录
    query = select(BillingRecord).where(
        BillingRecord.billing_period == billing_period
    )
    if subscription_id:
        query = query.where(
            BillingRecord.subscription_id == uuid.UUID(subscription_id)
        )
    db_result = await db.execute(query)
    db_records = db_result.scalars().all()

    # 2. 查询链上交易记录（通过 BlockchainTransaction）
    chain_query = select(BlockchainTransaction).where(
        and_(
            BlockchainTransaction.method == "createSettlement",
            BlockchainTransaction.params["billing_period"].as_string() == billing_period,
        )
    )
    chain_result = await db.execute(chain_query)
    chain_records = chain_result.scalars().all()

    # 3. 构建映射
    db_map: dict[str, dict] = {}
    for r in db_records:
        db_map[str(r.id)] = {
            "id": str(r.id),
            "subscription_id": str(r.subscription_id),
            "amount": float(r.amount),
            "billing_period": r.billing_period,
            "payment_status": r.payment_status,
            "tx_hash": r.tx_hash,
        }

    chain_map: dict[str, dict] = {}
    for r in chain_records:
        tx_hash = r.tx_hash
        params = r.params or {}
        chain_map[tx_hash] = {
            "tx_hash": tx_hash,
            "amount": float(params.get("amount", 0)),
            "subscription_id": params.get("subscription_id", ""),
        }

    # 4. 对账比较
    reconciled: list[SettlementReconciliationItem] = []
    discrepancies: list[SettlementReconciliationItem] = []
    db_only: list[SettlementReconciliationItem] = []
    chain_only: list[SettlementReconciliationItem] = []

    # 遍历数据库记录
    matched_db_ids: set[str] = set()
    matched_chain_hashes: set[str] = set()

    for db_id, db_item in db_map.items():
        tx_hash = db_item.get("tx_hash", "")
        if tx_hash and tx_hash in chain_map:
            chain_item = chain_map[tx_hash]
            # 比较金额
            amount_match = abs(db_item["amount"] - chain_item["amount"]) < 0.01
            item = SettlementReconciliationItem(
                billing_id=db_id,
                tx_hash=tx_hash,
                db_amount=db_item["amount"],
                chain_amount=chain_item["amount"],
                amount_match=amount_match,
                subscription_id=db_item["subscription_id"],
                payment_status=db_item["payment_status"],
            )
            if amount_match:
                reconciled.append(item)
            else:
                discrepancies.append(item)
            matched_db_ids.add(db_id)
            matched_chain_hashes.add(tx_hash)
        else:
            db_only.append(SettlementReconciliationItem(
                billing_id=db_id,
                tx_hash="",
                db_amount=db_item["amount"],
                chain_amount=0.0,
                amount_match=False,
                subscription_id=db_item["subscription_id"],
                payment_status=db_item["payment_status"],
            ))

    # 找链上有但数据库没有的
    for tx_hash, chain_item in chain_map.items():
        if tx_hash not in matched_chain_hashes:
            chain_only.append(SettlementReconciliationItem(
                billing_id="",
                tx_hash=tx_hash,
                db_amount=0.0,
                chain_amount=chain_item["amount"],
                amount_match=False,
                subscription_id=chain_item["subscription_id"],
                payment_status="",
            ))

    # 5. 汇总
    total_db_records: int = len(db_records)
    total_chain_records: int = len(chain_records)
    match_count: int = len(reconciled)
    discrepancy_count: int = len(discrepancies) + len(db_only) + len(chain_only)
    is_consistent: bool = discrepancy_count == 0

    return SettlementReconciliation(
        billing_period=billing_period,
        subscription_id_filter=subscription_id,
        total_db_records=total_db_records,
        total_chain_records=total_chain_records,
        match_count=match_count,
        discrepancy_count=discrepancy_count,
        is_consistent=is_consistent,
        reconciled=reconciled,
        discrepancies=discrepancies,
        db_only=db_only,
        chain_only=chain_only,
    )


async def generate_settlement_report(
    db: AsyncSession,
    request: SettlementReportRequest,
) -> SettlementReportResponse:
    """
    生成结算报告

    汇总指定条件下的结算数据，生成结构化报告:
    - 总结算金额/笔数
    - 按状态分组统计
    - 按计费周期统计
    - 链上交易统计

    Args:
        db: 异步数据库会话
        request: 报告请求参数

    Returns:
        结算报告响应
    """
    # 1. 基础查询条件
    conditions = []
    if request.billing_period:
        conditions.append(BillingRecord.billing_period == request.billing_period)
    if request.subscription_id:
        conditions.append(
            BillingRecord.subscription_id == uuid.UUID(request.subscription_id)
        )
    if request.start_date:
        conditions.append(BillingRecord.created_at >= request.start_date)
    if request.end_date:
        conditions.append(BillingRecord.created_at <= request.end_date)

    where_clause = and_(*conditions) if conditions else True

    # 2. 总量统计
    total_query = select(
        func.count(BillingRecord.id).label("count"),
        func.coalesce(func.sum(BillingRecord.amount), 0).label("total_amount"),
    ).where(where_clause)
    total_result = await db.execute(total_query)
    total_row = total_result.one()

    total_count: int = int(total_row.count) if total_row else 0
    total_amount: float = float(total_row.total_amount) if total_row else 0.0

    # 3. 按状态分组统计
    status_query = (
        select(
            BillingRecord.payment_status,
            func.count(BillingRecord.id).label("count"),
            func.coalesce(func.sum(BillingRecord.amount), 0).label("amount"),
        )
        .where(where_clause)
        .group_by(BillingRecord.payment_status)
    )
    status_result = await db.execute(status_query)
    status_rows = status_result.all()

    status_breakdown: dict[str, dict] = {}
    for row in status_rows:
        status_breakdown[row.payment_status] = {
            "count": int(row.count),
            "amount": float(row.amount),
        }

    # 4. 按计费周期统计
    period_query = (
        select(
            BillingRecord.billing_period,
            func.count(BillingRecord.id).label("count"),
            func.coalesce(func.sum(BillingRecord.amount), 0).label("amount"),
        )
        .where(where_clause)
        .group_by(BillingRecord.billing_period)
        .order_by(BillingRecord.billing_period.desc())
    )
    period_result = await db.execute(period_query)
    period_rows = period_result.all()

    period_breakdown: list[dict] = []
    for row in period_rows:
        period_breakdown.append({
            "billing_period": row.billing_period,
            "count": int(row.count),
            "amount": float(row.amount),
        })

    # 5. 链上交易统计
    chain_tx_count: int = 0
    try:
        chain_query = select(func.count(BlockchainTransaction.id)).where(
            BlockchainTransaction.method == "createSettlement"
        )
        chain_result = await db.execute(chain_query)
        chain_tx_count = chain_result.scalar() or 0
    except Exception as e:
        logger.warning(f"Failed to query chain transaction count: {e}")

    # 6. 计算成功率
    paid_count: int = status_breakdown.get("paid", {}).get("count", 0)
    success_rate: float = (paid_count / total_count * 100.0) if total_count > 0 else 0.0

    # 7. 生成摘要
    summary_parts: list[str] = [
        f"报告期间: {request.billing_period or '全部'}",
        f"总结算笔数: {total_count}",
        f"总结算金额: {total_amount:.2f}",
        f"成功率: {success_rate:.1f}%",
    ]
    if request.subscription_id:
        summary_parts.append(f"订阅 ID: {request.subscription_id}")

    return SettlementReportResponse(
        billing_period=request.billing_period,
        subscription_id=request.subscription_id,
        total_count=total_count,
        total_amount=total_amount,
        success_rate=round(success_rate, 2),
        status_breakdown=status_breakdown,
        period_breakdown=period_breakdown,
        chain_tx_count=chain_tx_count,
        generated_at=datetime.now(timezone.utc),
        summary=" | ".join(summary_parts),
    )
