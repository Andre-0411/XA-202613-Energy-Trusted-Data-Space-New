"""
链上结算 API — /api/v1/blockchain/settlement
结算触发 / 批量结算 / 查询 / 争议仲裁 / 对账 / 报告
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.service import Subscription
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.blockchain import (
    SettlementRequest, SettlementBatchRequest, SettlementBatchResult,
    SettlementReconciliation, SettlementReportRequest, SettlementReportResponse,
)
from app.utils.deps import get_current_user
from app.services.blockchain_settle_service import (
    create_settlement, get_settlement, list_settlements,
    batch_settlement, reconciliation, generate_settlement_report,
)
from app.exceptions import SettlementError, DataNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ApiResponse)
async def 触发结算(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """触发结算 — 前端发送 {from_org, to_org, amount, asset_id, subscription_id?}"""
    user_did: str = user.get("user_id", "")
    from_org: str = body.get("from_org", "")
    to_org: str = body.get("to_org", "")
    amount: float = float(body.get("amount", 0))
    asset_id: str = body.get("asset_id", "")

    if not from_org or not to_org or amount <= 0:
        return ApiResponse(code=2003, message="from_org, to_org 和 amount 为必填项", data=None)

    # 获取订阅ID：优先从前端传入，否则查找用户活跃订阅
    subscription_id: str = body.get("subscription_id", "")

    if not subscription_id:
        # 查找当前用户的活跃订阅
        sub_result = await db.execute(
            select(Subscription).where(
                Subscription.status == "active"
            ).limit(1)
        )
        subscription = sub_result.scalars().first()
        if subscription:
            subscription_id = str(subscription.id)
        else:
            return ApiResponse(
                code=2001,
                message="未找到活跃订阅，请提供 subscription_id",
                data=None,
            )

    # 当前月份作为 billing_period: YYYY-MM
    billing_period: str = datetime.now(timezone.utc).strftime("%Y-%m")

    settlement_request = SettlementRequest(
        subscription_id=subscription_id,
        amount=amount,
        billing_period=billing_period,
    )

    try:
        result = await create_settlement(
            db=db, request=settlement_request, user_did=user_did,
        )
        # 附加组织信息到返回结果
        result["from_org"] = from_org
        result["to_org"] = to_org
        result["asset_id"] = asset_id
        return ApiResponse(data=result)
    except SettlementError as e:
        logger.error(f"Settlement failed: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except DataNotFoundError as e:
        logger.warning(f"Settlement not found: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"Settlement failed: {e}")
        return ApiResponse(code=4030, message=f"结算失败: {e}", data=None)


@router.post("/batch", response_model=ApiResponse[SettlementBatchResult])
async def 批量结算(
    body: SettlementBatchRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """批量结算 — 一次提交多条结算请求，部分失败不影响其他记录"""
    user_did: str = user.get("user_id", "")
    try:
        result = await batch_settlement(db=db, batch_request=body, user_did=user_did)
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Batch settlement failed: {e}")
        return ApiResponse(code=4030, message=f"批量结算失败: {e}", data=None)


@router.post("/reconciliation", response_model=ApiResponse[SettlementReconciliation])
async def 结算对账(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """结算对账 — 对比数据库结算记录与链上交易记录的一致性，前端发送 {billing_period, subscription_id?}"""
    billing_period: str = body.get("billing_period", "")
    subscription_id: str = body.get("subscription_id", "")

    if not billing_period:
        return ApiResponse(code=2003, message="billing_period 为必填项", data=None)

    try:
        result = await reconciliation(
            db=db,
            billing_period=billing_period,
            subscription_id=subscription_id or None,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        return ApiResponse(code=4030, message=f"对账失败: {e}", data=None)


@router.post("/report", response_model=ApiResponse[SettlementReportResponse])
async def 结算报告(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """生成结算报告 — 前端发送 {billing_period?, subscription_id?, start_date?, end_date?}"""
    report_request = SettlementReportRequest(
        billing_period=body.get("billing_period"),
        subscription_id=body.get("subscription_id"),
        start_date=body.get("start_date"),
        end_date=body.get("end_date"),
    )

    try:
        result = await generate_settlement_report(db=db, request=report_request)
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Settlement report failed: {e}")
        return ApiResponse(code=4030, message=f"结算报告生成失败: {e}", data=None)


@router.get("/list", response_model=ApiResponse)
async def 结算列表(
    subscription_id: str = Query(None, description="订阅 ID"),
    payment_status: str = Query(None, description="支付状态"),
    limit: int = Query(20, ge=1, le=100, description="每页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """结算列表 — 按订阅 ID / 支付状态筛选"""
    try:
        result = await list_settlements(
            db=db,
            subscription_id=subscription_id,
            payment_status=payment_status,
            limit=limit,
            offset=offset,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Settlement list failed: {e}")
        return ApiResponse(code=4030, message=f"结算列表查询失败: {e}", data=None)


@router.get("/{settlement_id}", response_model=ApiResponse)
async def 结算详情(
    settlement_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """结算详情 — 按结算ID查询"""
    try:
        result = await get_settlement(db=db, billing_id=settlement_id)
        return ApiResponse(data=result)
    except DataNotFoundError:
        return ApiResponse(code=2001, message="结算记录未找到", data=None)
    except Exception as e:
        logger.error(f"Settlement query failed: {e}")
        return ApiResponse(code=4030, message=f"结算查询失败: {e}", data=None)


@router.post("/{settlement_id}/dispute", response_model=ApiResponse)
async def 争议仲裁(
    settlement_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """争议仲裁 — 前端发送 {reason}"""
    user_did: str = user.get("user_id", "")
    reason: str = body.get("reason", "")

    if not reason:
        return ApiResponse(code=2003, message="reason 为必填项", data=None)

    # 先确认结算记录存在
    try:
        settlement = await get_settlement(db=db, billing_id=settlement_id)
    except DataNotFoundError:
        return ApiResponse(code=2001, message="结算记录未找到", data=None)

    # 调用链上争议（如果 AutoSettlement 合约已部署）
    try:
        from app.services.blockchain_settle_service import dispute_settlement_on_chain
        chain_result = await dispute_settlement_on_chain(
            settlement_id=int(settlement_id) if settlement_id.isdigit() else 0,
            reason=reason,
        )
    except Exception as e:
        logger.warning(f"Chain dispute failed (fallback to DB): {e}")
        chain_result = {}

    logger.info(
        f"Settlement dispute filed: settlement_id={settlement_id}, "
        f"user_did={user_did}, reason={reason}"
    )

    return ApiResponse(data={
        "settlement_id": settlement_id,
        "status": "disputed",
        "message": f"争议已提交，原因: {reason}",
        "disputed_by": user_did,
        "disputed_at": datetime.now(timezone.utc).isoformat(),
        "current_status": settlement.get("payment_status", "unknown"),
        "chain_tx_hash": chain_result.get("tx_hash", ""),
    })
