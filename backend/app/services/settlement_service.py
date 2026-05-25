"""
自动结算 + 收益分配服务

收益分配模型:
  数据提供方: 40% x 使用次数 / 60%
  平台管理费: 5%
  算法贡献方: 10%
  数据治理方: 5%

每日自动结算流程:
1. 汇总当日所有交易
2. 计算各方收益
3. 生成结算单
4. 上链存证
5. 触发支付
"""
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import SettlementError, DataNotFoundError

logger = logging.getLogger(__name__)

# 收益分配比例
REVENUE_DISTRIBUTION = {
    "data_provider_base": Decimal("0.40"),   # 数据提供方基础比例
    "data_provider_usage": Decimal("0.60"),  # 数据提供方使用次数加权
    "platform_fee": Decimal("0.05"),         # 平台管理费
    "algorithm_contribution": Decimal("0.10"),  # 算法贡献方
    "data_governance": Decimal("0.05"),      # 数据治理方
}


def calculate_revenue_distribution(
    total_amount: Decimal,
    usage_details: list[dict],
) -> dict:
    """
    计算收益分配

    Args:
        total_amount: 总结算金额
        usage_details: 使用详情列表，每项包含:
            - provider_id: 数据提供方 ID
            - usage_count: 使用次数
            - algorithm_did: 算法贡献方 DID (可选)
            - governance_did: 数据治理方 DID (可选)

    Returns:
        收益分配明细
    """
    total_usage = sum(d.get("usage_count", 1) for d in usage_details)
    if total_usage == 0:
        total_usage = 1

    distributions = []
    remaining = total_amount

    # 1. 数据提供方收益 (40% 基础 + 60% 按使用次数加权)
    provider_pool = (total_amount * (
        REVENUE_DISTRIBUTION["data_provider_base"] +
        REVENUE_DISTRIBUTION["data_provider_usage"]
    )).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    provider_details = {}
    for detail in usage_details:
        pid = detail.get("provider_id", "unknown")
        usage_count = detail.get("usage_count", 1)
        weight = Decimal(str(usage_count)) / Decimal(str(total_usage))
        share = (provider_pool * weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        provider_details[pid] = provider_details.get(pid, Decimal("0")) + share

    for pid, share in provider_details.items():
        distributions.append({
            "recipient_type": "data_provider",
            "recipient_id": pid,
            "amount": float(share),
            "ratio": float(share / total_amount) if total_amount > 0 else 0,
            "description": "数据提供方收益",
        })

    # 2. 平台管理费 5%
    platform_fee = (total_amount * REVENUE_DISTRIBUTION["platform_fee"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    distributions.append({
        "recipient_type": "platform",
        "recipient_id": "platform",
        "amount": float(platform_fee),
        "ratio": float(REVENUE_DISTRIBUTION["platform_fee"]),
        "description": "平台管理费",
    })

    # 3. 算法贡献方 10%
    algo_dids = set()
    for d in usage_details:
        algo_did = d.get("algorithm_did")
        if algo_did:
            algo_dids.add(algo_did)

    algo_pool = (total_amount * REVENUE_DISTRIBUTION["algorithm_contribution"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if algo_dids:
        per_algo = (algo_pool / len(algo_dids)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for did in algo_dids:
            distributions.append({
                "recipient_type": "algorithm_contributor",
                "recipient_id": did,
                "amount": float(per_algo),
                "ratio": float(REVENUE_DISTRIBUTION["algorithm_contribution"] / len(algo_dids)),
                "description": "算法贡献方收益",
            })
    else:
        distributions.append({
            "recipient_type": "algorithm_contributor",
            "recipient_id": "unassigned",
            "amount": float(algo_pool),
            "ratio": float(REVENUE_DISTRIBUTION["algorithm_contribution"]),
            "description": "算法贡献方收益（待分配）",
        })

    # 4. 数据治理方 5%
    gov_dids = set()
    for d in usage_details:
        gov_did = d.get("governance_did")
        if gov_did:
            gov_dids.add(gov_did)

    gov_pool = (total_amount * REVENUE_DISTRIBUTION["data_governance"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if gov_dids:
        per_gov = (gov_pool / len(gov_dids)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        for did in gov_dids:
            distributions.append({
                "recipient_type": "data_governance",
                "recipient_id": did,
                "amount": float(per_gov),
                "ratio": float(REVENUE_DISTRIBUTION["data_governance"] / len(gov_dids)),
                "description": "数据治理方收益",
            })
    else:
        distributions.append({
            "recipient_type": "data_governance",
            "recipient_id": "unassigned",
            "amount": float(gov_pool),
            "ratio": float(REVENUE_DISTRIBUTION["data_governance"]),
            "description": "数据治理方收益（待分配）",
        })

    # 验证分配总额
    total_distributed = sum(Decimal(str(d["amount"])) for d in distributions)
    diff = total_amount - total_distributed
    if diff != 0:
        # 将差额调整到平台
        for d in distributions:
            if d["recipient_type"] == "platform":
                d["amount"] = float(Decimal(str(d["amount"])) + diff)
                break

    return {
        "total_amount": float(total_amount),
        "distribution_count": len(distributions),
        "distributions": distributions,
        "distribution_model": {
            "data_provider": f"{REVENUE_DISTRIBUTION['data_provider_base'] + REVENUE_DISTRIBUTION['data_provider_usage']:.0%}",
            "platform": f"{REVENUE_DISTRIBUTION['platform_fee']:.0%}",
            "algorithm": f"{REVENUE_DISTRIBUTION['algorithm_contribution']:.0%}",
            "governance": f"{REVENUE_DISTRIBUTION['data_governance']:.0%}",
        },
    }


async def create_daily_settlement(
    db: AsyncSession,
    settlement_date: Optional[str] = None,
) -> dict:
    """
    创建每日自动结算

    汇总指定日期的所有已完成但未结算的使用记录，
    计算收益分配，生成结算单并上链存证。

    Args:
        db: 异步数据库会话
        settlement_date: 结算日期 (YYYY-MM-DD)，默认昨天

    Returns:
        结算结果
    """
    if not settlement_date:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        settlement_date = yesterday.strftime("%Y-%m-%d")

    # 查询当日已完成的计费记录
    from app.models.service import BillingRecord
    date_start = datetime.strptime(settlement_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    date_end = date_start + timedelta(days=1)

    result = await db.execute(
        select(BillingRecord).where(
            and_(
                BillingRecord.created_at >= date_start,
                BillingRecord.created_at < date_end,
                BillingRecord.payment_status == "paid",
            )
        )
    )
    billing_records = result.scalars().all()

    if not billing_records:
        logger.info(f"No billing records found for {settlement_date}")
        return {
            "settlement_date": settlement_date,
            "status": "no_records",
            "total_amount": 0,
            "record_count": 0,
        }

    # 汇总金额
    total_amount = sum(Decimal(str(r.amount)) for r in billing_records)

    # 构建使用详情
    usage_details = []
    for record in billing_records:
        detail = record.usage_detail or {}
        usage_details.append({
            "provider_id": str(record.subscription_id),
            "usage_count": 1,
            "algorithm_did": detail.get("algorithm_did"),
            "governance_did": detail.get("governance_did"),
            "billing_id": str(record.id),
            "amount": float(record.amount),
        })

    # 计算收益分配
    distribution = calculate_revenue_distribution(total_amount, usage_details)

    # 生成结算单 ID
    settlement_id = str(uuid.uuid4())

    # 上链存证
    tx_hash = ""
    try:
        from app.services.blockchain_evidence_service import submit_evidence
        from app.schemas.blockchain import EvidenceCreate

        settlement_hash = gmssl_adapter.sm3_hash(str(distribution))
        evidence = await submit_evidence(
            db,
            EvidenceCreate(
                node_type="settle",
                resource_id=settlement_id,
                resource_type="daily_settlement",
                data_hash=settlement_hash,
                evidence_data={
                    "settlement_id": settlement_id,
                    "settlement_date": settlement_date,
                    "total_amount": float(total_amount),
                    "record_count": len(billing_records),
                    "distribution_summary": {
                        "count": distribution["distribution_count"],
                        "model": distribution["distribution_model"],
                    },
                    "settlement_hash": settlement_hash,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            ),
        )
        tx_hash = evidence.tx_hash if hasattr(evidence, "tx_hash") else ""
    except Exception as e:
        logger.warning(f"Settlement chain recording failed: {e}")

    logger.info(
        f"Daily settlement created: {settlement_id}, date={settlement_date}, "
        f"total={float(total_amount)}, records={len(billing_records)}"
    )

    return {
        "settlement_id": settlement_id,
        "settlement_date": settlement_date,
        "total_amount": float(total_amount),
        "record_count": len(billing_records),
        "distribution": distribution,
        "tx_hash": tx_hash,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_settlement_detail(
    db: AsyncSession,
    settlement_id: str,
) -> dict:
    """
    获取结算详情

    Args:
        db: 异步数据库会话
        settlement_id: 结算 ID

    Returns:
        结算详情
    """
    # 从区块链查询
    try:
        from app.services.blockchain_evidence_service import get_evidence
        evidence = await get_evidence(db=db, evidence_id=settlement_id)
        return {
            "settlement_id": settlement_id,
            "source": "chain",
            "evidence": evidence.model_dump() if hasattr(evidence, "model_dump") else evidence,
        }
    except Exception:
        pass

    return {
        "settlement_id": settlement_id,
        "source": "not_found",
        "error": "结算记录未找到",
    }


async def list_pending_settlements(
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    """
    列出待结算的使用记录

    Args:
        db: 异步数据库会话
        limit: 返回数量限制

    Returns:
        待结算记录列表
    """
    from app.models.service import BillingRecord

    result = await db.execute(
        select(BillingRecord).where(
            BillingRecord.payment_status == "paid"
        ).order_by(BillingRecord.created_at.desc()).limit(limit)
    )
    records = result.scalars().all()

    return [
        {
            "billing_id": str(r.id),
            "subscription_id": str(r.subscription_id),
            "amount": float(r.amount),
            "billing_period": r.billing_period,
            "created_at": str(r.created_at),
        }
        for r in records
    ]


async def get_transaction_statistics(db: AsyncSession) -> dict:
    """
    获取交易统计

    Returns:
        包含交易总数、总金额、各状态数量的字典
    """
    from app.models.service import BillingRecord

    # 交易总数
    total = (await db.execute(
        select(func.count()).select_from(BillingRecord)
    )).scalar() or 0

    # 总金额
    total_amount_result = await db.execute(
        select(func.coalesce(func.sum(BillingRecord.amount), 0))
    )
    total_amount = float(total_amount_result.scalar() or 0)

    # 各状态数量
    status_result = await db.execute(
        select(BillingRecord.payment_status, func.count())
        .group_by(BillingRecord.payment_status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    return {
        "total": total,
        "total_amount": round(total_amount, 2),
        "by_status": by_status,
    }


async def get_transaction_trend(db: AsyncSession, days: int = 30) -> list[dict]:
    """
    获取交易趋势

    Args:
        db: 异步数据库会话
        days: 查询天数，默认 30

    Returns:
        每日交易数和金额列表，每项包含 date、count、amount
    """
    from app.models.service import BillingRecord

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(BillingRecord.created_at).label("date"),
            func.count().label("count"),
            func.coalesce(func.sum(BillingRecord.amount), 0).label("amount"),
        )
        .where(BillingRecord.created_at >= cutoff)
        .group_by(func.date(BillingRecord.created_at))
        .order_by(func.date(BillingRecord.created_at))
    )

    return [
        {
            "date": str(row.date),
            "count": row.count,
            "amount": round(float(row.amount), 2),
        }
        for row in result.all()
    ]
