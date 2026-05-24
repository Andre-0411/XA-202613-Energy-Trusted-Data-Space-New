"""
MQTT 数据采集服务
基于现有 mqtt_simulator 和 mqtt_data_store，提供高级采集功能
包括：5大发电集团设备模拟、数据分类、质量标记
"""
import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from app.services.mqtt_data_store import mqtt_data_store
from app.services.mqtt_simulator import mqtt_simulator, DEVICE_CONFIGS

logger = logging.getLogger(__name__)

# 5大发电集团设备配置（扩展）
ENTERPRISE_DEVICE_CONFIGS = [
    # 华能集团
    {
        "did": "did:fisco:huaneng_wind_001",
        "name": "华能集团-锡林郭勒风场-01号风机",
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
        "did": "did:fisco:huaneng_solar_001",
        "name": "华能集团-敦煌光伏-01号电站",
        "type": "solar_panel",
        "enterprise": "华能集团",
        "location": "甘肃敦煌",
        "capacity_kw": 80000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 80000), "critical": True},
            "irradiance": {"unit": "W/m²", "range": (0, 1200), "critical": True},
            "panel_temperature": {"unit": "°C", "range": (-10, 85), "critical": True},
            "voltage": {"unit": "V", "range": (0, 1000), "critical": False},
            "current": {"unit": "A", "range": (0, 100), "critical": False},
        },
    },
    # 大唐集团
    {
        "did": "did:fisco:datang_wind_001",
        "name": "大唐集团-赤峰风场-01号风机",
        "type": "wind_turbine",
        "enterprise": "大唐集团",
        "location": "内蒙古赤峰",
        "capacity_kw": 2500,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 2500), "critical": True},
            "wind_speed": {"unit": "m/s", "range": (0, 28), "critical": True},
            "rotation_speed": {"unit": "rpm", "range": (0, 18), "critical": False},
            "temperature": {"unit": "°C", "range": (-25, 75), "critical": True},
            "vibration": {"unit": "mm/s", "range": (0, 12), "critical": False},
        },
    },
    # 华电集团
    {
        "did": "did:fisco:huadian_wind_001",
        "name": "华电集团-张北风场-01号风机",
        "type": "wind_turbine",
        "enterprise": "华电集团",
        "location": "河北张北",
        "capacity_kw": 3000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 3000), "critical": True},
            "wind_speed": {"unit": "m/s", "range": (0, 30), "critical": True},
            "rotation_speed": {"unit": "rpm", "range": (0, 16), "critical": False},
            "temperature": {"unit": "°C", "range": (-30, 70), "critical": True},
            "vibration": {"unit": "mm/s", "range": (0, 15), "critical": False},
        },
    },
    # 国家能源集团
    {
        "did": "did:fisco:chnenergy_solar_001",
        "name": "国家能源集团-格尔木光伏-01号电站",
        "type": "solar_panel",
        "enterprise": "国家能源集团",
        "location": "青海格尔木",
        "capacity_kw": 100000,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 100000), "critical": True},
            "irradiance": {"unit": "W/m²", "range": (0, 1300), "critical": True},
            "panel_temperature": {"unit": "°C", "range": (-15, 90), "critical": True},
            "voltage": {"unit": "V", "range": (0, 1200), "critical": False},
            "current": {"unit": "A", "range": (0, 120), "critical": False},
        },
    },
    # 国电投
    {
        "did": "did:fisco:spic_wind_001",
        "name": "国电投-酒泉风场-01号风机",
        "type": "wind_turbine",
        "enterprise": "国电投",
        "location": "甘肃酒泉",
        "capacity_kw": 3500,
        "data_types": {
            "power_output": {"unit": "kWh", "range": (0, 3500), "critical": True},
            "wind_speed": {"unit": "m/s", "range": (0, 32), "critical": True},
            "rotation_speed": {"unit": "rpm", "range": (0, 15), "critical": False},
            "temperature": {"unit": "°C", "range": (-35, 65), "critical": True},
            "vibration": {"unit": "mm/s", "range": (0, 18), "critical": False},
        },
    },
]


class MqttCollector:
    """MQTT 数据采集服务"""

    def __init__(self):
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._device_configs = {d["did"]: d for d in ENTERPRISE_DEVICE_CONFIGS}
        self._collection_stats = {
            "total_collected": 0,
            "by_enterprise": {},
            "by_device_type": {},
            "last_collection_time": None,
        }

    async def start_collection(self) -> dict:
        """启动采集服务"""
        if self._running:
            return {"status": "already_running", "message": "采集服务已在运行"}

        self._running = True

        # 注册所有设备到数据存储
        for config in ENTERPRISE_DEVICE_CONFIGS:
            await mqtt_data_store.register_device(config["did"], {
                "name": config["name"],
                "type": config["type"],
                "enterprise": config["enterprise"],
                "location": config["location"],
                "capacity_kw": config["capacity_kw"],
            })

        # 启动数据采集任务
        self._tasks = [
            asyncio.create_task(self._collect_device_data(config))
            for config in ENTERPRISE_DEVICE_CONFIGS
        ]
        # 启动心跳任务
        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
        # 启动统计任务
        self._tasks.append(asyncio.create_task(self._stats_update_loop()))

        logger.info(f"采集服务已启动，设备数: {len(ENTERPRISE_DEVICE_CONFIGS)}")

        return {
            "status": "started",
            "device_count": len(ENTERPRISE_DEVICE_CONFIGS),
            "enterprises": list(set(d["enterprise"] for d in ENTERPRISE_DEVICE_CONFIGS)),
        }

    async def stop_collection(self) -> dict:
        """停止采集服务"""
        if not self._running:
            return {"status": "not_running", "message": "采集服务未运行"}

        self._running = False

        # 取消所有任务
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

        logger.info("采集服务已停止")
        return {"status": "stopped"}

    async def get_collection_status(self) -> dict:
        """获取采集状态"""
        stats = await mqtt_data_store.get_statistics()
        return {
            "running": self._running,
            "device_count": len(self._device_configs),
            "collection_stats": self._collection_stats,
            "data_store_stats": stats,
        }

    async def get_devices_by_enterprise(self, enterprise: Optional[str] = None) -> list[dict]:
        """按企业获取设备列表"""
        devices = await mqtt_data_store.get_devices()
        if enterprise:
            devices = [d for d in devices if d.get("enterprise") == enterprise]
        return devices

    async def get_device_data(
        self,
        device_did: str,
        data_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """获取设备数据"""
        return await mqtt_data_store.get_device_history(
            device_did=device_did,
            data_type=data_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def get_enterprise_statistics(self) -> dict:
        """获取各企业统计"""
        devices = await mqtt_data_store.get_devices()
        stats = {}

        for device in devices:
            enterprise = device.get("enterprise", "未知")
            if enterprise not in stats:
                stats[enterprise] = {
                    "device_count": 0,
                    "online_count": 0,
                    "total_capacity_kw": 0,
                    "device_types": {},
                }
            stats[enterprise]["device_count"] += 1
            if device.get("status") == "online":
                stats[enterprise]["online_count"] += 1
            stats[enterprise]["total_capacity_kw"] += device.get("capacity_kw", 0)

            device_type = device.get("type", "unknown")
            stats[enterprise]["device_types"][device_type] = \
                stats[enterprise]["device_types"].get(device_type, 0) + 1

        return stats

    async def get_realtime_data(self, limit_per_device: int = 10) -> dict:
        """获取实时数据快照"""
        devices = await mqtt_data_store.get_devices()
        result = {}

        for device in devices:
            device_did = device["did"]
            latest = await mqtt_data_store.get_device_latest(device_did)
            if latest:
                result[device_did] = {
                    "device_info": device,
                    "latest_data": latest,
                }

        return result

    async def _collect_device_data(self, config: dict) -> None:
        """采集单个设备数据"""
        device_did = config["did"]
        data_types = config["data_types"]

        while self._running:
            try:
                # 核心数据每2秒采集
                critical_types = [k for k, v in data_types.items() if v.get("critical")]
                for data_type in critical_types:
                    values = self._generate_values(data_type, data_types[data_type], config)
                    timestamp = datetime.now(timezone.utc).isoformat()

                    await mqtt_data_store.store_data(
                        device_did, data_type, values, timestamp,
                        signature=f"sig-{uuid.uuid4().hex[:16]}"
                    )

                    # 更新统计
                    self._collection_stats["total_collected"] += 1
                    enterprise = config["enterprise"]
                    self._collection_stats["by_enterprise"][enterprise] = \
                        self._collection_stats["by_enterprise"].get(enterprise, 0) + 1
                    device_type = config["type"]
                    self._collection_stats["by_device_type"][device_type] = \
                        self._collection_stats["by_device_type"].get(device_type, 0) + 1

                await asyncio.sleep(2)

                # 非核心数据每10分钟采集
                if int(datetime.now().timestamp()) % 600 == 0:
                    non_critical_types = [k for k, v in data_types.items() if not v.get("critical")]
                    for data_type in non_critical_types:
                        values = self._generate_values(data_type, data_types[data_type], config)
                        timestamp = datetime.now(timezone.utc).isoformat()

                        await mqtt_data_store.store_data(
                            device_did, data_type, values, timestamp,
                            signature=f"sig-{uuid.uuid4().hex[:16]}"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"采集错误 {device_did}: {e}")
                await asyncio.sleep(2)

    def _generate_values(self, data_type: str, config: dict, device_config: dict) -> dict:
        """生成模拟数据值"""
        low, high = config["range"]
        enterprise = device_config.get("enterprise", "")

        # 根据企业特点调整数据
        enterprise_factor = {
            "华能集团": 1.0,
            "大唐集团": 0.95,
            "华电集团": 0.98,
            "国家能源集团": 1.02,
            "国电投": 0.97,
        }.get(enterprise, 1.0)

        if data_type == "power_output":
            hour = datetime.now().hour
            if 6 <= hour <= 18:
                base = (high - low) * 0.7 * enterprise_factor
            else:
                base = (high - low) * 0.1 * enterprise_factor
            value = base + random.uniform(-base * 0.1, base * 0.1)
        elif data_type == "wind_speed":
            value = random.uniform(2, 15) * enterprise_factor
        elif data_type == "temperature":
            value = random.uniform(15, 45)
        elif data_type == "irradiance":
            hour = datetime.now().hour
            if 6 <= hour <= 18:
                base = high * 0.8 * enterprise_factor
            else:
                base = 0
            value = base + random.uniform(-base * 0.1, base * 0.1)
        else:
            value = random.uniform(low, high) * enterprise_factor

        return {data_type: round(value, 2), "unit": config["unit"]}

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            try:
                for config in ENTERPRISE_DEVICE_CONFIGS:
                    await mqtt_data_store.update_heartbeat(config["did"])
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳错误: {e}")
                await asyncio.sleep(5)

    async def _stats_update_loop(self) -> None:
        """统计更新循环"""
        while self._running:
            try:
                self._collection_stats["last_collection_time"] = \
                    datetime.now(timezone.utc).isoformat()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"统计更新错误: {e}")
                await asyncio.sleep(5)


# 全局采集器实例
mqtt_collector = MqttCollector()
