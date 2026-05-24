"""
计费服务
计费记录生成（按次/按时/按量） + 月度账单汇总 + 计费汇总统计 + Subscription关联
账单明细下载 + 账单生成 + 账单统计 + 月度账单自动生成定时任务
"""
import uuid
import csv
import json
import io
import base64
import logging
import asyncio
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import select, and_, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import ServiceCatalog, Subscription, BillingRecord
from app.models.user import User
from app.schemas.service import (
    ServiceResponse, SubscriptionResponse, BillingRecordResponse,
)
from app.schemas.ops import BillingSummaryResponse
from app.schemas.common import PaginatedResponse
from app.schemas.billing import (
    BillResponse,
    BillDetailResponse,
    BillGenerateResponse,
    BillStatisticsResponse,
    BillDownloadResponse,
)
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import (
    DataNotFoundError, BillingError, DataValidationError,
)

logger = logging.getLogger(__name__)

# 计费模式
PRICING_MODELS = {"fixed", "usage", "tiered"}

# 支付状态
PAYMENT_STATUSES = {"pending", "paid", "overdue"}

# ==================== 月度账单定时任务 ====================

# 定时任务句柄
_monthly_task_handle: Optional[asyncio.Task] = None


async def start_monthly_billing_scheduler():
    """
    启动月度账单自动生成定时任务

    每月 1 日 00:30 UTC 自动执行上月账单生成
    """
    global _monthly_task_handle

    async def _scheduler_loop():
        """定时任务循环"""
        logger.info("Monthly billing scheduler started")
        while True:
            try:
                now = datetime.now(timezone.utc)
                # 计算下个月 1 日 00:30 UTC
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=1,
                                           hour=0, minute=30, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=1,
                                           hour=0, minute=30, second=0, microsecond=0)

                wait_seconds = (next_run - now).total_seconds()
                if wait_seconds <= 0:
                    wait_seconds = 3600  # 安全兜底：至少等 1 小时

                logger.info(
                    f"Next monthly billing run at {next_run.isoformat()}, "
                    f"waiting {wait_seconds:.0f}s"
                )
                await asyncio.sleep(wait_seconds)

                # 生成上月账单
                last_month = (now.replace(day=1) - __import__("datetime").timedelta(days=1))
                billing_period = last_month.strftime("%Y-%m")

                logger.info(f"Auto-generating monthly bills for period {billing_period}")
                # 注意：此处没有 db session，需要通过 app.database 创建
                from app.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    try:
                        result = await generate_monthly_bill(
                            db=db, billing_period=billing_period
                        )
                        await db.commit()
                        logger.info(
                            f"Auto monthly bill generated: period={billing_period}, "
                            f"count={result.bills_generated}, total={result.total_amount}"
                        )
                    except Exception as e:
                        await db.rollback()
                        logger.error(f"Auto monthly bill generation failed: {e}")

            except asyncio.CancelledError:
                logger.info("Monthly billing scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Monthly billing scheduler error: {e}")
                await asyncio.sleep(3600)  # 出错后等 1 小时重试

    _monthly_task_handle = asyncio.create_task(_scheduler_loop())
    logger.info("Monthly billing scheduler task created")


async def stop_monthly_billing_scheduler():
    """停止月度账单定时任务"""
    global _monthly_task_handle
    if _monthly_task_handle and not _monthly_task_handle.done():
        _monthly_task_handle.cancel()
        try:
            await _monthly_task_handle
        except asyncio.CancelledError:
            pass
    _monthly_task_handle = None
    logger.info("Monthly billing scheduler stopped")


async def get_monthly_report(
    db: AsyncSession,
    period: str,
    organization_id: Optional[str] = None,
) -> dict:
    """
    获取月度账单报告（GET /api/v1/billing/monthly-report 端点）

    Args:
        db: 数据库会话
        period: 账期 YYYY-MM
        organization_id: 组织 ID

    Returns:
        月度报告数据
    """
    invoice_data = await get_monthly_invoice(db, period, organization_id)

    # 扩展报告信息
    report = {
        **invoice_data,
        "report_type": "monthly_billing",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "currency": "CNY",
    }

    # 获取账单统计
    stats = await get_billing_statistics(
        db=db,
        start_period=period,
        end_period=period,
        organization_id=organization_id,
    )
    report["statistics"] = {
        "total_bills": stats.total_bills,
        "paid_bills": stats.paid_bills,
        "unpaid_bills": stats.unpaid_bills,
        "by_service_type": stats.by_service_type,
    }

    return report


# ==================== 原有功能 ====================

async def generate_billing_record(
    db: AsyncSession,
    subscription_id: str,
    usage_quantity: float = 1.0,
    usage_detail: Optional[dict] = None,
) -> BillingRecordResponse:
    """
    生成计费记录

    Args:
        db: 数据库会话
        subscription_id: 订阅 ID
        usage_quantity: 使用量
        usage_detail: 使用详情

    Returns:
        计费记录
    """
    sub_result = await db.execute(
        select(Subscription).where(Subscription.id == uuid.UUID(subscription_id))
    )
    subscription = sub_result.scalar_one_or_none()
    if not subscription:
        raise DataNotFoundError(message=f"订阅不存在: {subscription_id}")

    svc_result = await db.execute(
        select(ServiceCatalog).where(ServiceCatalog.id == subscription.service_id)
    )
    service = svc_result.scalar_one_or_none()
    if not service:
        raise DataNotFoundError(message=f"服务不存在: {subscription.service_id}")

    amount = _calculate_amount(
        pricing_model=service.pricing_model,
        pricing_config=service.pricing_config,
        usage_quantity=usage_quantity,
    )

    billing_period = date.today().strftime("%Y-%m")

    record = BillingRecord(
        subscription_id=subscription.id,
        amount=amount,
        billing_period=billing_period,
        usage_detail=usage_detail or {
            "quantity": usage_quantity,
            "pricing_model": service.pricing_model,
            "service_name": service.name,
        },
        payment_status="pending",
    )
    db.add(record)

    subscription.quota_used = (subscription.quota_used or 0) + int(usage_quantity)

    await db.commit()
    await db.refresh(record)

    logger.info(
        f"计费记录生成: 订阅 {subscription_id}, 金额 {amount}, 模式 {service.pricing_model}"
    )
    return BillingRecordResponse.model_validate(record)


def _calculate_amount(
    pricing_model: str,
    pricing_config: dict,
    usage_quantity: float,
) -> float:
    """根据计费模式计算金额"""
    if pricing_model == "fixed":
        return float(pricing_config.get("unit_price", 0.0))
    elif pricing_model == "usage":
        unit_price = float(pricing_config.get("unit_price", 0.0))
        return round(usage_quantity * unit_price, 2)
    elif pricing_model == "tiered":
        tiers = pricing_config.get("tiers", [])
        amount = 0.0
        remaining = usage_quantity
        for tier in sorted(tiers, key=lambda t: t.get("limit", 0)):
            limit = float(tier.get("limit", 0))
            price = float(tier.get("price", 0.0))
            if remaining <= 0:
                break
            tier_quantity = min(remaining, limit)
            amount += tier_quantity * price
            remaining -= tier_quantity
        if remaining > 0 and tiers:
            highest_price = float(tiers[-1].get("price", 0.0))
            amount += remaining * highest_price
        return round(amount, 2)
    else:
        raise BillingError(message=f"不支持的计费模式: {pricing_model}")


async def get_monthly_invoice(
    db: AsyncSession,
    period: str,
    organization_id: Optional[str] = None,
) -> dict:
    """月度账单汇总"""
    try:
        datetime.strptime(period, "%Y-%m")
    except ValueError:
        raise DataValidationError(message=f"无效账期格式: {period}，应为 YYYY-MM")

    query = select(BillingRecord).where(BillingRecord.billing_period == period)

    if organization_id:
        sub_query = select(Subscription.id).where(
            Subscription.user_id.in_(
                select(User.id).where(
                    User.organization_id == uuid.UUID(organization_id)
                )
            )
        )
        query = query.where(BillingRecord.subscription_id.in_(sub_query))

    result = await db.execute(query)
    records = result.scalars().all()

    total_amount = sum(float(r.amount) for r in records)
    paid_amount = sum(float(r.amount) for r in records if r.payment_status == "paid")
    pending_amount = sum(float(r.amount) for r in records if r.payment_status == "pending")
    overdue_amount = sum(float(r.amount) for r in records if r.payment_status == "overdue")

    by_service: dict[str, float] = {}
    for record in records:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.id == record.subscription_id)
        )
        sub = sub_result.scalar_one_or_none()
        if sub:
            svc_result = await db.execute(
                select(ServiceCatalog).where(ServiceCatalog.id == sub.service_id)
            )
            svc = svc_result.scalar_one_or_none()
            service_name = svc.name if svc else "unknown"
        else:
            service_name = "unknown"
        if service_name not in by_service:
            by_service[service_name] = 0.0
        by_service[service_name] += float(record.amount)

    return {
        "period": period,
        "total_amount": round(total_amount, 2),
        "paid_amount": round(paid_amount, 2),
        "pending_amount": round(pending_amount, 2),
        "overdue_amount": round(overdue_amount, 2),
        "record_count": len(records),
        "breakdown_by_service": {k: round(v, 2) for k, v in by_service.items()},
    }


async def get_billing_records(
    db: AsyncSession,
    params: PaginationParams,
    subscription_id: Optional[str] = None,
    payment_status: Optional[str] = None,
    billing_period: Optional[str] = None,
) -> PaginatedResponse:
    """查询计费记录"""
    query = select(BillingRecord)
    if subscription_id:
        query = query.where(BillingRecord.subscription_id == uuid.UUID(subscription_id))
    if payment_status:
        query = query.where(BillingRecord.payment_status == payment_status)
    if billing_period:
        query = query.where(BillingRecord.billing_period == billing_period)
    result = await paginate_query(db, query, params, BillingRecordResponse)
    return result


async def get_billing_summary(
    db: AsyncSession,
    organization_id: Optional[str] = None,
) -> BillingSummaryResponse:
    """计费汇总统计"""
    query = select(BillingRecord)
    if organization_id:
        sub_query = select(Subscription.id).where(
            Subscription.user_id.in_(
                select(User.id).where(
                    User.organization_id == uuid.UUID(organization_id)
                )
            )
        )
        query = query.where(BillingRecord.subscription_id.in_(sub_query))

    result = await db.execute(query)
    records = result.scalars().all()

    total_revenue = sum(float(r.amount) for r in records)
    completed_payments = sum(float(r.amount) for r in records if r.payment_status == "paid")
    pending_payments = sum(float(r.amount) for r in records if r.payment_status == "pending")
    overdue_payments = sum(float(r.amount) for r in records if r.payment_status == "overdue")

    billing_by_service: dict[str, float] = {}
    billing_by_month: dict[str, float] = {}

    for record in records:
        month = record.billing_period
        billing_by_month[month] = billing_by_month.get(month, 0.0) + float(record.amount)

    for record in records:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.id == record.subscription_id)
        )
        sub = sub_result.scalar_one_or_none()
        if sub:
            svc_result = await db.execute(
                select(ServiceCatalog).where(ServiceCatalog.id == sub.service_id)
            )
            svc = svc_result.scalar_one_or_none()
            service_name = svc.name if svc else "unknown"
        else:
            service_name = "unknown"
        billing_by_service[service_name] = billing_by_service.get(service_name, 0.0) + float(record.amount)

    return BillingSummaryResponse(
        total_revenue=round(total_revenue, 2),
        pending_payments=round(pending_payments, 2),
        completed_payments=round(completed_payments, 2),
        overdue_payments=round(overdue_payments, 2),
        billing_by_service={k: round(v, 2) for k, v in billing_by_service.items()},
        billing_by_month={k: round(v, 2) for k, v in billing_by_month.items()},
    )


async def get_bills(
    db: AsyncSession,
    params: PaginationParams,
    billing_period: Optional[str] = None,
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
) -> PaginatedResponse:
    """获取账单列表"""
    query = select(BillingRecord)
    if billing_period:
        query = query.where(BillingRecord.billing_period == billing_period)
    if status:
        query = query.where(BillingRecord.payment_status == status)
    if organization_id:
        sub_query = select(Subscription.id).where(
            Subscription.user_id.in_(
                select(User.id).where(
                    User.organization_id == uuid.UUID(organization_id)
                )
            )
        )
        query = query.where(BillingRecord.subscription_id.in_(sub_query))
    query = query.order_by(BillingRecord.created_at.desc())
    result = await paginate_query(db, query, params, BillingRecordResponse)
    return result


async def download_bill_detail(
    db: AsyncSession,
    bill_id: str,
    fmt: str = "csv",
) -> BillDownloadResponse:
    """下载账单明细"""
    result = await db.execute(
        select(BillingRecord).where(BillingRecord.id == uuid.UUID(bill_id))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise DataNotFoundError(message=f"账单不存在: {bill_id}")

    service_name = "unknown"
    service_category = ""
    sub_result = await db.execute(
        select(Subscription).where(Subscription.id == record.subscription_id)
    )
    sub = sub_result.scalar_one_or_none()
    if sub:
        svc_result = await db.execute(
            select(ServiceCatalog).where(ServiceCatalog.id == sub.service_id)
        )
        svc = svc_result.scalar_one_or_none()
        if svc:
            service_name = svc.name
            service_category = svc.category

    bill_no = f"BILL-{record.billing_period}-{str(record.id)[:8].upper()}"

    detail_items = []
    usage_detail = record.usage_detail or {}
    detail_items.append({
        "bill_no": bill_no,
        "billing_period": record.billing_period,
        "service_name": service_name,
        "service_category": service_category,
        "usage_quantity": usage_detail.get("quantity", 0),
        "pricing_model": usage_detail.get("pricing_model", ""),
        "amount": float(record.amount),
        "payment_status": record.payment_status,
        "created_at": record.created_at.isoformat() if record.created_at else "",
    })

    if "items" in usage_detail and isinstance(usage_detail["items"], list):
        for item in usage_detail["items"]:
            detail_items.append({
                "bill_no": bill_no,
                "billing_period": record.billing_period,
                "service_name": item.get("service_name", service_name),
                "service_category": item.get("category", service_category),
                "usage_quantity": item.get("quantity", 0),
                "pricing_model": item.get("pricing_model", ""),
                "amount": float(item.get("amount", 0)),
                "payment_status": record.payment_status,
                "created_at": record.created_at.isoformat() if record.created_at else "",
            })

    if fmt == "json":
        content = json.dumps(detail_items, ensure_ascii=False, indent=2)
        filename = f"{bill_no}.json"
    else:
        output = io.StringIO()
        if detail_items:
            writer = csv.DictWriter(output, fieldnames=detail_items[0].keys())
            writer.writeheader()
            writer.writerows(detail_items)
        content = output.getvalue()
        filename = f"{bill_no}.csv"

    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    return BillDownloadResponse(
        bill_id=bill_id,
        bill_no=bill_no,
        format=fmt,
        filename=filename,
        content=encoded_content,
        item_count=len(detail_items),
    )


async def get_billing_statistics(
    db: AsyncSession,
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> BillStatisticsResponse:
    """账单统计"""
    query = select(BillingRecord)
    if start_period:
        query = query.where(BillingRecord.billing_period >= start_period)
    if end_period:
        query = query.where(BillingRecord.billing_period <= end_period)
    if organization_id:
        sub_query = select(Subscription.id).where(
            Subscription.user_id.in_(
                select(User.id).where(
                    User.organization_id == uuid.UUID(organization_id)
                )
            )
        )
        query = query.where(BillingRecord.subscription_id.in_(sub_query))

    result = await db.execute(query)
    records = result.scalars().all()

    total_revenue = sum(float(r.amount) for r in records)
    total_bills = len(records)
    paid_bills = sum(1 for r in records if r.payment_status == "paid")
    unpaid_bills = total_bills - paid_bills

    by_service_type: dict[str, dict] = {}
    by_period: dict[str, dict] = {}

    for record in records:
        service_name = "unknown"
        service_category = "other"
        sub_result = await db.execute(
            select(Subscription).where(Subscription.id == record.subscription_id)
        )
        sub = sub_result.scalar_one_or_none()
        if sub:
            svc_result = await db.execute(
                select(ServiceCatalog).where(ServiceCatalog.id == sub.service_id)
            )
            svc = svc_result.scalar_one_or_none()
            if svc:
                service_name = svc.name
                service_category = svc.category

        if service_category not in by_service_type:
            by_service_type[service_category] = {"total_amount": 0.0, "count": 0, "services": {}}
        by_service_type[service_category]["total_amount"] += float(record.amount)
        by_service_type[service_category]["count"] += 1
        svc_stats = by_service_type[service_category]["services"]
        svc_stats[service_name] = svc_stats.get(service_name, 0.0) + float(record.amount)

        period = record.billing_period
        if period not in by_period:
            by_period[period] = {"total_amount": 0.0, "count": 0, "paid_amount": 0.0, "pending_amount": 0.0}
        by_period[period]["total_amount"] += float(record.amount)
        by_period[period]["count"] += 1
        if record.payment_status == "paid":
            by_period[period]["paid_amount"] += float(record.amount)
        elif record.payment_status == "pending":
            by_period[period]["pending_amount"] += float(record.amount)

    for category_data in by_service_type.values():
        category_data["total_amount"] = round(category_data["total_amount"], 2)
        for svc_name in category_data["services"]:
            category_data["services"][svc_name] = round(category_data["services"][svc_name], 2)
    for period_data in by_period.values():
        period_data["total_amount"] = round(period_data["total_amount"], 2)
        period_data["paid_amount"] = round(period_data["paid_amount"], 2)
        period_data["pending_amount"] = round(period_data["pending_amount"], 2)

    return BillStatisticsResponse(
        total_revenue=round(total_revenue, 2),
        total_bills=total_bills,
        paid_bills=paid_bills,
        unpaid_bills=unpaid_bills,
        by_service_type=by_service_type,
        by_period=dict(sorted(by_period.items())),
        generated_at=datetime.now(timezone.utc),
    )


async def generate_monthly_bill(
    db: AsyncSession,
    billing_period: str,
    organization_id: Optional[str] = None,
) -> BillGenerateResponse:
    """生成月度账单"""
    try:
        datetime.strptime(billing_period, "%Y-%m")
    except ValueError:
        raise DataValidationError(
            message=f"无效账期格式: {billing_period}，应为 YYYY-MM"
        )

    query = select(BillingRecord).where(BillingRecord.billing_period == billing_period)
    if organization_id:
        sub_query = select(Subscription.id).where(
            Subscription.user_id.in_(
                select(User.id).where(
                    User.organization_id == uuid.UUID(organization_id)
                )
            )
        )
        query = query.where(BillingRecord.subscription_id.in_(sub_query))

    result = await db.execute(query)
    records = result.scalars().all()

    if not records:
        raise BillingError(
            message=f"账期 {billing_period} 无计费记录，无法生成账单"
        )

    total_amount = sum(float(r.amount) for r in records)
    bills_generated = len(records)

    updated_count = 0
    for record in records:
        if record.payment_status == "pending":
            record.payment_status = "issued"
            updated_count += 1

    await db.commit()

    logger.info(
        f"月度账单生成完成: period={billing_period}, "
        f"bills={bills_generated}, total={total_amount}"
    )

    return BillGenerateResponse(
        billing_period=billing_period,
        bills_generated=bills_generated,
        total_amount=round(total_amount, 2),
        generated_at=datetime.now(timezone.utc),
    )
