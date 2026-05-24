"""
密钥管理服务
============
- Shamir 秘密分享（N-of-M 门限方案）
- 密钥生成/存储/轮换
- 密钥备份/恢复
- 密钥派生（HKDF-like）
"""
import os
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class KeyShare:
    """Shamir 秘密分享片段"""
    index: int
    share: str  # hex string
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KeyMetadata:
    """密钥元数据"""
    key_id: str
    algorithm: str
    purpose: str
    created_at: str
    expires_at: Optional[str] = None
    is_active: bool = True
    version: int = 1
    rotated_from: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# Shamir 秘密分享
# ============================================================

class ShamirSecretSharing:
    """
    Shamir (k, n) 秘密分享方案
    - 将秘密分成 n 份
    - 至少 k 份可以恢复秘密
    - 少于 k 份无法获得任何信息
    """

    # 使用 256 位素数（简化实现，实际应使用更大的素数）
    PRIME = 2**256 - 189

    @staticmethod
    def split(secret: int, n: int, k: int) -> List[Tuple[int, int]]:
        """
        将秘密分割为 n 份，需要 k 份才能恢复

        Args:
            secret: 要分享的秘密（必须是非负整数）
            n: 总份数
            k: 门限值（最少需要几份）

        Returns:
            [(x1, y1), (x2, y2), ...] 分享片段
        """
        if k > n:
            raise ValueError("门限值 k 不能大于总份数 n")
        if k < 2:
            raise ValueError("门限值 k 至少为 2")
        if secret < 0:
            raise ValueError("秘密必须是非负整数")

        prime = ShamirSecretSharing.PRIME

        # 生成 k-1 个随机系数
        # f(x) = secret + a1*x + a2*x^2 + ... + a(k-1)*x^(k-1)
        coefficients = [secret % prime]
        for _ in range(k - 1):
            coeff = int.from_bytes(os.urandom(32), 'big') % prime
            coefficients.append(coeff)

        # 计算 n 个点 (x, f(x))
        shares = []
        for i in range(1, n + 1):
            x = i
            y = 0
            for j, coeff in enumerate(coefficients):
                y = (y + coeff * pow(x, j, prime)) % prime
            shares.append((x, y))

        return shares

    @staticmethod
    def reconstruct(shares: List[Tuple[int, int]]) -> int:
        """
        从分享片段恢复秘密（拉格朗日插值）

        Args:
            shares: [(x1, y1), (x2, y2), ...] 至少 k 个片段

        Returns:
            恢复的秘密整数
        """
        if len(shares) < 2:
            raise ValueError("至少需要 2 个分享片段")

        prime = ShamirSecretSharing.PRIME
        secret = 0

        for i, (xi, yi) in enumerate(shares):
            # 拉格朗日基函数
            numerator = 1
            denominator = 1
            for j, (xj, _) in enumerate(shares):
                if i != j:
                    numerator = (numerator * (-xj)) % prime
                    denominator = (denominator * (xi - xj)) % prime

            # 分母的模逆
            denom_inv = pow(denominator, -1, prime)
            lagrange_coeff = (numerator * denom_inv) % prime
            secret = (secret + yi * lagrange_coeff) % prime

        return secret


# ============================================================
# 密钥管理器
# ============================================================

class KeyManager:
    """
    密钥管理器
    - 密钥生成（SM2/SM4/HMAC）
    - Shamir 秘密分享备份
    - 密钥轮换
    - 密钥撤销
    """

    def __init__(self):
        self._keys: Dict[str, KeyMetadata] = {}
        self._key_data: Dict[str, str] = {}  # key_id -> private_key_hex (仅开发环境)
        self._key_shares: Dict[str, List[KeyShare]] = {}
        self._shamir = ShamirSecretSharing()
        logger.info("KeyManager initialized")

    def generate_key(
        self,
        key_id: str,
        algorithm: str = "SM2",
        purpose: str = "signing",
        expires_hours: Optional[int] = None
    ) -> str:
        """
        生成新密钥

        Args:
            key_id: 密钥标识
            algorithm: 算法类型（SM2/SM4/HMAC）
            purpose: 用途（signing/encryption/authentication）
            expires_hours: 过期时间（小时），None 表示不过期

        Returns:
            私钥十六进制字符串
        """
        private_key = os.urandom(32).hex()

        expires_at = None
        if expires_hours:
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_hours)).isoformat()

        self._keys[key_id] = KeyMetadata(
            key_id=key_id,
            algorithm=algorithm,
            purpose=purpose,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at
        )
        self._key_data[key_id] = private_key

        logger.info(f"Key generated: {key_id} ({algorithm}/{purpose})")
        return private_key

    def get_key(self, key_id: str) -> Optional[str]:
        """获取私钥（仅开发环境使用）"""
        meta = self._keys.get(key_id)
        if not meta:
            return None
        if not meta.is_active:
            logger.warning(f"Key {key_id} is revoked")
            return None
        if meta.expires_at:
            if datetime.fromisoformat(meta.expires_at) < datetime.now(timezone.utc):
                logger.warning(f"Key {key_id} is expired")
                return None
        return self._key_data.get(key_id)

    def split_key(
        self,
        key_id: str,
        total_shares: int = 5,
        threshold: int = 3
    ) -> List[KeyShare]:
        """
        使用 Shamir 秘密分享分割密钥

        Args:
            key_id: 要分割的密钥
            total_shares: 总份数
            threshold: 门限值

        Returns:
            KeyShare 列表
        """
        private_key = self._key_data.get(key_id)
        if not private_key:
            raise ValueError(f"Key {key_id} not found")

        secret_int = int(private_key, 16)
        shares = self._shamir.split(secret_int, total_shares, threshold)

        key_shares = []
        for x, y in shares:
            share = KeyShare(
                index=x,
                share=hex(y)[2:].zfill(64),  # 固定 64 字符
                created_at=datetime.now(timezone.utc).isoformat()
            )
            key_shares.append(share)

        self._key_shares[key_id] = key_shares
        logger.info(f"Key {key_id} split into {total_shares} shares (threshold={threshold})")
        return key_shares

    def reconstruct_key(self, key_id: str, shares: List[Tuple[int, int]]) -> str:
        """
        从分享片段恢复密钥

        Args:
            key_id: 密钥标识
            shares: [(index, share_hex), ...] 至少 threshold 个片段

        Returns:
            恢复的私钥十六进制字符串
        """
        secret_int = self._shamir.reconstruct(shares)
        private_key = hex(secret_int)[2:].zfill(64)

        # 验证恢复结果
        original = self._key_data.get(key_id)
        if original and private_key != original:
            logger.error(f"Key reconstruction mismatch for {key_id}")
            raise ValueError("Key reconstruction failed")

        logger.info(f"Key {key_id} reconstructed successfully")
        return private_key

    def rotate_key(self, key_id: str) -> str:
        """
        轮换密钥（保留旧版本，生成新版本）

        Returns:
            新私钥十六进制字符串
        """
        old_meta = self._keys.get(key_id)
        if not old_meta:
            raise ValueError(f"Key {key_id} not found")

        # 标记旧密钥为不活跃
        old_meta.is_active = False

        # 生成新密钥
        new_key = os.urandom(32).hex()
        new_version = old_meta.version + 1

        self._keys[key_id] = KeyMetadata(
            key_id=key_id,
            algorithm=old_meta.algorithm,
            purpose=old_meta.purpose,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=old_meta.expires_at,
            is_active=True,
            version=new_version,
            rotated_from=f"v{old_meta.version}"
        )
        self._key_data[key_id] = new_key

        logger.info(f"Key {key_id} rotated to version {new_version}")
        return new_key

    def revoke_key(self, key_id: str):
        """撤销密钥"""
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            # 安全清除内存中的密钥
            if key_id in self._key_data:
                del self._key_data[key_id]
            logger.info(f"Key {key_id} revoked")

    def list_keys(self, active_only: bool = True) -> List[KeyMetadata]:
        """列出所有密钥"""
        keys = list(self._keys.values())
        if active_only:
            keys = [k for k in keys if k.is_active]
        return keys

    def get_key_info(self, key_id: str) -> Optional[KeyMetadata]:
        """获取密钥元数据"""
        return self._keys.get(key_id)

    def derive_key(self, master_key_id: str, context: str) -> str:
        """
        从主密钥派生子密钥（HKDF-like）

        Args:
            master_key_id: 主密钥ID
            context: 派生上下文字符串

        Returns:
            派生的子密钥十六进制字符串
        """
        master_key = self.get_key(master_key_id)
        if not master_key:
            raise ValueError(f"Master key {master_key_id} not found")

        # HKDF-like: extract + expand
        prk = hmac.new(
            bytes.fromhex(master_key),
            context.encode(),
            hashlib.sha256
        ).digest()

        derived = hmac.new(prk, b'\x01', hashlib.sha256).hexdigest()
        return derived


# ============================================================
# 全局单例
# ============================================================
key_manager = KeyManager()
