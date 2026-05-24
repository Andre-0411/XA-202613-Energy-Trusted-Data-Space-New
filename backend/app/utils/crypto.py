"""
国密工具模块
SM2 签名/验签、SM3 哈希、SM4 加密/解密
"""
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入 gmssl，如不可用则提供降级方案
try:
    from gmssl import sm2, sm3, sm4, func
    GMSSL_AVAILABLE = True
    logger.info("GmSSL library loaded successfully")
except ImportError:
    GMSSL_AVAILABLE = False
    logger.warning("GmSSL library not available, using fallback implementations")


def sm3_hash(data: str) -> str:
    """
    SM3 哈希计算

    Args:
        data: 待哈希的字符串

    Returns:
        SM3 哈希值（十六进制字符串）
    """
    if GMSSL_AVAILABLE:
        return sm3.sm3_hash(func.bytes_to_list(data.encode('utf-8')))
    # 降级: 使用 SHA-256（仅开发环境）
    logger.warning("SM3 not available, using SHA-256 fallback")
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def sm3_hash_bytes(data: bytes) -> str:
    """
    SM3 哈希计算（字节输入）

    Args:
        data: 待哈希的字节数据

    Returns:
        SM3 哈希值（十六进制字符串）
    """
    if GMSSL_AVAILABLE:
        return sm3.sm3_hash(func.bytes_to_list(data))
    return hashlib.sha256(data).hexdigest()


class SM2Crypto:
    """SM2 签名/验签工具"""

    def __init__(
        self,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
    ):
        """
        初始化 SM2 实例

        Args:
            private_key: SM2 私钥（十六进制，不含 04 前缀）
            public_key: SM2 公钥（十六进制，不含 04 前缀）
        """
        self._private_key = private_key
        self._public_key = public_key

        if GMSSL_AVAILABLE and private_key and public_key:
            self._sm2 = sm2.CryptSM2(
                private_key=private_key,
                public_key=public_key,
            )
        else:
            self._sm2 = None

    def sign(self, data: str) -> str:
        """
        SM2 签名

        Args:
            data: 待签名数据

        Returns:
            签名值（十六进制字符串）
        """
        if self._sm2 is None:
            raise RuntimeError("SM2 not available or keys not configured")

        random_hex = func.random_hex(self._sm2.para_len)
        return self._sm2.sign(data.encode('utf-8'), random_hex)

    def verify(self, data: str, signature: str) -> bool:
        """
        SM2 验签

        Args:
            data: 原始数据
            signature: 签名值（十六进制字符串）

        Returns:
            验签是否通过
        """
        if self._sm2 is None:
            raise RuntimeError("SM2 not available or keys not configured")

        return self._sm2.verify(signature, data.encode('utf-8'))


class SM4Crypto:
    """SM4 对称加解密工具"""

    def __init__(self, key: str):
        """
        初始化 SM4 实例

        Args:
            key: SM4 密钥（十六进制，16字节=32字符）
        """
        if GMSSL_AVAILABLE:
            self._sm4 = sm4.CryptSM4()
            self._key = key
        else:
            self._sm4 = None
            self._key = key

    def encrypt(self, data: str) -> str:
        """
        SM4 加密

        Args:
            data: 明文

        Returns:
            密文（十六进制字符串）
        """
        if self._sm4 is None:
            raise RuntimeError("SM4 not available")

        self._sm4.set_key(self._key, sm4.SM4_ENCRYPT)
        return self._sm4.crypt_ecb(data.encode('utf-8'))

    def decrypt(self, data: str) -> str:
        """
        SM4 解密

        Args:
            data: 密文（十六进制字符串）

        Returns:
            明文
        """
        if self._sm4 is None:
            raise RuntimeError("SM4 not available")

        self._sm4.set_key(self._key, sm4.SM4_DECRYPT)
        return self._sm4.crypt_ecb(data).decode('utf-8')


def password_hash(password: str, salt: str = "") -> str:
    """
    密码哈希（使用 SM3）

    Args:
        password: 明文密码
        salt: 盐值

    Returns:
        SM3 哈希后的密码
    """
    return sm3_hash(salt + password)


def verify_password(password: str, hashed: str, salt: str = "") -> bool:
    """
    验证密码

    Args:
        password: 明文密码
        hashed: 已哈希的密码
        salt: 盐值

    Returns:
        密码是否匹配
    """
    return sm3_hash(salt + password) == hashed
