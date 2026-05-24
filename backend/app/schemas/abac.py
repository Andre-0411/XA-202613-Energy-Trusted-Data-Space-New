"""
ABAC（基于属性的访问控制）Schema
策略、属性、访问请求、策略评估

修复内容：
1. PolicyRule 增加 id, name, sub_rules 字段以支持嵌套规则评估
2. PolicyConflict 字段名对齐为 policy_a / policy_b
3. AbacPolicyCreateRequest.rules 改为 list[dict]（与 create_policy 一致）
4. AbacPolicyCreateRequest 增加 target 字段
5. AttributeDefinition 增加 display_name, validation_rules
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class AttributeDefinition(BaseModel):
    """属性定义"""
    name: str = Field(description="属性名称")
    display_name: Optional[str] = Field(default=None, description="属性显示名称")
    data_type: str = Field(description="数据类型: string/number/boolean/array/datetime")
    description: Optional[str] = Field(default=None, description="属性描述")
    category: str = Field(description="属性类别: subject/resource/environment/action")
    validation_rules: Optional[dict[str, Any]] = Field(default=None, description="校验规则（min/max/enum 等）")


class Condition(BaseModel):
    """策略条件"""
    attribute: str = Field(description="属性名")
    operator: str = Field(description="运算符: eq/ne/in/not_in/gte/lte/gt/lt/contains/starts_with/ends_with/exists/not_exists")
    value: Any = Field(default=None, description="比较值")
    logic: Optional[str] = Field(default=None, description="逻辑运算符: AND/OR/NOT（用于组合条件）")


class PolicyRule(BaseModel):
    """
    策略规则

    支持嵌套子规则以实现复杂的 AND/OR/NOT 逻辑组合。
    评估引擎会递归评估 conditions + sub_rules。
    """
    id: str = Field(default_factory=lambda: "", description="规则唯一标识")
    name: str = Field(default="", description="规则名称")
    effect: str = Field(description="效果: allow/deny")
    conditions: list[Condition] = Field(default_factory=list, description="条件列表")
    condition_logic: str = Field(default="AND", description="条件组合逻辑: AND/OR/NOT")
    allowed_actions: Optional[list[str]] = Field(default=None, description="允许的动作列表")
    resource_types: Optional[list[str]] = Field(default=None, description="适用的资源类型")
    sub_rules: list["PolicyRule"] = Field(default_factory=list, description="子规则列表（支持嵌套逻辑）")
    description: Optional[str] = Field(default=None, description="规则描述")


# 支持自引用的 Pydantic 模型
PolicyRule.model_rebuild()


class PolicyTarget(BaseModel):
    """策略目标 — 限定策略适用的资源类型、动作等"""
    resource_type: Optional[str] = Field(default=None, description="适用的资源类型")
    resource_ids: Optional[list[str]] = Field(default=None, description="适用的资源 ID 列表")
    actions: Optional[list[str]] = Field(default=None, description="适用的动作列表")


class Policy(BaseModel):
    """ABAC 策略"""
    id: Optional[str] = Field(default=None, description="策略 ID")
    name: str = Field(max_length=200, description="策略名称")
    description: Optional[str] = Field(default=None, description="策略描述")
    policy_type: str = Field(default="ABAC", description="策略类型: RBAC/ABAC/HYBRID")
    rules: list[dict] = Field(default_factory=list, description="策略规则列表（JSON 数组）")
    target: Optional[PolicyTarget] = Field(default=None, description="策略目标（限定适用范围）")
    priority: int = Field(default=0, description="优先级（越大越优先）")
    effect: str = Field(default="allow", description="默认效果: allow/deny")
    status: str = Field(default="active", description="状态: active/inactive/deleted")
    created_by: Optional[str] = Field(default=None, description="创建人")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")

    model_config = {"from_attributes": True}


class AccessRequest(BaseModel):
    """访问请求"""
    subject_did: str = Field(description="主体 DID")
    subject_attributes: Optional[dict[str, Any]] = Field(default=None, description="主体属性")
    resource_type: str = Field(description="资源类型")
    resource_id: str = Field(description="资源 ID")
    resource_attributes: Optional[dict[str, Any]] = Field(default=None, description="资源属性")
    action: str = Field(description="请求动作: read/compute/export/delete/admin")
    environment: Optional[dict[str, Any]] = Field(default=None, description="环境属性（时间、IP等）")
    context: Optional[dict[str, Any]] = Field(default=None, description="额外上下文")


class PolicyEvaluation(BaseModel):
    """策略评估结果"""
    allowed: bool = Field(description="是否允许")
    subject_did: str = Field(description="主体 DID")
    resource_type: str = Field(description="资源类型")
    resource_id: str = Field(description="资源 ID")
    action: str = Field(description="请求动作")
    matched_policies: list[str] = Field(default_factory=list, description="匹配的策略 ID 列表")
    deny_reason: Optional[str] = Field(default=None, description="拒绝原因")
    evaluation_details: Optional[list[dict[str, Any]]] = Field(default=None, description="评估详情")
    conflicts: Optional[list["PolicyConflict"]] = Field(default=None, description="策略冲突列表")
    evaluated_at: Optional[str] = Field(default=None, description="评估时间")


class PolicyConflict(BaseModel):
    """策略冲突"""
    policy_a: str = Field(description="策略 A 标识")
    policy_b: str = Field(description="策略 B 标识")
    conflict_type: str = Field(description="冲突类型: allow_deny/priority_overlap/scope_overlap")
    description: str = Field(description="冲突描述")
    resolution: Optional[str] = Field(default=None, description="解决建议")


class AbacPolicyCreateRequest(BaseModel):
    """创建 ABAC 策略请求"""
    name: str = Field(max_length=200, description="策略名称")
    description: Optional[str] = Field(default=None, description="策略描述")
    policy_type: str = Field(default="ABAC", description="策略类型: RBAC/ABAC/HYBRID")
    rules: list[dict] = Field(description="策略规则列表（JSON 数组）")
    target: Optional[PolicyTarget] = Field(default=None, description="策略目标（限定适用范围）")
    priority: int = Field(default=0, description="优先级")
    effect: str = Field(default="allow", description="默认效果")
    attributes: Optional[list[AttributeDefinition]] = Field(default=None, description="属性定义列表")


class AbacPolicyEvaluateRequest(BaseModel):
    """ABAC 策略评估请求"""
    subject_did: str = Field(description="主体 DID")
    subject_attributes: Optional[dict[str, Any]] = Field(default=None, description="主体属性")
    resource_type: str = Field(description="资源类型")
    resource_id: str = Field(description="资源 ID")
    resource_attributes: Optional[dict[str, Any]] = Field(default=None, description="资源属性")
    action: str = Field(description="请求动作")
    environment: Optional[dict[str, Any]] = Field(default=None, description="环境属性")
    context: Optional[dict[str, Any]] = Field(default=None, description="额外上下文")


# 支持延迟引用
PolicyEvaluation.model_rebuild()
