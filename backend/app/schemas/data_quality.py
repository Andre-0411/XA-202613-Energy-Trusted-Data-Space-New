"""
数据质量 Schema
质量评估、五维评分、质量报告等
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class QualityDimension(BaseModel):
    """质量维度评分"""
    dimension: str = Field(description="维度名称: completeness/accuracy/consistency/timeliness/uniqueness")
    score: float = Field(ge=0, le=100, description="维度得分 0-100")
    weight: float = Field(default=0.2, ge=0, le=1, description="权重")
    details: Optional[dict] = Field(default=None, description="维度详情")
    check_items: list[dict] = Field(default_factory=list, description="检查项列表")


class QualityAssessment(BaseModel):
    """质量评估结果"""
    asset_id: str = Field(description="资产 ID")
    asset_name: Optional[str] = Field(default=None, description="资产名称")
    total_score: float = Field(ge=0, le=100, description="综合得分 0-100")
    grade: str = Field(default="C", description="质量等级: A/B/C/D/F")
    dimensions: list[QualityDimension] = Field(default_factory=list, description="五维评分")
    assessed_at: str = Field(description="评估时间")
    assessed_by: str = Field(default="system", description="评估人")
    status: str = Field(default="completed", description="评估状态")


class QualityCheckRequest(BaseModel):
    """质量检查请求"""
    asset_id: str = Field(description="资产 ID")
    dimensions: Optional[list[str]] = Field(
        default=None,
        description="检查维度列表: completeness/accuracy/consistency/timeliness/uniqueness"
    )
    sample_size: int = Field(default=1000, ge=10, le=10000, description="采样大小")
    force_recheck: bool = Field(default=False, description="是否强制重新检查")


class QualityReport(BaseModel):
    """质量报告"""
    id: str = Field(description="报告 ID")
    asset_id: str = Field(description="资产 ID")
    asset_name: Optional[str] = Field(default=None, description="资产名称")
    total_score: float = Field(ge=0, le=100, description="综合得分")
    grade: str = Field(description="质量等级")
    completeness: float = Field(default=0.0, ge=0, le=100, description="完整性得分")
    accuracy: float = Field(default=0.0, ge=0, le=100, description="准确性得分")
    consistency: float = Field(default=0.0, ge=0, le=100, description="一致性得分")
    timeliness: float = Field(default=0.0, ge=0, le=100, description="时效性得分")
    uniqueness: float = Field(default=0.0, ge=0, le=100, description="唯一性得分")
    details: Optional[dict] = Field(default=None, description="详细信息")
    generated_at: datetime = Field(description="生成时间")
    status: str = Field(default="completed", description="状态")


class QualityTrend(BaseModel):
    """质量趋势"""
    date: str = Field(description="日期")
    total_score: float = Field(description="综合得分")
    completeness: float = Field(default=0.0, description="完整性")
    accuracy: float = Field(default=0.0, description="准确性")
    consistency: float = Field(default=0.0, description="一致性")
    timeliness: float = Field(default=0.0, description="时效性")
    uniqueness: float = Field(default=0.0, description="唯一性")


class QualityStatistics(BaseModel):
    """质量统计"""
    total_assets: int = Field(default=0, description="资产总数")
    checked_assets: int = Field(default=0, description="已检查资产数")
    avg_score: float = Field(default=0.0, description="平均得分")
    grade_distribution: dict = Field(default_factory=dict, description="等级分布")
    dimension_averages: dict = Field(default_factory=dict, description="各维度平均分")
    trend: list[QualityTrend] = Field(default_factory=list, description="质量趋势")


class QualityRule(BaseModel):
    """质量规则"""
    rule_id: str = Field(description="规则 ID")
    name: str = Field(description="规则名称")
    dimension: str = Field(description="所属维度")
    description: Optional[str] = Field(default=None, description="规则描述")
    check_type: str = Field(description="检查类型: null_check/range_check/format_check/unique_check")
    parameters: dict = Field(default_factory=dict, description="检查参数")
    weight: float = Field(default=1.0, ge=0, le=10, description="权重")
    enabled: bool = Field(default=True, description="是否启用")


class DataQualityConfig(BaseModel):
    """质量评估配置"""
    asset_id: str = Field(description="资产 ID")
    dimensions_config: dict = Field(
        default_factory=lambda: {
            "completeness": {"weight": 0.25, "threshold": 0.95},
            "accuracy": {"weight": 0.25, "threshold": 0.98},
            "consistency": {"weight": 0.20, "threshold": 0.95},
            "timeliness": {"weight": 0.15, "threshold": 0.90},
            "uniqueness": {"weight": 0.15, "threshold": 0.99},
        },
        description="维度配置"
    )
    auto_check_enabled: bool = Field(default=True, description="是否自动检查")
    check_interval_hours: int = Field(default=24, ge=1, description="检查间隔(小时)")
