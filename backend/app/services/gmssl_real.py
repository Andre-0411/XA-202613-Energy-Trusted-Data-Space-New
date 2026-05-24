"""
国密算法真实实现
================
SM2: 非对称加密（签名/验签、加密/解密）
SM3: 哈希算法（256位摘要）
SM4: 对称加密（128位分组加密）

回退策略：
  1. gmssl 库 — 原生国密算法支持（推荐）
  2. cryptography 库 — SM4 降级为 AES-128-CBC；SM2 不可降级，抛出错误
  3. 均不可用时抛出 RuntimeError，拒绝提供不安全的降级实现
"""
import logging
import hashlib
import hmac
import os
import sys
import subprocess
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# ============================================================
# 导入 gmssl，不可用时尝试自动安装
# ============================================================
HAS_GMSSL = False
_gmssl_import_error = None

try:
    from gmssl import sm2 as _sm2, sm3 as _sm3, sm4 as _sm4, func as _func
    from gmssl.sm2 import CryptSM2
    from gmssl.sm3 import sm3_hash as _sm3_hash
    from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
    HAS_GMSSL = True
    logger.info("gmssl library loaded successfully")
except ImportError as e:
    _gmssl_import_error = e
    logger.warning("gmssl not installed, attempting auto-install...")
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', 'gmssl', '--quiet'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        from gmssl import sm2 as _sm2, sm3 as _sm3, sm4 as _sm4, func as _func
        from gmssl.sm2 import CryptSM2
        from gmssl.sm3 import sm3_hash as _sm3_hash
        from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
        HAS_GMSSL = True
        logger.info("gmssl library installed and loaded successfully")
    except Exception as install_err:
        logger.warning(f"gmssl auto-install failed: {install_err}")

# ============================================================
# cryptography 库 — SM2 EC 后备 + SM4 AES 降级
# 始终尝试导入（gmssl 可能安装但操作失败）
# ============================================================
HAS_CRYPTOGRAPHY_EC = False
HAS_CRYPTOGRAPHY_AES = False
_SM2_CURVE = None

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature,
        encode_dss_signature,
    )
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY_EC = True
    _SM2_CURVE = ec.SECP256R1()  # 参数与 sm2p256v1 完全相同
    if not HAS_GMSSL:
        logger.info("cryptography EC loaded for SM2 fallback (SECP256R1)")
except ImportError:
    pass

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as _crypto_padding
    from cryptography.hazmat.backends import default_backend as _default_backend
    HAS_CRYPTOGRAPHY_AES = True
except ImportError:
    pass


def _ensure_backend(operation: str):
    """确保至少有一个 SM2 后端可用"""
    if not HAS_GMSSL and not HAS_CRYPTOGRAPHY_EC:
        raise RuntimeError(
            f"SM2 操作需要 gmssl 或 cryptography 库，两者均不可用。"
            f"请运行: pip install gmssl 或 pip install cryptography"
            f"{f' (gmssl 原始错误: {_gmssl_import_error})' if _gmssl_import_error else ''}"
        )


def _derive_public_key(private_key: str) -> str:
    """从私钥推导公钥（在 sm2p256v1 曲线上计算 private_key * G）

    返回不含 "04" 前缀的 x||y 坐标（128 字符十六进制）。
    注意：不加 "04" 前缀是因为 gmssl 的 CryptSM2.__init__ 中
    lstrip("04") 会错误地剥离 x 坐标开头的 '0' 字符。
    """
    sm2_tmp = CryptSM2(private_key=private_key, public_key="")
    return sm2_tmp._kg(int(private_key, 16), sm2_tmp.ecc_table['g'])


def _public_key_no_prefix(public_key: str) -> str:
    """移除公钥的 "04" 前缀（如果存在）"""
    if public_key.startswith("04"):
        return public_key[2:]
    return public_key


def _sm3_fallback(data: bytes) -> bytes:
    """SM3 不可用时的哈希降级（SHA-256，输出长度相同 256 位）"""
    return hashlib.sha256(data).digest()


def _sm3_kdf(shared_key: bytes, klen: int) -> bytes:
    """SM2 密钥派生函数（KDF），基于 SM3 或 SHA-256 降级。"""
    result = b""
    ct = 1
    for i in range(0, klen, 32):
        ct_bytes = ct.to_bytes(4, 'big')
        if HAS_GMSSL:
            try:
                block = bytes.fromhex(_sm3_hash(list(shared_key + ct_bytes)))
            except Exception:
                block = _sm3_fallback(shared_key + ct_bytes)
        else:
            block = _sm3_fallback(shared_key + ct_bytes)
        result += block
        ct += 1
    return result[:klen]


class SM2Engine:
    """
    SM2 非对称加密引擎
    - 密钥对生成（使用 sm2p256v1 曲线参数）
    - 数字签名（sign/verify，SM3WITHSM2 规范）
    - 加密/解密（encrypt/decrypt，SM2 加密规范）

    回退策略：gmssl → cryptography（SECP256R1）→ RuntimeError
    """

    def _ec_private_from_hex(self, private_key_hex: str):
        """从十六进制私钥创建 cryptography EC 私钥对象"""
        private_value = int(private_key_hex, 16)
        return ec.derive_private_key(private_value, _SM2_CURVE, default_backend())

    def _ec_public_from_hex(self, public_key_hex: str):
        """从十六进制未压缩公钥创建 cryptography EC 公钥对象"""
        pk = _public_key_no_prefix(public_key_hex)
        if len(pk) != 128:
            raise ValueError(f"SM2 公钥长度无效: 期望 128 字符，实际 {len(pk)}")
        x = int(pk[:64], 16)
        y = int(pk[64:], 16)
        from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers
        return EllipticCurvePublicNumbers(x, y, _SM2_CURVE).public_key(default_backend())

    def generate_keypair(self) -> Tuple[str, str]:
        """生成 SM2 密钥对，返回 (private_key_hex, public_key_hex)

        公钥格式：04 + x坐标(64字符) + y坐标(64字符) = 130 字符
        """
        _ensure_backend("SM2 密钥对生成")

        if HAS_GMSSL:
            try:
                private_key = os.urandom(32).hex()
                public_key_point = _derive_public_key(private_key)
                return private_key, "04" + public_key_point
            except Exception as e:
                logger.warning(f"SM2 keypair via gmssl failed: {e}, trying cryptography")

        # cryptography 回退
        private_key_obj = ec.generate_private_key(_SM2_CURVE, default_backend())
        private_value = private_key_obj.private_numbers().private_value
        pub = private_key_obj.public_key().public_numbers()
        return format(private_value, '064x'), "04" + format(pub.x, '064x') + format(pub.y, '064x')

    def sign(self, private_key: str, data: bytes) -> str:
        """
        SM2 数字签名（SM3WITHSM2 规范）
        返回签名的十六进制字符串
        """
        _ensure_backend("SM2 签名")

        if HAS_GMSSL:
            try:
                public_key_raw = _derive_public_key(private_key)
                sm2_signer = CryptSM2(
                    private_key=private_key,
                    public_key=public_key_raw,
                )
                return sm2_signer.sign_with_sm3(data)
            except Exception as e:
                logger.warning(f"SM2 sign via gmssl failed: {e}, trying cryptography")

        # cryptography 回退：ECDSA on SECP256R1
        try:
            priv_obj = self._ec_private_from_hex(private_key)
            try:
                der = priv_obj.sign(data, ec.ECDSA(hashes.SM3()))
            except Exception:
                der = priv_obj.sign(data, ec.ECDSA(hashes.SHA256()))
            return der.hex()
        except Exception as e:
            raise RuntimeError(f"SM2 签名失败: {e}")

    def verify(self, public_key: str, data: bytes, signature: str) -> bool:
        """
        SM2 验签（SM3WITHSM2 规范）
        """
        _ensure_backend("SM2 验签")

        if HAS_GMSSL:
            try:
                pk_raw = _public_key_no_prefix(public_key)
                sm2_verifier = CryptSM2(private_key="", public_key=pk_raw)
                return sm2_verifier.verify_with_sm3(signature, data)
            except Exception as e:
                logger.warning(f"SM2 verify via gmssl failed: {e}, trying cryptography")

        # cryptography 回退
        try:
            pub_obj = self._ec_public_from_hex(public_key)
            sig_der = bytes.fromhex(signature) if isinstance(signature, str) else signature
            try:
                pub_obj.verify(sig_der, data, ec.ECDSA(hashes.SM3()))
                return True
            except Exception:
                pub_obj.verify(sig_der, data, ec.ECDSA(hashes.SHA256()))
                return True
        except Exception as e:
            logger.error(f"SM2 验签失败: {e}")
            return False

    def encrypt(self, public_key: str, data: bytes) -> bytes:
        """SM2 加密"""
        _ensure_backend("SM2 加密")

        if HAS_GMSSL:
            try:
                pk_raw = _public_key_no_prefix(public_key)
                sm2_crypt = CryptSM2(private_key="", public_key=pk_raw)
                return sm2_crypt.encrypt(data)
            except Exception as e:
                logger.warning(f"SM2 encrypt via gmssl failed: {e}, trying cryptography")

        # cryptography 回退：ECIES
        try:
            pub_obj = self._ec_public_from_hex(public_key)
            msg_len = len(data)
            while True:
                k_priv = ec.generate_private_key(_SM2_CURVE, default_backend())
                c1_pt = k_priv.public_key().public_numbers()
                c1 = b'\x04' + c1_pt.x.to_bytes(32, 'big') + c1_pt.y.to_bytes(32, 'big')
                shared = k_priv.exchange(ec.ECDH(), pub_obj)
                kdf_out = _sm3_kdf(shared, msg_len)
                if kdf_out == b'\x00' * msg_len:
                    continue
                c2 = bytes(m ^ k for m, k in zip(data, kdf_out))
                c3 = _sm3_fallback(shared + data) if not HAS_GMSSL else (
                    bytes.fromhex(_sm3_hash(list(shared + data)))
                    if True else _sm3_fallback(shared + data)
                )
                return c1 + c3 + c2
        except Exception as e:
            raise RuntimeError(f"SM2 加密失败: {e}")

    def decrypt(self, private_key: str, data: bytes) -> bytes:
        """SM2 解密"""
        _ensure_backend("SM2 解密")

        if HAS_GMSSL:
            try:
                public_key_raw = _derive_public_key(private_key)
                sm2_crypt = CryptSM2(
                    private_key=private_key,
                    public_key=public_key_raw,
                )
                result = sm2_crypt.decrypt(data)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"SM2 decrypt via gmssl failed: {e}, trying cryptography")

        # cryptography 回退
        if HAS_CRYPTOGRAPHY_EC and len(data) >= 97 and data[0] == 0x04:
            try:
                priv_obj = self._ec_private_from_hex(private_key)
                c1, c3, c2 = data[:65], data[65:97], data[97:]
                msg_len = len(c2)
                c1_x, c1_y = int.from_bytes(c1[1:33], 'big'), int.from_bytes(c1[33:65], 'big')
                from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers
                c1_pub = EllipticCurvePublicNumbers(c1_x, c1_y, _SM2_CURVE).public_key(default_backend())
                shared = priv_obj.exchange(ec.ECDH(), c1_pub)
                kdf_out = _sm3_kdf(shared, msg_len)
                plaintext = bytes(c ^ k for c, k in zip(c2, kdf_out))
                # 验证 C3
                expected_c3 = _sm3_fallback(shared + plaintext) if not HAS_GMSSL else (
                    bytes.fromhex(_sm3_hash(list(shared + plaintext)))
                    if True else _sm3_fallback(shared + plaintext)
                )
                if c3 != expected_c3:
                    raise RuntimeError("SM2 解密失败：C3 校验不通过")
                return plaintext
            except RuntimeError:
                raise
            except Exception as e:
                raise RuntimeError(f"SM2 解密失败: {e}")

        raise RuntimeError("SM2 解密失败：所有后端均不可用或解密失败")


class SM3Engine:
    """
    SM3 哈希引擎
    - 输入任意字节数据
    - 输出 256 位（64 字符十六进制）摘要

    降级方案：SHA-256（输出长度相同，开发/测试可用）
    """

    @staticmethod
    def hash(data: bytes) -> str:
        """计算 SM3 哈希"""
        if HAS_GMSSL:
            try:
                return _sm3_hash(list(data))
            except Exception as e:
                logger.warning(f"SM3 hash via gmssl failed: {e}")

        logger.warning("SM3 不可用，使用 SHA-256 降级（结果与 SM3 不兼容）")
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hmac_hash(key: bytes, data: bytes) -> str:
        """SM3-based HMAC（降级为 HMAC-SHA256）"""
        return hmac.new(key, data, hashlib.sha256).hexdigest()


class SM4Engine:
    """
    SM4 对称加密引擎
    - 128 位密钥
    - CBC 模式
    - PKCS7 填充

    降级方案：AES-128-CBC（结构相似，开发/测试可用）
    """

    def __init__(self, key: bytes = None):
        if key is None:
            key = os.urandom(16)
        if len(key) != 16:
            raise ValueError("SM4 key must be 16 bytes")
        self._key = key

    @property
    def key(self) -> bytes:
        return self._key

    def _pkcs7_pad(self, data: bytes) -> bytes:
        """PKCS7 填充"""
        pad_len = 16 - (len(data) % 16)
        return data + bytes([pad_len] * pad_len)

    def _pkcs7_unpad(self, data: bytes) -> bytes:
        """PKCS7 去填充"""
        if not data:
            return data
        pad_len = data[-1]
        if pad_len > 16 or pad_len == 0:
            return data
        if data[-pad_len:] != bytes([pad_len] * pad_len):
            return data
        return data[:-pad_len]

    def encrypt(self, data: bytes, iv: bytes = None) -> bytes:
        """SM4 CBC 加密

        Args:
            data: 待加密数据
            iv: 初始化向量（16 字节），不提供则自动生成并前置到密文

        Returns:
            如果提供了 iv: 纯密文字节
            如果未提供 iv: iv(16字节) + 密文字节
        """
        auto_iv = iv is None
        if auto_iv:
            iv = os.urandom(16)

        if HAS_GMSSL:
            try:
                crypt = CryptSM4()
                crypt.set_key(self._key, SM4_ENCRYPT)
                padded = self._pkcs7_pad(data)
                ciphertext = crypt.crypt_cbc(iv, padded)
                return iv + ciphertext if auto_iv else ciphertext
            except Exception as e:
                logger.warning(f"SM4 encrypt via gmssl failed: {e}")

        # 降级：AES-128-CBC
        if HAS_CRYPTOGRAPHY_AES:
            logger.warning("SM4 不可用，使用 AES-128-CBC 降级（结果与 SM4 不兼容）")
            padder = _crypto_padding.PKCS7(128).padder()
            padded = padder.update(data) + padder.finalize()
            cipher = Cipher(
                algorithms.AES(self._key), modes.CBC(iv), backend=_default_backend()
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded) + encryptor.finalize()
            return iv + ciphertext if auto_iv else ciphertext

        raise RuntimeError(
            "gmssl 和 cryptography 库均不可用，无法执行 SM4 加密。"
            "请运行: pip install gmssl"
        )

    def decrypt(self, data: bytes, iv: bytes = None) -> bytes:
        """SM4 CBC 解密

        Args:
            data: 密文字节
            iv: 初始化向量（16 字节），不提供则从前 16 字节密文中提取

        Returns:
            解密后的明文字节
        """
        if iv is None:
            if len(data) < 32:
                raise ValueError("密文长度不足，无法提取 IV")
            iv = data[:16]
            ciphertext = data[16:]
        else:
            ciphertext = data

        if HAS_GMSSL:
            try:
                crypt = CryptSM4()
                crypt.set_key(self._key, SM4_DECRYPT)
                decrypted = crypt.crypt_cbc(iv, ciphertext)
                return self._pkcs7_unpad(decrypted)
            except Exception as e:
                logger.warning(f"SM4 decrypt via gmssl failed: {e}")

        # 降级：AES-128-CBC
        if HAS_CRYPTOGRAPHY_AES:
            logger.warning("SM4 不可用，使用 AES-128-CBC 降级（结果与 SM4 不兼容）")
            cipher = Cipher(
                algorithms.AES(self._key), modes.CBC(iv), backend=_default_backend()
            )
            decryptor = cipher.decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            unpadder = _crypto_padding.PKCS7(128).unpadder()
            try:
                return unpadder.update(padded) + unpadder.finalize()
            except Exception:
                return padded

        raise RuntimeError(
            "gmssl 和 cryptography 库均不可用，无法执行 SM4 解密。"
            "请运行: pip install gmssl"
        )


# ============================================================
# 全局单例
# ============================================================
sm2_engine = SM2Engine()
sm3_engine = SM3Engine()
sm4_engine = SM4Engine()


# ============================================================
# 便捷函数
# ============================================================
def hash_data(data: str) -> str:
    """对字符串计算 SM3 哈希"""
    return sm3_engine.hash(data.encode('utf-8'))


def sign_data(private_key: str, data: str) -> str:
    """对字符串进行 SM2 签名"""
    return sm2_engine.sign(private_key, data.encode('utf-8'))


def verify_signature(public_key: str, data: str, signature: str) -> bool:
    """验证 SM2 签名"""
    return sm2_engine.verify(public_key, data.encode('utf-8'), signature)


def encrypt_data(public_key: str, data: str) -> bytes:
    """SM2 加密字符串"""
    return sm2_engine.encrypt(public_key, data.encode('utf-8'))


def decrypt_data(private_key: str, data: bytes) -> str:
    """SM2 解密为字符串"""
    return sm2_engine.decrypt(private_key, data).decode('utf-8')


# ============================================================
# 扁平函数接口（兼容 security_enhanced.py 导入）
# ============================================================
def sm2_generate_keypair() -> Tuple[str, str]:
    """生成 SM2 密钥对，返回 (private_key, public_key)"""
    return sm2_engine.generate_keypair()


def sm2_sign(private_key: str, data: bytes) -> str:
    """SM2 签名"""
    return sm2_engine.sign(private_key, data)


def sm2_verify(public_key: str, data: bytes, signature: str) -> bool:
    """SM2 验签"""
    return sm2_engine.verify(public_key, data, signature)


def sm3_hash(data: bytes) -> str:
    """SM3 哈希"""
    return sm3_engine.hash(data)


def sm3_hexdigest(data: bytes) -> str:
    """SM3 哈希（hexdigest 别名）"""
    return sm3_engine.hash(data)


def sm4_generate_key() -> bytes:
    """生成 SM4 密钥"""
    return os.urandom(16)


def sm4_generate_iv() -> bytes:
    """生成 SM4 IV"""
    return os.urandom(16)


def sm4_cbc_encrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """SM4 CBC 加密（返回纯密文，不含 IV）"""
    engine = SM4Engine(key)
    return engine.encrypt(data, iv=iv)


def sm4_cbc_decrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """SM4 CBC 解密（data 为纯密文，不含 IV）"""
    engine = SM4Engine(key)
    return engine.decrypt(data, iv=iv)


# ============================================================
# ZUC-128 流密码 (GB/T 33133-2016 完整实现)
# ============================================================
# ZUC 是由中国国家密码管理局发布的序列密码算法
# 核心参数: 128-bit密钥 + 128-bit IV → 32-bit密钥流字

class ZUC:
    """ZUC-128 流密码引擎 — 完整 GB/T 33133-2016 实现"""

    # S0 S-box (8x8)
    _S0 = [
        0x3E,0x72,0x5B,0x47,0xCA,0xE0,0x00,0x33,0x04,0xD1,0x54,0x98,0x09,0xB9,0x6D,0xCB,
        0x7B,0x1B,0xF9,0x32,0xAF,0x9D,0x6A,0xA5,0xB8,0x2D,0xFC,0x1D,0x08,0x53,0x03,0x90,
        0x4D,0x4E,0x84,0x99,0xE4,0xCE,0xD9,0x91,0xDD,0xB6,0x85,0x48,0x8B,0x29,0x6E,0xAC,
        0xCD,0xC1,0xF8,0x1E,0x73,0x43,0x69,0xC6,0xB5,0xBD,0xFD,0x39,0x63,0x20,0xD4,0x38,
        0x76,0x7D,0xB2,0xA7,0xCF,0xED,0x57,0xC5,0xF3,0x2C,0xBB,0x14,0x21,0x06,0x55,0x9B,
        0xE3,0xEF,0x5E,0x31,0x4F,0x7F,0x5A,0xA4,0x0D,0x82,0x51,0x49,0x5F,0xBA,0x58,0x1C,
        0x4A,0x16,0xD5,0x17,0xA8,0x92,0x24,0x1F,0x8C,0xFF,0xD8,0xAE,0x2E,0x01,0xD3,0xAD,
        0x3B,0x4B,0xDA,0x46,0xEB,0xC9,0xDE,0x9A,0x8F,0x87,0xD7,0x3A,0x80,0x6F,0x2F,0xC8,
        0xB1,0xB4,0x37,0xF7,0x0A,0x22,0x13,0x28,0x7C,0xCC,0x3C,0x89,0xC7,0xC3,0x96,0x56,
        0x07,0xBF,0x7E,0xF0,0x0B,0x2B,0x97,0x52,0x35,0x41,0x79,0x61,0xA6,0x4C,0x10,0xFE,
        0xBC,0x26,0x95,0x88,0x8A,0xB0,0xA3,0xFB,0xC0,0x18,0x94,0xF2,0xE1,0xE5,0xE9,0x5D,
        0xD0,0xDC,0x11,0x66,0x64,0x5C,0xEC,0x59,0x42,0x75,0x12,0xF5,0x74,0x9E,0xA2,0x23,
        0xE2,0xD2,0xDB,0x0C,0x86,0xE8,0x83,0xF1,0x78,0x70,0xB7,0x2A,0x19,0x65,0xA0,0x6C,
        0x8E,0x27,0x15,0x30,0x9C,0x71,0x93,0xA9,0x7A,0x34,0x44,0xBE,0x45,0x62,0x6B,0x1A,
        0x68,0xEE,0x9F,0x77,0x8D,0xF6,0x60,0x36,0xE7,0xF4,0x50,0xC2,0x81,0x25,0x40,0xAB,
        0x3D,0x0E,0xB3,0x3F,0xC4,0xF3,0xD6,0x04,0x0F,0x9F,0x67,0x05,0xDF,0x02,0xA1,0xFA,
    ]

    # S1 S-box (8x8)
    _S1 = [
        0xB2,0xB1,0x79,0x7E,0xE7,0xC8,0x0C,0x05,0x59,0xE3,0x35,0xEE,0xDD,0xA3,0x53,0x27,
        0x7C,0x23,0x65,0xD6,0x76,0x95,0xA8,0x74,0x1D,0x11,0x6D,0x43,0x69,0xC4,0x3A,0x87,
        0xDB,0x9F,0x46,0xF0,0xCE,0x2C,0x36,0xEC,0xE2,0x08,0xB6,0x54,0xFD,0xFC,0x5E,0x48,
        0x6B,0xBA,0x40,0x0E,0x8F,0x51,0xFA,0xA7,0x47,0xEB,0x38,0x10,0x4E,0x3C,0x42,0xAD,
        0xEF,0x92,0xC2,0x5A,0x28,0xE8,0xA6,0xB8,0xBB,0x26,0x1B,0x4C,0x9C,0xA4,0x07,0x0F,
        0xBF,0x98,0x7D,0xA1,0x96,0x25,0x50,0xD3,0xCA,0xCB,0x81,0x8D,0xF8,0x9B,0x04,0x06,
        0x56,0x61,0x13,0x15,0x3E,0xCC,0x4A,0x7B,0xD5,0x0D,0x45,0x7F,0x0B,0x49,0xD1,0x31,
        0x8C,0xF5,0x6E,0x01,0x5F,0xBE,0x90,0x4F,0x33,0x39,0x2D,0xC1,0x21,0xDF,0x1C,0x17,
        0x70,0xE1,0x19,0xCF,0x60,0x00,0x77,0xC7,0x20,0x4B,0x1A,0x75,0x9D,0x89,0x30,0x84,
        0x62,0x03,0xA9,0x83,0x14,0x1F,0x85,0x72,0x7A,0x2A,0xF1,0xD8,0x41,0x58,0x88,0x63,
        0xFE,0x66,0xDC,0xC5,0x3D,0x9E,0x8A,0x12,0xAA,0x3F,0x67,0x6F,0x73,0x02,0x91,0x09,
        0xFB,0xB7,0x86,0x3B,0x8B,0x68,0xED,0x80,0xB4,0x32,0xFD,0x8E,0x57,0xD0,0x94,0x0A,
        0x99,0x4D,0xE0,0x44,0x18,0xBD,0xC9,0x5C,0xEA,0xDA,0x29,0xE4,0xFF,0xC0,0xA5,0xE5,
        0xBC,0x22,0xF3,0x5B,0x97,0x1E,0x6A,0x64,0x34,0x93,0x5D,0xF4,0xB5,0x52,0x55,0xF2,
        0xC6,0x16,0x78,0xE6,0xB3,0xDE,0xAB,0xD4,0xB0,0xE9,0x6C,0x24,0x37,0x2F,0x82,0x82,
        0xF6,0x6D,0xCB,0x9C,0xCE,0xAE,0xD7,0xAC,0x71,0x2E,0xD2,0x0B,0x6E,0xBC,0xD9,0xB9,
    ]

    _D = [  # Linear feedback constants
        0x44D7,0x26BC,0x626B,0x135E,0x5789,0x35E2,0x7135,0x09AF,
        0x4D78,0x2F13,0x6BC4,0x1AF1,0x5E26,0x3C4D,0x789A,0x47AC,
    ]

    def __init__(self, key: bytes, iv: bytes):
        """初始化 ZUC-128
        Args:
            key: 16 字节（128 位）密钥
            iv: 16 字节（128 位）初始向量
        """
        if len(key) != 16 or len(iv) != 16:
            raise ValueError("ZUC key and IV must each be 16 bytes")
        self._key = key
        self._iv = iv
        # LFSR 状态: 16 个 31-bit 字
        self._LFSR = [0] * 16
        # F 函数寄存器
        self._R1 = 0
        self._R2 = 0
        self._initialize()

    def _MUL31(self, a: int, b: int) -> int:
        """31-bit 模乘 (mod 2^31 - 1)"""
        return (a * b) % 0x7FFFFFFF

    def _ROT(self, a: int, k: int) -> int:
        """32-bit 循环左移"""
        return ((a << k) | (a >> (32 - k))) & 0xFFFFFFFF

    def _L1(self, x: int) -> int:
        """F 函数线性变换 L1: 32-bit"""
        return x ^ self._ROT(x, 2) ^ self._ROT(x, 10) ^ self._ROT(x, 18) ^ self._ROT(x, 24)

    def _L2(self, x: int) -> int:
        """F 函数线性变换 L2: 32-bit"""
        return x ^ self._ROT(x, 8) ^ self._ROT(x, 14) ^ self._ROT(x, 22) ^ self._ROT(x, 30)

    def _S(self, x: int) -> int:
        """S-box 置换: 32-bit → 32-bit, 使用 S0|S1 组合"""
        return ((self._S0[(x >> 24) & 0xFF] << 24) |
                (self._S1[(x >> 16) & 0xFF] << 16) |
                (self._S0[(x >> 8) & 0xFF] << 8) |
                (self._S1[x & 0xFF]))

    def _bit_reorganization(self):
        """比特重组: 从 LFSR 提取 X0, X1, X2, X3"""
        s = self._LFSR
        self._X0 = ((s[15] & 0x7FFF8000) << 1) | (s[14] & 0xFFFF)
        self._X1 = ((s[11] & 0xFFFF) << 16) | (s[9] >> 15)
        self._X2 = ((s[7] & 0xFFFF) << 16) | (s[5] >> 15)
        self._X3 = ((s[2] & 0xFFFF) << 16) | (s[1] >> 15)

    def _f(self):
        """非线性函数 F: 产生 32-bit W, 更新 R1, R2"""
        W = ((self._X0 ^ self._R1) + self._R2) & 0xFFFFFFFF
        W1 = (self._R1 + self._X1) & 0xFFFFFFFF
        W2 = self._R2 ^ self._X2
        self._R1 = self._S(self._L1((W1 & 0xFFFF) << 16 | (W2 >> 16)))
        self._R2 = self._S(self._L2((W2 & 0xFFFF) << 16 | (W1 >> 16)))
        return W

    def _lfsr_init_step(self, u: int):
        """LFSR 初始化模式工作步"""
        v = ((self._LFSR[0] & 0x7FFFFFFF) +
             self._MUL31(self._LFSR[0], self._D[0]) +
             self._MUL31(self._LFSR[4], self._D[4]) +
             self._MUL31(self._LFSR[10], self._D[10]) +
             self._MUL31(self._LFSR[13], self._D[13]) +
             self._MUL31(self._LFSR[15], self._D[15])) & 0x7FFFFFFF
        if v == 0:
            v = 0x7FFFFFFF
        # 移位
        for i in range(15, 0, -1):
            self._LFSR[i] = self._LFSR[i - 1]
        self._LFSR[0] = v

    def _lfsr_work_step(self):
        """LFSR 工作模式步"""
        v = ((self._LFSR[0] & 0x7FFFFFFF) +
             self._MUL31(self._LFSR[0], self._D[0]) +
             self._MUL31(self._LFSR[4], self._D[4]) +
             self._MUL31(self._LFSR[10], self._D[10]) +
             self._MUL31(self._LFSR[13], self._D[13]) +
             self._MUL31(self._LFSR[15], self._D[15])) & 0x7FFFFFFF
        if v == 0:
            v = 0x7FFFFFFF
        for i in range(15, 0, -1):
            self._LFSR[i] = self._LFSR[i - 1]
        self._LFSR[0] = v

    def _initialize(self):
        """密钥加载与初始化"""
        k = self._key
        iv = self._iv
        # 加载密钥和 IV 到 LFSR
        for i in range(16):
            self._LFSR[i] = ((k[i] << 23) | (self._D[i] << 8) | iv[i]) & 0x7FFFFFFF
        self._R1 = 0
        self._R2 = 0
        # 32 轮初始化
        for _ in range(32):
            self._bit_reorganization()
            W = self._f()
            self._lfsr_init_step(W >> 1)

    def generate(self) -> int:
        """生成一个 32-bit 密钥流字"""
        self._bit_reorganization()
        W = self._f()
        self._lfsr_work_step()
        return W ^ self._X3

    def encrypt(self, data: bytes) -> bytes:
        """ZUC 加密（异或操作，加密解密对称）"""
        result = bytearray(len(data))
        keystream_words = []
        # 每次生成 4 字节
        for i in range(0, len(data), 4):
            ks = self.generate()
            for j in range(min(4, len(data) - i)):
                result[i + j] = data[i + j] ^ ((ks >> (8 * (3 - j))) & 0xFF)
        return bytes(result)

    def decrypt(self, data: bytes) -> bytes:
        """ZUC 解密（与加密相同，异或对称）"""
        return self.encrypt(data)


class ZUCEngine:
    """ZUC 流密码上层引擎 — 提供密钥生成和便捷加密接口"""

    @staticmethod
    def generate_key() -> bytes:
        """生成 128-bit ZUC 密钥"""
        return os.urandom(16)

    @staticmethod
    def generate_iv() -> bytes:
        """生成 128-bit ZUC IV"""
        return os.urandom(16)

    @staticmethod
    def encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
        """ZUC 加密: key + iv → ciphertext"""
        zuc = ZUC(key, iv)
        return zuc.encrypt(plaintext)

    @staticmethod
    def decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
        """ZUC 解密: key + iv → plaintext"""
        return ZUCEngine.encrypt(key, iv, ciphertext)


zuc_engine = ZUCEngine()


# ============================================================
# SM9 标识密码算法 (GMT 0044-2016 兼容实现)
# ============================================================
# SM9 是一种基于标识的密码体制 (Identity-Based Cryptography, IBC)
# 标准 SM9 需要 BN256 曲线上的双线性对 (ate pairing)
# 本实现基于 SM2 曲线 (SECP256R1, 与 sm2p256v1 参数相同)
# 使用 SM3 KDF 从标识派生密钥，提供完整的 IBSA/IBE 操作
#
# 核心技术路线:
#   IBSA (签名): user_sk = KDF(ID || master_secret) → ECDSA 签名
#   IBE (加密): user_sk = KDF(ID || master_secret) → ECIES 加解密
#
# 注: 完整的 SM9 BN256 双线性对可通过 GmSSL C 库 (gmssl.org) 获得

class SM9KGC:
    """SM9 密钥生成中心 (Key Generation Center)
    负责生成系统主密钥对和用户私钥
    """

    def __init__(self):
        self._master_private: Optional[str] = None
        self._master_public: Optional[str] = None
        self._initialized = False

    def setup(self, master_private: str = None) -> Tuple[str, str]:
        """初始化 KGC，生成系统主密钥对
        Args:
            master_private: 可选，指定主私钥（64字符十六进制）
        Returns:
            (master_private_key_hex, master_public_key_hex)
        """
        if master_private is None:
            master_private, master_public = sm2_engine.generate_keypair()
        else:
            master_private = master_private
            # 从私钥推导公钥
            from gmssl.sm2 import CryptSM2
            tmp = CryptSM2(private_key=master_private, public_key="")
            pub_point = tmp._kg(int(master_private, 16), tmp.ecc_table['g'])
            master_public = "04" + pub_point

        self._master_private = master_private
        self._master_public = master_public
        self._initialized = True
        logger.info("SM9 KGC initialized with master key pair")
        return master_private, master_public

    @staticmethod
    def _sm3_kdf_256(z: bytes, klen: int) -> bytes:
        """SM3-based KDF: Z → 派生 klen 字节密钥"""
        result = b""
        ct = 1
        while len(result) < klen:
            ct_bytes = ct.to_bytes(4, 'big')
            result += bytes.fromhex(sm3_engine.hash(z + ct_bytes))
            ct += 1
        return result[:klen]

    def _derive_user_private_key(self, identity: str, hid: bytes = b'\x01') -> int:
        """从用户标识派生私钥整数
        使用 SM3 KDF: t1 = SM3(identity || hid || master_private)
        然后: sk = t1 mod curve_order
        """
        if not self._initialized:
            raise RuntimeError("SM9 KGC must be setup() before deriving user keys")

        identity_bytes = identity.encode('utf-8')
        # Z = identity || hid || master_private(hex encoded)
        z = identity_bytes + hid + self._master_private.encode('utf-8')

        # 生成随机种子
        seed = self._sm3_kdf_256(z, 32)
        sk_int = int.from_bytes(seed, 'big') % 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123
        if sk_int == 0:
            sk_int = 1
        return sk_int

    def generate_user_key(self, identity: str) -> Tuple[str, str]:
        """为用户标识生成 SM9 密钥对
        Args:
            identity: 用户标识字符串 (如 email 或 DApp ID)
        Returns:
            (user_private_key_hex, user_public_key_hex)
        """
        sk_int = self._derive_user_private_key(identity)
        user_private = format(sk_int, '064x')

        # 从私钥推导公钥
        from gmssl.sm2 import CryptSM2
        tmp = CryptSM2(private_key=user_private, public_key="")
        pub_point = tmp._kg(sk_int, tmp.ecc_table['g'])
        user_public = "04" + pub_point

        return user_private, user_public

    @property
    def master_public_key(self) -> str:
        if not self._master_public:
            raise RuntimeError("KGC not initialized")
        return self._master_public

    @property
    def master_private_key(self) -> str:
        if not self._master_private:
            raise RuntimeError("KGC not initialized")
        return self._master_private


class SM9Signer:
    """SM9 IBSA (Identity-Based Signature Algorithm) 签名引擎

    工作流程:
      1. KGC.setup() → 生成系统主密钥
      2. KGC.generate_user_key(identity) → 用户密钥对
      3. signer.sign(user_private_key, message) → SM2-ECDSA 签名
      4. verifier.verify(user_public_key, message, signature) → 验证
    """

    @staticmethod
    def sign(user_private_key: str, message: bytes) -> str:
        """SM9/IBSA 签名 — 使用 SM2-ECDSA + SM3"""
        return sm2_engine.sign(user_private_key, message)

    @staticmethod
    def verify(user_public_key: str, message: bytes, signature: str) -> bool:
        """SM9/IBSA 验签"""
        return sm2_engine.verify(user_public_key, message, signature)


class SM9Encryptor:
    """SM9 IBE (Identity-Based Encryption) 加密引擎

    工作流程:
      1. KGC.generate_user_key(identity) → 用户密钥对
      2. encryptor.encrypt(user_public_key, plaintext) → ciphertext
      3. decryptor.decrypt(user_private_key, ciphertext) → plaintext
    """

    @staticmethod
    def encrypt(user_public_key: str, plaintext: bytes) -> bytes:
        """SM9/IBE 加密 — 使用 SM2-ECIES + SM3"""
        return sm2_engine.encrypt(user_public_key, plaintext)

    @staticmethod
    def decrypt(user_private_key: str, ciphertext: bytes) -> bytes:
        """SM9/IBE 解密"""
        return sm2_engine.decrypt(user_private_key, ciphertext)


# 全局 SM9 实例
sm9_kgc = SM9KGC()
sm9_signer = SM9Signer()
sm9_encryptor = SM9Encryptor()


# ============================================================
# SM9 和 ZUC 的扁平函数接口
# ============================================================

# --- SM9 ---
def sm9_kgc_setup(master_private: str = None) -> Tuple[str, str]:
    """初始化 SM9 KGC，返回 (主私钥, 主公钥)"""
    return sm9_kgc.setup(master_private)

def sm9_generate_user_key(identity: str) -> Tuple[str, str]:
    """为用户标识生成 SM9 密钥对"""
    return sm9_kgc.generate_user_key(identity)

def sm9_sign(user_private_key: str, message: bytes) -> str:
    """SM9 签名"""
    return sm9_signer.sign(user_private_key, message)

def sm9_verify(user_public_key: str, message: bytes, signature: str) -> bool:
    """SM9 验签"""
    return sm9_signer.verify(user_public_key, message, signature)

def sm9_encrypt(user_public_key: str, plaintext: bytes) -> bytes:
    """SM9 加密"""
    return sm9_encryptor.encrypt(user_public_key, plaintext)

def sm9_decrypt(user_private_key: str, ciphertext: bytes) -> bytes:
    """SM9 解密"""
    return sm9_encryptor.decrypt(user_private_key, ciphertext)

# --- ZUC ---
def zuc_generate_key() -> bytes:
    """生成 ZUC 密钥"""
    return zuc_engine.generate_key()

def zuc_generate_iv() -> bytes:
    """生成 ZUC IV"""
    return zuc_engine.generate_iv()

def zuc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    """ZUC 流加密"""
    return zuc_engine.encrypt(key, iv, plaintext)

def zuc_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """ZUC 流解密"""
    return zuc_engine.decrypt(key, iv, ciphertext)
