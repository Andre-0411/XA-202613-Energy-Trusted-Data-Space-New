"""
ABAC（基于属性的访问控制）服务
属性定义 + 策略 CRUD + 策略评估引擎（AND/OR/NOT 逻辑）+ 冲突检测

增强功能：
- 时间条件（工作时间/非工作时间判断）
- IP 白名单/地理位置条件
- 属性条件（扩展比较操作符）
- 策略模板（预置策略快速创建）
- 评估缓存（LRU 缓存策略评估结果，提升性能）
"""
import re
import uuid
import hashlib
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional, Any
from enum import Enum

from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import SecurityPolicy, PolicyAssignment
from app.exceptions import DataNotFoundError, SecurityError
from app.schemas.abac import (
    AttributeDefinition,
    Condition,
    PolicyRule,
    Policy,
    PolicyTarget,
    AccessRequest,
    PolicyEvaluation,
    PolicyConflict,
    AbacPolicyCreateRequest,
    AbacPolicyEvaluateRequest,
)

logger = logging.getLogger(__name__)


class LogicOperator(str, Enum):
    """逻辑运算符"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(str, Enum):
    """比较运算符"""
    EQ = "eq"
    NE = "ne"
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    TIME_IN_RANGE = "time_in_range"           # 时间在指定范围内
    TIME_IS_WORK_HOURS = "time_is_work_hours"  # 是否工作时间
    IP_IN_SUBNET = "ip_in_subnet"             # IP 在子网内
    IP_IN_LIST = "ip_in_list"                 # IP 在白名单中


# ==================== 评估缓存 ====================

class _EvaluationCache:
    """
    LRU 缓存策略评估结果

    缓存键 = hash(策略ID + 上下文摘要)
    缓存容量默认 256 条，TTL 60 秒
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 60):
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_size: int = max_size
        self._ttl: int = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期则返回 None"""
        if key not in self._cache:
            return None
        ts, value = self._cache[key]
        if (datetime.now(timezone.utc).timestamp() - ts) > self._ttl:
            # 过期，移除
            del self._cache[key]
            return None
        # 移到末尾（最近使用）
        self._cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (datetime.now(timezone.utc).timestamp(), value)
        # 超过容量则淘汰最旧的
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, policy_id: Optional[str] = None) -> None:
        """清除缓存；若指定 policy_id 则仅清除该策略相关缓存"""
        if policy_id is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache if policy_id in k]
            for k in keys_to_remove:
                del self._cache[k]

    @staticmethod
    def build_key(policy_id: str, context: dict[str, Any]) -> str:
        """构建缓存键"""
        # 仅使用稳定的上下文子集来构建摘要
        stable_keys = [
            "subject.role", "subject.department", "subject.clearance_level",
            "resource.type", "resource.sensitivity", "resource.owner",
            "action.type", "environment.ip", "environment.location",
        ]
        parts = [f"{k}={context.get(k, '')}" for k in stable_keys]
        raw = f"{policy_id}|{'|'.join(parts)}"
        return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()


# 全局评估缓存实例
_eval_cache = _EvaluationCache()


# ==================== 内置属性定义 ====================

BUILTIN_ATTRIBUTES: list[AttributeDefinition] = [
    AttributeDefinition(
        name="subject.role",
        display_name="主体角色",
        data_type="string",
        description="请求主体的角色",
        category="subject",
    ),
    AttributeDefinition(
        name="subject.department",
        display_name="主体部门",
        data_type="string",
        description="请求主体的部门",
        category="subject",
    ),
    AttributeDefinition(
        name="subject.clearance_level",
        display_name="安全等级",
        data_type="integer",
        description="请求主体的安全许可等级",
        category="subject",
        validation_rules={"min": 1, "max": 5},
    ),
    AttributeDefinition(
        name="subject.did",
        display_name="主体 DID",
        data_type="string",
        description="请求主体的去中心化标识符",
        category="subject",
    ),
    AttributeDefinition(
        name="resource.type",
        display_name="资源类型",
        data_type="string",
        description="被访问资源的类型",
        category="resource",
    ),
    AttributeDefinition(
        name="resource.sensitivity",
        display_name="资源敏感度",
        data_type="integer",
        description="资源的敏感等级",
        category="resource",
        validation_rules={"min": 1, "max": 4},
    ),
    AttributeDefinition(
        name="resource.owner",
        display_name="资源所有者",
        data_type="string",
        description="资源的所有者 DID",
        category="resource",
    ),
    AttributeDefinition(
        name="action.type",
        display_name="操作类型",
        data_type="string",
        description="执行的操作类型",
        category="action",
    ),
    AttributeDefinition(
        name="environment.time",
        display_name="请求时间",
        data_type="datetime",
        description="请求发生的时间（ISO 8601 格式）",
        category="environment",
    ),
    AttributeDefinition(
        name="environment.ip",
        display_name="请求IP",
        data_type="string",
        description="请求来源 IP 地址",
        category="environment",
    ),
    AttributeDefinition(
        name="environment.location",
        display_name="请求位置",
        data_type="string",
        description="请求来源的地理位置",
        category="environment",
    ),
]


# ==================== 策略模板 ====================

POLICY_TEMPLATES: dict[str, dict[str, Any]] = {
    "working_hours_only": {
        "name": "仅工作时间访问",
        "description": "限制在工作时间（周一至周五 09:00-18:00）内访问",
        "rules": [
            {
                "id": "rule_wh",
                "name": "工作时间检查",
                "effect": "allow",
                "conditions": [
                    {
                        "attribute": "environment.time",
                        "operator": "time_is_work_hours",
                        "value": True,
                    }
                ],
                "condition_logic": "AND",
            }
        ],
    },
    "ip_whitelist": {
        "name": "IP 白名单访问",
        "description": "仅允许来自指定 IP 白名单的请求访问",
        "rules": [
            {
                "id": "rule_ip",
                "name": "IP 白名单检查",
                "effect": "allow",
                "conditions": [
                    {
                        "attribute": "environment.ip",
                        "operator": "ip_in_list",
                        "value": ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
                    }
                ],
                "condition_logic": "AND",
            }
        ],
    },
    "high_sensitivity_restricted": {
        "name": "高敏感资源限制",
        "description": "高敏感度资源（≥3）仅允许安全等级≥4的用户访问",
        "rules": [
            {
                "id": "rule_sens",
                "name": "敏感资源保护",
                "effect": "allow",
                "conditions": [
                    {
                        "attribute": "resource.sensitivity",
                        "operator": "lt",
                        "value": 3,
                    },
                ],
                "condition_logic": "AND",
            },
            {
                "id": "rule_sens_high",
                "name": "高敏感资源高等级访问",
                "effect": "allow",
                "conditions": [
                    {
                        "attribute": "resource.sensitivity",
                        "operator": "gte",
                        "value": 3,
                    },
                    {
                        "attribute": "subject.clearance_level",
                        "operator": "gte",
                        "value": 4,
                    },
                ],
                "condition_logic": "AND",
            },
        ],
    },
    "admin_only": {
        "name": "仅管理员访问",
        "description": "仅允许管理员角色执行管理操作",
        "rules": [
            {
                "id": "rule_admin",
                "name": "管理员角色检查",
                "effect": "allow",
                "conditions": [
                    {
                        "attribute": "subject.role",
                        "operator": "eq",
                        "value": "admin",
                    }
                ],
                "condition_logic": "AND",
            }
        ],
    },
    "owner_or_admin": {
        "name": "资源所有者或管理员",
        "description": "允许资源所有者或管理员访问",
        "rules": [
            {
                "id": "rule_owner",
                "name": "资源所有者",
                "effect": "allow",
                "conditions": [
                    {
                        "attribute": "resource.owner",
                        "operator": "eq",
                        "value": "${subject.did}",
                    }
                ],
                "condition_logic": "AND",
            },
            {
                "id": "rule_admin2",
                "name": "管理员角色",
                "effect": "allow",
                "conditions": [
                    {
                        "attribute": "subject.role",
                        "operator": "eq",
                        "value": "admin",
                    }
                ],
                "condition_logic": "AND",
            },
        ],
    },
}


# ==================== 时间/IP 工具函数 ====================

def _is_work_hours(dt_str: str) -> bool:
    """
    判断给定时间是否为工作时间（周一至周五 09:00-18:00）

    Args:
        dt_str: ISO 8601 格式的时间字符串

    Returns:
        是否为工作时间
    """
    try:
        # 解析 ISO 格式时间
        dt_str_clean = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str_clean)
        # 周一=0, 周日=6
        if dt.weekday() >= 5:
            return False
        return 9 <= dt.hour < 18
    except (ValueError, AttributeError):
        logger.warning(f"无法解析时间字符串: {dt_str}")
        return False


def _ip_in_subnet(ip_str: str, subnet: str) -> bool:
    """
    检查 IP 地址是否在指定子网内

    简化实现：支持 CIDR 格式（如 10.0.0.0/8）和精确 IP 匹配

    Args:
        ip_str: 待检查的 IP 地址
        subnet: 子网（CIDR 或精确 IP）

    Returns:
        是否在子网内
    """
    try:
        if "/" in subnet:
            # CIDR 模式
            parts = subnet.split("/")
            network_addr = parts[0]
            prefix_len = int(parts[1])

            ip_int = _ip_to_int(ip_str)
            net_int = _ip_to_int(network_addr)

            if ip_int is None or net_int is None:
                return False

            mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
            return (ip_int & mask) == (net_int & mask)
        else:
            # 精确匹配
            return ip_str == subnet
    except (ValueError, IndexError):
        return False


def _ip_to_int(ip_str: str) -> Optional[int]:
    """将 IPv4 地址转换为整数"""
    try:
        parts = ip_str.strip().split(".")
        if len(parts) != 4:
            return None
        result = 0
        for part in parts:
            result = (result << 8) | int(part)
        return result
    except (ValueError, AttributeError):
        return None


def _ip_in_list(ip_str: str, ip_list: list[str]) -> bool:
    """
    检查 IP 是否在白名单列表中

    支持 CIDR 和精确 IP 两种格式

    Args:
        ip_str: 待检查的 IP
        ip_list: 白名单列表

    Returns:
        是否在列表中
    """
    for entry in ip_list:
        if _ip_in_subnet(ip_str, entry):
            return True
    return False


# ==================== 条件评估 ====================

def _evaluate_condition(condition: Condition, context: dict[str, Any]) -> bool:
    """
    评估单个条件

    Args:
        condition: 条件定义
        context: 上下文属性

    Returns:
        条件是否满足
    """
    attr_value = context.get(condition.attribute)
    operator = condition.operator
    expected = condition.value

    # 处理 NOT 逻辑
    negate = condition.logic == "NOT"

    result = False

    if operator == ComparisonOperator.EXISTS:
        result = attr_value is not None
    elif operator == ComparisonOperator.NOT_EXISTS:
        result = attr_value is None
    elif operator == ComparisonOperator.TIME_IN_RANGE:
        # 时间范围检查：expected 格式 {"start": "09:00", "end": "18:00"}
        result = _check_time_range(attr_value, expected)
    elif operator == ComparisonOperator.TIME_IS_WORK_HOURS:
        # 工作时间检查
        if attr_value:
            is_work = _is_work_hours(str(attr_value))
            result = is_work == bool(expected)
        else:
            result = False
    elif operator == ComparisonOperator.IP_IN_SUBNET:
        # IP 子网检查
        if attr_value:
            result = _ip_in_subnet(str(attr_value), str(expected))
        else:
            result = False
    elif operator == ComparisonOperator.IP_IN_LIST:
        # IP 白名单检查
        if attr_value:
            ip_list = expected if isinstance(expected, list) else [expected]
            result = _ip_in_list(str(attr_value), ip_list)
        else:
            result = False
    elif attr_value is None:
        # 属性不存在且不是 exists/not_exists/时间/IP 操作
        result = False
    elif operator == ComparisonOperator.EQ:
        result = attr_value == expected
    elif operator == ComparisonOperator.NE:
        result = attr_value != expected
    elif operator == ComparisonOperator.IN:
        result = attr_value in (expected if isinstance(expected, list) else [expected])
    elif operator == ComparisonOperator.NOT_IN:
        result = attr_value not in (expected if isinstance(expected, list) else [expected])
    elif operator == ComparisonOperator.GT:
        result = _compare_values(attr_value, expected, lambda a, b: a > b)
    elif operator == ComparisonOperator.GTE:
        result = _compare_values(attr_value, expected, lambda a, b: a >= b)
    elif operator == ComparisonOperator.LT:
        result = _compare_values(attr_value, expected, lambda a, b: a < b)
    elif operator == ComparisonOperator.LTE:
        result = _compare_values(attr_value, expected, lambda a, b: a <= b)
    elif operator == ComparisonOperator.CONTAINS:
        result = str(expected) in str(attr_value)
    elif operator == ComparisonOperator.STARTS_WITH:
        result = str(attr_value).startswith(str(expected))
    elif operator == ComparisonOperator.ENDS_WITH:
        result = str(attr_value).endswith(str(expected))
    elif operator == ComparisonOperator.REGEX:
        result = bool(re.match(str(expected), str(attr_value)))
    else:
        logger.warning(f"未知操作符: {operator}")
        result = False

    return not result if negate else result


def _check_time_range(time_str: Any, expected: Any) -> bool:
    """
    检查时间是否在指定范围内

    Args:
        time_str: ISO 8601 时间字符串
        expected: {"start": "HH:MM", "end": "HH:MM"} 或 {"start_hour": 9, "end_hour": 18}

    Returns:
        是否在范围内
    """
    try:
        if not time_str:
            return False
        time_str_clean = str(time_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(time_str_clean)
        hour_min = dt.hour + dt.minute / 60.0

        if isinstance(expected, dict):
            if "start" in expected and "end" in expected:
                start_parts = str(expected["start"]).split(":")
                end_parts = str(expected["end"]).split(":")
                start_time = int(start_parts[0]) + int(start_parts[1]) / 60.0 if len(start_parts) == 2 else int(start_parts[0])
                end_time = int(end_parts[0]) + int(end_parts[1]) / 60.0 if len(end_parts) == 2 else int(end_parts[0])
                return start_time <= hour_min < end_time
            elif "start_hour" in expected and "end_hour" in expected:
                return expected["start_hour"] <= hour_min < expected["end_hour"]

        return False
    except (ValueError, AttributeError, TypeError):
        logger.warning(f"时间范围检查失败: time={time_str}, expected={expected}")
        return False


def _compare_values(
    actual: Any, expected: Any, comparator: Any
) -> bool:
    """
    比较两个值

    Args:
        actual: 实际值
        expected: 期望值
        comparator: 比较函数

    Returns:
        比较结果
    """
    try:
        # 尝试数值比较
        if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            return comparator(actual, expected)
        # 字符串转换后比较
        return comparator(str(actual), str(expected))
    except (TypeError, ValueError):
        return False


def _evaluate_conditions(
    conditions: list[Condition],
    condition_logic: str = "AND",
    context: Optional[dict[str, Any]] = None,
) -> tuple[bool, list[dict[str, Any]]]:
    """
    评估条件列表（支持 AND/OR 逻辑）

    Args:
        conditions: 条件列表
        condition_logic: 条件组合逻辑（AND/OR）
        context: 上下文属性

    Returns:
        (是否满足, 评估详情列表)
    """
    context = context or {}
    details: list[dict[str, Any]] = []

    if not conditions:
        return True, details

    results: list[bool] = []
    for condition in conditions:
        met = _evaluate_condition(condition, context)
        results.append(met)
        details.append({
            "attribute": condition.attribute,
            "operator": condition.operator,
            "expected": condition.value,
            "actual": context.get(condition.attribute),
            "met": met,
            "logic": condition.logic,
        })

    if condition_logic == "OR":
        overall = any(results)
    else:
        # 默认 AND
        overall = all(results)

    return overall, details


def _evaluate_rule(rule: PolicyRule, context: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """
    评估策略规则

    支持嵌套的 AND/OR/NOT 逻辑组合

    Args:
        rule: 策略规则
        context: 上下文属性

    Returns:
        (是否满足, 评估详情)
    """
    # 评估规则自身的条件
    conditions_met, condition_details = _evaluate_conditions(
        rule.conditions, rule.condition_logic, context
    )

    # 评估子规则
    sub_rule_results: list[bool] = []
    sub_rule_details: list[Any] = []
    for sub_rule in rule.sub_rules:
        sub_met, sub_detail = _evaluate_rule(sub_rule, context)
        sub_rule_results.append(sub_met)
        sub_rule_details.append(sub_detail)

    # 组合子规则结果
    if rule.sub_rules:
        if rule.condition_logic == "OR":
            sub_rules_met = any(sub_rule_results)
        elif rule.condition_logic == "NOT":
            sub_rules_met = not all(sub_rule_results)
        else:
            sub_rules_met = all(sub_rule_results)
    else:
        sub_rules_met = True

    # 最终结果：条件满足 AND 子规则满足
    overall = conditions_met and sub_rules_met

    detail: dict[str, Any] = {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "effect": rule.effect,
        "condition_logic": rule.condition_logic,
        "conditions": condition_details,
        "sub_rules": sub_rule_details,
        "conditions_met": conditions_met,
        "sub_rules_met": sub_rules_met,
        "overall": overall,
    }

    return overall, detail


def _evaluate_policy_rules(
    policy: dict[str, Any], context: dict[str, Any]
) -> tuple[bool, list[str], list[dict[str, Any]]]:
    """
    评估策略中的所有规则

    Args:
        policy: 策略数据（含 rules 列表）
        context: 上下文属性

    Returns:
        (是否允许, 匹配的规则 ID 列表, 评估详情)
    """
    rules = policy.get("rules", [])

    allow_rules_met: list[str] = []
    deny_rules_met: list[str] = []
    all_details: list[dict[str, Any]] = []

    for rule_data in rules:
        rule = PolicyRule(**rule_data)
        met, detail = _evaluate_rule(rule, context)
        all_details.append(detail)

        if met:
            if rule.effect == "allow":
                allow_rules_met.append(rule.id)
            elif rule.effect == "deny":
                deny_rules_met.append(rule.id)

    # Deny 优先
    if deny_rules_met:
        return False, deny_rules_met, all_details

    if allow_rules_met:
        return True, allow_rules_met, all_details

    return False, [], all_details


# ==================== 属性管理 ====================

async def list_attributes() -> list[dict[str, Any]]:
    """
    列出所有属性定义

    Returns:
        属性定义列表
    """
    return [attr.model_dump() for attr in BUILTIN_ATTRIBUTES]


async def get_attribute(name: str) -> Optional[dict[str, Any]]:
    """
    获取属性定义

    Args:
        name: 属性名称

    Returns:
        属性定义
    """
    for attr in BUILTIN_ATTRIBUTES:
        if attr.name == name:
            return attr.model_dump()
    return None


# ==================== 策略模板 ====================

async def list_policy_templates() -> list[dict[str, Any]]:
    """
    列出所有策略模板

    Returns:
        策略模板列表
    """
    templates: list[dict[str, Any]] = []
    for key, tpl in POLICY_TEMPLATES.items():
        templates.append({
            "template_key": key,
            "name": tpl["name"],
            "description": tpl["description"],
            "rules_count": len(tpl["rules"]),
        })
    return templates


async def get_policy_template(template_key: str) -> Optional[dict[str, Any]]:
    """
    获取策略模板详情

    Args:
        template_key: 模板键名

    Returns:
        模板详情
    """
    tpl = POLICY_TEMPLATES.get(template_key)
    if not tpl:
        return None
    return {
        "template_key": template_key,
        "name": tpl["name"],
        "description": tpl["description"],
        "rules": tpl["rules"],
    }


async def create_policy_from_template(
    db: AsyncSession,
    template_key: str,
    name: Optional[str] = None,
    priority: int = 0,
    user_id: str = "",
) -> dict[str, Any]:
    """
    从模板创建策略

    Args:
        db: 数据库会话
        template_key: 模板键名
        name: 策略名称（可选，不传则使用模板名称）
        priority: 优先级
        user_id: 创建人 ID

    Returns:
        创建的策略

    Raises:
        DataNotFoundError: 模板不存在
    """
    tpl = POLICY_TEMPLATES.get(template_key)
    if not tpl:
        raise DataNotFoundError(message=f"策略模板不存在: {template_key}")

    request = AbacPolicyCreateRequest(
        name=name or tpl["name"],
        description=tpl["description"],
        rules=tpl["rules"],
        priority=priority,
    )

    return await create_policy(db, request, user_id)


# ==================== 策略 CRUD ====================

async def list_policies(
    db: AsyncSession,
    policy_type: str = "ABAC",
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """
    列出 ABAC 策略

    Args:
        db: 数据库会话
        policy_type: 策略类型
        status: 状态过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        策略列表
    """
    query = select(SecurityPolicy).where(
        SecurityPolicy.policy_type == policy_type
    )
    if status:
        query = query.where(SecurityPolicy.status == status)

    # 计算总数
    count_q = select(func.count()).select_from(SecurityPolicy).where(
        SecurityPolicy.policy_type == policy_type
    )
    if status:
        count_q = count_q.where(SecurityPolicy.status == status)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = query.order_by(SecurityPolicy.priority.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    policies = result.scalars().all()

    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "policy_type": p.policy_type,
                "rules": p.rules,
                "priority": p.priority,
                "status": p.status,
                "created_at": str(p.created_at),
            }
            for p in policies
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def create_policy(
    db: AsyncSession,
    request: AbacPolicyCreateRequest,
    user_id: str = "",
) -> dict[str, Any]:
    """
    创建 ABAC 策略

    Args:
        db: 数据库会话
        request: 创建请求
        user_id: 创建人 ID

    Returns:
        创建的策略
    """
    # 验证规则
    for rule_data in request.rules:
        try:
            PolicyRule(**rule_data)
        except Exception as e:
            raise SecurityError(message=f"规则验证失败: {e}")

    rules_data: list[dict[str, Any]] = [r if isinstance(r, dict) else r for r in request.rules]

    policy = SecurityPolicy(
        name=request.name,
        policy_type="ABAC",
        rules={
            "rules": rules_data,
            "target": request.target.model_dump() if request.target else None,
        },
        priority=request.priority,
        status="active",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    logger.info(f"ABAC 策略创建成功: {policy.name} ({policy.id})")

    return {
        "id": str(policy.id),
        "name": policy.name,
        "policy_type": policy.policy_type,
        "rules": policy.rules,
        "priority": policy.priority,
        "status": policy.status,
        "created_at": str(policy.created_at),
    }


async def get_policy(db: AsyncSession, policy_id: str) -> dict[str, Any]:
    """
    获取策略详情

    Args:
        db: 数据库会话
        policy_id: 策略 ID

    Returns:
        策略详情
    """
    result = await db.execute(
        select(SecurityPolicy).where(SecurityPolicy.id == uuid.UUID(policy_id))
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise DataNotFoundError(message=f"策略未找到: {policy_id}")

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
    request: AbacPolicyCreateRequest,
) -> dict[str, Any]:
    """
    更新策略

    Args:
        db: 数据库会话
        policy_id: 策略 ID
        request: 更新请求

    Returns:
        更新后的策略
    """
    result = await db.execute(
        select(SecurityPolicy).where(SecurityPolicy.id == uuid.UUID(policy_id))
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise DataNotFoundError(message=f"策略未找到: {policy_id}")

    rules_data: list[dict[str, Any]] = [r if isinstance(r, dict) else r for r in request.rules]

    policy.name = request.name
    policy.rules = {
        "rules": rules_data,
        "target": request.target.model_dump() if request.target else None,
    }
    policy.priority = request.priority

    await db.commit()
    await db.refresh(policy)

    # 清除该策略的评估缓存
    _eval_cache.invalidate(policy_id)

    logger.info(f"ABAC 策略更新成功: {policy_id}")

    return {
        "id": str(policy.id),
        "name": policy.name,
        "policy_type": policy.policy_type,
        "rules": policy.rules,
        "priority": policy.priority,
        "status": policy.status,
    }


async def delete_policy(db: AsyncSession, policy_id: str) -> None:
    """
    删除策略（软删除）

    Args:
        db: 数据库会话
        policy_id: 策略 ID
    """
    result = await db.execute(
        select(SecurityPolicy).where(SecurityPolicy.id == uuid.UUID(policy_id))
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise DataNotFoundError(message=f"策略未找到: {policy_id}")

    policy.status = "deleted"
    await db.commit()

    # 清除缓存
    _eval_cache.invalidate(policy_id)

    logger.info(f"ABAC 策略已删除: {policy_id}")


# ==================== 策略评估 ====================

async def evaluate_access(
    db: AsyncSession,
    request: AbacPolicyEvaluateRequest,
) -> PolicyEvaluation:
    """
    评估访问请求

    支持 AND/OR/NOT 逻辑组合的策略评估引擎

    评估流程：
    1. 查找所有活跃的 ABAC 策略
    2. 对每个策略，先检查缓存；缓存未命中则评估其规则
    3. 支持时间条件（工作时间/时间范围）、IP 白名单/子网条件
    4. Deny 优先：任何匹配的 deny 规则都会拒绝访问
    5. 如果没有 deny，检查是否有 allow 规则匹配
    6. 返回详细评估结果

    Args:
        db: 数据库会话
        request: 评估请求

    Returns:
        评估结果
    """
    # 构建上下文
    now = datetime.now(timezone.utc)
    context: dict[str, Any] = {
        "subject.role": request.subject_attributes.get("role", "") if request.subject_attributes else "",
        "subject.department": request.subject_attributes.get("department", "") if request.subject_attributes else "",
        "subject.clearance_level": request.subject_attributes.get("clearance_level", 1) if request.subject_attributes else 1,
        "subject.did": request.subject_did,
        "resource.type": request.resource_type,
        "resource.id": request.resource_id,
        "resource.owner": request.resource_attributes.get("owner", "") if request.resource_attributes else "",
        "resource.sensitivity": request.resource_attributes.get("sensitivity", 1) if request.resource_attributes else 1,
        "action.type": request.action,
        "environment.time": now.isoformat(),
        "environment.ip": request.environment.get("ip", "") if request.environment else "",
        "environment.location": request.environment.get("location", "") if request.environment else "",
        **(request.context or {}),
    }

    # 查找所有活跃的 ABAC 策略
    query = select(SecurityPolicy).where(
        and_(
            SecurityPolicy.policy_type == "ABAC",
            SecurityPolicy.status == "active",
        )
    ).order_by(SecurityPolicy.priority.desc())

    result = await db.execute(query)
    policies = result.scalars().all()

    allowed = False
    matched_policies: list[str] = []
    all_evaluations: list[dict[str, Any]] = []
    deny_reason = ""

    for db_policy in policies:
        policy_data = db_policy.rules
        if not isinstance(policy_data, dict):
            continue

        # 检查目标匹配
        target = policy_data.get("target")
        if target:
            target_type = target.get("resource_type")
            if target_type and target_type != request.resource_type:
                continue

        # 评估规则
        rules = policy_data.get("rules", [])
        if not rules:
            continue

        # 尝试从缓存获取结果
        policy_id_str = str(db_policy.id)
        cache_key = _EvaluationCache.build_key(policy_id_str, context)
        cached = _eval_cache.get(cache_key)

        if cached is not None:
            policy_allowed, matched_rule_ids, rule_details = cached
        else:
            policy_allowed, matched_rule_ids, rule_details = _evaluate_policy_rules(
                policy_data, context
            )
            # 写入缓存
            _eval_cache.set(cache_key, (policy_allowed, matched_rule_ids, rule_details))

        all_evaluations.append({
            "policy_id": policy_id_str,
            "policy_name": db_policy.name,
            "priority": db_policy.priority,
            "allowed": policy_allowed,
            "matched_rules": matched_rule_ids,
            "rule_details": rule_details,
        })

        if matched_rule_ids:
            matched_policies.append(policy_id_str)

            if not policy_allowed:
                # Deny 优先
                allowed = False
                deny_reason = f"策略 {db_policy.name} 拒绝访问（匹配规则: {', '.join(matched_rule_ids)}）"
                break
            else:
                allowed = True

    if not allowed and not deny_reason:
        deny_reason = "无匹配策略或策略拒绝访问"

    # 检测冲突
    conflicts = detect_policy_conflicts(all_evaluations)

    return PolicyEvaluation(
        allowed=allowed,
        subject_did=request.subject_did,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        matched_policies=matched_policies,
        evaluation_details=all_evaluations,
        deny_reason=deny_reason if not allowed else None,
        conflicts=conflicts,
        evaluated_at=now.isoformat(),
    )


def detect_policy_conflicts(evaluations: list[dict[str, Any]]) -> list[PolicyConflict]:
    """
    检测策略冲突

    当同一请求同时匹配到 allow 和 deny 规则时，存在冲突。

    Args:
        evaluations: 评估详情列表

    Returns:
        冲突列表
    """
    conflicts: list[PolicyConflict] = []

    allow_policies: list[dict[str, Any]] = []
    deny_policies: list[dict[str, Any]] = []

    for evaluation in evaluations:
        if evaluation.get("matched_rules"):
            if evaluation.get("allowed"):
                allow_policies.append(evaluation)
            else:
                deny_policies.append(evaluation)

    # 如果同时有 allow 和 deny 策略匹配，存在冲突
    if allow_policies and deny_policies:
        for ap in allow_policies:
            for dp in deny_policies:
                conflicts.append(
                    PolicyConflict(
                        policy_a=ap.get("policy_name", ap.get("policy_id", "")),
                        policy_b=dp.get("policy_name", dp.get("policy_id", "")),
                        conflict_type="allow_deny",
                        description=(
                            f"策略 {ap.get('policy_name')} (allow) 与 "
                            f"策略 {dp.get('policy_name')} (deny) 存在冲突"
                        ),
                        resolution="deny 优先",
                    )
                )

    return conflicts


# ==================== 策略模拟 ====================

async def simulate_evaluation(
    db: AsyncSession,
    request: AbacPolicyEvaluateRequest,
) -> dict[str, Any]:
    """
    模拟策略评估（不影响实际授权，不使用缓存）

    Args:
        db: 数据库会话
        request: 评估请求

    Returns:
        模拟结果
    """
    # 模拟时清除缓存以获得真实评估
    _eval_cache.invalidate()

    evaluation = await evaluate_access(db, request)

    return {
        "simulation": True,
        "result": evaluation.model_dump(),
        "recommendation": (
            "访问允许" if evaluation.allowed
            else f"访问拒绝: {evaluation.deny_reason}"
        ),
    }


# ==================== 动态授权 ====================

# 临时授权存储
_temp_authorizations: dict[str, dict] = {}

# 条件授权存储
_conditional_authorizations: dict[str, dict] = {}


async def create_temporary_authorization(
    subject_did: str,
    resource_type: str,
    resource_id: str,
    action: str,
    granted_by: str,
    expires_in_seconds: int = 3600,
    reason: str = "",
) -> dict:
    """
    创建临时授权

    临时授权在指定时间后自动过期，适用于：
    - 临时数据访问授权
    - 紧急运维操作授权
    - 跨组织临时协作授权

    Args:
        subject_did: 被授权方 DID
        resource_type: 资源类型
        resource_id: 资源 ID
        action: 授权操作
        granted_by: 授权人
        expires_in_seconds: 过期时间（秒），默认 1 小时
        reason: 授权原因

    Returns:
        临时授权信息
    """
    import uuid as _uuid
    auth_id = f"temp_auth_{_uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    auth = {
        "auth_id": auth_id,
        "type": "temporary",
        "subject_did": subject_did,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        "granted_by": granted_by,
        "reason": reason,
        "status": "active",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=expires_in_seconds)).isoformat(),
        "expires_in_seconds": expires_in_seconds,
    }

    _temp_authorizations[auth_id] = auth
    logger.info(
        f"Temporary authorization created: {auth_id}, "
        f"subject={subject_did}, resource={resource_type}/{resource_id}, "
        f"expires_in={expires_in_seconds}s"
    )
    return auth


async def check_temporary_authorization(
    subject_did: str,
    resource_type: str,
    resource_id: str,
    action: str,
) -> bool:
    """
    检查临时授权是否有效

    Args:
        subject_did: 主体 DID
        resource_type: 资源类型
        resource_id: 资源 ID
        action: 操作

    Returns:
        是否有有效的临时授权
    """
    now = datetime.now(timezone.utc)

    for auth in _temp_authorizations.values():
        if auth["status"] != "active":
            continue
        if auth["subject_did"] != subject_did:
            continue
        if auth["resource_type"] != resource_type:
            continue
        if auth["resource_id"] != resource_id and auth["resource_id"] != "*":
            continue
        if auth["action"] != action and auth["action"] != "*":
            continue

        # 检查是否过期
        expires_at = datetime.fromisoformat(auth["expires_at"])
        if now > expires_at:
            auth["status"] = "expired"
            continue

        return True

    return False


async def revoke_temporary_authorization(auth_id: str) -> Optional[dict]:
    """
    撤销临时授权

    Args:
        auth_id: 授权 ID

    Returns:
        撤销后的授权信息，不存在返回 None
    """
    auth = _temp_authorizations.get(auth_id)
    if not auth:
        return None

    auth["status"] = "revoked"
    auth["revoked_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"Temporary authorization revoked: {auth_id}")
    return auth


async def list_temporary_authorizations(
    subject_did: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    """列出临时授权"""
    auths = list(_temp_authorizations.values())
    if subject_did:
        auths = [a for a in auths if a.get("subject_did") == subject_did]
    if status:
        auths = [a for a in auths if a.get("status") == status]
    return auths


async def create_conditional_authorization(
    subject_did: str,
    resource_type: str,
    resource_id: str,
    action: str,
    conditions: dict,
    granted_by: str,
    reason: str = "",
) -> dict:
    """
    创建条件授权

    条件授权在满足指定条件时才生效，支持的条件类型：
    - time_range: 时间范围限制 {start, end}
    - ip_whitelist: IP 白名单 {ips: [...]}
    - max_access_count: 最大访问次数 {count: N}
    - purpose: 使用目的限制 {purposes: [...]}
    - data_freshness: 数据新鲜度要求 {max_age_hours: N}

    Args:
        subject_did: 被授权方 DID
        resource_type: 资源类型
        resource_id: 资源 ID
        action: 授权操作
        conditions: 授权条件
        granted_by: 授权人
        reason: 授权原因

    Returns:
        条件授权信息
    """
    import uuid as _uuid
    auth_id = f"cond_auth_{_uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    auth = {
        "auth_id": auth_id,
        "type": "conditional",
        "subject_did": subject_did,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        "conditions": conditions,
        "granted_by": granted_by,
        "reason": reason,
        "status": "active",
        "access_count": 0,
        "created_at": now.isoformat(),
    }

    _conditional_authorizations[auth_id] = auth
    logger.info(
        f"Conditional authorization created: {auth_id}, "
        f"subject={subject_did}, conditions={list(conditions.keys())}"
    )
    return auth


async def check_conditional_authorization(
    subject_did: str,
    resource_type: str,
    resource_id: str,
    action: str,
    context: Optional[dict] = None,
) -> bool:
    """
    检查条件授权是否满足

    Args:
        subject_did: 主体 DID
        resource_type: 资源类型
        resource_id: 资源 ID
        action: 操作
        context: 上下文信息 {ip, timestamp, purpose, ...}

    Returns:
        条件是否满足
    """
    context = context or {}
    now = datetime.now(timezone.utc)

    for auth in _conditional_authorizations.values():
        if auth["status"] != "active":
            continue
        if auth["subject_did"] != subject_did:
            continue
        if auth["resource_type"] != resource_type:
            continue
        if auth["resource_id"] != resource_id and auth["resource_id"] != "*":
            continue
        if auth["action"] != action and auth["action"] != "*":
            continue

        conditions = auth.get("conditions", {})

        # 检查时间范围
        if "time_range" in conditions:
            tr = conditions["time_range"]
            start = datetime.fromisoformat(tr["start"]) if tr.get("start") else None
            end = datetime.fromisoformat(tr["end"]) if tr.get("end") else None
            if start and now < start:
                continue
            if end and now > end:
                auth["status"] = "expired"
                continue

        # 检查 IP 白名单
        if "ip_whitelist" in conditions:
            client_ip = context.get("ip", "")
            allowed_ips = conditions["ip_whitelist"].get("ips", [])
            if allowed_ips and client_ip not in allowed_ips:
                continue

        # 检查最大访问次数
        if "max_access_count" in conditions:
            max_count = conditions["max_access_count"].get("count", 0)
            if auth.get("access_count", 0) >= max_count:
                auth["status"] = "exhausted"
                continue

        # 检查使用目的
        if "purpose" in conditions:
            allowed_purposes = conditions["purpose"].get("purposes", [])
            request_purpose = context.get("purpose", "")
            if allowed_purposes and request_purpose not in allowed_purposes:
                continue

        # 所有条件满足，增加访问计数
        auth["access_count"] = auth.get("access_count", 0) + 1
        auth["last_accessed_at"] = now.isoformat()
        return True

    return False


async def revoke_conditional_authorization(auth_id: str) -> Optional[dict]:
    """撤销条件授权"""
    auth = _conditional_authorizations.get(auth_id)
    if not auth:
        return None

    auth["status"] = "revoked"
    auth["revoked_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"Conditional authorization revoked: {auth_id}")
    return auth


async def list_conditional_authorizations(
    subject_did: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    """列出条件授权"""
    auths = list(_conditional_authorizations.values())
    if subject_did:
        auths = [a for a in auths if a.get("subject_did") == subject_did]
    if status:
        auths = [a for a in auths if a.get("status") == status]
    return auths
