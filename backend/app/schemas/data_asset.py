"""
数据资产 Schema
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    """创建数据源"""
    name: str = Field(max_length=200, description="数据源名称")
    protocol_type: str = Field(description="协议类型: DLMS/Modbus/HTTP/WebSocket")
    connection_config: dict = Field(description="连接配置")
    device_did: Optional[str] = Field(default=None, description="设备 DID")
    mqtt_topic: Optional[str] = Field(default=None, description="MQTT 主题")
    collection_interval_ms: int = Field(default=5000, description="采集间隔(ms)")
    is_critical: bool = Field(default=False, description="是否核心数据")
    edge_preprocess: Optional[dict] = Field(default=None, description="边缘预处理配置")
    organization_id: str = Field(description="组织 ID")


class DataSourceResponse(BaseModel):
    """数据源响应"""
    id: str
    name: str
    protocol_type: str
    device_did: Optional[str] = None
    mqtt_topic: Optional[str] = None
    collection_interval_ms: int = 5000
    is_critical: bool = False
    edge_preprocess: Optional[dict] = None
    status: str
    organization_id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DataAssetCreate(BaseModel):
    """创建数据资产"""
    name: str = Field(max_length=200, description="资产名称")
    source_id: Optional[str] = Field(default=None, description="数据源 ID")
    category: str = Field(description="大类: 发电/用电/调度/市场/设备状态/地理信息")
    classification_level: int = Field(default=4, ge=1, le=4, description="敏感级别 1核心/2重要/3敏感/4公开")
    description: Optional[str] = Field(default=None, description="描述")
    schema_def: Optional[dict] = Field(default=None, description="数据 Schema")
    storage_format: str = Field(default="parquet", description="存储格式")
    owner_id: str = Field(description="所有者 ID")
    organization_id: str = Field(description="组织 ID")


class DataAssetResponse(BaseModel):
    """数据资产响应"""
    id: str
    name: str
    source_id: Optional[str] = None
    category: str
    classification_level: int
    description: Optional[str] = None
    schema_def: Optional[dict] = None
    storage_path: Optional[str] = None
    storage_format: str = "parquet"
    size_bytes: int = 0
    record_count: int = 0
    nft_token_id: Optional[str] = None
    status: str
    owner_id: str
    organization_id: str
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetadataCreate(BaseModel):
    """创建元数据"""
    asset_id: str = Field(description="关联资产 ID")
    standard: str = Field(default="GB/T 36073-2018", description="遵循标准")
    content: dict = Field(description="元数据内容")
    lineage_graph: Optional[dict] = Field(default=None, description="血缘图")


class MetadataResponse(BaseModel):
    """元数据响应"""
    id: str
    asset_id: str
    standard: str
    content: dict
    lineage_graph: Optional[dict] = None
    version: int
    previous_version_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityReportResponse(BaseModel):
    """数据质量报告响应"""
    id: str
    asset_id: str
    completeness: Optional[float] = None
    timeliness_ms: Optional[int] = None
    accuracy: Optional[float] = None
    consistency: Optional[float] = None
    overall_score: Optional[float] = None
    details: Optional[dict] = None
    generated_at: datetime

    model_config = {"from_attributes": True}


class DataAssetRatingCreate(BaseModel):
    """创建数据资产评价"""
    rating: int = Field(ge=1, le=5, description="评分（1-5）")
    comment: Optional[str] = Field(default=None, max_length=2000, description="评价内容")
    tags: Optional[list[str]] = Field(default=None, description="评价标签")
    user_name: Optional[str] = Field(default=None, max_length=100, description="评价用户名")


class DataAssetRatingResponse(BaseModel):
    """数据资产评价响应"""
    id: str
    asset_id: str
    user_id: Optional[str] = None
    user_name: str
    rating: int
    comment: Optional[str] = None
    tags: Optional[list[str]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RatingStatisticsResponse(BaseModel):
    """评价统计响应"""
    asset_id: str
    total_ratings: int = 0
    avg_rating: float = 0.0
    rating_distribution: dict = Field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
    recent_ratings: list[DataAssetRatingResponse] = Field(default_factory=list)


class ProtocolTestRequest(BaseModel):
    """协议连接测试请求"""
    protocol_type: str = Field(description="协议类型: DLMS/Modbus/IEC61850")
    host: str = Field(description="设备地址")
    port: int = Field(description="端口号")
    auth: Optional[dict] = Field(default=None, description="认证配置")
    device_address: Optional[str] = Field(default=None, description="设备地址(协议内)")


class ProtocolTestResponse(BaseModel):
    """协议连接测试响应"""
    protocol_type: str
    connected: bool
    device_did: Optional[str] = None
    config_errors: list[str] = Field(default_factory=list)
    adapter_status: Optional[dict] = None


class ProtocolInfoResponse(BaseModel):
    """协议适配器信息响应"""
    supported_protocols: list[str]
    adapter_info: list[dict]
