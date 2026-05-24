"""
统一门户 Schema
门户仪表盘、快速入口、数据概览
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class PortalDashboardRequest(BaseModel):
    """门户仪表盘请求"""
    user_id: str = Field(description="用户 ID")
    role: Optional[str] = Field(default=None, description="用户角色")
    time_range: str = Field(default="7d", description="时间范围: 1d/7d/30d/90d")


class PortalDashboardResponse(BaseModel):
    """门户仪表盘响应"""
    user_id: str = Field(description="用户 ID")
    role: str = Field(description="用户角色")
    data_assets_count: int = Field(default=0, description="数据资产数量")
    compute_tasks_count: int = Field(default=0, description="计算任务数量")
    active_alerts_count: int = Field(default=0, description="活跃告警数量")
    blockchain_transactions: int = Field(default=0, description="区块链交易数")
    recent_activities: List[Dict[str, Any]] = Field(default_factory=list, description="最近活动")
    quick_links: List[Dict[str, str]] = Field(default_factory=list, description="快速链接")
    system_status: str = Field(default="healthy", description="系统状态")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="最后更新时间")


class QuickLinkItem(BaseModel):
    """快速链接项"""
    id: str = Field(description="链接 ID")
    title: str = Field(description="标题")
    icon: str = Field(description="图标")
    url: str = Field(description="URL")
    description: Optional[str] = Field(default=None, description="描述")
    category: str = Field(default="general", description="分类")
    order: int = Field(default=0, description="排序")


class DataOverviewItem(BaseModel):
    """数据概览项"""
    metric_name: str = Field(description="指标名称")
    metric_value: float = Field(description="指标值")
    unit: str = Field(default="", description="单位")
    change_percent: Optional[float] = Field(default=None, description="变化百分比")
    trend: Optional[str] = Field(default=None, description="趋势: up/down/stable")


class PortalNotification(BaseModel):
    """门户通知"""
    id: str = Field(description="通知 ID")
    title: str = Field(description="标题")
    content: str = Field(description="内容")
    type: str = Field(default="info", description="类型: info/warning/error/success")
    read: bool = Field(default=False, description="是否已读")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    link: Optional[str] = Field(default=None, description="链接")


class PortalWidgetConfig(BaseModel):
    """门户小部件配置"""
    widget_id: str = Field(description="小部件 ID")
    widget_type: str = Field(description="类型: chart/table/stat/list")
    title: str = Field(description="标题")
    position: Dict[str, int] = Field(description="位置 {x, y, w, h}")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")
    visible: bool = Field(default=True, description="是否可见")


class PortalLayoutConfig(BaseModel):
    """门户布局配置"""
    user_id: str = Field(description="用户 ID")
    layout_name: str = Field(default="default", description="布局名称")
    widgets: List[PortalWidgetConfig] = Field(default_factory=list, description="小部件列表")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")


class ActivityLogItem(BaseModel):
    """活动日志项"""
    id: str = Field(description="日志 ID")
    user_id: str = Field(description="用户 ID")
    action: str = Field(description="操作")
    resource_type: str = Field(description="资源类型")
    resource_id: Optional[str] = Field(default=None, description="资源 ID")
    details: Optional[str] = Field(default=None, description="详情")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间")
