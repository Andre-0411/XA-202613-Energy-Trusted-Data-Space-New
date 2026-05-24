"""
FATE 集成服务单元测试 (v2 — SQLAlchemy 版本)
测试 fate_integration.py 中的连接管理、作业管理、数据管理、生命周期等功能
已适配 FateJob 数据库模型（替代原 _fate_jobs 字典）
"""
import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.services.fate_integration import (
    ConnectionState,
    ConnectionMetrics,
    check_fate_available,
    get_connection_status,
    submit_job,
    get_job_status,
    get_job_result,
    cancel_job,
    list_jobs,
    upload_data,
    download_data,
    upload_data_from_bytes,
    generate_homo_lr_config,
    generate_hetero_lr_config,
    generate_psi_config,
    cleanup_jobs,
    initialize,
    shutdown,
    reset_fate_availability,
    get_fate_service_info,
    get_fate_client,
    get_job_manager,
    _extract_algorithm_from_config,
    _generate_simulation_metrics,
    _is_circuit_open,
    _close_circuit_breaker,
    _get_http_client,
    _close_http_client,
    _local_simulation_submit,
    _retry_with_backoff,
    _connection_metrics,
    FATE_ALGORITHMS,
    validate_fate_config,
)
import app.services.fate_integration as fate_module


# ==================== 辅助函数 ====================


def _make_valid_config(components=None):
    """生成一个可通过 validate_fate_config 校验的任务配置"""
    if components is None:
        components = ["reader_0", "homo_lr_0"]
    return {
        "dag_name": f"test_{uuid.uuid4().hex[:8]}",
        "dsl_version": 2,
        "initiator": {"role": "guest", "party_id": 9999},
        "role": {"guest": [9999], "host": [10000]},
        "component_parameters": {
            "role": {
                "guest": {
                    "0": {
                        "reader_0": {"table": {"name": "test_data"}},
                    }
                },
                "host": {
                    "0": {
                        "reader_0": {"table": {"name": "test_data"}},
                    }
                },
            }
        },
        "component_list": components,
    }


# ==================== 辅助夹具 ====================


@pytest.fixture(autouse=True)
def reset_global_state():
    """每个测试前后重置全局状态"""
    fate_module._connection_state = ConnectionState.DISCONNECTED
    fate_module._connection_metrics = ConnectionMetrics()
    fate_module._circuit_opened_since = None
    fate_module._http_client = None
    fate_module._health_check_task = None
    fate_module._progress_subscribers.clear()
    yield
    fate_module._connection_state = ConnectionState.DISCONNECTED
    fate_module._connection_metrics = ConnectionMetrics()
    fate_module._circuit_opened_since = None
    fate_module._http_client = None
    fate_module._health_check_task = None
    fate_module._progress_subscribers.clear()


# ==================== 枚举和数据类测试 ====================


class TestConnectionState:
    """测试 ConnectionState 枚举"""

    def test_enum_values(self):
        assert ConnectionState.DISCONNECTED == "disconnected"
        assert ConnectionState.CONNECTING == "connecting"
        assert ConnectionState.CONNECTED == "connected"
        assert ConnectionState.RECONNECTING == "reconnecting"
        assert ConnectionState.CIRCUIT_OPEN == "circuit_open"

    def test_enum_is_str(self):
        assert isinstance(ConnectionState.CONNECTED, str)


class TestConnectionMetrics:
    """测试 ConnectionMetrics 数据类"""

    def test_initial_state(self):
        m = ConnectionMetrics()
        assert m.total_requests == 0
        assert m.successful_requests == 0
        assert m.failed_requests == 0
        assert m.consecutive_failures == 0
        assert m.last_latency_ms == 0.0
        assert m.avg_latency_ms == 0.0
        assert m.last_health_check is None
        assert m.last_failure_time is None
        assert m.last_failure_reason == ""
        assert m.connected_since is None
        assert m.circuit_opened_at is None
        assert m.health_check_history == []

    def test_record_success(self):
        m = ConnectionMetrics()
        m.record_success(150.0)
        assert m.total_requests == 1
        assert m.successful_requests == 1
        assert m.consecutive_failures == 0
        assert m.last_latency_ms == 150.0
        assert m.avg_latency_ms == 150.0

    def test_record_success_sliding_average(self):
        m = ConnectionMetrics()
        m.record_success(100.0)
        m.record_success(200.0)
        assert m.avg_latency_ms == 150.0
        m.record_success(300.0)
        assert m.avg_latency_ms == 200.0

    def test_record_success_resets_consecutive_failures(self):
        m = ConnectionMetrics()
        m.record_failure("error1")
        m.record_failure("error2")
        assert m.consecutive_failures == 2
        m.record_success(50.0)
        assert m.consecutive_failures == 0

    def test_record_failure(self):
        m = ConnectionMetrics()
        m.record_failure("Connection refused")
        assert m.total_requests == 1
        assert m.failed_requests == 1
        assert m.consecutive_failures == 1
        assert m.last_failure_reason == "Connection refused"
        assert m.last_failure_time is not None

    def test_record_health_check_healthy(self):
        m = ConnectionMetrics()
        m.record_health_check(True, 50.0)
        assert m.last_health_check is not None
        assert len(m.health_check_history) == 1
        assert m.health_check_history[0]["healthy"] is True
        assert m.health_check_history[0]["latency_ms"] == 50.0

    def test_record_health_check_unhealthy(self):
        m = ConnectionMetrics()
        m.record_health_check(False)
        assert m.health_check_history[0]["healthy"] is False

    def test_health_check_history_limit(self):
        m = ConnectionMetrics()
        for i in range(60):
            m.record_health_check(True, float(i))
        assert len(m.health_check_history) == 50

    def test_success_rate_empty(self):
        m = ConnectionMetrics()
        assert m.success_rate == 0.0

    def test_success_rate_partial(self):
        m = ConnectionMetrics()
        m.record_success(100.0)
        m.record_failure("error")
        m.record_success(100.0)
        assert abs(m.success_rate - 2 / 3) < 0.001

    def test_to_dict(self):
        m = ConnectionMetrics()
        m.record_success(100.0)
        m.record_health_check(True, 50.0)
        d = m.to_dict()
        assert d["total_requests"] == 1
        assert d["successful_requests"] == 1
        assert d["failed_requests"] == 0
        assert d["success_rate"] == 1.0
        assert d["last_latency_ms"] == 100.0
        assert d["avg_latency_ms"] == 100.0
        assert "recent_health_checks" in d
        assert len(d["recent_health_checks"]) == 1


# ==================== 断路器测试 ====================


class TestCircuitBreaker:
    """测试断路器逻辑"""

    def test_circuit_not_open_initially(self):
        assert _is_circuit_open() is False

    def test_circuit_opens_after_threshold(self):
        for _ in range(5):
            fate_module._connection_metrics.record_failure("test")
        assert _is_circuit_open() is True

    def test_circuit_opens_records_time(self):
        for _ in range(5):
            fate_module._connection_metrics.record_failure("test")
        _is_circuit_open()
        assert fate_module._circuit_opened_since is not None

    def test_circuit_recovery_after_timeout(self):
        for _ in range(5):
            fate_module._connection_metrics.record_failure("test")
        fate_module._circuit_opened_since = time.time() - 120
        assert _is_circuit_open() is False  # 半开探测

    def test_close_circuit_breaker(self):
        fate_module._circuit_opened_since = time.time()
        _close_circuit_breaker()
        assert fate_module._circuit_opened_since is None


# ==================== 健康检查和连接测试 ====================


class TestCheckFateAvailable:
    """测试 check_fate_available"""

    @pytest.mark.asyncio
    async def test_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.FATE_REAL_MODE", True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await check_fate_available()

        assert result is True
        assert fate_module._connection_state == ConnectionState.CONNECTED
        assert fate_module._connection_metrics.successful_requests == 1

    @pytest.mark.asyncio
    async def test_failure_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.FATE_REAL_MODE", True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await check_fate_available()

        assert result is False
        assert fate_module._connection_state == ConnectionState.DISCONNECTED
        assert fate_module._connection_metrics.failed_requests == 1

    @pytest.mark.asyncio
    async def test_failure_connection_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("app.services.fate_integration.FATE_REAL_MODE", True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await check_fate_available()

        assert result is False
        assert fate_module._connection_state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_circuit_open_blocks_request(self):
        for _ in range(5):
            fate_module._connection_metrics.record_failure("test")

        with patch("app.services.fate_integration.FATE_REAL_MODE", True):
            result = await check_fate_available()
        assert result is False
        assert fate_module._connection_state == ConnectionState.CIRCUIT_OPEN

    @pytest.mark.asyncio
    async def test_records_connected_since(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.FATE_REAL_MODE", True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            await check_fate_available()

        assert fate_module._connection_metrics.connected_since is not None

    @pytest.mark.asyncio
    async def test_health_check_history_recorded(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.FATE_REAL_MODE", True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            await check_fate_available()

        assert len(fate_module._connection_metrics.health_check_history) == 1
        assert fate_module._connection_metrics.health_check_history[0]["healthy"] is True


# ==================== HTTP 客户端测试 ====================


class TestHttpClient:
    """测试 HTTP 客户端管理"""

    @pytest.mark.asyncio
    async def test_get_http_client_creates_client(self):
        client = await _get_http_client()
        assert isinstance(client, httpx.AsyncClient)
        assert not client.is_closed

    @pytest.mark.asyncio
    async def test_get_http_client_reuses(self):
        c1 = await _get_http_client()
        c2 = await _get_http_client()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_close_http_client(self):
        await _get_http_client()
        await _close_http_client()
        assert fate_module._http_client is None

    @pytest.mark.asyncio
    async def test_close_http_client_when_none(self):
        fate_module._http_client = None
        await _close_http_client()  # should not raise


# ==================== 连接状态查询测试 ====================


class TestGetConnectionStatus:
    """测试 get_connection_status"""

    def test_returns_proper_structure(self):
        status = get_connection_status()
        assert "state" in status
        assert "fate_flow_url" in status
        assert "metrics" in status
        assert "config" in status

    def test_state_value(self):
        status = get_connection_status()
        assert status["state"] == "disconnected"

    def test_config_keys(self):
        status = get_connection_status()
        config = status["config"]
        assert "health_check_interval" in config
        assert "max_retries" in config
        assert "circuit_breaker_threshold" in config
        assert "circuit_breaker_recovery_timeout" in config
        assert "request_timeout" in config


# ==================== 重试机制测试 ====================


class TestRetryWithBackoff:
    """测试 _retry_with_backoff"""

    @pytest.mark.asyncio
    async def test_success_first_try(self):
        mock_func = AsyncMock(return_value="ok")
        result = await _retry_with_backoff(mock_func)
        assert result == "ok"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_connect_error(self):
        mock_func = AsyncMock(side_effect=[httpx.ConnectError("fail"), "ok"])
        with patch("app.services.fate_integration.RETRY_BACKOFF_BASE", 0.01):
            result = await _retry_with_backoff(mock_func, max_retries=2)
        assert result == "ok"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        mock_func = AsyncMock(side_effect=[httpx.ReadTimeout("timeout"), "ok"])
        with patch("app.services.fate_integration.RETRY_BACKOFF_BASE", 0.01):
            result = await _retry_with_backoff(mock_func, max_retries=2)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        mock_func = AsyncMock(side_effect=httpx.ConnectError("fail"))
        with patch("app.services.fate_integration.RETRY_BACKOFF_BASE", 0.001):
            with pytest.raises(httpx.ConnectError):
                await _retry_with_backoff(mock_func, max_retries=2)
        assert mock_func.call_count == 3  # initial + 2 retries


# ==================== 提交任务测试 ====================


class TestSubmitJob:
    """测试 submit_job"""

    @pytest.mark.asyncio
    async def test_submit_local_simulation(self, db_session):
        """FATE 不可用时降级为本地模拟"""
        with patch("app.services.fate_integration.check_fate_available", return_value=False):
            config = _make_valid_config()
            result = await submit_job(db_session, config)

        assert "job_id" in result
        assert result["status"] == "running"
        assert result["mode"] == "local_simulation"
        assert result["algorithm"] == "homo_lr"
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_submit_fate_flow_success(self, db_session):
        """FATE 可用时提交到远程"""
        mock_result = {"job_id": "fate-123", "status": "submitted"}
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_result
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            config = _make_valid_config()
            result = await submit_job(db_session, config)

        assert result["job_id"] == "fate-123"
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_submit_fate_flow_failure_fallback(self, db_session):
        """FATE 提交失败时降级为本地模拟"""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("fail"))

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client), \
             patch("app.services.fate_integration.RETRY_BACKOFF_BASE", 0.001):
            config = _make_valid_config()
            result = await submit_job(db_session, config)

        assert result["mode"] == "local_simulation"
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_submit_extracts_algorithm(self, db_session):
        """测试从配置中提取算法类型"""
        algorithms = [
            (["reader_0", "homo_lr_0"], "homo_lr"),
            (["reader_0", "hetero_lr_0"], "hetero_lr"),
            (["reader_0", "homo_nn_0"], "homo_nn"),
            (["reader_0", "hetero_nn_0"], "hetero_nn"),
            (["reader_0", "secureboost_0"], "secureboost"),
            (["reader_0", "intersect_0"], "psi"),
            (["reader_0", "statistic_0"], "homo_statistic"),
        ]
        for components, expected in algorithms:
            with patch("app.services.fate_integration.check_fate_available", return_value=False):
                config = _make_valid_config(components)
                result = await submit_job(db_session, config)
            assert result["algorithm"] == expected, f"Failed for {components}"
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_submit_validates_config(self, db_session):
        """无效配置应被拒绝"""
        from app.exceptions import DataValidationError
        invalid_config = {"component_list": ["homo_lr_0"]}
        with pytest.raises(DataValidationError):
            await submit_job(db_session, invalid_config)


# ==================== 本地模拟任务测试 ====================


class TestLocalSimulation:
    """测试本地模拟模式"""

    @pytest.mark.asyncio
    async def test_local_simulation_submit(self, db_session):
        config = _make_valid_config()
        result = await _local_simulation_submit(db_session, config)

        assert "job_id" in result
        assert result["status"] == "running"
        assert result["mode"] == "local_simulation"
        assert result["job_id"].startswith("local_")
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_simulation_completes(self, app_db_session):
        """本地模拟任务最终会完成"""
        config = _make_valid_config()
        result = await _local_simulation_submit(app_db_session, config)
        job_id = result["job_id"]

        # 等待模拟完成（模拟5秒，因为每个step 0.5秒 * 10步）
        await asyncio.sleep(6)

        status = await get_job_status(app_db_session, job_id)
        assert status["status"] == "completed"
        assert status["progress"] == 100

    @pytest.mark.asyncio
    async def test_simulation_has_result(self, app_db_session):
        config = _make_valid_config()
        result = await _local_simulation_submit(app_db_session, config)
        job_id = result["job_id"]

        await asyncio.sleep(6)

        job_result = await get_job_result(app_db_session, job_id)
        assert job_result["status"] == "completed"
        assert "metrics" in job_result
        assert "result" in job_result
        assert job_result["result"]["federation_type"] == "simulated"


# ==================== 任务状态查询测试 ====================


class TestGetJobStatus:
    """测试 get_job_status"""

    @pytest.mark.asyncio
    async def test_local_job_status(self, db_session):
        config = _make_valid_config()
        submit_result = await submit_job(db_session, config)
        job_id = submit_result["job_id"]

        status = await get_job_status(db_session, job_id)
        assert status["job_id"] == job_id
        assert status["status"] in ("running", "completed")
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_not_found(self, db_session):
        status = await get_job_status(db_session, "nonexistent")
        assert status["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_fate_flow_status(self, db_session):
        """远程任务状态查询 — 先在 DB 中插入一条 fate_flow 记录"""
        from app.models.fate_job import FateJob
        fate_job = FateJob(
            job_id="fate-123",
            mode="fate_flow",
            algorithm="homo_lr",
            status="running",
            config={"dag_name": "test"},
        )
        db_session.add(fate_job)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "fate-123", "status": "success"}
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            status = await get_job_status(db_session, "fate-123")

        assert status["status"] == "success"
        await db_session.rollback()


# ==================== 任务结果查询测试 ====================


class TestGetJobResult:
    """测试 get_job_result"""

    @pytest.mark.asyncio
    async def test_local_job_result(self, db_session):
        config = _make_valid_config()
        submit_result = await submit_job(db_session, config)
        job_id = submit_result["job_id"]

        # 由于本地模拟的后台任务可能还没完成，直接查询 DB
        # 如果已降级到本地模拟，查询应该返回 job_id
        result = await get_job_result(db_session, job_id)
        assert result["job_id"] == job_id
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_not_found(self, db_session):
        result = await get_job_result(db_session, "nonexistent")
        assert result["status"] == "not_found"


# ==================== 取消任务测试 ====================


class TestCancelJob:
    """测试 cancel_job"""

    @pytest.mark.asyncio
    async def test_cancel_local_running_job(self, db_session):
        config = _make_valid_config()
        submit_result = await submit_job(db_session, config)
        job_id = submit_result["job_id"]

        result = await cancel_job(db_session, job_id)
        assert result["status"] == "cancelled"
        assert result["mode"] == "local_simulation"
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_cancel_local_completed_job(self, db_session):
        config = _make_valid_config()
        submit_result = await submit_job(db_session, config)
        job_id = submit_result["job_id"]

        # 手动将状态设为已完成
        from sqlalchemy import select
        from app.models.fate_job import FateJob
        stmt = select(FateJob).where(FateJob.job_id == job_id)
        result = await db_session.execute(stmt)
        job = result.scalar_one()
        job.status = "completed"
        await db_session.flush()

        result = await cancel_job(db_session, job_id)
        assert "message" in result  # 任务不在可取消状态
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_cancel_fate_flow_job(self, db_session):
        """取消远程任务"""
        from app.models.fate_job import FateJob
        fate_job = FateJob(
            job_id="fate-123",
            mode="fate_flow",
            algorithm="homo_lr",
            status="running",
            config={"dag_name": "test"},
        )
        db_session.add(fate_job)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"job_id": "fate-123", "status": "cancelled"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await cancel_job(db_session, "fate-123")

        # 验证 DB 中状态已更新
        from sqlalchemy import select
        stmt = select(FateJob).where(FateJob.job_id == "fate-123")
        db_result = await db_session.execute(stmt)
        updated_job = db_result.scalar_one()
        assert updated_job.status == "cancelled"
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_cancel_fate_unavailable_for_remote_job(self, db_session):
        """FATE 不可用时无法取消远程任务"""
        from app.models.fate_job import FateJob
        fate_job = FateJob(
            job_id="fate-456",
            mode="fate_flow",
            algorithm="homo_lr",
            status="running",
            config={"dag_name": "test"},
        )
        db_session.add(fate_job)
        await db_session.flush()

        with patch("app.services.fate_integration.check_fate_available", return_value=False):
            from app.exceptions import ComputeError
            with pytest.raises(ComputeError):
                await cancel_job(db_session, "fate-456")
        await db_session.rollback()


# ==================== 列出任务测试 ====================


class TestListJobs:
    """测试 list_jobs"""

    @pytest.mark.asyncio
    async def test_empty_list(self, db_session):
        result = await list_jobs(db_session)
        assert "items" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result

    @pytest.mark.asyncio
    async def test_local_jobs_in_list(self, db_session):
        config1 = _make_valid_config()
        config2 = _make_valid_config()
        await submit_job(db_session, config1)
        await submit_job(db_session, config2)

        result = await list_jobs(db_session)
        assert result["total"] >= 2
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_pagination(self, db_session):
        for i in range(5):
            config = _make_valid_config()
            await submit_job(db_session, config)

        result = await list_jobs(db_session, limit=2, offset=0)
        assert len(result["items"]) == 2
        assert result["total"] >= 5
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_fate_flow_jobs_included(self, db_session):
        """远程任务也应包含在列表中"""
        from app.models.fate_job import FateJob
        fate_job = FateJob(
            job_id="remote-1",
            mode="fate_flow",
            algorithm="homo_lr",
            status="success",
            config={"dag_name": "test"},
        )
        db_session.add(fate_job)
        await db_session.flush()

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"job_id": "remote-1", "status": "success"}]
        }
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await list_jobs(db_session)

        assert any(j.get("job_id") == "remote-1" for j in result["items"])
        await db_session.rollback()


# ==================== 数据管理测试 ====================


class TestUploadData:
    """测试 upload_data"""

    @pytest.mark.asyncio
    async def test_fate_unavailable(self):
        with patch("app.services.fate_integration.check_fate_available", return_value=False):
            from app.exceptions import ComputeError
            with pytest.raises(ComputeError):
                await upload_data("test_table", "/path/to/data.csv")

    @pytest.mark.asyncio
    async def test_upload_success(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await upload_data("test_table", "/path/to/data.csv", namespace="test")

        assert result["status"] == "success"


class TestDownloadData:
    """测试 download_data"""

    @pytest.mark.asyncio
    async def test_fate_unavailable(self):
        with patch("app.services.fate_integration.check_fate_available", return_value=False):
            from app.exceptions import ComputeError
            with pytest.raises(ComputeError):
                await download_data("test_table")

    @pytest.mark.asyncio
    async def test_download_success(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": []}
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await download_data("test_table", "test_ns")

        assert result["status"] == "success"


class TestUploadDataFromBytes:
    """测试 upload_data_from_bytes"""

    @pytest.mark.asyncio
    async def test_fate_unavailable(self):
        with patch("app.services.fate_integration.check_fate_available", return_value=False):
            from app.exceptions import ComputeError
            with pytest.raises(ComputeError):
                await upload_data_from_bytes("test_table", b"test,data\n1,2")

    @pytest.mark.asyncio
    async def test_upload_success(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("app.services.fate_integration.check_fate_available", return_value=True), \
             patch("app.services.fate_integration._get_http_client", return_value=mock_client):
            result = await upload_data_from_bytes("test_table", b"id,label\n1,0\n2,1")

        assert result["status"] == "success"


# ==================== 配置生成测试 ====================


class TestGenerateHomoLrConfig:
    """测试 generate_homo_lr_config"""

    def test_basic_structure(self):
        parties = [
            {"role": "guest", "party_id": 9999},
            {"role": "host", "party_id": 10000},
        ]
        config = generate_homo_lr_config(parties, "energy_data", epochs=20)

        assert config["dsl_version"] == 2
        assert "homo_lr_" in config["dag_name"]
        assert 9999 in config["role"]["guest"]
        assert 10000 in config["role"]["host"]
        assert 9999 == config["initiator"]["party_id"]

    def test_component_list(self):
        parties = [{"role": "guest", "party_id": 9999}]
        config = generate_homo_lr_config(parties, "data")
        assert "homo_lr_0" in config["component_list"]
        assert "reader_0" in config["component_list"]
        assert "evaluation_0" in config["component_list"]

    def test_custom_params(self):
        parties = [{"role": "guest", "party_id": 9999}]
        config = generate_homo_lr_config(
            parties, "data", epochs=50, learning_rate=0.05
        )
        guest_params = config["component_parameters"]["role"]["guest"]["0"]["homo_lr_0"]
        assert guest_params["max_iter"] == 50
        assert guest_params["learning_rate"] == 0.05


class TestGenerateHeteroLrConfig:
    """测试 generate_hetero_lr_config"""

    def test_basic_structure(self):
        config = generate_hetero_lr_config(
            guest_party_id=9999,
            host_party_ids=[10000, 10001],
            guest_dataset="guest_data",
            host_datasets=["host_data1", "host_data2"],
        )
        assert "hetero_lr_" in config["dag_name"]
        assert 9999 in config["role"]["guest"]
        assert 10000 in config["role"]["host"]
        assert 10001 in config["role"]["host"]

    def test_has_intersect_component(self):
        config = generate_hetero_lr_config(
            guest_party_id=9999,
            host_party_ids=[10000],
            guest_dataset="guest_data",
            host_datasets=["host_data"],
        )
        assert "intersect_0" in config["component_list"]
        assert "hetero_lr_0" in config["component_list"]


class TestGeneratePsiConfig:
    """测试 generate_psi_config"""

    def test_basic_structure(self):
        parties = [
            {"role": "guest", "party_id": 9999},
            {"role": "host", "party_id": 10000},
        ]
        config = generate_psi_config(parties, ["data_a", "data_b"])

        assert "psi_" in config["dag_name"]
        assert "intersect_0" in config["component_list"]
        assert 9999 in config["role"]["guest"]
        assert 10000 in config["role"]["host"]

    def test_intersect_params(self):
        parties = [
            {"role": "guest", "party_id": 9999},
            {"role": "host", "party_id": 10000},
        ]
        config = generate_psi_config(parties, ["data_a", "data_b"])
        intersect_params = config["component_parameters"]["role"]["guest"]["0"]["intersect_0"]
        assert intersect_params["intersect_method"] == "rsa"
        assert intersect_params["sync_intersect_ids"] is True


# ==================== 辅助函数测试 ====================


class TestExtractAlgorithmFromConfig:
    """测试 _extract_algorithm_from_config"""

    def test_homo_lr(self):
        assert _extract_algorithm_from_config({"component_list": ["reader_0", "homo_lr_0"]}) == "homo_lr"

    def test_hetero_lr(self):
        assert _extract_algorithm_from_config({"component_list": ["reader_0", "hetero_lr_0"]}) == "hetero_lr"

    def test_homo_nn(self):
        assert _extract_algorithm_from_config({"component_list": ["homo_nn_0"]}) == "homo_nn"

    def test_hetero_nn(self):
        assert _extract_algorithm_from_config({"component_list": ["hetero_nn_0"]}) == "hetero_nn"

    def test_secureboost(self):
        assert _extract_algorithm_from_config({"component_list": ["secureboost_0"]}) == "secureboost"

    def test_psi(self):
        assert _extract_algorithm_from_config({"component_list": ["intersect_0"]}) == "psi"

    def test_statistic(self):
        assert _extract_algorithm_from_config({"component_list": ["statistic_0"]}) == "homo_statistic"

    def test_default(self):
        assert _extract_algorithm_from_config({"component_list": ["reader_0"]}) == "homo_lr"

    def test_empty(self):
        assert _extract_algorithm_from_config({"component_list": []}) == "homo_lr"


class TestGenerateSimulationMetrics:
    """测试 _generate_simulation_metrics"""

    def test_lr_metrics(self):
        metrics = _generate_simulation_metrics("homo_lr")
        assert "auc" in metrics
        assert "accuracy" in metrics
        assert metrics["auc"] > 0.9

    def test_nn_metrics(self):
        metrics = _generate_simulation_metrics("homo_nn")
        assert "loss" in metrics
        assert "auc" in metrics

    def test_secureboost_metrics(self):
        metrics = _generate_simulation_metrics("secureboost")
        assert "feature_importance" in metrics

    def test_psi_metrics(self):
        metrics = _generate_simulation_metrics("psi")
        assert "match_rate" in metrics
        assert "matched_count" in metrics

    def test_statistic_metrics(self):
        metrics = _generate_simulation_metrics("homo_statistic")
        assert "mean" in metrics
        assert "std" in metrics

    def test_unknown_metrics(self):
        metrics = _generate_simulation_metrics("unknown_algo")
        assert "loss" in metrics


# ==================== 配置校验测试 ====================


class TestValidateFateConfig:
    """测试 validate_fate_config"""

    def test_valid_config(self):
        config = _make_valid_config()
        result = validate_fate_config(config)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_missing_dsl_version(self):
        config = _make_valid_config()
        del config["dsl_version"]
        result = validate_fate_config(config)
        assert result["valid"] is False
        assert any("dsl_version" in e for e in result["errors"])

    def test_wrong_dsl_version(self):
        config = _make_valid_config()
        config["dsl_version"] = 1
        result = validate_fate_config(config)
        assert result["valid"] is False

    def test_missing_initiator(self):
        config = _make_valid_config()
        del config["initiator"]
        result = validate_fate_config(config)
        assert result["valid"] is False


# ==================== 清理任务测试 ====================


class TestCleanupJobs:
    """测试 cleanup_jobs"""

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent_jobs(self, db_session):
        config = _make_valid_config()
        await submit_job(db_session, config)

        removed = await cleanup_jobs(db_session, max_age_hours=24)
        assert removed == 0
        await db_session.rollback()


# ==================== 兼容性 API 测试 ====================


class TestCompatibilityWrappers:
    """测试兼容性包装器"""

    def test_get_fate_service_info_structure(self):
        info = get_fate_service_info()
        assert "config" in info
        assert "health" in info
        assert "monitor" in info
        assert "base_url" in info

    def test_get_fate_service_info_health_key(self):
        info = get_fate_service_info()
        assert "is_healthy" in info["health"]
        assert "state" in info["health"]

    def test_get_fate_service_info_config_keys(self):
        info = get_fate_service_info()
        config = info["config"]
        assert "base_url" in config
        assert "operation_mode" in config
        assert "request_timeout" in config
        assert "max_retries" in config

    def test_get_fate_client_returns_fate_client(self):
        client = get_fate_client()
        assert hasattr(client, "check_health")

    @pytest.mark.asyncio
    async def test_fate_client_check_health(self):
        client = get_fate_client()
        with patch("app.services.fate_integration.check_fate_available", return_value=True):
            result = await client.check_health(force=True)
        assert result is True

    def test_get_job_manager_returns_job_manager(self):
        manager = get_job_manager()
        assert hasattr(manager, "cancel")
        assert hasattr(manager, "cleanup")


# ==================== 生命周期管理测试 ====================


class TestLifecycle:
    """测试 initialize/shutdown"""

    @pytest.mark.asyncio
    async def test_initialize(self):
        with patch("app.services.fate_integration.check_fate_available", return_value=False), \
             patch("app.services.fate_integration._start_health_check_loop") as mock_start:
            await initialize()
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown(self):
        with patch("app.services.fate_integration.stop_health_check") as mock_stop, \
             patch("app.services.fate_integration._close_http_client") as mock_close:
            await shutdown()
            mock_stop.assert_called_once()
            mock_close.assert_called_once()


# ==================== 重置测试 ====================


class TestResetFateAvailability:
    """测试 reset_fate_availability"""

    def test_resets_state(self):
        fate_module._connection_state = ConnectionState.CONNECTED
        fate_module._connection_metrics.record_success(100.0)
        fate_module._circuit_opened_since = time.time()

        reset_fate_availability()

        assert fate_module._connection_state == ConnectionState.DISCONNECTED
        assert fate_module._circuit_opened_since is None
        assert fate_module._connection_metrics.consecutive_failures == 0


# ==================== FATE 算法常量测试 ====================


class TestFateAlgorithms:
    """测试 FATE_ALGORITHMS 常量"""

    def test_contains_expected_algorithms(self):
        assert "homo_lr" in FATE_ALGORITHMS
        assert "hetero_lr" in FATE_ALGORITHMS
        assert "homo_nn" in FATE_ALGORITHMS
        assert "hetero_nn" in FATE_ALGORITHMS
        assert "secureboost" in FATE_ALGORITHMS
        assert "psi" in FATE_ALGORITHMS
        assert "homo_statistic" in FATE_ALGORITHMS

    def test_descriptions_are_strings(self):
        for algo, desc in FATE_ALGORITHMS.items():
            assert isinstance(desc, str), f"{algo} description is not a string"
