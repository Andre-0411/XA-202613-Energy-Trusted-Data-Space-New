"""
需求大厅服务
需求发布 / 安全风险评估 / 需求展示 / 认领承接 / 自动下架
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demand import Demand, DemandClaim
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    DataNotFoundError, DataValidationError, DataAlreadyExistsError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)

# 需求类型
VALID_DEMAND_TYPES = ("data_resource", "data_product", "compute_service")

# 需求状态
VALID_DEMAND_STATUSES = ("pending", "published", "claimed", "in_progress", "completed", "closed", "expired")

# 5类安全风险
RISK_CATEGORIES = (
    "data_security",       # 数据安全
    "privacy_compliance",  # 隐私合规
    "intellectual_property",  # 知识产权
    "commercial_secret",   # 商业秘密
    "regulatory_compliance",  # 监管合规
)


# ==================== 需求发布 ====================

async def create_demand(
    db: AsyncSession,
    demand_type: str,
    title: str,
    description: str,
    organization_id: str,
    publisher_id: str,
    technical_requirements: Optional[dict] = None,
    budget_range: Optional[str] = None,
    deadline: Optional[str] = None,
) -> dict:
    """发布需求"""
    if demand_type not in VALID_DEMAND_TYPES:
        raise DataValidationError(f"无效的需求类型: {demand_type}, 可选: {VALID_DEMAND_TYPES}")

    demand = Demand(
        demand_type=demand_type,
        title=title,
        description=description,
        technical_requirements=technical_requirements or {},
        budget_range=budget_range,
        deadline=datetime.fromisoformat(deadline).date() if deadline else None,
        organization_id=uuid.UUID(organization_id),
        publisher_id=uuid.UUID(publisher_id),
        status="published",
        published_at=datetime.now(timezone.utc),
    )
    db.add(demand)
    await db.commit()
    await db.refresh(demand)

    logger.info(f"Demand published: {title}, type={demand_type}, publisher={publisher_id}")
    return _demand_to_dict(demand)


async def update_demand(db: AsyncSession, demand_id: str, **kwargs) -> dict:
    """更新需求"""
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if demand.status not in ("pending", "published"):
        raise DataValidationError(f"需求状态不允许修改: {demand.status}")

    allowed = ["title", "description", "technical_requirements", "budget_range", "deadline"]
    for field in allowed:
        if field in kwargs and kwargs[field] is not None:
            if field == "deadline" and isinstance(kwargs[field], str):
                setattr(demand, field, datetime.fromisoformat(kwargs[field]).date())
            else:
                setattr(demand, field, kwargs[field])

    await db.commit()
    await db.refresh(demand)
    logger.info(f"Demand updated: {demand_id}")
    return _demand_to_dict(demand)


async def get_demand(db: AsyncSession, demand_id: str) -> dict:
    """获取需求详情"""
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    return _demand_to_dict(demand)


async def list_demands(
    db: AsyncSession,
    params: PaginationParams,
    demand_type: Optional[str] = None,
    status: Optional[str] = None,
    organization_id: Optional[str] = None,
    publisher_id: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by_popularity: bool = False,
) -> PaginatedResponse:
    """列出需求（支持分类筛选、热度排序）"""
    query = select(Demand)
    if demand_type:
        query = query.where(Demand.demand_type == demand_type)
    if status:
        query = query.where(Demand.status == status)
    else:
        # 默认只显示已发布的需求
        query = query.where(Demand.status.in_(["published", "claimed"]))
    if organization_id:
        query = query.where(Demand.organization_id == uuid.UUID(organization_id))
    if publisher_id:
        query = query.where(Demand.publisher_id == uuid.UUID(publisher_id))
    if keyword:
        query = query.where(
            Demand.title.ilike(f"%{keyword}%") | Demand.description.ilike(f"%{keyword}%")
        )

    if sort_by_popularity:
        # 热度排序：认领数量多的排前面（简化实现：按创建时间倒序）
        query = query.order_by(Demand.created_at.desc())
    else:
        query = query.order_by(Demand.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def close_demand(db: AsyncSession, demand_id: str, user_id: str) -> dict:
    """关闭需求"""
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if str(demand.publisher_id) != user_id:
        raise PermissionDeniedError("只有发布者可以关闭需求")
    if demand.status in ("closed", "expired", "completed"):
        raise DataValidationError(f"需求已终结: {demand.status}")

    demand.status = "closed"
    demand.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(demand)
    logger.info(f"Demand closed: {demand_id}")
    return _demand_to_dict(demand)


async def delete_demand(db: AsyncSession, demand_id: str, user_id: str) -> bool:
    """删除需求"""
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if str(demand.publisher_id) != user_id:
        raise PermissionDeniedError("只有发布者可以删除需求")
    if demand.status not in ("pending", "published", "closed"):
        raise DataValidationError(f"需求状态不允许删除: {demand.status}")

    await db.delete(demand)
    await db.commit()
    logger.info(f"Demand deleted: {demand_id}")
    return True


# ==================== 安全风险评估 ====================

async def assess_security_risk(
    db: AsyncSession,
    demand_id: str,
    assessment_data: Optional[dict] = None,
) -> dict:
    """5类安全风险评估"""
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")

    data = assessment_data or {}
    risk_results = []
    total_score = 0

    # 1. 数据安全风险
    ds_score = _assess_data_security(data.get("data_security", {}))
    risk_results.append({"category": "data_security", "category_cn": "数据安全", **ds_score})
    total_score += ds_score["score"]

    # 2. 隐私合规风险
    pc_score = _assess_privacy_compliance(data.get("privacy_compliance", {}))
    risk_results.append({"category": "privacy_compliance", "category_cn": "隐私合规", **pc_score})
    total_score += pc_score["score"]

    # 3. 知识产权风险
    ip_score = _assess_intellectual_property(data.get("intellectual_property", {}))
    risk_results.append({"category": "intellectual_property", "category_cn": "知识产权", **ip_score})
    total_score += ip_score["score"]

    # 4. 商业秘密风险
    cs_score = _assess_commercial_secret(data.get("commercial_secret", {}))
    risk_results.append({"category": "commercial_secret", "category_cn": "商业秘密", **cs_score})
    total_score += cs_score["score"]

    # 5. 监管合规风险
    rc_score = _assess_regulatory_compliance(data.get("regulatory_compliance", {}))
    risk_results.append({"category": "regulatory_compliance", "category_cn": "监管合规", **rc_score})
    total_score += rc_score["score"]

    avg_score = total_score / 5
    if avg_score >= 80:
        risk_level = "critical"
    elif avg_score >= 60:
        risk_level = "high"
    elif avg_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    assessment_result = {
        "demand_id": demand_id,
        "risk_level": risk_level,
        "total_score": total_score,
        "average_score": round(avg_score, 2),
        "risk_details": risk_results,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }

    # 保存评估结果到需求
    demand.security_risk_assessment = assessment_result
    await db.commit()

    logger.info(f"Security risk assessed for demand={demand_id}: level={risk_level}, score={avg_score}")
    return assessment_result


def _assess_data_security(data: dict) -> dict:
    """数据安全风险评估"""
    score = 0
    factors = []

    data_volume = data.get("data_volume", 0)
    if data_volume > 1000000:
        score += 30
        factors.append("数据量较大")
    elif data_volume > 100000:
        score += 15

    contains_sensitive = data.get("contains_sensitive", False)
    if contains_sensitive:
        score += 25
        factors.append("包含敏感数据")

    cross_border = data.get("cross_border", False)
    if cross_border:
        score += 20
        factors.append("涉及跨境传输")

    encryption = data.get("encryption_required", False)
    if not encryption:
        score += 10
        factors.append("未要求加密")

    return {"score": min(score, 100), "level": _score_to_level(score), "factors": factors}


def _assess_privacy_compliance(data: dict) -> dict:
    """隐私合规风险评估"""
    score = 0
    factors = []

    contains_pii = data.get("contains_pii", False)
    if contains_pii:
        score += 30
        factors.append("包含个人信息")

    consent_obtained = data.get("consent_obtained", True)
    if not consent_obtained:
        score += 25
        factors.append("未获得数据主体同意")

    purpose_limitation = data.get("purpose_specified", True)
    if not purpose_limitation:
        score += 15
        factors.append("未明确使用目的")

    return {"score": min(score, 100), "level": _score_to_level(score), "factors": factors}


def _assess_intellectual_property(data: dict) -> dict:
    """知识产权风险评估"""
    score = 0
    factors = []

    third_party_data = data.get("contains_third_party", False)
    if third_party_data:
        score += 25
        factors.append("包含第三方数据")

    license_clarity = data.get("license_clear", True)
    if not license_clarity:
        score += 20
        factors.append("授权许可不明确")

    derivative_use = data.get("derivative_use", False)
    if derivative_use:
        score += 15
        factors.append("涉及衍生使用")

    return {"score": min(score, 100), "level": _score_to_level(score), "factors": factors}


def _assess_commercial_secret(data: dict) -> dict:
    """商业秘密风险评估"""
    score = 0
    factors = []

    contains_trade_secret = data.get("contains_trade_secret", False)
    if contains_trade_secret:
        score += 35
        factors.append("包含商业秘密")

    competitor_access = data.get("competitor_accessible", False)
    if competitor_access:
        score += 20
        factors.append("竞争对手可访问")

    nda_required = data.get("nda_signed", True)
    if not nda_required:
        score += 15
        factors.append("未签署保密协议")

    return {"score": min(score, 100), "level": _score_to_level(score), "factors": factors}


def _assess_regulatory_compliance(data: dict) -> dict:
    """监管合规风险评估"""
    score = 0
    factors = []

    regulated_industry = data.get("regulated_industry", False)
    if regulated_industry:
        score += 25
        factors.append("受监管行业")

    data_localization = data.get("data_localization_required", False)
    if data_localization:
        score += 20
        factors.append("数据本地化要求")

    audit_trail = data.get("audit_trail_required", True)
    if not audit_trail:
        score += 15
        factors.append("缺少审计跟踪")

    return {"score": min(score, 100), "level": _score_to_level(score), "factors": factors}


def _score_to_level(score: int) -> str:
    """分数转风险等级"""
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "medium"
    return "low"


# ==================== 认领承接 ====================

async def claim_demand(
    db: AsyncSession,
    demand_id: str,
    claimer_id: str,
    claimer_org_id: str,
    proposal: Optional[str] = None,
) -> dict:
    """认领需求"""
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if demand.status != "published":
        raise DataValidationError(f"需求状态不允许认领: {demand.status}")
    if str(demand.organization_id) == claimer_org_id:
        raise DataValidationError("不能认领自己发布的需求")

    # 检查是否已认领
    existing = await db.execute(
        select(DemandClaim).where(
            and_(
                DemandClaim.demand_id == uuid.UUID(demand_id),
                DemandClaim.claimer_id == uuid.UUID(claimer_id),
                DemandClaim.status.in_(["pending", "approved"]),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("已认领过此需求")

    claim = DemandClaim(
        demand_id=uuid.UUID(demand_id),
        claimer_id=uuid.UUID(claimer_id),
        claimer_org_id=uuid.UUID(claimer_org_id),
        proposal=proposal,
        status="pending",
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)

    logger.info(f"Demand claimed: demand={demand_id}, claimer={claimer_id}")
    return _claim_to_dict(claim)


async def approve_claim(
    db: AsyncSession,
    claim_id: str,
    reviewer_id: str,
    approved: bool,
) -> dict:
    """审批认领"""
    result = await db.execute(
        select(DemandClaim).where(DemandClaim.id == uuid.UUID(claim_id))
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise DataNotFoundError("认领记录不存在")
    if claim.status != "pending":
        raise DataValidationError(f"认领状态不允许审批: {claim.status}")

    claim.reviewed_by = uuid.UUID(reviewer_id)
    claim.reviewed_at = datetime.now(timezone.utc)

    if approved:
        claim.status = "approved"
        # 更新需求状态
        demand_result = await db.execute(
            select(Demand).where(Demand.id == claim.demand_id)
        )
        demand = demand_result.scalar_one_or_none()
        if demand:
            demand.status = "claimed"
            demand.claimed_by_org = claim.claimer_org_id
            demand.claimed_by_user = claim.claimer_id
            demand.claimed_at = datetime.now(timezone.utc)
    else:
        claim.status = "rejected"

    await db.commit()
    await db.refresh(claim)
    logger.info(f"Claim {claim_id}: {'approved' if approved else 'rejected'} by {reviewer_id}")
    return _claim_to_dict(claim)


async def list_claims(
    db: AsyncSession,
    params: PaginationParams,
    demand_id: Optional[str] = None,
    claimer_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出认领记录"""
    query = select(DemandClaim)
    if demand_id:
        query = query.where(DemandClaim.demand_id == uuid.UUID(demand_id))
    if claimer_id:
        query = query.where(DemandClaim.claimer_id == uuid.UUID(claimer_id))
    if status:
        query = query.where(DemandClaim.status == status)
    query = query.order_by(DemandClaim.created_at.desc())

    result = await paginate_query(db, query, params)
    return result


async def complete_demand(db: AsyncSession, demand_id: str, user_id: str) -> dict:
    """完成需求"""
    result = await db.execute(
        select(Demand).where(Demand.id == uuid.UUID(demand_id))
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if str(demand.publisher_id) != user_id:
        raise PermissionDeniedError("只有发布者可以完成需求")
    if demand.status != "claimed":
        raise DataValidationError(f"需求状态不允许完成: {demand.status}")

    demand.status = "completed"
    demand.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(demand)
    logger.info(f"Demand completed: {demand_id}")
    return _demand_to_dict(demand)


# ==================== 自动下架 ====================

async def auto_expire_demands(db: AsyncSession, expire_days: int = 30) -> int:
    """自动下架：超时未承接的需求自动下架"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=expire_days)
    result = await db.execute(
        select(Demand).where(
            Demand.status == "published",
            Demand.published_at < cutoff,
        )
    )
    demands = list(result.scalars().all())
    count = 0
    for demand in demands:
        demand.status = "expired"
        demand.closed_at = datetime.now(timezone.utc)
        count += 1
    if count > 0:
        await db.commit()
        logger.info(f"Auto-expired {count} demands (published before {cutoff.isoformat()})")
    return count


async def get_demand_stats(db: AsyncSession) -> dict:
    """获取需求大厅统计"""
    total_result = await db.execute(
        select(Demand).where(Demand.status.in_(["published", "claimed"]))
    )
    active_demands = list(total_result.scalars().all())

    by_type = {}
    for d in active_demands:
        by_type[d.demand_type] = by_type.get(d.demand_type, 0) + 1

    by_status = {}
    for d in active_demands:
        by_status[d.status] = by_status.get(d.status, 0) + 1

    return {
        "total_active": len(active_demands),
        "by_type": by_type,
        "by_status": by_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== Helpers ====================

def _demand_to_dict(d: Demand) -> dict:
    """需求转字典"""
    return {
        "id": str(d.id),
        "demand_type": d.demand_type,
        "title": d.title,
        "description": d.description,
        "technical_requirements": d.technical_requirements or {},
        "budget_range": d.budget_range,
        "deadline": d.deadline.isoformat() if d.deadline else None,
        "organization_id": str(d.organization_id),
        "publisher_id": str(d.publisher_id),
        "security_risk_assessment": d.security_risk_assessment or {},
        "status": d.status,
        "claimed_by_org": str(d.claimed_by_org) if d.claimed_by_org else None,
        "claimed_by_user": str(d.claimed_by_user) if d.claimed_by_user else None,
        "claimed_at": d.claimed_at.isoformat() if d.claimed_at else None,
        "published_at": d.published_at.isoformat() if d.published_at else None,
        "closed_at": d.closed_at.isoformat() if d.closed_at else None,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


def _claim_to_dict(c: DemandClaim) -> dict:
    """认领转字典"""
    return {
        "id": str(c.id),
        "demand_id": str(c.demand_id),
        "claimer_id": str(c.claimer_id),
        "claimer_org_id": str(c.claimer_org_id),
        "proposal": c.proposal,
        "status": c.status,
        "reviewed_by": str(c.reviewed_by) if c.reviewed_by else None,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "created_at": c.created_at.isoformat(),
    }
