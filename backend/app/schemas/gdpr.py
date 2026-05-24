"""
GDPR / 数据安全法合规 Schema
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class DataSubjectRequestCreate(BaseModel):
    """创建数据主体请求"""
    request_type: str = Field(
        description="请求类型: access/erasure/portability/rectification/restrict_processing"
    )
    subject_user_id: Optional[str] = Field(default=None, description="平台内用户 ID")
    subject_email: Optional[str] = Field(default=None, description="请求者邮箱")
    subject_name: Optional[str] = Field(default=None, description="请求者姓名")
    organization_id: Optional[str] = Field(default=None, description="关联组织 ID")
    description: Optional[str] = Field(default=None, description="请求描述")
    priority: str = Field(default="normal", description="优先级: low/normal/high/urgent")


class DataSubjectRequestUpdate(BaseModel):
    """更新数据主体请求"""
    status: Optional[str] = Field(default=None, description="状态")
    assigned_to: Optional[str] = Field(default=None, description="处理人 ID")
    rejection_reason: Optional[str] = Field(default=None, description="拒绝原因")
    response_data: Optional[dict] = Field(default=None, description="响应数据")


class DataSubjectRequestResponse(BaseModel):
    """数据主体请求响应"""
    id: str
    request_type: str
    subject_user_id: Optional[str] = None
    subject_email: Optional[str] = None
    subject_name: Optional[str] = None
    organization_id: Optional[str] = None
    description: Optional[str] = None
    status: str
    priority: str
    assigned_to: Optional[str] = None
    response_data: Optional[dict] = None
    rejection_reason: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DataExportRequest(BaseModel):
    """数据导出请求"""
    user_id: str = Field(description="要导出数据的用户 ID")
    format: str = Field(default="json", description="导出格式: json/csv")


class DataExportResponse(BaseModel):
    """数据导出响应"""
    user_id: str
    format: str
    data: dict = Field(description="导出的数据")
    exported_at: datetime


class DataDeletionRequest(BaseModel):
    """数据删除请求"""
    user_id: str = Field(description="要删除数据的用户 ID")
    confirm: bool = Field(description="确认删除")
    retain_anonymized: bool = Field(default=True, description="是否保留匿名化数据用于统计")


class DataDeletionResponse(BaseModel):
    """数据删除响应"""
    user_id: str
    records_deleted: dict = Field(description="各表删除记录数")
    anonymized: bool
    processed_at: datetime
