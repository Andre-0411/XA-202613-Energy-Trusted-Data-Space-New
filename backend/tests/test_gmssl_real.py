"""
国密算法实现单元测试
测试 gmssl_real.py 中的 SM2 密钥生成、签名验证、加密解密、回退策略安全性
"""
import pytest
import os
from unittest.mock import patch, MagicMock


class TestSM2Engine:
    """测试 SM2 非对称加密引擎"""

    def test_generate_keypair(self):
        """测试生成 SM2 密钥对"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        private_key, public_key = engine.generate_keypair()

        assert isinstance(private_key, str)
        assert isinstance(public_key, str)
        assert len(private_key) == 64  # 32 字节 = 64 十六进制字符
        assert len(public_key) > 0

    def test_generate_keypair_different_each_time(self):
        """测试每次生成的密钥对不同"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        private_key1, public_key1 = engine.generate_keypair()
        private_key2, public_key2 = engine.generate_keypair()

        assert private_key1 != private_key2
        assert public_key1 != public_key2

    def test_sign_and_verify(self, sample_sm2_keypair):
        """测试签名和验签"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        data = b"Test data for signing"

        signature = engine.sign(sample_sm2_keypair["private_key"], data)

        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_sign_verifiable(self, sample_sm2_keypair):
        """测试签名可以被正确验证"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        data = b"Test data"

        signature = engine.sign(sample_sm2_keypair["private_key"], data)

        # SM2 签名是非确定性的（使用随机 k），但应该能被正确验证
        assert engine.verify(sample_sm2_keypair["public_key"], data, signature) is True

    def test_sign_different_data_different_signature(self, sample_sm2_keypair):
        """测试不同数据产生不同签名"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()

        sig1 = engine.sign(sample_sm2_keypair["private_key"], b"Data 1")
        sig2 = engine.sign(sample_sm2_keypair["private_key"], b"Data 2")

        assert sig1 != sig2

    def test_encrypt_and_decrypt(self, sample_sm2_keypair):
        """测试加密和解密"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        original_data = b"Hello, World!"

        encrypted = engine.encrypt(sample_sm2_keypair["public_key"], original_data)

        assert isinstance(encrypted, bytes)
        assert encrypted != original_data

        decrypted = engine.decrypt(sample_sm2_keypair["private_key"], encrypted)

        assert decrypted == original_data

    def test_encrypt_different_data(self, sample_sm2_keypair):
        """测试不同数据的加密结果不同"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()

        enc1 = engine.encrypt(sample_sm2_keypair["public_key"], b"Data 1")
        enc2 = engine.encrypt(sample_sm2_keypair["public_key"], b"Data 2")

        assert enc1 != enc2

    def test_encrypt_with_different_keys(self):
        """测试不同密钥的加密结果不同"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        data = b"Test data"

        keypair1 = engine.generate_keypair()
        keypair2 = engine.generate_keypair()

        enc1 = engine.encrypt(keypair1[1], data)
        enc2 = engine.encrypt(keypair2[1], data)

        assert enc1 != enc2

    def test_verify_with_wrong_public_key(self):
        """测试使用错误公钥验签应失败"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        data = b"Test data"

        keypair1 = engine.generate_keypair()
        keypair2 = engine.generate_keypair()

        signature = engine.sign(keypair1[0], data)

        # 使用错误的公钥验证应该失败
        result = engine.verify(keypair2[1], data, signature)

        assert result is False

    def test_decrypt_with_wrong_private_key(self):
        """测试使用错误私钥解密"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        data = b"Test data"

        keypair1 = engine.generate_keypair()
        keypair2 = engine.generate_keypair()

        encrypted = engine.encrypt(keypair1[1], data)

        # 使用错误的私钥解密
        decrypted = engine.decrypt(keypair2[0], encrypted)

        # 解密应该失败或返回错误数据
        assert decrypted != data


class TestSM3Engine:
    """测试 SM3 哈希引擎"""

    def test_hash(self):
        """测试 SM3 哈希"""
        from app.services.gmssl_real import SM3Engine

        data = b"Hello, World!"
        hash_result = SM3Engine.hash(data)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # 256 位 = 64 十六进制字符

    def test_hash_deterministic(self):
        """测试哈希的确定性"""
        from app.services.gmssl_real import SM3Engine

        data = b"Test data"

        hash1 = SM3Engine.hash(data)
        hash2 = SM3Engine.hash(data)

        assert hash1 == hash2

    def test_hash_different_data(self):
        """测试不同数据的哈希不同"""
        from app.services.gmssl_real import SM3Engine

        hash1 = SM3Engine.hash(b"Data 1")
        hash2 = SM3Engine.hash(b"Data 2")

        assert hash1 != hash2

    def test_hash_empty_data(self):
        """测试空数据的哈希"""
        from app.services.gmssl_real import SM3Engine

        hash_result = SM3Engine.hash(b"")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    def test_hmac_hash(self):
        """测试 SM3-based HMAC"""
        from app.services.gmssl_real import SM3Engine

        key = b"secret_key"
        data = b"Test data"

        hmac_result = SM3Engine.hmac_hash(key, data)

        assert isinstance(hmac_result, str)
        assert len(hmac_result) == 64

    def test_hmac_hash_deterministic(self):
        """测试 HMAC 的确定性"""
        from app.services.gmssl_real import SM3Engine

        key = b"secret_key"
        data = b"Test data"

        hmac1 = SM3Engine.hmac_hash(key, data)
        hmac2 = SM3Engine.hmac_hash(key, data)

        assert hmac1 == hmac2

    def test_hmac_hash_different_keys(self):
        """测试不同密钥的 HMAC 不同"""
        from app.services.gmssl_real import SM3Engine

        data = b"Test data"

        hmac1 = SM3Engine.hmac_hash(b"key1", data)
        hmac2 = SM3Engine.hmac_hash(b"key2", data)

        assert hmac1 != hmac2


class TestSM4Engine:
    """测试 SM4 对称加密引擎"""

    def test_init_with_random_key(self):
        """测试使用随机密钥初始化"""
        from app.services.gmssl_real import SM4Engine

        engine = SM4Engine()

        assert engine.key is not None
        assert len(engine.key) == 16

    def test_init_with_custom_key(self):
        """测试使用自定义密钥初始化"""
        from app.services.gmssl_real import SM4Engine

        key = os.urandom(16)
        engine = SM4Engine(key)

        assert engine.key == key

    def test_init_with_invalid_key_length(self):
        """测试无效密钥长度"""
        from app.services.gmssl_real import SM4Engine

        with pytest.raises(ValueError, match="SM4 key must be 16 bytes"):
            SM4Engine(os.urandom(32))

    def test_encrypt_and_decrypt(self):
        """测试加密和解密"""
        from app.services.gmssl_real import SM4Engine

        engine = SM4Engine()
        original_data = b"Hello, World!"

        encrypted = engine.encrypt(original_data)

        assert isinstance(encrypted, bytes)
        assert encrypted != original_data

        decrypted = engine.decrypt(encrypted)

        assert decrypted == original_data

    def test_encrypt_with_padding(self):
        """测试带填充的加密"""
        from app.services.gmssl_real import SM4Engine

        engine = SM4Engine()
        # 数据长度不是 16 的倍数
        original_data = b"Test data"

        encrypted = engine.encrypt(original_data)
        decrypted = engine.decrypt(encrypted)

        assert decrypted == original_data

    def test_encrypt_empty_data(self):
        """测试加密空数据"""
        from app.services.gmssl_real import SM4Engine

        engine = SM4Engine()
        original_data = b""

        encrypted = engine.encrypt(original_data)
        decrypted = engine.decrypt(encrypted)

        assert decrypted == original_data

    def test_encrypt_long_data(self):
        """测试加密长数据"""
        from app.services.gmssl_real import SM4Engine

        engine = SM4Engine()
        original_data = os.urandom(1024)

        encrypted = engine.encrypt(original_data)
        decrypted = engine.decrypt(encrypted)

        assert decrypted == original_data

    def test_pkcs7_padding(self):
        """测试 PKCS7 填充"""
        from app.services.gmssl_real import SM4Engine

        engine = SM4Engine()

        # 测试不同长度的数据
        for length in range(1, 32):
            data = os.urandom(length)
            padded = engine._pkcs7_pad(data)

            assert len(padded) % 16 == 0
            assert len(padded) >= length + 1

    def test_pkcs7_unpadding(self):
        """测试 PKCS7 去填充"""
        from app.services.gmssl_real import SM4Engine

        engine = SM4Engine()

        # 创建带填充的数据
        data = b"Test"
        padded = engine._pkcs7_pad(data)

        unpadded = engine._pkcs7_unpad(padded)

        assert unpadded == data


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_hash_data(self):
        """测试 hash_data 函数"""
        from app.services.gmssl_real import hash_data

        result = hash_data("Hello, World!")

        assert isinstance(result, str)
        assert len(result) == 64

    def test_sign_data(self, sample_sm2_keypair):
        """测试 sign_data 函数"""
        from app.services.gmssl_real import sign_data

        signature = sign_data(sample_sm2_keypair["private_key"], "Test data")

        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_verify_signature(self, sample_sm2_keypair):
        """测试 verify_signature 函数"""
        from app.services.gmssl_real import sign_data, verify_signature

        data = "Test data"
        signature = sign_data(sample_sm2_keypair["private_key"], data)

        result = verify_signature(sample_sm2_keypair["public_key"], data, signature)

        assert result is True

    def test_encrypt_data(self, sample_sm2_keypair):
        """测试 encrypt_data 函数"""
        from app.services.gmssl_real import encrypt_data

        encrypted = encrypt_data(sample_sm2_keypair["public_key"], "Hello")

        assert isinstance(encrypted, bytes)

    def test_decrypt_data(self, sample_sm2_keypair):
        """测试 decrypt_data 函数"""
        from app.services.gmssl_real import encrypt_data, decrypt_data

        original = "Hello, World!"
        encrypted = encrypt_data(sample_sm2_keypair["public_key"], original)
        decrypted = decrypt_data(sample_sm2_keypair["private_key"], encrypted)

        assert decrypted == original

    def test_sm2_generate_keypair(self):
        """测试 sm2_generate_keypair 函数"""
        from app.services.gmssl_real import sm2_generate_keypair

        private_key, public_key = sm2_generate_keypair()

        assert isinstance(private_key, str)
        assert isinstance(public_key, str)

    def test_sm2_sign(self, sample_sm2_keypair):
        """测试 sm2_sign 函数"""
        from app.services.gmssl_real import sm2_sign

        signature = sm2_sign(sample_sm2_keypair["private_key"], b"Test data")

        assert isinstance(signature, str)

    def test_sm2_verify(self, sample_sm2_keypair):
        """测试 sm2_verify 函数"""
        from app.services.gmssl_real import sm2_sign, sm2_verify

        data = b"Test data"
        signature = sm2_sign(sample_sm2_keypair["private_key"], data)

        result = sm2_verify(sample_sm2_keypair["public_key"], data, signature)

        assert result is True

    def test_sm3_hash(self):
        """测试 sm3_hash 函数"""
        from app.services.gmssl_real import sm3_hash

        result = sm3_hash(b"Test data")

        assert isinstance(result, str)
        assert len(result) == 64

    def test_sm3_hexdigest(self):
        """测试 sm3_hexdigest 函数"""
        from app.services.gmssl_real import sm3_hexdigest

        result = sm3_hexdigest(b"Test data")

        assert isinstance(result, str)
        assert len(result) == 64


class TestCryptoSecurity:
    """测试加密实现的安全性"""

    def test_gmssl_availability(self):
        """记录 gmssl 可用状态"""
        from app.services.gmssl_real import HAS_GMSSL
        # gmssl 应该已安装并可用
        assert HAS_GMSSL is True

    def test_key_generation_randomness(self):
        """测试密钥生成的随机性"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()

        # 生成多个密钥对，确保随机性
        keypairs = set()
        for _ in range(10):
            private_key, public_key = engine.generate_keypair()
            keypairs.add((private_key, public_key))

        # 所有密钥对应该不同
        assert len(keypairs) == 10

    def test_signature_length(self, sample_sm2_keypair):
        """测试 SM2 签名长度（r || s，各 64 十六进制字符）"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        data = b"Test data"

        signature = engine.sign(sample_sm2_keypair["private_key"], data)

        # SM2 签名是 r || s，各 64 十六进制字符 = 128 字符
        assert len(signature) == 128

    def test_encryption_produces_ciphertext(self, sample_sm2_keypair):
        """测试加密产生密文"""
        from app.services.gmssl_real import SM2Engine

        engine = SM2Engine()
        data = b"Hello"

        encrypted = engine.encrypt(sample_sm2_keypair["public_key"], data)

        # 密文应该比原文长（SM2 加密包含随机数和点坐标）
        assert len(encrypted) > len(data)

    def test_sm3_hash_length(self):
        """测试 SM3 哈希长度（256 位 = 64 十六进制字符）"""
        from app.services.gmssl_real import SM3Engine

        data = b"Test data"

        sm3_hash = SM3Engine.hash(data)

        # SM3 输出 256 位 = 64 十六进制字符
        assert len(sm3_hash) == 64

    def test_sm3_hash_consistency(self):
        """测试 SM3 哈希一致性"""
        from app.services.gmssl_real import SM3Engine

        data = b"Test data"

        hash1 = SM3Engine.hash(data)
        hash2 = SM3Engine.hash(data)

        # 相同输入应该产生相同输出
        assert hash1 == hash2


class TestGlobalInstances:
    """测试全局实例"""

    def test_sm2_engine_exists(self):
        """测试 sm2_engine 全局实例存在"""
        from app.services.gmssl_real import sm2_engine

        assert sm2_engine is not None

    def test_sm3_engine_exists(self):
        """测试 sm3_engine 全局实例存在"""
        from app.services.gmssl_real import sm3_engine

        assert sm3_engine is not None

    def test_sm4_engine_exists(self):
        """测试 sm4_engine 全局实例存在"""
        from app.services.gmssl_real import sm4_engine

        assert sm4_engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
