"""
MFA 服务测试
测试 MFA 数据库存储功能
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio

from app.models.mfa_model import MfaConfig, MfaBackupCode, MfaSession


class TestMfaService:
    """MFA 服务测试类"""

    @pytest.mark.asyncio
    async def test_generate_secret(self):
        """测试生成 TOTP 密钥"""
        from app.services.mfa_service import _generate_secret

        secret = _generate_secret()
        assert secret is not None
        assert len(secret) > 0
        # Base32 编码应该只包含大写字母和数字2-7
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    @pytest.mark.asyncio
    async def test_generate_totp(self):
        """测试生成 TOTP 码"""
        from app.services.mfa_service import _generate_totp, _generate_secret

        secret = _generate_secret()
        totp = _generate_totp(secret)

        assert totp is not None
        assert len(totp) == 6
        assert totp.isdigit()

    @pytest.mark.asyncio
    async def test_verify_totp(self):
        """测试验证 TOTP 码"""
        from app.services.mfa_service import _generate_totp, _generate_secret, _verify_totp

        secret = _generate_secret()
        totp = _generate_totp(secret)

        # 验证应该成功
        assert _verify_totp(secret, totp) is True

        # 错误的码应该失败
        assert _verify_totp(secret, "000000") is False

    @pytest.mark.asyncio
    async def test_generate_backup_codes(self):
        """测试生成备份码"""
        from app.services.mfa_service import _generate_backup_codes

        codes = _generate_backup_codes()

        assert len(codes) == 10
        for code in codes:
            assert len(code) == 9  # XXXX-XXXX 格式
            assert code[4] == "-"

    @pytest.mark.asyncio
    async def test_hash_backup_code(self):
        """测试备份码哈希"""
        from app.services.mfa_service import _hash_backup_code

        code = "ABCD-1234"
        hash1 = _hash_backup_code(code)
        hash2 = _hash_backup_code(code)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 十六进制长度

    @pytest.mark.asyncio
    async def test_generate_totp_uri(self):
        """测试生成 TOTP URI"""
        from app.services.mfa_service import _generate_totp_uri, _generate_secret

        secret = _generate_secret()
        uri = _generate_totp_uri(secret, "test_user")

        assert uri.startswith("otpauth://totp/")
        assert "test_user" in uri
        assert secret in uri
        assert "EnergyDataSpace" in uri


class TestMfaServiceIntegration:
    """MFA 服务集成测试（需要 mock 数据库）"""

    @pytest.mark.asyncio
    async def test_setup_mfa_creates_config(self):
        """测试 setup_mfa 创建配置"""
        from app.services.mfa_service import setup_mfa

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()

        with patch("app.services.mfa_service.AsyncSessionLocal") as mock_local:
            mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

            response = await setup_mfa("test_user", "totp")

            assert response.secret is not None
            assert response.qr_code_url is not None
            assert len(response.backup_codes) == 10
            assert response.method == "totp"
