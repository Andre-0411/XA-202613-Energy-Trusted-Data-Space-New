"""
连接器文件/文件集/API代理 Schema
ConnectorFile / FileSet / ApiProxy
"""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 文件集 ====================

class FileSetCreate(BaseModel):
    """创建文件集"""
    name: str = Field(description="文件集名称")
    description: Optional[str] = Field(default=None, description="描述")


class FileSetResponse(BaseModel):
    """文件集响应"""
    id: str = Field(description="文件集 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    organization_id: str = Field(description="所属组织 ID")
    created_by: str = Field(description="创建者 ID")
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")
    files: List["ConnectorFileResponse"] = Field(default_factory=list)


# ==================== 连接器文件 ====================

class ConnectorFileCreate(BaseModel):
    """上传连接器文件"""
    connector_id: str = Field(description="连接器 ID")
    file_set_id: Optional[str] = Field(default=None, description="文件集 ID")
    file_name: str = Field(description="文件名")
    file_path: str = Field(description="存储路径")
    file_type: str = Field(description="文件类型: csv/json/xml/pdf/parquet/xlsx")
    file_size_bytes: int = Field(default=0, description="文件大小（字节）")
    content_hash: Optional[str] = Field(default=None, description="内容哈希 SHA256")
    row_count: Optional[int] = Field(default=None, description="数据行数")
    column_schema: list = Field(default_factory=list, description="列结构定义")


class ConnectorFileUpdate(BaseModel):
    """更新连接器文件"""
    file_set_id: Optional[str] = Field(default=None, description="文件集 ID")
    file_name: Optional[str] = Field(default=None, description="文件名")
    column_schema: Optional[list] = Field(default=None, description="列结构定义")
    status: Optional[str] = Field(default=None, description="状态")


class ConnectorFileResponse(BaseModel):
    """连接器文件响应"""
    id: str = Field(description="文件 ID")
    connector_id: str = Field(description="连接器 ID")
    file_set_id: Optional[str] = Field(default=None)
    file_name: str = Field(description="文件名")
    file_path: str = Field(description="存储路径")
    file_type: str = Field(description="文件类型")
    file_size_bytes: int = Field(default=0)
    content_hash: Optional[str] = Field(default=None)
    row_count: Optional[int] = Field(default=None)
    column_schema: list = Field(default_factory=list)
    metadata_: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    uploaded_by: str = Field(description="上传者 ID")
    created_at: str = Field(description="创建时间")


# ==================== API代理 ====================

class ApiProxyCreate(BaseModel):
    """创建API代理"""
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="代理名称")
    description: Optional[str] = Field(default=None, description="描述")
    target_url: str = Field(description="目标URL")
    http_method: str = Field(default="GET", description="HTTP方法: GET/POST/PUT/DELETE")
    request_headers: dict = Field(default_factory=dict, description="请求头")
    request_params: dict = Field(default_factory=dict, description="请求参数模板")
    request_body_template: Optional[str] = Field(default=None, description="请求体模板")
    response_mapping: dict = Field(default_factory=dict, description="响应字段映射")
    auth_config: dict = Field(default_factory=dict, description="认证配置")
    rate_limit: int = Field(default=60, description="每分钟请求限制")
    timeout_ms: int = Field(default=30000, description="超时毫秒")
    retry_count: int = Field(default=3, description="重试次数")


class ApiProxyUpdate(BaseModel):
    """更新API代理"""
    name: Optional[str] = Field(default=None, description="代理名称")
    description: Optional[str] = Field(default=None, description="描述")
    target_url: Optional[str] = Field(default=None, description="目标URL")
    http_method: Optional[str] = Field(default=None, description="HTTP方法")
    request_headers: Optional[dict] = Field(default=None, description="请求头")
    request_params: Optional[dict] = Field(default=None, description="请求参数模板")
    request_body_template: Optional[str] = Field(default=None, description="请求体模板")
    response_mapping: Optional[dict] = Field(default=None, description="响应字段映射")
    auth_config: Optional[dict] = Field(default=None, description="认证配置")
    rate_limit: Optional[int] = Field(default=None, description="每分钟请求限制")
    timeout_ms: Optional[int] = Field(default=None, description="超时毫秒")
    retry_count: Optional[int] = Field(default=None, description="重试次数")
    is_enabled: Optional[bool] = Field(default=None, description="是否启用")


class ApiProxyResponse(BaseModel):
    """API代理响应"""
    id: str = Field(description="代理 ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    target_url: str = Field(description="目标URL")
    http_method: str = Field(description="HTTP方法")
    request_headers: dict = Field(default_factory=dict)
    request_params: dict = Field(default_factory=dict)
    request_body_template: Optional[str] = Field(default=None)
    response_mapping: dict = Field(default_factory=dict)
    auth_config: dict = Field(default_factory=dict)
    rate_limit: int = Field(default=60)
    timeout_ms: int = Field(default=30000)
    retry_count: int = Field(default=3)
    is_enabled: bool = Field(default=True)
    status: str = Field(description="状态")
    created_by: str = Field(description="创建者 ID")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# 重建引用
FileSetResponse.model_rebuild()
