"""
计费规则上链服务

支持三种计费模式:
- 按次计费 (per_use): 每次使用固定金额
- 按量计费 (per_unit): 按数据量/CPU时长等计量
- 订阅制 (subscription): 按月/年订阅，无限使用

计费规则上链存证，确保规则透明可审计
"""
import uuid
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import BillingError, DataNotFoundError

logger = logging.getLogger(__name__)


class BillingMode(str, Enum):
    """计费模式枚举"""
    PER_USE = "per_use"         # 按次
    PER_UNIT = "per_unit"       # 按量
    SUBSCRIPTION = "subscription"  # 订阅


# 计费规则模板
BILLING_TEMPLATES: dict[str, dict] = {
    "per_use": {
        "mode": "per_use",
        "description": "按次计费 - 每次使用收取固定费用",
        "fields": ["price_per_use", "min_charge", "free_quota"],
        "default_values": {
            "price_per_use": 1.0,
            "min_charge": 0.0,
            "free_quota": 0,
        },
    },
    "per_unit": {
        "mode": "per_unit",
        "description": "按量计费 - 按使用量阶梯计费",
        "fields": ["unit_type", "price_per_unit", "tiers"],
        "default_values": {
            "unit_type": "MB",
            "price_per_unit": 0.1,
            "tiers": [
                {"from": 0, "to": 1000, "price": 0.1},
                {"from": 1000, "to": 10000, "price": 0.08},
                {"from": 10000, "to": -1, "price": 0.05},
            ],
        },
    },
    "subscription": {
        "mode": "subscription",
        "description": "订阅制 - 按月/年订阅，享受配额内无限使用",
        "fields": ["period", "price", "included_quota"],
        "default_values": {
            "period": "monthly",
            "price": 99.0,
            "included_quota": {
                "api_calls": 10000,
                "data_mb": 1000,
                "compute_hours": 100,
            },
        },
    },
}


def calculate_cost(
    billing_rule: dict,
    usage: dict,
) -> dict:
    """
    根据计费规则和使用量计算费用

    Args:
        billing_rule: 计费规则配置
        usage: 使用量数据

    Returns:
        费用计算结果
    """
    mode = billing_rule.get("mode", "per_use")

    if mode == "per_use":
        price_per_use = billing_rule.get("price_per_use", 1.0)
        use_count = usage.get("count", 1)
        free_quota = billing_rule.get("free_quota", 0)
        billable_count = max(0, use_count - free_quota)
        amount = billable_count * price_per_use
        min_charge = billing_rule.get("min_charge", 0.0)
        amount = max(amount, min_charge)

        return {
            "mode": mode,
            "amount": round(amount, 2),
            "detail": {
                "use_count": use_count,
                "free_quota": free_quota,
                "billable_count": billable_count,
                "price_per_use": price_per_use,
            },
        }

    elif mode == "per_unit":
        unit_type = billing_rule.get("unit_type", "MB")
        usage_amount = usage.get("amount", 0)
        tiers = billing_rule.get("tiers", [])

        amount = 0.0
        remaining = usage_amount
        tier_details = []

        for tier in sorted(tiers, key=lambda t: t["from"]):
            tier_from = tier["from"]
            tier_to = tier["to"] if tier["to"] > 0 else float("inf")
            tier_price = tier["price"]
            tier_range = min(remaining, tier_to - tier_from)

            if tier_range > 0:
                tier_cost = tier_range * tier_price
                amount += tier_cost
                remaining -= tier_range
                tier_details.append({
                    "from": tier_from,
                    "to": tier["to"],
                    "price": tier_price,
                    "usage": tier_range,
                    "cost": round(tier_cost, 2),
                })

        return {
            "mode": mode,
            "amount": round(amount, 2),
            "detail": {
                "unit_type": unit_type,
                "total_usage": usage_amount,
                "tiers_applied": tier_details,
            },
        }

    elif mode == "subscription":
        price = billing_rule.get("price", 0)
        period = billing_rule.get("period", "monthly")
        included_quota = billing_rule.get("included_quota", {})

        # 检查是否超出配额
        overage = {}
        overage_cost = 0.0
        overage_rate = billing_rule.get("overage_rate", 0.01)

        for key, included in included_quota.items():
            used = usage.get(key, 0)
            if used > included:
                overage[key] = used - included
                overage_cost += overage[key] * overage_rate

        total = price + overage_cost

        return {
            "mode": mode,
            "amount": round(total, 2),
            "detail": {
                "period": period,
                "base_price": price,
                "included_quota": included_quota,
                "usage": usage,
                "overage": overage,
                "overage_cost": round(overage_cost, 2),
            },
        }

    else:
        raise BillingError(f"不支持的计费模式: {mode}")


async def register_billing_rule(
    db: AsyncSession,
    product_id: str,
    rule_config: dict,
    creator_did: str,
) -> dict:
    """
    注册计费规则并上链存证

    Args:
        db: 异步数据库会话
        product_id: 关联产品 ID
        rule_config: 计费规则配置
        creator_did: 创建者 DID

    Returns:
        注册结果
    """
    mode = rule_config.get("mode", "per_use")
    if mode not in [m.value for m in BillingMode]:
        raise BillingError(f"不支持的计费模式: {mode}")

    rule_id = str(uuid.uuid4())
    rule_hash = gmssl_adapter.sm3_hash(str(rule_config))

    # 上链存证
    tx_hash = ""
    try:
        from app.services.blockchain_evidence_service import submit_evidence
        from app.schemas.blockchain import EvidenceCreate

        evidence = await submit_evidence(
            db,
            EvidenceCreate(
                node_type="publish",
                resource_id=product_id,
                resource_type="billing_rule",
                data_hash=rule_hash,
                evidence_data={
                    "rule_id": rule_id,
                    "product_id": product_id,
                    "mode": mode,
                    "rule_config": rule_config,
                    "creator_did": creator_did,
                    "registered_at": datetime.now(timezone.utc).isoformat(),
                    "rule_hash": rule_hash,
                },
            ),
        )
        tx_hash = evidence.tx_hash if hasattr(evidence, "tx_hash") else ""
    except Exception as e:
        logger.warning(f"Billing rule chain recording failed: {e}")

    logger.info(f"Billing rule registered: {rule_id}, mode={mode}, product={product_id}")

    return {
        "rule_id": rule_id,
        "product_id": product_id,
        "mode": mode,
        "rule_hash": rule_hash,
        "tx_hash": tx_hash,
        "creator_did": creator_did,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


def get_billing_template(mode: str) -> dict:
    """
    获取计费模式模板

    Args:
        mode: 计费模式

    Returns:
        模板信息
    """
    if mode not in BILLING_TEMPLATES:
        raise BillingError(f"未知的计费模式: {mode}")
    return BILLING_TEMPLATES[mode]


def list_billing_templates() -> list[dict]:
    """
    列出所有可用的计费模式模板

    Returns:
        模板列表
    """
    return list(BILLING_TEMPLATES.values())
