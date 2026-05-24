"""
合约管理服务
合约创建/签署/修订/查询
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract, ContractAmendment
from app.models.user import Organization
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)


def _generate_contract_no() -> str:
    """生成合约编号: CTR-{timestamp}-{random4}"""
    import secrets
    import string
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"CTR-{ts}-{rand}"


async def create_contract(
    db: AsyncSession,
    title: str,
    contract_type: str,
    party_a_org_id: str,
    party_a_user_id: str,
    party_b_org_id: str,
    content: str,
    created_by: str,
    party_b_user_id: Optional[str] = None,
    related_subscription_id: Optional[str] = None,
    related_product_id: Optional[str] = None,
    terms: Optional[dict] = None,
    pricing: Optional[dict] = None,
    effective_date: Optional[str] = None,
    expiration_date: Optional[str] = None,
) -> dict:
    """创建合约"""
    # 生成唯一合约编号
    contract_no = _generate_contract_no()
    existing = await db.execute(select(Contract).where(Contract.contract_no == contract_no))
    while existing.scalar_one_or_none():
        contract_no = _generate_contract_no()
        existing = await db.execute(select(Contract).where(Contract.contract_no == contract_no))

    contract = Contract(
        contract_no=contract_no,
        title=title,
        contract_type=contract_type,
        party_a_org_id=uuid.UUID(party_a_org_id),
        party_a_user_id=uuid.UUID(party_a_user_id),
        party_b_org_id=uuid.UUID(party_b_org_id),
        party_b_user_id=uuid.UUID(party_b_user_id) if party_b_user_id else None,
        related_subscription_id=uuid.UUID(related_subscription_id) if related_subscription_id else None,
        related_product_id=uuid.UUID(related_product_id) if related_product_id else None,
        content=content,
        terms=terms or {},
        pricing=pricing or {},
        effective_date=datetime.fromisoformat(effective_date) if effective_date else None,
        expiration_date=datetime.fromisoformat(expiration_date) if expiration_date else None,
        status="draft",
        created_by=uuid.UUID(created_by),
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    logger.info(f"Contract created: {contract_no}")
    return _contract_to_dict(contract)


async def update_contract(db: AsyncSession, contract_id: str, **kwargs) -> dict:
    """更新合约"""
    result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
    contract = result.scalar_one_or_none()
    if not contract:
        raise DataNotFoundError("合约不存在")
    if contract.status not in ("draft",):
        raise DataValidationError("只有草稿状态的合约可以修改")

    allowed = ["title", "content", "terms", "pricing", "status"]
    for field in allowed:
        if field in kwargs and kwargs[field] is not None:
            setattr(contract, field, kwargs[field])
    if "effective_date" in kwargs and kwargs["effective_date"]:
        contract.effective_date = datetime.fromisoformat(kwargs["effective_date"])
    if "expiration_date" in kwargs and kwargs["expiration_date"]:
        contract.expiration_date = datetime.fromisoformat(kwargs["expiration_date"])

    await db.commit()
    await db.refresh(contract)
    logger.info(f"Contract updated: {contract_id}")
    return _contract_to_dict(contract)


async def sign_contract(
    db: AsyncSession,
    contract_id: str,
    signer_id: str,
    blockchain_enabled: bool = False,
) -> dict:
    """签署合约"""
    result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
    contract = result.scalar_one_or_none()
    if not contract:
        raise DataNotFoundError("合约不存在")
    if contract.status not in ("draft", "pending_review"):
        raise DataValidationError(f"合约状态不可签署: {contract.status}")

    contract.status = "active"
    contract.effective_date = contract.effective_date or datetime.now(timezone.utc)

    # 使用 SM3 国密哈希生成区块链存证（符合国密标准）
    if blockchain_enabled:
        content_hash = gmssl_adapter.sm3_hash(contract.content)
        contract.blockchain_tx_hash = f"0x{content_hash[:64]}"
        contract.blockchain_contract_address = f"0x{content_hash[:40]}"

    await db.commit()
    await db.refresh(contract)
    logger.info(f"Contract signed: {contract_id}, blockchain={blockchain_enabled}")
    return _contract_to_dict(contract)


async def terminate_contract(db: AsyncSession, contract_id: str, user_id: str) -> dict:
    """终止合约"""
    result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
    contract = result.scalar_one_or_none()
    if not contract:
        raise DataNotFoundError("合约不存在")
    if contract.status != "active":
        raise DataValidationError("只有生效中的合约可以终止")

    contract.status = "terminated"
    await db.commit()
    await db.refresh(contract)
    logger.info(f"Contract terminated: {contract_id}")
    return _contract_to_dict(contract)


async def get_contract(db: AsyncSession, contract_id: str) -> dict:
    """获取合约详情"""
    result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
    contract = result.scalar_one_or_none()
    if not contract:
        raise DataNotFoundError("合约不存在")

    # 加载修订记录
    amendments_result = await db.execute(
        select(ContractAmendment).where(ContractAmendment.contract_id == contract.id)
    )
    amendments = amendments_result.scalars().all()

    contract_dict = _contract_to_dict(contract)
    contract_dict["amendments"] = [_amendment_to_dict(a) for a in amendments]
    return contract_dict


async def list_contracts(
    db: AsyncSession,
    params: PaginationParams,
    status: Optional[str] = None,
    contract_type: Optional[str] = None,
    party_a_org_id: Optional[str] = None,
    party_b_org_id: Optional[str] = None,
) -> PaginatedResponse:
    """列出合约"""
    query = select(Contract)
    if status:
        query = query.where(Contract.status == status)
    if contract_type:
        query = query.where(Contract.contract_type == contract_type)
    if party_a_org_id:
        query = query.where(Contract.party_a_org_id == uuid.UUID(party_a_org_id))
    if party_b_org_id:
        query = query.where(Contract.party_b_org_id == uuid.UUID(party_b_org_id))
    query = query.order_by(Contract.created_at.desc())

    from app.schemas.contract import ContractResponse
    result = await paginate_query(db, query, params, ContractResponse)
    return result


# ==================== 合约修订 ====================

async def create_amendment(
    db: AsyncSession,
    contract_id: str,
    reason: str,
    created_by: str,
    changes: Optional[dict] = None,
    new_terms: Optional[dict] = None,
) -> dict:
    """创建合约修订"""
    result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
    contract = result.scalar_one_or_none()
    if not contract:
        raise DataNotFoundError("合约不存在")

    # 获取修订序号
    count_result = await db.execute(
        select(func.count(ContractAmendment.id)).where(
            ContractAmendment.contract_id == uuid.UUID(contract_id)
        )
    )
    amendment_no = (count_result.scalar() or 0) + 1

    amendment = ContractAmendment(
        contract_id=uuid.UUID(contract_id),
        amendment_no=amendment_no,
        reason=reason,
        changes=changes or {},
        previous_terms=contract.terms.copy() if contract.terms else {},
        new_terms=new_terms or {},
        status="pending",
        created_by=uuid.UUID(created_by),
    )
    db.add(amendment)
    await db.commit()
    await db.refresh(amendment)

    logger.info(f"Contract amendment created: contract={contract_id}, no={amendment_no}")
    return _amendment_to_dict(amendment)


async def review_amendment(
    db: AsyncSession,
    amendment_id: str,
    reviewer_id: str,
    status: str,
) -> dict:
    """审核合约修订"""
    result = await db.execute(
        select(ContractAmendment).where(ContractAmendment.id == uuid.UUID(amendment_id))
    )
    amendment = result.scalar_one_or_none()
    if not amendment:
        raise DataNotFoundError("修订记录不存在")
    if amendment.status != "pending":
        raise DataValidationError(f"修订状态不为待审批: {amendment.status}")

    amendment.status = status
    amendment.approved_by = uuid.UUID(reviewer_id)
    amendment.approved_at = datetime.now(timezone.utc)

    # 如果审批通过，更新合约条款
    if status == "approved" and amendment.new_terms:
        contract_result = await db.execute(
            select(Contract).where(Contract.id == amendment.contract_id)
        )
        contract = contract_result.scalar_one_or_none()
        if contract:
            contract.terms = amendment.new_terms
            contract.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(amendment)
    logger.info(f"Contract amendment {amendment_id} reviewed: {status}")
    return _amendment_to_dict(amendment)


# ==================== Helpers ====================

def _contract_to_dict(contract: Contract) -> dict:
    """合约转字典"""
    return {
        "id": str(contract.id),
        "contract_no": contract.contract_no,
        "title": contract.title,
        "contract_type": contract.contract_type,
        "party_a_org_id": str(contract.party_a_org_id),
        "party_a_user_id": str(contract.party_a_user_id),
        "party_b_org_id": str(contract.party_b_org_id),
        "party_b_user_id": str(contract.party_b_user_id) if contract.party_b_user_id else None,
        "related_subscription_id": str(contract.related_subscription_id) if contract.related_subscription_id else None,
        "related_product_id": str(contract.related_product_id) if contract.related_product_id else None,
        "content": contract.content,
        "terms": contract.terms or {},
        "pricing": contract.pricing or {},
        "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
        "expiration_date": contract.expiration_date.isoformat() if contract.expiration_date else None,
        "blockchain_tx_hash": contract.blockchain_tx_hash,
        "blockchain_contract_address": contract.blockchain_contract_address,
        "status": contract.status,
        "created_by": str(contract.created_by),
        "created_at": contract.created_at.isoformat(),
        "updated_at": contract.updated_at.isoformat(),
    }


def _amendment_to_dict(a: ContractAmendment) -> dict:
    """修订转字典"""
    return {
        "id": str(a.id),
        "contract_id": str(a.contract_id),
        "amendment_no": a.amendment_no,
        "reason": a.reason,
        "changes": a.changes or {},
        "previous_terms": a.previous_terms or {},
        "new_terms": a.new_terms or {},
        "approved_by": str(a.approved_by) if a.approved_by else None,
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
        "status": a.status,
        "created_by": str(a.created_by),
        "created_at": a.created_at.isoformat(),
    }
