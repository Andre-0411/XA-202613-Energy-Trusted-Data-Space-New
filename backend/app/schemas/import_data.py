"""
批量导入 Schema
"""
from typing import Optional, List

from pydantic import BaseModel, Field


class ImportResult(BaseModel):
    """导入结果"""
    total_rows: int = Field(description="总行数")
    success_count: int = Field(description="成功数")
    error_count: int = Field(description="失败数")
    errors: List[dict] = Field(default_factory=list, description="错误详情")
    imported_ids: List[str] = Field(default_factory=list, description="成功导入的 ID 列表")


class UserImportRow(BaseModel):
    """用户导入行"""
    username: str = Field(description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱")
    phone: Optional[str] = Field(default=None, description="手机号")
    role: str = Field(default="user", description="角色")
    organization_name: Optional[str] = Field(default=None, description="组织名称")
    department_name: Optional[str] = Field(default=None, description="部门名称")


class AssetImportRow(BaseModel):
    """数据资产导入行"""
    name: str = Field(description="资产名称")
    description: Optional[str] = Field(default=None, description="描述")
    source_type: str = Field(default="file", description="数据源类型")
    format: Optional[str] = Field(default=None, description="数据格式")
    classification: Optional[str] = Field(default=None, description="数据分类")
    security_level: str = Field(default="public", description="安全等级")
    tags: Optional[str] = Field(default=None, description="标签（逗号分隔）")
