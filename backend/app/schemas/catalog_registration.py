"""
数据目录登记 Schema
CatalogRegistration / ControlTemplate / AccessScopeRule
"""
from typing import Optional, Any, List
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 数据目录登记 ====================

class CatalogRegistrationCreate(BaseModel):
    """创建数据目录登记"""
    catalog_type: str = Field(description="目录类型: api/file/database/service/model")
    name: str = Field(description="目录名称")
    description: Optional[str] = Field(default=None, description="目录描述")
    security_level: str = Field(description="安全等级: public/internal/confidential/secret")
    visibility: str = Field(default="public", description="可见性: public/restricted/private")
    supply_channels: list = Field(default_factory=list, description="供给通道列表")
    control_protocol: dict = Field(default_factory=dict, description="管控协议")
    compliance_docs: list = Field(default_factory=list, description="合规文档")
    api_config: dict = Field(default_factory=dict, description="API 配置")
    tags: list = Field(default_factory=list, description="标签列表")


class CatalogRegistrationUpdate(BaseModel):
    """更新数据目录登记"""
    name: Optional[str] = Field(default=None, description="名称")
    description: Optional[str] = Field(default=None, description="描述")
    security_level: Optional[str] = Field(default=None, description="安全等级")
    visibility: Optional[str] = Field(default=None, description="可见性")
    control_protocol: Optional[dict] = Field(default=None, description="管控协议")
    compliance_docs: Optional[list] = Field(default=None, description="合规文档")
    api_config: Optional[dict] = Field(default=None, description="API 配置")
    tags: Optional[list] = Field(default=None, description="标签列表")


class CatalogRegistrationResponse(BaseModel):
    """数据目录登记响应"""
    id: str = Field(description="目录登记 ID")
    catalog_type: str = Field(description="目录类型")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    security_level: str = Field(description="安全等级")
    visibility: str = Field(description="可见性")
    supply_channels: list = Field(default_factory=list)
    control_protocol: dict = Field(default_factory=dict)
    compliance_docs: list = Field(default_factory=list)
    api_config: dict = Field(default_factory=dict)
    tags: list = Field(default_factory=list)
    organization_id: str = Field(description="所属组织 ID")
    owner_id: str = Field(description="负责人 ID")
    status: str = Field(description="状态")
    published_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 管控模板 ====================

class ControlTemplateCreate(BaseModel):
    """创建管控模板"""
    name: str = Field(description="模板名称")
    template_type: str = Field(description="模板类型: access_control/usage_limit/retention/encryption")
    rules: dict = Field(default_factory=dict, description="规则配置")
    description: Optional[str] = Field(default=None, description="描述")


class ControlTemplateUpdate(BaseModel):
    """更新管控模板"""
    name: Optional[str] = Field(default=None, description="模板名称")
    template_type: Optional[str] = Field(default=None, description="模板类型")
    rules: Optional[dict] = Field(default=None, description="规则配置")
    description: Optional[str] = Field(default=None, description="描述")
    status: Optional[str] = Field(default=None, description="状态")


class ControlTemplateResponse(BaseModel):
    """管控模板响应"""
    id: str = Field(description="模板 ID")
    catalog_id: str = Field(description="所属目录 ID")
    name: str = Field(description="名称")
    template_type: str = Field(description="模板类型")
    rules: dict = Field(default_factory=dict)
    description: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 访问范围规则 ====================

class AccessScopeRuleCreate(BaseModel):
    """创建访问范围规则"""
    rule_type: str = Field(description="规则类型: whitelist/blacklist/conditional")
    target_id: str = Field(description="目标 ID（组织/用户/角色）")
    permissions: dict = Field(default_factory=dict, description="权限配置")
    conditions: dict = Field(default_factory=dict, description="条件配置")


class AccessScopeRuleResponse(BaseModel):
    """访问范围规则响应"""
    id: str = Field(description="规则 ID")
    catalog_id: str = Field(description="所属目录 ID")
    rule_type: str = Field(description="规则类型")
    target_id: str = Field(description="目标 ID")
    permissions: dict = Field(default_factory=dict)
    conditions: dict = Field(default_factory=dict)
    created_at: str = Field(description="创建时间")


# ==================== 供给渠道 / 管控协议 / 开放范围 / 合规文档 / 审批 ====================

class SupplyChannelConfig(BaseModel):
    """供给渠道配置"""
    channels: List[dict] = Field(default_factory=list, description="供给渠道列表")


class ControlProtocolConfig(BaseModel):
    """管控协议配置"""
    protocol_type: str = Field(default="default", description="协议类型")
    rules: dict = Field(default_factory=dict, description="协议规则")
    description: Optional[str] = Field(default=None, description="协议描述")


class AccessScopeConfig(BaseModel):
    """开放范围配置"""
    scope_type: str = Field(description="范围类型: public/whitelist/blacklist")
    allowed_orgs: List[str] = Field(default_factory=list, description="允许的组织列表")
    denied_orgs: List[str] = Field(default_factory=list, description="拒绝的组织列表")
    conditions: dict = Field(default_factory=dict, description="附加条件")


class ComplianceDocUpload(BaseModel):
    """合规文档上传"""
    docs: List[dict] = Field(default_factory=list, description="合规文档列表")


class CatalogReview(BaseModel):
    """目录审批"""
    action: str = Field(description="审批动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审批意见")
