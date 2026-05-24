"""
运营服务 Schema
"""
from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    """创建服务"""
    name: str = Field(max_length=200, description="服务名称")
    category: str = Field(max_length=50, description="分类")
    parent_id: Optional[str] = Field(default=None, description="父级服务 ID")
    level: int = Field(ge=1, le=3, description="层级")
    description: Optional[str] = Field(default=None, description="描述")
    pricing_model: str = Field(description="计费模式: fixed/usage/tiered")
    pricing_config: dict = Field(description="计费配置")
    quota_limit: Optional[int] = Field(default=None, description="配额限制")


class ServiceResponse(BaseModel):
    """服务响应"""
    id: str
    name: str
    category: str
    parent_id: Optional[str] = None
    level: int
    description: Optional[str] = None
    pricing_model: str
    pricing_config: dict
    quota_limit: Optional[int] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionCreate(BaseModel):
    """订阅服务请求"""
    service_id: str = Field(description="服务 ID")
    start_date: date = Field(description="开始日期")
    end_date: Optional[date] = Field(default=None, description="结束日期")


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    id: str
    user_id: str
    service_id: str
    status: str
    start_date: date
    end_date: Optional[date] = None
    quota_used: int = 0
    approval_status: str
    approved_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingRecordResponse(BaseModel):
    """计费记录响应"""
    id: str
    subscription_id: str
    amount: float
    billing_period: str
    usage_detail: Optional[dict] = None
    payment_status: str
    tx_hash: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
