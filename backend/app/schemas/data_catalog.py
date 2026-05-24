"""
数据目录 Schema
数据分类、敏感级别、目录条目、搜索结果等
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class DataClassification(BaseModel):
    """数据分类信息"""
    category: str = Field(description="数据大类: 发电/用电/调度/市场/设备状态/地理信息")
    subcategory: Optional[str] = Field(default=None, description="数据子类")
    classification_level: int = Field(default=4, ge=1, le=4, description="敏感级别: 1核心/2重要/3敏感/4公开")
    sensitivity_label: str = Field(default="公开", description="敏感级别标签")
    sm3_hash: Optional[str] = Field(default=None, description="SM3 哈希指纹")
    classification_reason: Optional[str] = Field(default=None, description="分类原因")
    classified_at: Optional[str] = Field(default=None, description="分类时间")
    classified_by: Optional[str] = Field(default=None, description="分类人")


class CatalogItem(BaseModel):
    """目录条目"""
    id: str = Field(description="条目 ID")
    name: str = Field(description="数据名称")
    description: Optional[str] = Field(default=None, description="数据描述")
    category: str = Field(description="数据大类")
    subcategory: Optional[str] = Field(default=None, description="数据子类")
    classification_level: int = Field(default=4, description="敏感级别")
    sensitivity_label: str = Field(default="公开", description="敏感级别标签")
    owner_name: Optional[str] = Field(default=None, description="所有者名称")
    organization_name: Optional[str] = Field(default=None, description="所属组织")
    record_count: int = Field(default=0, description="记录数")
    size_bytes: int = Field(default=0, description="数据大小(字节)")
    storage_format: str = Field(default="parquet", description="存储格式")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    avg_rating: float = Field(default=0.0, description="平均评分")
    rating_count: int = Field(default=0, description="评价数")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")
    status: str = Field(default="published", description="状态")


class CatalogSearchParams(BaseModel):
    """目录搜索参数"""
    keyword: Optional[str] = Field(default=None, description="搜索关键词")
    category: Optional[str] = Field(default=None, description="数据大类筛选")
    classification_level: Optional[int] = Field(default=None, ge=1, le=4, description="敏感级别筛选")
    min_level: Optional[int] = Field(default=None, ge=1, le=4, description="最低敏感级别")
    max_level: Optional[int] = Field(default=None, ge=1, le=4, description="最高敏感级别")
    organization_id: Optional[str] = Field(default=None, description="组织 ID 筛选")
    tags: Optional[list[str]] = Field(default=None, description="标签筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")


class CatalogApplyRequest(BaseModel):
    """目录申请请求"""
    asset_id: str = Field(description="资产 ID")
    purpose: str = Field(description="使用目的")
    duration_days: int = Field(default=30, ge=1, le=365, description="申请使用天数")
    data_scope: Optional[str] = Field(default=None, description="数据范围说明")


class CatalogFeedbackRequest(BaseModel):
    """目录评价请求"""
    asset_id: str = Field(description="资产 ID")
    rating: int = Field(ge=1, le=5, description="评分 1-5")
    comment: str = Field(default="", description="评价内容")


class DataPreview(BaseModel):
    """数据预览"""
    asset_id: str = Field(description="资产 ID")
    total_records: int = Field(default=0, description="总记录数")
    preview_records: list[dict] = Field(default_factory=list, description="预览记录")
    fields: list[dict] = Field(default_factory=list, description="字段信息")
    masked: bool = Field(default=True, description="是否已脱敏")


class ClassificationRule(BaseModel):
    """分类规则"""
    rule_id: str = Field(description="规则 ID")
    name: str = Field(description="规则名称")
    description: Optional[str] = Field(default=None, description="规则描述")
    category: str = Field(description="适用大类")
    keywords: list[str] = Field(default_factory=list, description="关键词列表")
    sensitivity_level: int = Field(default=4, description="敏感级别")
    auto_classify: bool = Field(default=True, description="是否自动分类")
    priority: int = Field(default=0, description="优先级")
