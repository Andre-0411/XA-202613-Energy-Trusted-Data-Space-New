"""
协议适配器统一接口

定义统一的设备数据采集协议适配层:
- ProtocolAdapter: 抽象基类，定义统一接口
- ProtocolType: 协议类型枚举
- MQTTMessage: 统一MQTT上报消息格式

所有协议适配器将原始协议数据转换为标准MQTT主题格式上报:
  energy/device/{device_did}/{protocol}/{metric}
"""
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProtocolType(str, Enum):
    """协议类型枚举"""
    DLMS = "DLMS"
    MODBUS = "Modbus"
    IEC61850 = "IEC61850"
    HTTP = "HTTP"
    MQTT = "MQTT"
    WEBSOCKET = "WebSocket"


class MQTTMessage(BaseModel):
    """统一MQTT上报消息格式"""
    topic: str = Field(description="MQTT主题")
    payload: dict = Field(description="消息载荷")
    qos: int = Field(default=1, ge=0, le=2, description="QoS等级")
    retain: bool = Field(default=False, description="是否保留消息")

    class Config:
        frozen = True


class DeviceDataPoint(BaseModel):
    """设备数据点"""
    device_did: str = Field(description="设备唯一标识")
    protocol: ProtocolType = Field(description="协议类型")
    metric_name: str = Field(description="指标名称")
    metric_value: Any = Field(description="指标值")
    unit: Optional[str] = Field(default=None, description="计量单位")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="采集时间戳",
    )
    quality: str = Field(default="good", description="数据质量标识: good/bad/uncertain")
    metadata: Optional[dict] = Field(default=None, description="附加元数据")


class ProtocolConfig(BaseModel):
    """协议连接配置"""
    protocol_type: ProtocolType = Field(description="协议类型")
    host: str = Field(description="设备地址")
    port: int = Field(description="端口号")
    timeout_ms: int = Field(default=5000, description="连接超时(ms)")
    retry_count: int = Field(default=3, description="重试次数")
    auth: Optional[dict] = Field(default=None, description="认证信息")
    device_address: Optional[str] = Field(default=None, description="设备地址(协议内)")
    polling_interval_ms: int = Field(default=5000, description="轮询间隔(ms)")


class ProtocolAdapter(ABC):
    """
    协议适配器抽象基类

    所有协议适配器必须实现以下方法:
    - connect: 建立连接
    - disconnect: 断开连接
    - read_data: 读取设备数据
    - convert_to_mqtt: 将原始数据转换为MQTT消息格式
    - validate_config: 验证连接配置
    """

    def __init__(self, config: ProtocolConfig):
        self._config = config
        self._connected: bool = False
        self._device_did: str = ""
        self._last_read_time: Optional[datetime] = None
        self._error_count: int = 0

    @property
    def protocol_type(self) -> ProtocolType:
        """协议类型"""
        return self._config.protocol_type

    @property
    def is_connected(self) -> bool:
        """连接状态"""
        return self._connected

    @property
    def device_did(self) -> str:
        """设备标识"""
        return self._device_did

    @device_did.setter
    def device_did(self, value: str) -> None:
        self._device_did = value

    @property
    def last_read_time(self) -> Optional[datetime]:
        """最后读取时间"""
        return self._last_read_time

    @property
    def error_count(self) -> int:
        """错误计数"""
        return self._error_count

    @abstractmethod
    async def connect(self) -> bool:
        """
        建立连接

        Returns:
            连接是否成功
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        ...

    @abstractmethod
    async def read_data(self) -> list[DeviceDataPoint]:
        """
        读取设备数据

        Returns:
            数据点列表
        """
        ...

    @abstractmethod
    def validate_config(self) -> list[str]:
        """
        验证连接配置

        Returns:
            验证错误列表，空列表表示验证通过
        """
        ...

    def convert_to_mqtt(
        self,
        data_points: list[DeviceDataPoint],
        base_topic: str = "energy/device",
    ) -> list[MQTTMessage]:
        """
        将数据点转换为MQTT消息

        消息主题格式: {base_topic}/{device_did}/{protocol}/{metric}
        消息载荷格式: {"value": ..., "unit": ..., "timestamp": ..., "quality": ...}

        Args:
            data_points: 数据点列表
            base_topic: 基础主题前缀

        Returns:
            MQTT消息列表
        """
        messages: list[MQTTMessage] = []
        for dp in data_points:
            topic = f"{base_topic}/{dp.device_did}/{dp.protocol.value}/{dp.metric_name}"
            payload = {
                "value": dp.metric_value,
                "unit": dp.unit,
                "timestamp": dp.timestamp.isoformat(),
                "quality": dp.quality,
                "device_did": dp.device_did,
                "protocol": dp.protocol.value,
            }
            if dp.metadata:
                payload["metadata"] = dp.metadata

            messages.append(MQTTMessage(
                topic=topic,
                payload=payload,
                qos=1,
                retain=False,
            ))

        self._last_read_time = datetime.now(timezone.utc)
        return messages

    def get_status(self) -> dict:
        """获取适配器状态"""
        return {
            "protocol": self._config.protocol_type.value,
            "connected": self._connected,
            "device_did": self._device_did,
            "host": self._config.host,
            "port": self._config.port,
            "last_read_time": self._last_read_time.isoformat() if self._last_read_time else None,
            "error_count": self._error_count,
        }


class ProtocolAdapterFactory:
    """协议适配器工厂"""

    _registry: dict[ProtocolType, type[ProtocolAdapter]] = {}

    @classmethod
    def register(cls, protocol_type: ProtocolType, adapter_class: type[ProtocolAdapter]) -> None:
        """注册协议适配器"""
        cls._registry[protocol_type] = adapter_class
        logger.info(f"Protocol adapter registered: {protocol_type.value} -> {adapter_class.__name__}")

    @classmethod
    def create(cls, config: ProtocolConfig) -> ProtocolAdapter:
        """
        创建协议适配器实例

        Args:
            config: 协议连接配置

        Returns:
            协议适配器实例

        Raises:
            ValueError: 不支持的协议类型
        """
        adapter_class = cls._registry.get(config.protocol_type)
        if not adapter_class:
            raise ValueError(
                f"不支持的协议类型: {config.protocol_type.value}，"
                f"支持的协议: {list(cls._registry.keys())}"
            )
        return adapter_class(config)

    @classmethod
    def supported_protocols(cls) -> list[str]:
        """获取支持的协议列表"""
        return [p.value for p in cls._registry.keys()]

    @classmethod
    def get_adapter_info(cls) -> list[dict]:
        """获取所有已注册适配器信息"""
        return [
            {
                "protocol": ptype.value,
                "adapter_class": adapter_cls.__name__,
                "module": adapter_cls.__module__,
            }
            for ptype, adapter_cls in cls._registry.items()
        ]
