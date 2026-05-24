"""
需求管理服务
需求发布/认领/审核管理
"""
import uuid
import logging
from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demand import Demand, DemandClaim
from app.models.user import Organization
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError

logger = logging.getLogger(__name__)


# ==================== 需求管理 ====================

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
    security_risk_assessment: Optional[dict] = None,
) -> dict:
    """创建需求"""
    demand = Demand(
        demand_type=demand_type,
        title=title,
        description=description,
        technical_requirements=technical_requirements or {},
        budget_range=budget_range,
        deadline=date.fromisoformat(deadline) if deadline else None,
        organization_id=uuid.UUID(organization_id),
        publisher_id=uuid.UUID(publisher_id),
        security_risk_assessment=security_risk_assessment or {},
        status="pending",
    )
    db.add(demand)
    await db.commit()
    await db.refresh(demand)

    logger.info(f"Demand created: {title} ({demand_type})")
    return _demand_to_dict(demand)


async def update_demand(db: AsyncSession, demand_id: str, **kwargs) -> dict:
    """更新需求"""
    result = await db.execute(select(Demand).where(Demand.id == uuid.UUID(demand_id)))
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if demand.status not in ("pending",):
        raise DataValidationError("只有待发布状态的需求可以修改")

    allowed_fields = [
        "demand_type", "title", "description", "technical_requirements",
        "budget_range", "security_risk_assessment",
    ]
    for field in allowed_fields:
        if field in kwargs and kwargs[field] is not None:
            setattr(demand, field, kwargs[field])
    if "deadline" in kwargs and kwargs["deadline"]:
        demand.deadline = date.fromisoformat(kwargs["deadline"])

    await db.commit()
    await db.refresh(demand)
    logger.info(f"Demand updated: {demand_id}")
    return _demand_to_dict(demand)


async def publish_demand(db: AsyncSession, demand_id: str, publisher_id: str) -> dict:
    """发布需求"""
    result = await db.execute(select(Demand).where(Demand.id == uuid.UUID(demand_id)))
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if demand.publisher_id != uuid.UUID(publisher_id):
        raise DataValidationError("只有发布者本人可以发布需求")
    if demand.status != "pending":
        raise DataValidationError(f"需求状态不可发布: {demand.status}")

    demand.status = "published"
    demand.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(demand)
    logger.info(f"Demand published: {demand_id}")
    return _demand_to_dict(demand)


async def close_demand(db: AsyncSession, demand_id: str, user_id: str) -> dict:
    """关闭需求"""
    result = await db.execute(select(Demand).where(Demand.id == uuid.UUID(demand_id)))
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if demand.status not in ("published", "claimed"):
        raise DataValidationError(f"需求状态不可关闭: {demand.status}")

    demand.status = "closed"
    demand.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(demand)
    logger.info(f"Demand closed: {demand_id}")
    return _demand_to_dict(demand)


async def get_demand(db: AsyncSession, demand_id: str) -> dict:
    """获取需求详情"""
    result = await db.execute(select(Demand).where(Demand.id == uuid.UUID(demand_id)))
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")

    # 加载认领记录
    claims_result = await db.execute(
        select(DemandClaim).where(DemandClaim.demand_id == demand.id)
    )
    claims = claims_result.scalars().all()

    demand_dict = _demand_to_dict(demand)
    demand_dict["claims"] = [_claim_to_dict(c) for c in claims]
    return demand_dict


async def list_demands(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    demand_type: Optional[str] = None,
    organization_id: Optional[str] = None,
    publisher_id: Optional[str] = None,
    keyword: Optional[str] = None,
) -> PaginatedResponse:
    """列出需求"""
    query = select(Demand)
    if status:
        query = query.where(Demand.status == status)
    if demand_type:
        query = query.where(Demand.demand_type == demand_type)
    if organization_id:
        query = query.where(Demand.organization_id == uuid.UUID(organization_id))
    if publisher_id:
        query = query.where(Demand.publisher_id == uuid.UUID(publisher_id))
    if keyword:
        query = query.where(Demand.title.ilike(f"%{keyword}%"))
    query = query.order_by(Demand.created_at.desc())

    from app.schemas.demand import DemandResponse
    result = await paginate_query(db, query, params, DemandResponse)
    return result


async def delete_demand(db: AsyncSession, demand_id: str) -> bool:
    """删除需求（软删除）"""
    result = await db.execute(select(Demand).where(Demand.id == uuid.UUID(demand_id)))
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if demand.status not in ("pending",):
        raise DataValidationError("只有待发布状态的需求可以删除")

    demand.status = "deleted"
    await db.commit()
    logger.info(f"Demand deleted: {demand_id}")
    return True


# ==================== 需求认领 ====================

async def create_claim(
    db: AsyncSession,
    demand_id: str,
    claimer_id: str,
    claimer_org_id: str,
    proposal: Optional[str] = None,
) -> dict:
    """创建需求认领"""
    result = await db.execute(select(Demand).where(Demand.id == uuid.UUID(demand_id)))
    demand = result.scalar_one_or_none()
    if not demand:
        raise DataNotFoundError("需求不存在")
    if demand.status != "published":
        raise DataValidationError("只能认领已发布的需求")
    if demand.organization_id == uuid.UUID(claimer_org_id):
        raise DataValidationError("不能认领自己组织的需求")

    # 检查重复认领
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
        raise DataAlreadyExistsError("已存在对此需求的认领申请")

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

    logger.info(f"Demand claim created: demand={demand_id}, claimer={claimer_id}")
    return _claim_to_dict(claim)


async def review_claim(
    db: AsyncSession,
    claim_id: str,
    reviewer_id: str,
    status: str,
) -> dict:
    """审核需求认领"""
    result = await db.execute(
        select(DemandClaim).where(DemandClaim.id == uuid.UUID(claim_id))
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise DataNotFoundError("认领申请不存在")
    if claim.status != "pending":
        raise DataValidationError(f"认领状态不为待审批: {claim.status}")

    claim.status = status
    claim.reviewed_by = uuid.UUID(reviewer_id)
    claim.reviewed_at = datetime.now(timezone.utc)

    # 如果审批通过，更新需求状态
    if status == "approved":
        demand_result = await db.execute(
            select(Demand).where(Demand.id == claim.demand_id)
        )
        demand = demand_result.scalar_one_or_none()
        if demand:
            demand.status = "claimed"
            demand.claimed_by_org = claim.claimer_org_id
            demand.claimed_by_user = claim.claimer_id
            demand.claimed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(claim)
    logger.info(f"Demand claim {claim_id} reviewed: {status}")
    return _claim_to_dict(claim)


async def list_claims(
    db: AsyncSession,
    params: PaginationParams,
    demand_id: Optional[str] = None,
    claimer_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """列出需求认领"""
    query = select(DemandClaim)
    if demand_id:
        query = query.where(DemandClaim.demand_id == uuid.UUID(demand_id))
    if claimer_id:
        query = query.where(DemandClaim.claimer_id == uuid.UUID(claimer_id))
    if status:
        query = query.where(DemandClaim.status == status)
    query = query.order_by(DemandClaim.created_at.desc())

    from app.schemas.demand import DemandClaimResponse
    result = await paginate_query(db, query, params, DemandClaimResponse)
    return result


# ==================== Helpers ====================

def _demand_to_dict(demand: Demand) -> dict:
    """需求转字典"""
    return {
        "id": str(demand.id),
        "demand_type": demand.demand_type,
        "title": demand.title,
        "description": demand.description,
        "technical_requirements": demand.technical_requirements or {},
        "budget_range": demand.budget_range,
        "deadline": demand.deadline.isoformat() if demand.deadline else None,
        "organization_id": str(demand.organization_id),
        "publisher_id": str(demand.publisher_id),
        "security_risk_assessment": demand.security_risk_assessment or {},
        "status": demand.status,
        "claimed_by_org": str(demand.claimed_by_org) if demand.claimed_by_org else None,
        "claimed_by_user": str(demand.claimed_by_user) if demand.claimed_by_user else None,
        "claimed_at": demand.claimed_at.isoformat() if demand.claimed_at else None,
        "published_at": demand.published_at.isoformat() if demand.published_at else None,
        "closed_at": demand.closed_at.isoformat() if demand.closed_at else None,
        "created_at": demand.created_at.isoformat(),
        "updated_at": demand.updated_at.isoformat(),
    }


def _claim_to_dict(claim: DemandClaim) -> dict:
    """认领转字典"""
    return {
        "id": str(claim.id),
        "demand_id": str(claim.demand_id),
        "claimer_id": str(claim.claimer_id),
        "claimer_org_id": str(claim.claimer_org_id),
        "proposal": claim.proposal,
        "status": claim.status,
        "reviewed_by": str(claim.reviewed_by) if claim.reviewed_by else None,
        "reviewed_at": claim.reviewed_at.isoformat() if claim.reviewed_at else None,
        "created_at": claim.created_at.isoformat(),
    }
