"""
MQTT 数据采集模拟器
模拟能源设备数据上报，支持断线续传和异常注入
"""
import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt

from app.config import settings
from app.services.mqtt_data_store import mqtt_data_store

logger = logging.getLogger(__name__)

# 设备配置
DEVICE_CONFIGS = [
    # 风力发电机组 (3个)
    {
        "did": "did:fisco:wind_farm_001",
        "name": "华能风场-01号风机",
        "type": "wind_turbine",
        "enterprise": "华能集团",
        "location": "内蒙古锡林郭勒",
        "capacity_kw": 2000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 2000), "critical": True},
            "wind_speed": {"unit": "m/s", "range": (0, 25), "critical": True},
            "rotation_speed": {"unit": "rpm", "range": (0, 20), "critical": False},
            "temperature": {"unit": "°C", "range": (-20, 80), "critical": True},
            "vibration": {"unit": "mm/s", "range": (0, 10), "critical": False},
        },
    },
    {
        "did": "did:fisco:wind_farm_002",
        "name": "华能风场-02号风机",
        "type": "wind_turbine",
        "enterprise": "华能集团",
        "location": "内蒙古锡林郭勒",
        "capacity_kw": 2000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 2000), "critical": True},
            "wind_speed": {"unit": "m/s", "range": (0, 25), "critical": True},
            "rotation_speed": {"unit": "rpm", "range": (0, 20), "critical": False},
            "temperature": {"unit": "°C", "range": (-20, 80), "critical": True},
            "vibration": {"unit": "mm/s", "range": (0, 10), "critical": False},
        },
    },
    {
        "did": "did:fisco:wind_farm_003",
        "name": "龙源风场-01号风机",
        "type": "wind_turbine",
        "enterprise": "龙源电力",
        "location": "甘肃酒泉",
        "capacity_kw": 3000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 3000), "critical": True},
            "wind_speed": {"unit": "m/s", "range": (0, 30), "critical": True},
            "rotation_speed": {"unit": "rpm", "range": (0, 18), "critical": False},
            "temperature": {"unit": "°C", "range": (-30, 70), "critical": True},
            "vibration": {"unit": "mm/s", "range": (0, 12), "critical": False},
        },
    },
    # 光伏发电站 (2个)
    {
        "did": "did:fisco:solar_plant_001",
        "name": "中广核光伏-01号电站",
        "type": "solar_panel",
        "enterprise": "中广核",
        "location": "青海格尔木",
        "capacity_kw": 50000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 50000), "critical": True},
            "irradiance": {"unit": "W/m²", "range": (0, 1200), "critical": True},
            "panel_temperature": {"unit": "°C", "range": (-10, 85), "critical": True},
            "voltage": {"unit": "V", "range": (0, 1000), "critical": False},
            "current": {"unit": "A", "range": (0, 100), "critical": False},
        },
    },
    {
        "did": "did:fisco:solar_plant_002",
        "name": "三峡光伏-01号电站",
        "type": "solar_panel",
        "enterprise": "三峡集团",
        "location": "宁夏中卫",
        "capacity_kw": 100000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 100000), "critical": True},
            "irradiance": {"unit": "W/m²", "range": (0, 1200), "critical": True},
            "panel_temperature": {"unit": "°C", "range": (-10, 85), "critical": True},
            "voltage": {"unit": "V", "range": (0, 1000), "critical": False},
            "current": {"unit": "A", "range": (0, 100), "critical": False},
        },
    },
]


class MqttSimulator:
    """MQTT 数据采集模拟器"""

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._offline_buffer: list[dict] = []  # 离线缓存
        self._connected = False
        self._reconnect_count = 0
        self._device_configs = {d["did"]: d for d in DEVICE_CONFIGS}

    async def start(self) -> dict:
        """启动模拟器"""
        if self._running:
            return {"status": "already_running", "message": "模拟器已在运行"}

        self._running = True
        mqtt_data_store.set_start_time()

        # 注册所有设备
        for config in DEVICE_CONFIGS:
            await mqtt_data_store.register_device(config["did"], {
                "name": config["name"],
                "type": config["type"],
                "enterprise": config["enterprise"],
                "location": config["location"],
                "capacity_kw": config["capacity_kw"],
            })

        # 尝试连接 MQTT Broker
        connected = await self._connect_mqtt()

        # 启动数据生成任务
        self._tasks = [
            asyncio.create_task(self._generate_device_data(config))
            for config in DEVICE_CONFIGS
        ]
        # 启动心跳任务
        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
        # 启动告警注入任务
        self._tasks.append(asyncio.create_task(self._alarm_injection_loop()))
        # 启动离线缓存刷新任务
        if connected:
            self._tasks.append(asyncio.create_task(self._flush_offline_buffer()))

        mode = "mqtt" if connected else "memory"
        logger.info(f"模拟器已启动，模式: {mode}，设备数: {len(DEVICE_CONFIGS)}")

        return {
            "status": "started",
            "mode": mode,
            "device_count": len(DEVICE_CONFIGS),
            "devices": [d["did"] for d in DEVICE_CONFIGS],
        }

    async def stop(self) -> dict:
        """停止模拟器"""
        if not self._running:
            return {"status": "not_running", "message": "模拟器未运行"}

        self._running = False

        # 取消所有任务
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

        # 断开 MQTT
        await self._disconnect_mqtt()

        logger.info("模拟器已停止")
        return {"status": "stopped"}

    async def get_status(self) -> dict:
        """获取模拟器状态"""
        stats = await mqtt_data_store.get_statistics()
        return {
            "running": self._running,
            "connected": self._connected,
            "mode": "mqtt" if self._connected else "memory",
            "device_count": len(self._device_configs),
            "offline_buffer_size": len(self._offline_buffer),
            "reconnect_count": self._reconnect_count,
            **stats,
        }

    async def inject_alarm(
        self,
        device_did: str,
        alarm_type: str,
        message: str,
        severity: str = "warning",
    ) -> dict:
        """手动注入告警"""
        if device_did not in self._device_configs:
            return {"success": False, "message": f"设备不存在: {device_did}"}

        await mqtt_data_store.store_alarm(device_did, alarm_type, message, severity)

        # 如果 MQTT 已连接，也发布告警
        if self._connected and self.client:
            alarm_topic = f"energy/alarm/{device_did}/{alarm_type}"
            alarm_payload = json.dumps({
                "device_did": device_did,
                "alarm_type": alarm_type,
                "message": message,
                "severity": severity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self.client.publish(alarm_topic, alarm_payload, qos=1)

        return {"success": True, "message": f"告警已注入: {device_did} - {alarm_type}"}

    async def _connect_mqtt(self) -> bool:
        """连接 MQTT Broker"""
        try:
            self.client = mqtt.Client(
                client_id=f"simulator-{uuid.uuid4().hex[:8]}",
                protocol=mqtt.MQTTv5,
            )
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            broker_host = settings.MQTT_BROKER.replace("tcp://", "").split(":")[0]
            broker_port = 1883

            self.client.connect(broker_host, broker_port, keepalive=60)
            self.client.loop_start()

            # 等待连接结果
            for _ in range(10):
                if self._connected:
                    return True
                await asyncio.sleep(0.5)

            logger.warning("MQTT Broker 连接超时，降级为内存模式")
            return False

        except Exception as e:
            logger.warning(f"MQTT 连接失败: {e}，降级为内存模式")
            return False

    async def _disconnect_mqtt(self) -> None:
        """断开 MQTT"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        """MQTT 连接回调"""
        if rc == 0:
            self._connected = True
            logger.info("模拟器 MQTT 连接成功")
        else:
            logger.error(f"模拟器 MQTT 连接失败: {rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None) -> None:
        """MQTT 断开回调"""
        self._connected = False
        self._reconnect_count += 1
        if rc != 0:
            logger.warning(f"模拟器 MQTT 断开: {rc}，将尝试重连")

    async def _generate_device_data(self, config: dict) -> None:
        """生成设备数据"""
        device_did = config["did"]
        data_types = config["data_types"]

        while self._running:
            try:
                # 核心数据每1秒
                critical_types = [k for k, v in data_types.items() if v.get("critical")]
                for data_type in critical_types:
                    values = self._generate_values(data_type, data_types[data_type])
                    timestamp = datetime.now(timezone.utc).isoformat()

                    record = {
                        "device_did": device_did,
                        "data_type": data_type,
                        "values": values,
                        "timestamp": timestamp,
                        "signature": f"sig-{uuid.uuid4().hex[:16]}",  # 模拟签名
                    }

                    # 存入内存
                    await mqtt_data_store.store_data(
                        device_did, data_type, values, timestamp, record["signature"]
                    )

                    # 发布到 MQTT 或缓存
                    await self._publish_or_buffer(record)

                await asyncio.sleep(1)

                # 非核心数据每5分钟（简化：每300秒生成一次）
                if int(time.time()) % 300 == 0:
                    non_critical_types = [k for k, v in data_types.items() if not v.get("critical")]
                    for data_type in non_critical_types:
                        values = self._generate_values(data_type, data_types[data_type])
                        timestamp = datetime.now(timezone.utc).isoformat()

                        record = {
                            "device_did": device_did,
                            "data_type": data_type,
                            "values": values,
                            "timestamp": timestamp,
                            "signature": f"sig-{uuid.uuid4().hex[:16]}",
                        }

                        await mqtt_data_store.store_data(
                            device_did, data_type, values, timestamp, record["signature"]
                        )
                        await self._publish_or_buffer(record)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"数据生成错误 {device_did}: {e}")
                await asyncio.sleep(1)

    def _generate_values(self, data_type: str, config: dict) -> dict:
        """生成模拟数据值"""
        low, high = config["range"]

        # 添加一些随机波动
        if data_type == "power_output":
            # 发电量随时间变化（白天高，晚上低）
            hour = datetime.now().hour
            if 6 <= hour <= 18:
                base = (high - low) * 0.7
            else:
                base = (high - low) * 0.1
            value = base + random.uniform(-base * 0.1, base * 0.1)
        elif data_type == "wind_speed":
            # 风速随机但有一定持续性
            value = random.uniform(2, 15)
        elif data_type == "temperature":
            # 温度在合理范围内波动
            value = random.uniform(15, 45)
        elif data_type == "irradiance":
            # 辐照度随时间变化
            hour = datetime.now().hour
            if 6 <= hour <= 18:
                base = high * 0.8
            else:
                base = 0
            value = base + random.uniform(-base * 0.1, base * 0.1)
        else:
            value = random.uniform(low, high)

        return {data_type: round(value, 2), "unit": config["unit"]}

    async def _publish_or_buffer(self, record: dict) -> None:
        """发布到 MQTT 或存入离线缓存"""
        if self._connected and self.client:
            topic = f"energy/collect/{record['device_did']}/{record['data_type']}"
            payload = json.dumps(record)
            self.client.publish(topic, payload, qos=1)
        else:
            # 离线缓存
            self._offline_buffer.append(record)
            # 限制缓存大小
            if len(self._offline_buffer) > 10000:
                self._offline_buffer = self._offline_buffer[-5000:]

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            try:
                for config in DEVICE_CONFIGS:
                    device_did = config["did"]
                    await mqtt_data_store.update_heartbeat(device_did)

                    if self._connected and self.client:
                        topic = f"energy/heartbeat/{device_did}"
                        payload = json.dumps({
                            "device_did": device_did,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "status": "online",
                        })
                        self.client.publish(topic, payload, qos=0)

                await asyncio.sleep(30)  # 每30秒心跳

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳错误: {e}")
                await asyncio.sleep(5)

    async def _alarm_injection_loop(self) -> None:
        """随机告警注入循环"""
        while self._running:
            try:
                # 随机等待30-300秒
                await asyncio.sleep(random.uniform(30, 300))

                if not self._running:
                    break

                # 随机选择设备和告警类型
                config = random.choice(DEVICE_CONFIGS)
                device_did = config["did"]
                device_type = config["type"]

                if device_type == "wind_turbine":
                    alarm_types = [
                        ("temperature_high", "风机温度过高", "warning"),
                        ("vibration_abnormal", "振动异常", "critical"),
                        ("rotation_speed_low", "转速过低", "warning"),
                        ("power_output_low", "发电量异常偏低", "warning"),
                    ]
                else:
                    alarm_types = [
                        ("panel_temperature_high", "光伏面板温度过高", "warning"),
                        ("voltage_abnormal", "电压异常", "critical"),
                        ("current_abnormal", "电流异常", "warning"),
                        ("irradiance_low", "辐照度过低", "info"),
                    ]

                alarm_type, message, severity = random.choice(alarm_types)
                await mqtt_data_store.store_alarm(device_did, alarm_type, message, severity)

                # 发布告警到 MQTT
                if self._connected and self.client:
                    topic = f"energy/alarm/{device_did}/{alarm_type}"
                    payload = json.dumps({
                        "device_did": device_did,
                        "alarm_type": alarm_type,
                        "message": message,
                        "severity": severity,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    self.client.publish(topic, payload, qos=1)

                logger.info(f"随机告警: {device_did} - {alarm_type}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"告警注入错误: {e}")
                await asyncio.sleep(5)

    async def _flush_offline_buffer(self) -> None:
        """刷新离线缓存"""
        while self._running:
            try:
                await asyncio.sleep(10)

                if not self._offline_buffer or not self._connected:
                    continue

                # 批量发送缓存数据
                buffer_copy = self._offline_buffer.copy()
                self._offline_buffer.clear()

                for record in buffer_copy:
                    if not self._connected:
                        # 重新断连，放回缓存
                        self._offline_buffer.extend(buffer_copy[buffer_copy.index(record):])
                        break

                    topic = f"energy/collect/{record['device_did']}/{record['data_type']}"
                    payload = json.dumps(record)
                    self.client.publish(topic, payload, qos=1)

                logger.info(f"刷新离线缓存: {len(buffer_copy)} 条")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"缓存刷新错误: {e}")
                await asyncio.sleep(5)


# 全局模拟器实例
mqtt_simulator = MqttSimulator()