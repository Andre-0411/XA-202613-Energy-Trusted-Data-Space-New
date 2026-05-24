"""
MQTT 数据存储测试
测试 MQTT 数据持久化存储功能
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio

from app.models.mqtt_data_model import MqttDevice, MqttDataRecord, MqttAlarm


class TestMqttDataStore:
    """MQTT 数据存储测试类"""

    @pytest.mark.asyncio
    async def test_store_initialization(self):
        """测试存储初始化"""
        from app.services.mqtt_data_store import MqttDataStore

        store = MqttDataStore()

        assert store._stats["total_messages"] == 0
        assert store._stats["total_alarms"] == 0
        assert store._stats["start_time"] is None
        assert store._stats["last_message_time"] is None

    @pytest.mark.asyncio
    async def test_set_start_time(self):
        """测试设置启动时间"""
        from app.services.mqtt_data_store import MqttDataStore

        store = MqttDataStore()
        store.set_start_time()

        assert store._stats["start_time"] is not None

    @pytest.mark.asyncio
    async def test_global_instance(self):
        """测试全局实例"""
        from app.services.mqtt_data_store import mqtt_data_store

        assert mqtt_data_store is not None


class TestMqttDataStoreIntegration:
    """MQTT 数据存储集成测试（需要 mock 数据库）"""

    @pytest.mark.asyncio
    async def test_register_device(self):
        """测试注册设备"""
        from app.services.mqtt_data_store import MqttDataStore

        store = MqttDataStore()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()

        device_info = {
            "name": "Test Wind Turbine",
            "type": "wind_turbine",
            "enterprise": "Test Corp",
            "location": "Beijing",
            "capacity_kw": 1000.0,
        }

        with patch("app.services.mqtt_data_store.AsyncSessionLocal") as mock_local:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

            await store.register_device("test_device_001", device_info)

            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_data(self):
        """测试存储数据"""
        from app.services.mqtt_data_store import MqttDataStore

        store = MqttDataStore()
        mock_session = MagicMock()

        # Mock 设备查询
        mock_device = MagicMock()
        mock_device.id = uuid.uuid4()
        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = mock_device

        mock_session.execute = AsyncMock(return_value=mock_device_result)
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()

        values = {"power_output": 500.5, "wind_speed": 12.3}
        timestamp = datetime.now(timezone.utc).isoformat()

        with patch("app.services.mqtt_data_store.AsyncSessionLocal") as mock_local:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

            await store.store_data("test_device_001", "power_output", values, timestamp)

            assert store._stats["total_messages"] == 1
            assert store._stats["last_message_time"] == timestamp
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_alarm(self):
        """测试存储告警"""
        from app.services.mqtt_data_store import MqttDataStore

        store = MqttDataStore()
        mock_session = MagicMock()

        # Mock 设备查询
        mock_device = MagicMock()
        mock_device.id = uuid.uuid4()
        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = mock_device

        mock_session.execute = AsyncMock(return_value=mock_device_result)
        mock_session.commit = AsyncMock()

        with patch("app.services.mqtt_data_store.AsyncSessionLocal") as mock_local:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

            await store.store_alarm(
                "test_device_001",
                "high_temperature",
                "Temperature exceeded 80°C",
                "warning",
                {"temperature": 85.5},
            )

            assert store._stats["total_alarms"] == 1
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device_latest(self):
        """测试获取设备最新数据"""
        from app.services.mqtt_data_store import MqttDataStore

        store = MqttDataStore()
        mock_session = MagicMock()

        # Mock 设备查询
        mock_device = MagicMock()
        mock_device.id = uuid.uuid4()
        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = mock_device

        # Mock 数据类型查询
        mock_types_result = MagicMock()
        mock_types_result.all.return_value = [("power_output",)]

        # Mock 最新记录查询
        mock_record = MagicMock()
        mock_record.device_did = "test_device_001"
        mock_record.data_type = "power_output"
        mock_record.values = {"power": 500}
        mock_record.timestamp = datetime.now(timezone.utc).isoformat()
        mock_record.signature = ""
        mock_record.stored_at = datetime.now(timezone.utc)

        mock_latest_result = MagicMock()
        mock_latest_result.scalar_one_or_none.return_value = mock_record

        # 配置 execute 返回不同结果
        call_count = 0
        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_device_result
            elif call_count == 2:
                return mock_types_result
            else:
                return mock_latest_result

        mock_session.execute = mock_execute

        with patch("app.services.mqtt_data_store.AsyncSessionLocal") as mock_local:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await store.get_device_latest("test_device_001")

            assert "power_output" in result
            assert result["power_output"]["values"] == {"power": 500}

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空数据"""
        from app.services.mqtt_data_store import MqttDataStore

        store = MqttDataStore()
        store._stats["total_messages"] = 100
        store._stats["total_alarms"] = 5

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("app.services.mqtt_data_store.AsyncSessionLocal") as mock_local:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

            await store.clear()

            assert store._stats["total_messages"] == 0
            assert store._stats["total_alarms"] == 0
            assert store._stats["start_time"] is None
