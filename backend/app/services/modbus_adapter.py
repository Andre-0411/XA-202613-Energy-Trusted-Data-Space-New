"""
Modbus 协议适配器

支持 Modbus TCP/RTU 协议，用于 PLC、传感器、变频器等设备的数据采集。

Modbus 协议特点:
- Modbus TCP: 基于 TCP/IP，默认端口 502
- Modbus RTU: 基于串口 (RS-485/RS-232)
- 功能码支持: FC01(线圈) / FC02(离散输入) / FC03(保持寄存器) / FC04(输入寄存器)
- 地址范围: 0x0000 - 0xFFFF (0 - 65535)

本适配器模拟实现 Modbus 数据读取，将结果统一转换为 MQTT 消息上报。
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


# Modbus 功能码
class ModbusFunction:
    """Modbus 功能码"""
    READ_COILS = 0x01           # 读线圈
    READ_DISCRETE = 0x02        # 读离散输入
    READ_HOLDING = 0x03         # 读保持寄存器
    READ_INPUT = 0x04           # 读输入寄存器
    WRITE_SINGLE_COIL = 0x05   # 写单个线圈
    WRITE_SINGLE_REG = 0x06    # 写单个寄存器
    WRITE_MULTI_COIL = 0x0F    # 写多个线圈
    WRITE_MULTI_REG = 0x10     # 写多个寄存器


# 常见 Modbus 寄存器映射 (能源设备)
MODBUS_REGISTER_MAP = {
    "holding": {
        # 保持寄存器 (FC03)
        0: {"name": "设备状态", "metric": "device_status", "unit": "", "scale": 1},
        1: {"name": "运行模式", "metric": "run_mode", "unit": "", "scale": 1},
        100: {"name": "有功功率", "metric": "active_power", "unit": "kW", "scale": 0.1},
        102: {"name": "无功功率", "metric": "reactive_power", "unit": "kvar", "scale": 0.1},
        104: {"name": "功率因数", "metric": "power_factor", "unit": "", "scale": 0.01},
        200: {"name": "A相电压", "metric": "voltage_a", "unit": "V", "scale": 0.1},
        202: {"name": "B相电压", "metric": "voltage_b", "unit": "V", "scale": 0.1},
        204: {"name": "C相电压", "metric": "voltage_c", "unit": "V", "scale": 0.1},
        300: {"name": "A相电流", "metric": "current_a", "unit": "A", "scale": 0.01},
        302: {"name": "B相电流", "metric": "current_b", "unit": "A", "scale": 0.01},
        304: {"name": "C相电流", "metric": "current_c", "unit": "A", "scale": 0.01},
        400: {"name": "频率", "metric": "frequency", "unit": "Hz", "scale": 0.01},
        500: {"name": "温度", "metric": "temperature", "unit": "°C", "scale": 0.1},
        502: {"name": "湿度", "metric": "humidity", "unit": "%RH", "scale": 0.1},
        600: {"name": "风速", "metric": "wind_speed", "unit": "m/s", "scale": 0.01},
        602: {"name": "风向", "metric": "wind_direction", "unit": "°", "scale": 0.1},
        700: {"name": "辐照度", "metric": "irradiance", "unit": "W/m²", "scale": 1},
    },
    "input": {
        # 输入寄存器 (FC04)
        0: {"name": "累计发电量高字", "metric": "energy_high", "unit": "kWh", "scale": 1},
        1: {"name": "累计发电量低字", "metric": "energy_low", "unit": "kWh", "scale": 1},
        10: {"name": "日发电量", "metric": "daily_energy", "unit": "kWh", "scale": 0.01},
        20: {"name": "故障码", "metric": "fault_code", "unit": "", "scale": 1},
        30: {"name": "告警码", "metric": "alarm_code", "unit": "", "scale": 1},
    },
}


class ModbusAdapter(ProtocolAdapter):
    """
    Modbus TCP/RTU 协议适配器

    实现 Modbus 协议数据读取，将 PLC、传感器、变频器等设备的采集数据
    转换为标准 MQTT 消息格式上报。

    连接配置示例:
    {
        "host": "192.168.1.100",
        "port": 502,
        "auth": {
            "unit_id": 1,
            "protocol": "tcp",
            "registers": [
                {"function": 3, "address": 100, "count": 4, "name": "power"},
                {"function": 4, "address": 0, "count": 2, "name": "energy"}
            ]
        }
    }
    """

    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self._unit_id: int = 1
        self._register_configs: list[dict] = []

    def validate_config(self) -> list[str]:
        """验证 Modbus 连接配置"""
        errors: list[str] = []

        if not self._config.host:
            errors.append("Modbus 设备地址不能为空")
        if self._config.port <= 0 or self._config.port > 65535:
            errors.append(f"Modbus 端口无效: {self._config.port}")

        auth = self._config.auth or {}
        unit_id = auth.get("unit_id", 1)
        if not (1 <= unit_id <= 247):
            errors.append(f"Modbus Unit ID 无效: {unit_id}，有效范围: 1-247")

        protocol = auth.get("protocol", "tcp")
        if protocol not in ("tcp", "rtu"):
            errors.append(f"不支持的 Modbus 协议: {protocol}，支持: tcp/rtu")

        return errors

    async def connect(self) -> bool:
        """
        建立 Modbus 连接

        对于 TCP 模式，建立到设备的 TCP 连接。
        对于 RTU 模式，打开串口连接。
        """
        errors = self.validate_config()
        if errors:
            logger.error(f"Modbus 配置验证失败: {errors}")
            self._error_count += 1
            return False

        try:
            auth = self._config.auth or {}
            self._unit_id = auth.get("unit_id", 1)
            protocol = auth.get("protocol", "tcp")

            # 获取寄存器配置
            self._register_configs = auth.get("registers", [])
            if not self._register_configs:
                # 默认读取前8个保持寄存器
                self._register_configs = [
                    {"function": ModbusFunction.READ_HOLDING, "address": 100, "count": 4, "name": "power"},
                    {"function": ModbusFunction.READ_HOLDING, "address": 200, "count": 2, "name": "voltage"},
                    {"function": ModbusFunction.READ_INPUT, "address": 0, "count": 2, "name": "energy"},
                ]

            # 模拟连接
            logger.info(
                f"Modbus {protocol.upper()} 连接中: {self._config.host}:{self._config.port}, "
                f"unit_id={self._unit_id}"
            )

            self._connected = True
            self.device_did = self._config.device_address or f"modbus-{self._config.host}-{self._unit_id}"
            self._error_count = 0
            logger.info(f"Modbus 连接成功: device={self.device_did}")
            return True

        except Exception as e:
            logger.error(f"Modbus 连接失败: {e}")
            self._connected = False
            self._error_count += 1
            return False

    async def disconnect(self) -> None:
        """断开 Modbus 连接"""
        self._connected = False
        logger.info(f"Modbus 已断开: device={self.device_did}")

    async def read_data(self) -> list[DeviceDataPoint]:
        """
        读取 Modbus 设备数据

        按配置的寄存器列表读取数据，支持多种功能码。
        """
        if not self._connected:
            logger.warning("Modbus 未连接，无法读取数据")
            return []

        now = datetime.now(timezone.utc)
        data_points: list[DeviceDataPoint] = []

        for reg_config in self._register_configs:
            func_code = reg_config.get("function", ModbusFunction.READ_HOLDING)
            address = reg_config.get("address", 0)
            count = reg_config.get("count", 1)
            reg_name = reg_config.get("name", f"reg_{address}")

            # 读取寄存器值
            values = self._read_registers(func_code, address, count)

            # 映射到已知寄存器定义
            register_map = (
                MODBUS_REGISTER_MAP["holding"]
                if func_code in (ModbusFunction.READ_HOLDING, ModbusFunction.WRITE_SINGLE_REG)
                else MODBUS_REGISTER_MAP["input"]
            )

            for i, value in enumerate(values):
                reg_addr = address + i
                reg_def = register_map.get(reg_addr)
                if reg_def:
                    scaled_value = round(value * reg_def["scale"], 4)
                    data_points.append(DeviceDataPoint(
                        device_did=self.device_did,
                        protocol=ProtocolType.MODBUS,
                        metric_name=reg_def["metric"],
                        metric_value=scaled_value,
                        unit=reg_def["unit"],
                        timestamp=now,
                        quality="good",
                        metadata={
                            "function_code": func_code,
                            "register_address": reg_addr,
                            "raw_value": value,
                            "register_name": reg_def["name"],
                        },
                    ))
                else:
                    # 未映射的寄存器，使用原始值
                    data_points.append(DeviceDataPoint(
                        device_did=self.device_did,
                        protocol=ProtocolType.MODBUS,
                        metric_name=f"{reg_name}_reg{reg_addr}",
                        metric_value=value,
                        unit="",
                        timestamp=now,
                        quality="good",
                        metadata={
                            "function_code": func_code,
                            "register_address": reg_addr,
                            "raw_value": value,
                        },
                    ))

        logger.debug(f"Modbus 读取完成: {len(data_points)} 数据点, device={self.device_did}")
        return data_points

    def _read_registers(self, function_code: int, address: int, count: int) -> list[int]:
        """
        读取 Modbus 寄存器 (模拟)

        实际应使用 pymodbus 库:
        client.read_holding_registers(address, count, unit=unit_id)

        Args:
            function_code: 功能码
            address: 起始地址
            count: 寄存器数量

        Returns:
            寄存器值列表
        """
        values = []
        for i in range(count):
            reg_addr = address + i
            register_map = (
                MODBUS_REGISTER_MAP["holding"]
                if function_code in (ModbusFunction.READ_HOLDING, ModbusFunction.WRITE_SINGLE_REG)
                else MODBUS_REGISTER_MAP["input"]
            )
            reg_def = register_map.get(reg_addr)

            if reg_def:
                metric = reg_def["metric"]
                scale = reg_def["scale"]
                if "energy" in metric:
                    values.append(int(random.uniform(100000, 500000) / scale))
                elif "voltage" in metric:
                    values.append(int(random.uniform(218, 224) / scale))
                elif "current" in metric:
                    values.append(int(random.uniform(5, 100) / scale))
                elif "power" in metric and "factor" not in metric:
                    values.append(int(random.uniform(10, 500) / scale))
                elif "frequency" in metric:
                    values.append(int(random.uniform(49.9, 50.1) / scale))
                elif "factor" in metric:
                    values.append(int(random.uniform(0.85, 1.0) / scale))
                elif "temperature" in metric:
                    values.append(int(random.uniform(20, 45) / scale))
                elif "wind" in metric and "direction" in metric:
                    values.append(int(random.uniform(0, 360) / scale))
                elif "wind" in metric:
                    values.append(int(random.uniform(0, 25) / scale))
                elif "irradiance" in metric:
                    values.append(int(random.uniform(0, 1200) / scale))
                else:
                    values.append(random.randint(0, 65535))
            else:
                values.append(random.randint(0, 65535))

        return values


# 注册到工厂
ProtocolAdapterFactory.register(ProtocolType.MODBUS, ModbusAdapter)
