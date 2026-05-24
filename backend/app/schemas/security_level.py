"""
四级安全等级防护矩阵 Schema
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class SecurityLevelResponse(BaseModel):
    """安全等级响应"""
    level: int = Field(description="等级编号: 1/2/3/4")
    name: str = Field(description="等级名称: 核心/重要/一般/公开")
    classification_label: str = Field(default="", description="分类标签: 机密/敏感/内部/公开")
    description: str = Field(description="等级描述")
    color: str = Field(description="标识颜色")
    policies: dict = Field(description="防护策略详情")


class SecurityLevelPolicyResponse(BaseModel):
    """安全等级防护策略响应"""
    level: int
    name: str
    classification_label: str = Field(default="", description="分类标签: 机密/敏感/内部/公开")
    encryption: dict = Field(description="加密要求")
    signature: dict = Field(default_factory=dict, description="签名要求")
    authentication: dict = Field(description="认证要求")
    audit: dict = Field(description="审计要求")
    access_control: dict = Field(description="访问控制要求")
    data_handling: dict = Field(description="数据处理要求")


class SecurityCheckRequest(BaseModel):
    """安全等级检查请求"""
    resource_type: str = Field(description="资源类型: dataset/model/api/document/file")
    resource_id: str = Field(description="资源 ID")
    context: Optional[dict] = Field(default=None, description="附加上下文（数据量、敏感度标签等）")


class SecurityCheckResponse(BaseModel):
    """安全等级检查响应"""
    resource_type: str
    resource_id: str
    current_level: int = Field(description="当前安全等级")
    level_name: str
    classification_label: str = Field(default="", description="分类标签: 机密/敏感/内部/公开")
    required_measures: list[str] = Field(description="必须满足的安全措施")
    compliance_status: str = Field(description="合规状态: compliant/non_compliant/partial")
    missing_measures: list[str] = Field(default_factory=list, description="缺失的安全措施")
    recommendations: list[str] = Field(default_factory=list, description="改进建议")
    checked_at: datetime


class SetSecurityLevelRequest(BaseModel):
    """设置资源安全等级请求"""
    level: int = Field(ge=1, le=4, description="安全等级: 1-4")
    reason: Optional[str] = Field(default=None, description="设置原因")
    operator: Optional[str] = Field(default=None, description="操作人")
