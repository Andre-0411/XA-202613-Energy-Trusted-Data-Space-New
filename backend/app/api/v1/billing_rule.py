"""
计费规则 API - /api/v1/blockchain/billing-rules
计费规则上链 + 模板管理 + 费用计算
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services.billing_rule_service import (
    register_billing_rule,
    calculate_cost,
    get_billing_template,
    list_billing_templates,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/templates", response_model=ApiResponse)
async def get_templates():
    """列出所有计费模式模板"""
    templates = list_billing_templates()
    return ApiResponse(data=templates)


@router.get("/templates/{mode}", response_model=ApiResponse)
async def get_template(mode: str):
    """获取指定计费模式的模板"""
    try:
        template = get_billing_template(mode)
        return ApiResponse(data=template)
    except Exception as e:
        return ApiResponse(code=2003, message=str(e), data=None)


@router.post("/calculate", response_model=ApiResponse)
async def calc_cost(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """
    计算费用

    请求体:
    {
        "billing_rule": {"mode": "per_use", "price_per_use": 1.0},
        "usage": {"count": 10}
    }
    """
    billing_rule = body.get("billing_rule", {})
    usage = body.get("usage", {})

    if not billing_rule:
        return ApiResponse(code=2003, message="billing_rule 为必填项", data=None)

    try:
        result = calculate_cost(billing_rule, usage)
        return ApiResponse(data=result)
    except Exception as e:
        return ApiResponse(code=4020, message=f"费用计算失败: {e}", data=None)


@router.post("/register", response_model=ApiResponse)
async def register_rule(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    注册计费规则并上链存证

    请求体:
    {
        "product_id": "xxx",
        "rule_config": {
            "mode": "per_use",
            "price_per_use": 1.0,
            "free_quota": 100
        }
    }
    """
    product_id = body.get("product_id", "")
    rule_config = body.get("rule_config", {})

    if not product_id:
        return ApiResponse(code=2003, message="product_id 为必填项", data=None)
    if not rule_config:
        return ApiResponse(code=2003, message="rule_config 为必填项", data=None)

    user_did = user.get("user_id", "")
    try:
        result = await register_billing_rule(
            db=db,
            product_id=product_id,
            rule_config=rule_config,
            creator_did=user_did,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Billing rule registration failed: {e}")
        return ApiResponse(code=4020, message=f"计费规则注册失败: {e}", data=None)
