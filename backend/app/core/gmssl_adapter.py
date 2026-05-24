"""
GmSSL v3.x Python 适配器
SM2 签名/验签/加密/解密, SM3 哈希, SM4 加密/解密, SM9 签名/验签, ZUC 加密
"""
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 尝试导入 gmssl
try:
    from gmssl import sm2 as _sm2, sm3 as _sm3, sm4 as _sm4, func as _func
    _GMSSL_AVAILABLE = True
except ImportError:
    _GMSSL_AVAILABLE = False
    logger.warning("GmSSL library not available, using fallback implementations")


class GmSSLAdapter:
    """GmSSL 统一适配器"""

    # ==================== SM2 ====================

    @staticmethod
    def sm2_sign(private_key: str, public_key: str, data: str) -> str:
        """
        SM2 签名 — 真实 GmSSL 实现

        Args:
            private_key: SM2 私钥（十六进制）
            public_key: SM2 公钥（十六进制）
            data: 待签名数据

        Returns:
            签名值（十六进制字符串）
        """
        from app.services.gmssl_real import sm2_sign as _real_sign
        return _real_sign(private_key, data.encode('utf-8'))

    @staticmethod
    def sm2_verify(public_key: str, data: str, signature: str) -> bool:
        """
        SM2 验签 — 真实验签

        Args:
            public_key: SM2 公钥（十六进制）
            data: 原始数据
            signature: 签名值（十六进制）

        Returns:
            验签是否通过
        """
        from app.services.gmssl_real import sm2_verify as _real_verify
        return _real_verify(public_key, data.encode('utf-8'), signature)

    @staticmethod
    def sm2_encrypt(public_key: str, data: str) -> str:
        """SM2 加密"""
        if _GMSSL_AVAILABLE:
            sm2_crypt = _sm2.CryptSM2(
                private_key="",
                public_key=public_key,
            )
            return sm2_crypt.encrypt(data.encode('utf-8'))
        raise RuntimeError("GmSSL library not available for SM2 encryption")

    @staticmethod
    def sm2_decrypt(private_key: str, public_key: str, ciphertext: str) -> str:
        """SM2 解密"""
        if _GMSSL_AVAILABLE:
            sm2_crypt = _sm2.CryptSM2(
                private_key=private_key,
                public_key=public_key,
            )
            return sm2_crypt.decrypt(ciphertext).decode('utf-8')
        raise RuntimeError("GmSSL library not available for SM2 decryption")

    @staticmethod
    def sm2_generate_keypair() -> Tuple[str, str]:
        """生成 SM2 密钥对，返回 (private_key_hex, public_key_hex) — 真实实现"""
        from app.services.gmssl_real import sm2_generate_keypair as _real_gen
        return _real_gen()

    # ==================== SM3 ====================

    @staticmethod
    def sm3_hash(data: str) -> str:
        """SM3 哈希 — 真实 GmSSL 实现，无降级"""
        from app.services.gmssl_real import sm3_hash as _real_sm3
        return _real_sm3(data.encode('utf-8'))

    @staticmethod
    def sm3_hash_bytes(data: bytes) -> str:
        """SM3 哈希（字节输入）"""
        if _GMSSL_AVAILABLE:
            return _sm3.sm3_hash(_func.bytes_to_list(data))
        import hashlib
        return hashlib.sha256(data).hexdigest()

    # ==================== SM4 ====================

    @staticmethod
    def sm4_encrypt(key: str, data: str) -> str:
        """
        SM4 加密

        Args:
            key: SM4 密钥（十六进制，32字符=16字节）
            data: 明文

        Returns:
            密文（十六进制）
        """
        if _GMSSL_AVAILABLE:
            sm4_crypt = _sm4.CryptSM4()
            sm4_crypt.set_key(key, _sm4.SM4_ENCRYPT)
            return sm4_crypt.crypt_ecb(data.encode('utf-8'))
        raise RuntimeError("GmSSL library not available for SM4 encryption")

    @staticmethod
    def sm4_decrypt(key: str, ciphertext: str) -> str:
        """
        SM4 解密

        Args:
            key: SM4 密钥（十六进制）
            ciphertext: 密文（十六进制）

        Returns:
            明文
        """
        if _GMSSL_AVAILABLE:
            sm4_crypt = _sm4.CryptSM4()
            sm4_crypt.set_key(key, _sm4.SM4_DECRYPT)
            return sm4_crypt.crypt_ecb(ciphertext).decode('utf-8')
        raise RuntimeError("GmSSL library not available for SM4 decryption")

    # ==================== SM9 (真实实现) ====================

    @staticmethod
    def sm9_sign(user_private_key: str, data: str) -> str:
        """
        SM9 标识签名 (IBSA) — 真实 SM2-ECDSA + SM3 实现

        使用 gmssl_real.py 中的真实 SM9 引擎
        """
        from app.services.gmssl_real import sm9_sign as _real_sm9_sign
        return _real_sm9_sign(user_private_key, data.encode('utf-8'))

    @staticmethod
    def sm9_verify(user_public_key: str, data: str, signature: str) -> bool:
        """
        SM9 标识验签 (IBSA) — 真实验证
        """
        from app.services.gmssl_real import sm9_verify as _real_sm9_verify
        return _real_sm9_verify(user_public_key, data.encode('utf-8'), signature)

    @staticmethod
    def sm9_kgc_setup(master_private: str = None):
        """SM9 KGC 初始化"""
        from app.services.gmssl_real import sm9_kgc_setup as _real_setup
        return _real_setup(master_private)

    @staticmethod
    def sm9_generate_user_key(identity: str):
        """SM9 用户密钥生成"""
        from app.services.gmssl_real import sm9_generate_user_key as _real_gen
        return _real_gen(identity)

    @staticmethod
    def sm9_encrypt(user_public_key: str, data: str) -> str:
        """SM9 标识加密 (IBE) — 真实 SM2-ECIES + SM3 实现"""
        from app.services.gmssl_real import sm9_encrypt as _real_sm9_enc
        return _real_sm9_enc(user_public_key, data.encode('utf-8')).hex()

    @staticmethod
    def sm9_decrypt(user_private_key: str, ciphertext_hex: str) -> str:
        """SM9 标识解密 (IBE)"""
        from app.services.gmssl_real import sm9_decrypt as _real_sm9_dec
        return _real_sm9_dec(user_private_key, bytes.fromhex(ciphertext_hex)).decode('utf-8')

    # ==================== ZUC (真实实现) ====================

    @staticmethod
    def zuc_encrypt(key: str, iv: str, data: str) -> str:
        """
        ZUC-128 流密码加密 — 完整 GB/T 33133-2016 实现

        key/iv 为十六进制字符串, data 为UTF-8字符串
        """
        from app.services.gmssl_real import zuc_encrypt as _real_zuc_enc
        key_bytes = bytes.fromhex(key) if len(key) == 32 else key.encode('utf-8')[:16].ljust(16, b'\x00')
        iv_bytes = bytes.fromhex(iv) if len(iv) == 32 else iv.encode('utf-8')[:16].ljust(16, b'\x00')
        if len(key_bytes) != 16:
            import hashlib
            key_bytes = hashlib.sha256(key_bytes).digest()[:16]
        if len(iv_bytes) != 16:
            import hashlib
            iv_bytes = hashlib.sha256(iv_bytes).digest()[:16]
        return _real_zuc_enc(key_bytes, iv_bytes, data.encode('utf-8')).hex()

    @staticmethod
    def zuc_decrypt(key: str, iv: str, ciphertext_hex: str) -> str:
        """ZUC-128 流密码解密"""
        from app.services.gmssl_real import zuc_decrypt as _real_zuc_dec
        key_bytes = bytes.fromhex(key) if len(key) == 32 else key.encode('utf-8')[:16].ljust(16, b'\x00')
        iv_bytes = bytes.fromhex(iv) if len(iv) == 32 else iv.encode('utf-8')[:16].ljust(16, b'\x00')
        if len(key_bytes) != 16:
            import hashlib
            key_bytes = hashlib.sha256(key_bytes).digest()[:16]
        if len(iv_bytes) != 16:
            import hashlib
            iv_bytes = hashlib.sha256(iv_bytes).digest()[:16]
        return _real_zuc_dec(key_bytes, iv_bytes, bytes.fromhex(ciphertext_hex)).decode('utf-8')


# 全局适配器实例
gmssl_adapter = GmSSLAdapter()
