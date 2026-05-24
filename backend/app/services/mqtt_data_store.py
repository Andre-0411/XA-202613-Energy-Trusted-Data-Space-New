"""
MQTT 采集数据持久化存储层
使用 PostgreSQL 数据库存储设备数据、告警和统计信息
提供按设备/数据类型索引、时间范围查询和统计功能
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.mqtt_data_model import MqttDevice, MqttDataRecord, MqttAlarm

logger = logging.getLogger(__name__)

# 内存缓存大小限制
CACHE_MAX_SIZE = 1000


class MqttDataStore:
    """MQTT 采集数据持久化存储"""

    def __init__(self):
        # 内存缓存：{device_did: {data_type: deque}} 用于快速访问最近数据
        self._cache: dict[str, dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=CACHE_MAX_SIZE))
        )
        # 统计计数器（内存缓存）
        self._stats = {
            "total_messages": 0,
            "total_alarms": 0,
            "start_time": None,
            "last_message_time": None,
        }
        self._lock = asyncio.Lock()

    async def register_device(self, device_did: str, device_info: dict) -> None:
        """注册设备"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                # 检查设备是否已存在
                result = await session.execute(
                    select(MqttDevice).where(MqttDevice.device_did == device_did)
                )
                device = result.scalar_one_or_none()

                if device:
                    # 更新现有设备
                    for key, value in device_info.items():
                        if hasattr(device, key) and key not in ("id", "device_did", "created_at", "updated_at"):
                            setattr(device, key, value)
                    device.status = "online"
                    device.last_heartbeat = datetime.now(timezone.utc)
                else:
                    # 创建新设备
                    device = MqttDevice(
                        device_did=device_did,
                        name=device_info.get("name"),
                        device_type=device_info.get("type"),
                        enterprise=device_info.get("enterprise"),
                        location=device_info.get("location"),
                        capacity_kw=device_info.get("capacity_kw"),
                        status="online",
                        last_heartbeat=datetime.now(timezone.utc),
                        device_metadata=device_info,
                    )
                    session.add(device)

                await session.commit()
                logger.info(f"设备已注册: {device_did}")

    async def update_heartbeat(self, device_did: str) -> None:
        """更新设备心跳"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(MqttDevice).where(MqttDevice.device_did == device_did)
                )
                device = result.scalar_one_or_none()

                if device:
                    device.last_heartbeat = datetime.now(timezone.utc)
                    device.status = "online"
                    await session.commit()

    async def store_data(
        self,
        device_did: str,
        data_type: str,
        values: dict,
        timestamp: Optional[str] = None,
        signature: str = "",
    ) -> None:
        """存储采集数据"""
        async with self._lock:
            ts = timestamp or datetime.now(timezone.utc).isoformat()
            now = datetime.now(timezone.utc)

            async with AsyncSessionLocal() as session:
                # 确保设备存在
                result = await session.execute(
                    select(MqttDevice).where(MqttDevice.device_did == device_did)
                )
                device = result.scalar_one_or_none()

                if not device:
                    # 自动注册设备
                    device = MqttDevice(
                        device_did=device_did,
                        status="online",
                        last_heartbeat=now,
                    )
                    session.add(device)
                    await session.flush()

                # 存储数据记录
                record = MqttDataRecord(
                    device_id=device.id,
                    device_did=device_did,
                    data_type=data_type,
                    values=values,
                    timestamp=ts,
                    signature=signature,
                )
                session.add(record)
                await session.commit()

                # 更新内存缓存
                cache_record = {
                    "device_did": device_did,
                    "data_type": data_type,
                    "values": values,
                    "timestamp": ts,
                    "signature": signature,
                    "stored_at": now.isoformat(),
                }
                self._cache[device_did][data_type].append(cache_record)

                # 更新统计
                self._stats["total_messages"] += 1
                self._stats["last_message_time"] = ts

    async def store_alarm(
        self,
        device_did: str,
        alarm_type: str,
        message: str,
        severity: str = "warning",
        values: Optional[dict] = None,
    ) -> None:
        """存储告警数据"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                # 查找设备
                result = await session.execute(
                    select(MqttDevice).where(MqttDevice.device_did == device_did)
                )
                device = result.scalar_one_or_none()

                alarm = MqttAlarm(
                    device_id=device.id if device else None,
                    device_did=device_did,
                    alarm_type=alarm_type,
                    message=message,
                    severity=severity,
                    values=values or {},
                    acknowledged=False,
                )
                session.add(alarm)
                await session.commit()

                self._stats["total_alarms"] += 1
                logger.warning(f"告警: {device_did} - {alarm_type}: {message}")

    async def get_device_latest(self, device_did: str) -> dict:
        """获取设备最新数据"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(MqttDevice).where(MqttDevice.device_did == device_did)
                )
                device = result.scalar_one_or_none()

                if not device:
                    return {}

                # 查询每种数据类型的最新记录
                data_types_result = await session.execute(
                    select(MqttDataRecord.data_type)
                    .where(MqttDataRecord.device_did == device_did)
                    .distinct()
                )
                data_types = [row[0] for row in data_types_result.all()]

                result = {}
                for dt in data_types:
                    latest_result = await session.execute(
                        select(MqttDataRecord)
                        .where(
                            and_(
                                MqttDataRecord.device_did == device_did,
                                MqttDataRecord.data_type == dt,
                            )
                        )
                        .order_by(MqttDataRecord.stored_at.desc())
                        .limit(1)
                    )
                    latest = latest_result.scalar_one_or_none()
                    if latest:
                        result[dt] = {
                            "device_did": latest.device_did,
                            "data_type": latest.data_type,
                            "values": latest.values,
                            "timestamp": latest.timestamp,
                            "signature": latest.signature,
                            "stored_at": latest.stored_at.isoformat() if latest.stored_at else None,
                        }

                return result

    async def get_device_history(
        self,
        device_did: str,
        data_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """获取设备历史数据"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                query = select(MqttDataRecord).where(
                    MqttDataRecord.device_did == device_did
                )

                if data_type:
                    query = query.where(MqttDataRecord.data_type == data_type)

                if start_time:
                    query = query.where(MqttDataRecord.timestamp >= start_time)

                if end_time:
                    query = query.where(MqttDataRecord.timestamp <= end_time)

                query = query.order_by(MqttDataRecord.timestamp.desc()).limit(limit)

                result = await session.execute(query)
                records = result.scalars().all()

                return [
                    {
                        "device_did": r.device_did,
                        "data_type": r.data_type,
                        "values": r.values,
                        "timestamp": r.timestamp,
                        "signature": r.signature,
                        "stored_at": r.stored_at.isoformat() if r.stored_at else None,
                    }
                    for r in records
                ]

    async def get_devices(self) -> list[dict]:
        """获取所有已注册设备"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(MqttDevice))
                devices = result.scalars().all()

                return [
                    {
                        "did": d.device_did,
                        "name": d.name,
                        "type": d.device_type,
                        "enterprise": d.enterprise,
                        "location": d.location,
                        "capacity_kw": d.capacity_kw,
                        "status": d.status,
                        "last_heartbeat": d.last_heartbeat.isoformat() if d.last_heartbeat else None,
                        "registered_at": d.created_at.isoformat() if d.created_at else None,
                    }
                    for d in devices
                ]

    async def get_device_info(self, device_did: str) -> Optional[dict]:
        """获取单个设备信息"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(MqttDevice).where(MqttDevice.device_did == device_did)
                )
                device = result.scalar_one_or_none()

                if not device:
                    return None

                return {
                    "did": device.device_did,
                    "name": device.name,
                    "type": device.device_type,
                    "enterprise": device.enterprise,
                    "location": device.location,
                    "capacity_kw": device.capacity_kw,
                    "status": device.status,
                    "last_heartbeat": device.last_heartbeat.isoformat() if device.last_heartbeat else None,
                    "registered_at": device.created_at.isoformat() if device.created_at else None,
                }

    async def get_statistics(self) -> dict:
        """获取采集统计信息"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                # 设备统计
                device_count_result = await session.execute(
                    select(func.count(MqttDevice.id))
                )
                device_count = device_count_result.scalar() or 0

                online_count_result = await session.execute(
                    select(func.count(MqttDevice.id)).where(
                        MqttDevice.status == "online"
                    )
                )
                online_count = online_count_result.scalar() or 0

                # 数据记录统计
                total_records_result = await session.execute(
                    select(func.count(MqttDataRecord.id))
                )
                total_records = total_records_result.scalar() or 0

                # 告警统计
                total_alarms_result = await session.execute(
                    select(func.count(MqttAlarm.id))
                )
                total_alarms = total_alarms_result.scalar() or 0

                # 最近1小时告警数
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                recent_alarms_result = await session.execute(
                    select(func.count(MqttAlarm.id)).where(
                        MqttAlarm.timestamp >= one_hour_ago
                    )
                )
                recent_alarms = recent_alarms_result.scalar() or 0

                # 计算缺失率（简化：基于心跳间隔估算）
                missing_rate = 0.0
                if self._stats["start_time"] and self._stats["total_messages"] > 0:
                    try:
                        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(self._stats["start_time"])).total_seconds()
                        if elapsed > 0:
                            expected = elapsed * device_count
                            if expected > 0:
                                missing_rate = max(0, 1 - (self._stats["total_messages"] / expected))
                    except (ValueError, TypeError):
                        pass

                return {
                    "device_count": device_count,
                    "online_device_count": online_count,
                    "total_messages": self._stats["total_messages"],
                    "total_records": total_records,
                    "total_alarms": total_alarms,
                    "recent_alarms": recent_alarms,
                    "missing_rate": round(missing_rate, 4),
                    "start_time": self._stats["start_time"],
                    "last_message_time": self._stats["last_message_time"],
                }

    async def get_alarms(
        self,
        device_did: Optional[str] = None,
        alarm_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """获取告警列表"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                query = select(MqttAlarm)

                if device_did:
                    query = query.where(MqttAlarm.device_did == device_did)

                if alarm_type:
                    query = query.where(MqttAlarm.alarm_type == alarm_type)

                query = query.order_by(MqttAlarm.timestamp.desc()).limit(limit)

                result = await session.execute(query)
                alarms = result.scalars().all()

                return [
                    {
                        "device_did": a.device_did,
                        "alarm_type": a.alarm_type,
                        "message": a.message,
                        "severity": a.severity,
                        "values": a.values,
                        "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                        "acknowledged": a.acknowledged,
                    }
                    for a in alarms
                ]

    async def get_data_statistics(
        self,
        device_did: str,
        data_type: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> dict:
        """获取数据统计（均值/最大/最小/缺失率）"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                query = select(MqttDataRecord).where(
                    and_(
                        MqttDataRecord.device_did == device_did,
                        MqttDataRecord.data_type == data_type,
                    )
                )

                if start_time:
                    query = query.where(MqttDataRecord.timestamp >= start_time)
                if end_time:
                    query = query.where(MqttDataRecord.timestamp <= end_time)

                result = await session.execute(query)
                records = result.scalars().all()

                if not records:
                    return {"count": 0, "mean": {}, "max": {}, "min": {}, "missing_rate": 1.0}

                # 计算统计值
                all_keys = set()
                for r in records:
                    if r.values:
                        all_keys.update(r.values.keys())

                stats = {"count": len(records), "mean": {}, "max": {}, "min": {}}

                for key in all_keys:
                    values = [r.values.get(key) for r in records if r.values and key in r.values]
                    numeric_values = [v for v in values if isinstance(v, (int, float))]

                    if numeric_values:
                        stats["mean"][key] = round(sum(numeric_values) / len(numeric_values), 4)
                        stats["max"][key] = max(numeric_values)
                        stats["min"][key] = min(numeric_values)

                # 缺失率
                expected_count = len(records)
                actual_count = sum(1 for r in records if r.values)
                stats["missing_rate"] = round(1 - (actual_count / expected_count), 4) if expected_count > 0 else 1.0

                return stats

    async def clear(self) -> None:
        """清空所有数据"""
        async with self._lock:
            async with AsyncSessionLocal() as session:
                # 按顺序删除（外键约束）
                await session.execute(delete(MqttAlarm))
                await session.execute(delete(MqttDataRecord))
                await session.execute(delete(MqttDevice))
                await session.commit()

            # 清空内存缓存
            self._cache.clear()
            self._stats = {
                "total_messages": 0,
                "total_alarms": 0,
                "start_time": None,
                "last_message_time": None,
            }
            logger.info("数据存储已清空")

    def set_start_time(self) -> None:
        """设置启动时间"""
        self._stats["start_time"] = datetime.now(timezone.utc).isoformat()


# 全局数据存储实例
mqtt_data_store = MqttDataStore()
