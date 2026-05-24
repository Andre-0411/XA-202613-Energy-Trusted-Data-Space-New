"""
隐私计算路由 Schema
场景路由请求/响应、技术信息、引擎状态
"""
from typing import Optional
from pydantic import BaseModel, Field


class PrivacyRouteRequest(BaseModel):
    """隐私计算路由请求"""
    task_description: str = Field(description="任务描述（自然语言）")
    data_sensitivity: str = Field(default="high", description="数据敏感度: low/medium/high/critical")
    participants: int = Field(default=2, ge=2, description="参与方数量")
    scenario: Optional[str] = Field(default=None, description="业务场景（可选，自动推断）")
    requirements: Optional[dict] = Field(default=None, description="额外需求")


class TechnologyInfo(BaseModel):
    """隐私计算技术信息"""
    name: str = Field(description="技术全称")
    short_name: str = Field(description="技术简称")
    description: str = Field(description="技术描述")
    strengths: list[str] = Field(description="优势")
    weaknesses: list[str] = Field(description="劣势")


class PrivacyRouteResponse(BaseModel):
    """隐私计算路由响应"""
    technology: Optional[str] = Field(description="推荐技术")
    technology_name: Optional[str] = Field(default=None, description="推荐技术名称")
    scenario: Optional[str] = Field(description="业务场景")
    scenario_description: Optional[str] = Field(default=None, description="场景描述")
    technology_info: Optional[dict] = Field(default=None, description="技术详情")
    config: Optional[dict] = Field(default=None, description="建议配置")
    alternatives: list[dict] = Field(default_factory=list, description="备选方案")
    reasoning: Optional[str] = Field(default=None, description="推荐理由")
    error: Optional[str] = Field(default=None, description="错误信息")


class TechnologyItem(BaseModel):
    """技术列表条目"""
    technology: str = Field(description="技术标识")
    name: str = Field(description="技术名称")
    description: str = Field(description="技术描述")
    strengths: list[str] = Field(description="优势")
    weaknesses: list[str] = Field(description="劣势")
    available: bool = Field(description="是否可用")


class ScenarioItem(BaseModel):
    """场景列表条目"""
    scenario: str = Field(description="场景标识")
    description: str = Field(description="场景描述")
    recommended_technology: str = Field(description="推荐技术")
    alternatives: list[str] = Field(description="备选技术")
    typical_algorithms: list[str] = Field(description="典型算法")


class EngineStatusItem(BaseModel):
    """引擎状态条目"""
    available: bool = Field(description="是否可用")
    name: str = Field(description="引擎名称")


class EngineStatusResponse(BaseModel):
    """引擎状态响应"""
    engines: dict[str, EngineStatusItem] = Field(description="引擎状态映射")
