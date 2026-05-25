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


# ==================== 价值评估增强 ====================

def calculate_data_scarcity_score(
    category: str,
    record_count: int,
    provider_count: int,
) -> float:
    """
    计算数据稀缺性得分 (0-100)

    稀缺性因素：
    - 数据类别稀缺度
    - 数据量稀缺度
    - 提供方数量

    Args:
        category: 数据类别
        record_count: 记录数量
        provider_count: 同类数据提供方数量

    Returns:
        稀缺性得分
    """
    # 类别稀缺度（能源数据空间特定类别更稀缺）
    category_scarcity = {
        "调度": 90,
        "市场": 85,
        "设备状态": 75,
        "发电": 60,
        "用电": 50,
        "地理信息": 40,
    }
    base_score = category_scarcity.get(category, 50)

    # 数据量因子（数据量越少越稀缺）
    if record_count < 1000:
        volume_factor = 1.2
    elif record_count < 10000:
        volume_factor = 1.0
    elif record_count < 100000:
        volume_factor = 0.8
    else:
        volume_factor = 0.6

    # 提供方因子（提供方越少越稀缺）
    if provider_count <= 1:
        provider_factor = 1.3
    elif provider_count <= 3:
        provider_factor = 1.0
    elif provider_count <= 10:
        provider_factor = 0.8
    else:
        provider_factor = 0.6

    scarcity_score = base_score * volume_factor * provider_factor
    return min(100.0, max(0.0, scarcity_score))


def calculate_timeliness_score(
    last_updated_at: Optional[datetime],
    update_frequency_hours: float = 24.0,
) -> float:
    """
    计算数据时效性得分 (0-100)

    时效性因素：
    - 最后更新时间
    - 更新频率

    Args:
        last_updated_at: 最后更新时间
        update_frequency_hours: 更新频率（小时）

    Returns:
        时效性得分
    """
    if not last_updated_at:
        return 50.0

    now = datetime.now(timezone.utc)
    if last_updated_at.tzinfo is None:
        last_updated_at = last_updated_at.replace(tzinfo=timezone.utc)

    hours_since_update = (now - last_updated_at).total_seconds() / 3600

    # 基于更新延迟计算得分
    if hours_since_update < 1:
        delay_score = 100.0
    elif hours_since_update < 6:
        delay_score = 90.0
    elif hours_since_update < 24:
        delay_score = 75.0
    elif hours_since_update < 72:
        delay_score = 60.0
    elif hours_since_update < 168:
        delay_score = 40.0
    else:
        delay_score = 20.0

    # 基于更新频率调整
    if update_frequency_hours <= 1:
        frequency_bonus = 10.0
    elif update_frequency_hours <= 6:
        frequency_bonus = 5.0
    elif update_frequency_hours <= 24:
        frequency_bonus = 0.0
    else:
        frequency_bonus = -5.0

    return min(100.0, max(0.0, delay_score + frequency_bonus))


def calculate_comprehensive_value_score(
    data_asset: dict,
    usage_stats: dict,
    market_info: Optional[dict] = None,
) -> dict:
    """
    计算数据资产综合价值评分

    价值维度：
    1. 数据质量 (30%)
    2. 使用频率 (25%)
    3. 稀缺性 (20%)
    4. 时效性 (15%)
    5. 安全等级 (10%)

    Args:
        data_asset: 数据资产信息
        usage_stats: 使用统计信息
        market_info: 市场信息（可选）

    Returns:
        综合价值评分
    """
    # 1. 数据质量得分 (30%)
    quality_score = _calculate_quality_score(data_asset)
    quality_weight = 0.30

    # 2. 使用频率得分 (25%)
    usage_count = usage_stats.get("total_access_count", 0)
    usage_score = _calculate_usage_score(usage_count)
    usage_weight = 0.25

    # 3. 稀缺性得分 (20%)
    category = data_asset.get("category", "其他")
    record_count = data_asset.get("record_count", 0)
    provider_count = market_info.get("provider_count", 5) if market_info else 5
    scarcity_score = calculate_data_scarcity_score(category, record_count, provider_count)
    scarcity_weight = 0.20

    # 4. 时效性得分 (15%)
    last_updated = data_asset.get("updated_at")
    update_frequency = data_asset.get("update_frequency_hours", 24.0)
    timeliness_score = calculate_timeliness_score(last_updated, update_frequency)
    timeliness_weight = 0.15

    # 5. 安全等级得分 (10%)
    security_level = data_asset.get("classification_level", 4)
    security_score = {1: 100, 2: 80, 3: 60, 4: 40}.get(security_level, 40)
    security_weight = 0.10

    # 计算综合得分
    comprehensive_score = (
        quality_score * quality_weight +
        usage_score * usage_weight +
        scarcity_score * scarcity_weight +
        timeliness_score * timeliness_weight +
        security_score * security_weight
    )

    return {
        "comprehensive_score": round(comprehensive_score, 2),
        "dimensions": {
            "quality": {"score": round(quality_score, 2), "weight": quality_weight},
            "usage": {"score": round(usage_score, 2), "weight": usage_weight},
            "scarcity": {"score": round(scarcity_score, 2), "weight": scarcity_weight},
            "timeliness": {"score": round(timeliness_score, 2), "weight": timeliness_weight},
            "security": {"score": round(security_score, 2), "weight": security_weight},
        },
        "grade": _get_value_grade(comprehensive_score),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


def _get_value_grade(score: float) -> str:
    """获取价值评级"""
    if score >= 90:
        return "S"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "E"


# ==================== 多种计费模型 ====================

async def calculate_billing_by_usage(
    db: AsyncSession,
    asset_id: str,
    usage_records: List[dict],
    unit_price: float = 0.01,
) -> dict:
    """
    按使用量计费

    计费规则：
    - 按API调用次数计费
    - 按数据下载量计费
    - 按计算任务次数计费

    Args:
        db: 数据库会话
        asset_id: 数据资产ID
        usage_records: 使用记录列表
        unit_price: 单价

    Returns:
        计费结果
    """
    total_usage = len(usage_records)
    total_amount = total_usage * unit_price

    # 计算阶梯价格（使用量越大，单价越低）
    if total_usage > 10000:
        discount = 0.8
    elif total_usage > 1000:
        discount = 0.9
    else:
        discount = 1.0

    discounted_amount = total_amount * discount

    return {
        "billing_model": "usage_based",
        "asset_id": asset_id,
        "total_usage": total_usage,
        "unit_price": unit_price,
        "discount": discount,
        "total_amount": round(total_amount, 2),
        "discounted_amount": round(discounted_amount, 2),
        "currency": "CNY",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


async def calculate_billing_by_effect(
    db: AsyncSession,
    asset_id: str,
    effect_metrics: dict,
    base_price: float = 100.0,
) -> dict:
    """
    按效果分成计费

    计费规则：
    - 按数据使用效果（如预测准确率提升）分成
    - 按业务指标改善分成

    Args:
        db: 数据库会话
        asset_id: 数据资产ID
        effect_metrics: 效果指标
        base_price: 基础价格

    Returns:
        计费结果
    """
    # 效果指标
    accuracy_improvement = effect_metrics.get("accuracy_improvement", 0)
    business_value = effect_metrics.get("business_value", 0)
    cost_reduction = effect_metrics.get("cost_reduction", 0)

    # 计算效果得分
    effect_score = (
        accuracy_improvement * 0.4 +
        business_value * 0.3 +
        cost_reduction * 0.3
    )

    # 效果分成比例（效果越好，分成越高）
    if effect_score > 0.5:
        share_ratio = 0.3
    elif effect_score > 0.3:
        share_ratio = 0.2
    elif effect_score > 0.1:
        share_ratio = 0.1
    else:
        share_ratio = 0.05

    total_amount = base_price + (business_value * share_ratio)

    return {
        "billing_model": "effect_based",
        "asset_id": asset_id,
        "effect_metrics": effect_metrics,
        "effect_score": round(effect_score, 4),
        "share_ratio": share_ratio,
        "base_price": base_price,
        "total_amount": round(total_amount, 2),
        "currency": "CNY",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


async def calculate_billing_fixed(
    db: AsyncSession,
    asset_id: str,
    subscription_type: str = "monthly",
    monthly_price: float = 1000.0,
    duration_months: int = 1,
) -> dict:
    """
    固定费用计费

    计费规则：
    - 按月/季/年固定费用
    - 包含一定使用额度

    Args:
        db: 数据库会话
        asset_id: 数据资产ID
        subscription_type: 订阅类型 (monthly/quarterly/yearly)
        monthly_price: 月价格
        duration_months: 订阅月数

    Returns:
        计费结果
    """
    # 订阅类型折扣
    type_discount = {
        "monthly": 1.0,
        "quarterly": 0.95,
        "yearly": 0.85,
    }
    discount = type_discount.get(subscription_type, 1.0)

    # 计算总费用
    base_amount = monthly_price * duration_months
    total_amount = base_amount * discount

    # 包含的使用额度
    included_quota = {
        "monthly": 10000,
        "quarterly": 35000,
        "yearly": 150000,
    }
    quota = included_quota.get(subscription_type, 10000) * duration_months

    return {
        "billing_model": "fixed_fee",
        "asset_id": asset_id,
        "subscription_type": subscription_type,
        "duration_months": duration_months,
        "monthly_price": monthly_price,
        "discount": discount,
        "base_amount": round(base_amount, 2),
        "total_amount": round(total_amount, 2),
        "included_quota": quota,
        "currency": "CNY",
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== 自动结算与区块链存证 ====================

async def create_automated_settlement(
    db: AsyncSession,
    billing_period: str,
    organization_id: Optional[str] = None,
    enable_blockchain: bool = True,
) -> dict:
    """
    自动结算与区块链存证

    步骤：
    1. 汇总账期所有计费记录
    2. 计算收益分配
    3. 生成结算单
    4. 上链存证
    5. 触发支付

    Args:
        db: 数据库会话
        billing_period: 账期 YYYY-MM
        organization_id: 组织ID（可选）
        enable_blockchain: 是否启用区块链存证

    Returns:
        结算结果
    """
    # 1. 计算收益分配
    distribution = await calculate_revenue_distribution(db, billing_period, organization_id)

    if not distribution["distributions"]:
        return {
            "status": "no_records",
            "billing_period": billing_period,
            "message": "该账期无计费记录",
        }

    # 2. 生成结算单
    settlement_id = str(uuid.uuid4())
    settlement = {
        "settlement_id": settlement_id,
        "billing_period": billing_period,
        "total_revenue": distribution["total_revenue"],
        "distributions": distribution["distributions"],
        "summary": distribution["summary"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 3. 上链存证
    if enable_blockchain:
        try:
            from app.core.gmssl_adapter import gmssl_adapter
            from app.services.blockchain_evidence_service import submit_evidence
            from app.schemas.blockchain import EvidenceCreate

            settlement_hash = gmssl_adapter.sm3_hash(str(settlement))
            evidence = await submit_evidence(
                db,
                EvidenceCreate(
                    node_type="settle",
                    resource_id=settlement_id,
                    resource_type="revenue_settlement",
                    data_hash=settlement_hash,
                    evidence_data={
                        "settlement_id": settlement_id,
                        "billing_period": billing_period,
                        "total_revenue": distribution["total_revenue"],
                        "distribution_count": len(distribution["distributions"]),
                        "settlement_hash": settlement_hash,
                    },
                ),
            )
            settlement["tx_hash"] = evidence.tx_hash if hasattr(evidence, "tx_hash") else ""
            settlement["blockchain_recorded"] = True
        except Exception as e:
            logger.warning(f"Settlement blockchain recording failed: {e}")
            settlement["blockchain_recorded"] = False

    # 4. 存储结算单
    settlement["status"] = "completed"
    _revenue_settlements[settlement_id] = settlement

    logger.info(f"Automated settlement created: {settlement_id}, period={billing_period}")
    return settlement


async def generate_invoice(
    db: AsyncSession,
    settlement_id: str,
    invoice_type: str = "digital",
) -> dict:
    """
    生成账单/发票

    Args:
        db: 数据库会话
        settlement_id: 结算单ID
        invoice_type: 发票类型 (digital/paper)

    Returns:
        发票信息
    """
    settlement = _revenue_settlements.get(settlement_id)
    if not settlement:
        raise DataNotFoundError(f"结算单未找到: {settlement_id}")

    invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    invoice = {
        "invoice_id": invoice_id,
        "settlement_id": settlement_id,
        "invoice_type": invoice_type,
        "amount": settlement["total_revenue"],
        "currency": "CNY",
        "status": "issued",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "items": [
            {
                "description": f"数据服务费用 - {settlement['billing_period']}",
                "amount": settlement["total_revenue"],
                "tax_rate": 0.06,
                "tax_amount": round(settlement["total_revenue"] * 0.06, 2),
            }
        ],
    }

    logger.info(f"Invoice generated: {invoice_id} for settlement {settlement_id}")
    return invoice


# ==================== 收益争议处理 ====================

# 争议存储
_revenue_disputes: Dict[str, dict] = {}


async def submit_revenue_dispute(
    db: AsyncSession,
    settlement_id: str,
    submitter_id: str,
    dispute_type: str,
    dispute_amount: float,
    reason: str,
    evidence: Optional[List[dict]] = None,
) -> dict:
    """
    提交收益争议

    争议类型：
    - amount_dispute: 金额争议
    - quality_dispute: 质量评分争议
    - usage_dispute: 使用量争议
    - distribution_dispute: 分配比例争议

    Args:
        db: 数据库会话
        settlement_id: 结算单ID
        submitter_id: 提交者ID
        dispute_type: 争议类型
        dispute_amount: 争议金额
        reason: 争议原因
        evidence: 证据材料

    Returns:
        争议记录
    """
    settlement = _revenue_settlements.get(settlement_id)
    if not settlement:
        raise DataNotFoundError(f"结算单未找到: {settlement_id}")

    dispute_id = str(uuid.uuid4())
    dispute = {
        "dispute_id": dispute_id,
        "settlement_id": settlement_id,
        "submitter_id": submitter_id,
        "dispute_type": dispute_type,
        "dispute_amount": dispute_amount,
        "reason": reason,
        "evidence": evidence or [],
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    _revenue_disputes[dispute_id] = dispute

    # 更新结算单状态
    settlement["status"] = "disputed"
    settlement["dispute_id"] = dispute_id

    logger.info(f"Revenue dispute submitted: {dispute_id}, settlement={settlement_id}")
    return dispute


async def review_revenue_dispute(
    db: AsyncSession,
    dispute_id: str,
    reviewer_id: str,
    review_result: str,
    resolution: dict,
) -> dict:
    """
    审核收益争议

    Args:
        db: 数据库会话
        dispute_id: 争议ID
        reviewer_id: 审核者ID
        review_result: 审核结果 (approved/rejected/partial)
        resolution: 解决方案

    Returns:
        审核结果
    """
    dispute = _revenue_disputes.get(dispute_id)
    if not dispute:
        raise DataNotFoundError(f"争议记录未找到: {dispute_id}")

    dispute["status"] = "reviewed"
    dispute["reviewer_id"] = reviewer_id
    dispute["review_result"] = review_result
    dispute["resolution"] = resolution
    dispute["reviewed_at"] = datetime.now(timezone.utc).isoformat()

    # 根据审核结果处理
    settlement = _revenue_settlements.get(dispute["settlement_id"])
    if settlement:
        if review_result == "approved":
            # 调整结算金额
            adjustment = resolution.get("adjustment_amount", 0)
            settlement["total_revenue"] = round(settlement["total_revenue"] + adjustment, 2)
            settlement["status"] = "adjusted"
        elif review_result == "rejected":
            settlement["status"] = "completed"
        elif review_result == "partial":
            partial_adjustment = resolution.get("partial_adjustment", 0)
            settlement["total_revenue"] = round(settlement["total_revenue"] + partial_adjustment, 2)
            settlement["status"] = "partially_adjusted"

    logger.info(f"Revenue dispute reviewed: {dispute_id}, result={review_result}")
    return dispute


async def get_dispute_statistics(
    db: AsyncSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """
    获取争议统计

    Args:
        db: 数据库会话
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        争议统计
    """
    disputes = list(_revenue_disputes.values())

    # 按日期过滤
    if start_date:
        disputes = [d for d in disputes if d["submitted_at"] >= start_date]
    if end_date:
        disputes = [d for d in disputes if d["submitted_at"] <= end_date]

    total_disputes = len(disputes)
    if total_disputes == 0:
        return {
            "total_disputes": 0,
            "by_status": {},
            "by_type": {},
            "total_dispute_amount": 0,
            "resolution_rate": 0,
        }

    # 按状态统计
    by_status = {}
    for d in disputes:
        status = d["status"]
        by_status[status] = by_status.get(status, 0) + 1

    # 按类型统计
    by_type = {}
    for d in disputes:
        dtype = d["dispute_type"]
        by_type[dtype] = by_type.get(dtype, 0) + 1

    # 总争议金额
    total_dispute_amount = sum(d["dispute_amount"] for d in disputes)

    # 解决率
    resolved_count = sum(1 for d in disputes if d["status"] in ["reviewed", "resolved"])
    resolution_rate = resolved_count / total_disputes if total_disputes > 0 else 0

    return {
        "total_disputes": total_disputes,
        "by_status": by_status,
        "by_type": by_type,
        "total_dispute_amount": round(total_dispute_amount, 2),
        "resolution_rate": round(resolution_rate, 4),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
