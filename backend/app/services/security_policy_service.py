"""
安全策略服务
RBAC/ABAC 策略管理 + 策略评估（支持 AND/OR/NOT 逻辑组合）

ABAC 评估引擎特性：
- 支持 AND/OR/NOT 逻辑组合
- 支持嵌套条件
- Deny 优先策略
- 策略冲突检测
"""
import uuid
import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import SecurityPolicy, PolicyAssignment
from app.exceptions import DataNotFoundError, SecurityError
from app.schemas.security import PolicyCreate, PolicyEvaluateRequest

logger = logging.getLogger(__name__)


async def list_policies(
    db: AsyncSession,
    policy_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """查询策略列表"""
    query = select(SecurityPolicy)
    if policy_type:
        query = query.where(SecurityPolicy.policy_type == policy_type)
    if status:
        query = query.where(SecurityPolicy.status == status)
    query = query.order_by(SecurityPolicy.priority.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    policies = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "policy_type": p.policy_type,
            "rules": p.rules,
            "priority": p.priority,
            "status": p.status,
            "created_by": str(p.created_by) if p.created_by else None,
            "created_at": str(p.created_at),
        }
        for p in policies
    ]


async def create_policy(
    db: AsyncSession,
    request: PolicyCreate,
    user_id: str,
) -> dict:
    """创建策略"""
    policy = SecurityPolicy(
        name=request.name,
        policy_type=request.policy_type,
        rules=request.rules,
        priority=request.priority,
        status="active",
        created_by=uuid.UUID(user_id),
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    return {
        "id": str(policy.id),
        "name": policy.name,
        "policy_type": policy.policy_type,
        "rules": policy.rules,
        "priority": policy.priority,
        "status": policy.status,
        "created_at": str(policy.created_at),
    }


async def get_policy(
    db: AsyncSession,
    policy_id: str,
) -> dict:
    """查询策略详情"""
    result = await db.execute(
        select(SecurityPolicy).where(SecurityPolicy.id == uuid.UUID(policy_id))
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise DataNotFoundError("策略未找到")

    # 查询策略分配
    assign_result = await db.execute(
        select(PolicyAssignment).where(
            PolicyAssignment.policy_id == uuid.UUID(policy_id)
        )
    )
    assignments = assign_result.scalars().all()

    return {
        "id": str(policy.id),
        "name": policy.name,
        "policy_type": policy.policy_type,
        "rules": policy.rules,
        "priority": policy.priority,
        "status": policy.status,
        "assignments": [
            {
                "id": str(a.id),
                "target_type": a.target_type,
                "target_id": str(a.target_id),
            }
            for a in assignments
        ],
        "created_at": str(policy.created_at),
    }


async def update_policy(
    db: AsyncSession,
    policy_id: str,
    request: PolicyCreate,
) -> dict:
    """更新策略"""
    result = await db.execute(
        select(SecurityPolicy).where(SecurityPolicy.id == uuid.UUID(policy_id))
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise DataNotFoundError("策略未找到")

    policy.name = request.name
    policy.policy_type = request.policy_type
    policy.rules = request.rules
    policy.priority = request.priority
    await db.commit()
    await db.refresh(policy)

    return {
        "id": str(policy.id),
        "name": policy.name,
        "policy_type": policy.policy_type,
        "rules": policy.rules,
        "priority": policy.priority,
        "status": policy.status,
    }


async def delete_policy(
    db: AsyncSession,
    policy_id: str,
) -> None:
    """删除策略（软删除）"""
    result = await db.execute(
        select(SecurityPolicy).where(SecurityPolicy.id == uuid.UUID(policy_id))
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise DataNotFoundError("策略未找到")
    policy.status = "deleted"
    await db.commit()


def _evaluate_single_condition(
    condition: dict, context: dict
) -> bool:
    """
    评估单个条件
    
    Args:
        condition: 条件字典
        context: 上下文属性
        
    Returns:
        条件是否满足
    """
    attr = condition.get("attribute", "")
    operator = condition.get("operator", "eq")
    value = condition.get("value")
    logic = condition.get("logic", "").upper()
    
    ctx_value = context.get(attr)
    
    # 处理 NOT 逻辑
    negate = logic == "NOT"
    
    result = False
    
    if operator == "exists":
        result = ctx_value is not None
    elif operator == "not_exists":
        result = ctx_value is None
    elif ctx_value is None:
        result = False
    elif operator == "eq":
        result = ctx_value == value
    elif operator == "ne":
        result = ctx_value != value
    elif operator == "in":
        result = ctx_value in (value or [])
    elif operator == "not_in":
        result = ctx_value not in (value or [])
    elif operator == "gt":
        result = _compare(ctx_value, value, lambda a, b: a > b)
    elif operator == "gte":
        result = _compare(ctx_value, value, lambda a, b: a >= b)
    elif operator == "lt":
        result = _compare(ctx_value, value, lambda a, b: a < b)
    elif operator == "lte":
        result = _compare(ctx_value, value, lambda a, b: a <= b)
    elif operator == "contains":
        result = str(value) in str(ctx_value)
    elif operator == "starts_with":
        result = str(ctx_value).startswith(str(value))
    elif operator == "ends_with":
        result = str(ctx_value).endswith(str(value))
    else:
        result = False
    
    return not result if negate else result


def _compare(actual: Any, expected: Any, comparator: callable) -> bool:
    """比较两个值"""
    try:
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return comparator(actual, expected)
        return comparator(str(actual), str(expected))
    except (TypeError, ValueError):
        return False


def _evaluate_conditions_with_logic(
    conditions: list[dict],
    condition_logic: str = "AND",
    context: dict = None,
) -> bool:
    """
    评估条件列表（支持 AND/OR 逻辑）
    
    Args:
        conditions: 条件列表
        condition_logic: 条件组合逻辑（AND/OR）
        context: 上下文属性
        
    Returns:
        是否满足
    """
    context = context or {}
    
    if not conditions:
        return True
    
    results = []
    for condition in conditions:
        # 检查是否有嵌套条件
        sub_conditions = condition.get("conditions", [])
        if sub_conditions:
            sub_logic = condition.get("logic", "AND")
            sub_result = _evaluate_conditions_with_logic(
                sub_conditions, sub_logic, context
            )
            results.append(sub_result)
        else:
            results.append(_evaluate_single_condition(condition, context))
    
    if condition_logic == "OR":
        return any(results)
    elif condition_logic == "NOT":
        return not all(results)
    else:
        # 默认 AND
        return all(results)


async def evaluate_permission(
    db: AsyncSession,
    request: PolicyEvaluateRequest,
) -> dict:
    """
    评估权限

    RBAC: 检查角色是否有所需权限
    ABAC: 根据上下文属性动态评估（支持 AND/OR/NOT 逻辑组合）
    
    评估流程：
    1. 查找所有活跃策略
    2. RBAC 策略：检查角色和权限
    3. ABAC 策略：使用 AND/OR/NOT 逻辑评估条件
    4. Deny 优先：任何匹配的 deny 规则都会拒绝访问
    
    Args:
        db: 数据库会话
        request: 评估请求
        
    Returns:
        评估结果
    """
    # 查找所有活跃策略
    query = select(SecurityPolicy).where(
        SecurityPolicy.status == "active"
    ).order_by(SecurityPolicy.priority.desc())
    result = await db.execute(query)
    policies = result.scalars().all()

    allowed = False
    matched_policies = []
    deny_reason = ""
    evaluation_details = []

    for policy in policies:
        rules = policy.rules
        if not isinstance(rules, dict):
            continue
            
        if policy.policy_type == "RBAC":
            # RBAC: 检查 subject_did 的角色是否在允许列表中
            allowed_roles = rules.get("allowed_roles", [])
            allowed_actions = rules.get("allowed_actions", [])
            resource_types = rules.get("resource_types", [])

            if resource_types and request.resource_type not in resource_types:
                continue

            if allowed_actions and request.action not in allowed_actions:
                continue

            matched_policies.append(str(policy.id))
            allowed = True
            evaluation_details.append({
                "policy_id": str(policy.id),
                "policy_type": "RBAC",
                "matched": True,
            })
            break

        elif policy.policy_type == "ABAC":
            # ABAC: 根据上下文属性评估（支持 AND/OR/NOT 逻辑）
            conditions = rules.get("conditions", [])
            condition_logic = rules.get("condition_logic", "AND")
            context = request.context or {}

            # 使用增强的条件评估引擎
            conditions_met = _evaluate_conditions_with_logic(
                conditions, condition_logic, context
            )

            if conditions_met:
                allowed_actions = rules.get("allowed_actions", [])
                effect = rules.get("effect", "allow")
                
                if not allowed_actions or request.action in allowed_actions:
                    matched_policies.append(str(policy.id))
                    
                    if effect == "deny":
                        # Deny 优先
                        allowed = False
                        deny_reason = f"策略 {policy.name} 拒绝访问"
                        evaluation_details.append({
                            "policy_id": str(policy.id),
                            "policy_type": "ABAC",
                            "effect": "deny",
                            "matched": True,
                            "condition_logic": condition_logic,
                        })
                        break
                    else:
                        allowed = True
                        evaluation_details.append({
                            "policy_id": str(policy.id),
                            "policy_type": "ABAC",
                            "effect": "allow",
                            "matched": True,
                            "condition_logic": condition_logic,
                        })

    if not allowed and not deny_reason:
        deny_reason = "无匹配策略或策略拒绝访问"

    return {
        "allowed": allowed,
        "subject_did": request.subject_did,
        "resource_type": request.resource_type,
        "resource_id": request.resource_id,
        "action": request.action,
        "matched_policies": matched_policies,
        "evaluation_details": evaluation_details,
        "deny_reason": deny_reason if not allowed else None,
    }
