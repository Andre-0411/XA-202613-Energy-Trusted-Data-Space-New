"""
SSO 服务测试
测试 SSO 数据库存储功能
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio

from app.models.sso_model import SsoProvider, SsoSession, SsoPendingAuth
from app.schemas.sso import SSOProviderConfig


class TestSsoService:
    """SSO 服务测试类"""

    @pytest.mark.asyncio
    async def test_provider_model_to_schema(self):
        """测试提供者模型转换为 Schema"""
        from app.services.sso_service import _provider_model_to_schema

        provider = SsoProvider(
            id=uuid.uuid4(),
            provider_id="test_provider",
            name="Test Provider",
            protocol="oauth2",
            client_id="test_client",
            client_secret="test_secret",
            authorize_url="https://auth.example.com/authorize",
            token_url="https://auth.example.com/token",
            userinfo_url="https://auth.example.com/userinfo",
            redirect_uri="http://localhost:3000/callback",
            scopes=["openid", "profile"],
            enabled=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        schema = _provider_model_to_schema(provider)

        assert schema.provider_id == "test_provider"
        assert schema.name == "Test Provider"
        assert schema.protocol == "oauth2"
        assert schema.client_id == "test_client"
        assert schema.enabled is True

    @pytest.mark.asyncio
    async def test_session_model_to_schema(self):
        """测试会话模型转换为 Schema"""
        from app.services.sso_service import _session_model_to_schema

        session = SsoSession(
            id=uuid.uuid4(),
            session_id="test_session_123",
            user_id="test_user",
            provider_id_ref="oauth2_default",
            access_token="test_token",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        schema = _session_model_to_schema(session)

        assert schema.session_id == "test_session_123"
        assert schema.user_id == "test_user"
        assert schema.provider_id == "oauth2_default"
        assert schema.ip_address == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_generate_saml_request(self):
        """测试生成 SAML 请求"""
        from app.services.sso_service import _generate_saml_request

        provider = SSOProviderConfig(
            provider_id="saml_test",
            name="SAML Test",
            protocol="saml2",
            redirect_uri="http://localhost:3000/saml/callback",
        )

        saml_request = _generate_saml_request(provider)

        assert saml_request is not None
        assert len(saml_request) > 0
        # 应该是 Base64 编码
        import base64
        try:
            decoded = base64.b64decode(saml_request).decode("utf-8")
            assert "AuthnRequest" in decoded
        except Exception:
            pytest.fail("SAML request is not valid Base64")


class TestSsoServiceIntegration:
    """SSO 服务集成测试（需要 mock 数据库）"""

    @pytest.mark.asyncio
    async def test_list_providers(self):
        """测试列出提供者"""
        from app.services.sso_service import list_providers

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with patch("app.services.sso_service.AsyncSessionLocal") as mock_local, \
             patch("app.services.sso_service._ensure_providers_initialized") as mock_init:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_init.return_value = None

            providers = await list_providers()

            assert isinstance(providers, list)

    @pytest.mark.asyncio
    async def test_add_provider(self):
        """测试添加提供者"""
        from app.services.sso_service import add_provider

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        config = SSOProviderConfig(
            provider_id="test_new",
            name="Test New Provider",
            protocol="oauth2",
            client_id="new_client",
            enabled=True,
        )

        with patch("app.services.sso_service.AsyncSessionLocal") as mock_local:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await add_provider(config)

            assert result.provider_id == "test_new"
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
