"""
账单明细 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class BillResponse(BaseModel):
    """账单响应"""
    id: str = Field(description="账单 ID")
    bill_no: str = Field(description="账单编号")
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    billing_period: str = Field(description="账期 YYYY-MM")
    total_amount: float = Field(description="总金额")
    paid_amount: float = Field(default=0.0, description="已付金额")
    pending_amount: float = Field(default=0.0, description="待付金额")
    item_count: int = Field(default=0, description="明细条数")
    status: str = Field(description="账单状态: draft/issued/paid/overdue")
    generated_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillDetailResponse(BaseModel):
    """账单明细响应"""
    id: str
    bill_id: str
    service_name: str = Field(description="服务名称")
    service_category: str = Field(default="", description="服务分类")
    usage_quantity: float = Field(default=0.0, description="使用量")
    unit_price: float = Field(default=0.0, description="单价")
    amount: float = Field(description="金额")
    billing_period: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BillGenerateRequest(BaseModel):
    """生成月度账单请求"""
    billing_period: str = Field(description="账期 YYYY-MM")
    organization_id: Optional[str] = Field(default=None, description="指定组织 ID（可选，默认为全部）")


class BillGenerateResponse(BaseModel):
    """生成账单响应"""
    billing_period: str
    bills_generated: int = Field(description="生成账单数")
    total_amount: float = Field(description="总金额")
    generated_at: datetime


class BillStatisticsResponse(BaseModel):
    """账单统计响应"""
    total_revenue: float = Field(default=0.0, description="总收入")
    total_bills: int = Field(default=0, description="账单总数")
    paid_bills: int = Field(default=0, description="已付账单数")
    unpaid_bills: int = Field(default=0, description="未付账单数")
    by_service_type: dict = Field(default_factory=dict, description="按服务类型统计")
    by_period: dict = Field(default_factory=dict, description="按时间区间统计")
    generated_at: datetime


class BillDownloadResponse(BaseModel):
    """账单下载响应"""
    bill_id: str
    bill_no: str
    format: str = Field(description="下载格式: csv/json")
    filename: str = Field(description="文件名")
    content: str = Field(description="文件内容（Base64 编码）")
    item_count: int = Field(description="明细条数")
