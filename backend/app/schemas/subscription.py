"""
数据资源订阅 Schema
DataSubscription / DataDelivery
"""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 数据订阅 ====================

class DataSubscriptionCreate(BaseModel):
    """创建数据资源订阅申请"""
    catalog_id: str = Field(description="数据目录 ID")
    reason: Optional[str] = Field(default=None, description="订阅理由")
    subscription_config: dict = Field(default_factory=dict, description="订阅配置")


class DataSubscriptionUpdate(BaseModel):
    """更新数据订阅"""
    reason: Optional[str] = Field(default=None, description="订阅理由")
    subscription_config: Optional[dict] = Field(default=None, description="订阅配置")
    status: Optional[str] = Field(default=None, description="状态")


class DataSubscriptionReview(BaseModel):
    """审核订阅申请"""
    action: str = Field(description="审核动作: approve/reject")
    comment: Optional[str] = Field(default=None, description="审核意见")
    contract_id: Optional[str] = Field(default=None, description="关联合约 ID")
    subscription_config: Optional[dict] = Field(default=None, description="订阅配置")
    status: Optional[str] = Field(default=None, description="审核结果（兼容字段）")
    expires_at: Optional[str] = Field(default=None, description="过期时间")


class DataSubscriptionResponse(BaseModel):
    """数据订阅响应"""
    id: str = Field(description="订阅 ID")
    catalog_id: str = Field(description="数据目录 ID")
    subscriber_id: str = Field(description="订阅者 ID")
    subscriber_org_id: str = Field(description="订阅者组织 ID")
    reason: Optional[str] = Field(default=None)
    contract_id: Optional[str] = Field(default=None)
    subscription_config: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    approved_by: Optional[str] = Field(default=None)
    approved_at: Optional[str] = Field(default=None)
    expires_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    deliveries: List["DataDeliveryResponse"] = Field(default_factory=list)


# ==================== 数据交付 ====================

class DataDeliveryCreate(BaseModel):
    """创建数据交付"""
    subscription_id: str = Field(description="订阅 ID")
    delivery_type: str = Field(description="交付类型: api_download/file_download/streaming/database_query")
    delivery_config: dict = Field(default_factory=dict, description="交付配置")


class DataDeliveryResponse(BaseModel):
    """数据交付响应"""
    id: str = Field(description="交付 ID")
    subscription_id: str = Field(description="订阅 ID")
    delivery_type: str = Field(description="交付类型")
    delivery_config: dict = Field(default_factory=dict)
    access_token: Optional[str] = Field(default=None)
    file_path: Optional[str] = Field(default=None)
    download_count: int = Field(default=0)
    last_accessed_at: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


# 别名: DeliveryInfo 用于交付信息查询端点
DeliveryInfo = DataDeliveryResponse


# 重建引用
DataSubscriptionResponse.model_rebuild()
