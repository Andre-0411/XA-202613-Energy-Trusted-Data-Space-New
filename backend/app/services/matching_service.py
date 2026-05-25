"""
供需撮合服务
基于《可信数据空间标准体系建设指南》（2025版）和《可信数据空间 能力要求》(TDSA/A-001-2025)

功能：
1. 需求分析：需求解析、能力匹配
2. 智能推荐：基于历史数据的推荐算法
3. 撮合流程：需求发布 → 供需匹配 → 意向确认 → 合约签署
4. 效果评估：匹配成功率、用户满意度
"""
import uuid
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from collections import defaultdict

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_asset import DataAsset, DataSource
from app.models.demand import Demand, DemandClaim
from app.models.contract import Contract
from app.models.access_log import AccessLog
from app.models.user import Organization
from app.exceptions import DataNotFoundError, DataValidationError, MatchingError
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)


# ==================== 匹配模型定义 ====================

class MatchingStrategy(str, Enum):
    """匹配策略"""
    CONTENT_BASED = "content_based"        # 基于内容匹配
    COLLABORATIVE = "collaborative"        # 协同过滤
    HYBRID = "hybrid"                      # 混合推荐
    KEYWORD = "keyword"                    # 关键词匹配
    SEMANTIC = "semantic"                  # 语义匹配


class DemandStatus(str, Enum):
    """需求状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    MATCHING = "matching"
    MATCHED = "matched"
    NEGOTIATING = "negotiating"
    CONTRACTING = "contracting"
    FULFILLED = "fulfilled"
    CLOSED = "closed"
    EXPIRED = "expired"


class MatchConfidence(str, Enum):
    """匹配置信度"""
    HIGH = "high"          # 高置信度 (>0.8)
    MEDIUM = "medium"      # 中置信度 (0.6-0.8)
    LOW = "low"            # 低置信度 (0.4-0.6)
    VERY_LOW = "very_low"  # 极低置信度 (<0.4)


# 匹配权重配置
MATCHING_WEIGHTS = {
    "category_match": 0.25,        # 类别匹配
    "keyword_match": 0.20,         # 关键词匹配
    "quality_score": 0.15,         # 质量得分
    "freshness_score": 0.10,       # 新鲜度
    "security_level_match": 0.10,  # 安全等级匹配
    "provider_reliability": 0.10,  # 提供方可靠性
    "price_competitiveness": 0.10, # 价格竞争力
}


# ==================== 需求分析 ====================

async def analyze_demand(
    db: AsyncSession,
    demand_id: str,
) -> Dict[str, Any]:
    """
    需求分析

    步骤：
    1. 解析需求内容
    2. 提取关键特征
    3. 生成需求画像
    4. 识别匹配条件

    Args:
        db: 数据库会话
        demand_id: 需求ID

    Returns:
        需求分析结果
    """
    # 获取需求信息
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError(f"需求未找到: {demand_id}")

    # 提取关键特征
    features = _extract_demand_features(demand)

    # 生成需求画像
    profile = _generate_demand_profile(features)

    # 识别匹配条件
    matching_conditions = _identify_matching_conditions(features)

    logger.info(f"Demand analyzed: {demand_id}")
    return {
        "demand_id": demand_id,
        "demand_type": demand.demand_type,
        "title": demand.title,
        "features": features,
        "profile": profile,
        "matching_conditions": matching_conditions,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_demand_features(demand: Demand) -> Dict[str, Any]:
    """提取需求特征"""
    features = {
        "demand_type": demand.demand_type,
        "title_keywords": _extract_keywords(demand.title),
        "description_keywords": _extract_keywords(demand.description),
        "technical_requirements": demand.technical_requirements or {},
        "budget_range": demand.budget_range,
        "deadline": demand.deadline.isoformat() if demand.deadline else None,
    }

    # 从技术要求中提取特征
    tech_req = features["technical_requirements"]
    if isinstance(tech_req, dict):
        features["data_category"] = tech_req.get("data_category")
        features["security_level"] = tech_req.get("security_level")
        features["data_format"] = tech_req.get("data_format")
        features["update_frequency"] = tech_req.get("update_frequency")
        features["min_quality_score"] = tech_req.get("min_quality_score")

    return features


def _extract_keywords(text: str) -> List[str]:
    """提取关键词"""
    if not text:
        return []

    # 简单的关键词提取（实际应该使用NLP）
    import re

    # 能源领域关键词
    energy_keywords = [
        "风电", "光伏", "火电", "水电", "核电",
        "发电量", "功率", "电压", "电流", "频率",
        "气象", "风速", "温度", "湿度", "辐照度",
        "设备", "风机", "逆变器", "变压器",
        "调度", "负荷", "预测", "优化",
        "市场", "交易", "价格", "结算",
        "电网", "输电", "配电", "用电",
    ]

    found_keywords = []
    text_lower = text.lower()

    for keyword in energy_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)

    # 提取其他有意义的词
    words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
    for word in words:
        if word not in found_keywords and len(word) >= 2:
            found_keywords.append(word)

    return found_keywords[:20]  # 最多返回20个关键词


def _generate_demand_profile(features: Dict[str, Any]) -> Dict[str, Any]:
    """生成需求画像"""
    profile = {
        "data_needs": [],
        "quality_requirements": {},
        "security_requirements": {},
        "delivery_requirements": {},
        "budget_constraints": {},
    }

    # 数据需求
    if features.get("data_category"):
        profile["data_needs"].append({
            "type": "category",
            "value": features["data_category"],
        })

    # 质量要求
    if features.get("min_quality_score"):
        profile["quality_requirements"]["min_score"] = features["min_quality_score"]
    else:
        profile["quality_requirements"]["min_score"] = 0.7  # 默认

    # 安全要求
    if features.get("security_level"):
        profile["security_requirements"]["level"] = features["security_level"]
    else:
        profile["security_requirements"]["level"] = 3  # 默认敏感级

    # 交付要求
    if features.get("data_format"):
        profile["delivery_requirements"]["format"] = features["data_format"]
    if features.get("update_frequency"):
        profile["delivery_requirements"]["frequency"] = features["update_frequency"]

    # 预算约束
    if features.get("budget_range"):
        profile["budget_constraints"]["range"] = features["budget_range"]

    return profile


def _identify_matching_conditions(features: Dict[str, Any]) -> List[Dict[str, Any]]:
    """识别匹配条件"""
    conditions = []

    # 必要条件
    if features.get("data_category"):
        conditions.append({
            "field": "category",
            "operator": "eq",
            "value": features["data_category"],
            "required": True,
            "weight": MATCHING_WEIGHTS["category_match"],
        })

    # 关键词条件
    all_keywords = features.get("title_keywords", []) + features.get("description_keywords", [])
    if all_keywords:
        conditions.append({
            "field": "keywords",
            "operator": "contains_any",
            "value": list(set(all_keywords)),
            "required": False,
            "weight": MATCHING_WEIGHTS["keyword_match"],
        })

    # 安全等级条件
    if features.get("security_level"):
        conditions.append({
            "field": "classification_level",
            "operator": "lte",
            "value": features["security_level"],
            "required": True,
            "weight": MATCHING_WEIGHTS["security_level_match"],
        })

    # 质量条件
    min_quality = features.get("min_quality_score", 0.7)
    conditions.append({
        "field": "quality_score",
        "operator": "gte",
        "value": min_quality,
        "required": False,
        "weight": MATCHING_WEIGHTS["quality_score"],
    })

    return conditions


# ==================== 智能推荐 ====================

async def find_matching_assets(
    db: AsyncSession,
    demand_id: str,
    strategy: MatchingStrategy = MatchingStrategy.HYBRID,
    top_k: int = 10,
    min_confidence: float = 0.4,
) -> Dict[str, Any]:
    """
    智能匹配数据资产

    匹配策略：
    1. 内容匹配：基于类别、关键词、标签
    2. 协同过滤：基于历史使用行为
    3. 混合推荐：结合多种策略

    Args:
        db: 数据库会话
        demand_id: 需求ID
        strategy: 匹配策略
        top_k: 返回数量
        min_confidence: 最小置信度

    Returns:
        匹配结果
    """
    # 1. 分析需求
    demand_analysis = await analyze_demand(db, demand_id)
    features = demand_analysis["features"]
    conditions = demand_analysis["matching_conditions"]

    # 2. 获取候选资产
    query = select(DataAsset).where(
        and_(
            DataAsset.status == "published",
            DataAsset.classification_level.isnot(None),
        )
    )

    # 应用必要条件过滤
    if features.get("data_category"):
        query = query.where(DataAsset.category == features["data_category"])

    if features.get("security_level"):
        query = query.where(DataAsset.classification_level <= features["security_level"])

    result = await db.execute(query.limit(100))  # 限制候选集大小
    candidates = result.scalars().all()

    # 3. 计算匹配分数
    scored_candidates = []
    for candidate in candidates:
        score_details = await _calculate_match_score(
            db, candidate, features, conditions, strategy
        )
        if score_details["total_score"] >= min_confidence:
            scored_candidates.append({
                "asset": candidate,
                "score_details": score_details,
            })

    # 4. 排序并返回Top-K
    scored_candidates.sort(key=lambda x: x["score_details"]["total_score"], reverse=True)
    top_matches = scored_candidates[:top_k]

    # 5. 构建返回结果
    matches = []
    for match in top_matches:
        asset = match["asset"]
        score = match["score_details"]

        # 获取资产质量信息
        quality_info = await _get_asset_quality_info(db, str(asset.id))

        matches.append({
            "asset_id": str(asset.id),
            "asset_name": asset.name,
            "category": asset.category,
            "classification_level": asset.classification_level,
            "description": asset.description,
            "record_count": asset.record_count,
            "storage_format": asset.storage_format,
            "quality_score": quality_info.get("overall_score", 0),
            "match_score": round(score["total_score"], 4),
            "confidence": _get_confidence_level(score["total_score"]),
            "score_breakdown": score["breakdown"],
            "matching_reasons": score["reasons"],
        })

    logger.info(f"Found {len(matches)} matching assets for demand {demand_id}")
    return {
        "demand_id": demand_id,
        "strategy": strategy.value,
        "total_candidates": len(candidates),
        "matched_count": len(matches),
        "matches": matches,
        "searched_at": datetime.now(timezone.utc).isoformat(),
    }


async def _calculate_match_score(
    db: AsyncSession,
    asset: DataAsset,
    demand_features: Dict[str, Any],
    conditions: List[Dict[str, Any]],
    strategy: MatchingStrategy,
) -> Dict[str, Any]:
    """计算匹配分数"""
    breakdown = {}
    reasons = []

    # 1. 类别匹配 (25%)
    category_score = 0.0
    if demand_features.get("data_category"):
        if asset.category == demand_features["data_category"]:
            category_score = 1.0
            reasons.append(f"类别完全匹配: {asset.category}")
        elif _is_related_category(asset.category, demand_features["data_category"]):
            category_score = 0.6
            reasons.append(f"类别相关: {asset.category} <-> {demand_features['data_category']}")
    else:
        category_score = 0.5  # 无类别要求时给基础分
    breakdown["category_match"] = round(category_score, 4)

    # 2. 关键词匹配 (20%)
    keyword_score = 0.0
    demand_keywords = set(
        demand_features.get("title_keywords", []) +
        demand_features.get("description_keywords", [])
    )
    if demand_keywords:
        asset_text = f"{asset.name} {asset.description or ''}".lower()
        matched_keywords = [kw for kw in demand_keywords if kw in asset_text]
        if matched_keywords:
            keyword_score = min(1.0, len(matched_keywords) / max(len(demand_keywords), 1))
            reasons.append(f"关键词匹配: {', '.join(matched_keywords[:3])}")
    else:
        keyword_score = 0.5
    breakdown["keyword_match"] = round(keyword_score, 4)

    # 3. 质量得分 (15%)
    quality_info = await _get_asset_quality_info(db, str(asset.id))
    quality_score = quality_info.get("overall_score", 0.5)
    breakdown["quality_score"] = round(quality_score, 4)
    if quality_score >= 0.9:
        reasons.append(f"高质量数据: {quality_score:.0%}")

    # 4. 新鲜度 (10%)
    freshness_score = _calculate_freshness_score(asset)
    breakdown["freshness_score"] = round(freshness_score, 4)
    if freshness_score >= 0.8:
        reasons.append("数据新鲜度高")

    # 5. 安全等级匹配 (10%)
    security_score = 0.0
    required_level = demand_features.get("security_level", 4)
    if asset.classification_level:
        if asset.classification_level <= required_level:
            security_score = 1.0
        elif asset.classification_level == required_level + 1:
            security_score = 0.5
        else:
            security_score = 0.0
    else:
        security_score = 0.5
    breakdown["security_level_match"] = round(security_score, 4)

    # 6. 提供方可靠性 (10%)
    reliability_score = await _calculate_provider_reliability(db, str(asset.organization_id))
    breakdown["provider_reliability"] = round(reliability_score, 4)
    if reliability_score >= 0.9:
        reasons.append("提供方信誉良好")

    # 7. 价格竞争力 (10%)
    price_score = 0.7  # 默认中等价格竞争力
    breakdown["price_competitiveness"] = round(price_score, 4)

    # 计算总分
    total_score = (
        breakdown["category_match"] * MATCHING_WEIGHTS["category_match"] +
        breakdown["keyword_match"] * MATCHING_WEIGHTS["keyword_match"] +
        breakdown["quality_score"] * MATCHING_WEIGHTS["quality_score"] +
        breakdown["freshness_score"] * MATCHING_WEIGHTS["freshness_score"] +
        breakdown["security_level_match"] * MATCHING_WEIGHTS["security_level_match"] +
        breakdown["provider_reliability"] * MATCHING_WEIGHTS["provider_reliability"] +
        breakdown["price_competitiveness"] * MATCHING_WEIGHTS["price_competitiveness"]
    )

    return {
        "total_score": total_score,
        "breakdown": breakdown,
        "reasons": reasons,
    }


def _is_related_category(category1: str, category2: str) -> bool:
    """判断两个类别是否相关"""
    related_groups = [
        {"发电", "风电", "光伏", "火电", "水电"},
        {"用电", "负荷", "需求侧"},
        {"调度", "电网", "输电", "配电"},
        {"市场", "交易", "价格"},
        {"设备状态", "风机", "逆变器", "变压器"},
    ]

    for group in related_groups:
        if category1 in group and category2 in group:
            return True
    return False


def _calculate_freshness_score(asset: DataAsset) -> float:
    """计算数据新鲜度分数"""
    if not asset.updated_at:
        return 0.3

    now = datetime.now(timezone.utc)
    updated_at = asset.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    hours_since_update = (now - updated_at).total_seconds() / 3600

    if hours_since_update < 1:
        return 1.0
    elif hours_since_update < 6:
        return 0.9
    elif hours_since_update < 24:
        return 0.8
    elif hours_since_update < 72:
        return 0.6
    elif hours_since_update < 168:
        return 0.4
    else:
        return 0.2


async def _calculate_provider_reliability(db: AsyncSession, org_id: str) -> float:
    """计算提供方可靠性"""
    # 查询该组织的数据资产数量
    asset_count_result = await db.execute(
        select(func.count(DataAsset.id)).where(
            and_(
                DataAsset.organization_id == uuid.UUID(org_id),
                DataAsset.status == "published",
            )
        )
    )
    asset_count = asset_count_result.scalar() or 0

    # 查询该组织的合约完成情况
    contract_count_result = await db.execute(
        select(func.count(Contract.id)).where(
            and_(
                Contract.party_a_org_id == uuid.UUID(org_id),
                Contract.status == "completed",
            )
        )
    )
    completed_contracts = contract_count_result.scalar() or 0

    # 计算可靠性分数
    if asset_count == 0:
        return 0.5

    # 基于资产数量和合约完成情况
    asset_factor = min(1.0, asset_count / 10)  # 10个资产以上满分
    contract_factor = min(1.0, completed_contracts / 5)  # 5个合约以上满分

    reliability = (asset_factor * 0.6 + contract_factor * 0.4)
    return min(1.0, max(0.0, reliability))


async def _get_asset_quality_info(db: AsyncSession, asset_id: str) -> Dict[str, Any]:
    """获取资产质量信息"""
    from app.models.compliance import DataQualityReport

    result = await db.execute(
        select(DataQualityReport)
        .where(DataQualityReport.asset_id == uuid.UUID(asset_id))
        .order_by(DataQualityReport.generated_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()

    if report:
        return {
            "overall_score": float(report.overall_score or 0),
            "completeness": float(report.completeness or 0),
            "accuracy": float(report.accuracy or 0),
            "timeliness_ms": report.timeliness_ms,
            "consistency": float(report.consistency or 0),
        }
    return {"overall_score": 0.5}


def _get_confidence_level(score: float) -> str:
    """获取置信度级别"""
    if score >= 0.8:
        return MatchConfidence.HIGH.value
    elif score >= 0.6:
        return MatchConfidence.MEDIUM.value
    elif score >= 0.4:
        return MatchConfidence.LOW.value
    else:
        return MatchConfidence.VERY_LOW.value


# ==================== 撮合流程 ====================

async def initiate_matching(
    db: AsyncSession,
    demand_id: str,
    user_id: str,
    matching_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    发起撮合

    步骤：
    1. 验证需求状态
    2. 执行智能匹配
    3. 生成匹配报告
    4. 通知相关方

    Args:
        db: 数据库会话
        demand_id: 需求ID
        user_id: 发起用户ID
        matching_config: 匹配配置

    Returns:
        撮合结果
    """
    # 获取需求
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError(f"需求未找到: {demand_id}")

    if demand.status not in [DemandStatus.PUBLISHED.value, DemandStatus.DRAFT.value]:
        raise MatchingError(f"需求状态不允许撮合: {demand.status}")

    # 更新需求状态
    demand.status = DemandStatus.MATCHING.value
    await db.commit()

    # 执行匹配
    strategy = MatchingStrategy(matching_config.get("strategy", "hybrid")) if matching_config else MatchingStrategy.HYBRID
    top_k = matching_config.get("top_k", 10) if matching_config else 10

    matching_result = await find_matching_assets(
        db, demand_id, strategy, top_k
    )

    # 生成匹配ID
    matching_id = str(uuid.uuid4())

    # 更新需求状态为已匹配
    if matching_result["matched_count"] > 0:
        demand.status = DemandStatus.MATCHED.value
    else:
        demand.status = DemandStatus.PUBLISHED.value

    await db.commit()

    logger.info(f"Matching initiated: {matching_id}, demand={demand_id}, matches={matching_result['matched_count']}")
    return {
        "matching_id": matching_id,
        "demand_id": demand_id,
        "status": "completed",
        "matching_result": matching_result,
        "initiated_by": user_id,
        "initiated_at": datetime.now(timezone.utc).isoformat(),
    }


async def express_interest(
    db: AsyncSession,
    demand_id: str,
    asset_id: str,
    user_id: str,
    proposal: Optional[str] = None,
) -> Dict[str, Any]:
    """
    意向确认

    数据提供方对需求表达合作意向

    Args:
        db: 数据库会话
        demand_id: 需求ID
        asset_id: 数据资产ID
        user_id: 用户ID
        proposal: 合作提案

    Returns:
        意向记录
    """
    # 验证需求和资产
    demand_result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = demand_result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError(f"需求未找到: {demand_id}")

    asset_result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError(f"数据资产未找到: {asset_id}")

    # 检查是否已有意向
    existing = await db.execute(
        select(DemandClaim).where(
            and_(
                DemandClaim.demand_id == uuid.UUID(demand_id),
                DemandClaim.claimer_id == uuid.UUID(user_id),
                DemandClaim.status.in_(["pending", "approved"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise MatchingError("已存在对此需求的意向申请")

    # 创建意向记录
    claim = DemandClaim(
        demand_id=uuid.UUID(demand_id),
        claimer_id=uuid.UUID(user_id),
        claimer_org_id=asset.organization_id,
        proposal=proposal or f"提供数据资产: {asset.name}",
        status="pending",
    )
    db.add(claim)

    # 更新需求状态
    demand.status = DemandStatus.NEGOTIATING.value

    await db.commit()
    await db.refresh(claim)

    logger.info(f"Interest expressed: demand={demand_id}, asset={asset_id}, user={user_id}")
    return {
        "claim_id": str(claim.id),
        "demand_id": demand_id,
        "asset_id": asset_id,
        "user_id": user_id,
        "status": "pending",
        "expressed_at": datetime.now(timezone.utc).isoformat(),
    }


async def confirm_matching(
    db: AsyncSession,
    demand_id: str,
    claim_id: str,
    reviewer_id: str,
    confirmed: bool,
    feedback: str = "",
) -> Dict[str, Any]:
    """
    确认匹配

    需求方确认匹配结果

    Args:
        db: 数据库会话
        demand_id: 需求ID
        claim_id: 意向ID
        reviewer_id: 审核者ID
        confirmed: 是否确认
        feedback: 反馈信息

    Returns:
        确认结果
    """
    # 获取意向记录
    result = await db.execute(
        select(DemandClaim).where(DemandClaim.id == uuid.UUID(claim_id))
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise DataNotFoundError(f"意向记录未找到: {claim_id}")

    # 更新意向状态
    claim.status = "approved" if confirmed else "rejected"
    claim.reviewed_by = uuid.UUID(reviewer_id)
    claim.reviewed_at = datetime.now(timezone.utc)

    # 更新需求状态
    demand_result = await db.execute(
        select(Demand).where(Demand.id == claim.demand_id)
    )
    demand = demand_result.scalar_one_or_none()

    if demand:
        if confirmed:
            demand.status = DemandStatus.CONTRACTING.value
            demand.claimed_by_org = claim.claimer_org_id
            demand.claimed_by_user = claim.claimer_id
            demand.claimed_at = datetime.now(timezone.utc)
        else:
            demand.status = DemandStatus.PUBLISHED.value

    await db.commit()

    logger.info(f"Matching confirmed: claim={claim_id}, confirmed={confirmed}")
    return {
        "claim_id": claim_id,
        "demand_id": str(claim.demand_id),
        "confirmed": confirmed,
        "reviewer_id": reviewer_id,
        "feedback": feedback,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }


async def create_contract_from_matching(
    db: AsyncSession,
    demand_id: str,
    claim_id: str,
    user_id: str,
    contract_terms: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    从匹配创建合约

    Args:
        db: 数据库会话
        demand_id: 需求ID
        claim_id: 意向ID
        user_id: 用户ID
        contract_terms: 合约条款

    Returns:
        合约信息
    """
    # 获取需求和意向
    demand_result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = demand_result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError(f"需求未找到: {demand_id}")

    claim_result = await db.execute(
        select(DemandClaim).where(DemandClaim.id == uuid.UUID(claim_id))
    )
    claim = claim_result.scalar_one_or_none()
    if not claim:
        raise DataNotFoundError(f"意向记录未找到: {claim_id}")

    if claim.status != "approved":
        raise MatchingError("意向未确认，无法创建合约")

    # 生成合约编号
    import secrets
    import string
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = "".join(secrets.choice(string.digits) for _ in range(4))
    contract_no = f"CTR-{ts}-{rand}"

    # 创建合约
    contract = Contract(
        contract_no=contract_no,
        title=f"数据共享协议 - {demand.title}",
        contract_type="data_sharing",
        party_a_org_id=demand.organization_id,
        party_a_user_id=demand.publisher_id,
        party_b_org_id=claim.claimer_org_id,
        party_b_user_id=claim.claimer_id,
        related_product_id=None,
        content=f"基于需求 {demand.title} 创建的数据共享协议",
        terms=contract_terms or {
            "demand_id": demand_id,
            "claim_id": claim_id,
            "data_scope": demand.description,
            "usage_purpose": "数据分析",
        },
        pricing={},
        status="draft",
        created_by=uuid.UUID(user_id),
    )
    db.add(contract)

    # 更新需求状态
    demand.status = DemandStatus.FULFILLED.value

    await db.commit()
    await db.refresh(contract)

    logger.info(f"Contract created from matching: {contract_no}")
    return {
        "contract_id": str(contract.id),
        "contract_no": contract_no,
        "demand_id": demand_id,
        "claim_id": claim_id,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== 效果评估 ====================

async def evaluate_matching_effectiveness(
    db: AsyncSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    评估匹配效果

    评估指标：
    - 匹配成功率
    - 平均匹配时间
    - 用户满意度
    - 合约转化率

    Args:
        db: 数据库会话
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        效果评估报告
    """
    # 构建日期过滤
    date_filter = []
    if start_date:
        date_filter.append(Demand.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        date_filter.append(Demand.created_at <= datetime.fromisoformat(end_date))

    # 查询需求统计
    demand_query = select(
        func.count(Demand.id).label("total_demands"),
        func.count(Demand.id).filter(Demand.status == DemandStatus.FULFILLED.value).label("fulfilled_demands"),
        func.count(Demand.id).filter(Demand.status == DemandStatus.MATCHED.value).label("matched_demands"),
    )
    if date_filter:
        demand_query = demand_query.where(and_(*date_filter))

    demand_result = await db.execute(demand_query)
    demand_stats = demand_result.one_or_none()

    total_demands = demand_stats.total_demands if demand_stats else 0
    fulfilled_demands = demand_stats.fulfilled_demands if demand_stats else 0
    matched_demands = demand_stats.matched_demands if demand_stats else 0

    # 计算匹配成功率
    match_success_rate = matched_demands / total_demands if total_demands > 0 else 0
    fulfillment_rate = fulfilled_demands / total_demands if total_demands > 0 else 0

    # 查询意向统计
    claim_query = select(
        func.count(DemandClaim.id).label("total_claims"),
        func.count(DemandClaim.id).filter(DemandClaim.status == "approved").label("approved_claims"),
    )
    if date_filter:
        claim_query = claim_query.where(
            DemandClaim.created_at >= datetime.fromisoformat(start_date) if start_date else True,
            DemandClaim.created_at <= datetime.fromisoformat(end_date) if end_date else True,
        )

    claim_result = await db.execute(claim_query)
    claim_stats = claim_result.one_or_none()

    total_claims = claim_stats.total_claims if claim_stats else 0
    approved_claims = claim_stats.approved_claims if claim_stats else 0

    # 计算合约转化率
    contract_conversion_rate = approved_claims / total_claims if total_claims > 0 else 0

    # 查询平均匹配时间（从需求发布到匹配完成）
    # 这里简化处理，实际需要更复杂的查询
    avg_matching_hours = 24.0  # 模拟值

    # 用户满意度（基于反馈）
    satisfaction_score = 4.2  # 模拟值（5分制）

    return {
        "evaluation_period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "demand_statistics": {
            "total_demands": total_demands,
            "fulfilled_demands": fulfilled_demands,
            "matched_demands": matched_demands,
            "match_success_rate": round(match_success_rate, 4),
            "fulfillment_rate": round(fulfillment_rate, 4),
        },
        "claim_statistics": {
            "total_claims": total_claims,
            "approved_claims": approved_claims,
            "contract_conversion_rate": round(contract_conversion_rate, 4),
        },
        "performance_metrics": {
            "avg_matching_hours": avg_matching_hours,
            "satisfaction_score": satisfaction_score,
            "recommendation_accuracy": 0.75,  # 模拟值
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_matching_recommendations(
    db: AsyncSession,
    user_id: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    获取个性化推荐

    基于用户历史行为和偏好生成推荐

    Args:
        db: 数据库会话
        user_id: 用户ID
        limit: 推荐数量

    Returns:
        推荐结果
    """
    # 查询用户历史访问记录
    history_result = await db.execute(
        select(AccessLog)
        .where(AccessLog.user_id == uuid.UUID(user_id))
        .order_by(AccessLog.created_at.desc())
        .limit(50)
    )
    history = history_result.scalars().all()

    # 分析用户偏好
    category_counts = defaultdict(int)
    for log in history:
        # 获取资产类别
        asset_result = await db.execute(
            select(DataAsset.category).where(DataAsset.id == log.asset_id)
        )
        category = asset_result.scalar_one_or_none()
        if category:
            category_counts[category] += 1

    # 获取推荐类别
    preferred_categories = sorted(
        category_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]
    preferred_category_names = [cat for cat, _ in preferred_categories]

    # 查询推荐资产
    if preferred_category_names:
        query = select(DataAsset).where(
            and_(
                DataAsset.status == "published",
                DataAsset.category.in_(preferred_category_names),
            )
        ).limit(limit)
    else:
        # 无历史记录时推荐热门资产
        query = select(DataAsset).where(
            DataAsset.status == "published"
        ).order_by(DataAsset.created_at.desc()).limit(limit)

    result = await db.execute(query)
    recommended_assets = result.scalars().all()

    recommendations = []
    for asset in recommended_assets:
        quality_info = await _get_asset_quality_info(db, str(asset.id))
        recommendations.append({
            "asset_id": str(asset.id),
            "asset_name": asset.name,
            "category": asset.category,
            "classification_level": asset.classification_level,
            "quality_score": quality_info.get("overall_score", 0),
            "recommendation_reason": f"基于您对{asset.category}类数据的兴趣",
        })

    return {
        "user_id": user_id,
        "preferred_categories": preferred_category_names,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== 辅助函数 ====================

async def search_demands(
    db: AsyncSession,
    keyword: str = "",
    demand_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    搜索需求

    Args:
        db: 数据库会话
        keyword: 搜索关键词
        demand_type: 需求类型
        status: 需求状态
        page: 页码
        page_size: 每页大小

    Returns:
        搜索结果
    """
    query = select(Demand)

    if keyword:
        search_term = f"%{keyword}%"
        query = query.where(
            or_(
                Demand.title.ilike(search_term),
                Demand.description.ilike(search_term),
            )
        )

    if demand_type:
        query = query.where(Demand.demand_type == demand_type)

    if status:
        query = query.where(Demand.status == status)

    query = query.order_by(Demand.created_at.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    demands = result.scalars().all()

    # 获取总数
    count_query = select(func.count(Demand.id))
    if keyword:
        count_query = count_query.where(
            or_(
                Demand.title.ilike(f"%{keyword}%"),
                Demand.description.ilike(f"%{keyword}%"),
            )
        )
    if demand_type:
        count_query = count_query.where(Demand.demand_type == demand_type)
    if status:
        count_query = count_query.where(Demand.status == status)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(d.id),
                "demand_type": d.demand_type,
                "title": d.title,
                "description": d.description,
                "status": d.status,
                "organization_id": str(d.organization_id),
                "created_at": d.created_at.isoformat(),
            }
            for d in demands
        ],
    }
