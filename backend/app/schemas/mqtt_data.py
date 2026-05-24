"""
MQTT 数据采集 Schema
设备信息、采集数据、统计信息、告警信息等
"""
from typing import Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """设备信息"""
    did: str = Field(description="设备 DID")
    name: str = Field(description="设备名称")
    type: str = Field(description="设备类型: wind_turbine/solar_panel")
    enterprise: str = Field(description="所属企业")
    location: str = Field(description="设备位置")
    capacity_kw: float = Field(description="装机容量(kW)")
    status: str = Field(default="online", description="设备状态: online/offline/alarm")
    last_heartbeat: Optional[str] = Field(default=None, description="最后心跳时间")
    registered_at: Optional[str] = Field(default=None, description="注册时间")


class DeviceDataRecord(BaseModel):
    """设备采集数据记录"""
    device_did: str = Field(description="设备 DID")
    data_type: str = Field(description="数据类型: power_output/wind_speed/temperature等")
    values: dict = Field(description="采集数值")
    timestamp: str = Field(description="采集时间戳")
    signature: str = Field(default="", description="数据签名")
    stored_at: Optional[str] = Field(default=None, description="存储时间")


class CollectStatistics(BaseModel):
    """采集统计信息"""
    device_count: int = Field(default=0, description="设备总数")
    online_device_count: int = Field(default=0, description="在线设备数")
    total_messages: int = Field(default=0, description="总消息数")
    total_records: int = Field(default=0, description="总记录数")
    total_alarms: int = Field(default=0, description="告警总数")
    recent_alarms: int = Field(default=0, description="最近1小时告警数")
    missing_rate: float = Field(default=0.0, description="数据缺失率")
    start_time: Optional[str] = Field(default=None, description="启动时间")
    last_message_time: Optional[str] = Field(default=None, description="最后消息时间")


class AlarmRecord(BaseModel):
    """告警记录"""
    device_did: str = Field(description="设备 DID")
    alarm_type: str = Field(description="告警类型")
    message: str = Field(description="告警消息")
    severity: str = Field(default="warning", description="严重程度: info/warning/critical")
    values: Optional[dict] = Field(default=None, description="相关数据值")
    timestamp: str = Field(description="告警时间")
    acknowledged: bool = Field(default=False, description="是否已确认")


class SimulatorStatus(BaseModel):
    """模拟器状态"""
    running: bool = Field(description="是否运行中")
    connected: bool = Field(description="MQTT 是否已连接")
    mode: str = Field(description="运行模式: mqtt/memory")
    device_count: int = Field(description="设备数量")
    offline_buffer_size: int = Field(default=0, description="离线缓存大小")
    reconnect_count: int = Field(default=0, description="重连次数")


class CollectorConfig(BaseModel):
    """采集器配置"""
    enterprise_filter: Optional[str] = Field(default=None, description="企业过滤")
    device_type_filter: Optional[str] = Field(default=None, description="设备类型过滤")
    data_type_filter: Optional[str] = Field(default=None, description="数据类型过滤")
    time_range_start: Optional[str] = Field(default=None, description="时间范围开始")
    time_range_end: Optional[str] = Field(default=None, description="时间范围结束")
    limit: int = Field(default=100, ge=1, le=1000, description="返回条数")


class DataFetchRequest(BaseModel):
    """数据拉取请求"""
    device_did: Optional[str] = Field(default=None, description="设备 DID")
    data_type: Optional[str] = Field(default=None, description="数据类型")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    end_time: Optional[str] = Field(default=None, description="结束时间")
    limit: int = Field(default=100, ge=1, le=1000, description="返回条数")


class DeviceDataStatistics(BaseModel):
    """设备数据统计"""
    count: int = Field(default=0, description="数据条数")
    mean: dict = Field(default_factory=dict, description="均值")
    max: dict = Field(default_factory=dict, description="最大值")
    min: dict = Field(default_factory=dict, description="最小值")
    missing_rate: float = Field(default=0.0, description="缺失率")


class MqttStreamResponse(BaseModel):
    """MQTT 流数据响应"""
    devices: list[DeviceInfo] = Field(default_factory=list, description="设备列表")
    statistics: CollectStatistics = Field(default_factory=CollectStatistics, description="统计信息")
    recent_data: list[DeviceDataRecord] = Field(default_factory=list, description="最近数据")
    alarms: list[AlarmRecord] = Field(default_factory=list, description="告警列表")
