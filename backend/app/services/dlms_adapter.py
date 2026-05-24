"""
DLMS/COSEM 协议适配器

支持 DLMS (Device Language Message Specification) / COSEM (Companion Specification for Energy Metering) 协议。
用于智能电表、电力终端等设备的数据采集。

DLMS协议特点:
- 基于 HDLC (High-level Data Link Control) 或 TCP/IP 传输
- 使用 OBIS (Object Identification System) 码标识数据对象
- 支持加密认证 (LS/HLS)
- 适用于 IEC 62056 标准

本适配器模拟实现 DLMS 协议数据读取，将结果统一转换为 MQTT 消息上报。
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.services.protocol_adapter import (
    ProtocolAdapter,
    ProtocolConfig,
    ProtocolType,
    DeviceDataPoint,
    ProtocolAdapterFactory,
)

logger = logging.getLogger(__name__)

# OBIS 码定义 (常见电力参数)
OBIS_DEFINITIONS = {
    "1.0.1.8.0.255": {"name": "正向有功总电能", "unit": "kWh", "metric": "active_energy_import"},
    "1.0.2.8.0.255": {"name": "反向有功总电能", "unit": "kWh", "metric": "active_energy_export"},
    "1.0.3.8.0.255": {"name": "正向无功总电能", "unit": "kvarh", "metric": "reactive_energy_import"},
    "1.0.4.8.0.255": {"name": "反向无功总电能", "unit": "kvarh", "metric": "reactive_energy_export"},
    "1.0.1.7.0.255": {"name": "瞬时有功功率", "unit": "kW", "metric": "active_power"},
    "1.0.2.7.0.255": {"name": "瞬时反向有功功率", "unit": "kW", "metric": "active_power_reverse"},
    "1.0.3.7.0.255": {"name": "瞬时无功功率", "unit": "kvar", "metric": "reactive_power"},
    "1.0.12.7.0.255": {"name": "频率", "unit": "Hz", "metric": "frequency"},
    "1.0.32.7.0.255": {"name": "A相电压", "unit": "V", "metric": "voltage_a"},
    "1.0.52.7.0.255": {"name": "B相电压", "unit": "V", "metric": "voltage_b"},
    "1.0.72.7.0.255": {"name": "C相电压", "unit": "V", "metric": "voltage_c"},
    "1.0.31.7.0.255": {"name": "A相电流", "unit": "A", "metric": "current_a"},
    "1.0.51.7.0.255": {"name": "B相电流", "unit": "A", "metric": "current_b"},
    "1.0.71.7.0.255": {"name": "C相电流", "unit": "A", "metric": "current_c"},
    "1.0.13.7.0.255": {"name": "功率因数", "unit": "", "metric": "power_factor"},
    "1.0.96.1.0.255": {"name": "设备序列号", "unit": "", "metric": "serial_number"},
    "0.0.1.0.0.255": {"name": "时钟", "unit": "", "metric": "clock"},
    "0.0.96.3.10.255": {"name": "继电器状态", "unit": "", "metric": "relay_status"},
}


class DLMSAdapter(ProtocolAdapter):
    """
    DLMS/COSEM 协议适配器

    实现 DLMS 协议数据读取，将电表、电力终端等设备的采集数据
    转换为标准 MQTT 消息格式上报。

    连接配置示例:
    {
        "host": "192.168.1.100",
        "port": 4059,
        "auth": {
            "client_id": 0x01,
            "auth_type": "low_level",
            "password": "123456"
        },
        "device_address": "12345678",
        "obis_codes": ["1.0.1.8.0.255", "1.0.1.7.0.255"]
    }
    """

    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self._obis_codes: list[str] = []
        self._client: Optional[object] = None

    def validate_config(self) -> list[str]:
        """验证 DLMS 连接配置"""
        errors: list[str] = []

        if not self._config.host:
            errors.append("DLMS 设备地址不能为空")
        if self._config.port <= 0 or self._config.port > 65535:
            errors.append(f"DLMS 端口无效: {self._config.port}")

        # 验证认证信息
        auth = self._config.auth or {}
        if auth:
            auth_type = auth.get("auth_type", "none")
            if auth_type not in ("none", "low_level", "high_level"):
                errors.append(f"不支持的 DLMS 认证类型: {auth_type}")
            if auth_type in ("low_level", "high_level") and not auth.get("password"):
                errors.append(f"DLMS {auth_type} 认证需要密码")

        return errors

    async def connect(self) -> bool:
        """
        建立 DLMS 连接

        模拟 HDLC/TCP 连接建立和 COSEM 关联协商
        """
        errors = self.validate_config()
        if errors:
            logger.error(f"DLMS 配置验证失败: {errors}")
            self._error_count += 1
            return False

        try:
            # 模拟 DLMS 连接过程
            # 实际应使用 gxDLMS 客户端或 gurux-dlms-python 库
            logger.info(
                f"DLMS 连接中: {self._config.host}:{self._config.port}, "
                f"device={self._config.device_address}"
            )

            # 获取需要采集的 OBIS 码列表
            self._obis_codes = (
                self._config.auth.get("obis_codes", list(OBIS_DEFINITIONS.keys())[:8])
                if self._config.auth
                else list(OBIS_DEFINITIONS.keys())[:8]
            )

            # 模拟连接成功
            self._connected = True
            self.device_did = self._config.device_address or f"dlms-{self._config.host}"
            self._error_count = 0
            logger.info(f"DLMS 连接成功: device={self.device_did}")
            return True

        except Exception as e:
            logger.error(f"DLMS 连接失败: {e}")
            self._connected = False
            self._error_count += 1
            return False

    async def disconnect(self) -> None:
        """断开 DLMS 连接"""
        if self._client:
            self._client = None
        self._connected = False
        logger.info(f"DLMS 已断开: device={self.device_did}")

    async def read_data(self) -> list[DeviceDataPoint]:
        """
        读取 DLMS 设备数据

        通过 GET 请求读取 OBIS 码对应的数据对象，
        将结果转换为 DeviceDataPoint 列表。
        """
        if not self._connected:
            logger.warning("DLMS 未连接，无法读取数据")
            return []

        import random

        now = datetime.now(timezone.utc)
        data_points: list[DeviceDataPoint] = []

        # 模拟读取各 OBIS 码的数据
        for obis_code in self._obis_codes:
            obis_def = OBIS_DEFINITIONS.get(obis_code)
            if not obis_def:
                logger.warning(f"未知的 OBIS 码: {obis_code}")
                continue

            # 模拟数据值
            metric = obis_def["metric"]
            if "energy" in metric:
                value = round(random.uniform(1000, 50000), 2)
            elif "voltage" in metric:
                value = round(random.uniform(218, 224), 1)
            elif "current" in metric:
                value = round(random.uniform(5, 100), 2)
            elif "power" in metric:
                value = round(random.uniform(10, 500), 2)
            elif "frequency" in metric:
                value = round(random.uniform(49.9, 50.1), 2)
            elif "factor" in metric:
                value = round(random.uniform(0.85, 1.0), 3)
            else:
                value = round(random.uniform(0, 100), 2)

            data_points.append(DeviceDataPoint(
                device_did=self.device_did,
                protocol=ProtocolType.DLMS,
                metric_name=metric,
                metric_value=value,
                unit=obis_def["unit"],
                timestamp=now,
                quality="good",
                metadata={"obis_code": obis_code, "obis_name": obis_def["name"]},
            ))

        logger.debug(f"DLMS 读取完成: {len(data_points)} 数据点, device={self.device_did}")
        return data_points


# 注册到工厂
ProtocolAdapterFactory.register(ProtocolType.DLMS, DLMSAdapter)
