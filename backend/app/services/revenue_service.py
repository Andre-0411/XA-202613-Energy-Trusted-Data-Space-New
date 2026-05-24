"""
收益分配服务
收益计算模型：数据质量40%×使用次数60%
平台服务费：5%
算法贡献：10%
数据治理奖励：5%

收益分配公式：
  数据提供方收益 = 总收益 × (数据质量得分×40% + 使用次数得分×60%) × (1 - 平台费率)
  平台收益 = 总收益 × 平台费率(5%)
  算法贡献收益 = 总收益 × 算法贡献率(10%)
  数据治理奖励 = 总收益 × 治理奖励率(5%)
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Organization
from app.models.service import BillingRecord
from app.models.data_asset import DataAsset
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query

logger = logging.getLogger(__name__)

# 收益分配比例
PLATFORM_FEE_RATE = 0.05       # 平台服务费 5%
ALGORITHM_CONTRIBUTION_RATE = 0.10  # 算法贡献 10%
DATA_GOVERNANCE_RATE = 0.05    # 数据治理奖励 5%
DATA_QUALITY_WEIGHT = 0.40     # 数据质量权重 40%
USAGE_COUNT_WEIGHT = 0.60      # 使用次数权重 60%

# 收益分配存储
_revenue_distributions: Dict[str, dict] = {}
_revenue_settlements: Dict[str, dict] = {}


def _calculate_quality_score(data_asset: dict) -> float:
    """
    计算数据质量得分 (0-100)

    基于以下维度：
    - 完整性: 字段填充率
    - 准确性: 数据校验通过率
    - 时效性: 数据更新频率
    - 一致性: 数据格式一致性
    """
    completeness = data_asset.get("completeness_score", 80.0)
    accuracy = data_asset.get("accuracy_score", 85.0)
    timeliness = data_asset.get("timeliness_score", 90.0)
    consistency = data_asset.get("consistency_score", 88.0)

    quality_score = (
        completeness * 0.3 +
        accuracy * 0.3 +
        timeliness * 0.2 +
        consistency * 0.2
    )
    return min(100.0, max(0.0, quality_score))


def _calculate_usage_score(usage_count: int, max_usage: int = 10000) -> float:
    """
    计算使用次数得分 (0-100)

    使用对数归一化，避免极端值影响

    Args:
        usage_count: 实际使用次数
        max_usage: 最大使用次数基准

    Returns:
        使用次数得分
    """
    import math
    if usage_count <= 0:
        return 0.0
    if usage_count >= max_usage:
        return 100.0
    return (math.log(usage_count + 1) / math.log(max_usage + 1)) * 100


async def calculate_revenue_distribution(
    db: AsyncSession,
    period: str,
    organization_id: Optional[str] = None,
) -> dict:
    """
    计算指定账期的收益分配

    Args:
        db: 数据库会话
        period: 账期 YYYY-MM
        organization_id: 可选，指定组织 ID

    Returns:
        收益分配结果
    """
    # 获取账期的计费记录
    query = select(BillingRecord).where(
        BillingRecord.billing_period == period
    )
    if organization_id:
        query = query.where(
            BillingRecord.organization_id == uuid.UUID(organization_id)
        )

    result = await db.execute(query)
    billing_records = result.scalars().all()

    if not billing_records:
        return {
            "period": period,
            "total_revenue": 0.0,
            "distributions": [],
            "summary": {
                "platform_fee": 0.0,
                "algorithm_contribution": 0.0,
                "data_governance_reward": 0.0,
                "data_provider_total": 0.0,
            },
        }

    # 计算总收益
    total_revenue = sum(float(r.amount) for r in billing_records)

    # 按组织分组计算
    org_revenues: Dict[str, float] = {}
    for record in billing_records:
        org_id = str(record.organization_id)
        org_revenues[org_id] = org_revenues.get(org_id, 0.0) + float(record.amount)

    # 计算各组织的收益分配
    distributions = []
    for org_id, org_revenue in org_revenues.items():
        # 获取组织信息
        org_result = await db.execute(
            select(Organization).where(Organization.id == uuid.UUID(org_id))
        )
        org = org_result.scalar_one_or_none()
        org_name = org.name if org else "未知组织"

        # 获取该组织的数据资产使用情况
        assets_result = await db.execute(
            select(DataAsset).where(DataAsset.owner_org_id == uuid.UUID(org_id))
        )
        assets = assets_result.scalars().all()

        # 计算数据质量得分（所有资产的平均质量）
        if assets:
            quality_scores = [
                _calculate_quality_score({
                    "completeness_score": getattr(a, "completeness_score", 80.0) or 80.0,
                    "accuracy_score": getattr(a, "accuracy_score", 85.0) or 85.0,
                    "timeliness_score": getattr(a, "timeliness_score", 90.0) or 90.0,
                    "consistency_score": getattr(a, "consistency_score", 88.0) or 88.0,
                })
                for a in assets
            ]
            avg_quality_score = sum(quality_scores) / len(quality_scores)
            total_usage = sum(getattr(a, "access_count", 0) or 0 for a in assets)
        else:
            avg_quality_score = 80.0
            total_usage = 0

        usage_score = _calculate_usage_score(total_usage)

        # 计算综合得分
        composite_score = (
            avg_quality_score * DATA_QUALITY_WEIGHT +
            usage_score * USAGE_COUNT_WEIGHT
        )

        # 计算分配金额
        provider_share = org_revenue * (1 - PLATFORM_FEE_RATE) * (composite_score / 100.0)
        platform_fee = org_revenue * PLATFORM_FEE_RATE
        algorithm_share = org_revenue * ALGORITHM_CONTRIBUTION_RATE
        governance_share = org_revenue * DATA_GOVERNANCE_RATE

        distributions.append({
            "organization_id": org_id,
            "organization_name": org_name,
            "total_revenue": round(org_revenue, 2),
            "quality_score": round(avg_quality_score, 2),
            "usage_score": round(usage_score, 2),
            "composite_score": round(composite_score, 2),
            "provider_share": round(provider_share, 2),
            "platform_fee": round(platform_fee, 2),
            "algorithm_contribution": round(algorithm_share, 2),
            "governance_reward": round(governance_share, 2),
            "data_asset_count": len(assets) if assets else 0,
            "total_usage_count": total_usage,
        })

    # 汇总
    summary = {
        "platform_fee": round(total_revenue * PLATFORM_FEE_RATE, 2),
        "algorithm_contribution": round(total_revenue * ALGORITHM_CONTRIBUTION_RATE, 2),
        "data_governance_reward": round(total_revenue * DATA_GOVERNANCE_RATE, 2),
        "data_provider_total": round(
            total_revenue * (1 - PLATFORM_FEE_RATE - ALGORITHM_CONTRIBUTION_RATE - DATA_GOVERNANCE_RATE), 2
        ),
    }

    return {
        "period": period,
        "total_revenue": round(total_revenue, 2),
        "distributions": distributions,
        "summary": summary,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_revenue_summary(
    db: AsyncSession,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> dict:
    """
    获取收益分配汇总

    Args:
        db: 数据库会话
        start_period: 开始账期
        end_period: 结束账期
        organization_id: 组织 ID

    Returns:
        收益汇总
    """
    query = select(
        BillingRecord.billing_period,
        func.sum(BillingRecord.amount).label("total_amount"),
        func.count(BillingRecord.id).label("record_count"),
    ).group_by(BillingRecord.billing_period)

    if start_period:
        query = query.where(BillingRecord.billing_period >= start_period)
    if end_period:
        query = query.where(BillingRecord.billing_period <= end_period)
    if organization_id:
        query = query.where(BillingRecord.organization_id == uuid.UUID(organization_id))

    query = query.order_by(BillingRecord.billing_period.desc())

    result = await db.execute(query)
    rows = result.all()

    periods = []
    total_revenue = 0.0
    for row in rows:
        period_revenue = float(row.total_amount)
        total_revenue += period_revenue
        periods.append({
            "period": row.billing_period,
            "total_revenue": round(period_revenue, 2),
            "record_count": row.record_count,
            "platform_fee": round(period_revenue * PLATFORM_FEE_RATE, 2),
            "provider_share": round(
                period_revenue * (1 - PLATFORM_FEE_RATE - ALGORITHM_CONTRIBUTION_RATE - DATA_GOVERNANCE_RATE), 2
            ),
        })

    return {
        "total_revenue": round(total_revenue, 2),
        "total_platform_fee": round(total_revenue * PLATFORM_FEE_RATE, 2),
        "total_algorithm_contribution": round(total_revenue * ALGORITHM_CONTRIBUTION_RATE, 2),
        "total_governance_reward": round(total_revenue * DATA_GOVERNANCE_RATE, 2),
        "total_provider_share": round(
            total_revenue * (1 - PLATFORM_FEE_RATE - ALGORITHM_CONTRIBUTION_RATE - DATA_GOVERNANCE_RATE), 2
        ),
        "periods": periods,
    }


async def create_settlement(
    db: AsyncSession,
    period: str,
    organization_id: str,
) -> dict:
    """
    创建结算单

    Args:
        db: 数据库会话
        period: 账期
        organization_id: 组织 ID

    Returns:
        结算单信息
    """
    # 计算收益分配
    distribution = await calculate_revenue_distribution(db, period, organization_id)

    if not distribution["distributions"]:
        return {"error": "该账期无计费记录"}

    org_dist = distribution["distributions"][0]

    settlement_id = f"settlement_{uuid.uuid4().hex[:8]}"
    settlement = {
        "settlement_id": settlement_id,
        "period": period,
        "organization_id": organization_id,
        "organization_name": org_dist["organization_name"],
        "total_revenue": org_dist["total_revenue"],
        "provider_share": org_dist["provider_share"],
        "platform_fee": org_dist["platform_fee"],
        "algorithm_contribution": org_dist["algorithm_contribution"],
        "governance_reward": org_dist["governance_reward"],
        "quality_score": org_dist["quality_score"],
        "usage_score": org_dist["usage_score"],
        "composite_score": org_dist["composite_score"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _revenue_settlements[settlement_id] = settlement
    logger.info(f"Settlement created: {settlement_id} for org {organization_id}, period {period}")
    return settlement


async def list_settlements(
    period: Optional[str] = None,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[dict]:
    """列出结算单"""
    settlements = list(_revenue_settlements.values())
    if period:
        settlements = [s for s in settlements if s.get("period") == period]
    if organization_id:
        settlements = [s for s in settlements if s.get("organization_id") == organization_id]
    if status:
        settlements = [s for s in settlements if s.get("status") == status]
    return settlements


async def confirm_settlement(settlement_id: str) -> Optional[dict]:
    """确认结算单"""
    settlement = _revenue_settlements.get(settlement_id)
    if not settlement:
        return None
    settlement["status"] = "confirmed"
    settlement["confirmed_at"] = datetime.now(timezone.utc).isoformat()
    return settlement
