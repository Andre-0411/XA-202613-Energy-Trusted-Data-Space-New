"""
数据产品智能推荐服务
====================
- 基于内容的推荐：分析用户历史订阅的数据类型、行业、安全等级，推荐相似数据产品
- 协同过滤：找到相似用户（订阅了相同数据产品的用户），推荐他们订阅但当前用户未订阅的产品
- 热度推荐：基于订阅次数、评分、最近活跃度排序
- 推荐理由：每个推荐结果附带推荐理由
"""
import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import Counter

from sqlalchemy import select, func, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import DataProduct, ProductSubscription
from app.models.user import Organization

logger = logging.getLogger(__name__)


# ==================== 推荐理由生成 ====================

def _generate_reason(
    product: DataProduct,
    strategy: str,
    matched_products: list[str] = None,
    similar_users_count: int = 0,
) -> str:
    """生成推荐理由"""
    name = product.name
    ptype = product.product_type or "数据产品"

    if strategy == "content_based":
        if matched_products:
            return f"因为您订阅了「{matched_products[0]}」等同类产品，推荐您关注「{name}」（{ptype}）"
        return f"基于您的订阅偏好，推荐「{name}」（{ptype}）"

    elif strategy == "collaborative":
        return f"有 {similar_users_count} 位与您兴趣相似的用户订阅了「{name}」，推荐您也关注"

    elif strategy == "hot":
        return f"「{name}」是近期热门的{ptype}产品，订阅量持续增长"

    return f"推荐关注「{name}」"


# ==================== 基于内容的推荐 ====================

async def _content_based_recommend(
    session: AsyncSession,
    user_id: str,
    limit: int = 5,
) -> list[dict]:
    """
    基于内容的推荐
    分析用户历史订阅的产品类型，推荐同类但未订阅的产品
    """
    # 1. 获取用户已订阅的产品
    sub_result = await session.execute(
        select(ProductSubscription.product_id).where(
            ProductSubscription.subscriber_id == user_id,
            ProductSubscription.status.in_(["approved", "active"]),
        )
    )
    subscribed_ids = [str(row[0]) for row in sub_result.all()]

    if not subscribed_ids:
        return []

    # 2. 获取已订阅产品的类型分布
    prod_result = await session.execute(
        select(DataProduct).where(DataProduct.id.in_(subscribed_ids))
    )
    subscribed_products = prod_result.scalars().all()

    # 统计偏好
    type_counter = Counter()
    subscribed_names = []
    for p in subscribed_products:
        type_counter[p.product_type] += 1
        subscribed_names.append(p.name)

    preferred_types = [t for t, _ in type_counter.most_common(3)]

    # 3. 推荐同类但未订阅的产品
    rec_result = await session.execute(
        select(DataProduct).where(
            DataProduct.status == "published",
            DataProduct.product_type.in_(preferred_types),
            ~DataProduct.id.in_(subscribed_ids),
        ).order_by(DataProduct.created_at.desc()).limit(limit * 2)
    )
    candidates = rec_result.scalars().all()

    results = []
    for p in candidates:
        results.append({
            "product_id": str(p.id),
            "name": p.name,
            "product_type": p.product_type,
            "pricing": p.pricing,
            "description": (p.description or "")[:200],
            "strategy": "content_based",
            "reason": _generate_reason(p, "content_based", matched_products=subscribed_names[:2]),
            "score": 0.8,
        })
        if len(results) >= limit:
            break

    return results


# ==================== 协同过滤推荐 ====================

async def _collaborative_recommend(
    session: AsyncSession,
    user_id: str,
    limit: int = 5,
) -> list[dict]:
    """
    协同过滤推荐
    找到与当前用户订阅了相同产品的用户，推荐他们订阅但当前用户未订阅的产品
    """
    # 1. 获取当前用户已订阅的产品ID
    my_subs_result = await session.execute(
        select(ProductSubscription.product_id).where(
            ProductSubscription.subscriber_id == user_id,
            ProductSubscription.status.in_(["approved", "active"]),
        )
    )
    my_product_ids = [str(row[0]) for row in my_subs_result.all()]

    if not my_product_ids:
        return []

    # 2. 找到订阅了相同产品的其他用户
    similar_users_result = await session.execute(
        select(distinct(ProductSubscription.subscriber_id)).where(
            ProductSubscription.product_id.in_(my_product_ids),
            ProductSubscription.subscriber_id != user_id,
            ProductSubscription.status.in_(["approved", "active"]),
        )
    )
    similar_user_ids = [str(row[0]) for row in similar_users_result.all()]

    if not similar_user_ids:
        return []

    # 3. 获取这些相似用户订阅了但当前用户未订阅的产品
    others_subs_result = await session.execute(
        select(
            ProductSubscription.product_id,
            func.count(ProductSubscription.id).label("sub_count"),
        ).where(
            ProductSubscription.subscriber_id.in_(similar_user_ids),
            ProductSubscription.product_id.notin_(my_product_ids),
            ProductSubscription.status.in_(["approved", "active"]),
        ).group_by(ProductSubscription.product_id)
        .order_by(func.count(ProductSubscription.id).desc())
        .limit(limit)
    )
    recommended_ids = [(str(row[0]), row[1]) for row in others_subs_result.all()]

    if not recommended_ids:
        return []

    # 4. 获取产品详情
    prod_ids = [pid for pid, _ in recommended_ids]
    prod_result = await session.execute(
        select(DataProduct).where(DataProduct.id.in_(prod_ids))
    )
    products_map = {str(p.id): p for p in prod_result.scalars().all()}

    results = []
    sub_count_map = dict(recommended_ids)
    for pid, count in recommended_ids:
        p = products_map.get(pid)
        if not p:
            continue
        results.append({
            "product_id": str(p.id),
            "name": p.name,
            "product_type": p.product_type,
            "pricing": p.pricing,
            "description": (p.description or "")[:200],
            "strategy": "collaborative",
            "reason": _generate_reason(p, "collaborative", similar_users_count=count),
            "score": min(0.5 + count * 0.1, 0.95),
        })

    return results


# ==================== 热度推荐 ====================

async def _hot_recommend(
    session: AsyncSession,
    limit: int = 5,
    days: int = 30,
) -> list[dict]:
    """
    热度推荐
    基于最近N天的订阅次数排序
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 统计最近订阅次数
    hot_result = await session.execute(
        select(
            ProductSubscription.product_id,
            func.count(ProductSubscription.id).label("sub_count"),
        ).where(
            ProductSubscription.created_at >= since,
            ProductSubscription.status.in_(["approved", "active", "pending"]),
        ).group_by(ProductSubscription.product_id)
        .order_by(func.count(ProductSubscription.id).desc())
        .limit(limit)
    )
    hot_ids = [(str(row[0]), row[1]) for row in hot_result.all()]

    if not hot_ids:
        # 回退：返回最新的已发布产品
        fallback_result = await session.execute(
            select(DataProduct).where(DataProduct.status == "published")
            .order_by(DataProduct.created_at.desc()).limit(limit)
        )
        products = fallback_result.scalars().all()
        return [{
            "product_id": str(p.id),
            "name": p.name,
            "product_type": p.product_type,
            "pricing": p.pricing,
            "description": (p.description or "")[:200],
            "strategy": "hot",
            "reason": _generate_reason(p, "hot"),
            "score": 0.6,
            "subscription_count": 0,
        } for p in products]

    prod_ids = [pid for pid, _ in hot_ids]
    prod_result = await session.execute(
        select(DataProduct).where(DataProduct.id.in_(prod_ids))
    )
    products_map = {str(p.id): p for p in prod_result.scalars().all()}
    sub_count_map = dict(hot_ids)

    results = []
    for pid, count in hot_ids:
        p = products_map.get(pid)
        if not p:
            continue
        results.append({
            "product_id": str(p.id),
            "name": p.name,
            "product_type": p.product_type,
            "pricing": p.pricing,
            "description": (p.description or "")[:200],
            "strategy": "hot",
            "reason": _generate_reason(p, "hot"),
            "score": min(0.6 + count * 0.05, 0.95),
            "subscription_count": count,
        })

    return results


# ==================== 统一推荐接口 ====================

async def get_recommendations(
    db: AsyncSession,
    user_id: str = "",
    limit: int = 10,
    strategies: Optional[list[str]] = None,
) -> dict:
    """
    获取数据产品智能推荐

    参数：
        db: 数据库会话
        user_id: 用户ID
        limit: 推荐数量
        strategies: 指定策略列表，可选 ["content_based", "collaborative", "hot"]
                    默认全部策略混合

    返回：
        {
            "recommendations": [...],  # 推荐列表
            "total": int,
            "strategies_used": [...],  # 使用的推荐策略
        }
    """
    if strategies is None:
        strategies = ["content_based", "collaborative", "hot"]

    all_recommendations = []
    used_strategies = []

    # 每种策略分配配额
    per_strategy = max(limit // len(strategies), 3)

    for strategy in strategies:
        try:
            if strategy == "content_based" and user_id:
                recs = await _content_based_recommend(db, user_id, limit=per_strategy)
                all_recommendations.extend(recs)
                used_strategies.append(strategy)

            elif strategy == "collaborative" and user_id:
                recs = await _collaborative_recommend(db, user_id, limit=per_strategy)
                all_recommendations.extend(recs)
                used_strategies.append(strategy)

            elif strategy == "hot":
                recs = await _hot_recommend(db, limit=per_strategy)
                all_recommendations.extend(recs)
                used_strategies.append(strategy)

        except Exception as e:
            logger.warning(f"Recommendation strategy '{strategy}' failed: {e}")

    # 去重（同一产品取最高分）
    seen = {}
    for rec in all_recommendations:
        pid = rec["product_id"]
        if pid not in seen or rec["score"] > seen[pid]["score"]:
            seen[pid] = rec

    # 按分数排序
    deduplicated = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

    return {
        "recommendations": deduplicated[:limit],
        "total": len(deduplicated[:limit]),
        "strategies_used": used_strategies,
    }


async def get_personalized_recommendations(
    db: AsyncSession,
    user_id: str,
    industry: str = "",
    data_type: str = "",
    security_level: str = "",
    limit: int = 5,
) -> dict:
    """
    个性化推荐（带用户偏好参数）

    参数：
        user_id: 用户ID
        industry: 偏好行业（如：新能源/电力/燃气）
        data_type: 偏好数据类型（如：发电量/负荷/气象）
        security_level: 偏好安全等级（如：public/internal/confidential）
        limit: 推荐数量
    """
    # 先尝试基于内容 + 协同过滤
    recommendations = await get_recommendations(
        db=db, user_id=user_id, limit=limit + 5,
        strategies=["content_based", "collaborative"],
    )

    results = recommendations["recommendations"]

    # 如果有额外偏好参数，进行二次过滤
    if industry or data_type:
        filtered = []
        for rec in results:
            name_lower = (rec.get("name", "") + rec.get("description", "")).lower()
            ptype = (rec.get("product_type", "")).lower()

            match = True
            if industry and industry.lower() not in name_lower and industry.lower() not in ptype:
                match = False
            if data_type and data_type.lower() not in name_lower:
                match = False

            if match:
                filtered.append(rec)

        if filtered:
            results = filtered

    # 如果个性化结果不足，补充热度推荐
    if len(results) < limit:
        hot_recs = await _hot_recommend(db, limit=limit - len(results))
        existing_ids = {r["product_id"] for r in results}
        for rec in hot_recs:
            if rec["product_id"] not in existing_ids:
                results.append(rec)

    return {
        "recommendations": results[:limit],
        "total": len(results[:limit]),
        "filters": {
            "industry": industry,
            "data_type": data_type,
            "security_level": security_level,
        },
    }
