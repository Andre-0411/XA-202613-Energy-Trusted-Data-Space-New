"""
IEC 61850 协议适配器

支持 IEC 61850 MMS (Manufacturing Message Specification) 协议，
用于变电站自动化系统、智能电网设备的数据采集。

IEC 61850 协议特点:
- 基于 MMS (ISO 9506) 协议，使用 TCP/IP 传输
- 使用 SCL (Substation Configuration Language) 配置
- 数据模型: 逻辑设备(LD) / 逻辑节点(LN) / 数据对象(DO) / 数据属性(DA)
- 通信服务: 定值(Setting) / 遥测(Measurand) / 遥信(Status) / 遥控(Control)
- 报告服务: 缓冲/非缓冲报告 (BRCB/URCB)
- GOOSE 报文: 快速跳闸/联锁等实时信号

本适配器模拟实现 IEC 61850 数据读取，将结果统一转换为 MQTT 消息上报。
"""
import logging
import random
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


# IEC 61850 常见逻辑节点和数据对象
IEC61850_DATA_OBJECTS = {
    # 遥测 (Measurement)
    "MMXU1.PhV.phsA.mag.f": {"name": "A相电压", "unit": "V", "metric": "voltage_a"},
    "MMXU1.PhV.phsB.mag.f": {"name": "B相电压", "unit": "V", "metric": "voltage_b"},
    "MMXU1.PhV.phsC.mag.f": {"name": "C相电压", "unit": "V", "metric": "voltage_c"},
    "MMXU1.A.phsA.mag.f": {"name": "A相电流", "unit": "A", "metric": "current_a"},
    "MMXU1.A.phsB.mag.f": {"name": "B相电流", "unit": "A", "metric": "current_b"},
    "MMXU1.A.phsC.mag.f": {"name": "C相电流", "unit": "A", "metric": "current_c"},
    "MMXU1.TotW.mag.f": {"name": "总有功功率", "unit": "MW", "metric": "active_power"},
    "MMXU1.TotVAr.mag.f": {"name": "总无功功率", "unit": "Mvar", "metric": "reactive_power"},
    "MMXU1.TotVA.mag.f": {"name": "总视在功率", "unit": "MVA", "metric": "apparent_power"},
    "MMXU1.Hz.mag.f": {"name": "频率", "unit": "Hz", "metric": "frequency"},
    "MMXU1.TotPF.mag.f": {"name": "总功率因数", "unit": "", "metric": "power_factor"},
    "MMXU1.W.phsA.mag.f": {"name": "A相有功功率", "unit": "MW", "metric": "active_power_a"},
    "MMXU1.W.phsB.mag.f": {"name": "B相有功功率", "unit": "MW", "metric": "active_power_b"},
    "MMXU1.W.phsC.mag.f": {"name": "C相有功功率", "unit": "MW", "metric": "active_power_c"},
    # 环境测量
    "MMET1.EnvTmp.mag.f": {"name": "环境温度", "unit": "°C", "metric": "env_temperature"},
    "MMET1.EnvHum.mag.f": {"name": "环境湿度", "unit": "%RH", "metric": "env_humidity"},
    "MMET1.WndSpd.mag.f": {"name": "风速", "unit": "m/s", "metric": "wind_speed"},
    "MMET1.WndDir.mag.f": {"name": "风向", "unit": "°", "metric": "wind_direction"},
    "MMET1.SolRadi.mag.f": {"name": "太阳辐照度", "unit": "W/m²", "metric": "irradiance"},
    # 遥信 (Status)
    "CSWI1.Pos.stVal": {"name": "断路器位置", "unit": "", "metric": "breaker_position"},
    "XCBR1.Pos.stVal": {"name": "隔离开关位置", "unit": "", "metric": "switch_position"},
    # 保护装置
    "PDIS1.Op.general": {"name": "距离保护动作", "unit": "", "metric": "distance_protection"},
    "PTOC1.Op.general": {"name": "过流保护动作", "unit": "", "metric": "overcurrent_protection"},
    # 电能计量
    "MMTR1.TotWh.actVal": {"name": "正向有功电能", "unit": "MWh", "metric": "energy_import"},
    "MMTR1.TotVArh.actVal": {"name": "正向无功电能", "unit": "Mvarh", "metric": "reactive_energy"},
}


class IEC61850Adapter(ProtocolAdapter):
    """
    IEC 61850 MMS 协议适配器

    实现 IEC 61850 数据读取，将变电站、智能电网设备的采集数据
    转换为标准 MQTT 消息格式上报。

    连接配置示例:
    {
        "host": "192.168.1.100",
        "port": 102,
        "auth": {
            "ied_name": "IED1",
            "access_point": "S1",
            "logical_device": "LD0",
            "data_objects": ["MMXU1.PhV.phsA.mag.f", "MMXU1.TotW.mag.f"]
        }
    }
    """

    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self._ied_name: str = ""
        self._access_point: str = ""
        self._logical_device: str = ""
        self._data_objects: list[str] = []

    def validate_config(self) -> list[str]:
        """验证 IEC 61850 连接配置"""
        errors: list[str] = []

        if not self._config.host:
            errors.append("IEC 61850 设备地址不能为空")
        if self._config.port <= 0 or self._config.port > 65535:
            errors.append(f"IEC 61850 端口无效: {self._config.port}")

        auth = self._config.auth or {}
        if auth:
            ied_name = auth.get("ied_name", "")
            if not ied_name:
                errors.append("IEC 61850 IED 名称不能为空")
            logical_device = auth.get("logical_device", "")
            if not logical_device:
                errors.append("IEC 61850 逻辑设备名不能为空")

        return errors

    async def connect(self) -> bool:
        """
        建立 IEC 61850 MMS 连接

        模拟 MMS 连接建立过程 (TCP 连接 + MMS Initiate)
        """
        errors = self.validate_config()
        if errors:
            logger.error(f"IEC 61850 配置验证失败: {errors}")
            self._error_count += 1
            return False

        try:
            auth = self._config.auth or {}
            self._ied_name = auth.get("ied_name", "IED1")
            self._access_point = auth.get("access_point", "S1")
            self._logical_device = auth.get("logical_device", "LD0")

            # 获取要读取的数据对象列表
            self._data_objects = auth.get("data_objects", list(IEC61850_DATA_OBJECTS.keys())[:15])

            # 模拟 MMS 连接
            logger.info(
                f"IEC 61850 连接中: {self._config.host}:{self._config.port}, "
                f"IED={self._ied_name}, AP={self._access_point}, LD={self._logical_device}"
            )

            self._connected = True
            self.device_did = (
                self._config.device_address
                or f"iec61850-{self._ied_name}-{self._logical_device}"
            )
            self._error_count = 0
            logger.info(f"IEC 61850 连接成功: device={self.device_did}")
            return True

        except Exception as e:
            logger.error(f"IEC 61850 连接失败: {e}")
            self._connected = False
            self._error_count += 1
            return False

    async def disconnect(self) -> None:
        """断开 IEC 61850 MMS 连接"""
        self._connected = False
        logger.info(f"IEC 61850 已断开: device={self.device_did}")

    async def read_data(self) -> list[DeviceDataPoint]:
        """
        读取 IEC 61850 设备数据

        通过 MMS Read 服务读取数据对象的值，
        将结果转换为 DeviceDataPoint 列表。
        """
        if not self._connected:
            logger.warning("IEC 61850 未连接，无法读取数据")
            return []

        now = datetime.now(timezone.utc)
        data_points: list[DeviceDataPoint] = []

        for obj_path in self._data_objects:
            obj_def = IEC61850_DATA_OBJECTS.get(obj_path)
            if not obj_def:
                logger.warning(f"未知的 IEC 61850 数据对象: {obj_path}")
                continue

            # 模拟读取数据
            value = self._read_data_object(obj_path, obj_def)

            data_points.append(DeviceDataPoint(
                device_did=self.device_did,
                protocol=ProtocolType.IEC61850,
                metric_name=obj_def["metric"],
                metric_value=value,
                unit=obj_def["unit"],
                timestamp=now,
                quality="good",
                metadata={
                    "ied_name": self._ied_name,
                    "access_point": self._access_point,
                    "logical_device": self._logical_device,
                    "data_object": obj_path,
                    "object_name": obj_def["name"],
                },
            ))

        logger.debug(f"IEC 61850 读取完成: {len(data_points)} 数据点, device={self.device_did}")
        return data_points

    def _read_data_object(self, obj_path: str, obj_def: dict) -> float:
        """
        读取 IEC 61850 数据对象值 (模拟)

        实际应使用 libiec61850 或 iec61850-python 库:
        ied_connection.read_object_value(con, object_reference, fc)

        Args:
            obj_path: 数据对象路径
            obj_def: 数据对象定义

        Returns:
            数据对象值
        """
        metric = obj_def["metric"]

        if "voltage" in metric:
            return round(random.uniform(110000, 115000), 1)
        elif "current" in metric:
            return round(random.uniform(100, 2000), 1)
        elif "active_power" in metric and "a" not in metric and "b" not in metric and "c" not in metric:
            return round(random.uniform(50, 500), 2)
        elif "active_power" in metric:
            return round(random.uniform(15, 180), 2)
        elif "reactive_power" in metric:
            return round(random.uniform(10, 200), 2)
        elif "apparent_power" in metric:
            return round(random.uniform(60, 550), 2)
        elif "frequency" in metric:
            return round(random.uniform(49.95, 50.05), 3)
        elif "power_factor" in metric:
            return round(random.uniform(0.85, 0.99), 3)
        elif "energy" in metric:
            return round(random.uniform(1000, 50000), 1)
        elif "temperature" in metric:
            return round(random.uniform(15, 40), 1)
        elif "humidity" in metric:
            return round(random.uniform(30, 80), 1)
        elif "wind_speed" in metric:
            return round(random.uniform(0, 25), 1)
        elif "wind_direction" in metric:
            return round(random.uniform(0, 360), 1)
        elif "irradiance" in metric:
            return round(random.uniform(0, 1200), 1)
        elif "breaker" in metric or "switch" in metric or "protection" in metric:
            return float(random.choice([0, 1]))
        else:
            return round(random.uniform(0, 100), 2)


# 注册到工厂
ProtocolAdapterFactory.register(ProtocolType.IEC61850, IEC61850Adapter)
