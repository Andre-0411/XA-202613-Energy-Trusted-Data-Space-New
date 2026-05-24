"""
连接器 Schema
Connector / ConnectorDataSource / MetadataDiscovery
"""
from typing import Optional, Any, List
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 连接器 ====================

class ConnectorCreate(BaseModel):
    """创建连接器"""
    name: str = Field(description="连接器名称")
    connector_type: str = Field(default="lite", description="连接器类型: lite/professional")
    version: Optional[str] = Field(default=None, description="版本号")
    deployment_config: dict = Field(default_factory=dict, description="部署配置")


class ConnectorUpdate(BaseModel):
    """更新连接器"""
    name: Optional[str] = Field(default=None, description="连接器名称")
    version: Optional[str] = Field(default=None, description="版本号")
    deployment_config: Optional[dict] = Field(default=None, description="部署配置")
    status: Optional[str] = Field(default=None, description="状态")


class ConnectorHeartbeat(BaseModel):
    """连接器心跳"""
    system_status: dict = Field(default_factory=dict, description="系统状态")
    resource_usage: Optional[dict] = Field(default=None, description="资源使用情况")
    network_info: Optional[dict] = Field(default=None, description="网络信息")


class ConnectorResponse(BaseModel):
    """连接器响应"""
    id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    connector_type: str = Field(description="类型")
    version: Optional[str] = Field(default=None)
    deployment_config: dict = Field(default_factory=dict)
    organization_id: str = Field(description="所属组织 ID")
    owner_id: str = Field(description="负责人 ID")
    status: str = Field(description="状态")
    last_heartbeat: Optional[str] = Field(default=None)
    system_status: Optional[dict] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 连接器数据源 ====================

class ConnectorDataSourceCreate(BaseModel):
    """创建连接器数据源"""
    name: str = Field(description="数据源名称")
    source_type: str = Field(description="数据源类型: mysql/postgresql/oracle/mqtt/file/api")
    connection_config: dict = Field(default_factory=dict, description="连接配置")
    refresh_schedule: Optional[str] = Field(default=None, description="刷新计划 cron 表达式")


class ConnectorDataSourceUpdate(BaseModel):
    """更新连接器数据源"""
    name: Optional[str] = Field(default=None, description="数据源名称")
    connection_config: Optional[dict] = Field(default=None, description="连接配置")
    refresh_schedule: Optional[str] = Field(default=None, description="刷新计划")
    status: Optional[str] = Field(default=None, description="状态")


class ConnectorDataSourceResponse(BaseModel):
    """连接器数据源响应"""
    id: str = Field(description="数据源 ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    source_type: str = Field(description="数据源类型")
    connection_config: dict = Field(default_factory=dict)
    refresh_schedule: Optional[str] = Field(default=None)
    status: str = Field(description="状态")
    last_sync_at: Optional[str] = Field(default=None)
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 元数据发现 ====================

class MetadataDiscoverRequest(BaseModel):
    """元数据发现请求"""
    data_source_id: str = Field(description="数据源 ID")
    discovery_scope: dict = Field(default_factory=dict, description="发现范围配置")


class MetadataDiscoveryResponse(BaseModel):
    """元数据发现响应"""
    id: str = Field(description="发现记录 ID")
    connector_id: str = Field(description="连接器 ID")
    data_source_id: str = Field(description="数据源 ID")
    discovery_scope: dict = Field(default_factory=dict)
    discovered_metadata: dict = Field(default_factory=dict)
    security_scan_result: dict = Field(default_factory=dict)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")
    updated_at: str = Field(description="更新时间")


# ==================== 连接器文件库 ====================

class ConnectorFileResponse(BaseModel):
    """连接器文件响应"""
    id: str = Field(description="文件 ID")
    connector_id: str = Field(description="连接器 ID")
    file_name: str = Field(description="文件名")
    file_path: str = Field(description="文件路径")
    file_size: Optional[int] = Field(default=None, description="文件大小")
    file_type: Optional[str] = Field(default=None, description="文件类型")
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class FileSetCreate(BaseModel):
    """创建文件集"""
    name: str = Field(description="文件集名称")
    description: Optional[str] = Field(default=None, description="描述")
    file_ids: List[str] = Field(default_factory=list, description="文件 ID 列表")


class FileSetResponse(BaseModel):
    """文件集响应"""
    id: str = Field(description="文件集 ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    description: Optional[str] = Field(default=None)
    file_ids: List[str] = Field(default_factory=list)
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class ApiProxyCreate(BaseModel):
    """创建 API 代理"""
    name: str = Field(description="API 名称")
    target_url: str = Field(description="目标 URL")
    http_method: str = Field(default="GET", description="HTTP 方法")
    headers: dict = Field(default_factory=dict, description="请求头")
    auth_config: dict = Field(default_factory=dict, description="认证配置")


class ApiProxyResponse(BaseModel):
    """API 代理响应"""
    id: str = Field(description="API ID")
    connector_id: str = Field(description="连接器 ID")
    name: str = Field(description="名称")
    target_url: str = Field(description="目标 URL")
    http_method: str = Field(description="HTTP 方法")
    status: str = Field(description="状态")
    created_at: str = Field(description="创建时间")


class ApiProxyTestResult(BaseModel):
    """API 代理测试结果"""
    success: bool = Field(description="是否成功")
    status_code: Optional[int] = Field(default=None, description="HTTP 状态码")
    response_time_ms: Optional[float] = Field(default=None, description="响应时间(ms)")
    error_message: Optional[str] = Field(default=None, description="错误信息")
