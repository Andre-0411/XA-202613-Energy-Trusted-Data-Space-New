"""
数据搜索 Schema
全文搜索、多维筛选、搜索结果等
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """搜索请求"""
    keyword: str = Field(default="", description="搜索关键词")
    category: Optional[str] = Field(default=None, description="数据大类筛选")
    classification_level: Optional[int] = Field(default=None, ge=1, le=4, description="敏感级别筛选")
    min_level: Optional[int] = Field(default=None, ge=1, le=4, description="最低敏感级别")
    max_level: Optional[int] = Field(default=None, ge=1, le=4, description="最高敏感级别")
    organization_id: Optional[str] = Field(default=None, description="组织 ID 筛选")
    tags: Optional[list[str]] = Field(default=None, description="标签筛选")
    status: Optional[str] = Field(default=None, description="状态筛选")
    date_from: Optional[str] = Field(default=None, description="开始日期")
    date_to: Optional[str] = Field(default=None, description="结束日期")
    sort_by: str = Field(default="relevance", description="排序方式: relevance/date/rating/size")
    sort_order: str = Field(default="desc", description="排序方向: asc/desc")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")


class SearchResultItem(BaseModel):
    """搜索结果条目"""
    id: str = Field(description="条目 ID")
    name: str = Field(description="数据名称")
    description: Optional[str] = Field(default=None, description="数据描述")
    category: str = Field(description="数据大类")
    classification_level: int = Field(default=4, description="敏感级别")
    sensitivity_label: str = Field(default="公开", description="敏感级别标签")
    organization_name: Optional[str] = Field(default=None, description="所属组织")
    record_count: int = Field(default=0, description="记录数")
    size_bytes: int = Field(default=0, description="数据大小")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    relevance_score: float = Field(default=0.0, description="相关性得分")
    highlight: Optional[str] = Field(default=None, description="高亮摘要")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")
    status: str = Field(default="published", description="状态")


class SearchResponse(BaseModel):
    """搜索响应"""
    total: int = Field(default=0, description="总结果数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页大小")
    total_pages: int = Field(default=0, description="总页数")
    items: list[SearchResultItem] = Field(default_factory=list, description="搜索结果")
    facets: dict = Field(default_factory=dict, description="分面统计")
    query_time_ms: float = Field(default=0.0, description="查询耗时(ms)")


class SearchSuggestion(BaseModel):
    """搜索建议"""
    keyword: str = Field(description="建议关键词")
    category: Optional[str] = Field(default=None, description="所属类别")
    count: int = Field(default=0, description="匹配数量")


class SearchFacets(BaseModel):
    """搜索分面"""
    categories: dict = Field(default_factory=dict, description="按类别统计")
    classification_levels: dict = Field(default_factory=dict, description="按敏感级别统计")
    organizations: dict = Field(default_factory=dict, description="按组织统计")
    tags: dict = Field(default_factory=dict, description="按标签统计")


class DataLineageNode(BaseModel):
    """数据血缘节点"""
    id: str = Field(description="节点 ID")
    name: str = Field(description="节点名称")
    type: str = Field(description="节点类型: datasource/asset/task")
    metadata: Optional[dict] = Field(default=None, description="节点元数据")


class DataLineageEdge(BaseModel):
    """数据血缘边"""
    source: str = Field(description="源节点 ID")
    target: str = Field(description="目标节点 ID")
    label: Optional[str] = Field(default=None, description="边标签")
    metadata: Optional[dict] = Field(default=None, description="边元数据")


class DataLineageGraph(BaseModel):
    """数据血缘图"""
    nodes: list[DataLineageNode] = Field(default_factory=list, description="节点列表")
    edges: list[DataLineageEdge] = Field(default_factory=list, description="边列表")
    center_node_id: Optional[str] = Field(default=None, description="中心节点 ID")
