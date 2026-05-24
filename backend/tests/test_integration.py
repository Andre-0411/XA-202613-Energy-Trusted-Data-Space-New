"""
集成测试套件
测试组件之间的集成、API 端点的功能、前后端交互
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# TestSessionLocal is available via conftest.py - import directly from module
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from conftest import TestSessionLocal


class TestMfaAndAuthIntegration:
    """测试 MFA 和认证集成"""

    @pytest.mark.asyncio
    async def test_mfa_setup_and_verify_flow(self):
        """测试完整的 MFA 设置和验证流程"""
        from app.services.mfa_service import (
            setup_mfa, verify_mfa, enable_mfa, get_mfa_status,
            _generate_totp
        )

        async with TestSessionLocal() as session:
            with patch("app.services.mfa_service.AsyncSessionLocal") as mock_local:
                mock_local.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

                # 1. 设置 MFA
                setup_response = await setup_mfa("integration_user_001")
                assert setup_response.secret is not None
                assert len(setup_response.backup_codes) == 10

                # 2. 验证 MFA 状态（未启用）
                status = await get_mfa_status("integration_user_001")
                assert status.enabled is False

                # 3. 使用 TOTP 启用 MFA
                totp = _generate_totp(setup_response.secret)
                enable_result = await enable_mfa("integration_user_001", totp)
                assert enable_result is True

                # 4. 验证 MFA 状态（已启用）
                status = await get_mfa_status("integration_user_001")
                assert status.enabled is True

                # 5. 使用 TOTP 验证
                totp = _generate_totp(setup_response.secret)
                verify_response = await verify_mfa("integration_user_001", totp, session_id="session_001")
                assert verify_response.verified is True


class TestSSOAndSessionIntegration:
    """测试 SSO 和会话集成"""

    @pytest.mark.asyncio
    async def test_sso_authorization_flow(self):
        """测试完整的 SSO 授权流程"""
        from app.services.sso_service import (
            generate_authorize_url, exchange_token, get_user_info,
            create_sso_session, list_sessions, invalidate_session
        )

        async with TestSessionLocal() as session:
            with patch("app.services.sso_service.AsyncSessionLocal") as mock_local:
                mock_local.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

                # 1. 生成授权 URL
                auth_response = await generate_authorize_url("oauth2_default", state="test_state")
                assert auth_response.authorize_url is not None
                assert auth_response.state == "test_state"

                # 2. 交换 Token
                token_response = await exchange_token(
                    provider_id="oauth2_default",
                    code="test_code",
                    state="test_state"
                )
                assert token_response.access_token is not None

                # 3. 获取用户信息
                user_info = await get_user_info(token_response.access_token)
                assert user_info is not None
                assert user_info.provider_id == "oauth2_default"

                # 4. 创建会话
                session_info = await create_sso_session(
                    user_id=user_info.sub,
                    provider_id="oauth2_default",
                    ip_address="127.0.0.1"
                )


class TestWebSocketAndNotificationIntegration:
    """测试 WebSocket 和通知集成"""

    @pytest.mark.asyncio
    async def test_websocket_notification_flow(self):
        """测试 WebSocket 通知流程"""
        from app.services.websocket_manager import WebSocketManager, WSMessage, WSMessageType

        manager = WebSocketManager()

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # 1. 连接
        conn_id = await manager.connect(mock_ws, user_id="user_001")
        assert conn_id is not None

        # 2. 订阅频道
        await manager.subscribe(conn_id, ["notifications"])

        # 3. 广播消息到频道
        message = WSMessage(
            type=WSMessageType.NOTIFICATION,
            channel="notifications",
            data={"message": "Test notification"}
        )
        await manager.broadcast_to_channel("notifications", message)

        # 验证消息已发送
        assert mock_ws.send_json.called

        # 4. 断开连接
        await manager.disconnect(conn_id)

    @pytest.mark.asyncio
    async def test_websocket_user_specific_notification(self):
        """测试用户特定通知"""
        from app.services.websocket_manager import WebSocketManager, WSMessage, WSMessageType

        manager = WebSocketManager()

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # 连接
        conn_id = await manager.connect(mock_ws, user_id="user_002")

        # 发送用户特定消息
        message = WSMessage(
            type=WSMessageType.NOTIFICATION,
            data={"message": "您有新的数据请求"}
        )
        await manager.send_to_user("user_002", message)

        # 验证消息已发送
        assert mock_ws.send_json.called

        # 清理
        await manager.disconnect(conn_id)


class TestFateAndComputeIntegration:
    """测试 FATE 和计算集成"""

    @pytest.mark.asyncio
    async def test_fate_job_lifecycle(self, db_session):
        """测试 FATE 作业生命周期"""
        from app.services.fate_integration import (
            submit_job, get_job_status, list_jobs,
            generate_homo_lr_config
        )

        # 生成配置（需要包含 arbiter 角色）
        config = generate_homo_lr_config(
            parties=[
                {"party_id": "party1", "role": "guest"},
                {"party_id": "party2", "role": "host"},
                {"party_id": "party3", "role": "arbiter"},
            ],
            dataset="test_dataset",
            epochs=5,
            learning_rate=0.01
        )

        # 提交作业 (需要 db_session)
        job_result = await submit_job(db_session, config)
        assert "job_id" in job_result
        job_id = job_result["job_id"]

        # 查询状态
        status = await get_job_status(db_session, job_id)
        assert "status" in status

        # 列出作业
        jobs_result = await list_jobs(db_session)
        assert isinstance(jobs_result, dict)
        assert "items" in jobs_result

    @pytest.mark.asyncio
    async def test_fate_multiple_jobs(self, db_session):
        """测试多个 FATE 作业"""
        from app.services.fate_integration import (
            submit_job, list_jobs, generate_homo_lr_config
        )

        # 提交多个作业（需要包含 arbiter 角色）
        for i in range(3):
            config = generate_homo_lr_config(
                parties=[
                    {"party_id": "party1", "role": "guest"},
                    {"party_id": "party2", "role": "host"},
                    {"party_id": "party3", "role": "arbiter"},
                ],
                dataset=f"test_dataset_{i}",
                epochs=5,
                learning_rate=0.01
            )
            await submit_job(db_session, config)

        # 列出所有作业
        jobs_result = await list_jobs(db_session)
        assert isinstance(jobs_result, dict)
        assert len(jobs_result.get("items", [])) >= 3


class TestEndToEndFlow:
    """端到端流程测试"""

    @pytest.mark.asyncio
    async def test_complete_user_authentication_flow(self):
        """测试完整的用户认证流程"""
        from app.services.mfa_service import setup_mfa, verify_mfa, _generate_totp

        async with TestSessionLocal() as session:
            with patch("app.services.mfa_service.AsyncSessionLocal") as mock_local:
                mock_local.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

                # 1. 设置 MFA
                setup_response = await setup_mfa("e2e_user_001")
                assert setup_response.secret is not None

                # 2. 验证 MFA
                totp = _generate_totp(setup_response.secret)
                verify_response = await verify_mfa("e2e_user_001", totp)
                assert verify_response.verified is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
