"""
数据产品 Schema
ProductProject / DataProduct / ProductAcceptance / ProductPublishRequest
ProductUnpublishRequest / ProductSubscription / ProductDelivery
"""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 产品项目 ====================

class ProductProjectCreate(BaseModel):
    """创建产品项目"""
    name: str = Field(description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    project_type: str = Field(description="项目类型: standard/custom/collaborative")
    data_sources: list = Field(default_factory=list, description="数据源列表")


class ProductProjectUpdate(BaseModel):
    """更新产品项目"""
    name: Optional[str] = Field(default=None, description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    project_type: Optional[str] = Field(default=None, description="项目类型")
    data_sources: Optional[list] = Field(default=None, description="数据源列表")
    status: Optional[str] = Field(default=None, description="状态")


class ProjectMemberCreate(BaseModel):
    """添加项目成员"""
    user_id: str = Field(description="用户 ID")
    role: str = Field(default="member", description="角色: owner/admin/developer/tester/member")


# 别名: ProjectMemberAdd 与 ProjectMemberCreate 语义一致
ProjectMemberAdd = ProjectMemberCreate


class DataSourceConfig(BaseModel):
    """项目数据源配置"""
    data_sources: list = Field(default_factory=list, description="数据源列表")
    config: dict = Field(default_factory=dict, description="配置参数")


class ProjectMemberResponse(BaseModel):
    """项目成员响应"""
    id: str = Field(description="成员 ID")
    project_id: str = Field(description="项目 ID")
    user_id: str = Field(description="用户 ID")
    role: str = Field(description="角色")
    joined_at: str = Field(description="加入时间")


class ProductProjectResponse(BaseModel):
    """产品项目响应"""
    id: str = Field(description="项目 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    project_type: str = Field(description="项目类型")
    organization_id: str = Field(description="所属组织 ID")
    owner_id: str = Field(description="负责人 ID")
    data_sources: list = Field(default_factory=list)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    members: List[ProjectMemberResponse] = Field(default_factory=list)


# ==================== 数据产品 ====================

class DataProductCreate(BaseModel):
    """创建数据产品"""
    project_id: Optional[str] = Field(default=None, description="关联项目 ID")
    name: str = Field(description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    product_type: str = Field(description="产品类型: analytics/report/model/api/dataset")
    compute_engine: Optional[str] = Field(default=None, description="计算引擎")
    version: str = Field(default="1.0.0", description="版本号")
    technical_spec: dict = Field(default_factory=dict, description="技术规格")
    pricing: dict = Field(default_factory=dict, description="定价信息")
    delivery_config: dict = Field(default_factory=dict, description="交付配置")
    compliance_docs: list = Field(default_factory=list, description="合规文档")
    control_protocol: dict = Field(default_factory=dict, description="管控协议")


class DataProductUpdate(BaseModel):
    """更新数据产品"""
    name: Optional[str] = Field(default=None, description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    product_type: Optional[str] = Field(default=None, description="产品类型")
    compute_engine: Optional[str] = Field(default=None, description="计算引擎")
    version: Optional[str] = Field(default=None, description="版本号")
    technical_spec: Optional[dict] = Field(default=None, description="技术规格")
    pricing: Optional[dict] = Field(default=None, description="定价信息")
    delivery_config: Optional[dict] = Field(default=None, description="交付配置")
    compliance_docs: Optional[list] = Field(default=None, description="合规文档")
    control_protocol: Optional[dict] = Field(default=None, description="管控协议")
    status: Optional[str] = Field(default=None, description="状态")


class ComputeEngineConfig(BaseModel):
    """计算引擎配置"""
    engine_type: str = Field(description="引擎类型: sql/python/spark/flink/custom")
    engine_config: dict = Field(default_factory=dict, description="引擎参数")
    resource_limits: dict = Field(default_factory=dict, description="资源限制")


class DataProductResponse(BaseModel):
    """数据产品响应"""
    id: str = Field(description="产品 ID")
    project_id: Optional[str] = Field(default=None)
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    product_type: str = Field(description="产品类型")
    compute_engine: Optional[str] = Field(default=None)
    version: str = Field(description="版本号")
    organization_id: str = Field(description="所属组织 ID")
    owner_id: str = Field(description="负责人 ID")
    technical_spec: dict = Field(default_factory=dict)
    pricing: dict = Field(default_factory=dict)
    delivery_config: dict = Field(default_factory=dict)
    compliance_docs: list = Field(default_factory=list)
    control_protocol: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    published_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 产品验收 ====================

class ProductAcceptanceCreate(BaseModel):
    """创建产品验收"""
    product_id: str = Field(description="产品 ID")
    acceptor_id: str = Field(description="验收人 ID")
    test_result: dict = Field(default_factory=dict, description="测试结果")
    status: Optional[str] = Field(default=None, description="验收状态")
    comment: Optional[str] = Field(default=None, description="验收意见")


# 别名: ProductAcceptance 与 ProductAcceptanceCreate 语义一致
ProductAcceptance = ProductAcceptanceCreate


class ProductAcceptanceResponse(BaseModel):
    """产品验收响应"""
    id: str = Field(description="验收 ID")
    product_id: str = Field(description="产品 ID")
    acceptor_id: str = Field(description="验收人 ID")
    test_result: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    comment: Optional[str] = Field(default=None)
    accepted_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")


# ==================== 产品上下架 ====================

class ProductPublishCreate(BaseModel):
    """创建产品上架申请"""
    product_id: str = Field(description="产品 ID")
    review_deadline: Optional[str] = Field(default=None, description="审核截止时间")
    control_protocol: dict = Field(default_factory=dict, description="管控协议")
    compliance_docs: list = Field(default_factory=list, description="合规文档")
    pricing_config: dict = Field(default_factory=dict, description="定价配置")


# 别名: ProductPublishRequest 与 ProductPublishCreate 语义一致
ProductPublishRequest = ProductPublishCreate


class ProductPublishReview(BaseModel):
    """审核产品上架"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")
    status: Optional[str] = Field(default=None, description="审核结果: approved/rejected（兼容字段）")
    review_comment: Optional[str] = Field(default=None, description="审核意见（兼容字段）")


class ProductPublishRequestResponse(BaseModel):
    """产品上架申请响应"""
    id: str = Field(description="申请 ID")
    product_id: str = Field(description="产品 ID")
    applicant_id: str = Field(description="申请人 ID")
    organization_id: str = Field(description="组织 ID")
    review_deadline: Optional[str] = Field(default=None)
    control_protocol: dict = Field(default_factory=dict)
    compliance_docs: list = Field(default_factory=list)
    pricing_config: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    published_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# 别名: ProductPublishResponse 与 ProductPublishRequestResponse 语义一致
ProductPublishResponse = ProductPublishRequestResponse


class UnpublishRequest(BaseModel):
    """产品下架申请"""
    product_id: str = Field(description="产品 ID")
    reason: Optional[str] = Field(default=None, description="下架理由")


class UnpublishReview(BaseModel):
    """审核产品下架"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")


class ProductUnpublishCreate(BaseModel):
    """创建产品下架申请"""
    product_id: str = Field(description="产品 ID")
    reason: Optional[str] = Field(default=None, description="下架理由")


class ProductUnpublishResponse(BaseModel):
    """产品下架申请响应"""
    id: str = Field(description="申请 ID")
    product_id: str = Field(description="产品 ID")
    applicant_id: str = Field(description="申请人 ID")
    reason: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    reviewer_id: Optional[str] = Field(default=None)
    review_comment: Optional[str] = Field(default=None)
    reviewed_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")


class ProductMarketItem(BaseModel):
    """产品市场列表项"""
    id: str = Field(description="产品 ID")
    name: str = Field(description="产品名称")
    description: Optional[str] = Field(default=None, description="产品描述")
    product_type: str = Field(description="产品类型")
    organization_id: str = Field(description="所属组织 ID")
    organization_name: Optional[str] = Field(default=None, description="组织名称")
    pricing: dict = Field(default_factory=dict, description="定价信息")
    rating: float = Field(default=0.0, description="评分")
    subscriber_count: int = Field(default=0, description="订阅数")
    published_at: Optional[str] = Field(default=None, description="上架时间")
    tags: list = Field(default_factory=list, description="标签")


class ContractFiling(BaseModel):
    """合约备案"""
    contract_id: str = Field(description="合约 ID")


class ProductDeliveryInfo(BaseModel):
    """产品交付信息"""
    subscription_id: str = Field(description="订阅 ID")
    delivery_type: str = Field(description="交付类型")
    delivery_config: dict = Field(default_factory=dict, description="交付配置")
    access_token: Optional[str] = Field(default=None, description="访问令牌")
    access_url: Optional[str] = Field(default=None, description="访问 URL")
    status: str = Field(default="pending", description="交付状态")
    last_delivered_at: Optional[str] = Field(default=None, description="最后交付时间")


class ControlProtocolConfig(BaseModel):
    """管控协议配置"""
    protocol_type: str = Field(default="default", description="协议类型")
    rules: dict = Field(default_factory=dict, description="协议规则")
    description: Optional[str] = Field(default=None, description="协议描述")


class ComplianceDocUpload(BaseModel):
    """合规材料上传"""
    docs: List[dict] = Field(default_factory=list, description="合规文档列表")


# ==================== 产品订阅 ====================

class ProductSubscriptionCreate(BaseModel):
    """创建产品订阅"""
    product_id: str = Field(description="产品 ID")
    reason: Optional[str] = Field(default=None, description="订阅理由")
    subscription_config: dict = Field(default_factory=dict, description="订阅配置")
    delivery_config: dict = Field(default_factory=dict, description="交付配置")


class ProductSubscriptionReview(BaseModel):
    """审核产品订阅"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")
    status: Optional[str] = Field(default=None, description="审核结果（兼容字段）")
    expires_at: Optional[str] = Field(default=None, description="过期时间")


class ProductSubscriptionResponse(BaseModel):
    """产品订阅响应"""
    id: str = Field(description="订阅 ID")
    product_id: str = Field(description="产品 ID")
    subscriber_id: str = Field(description="订阅者 ID")
    subscriber_org_id: str = Field(description="订阅者组织 ID")
    reason: Optional[str] = Field(default=None)
    contract_id: Optional[str] = Field(default=None)
    subscription_config: dict = Field(default_factory=dict)
    delivery_config: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[str] = Field(default=None)
    expires_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    deliveries: List["ProductDeliveryResponse"] = Field(default_factory=list)


# ==================== 产品交付 ====================

class ProductDeliveryCreate(BaseModel):
    """创建产品交付"""
    subscription_id: str = Field(description="订阅 ID")
    delivery_type: str = Field(description="交付类型: api_download/file_download/streaming/database_query")
    delivery_config: dict = Field(default_factory=dict, description="交付配置")


class ProductDeliveryResponse(BaseModel):
    """产品交付响应"""
    id: str = Field(description="交付 ID")
    subscription_id: str = Field(description="订阅 ID")
    delivery_type: str = Field(description="交付类型")
    delivery_config: dict = Field(default_factory=dict)
    access_token: Optional[str] = Field(default=None)
    access_url: Optional[str] = Field(default=None)
    download_count: int = Field(default=0)
    last_accessed_at: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


# 重建引用
ProductSubscriptionResponse.model_rebuild()
