"""
同态加密（SEAL HE）适配器

包装 he_service.py 的功能函数为 PrivacyComputeInterface 实现。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.privacy.compute_interface import PrivacyComputeInterface
from app.services import he_service

logger = logging.getLogger(__name__)


class HEComputeService(PrivacyComputeInterface):
    """SEAL 同态加密计算服务适配器"""

    @property
    def engine_name(self) -> str:
        return "HE"

    @property
    def engine_description(self) -> str:
        return "TenSEAL 同态加密 (Microsoft SEAL) - 真实密文计算，CKKS/BFV"

    async def initialize(
        self,
        db: AsyncSession,
        config: dict,
    ) -> dict:
        """
        初始化 HE 加密环境

        config 支持两种模式:
        1. 加密上传:
            - mode: "encrypt"
            - name, scheme, asset_id, encryption_params
        2. 密文计算:
            - mode: "compute"
            - name, scheme, operation, ciphertext_ids, compute_params
        """
        mode = config.get("mode", "compute")

        if mode == "encrypt":
            result = await he_service.encrypt_upload(
                db=db,
                name=config.get("name", "HE Encrypt"),
                scheme=config.get("scheme", "ckks"),
                asset_id=config.get("asset_id", ""),
                encryption_params=config.get("encryption_params"),
                user_id=config.get("user_id", ""),
                organization_id=config.get("organization_id", ""),
            )
        else:
            result = await he_service.he_compute(
                db=db,
                name=config.get("name", "HE Compute"),
                scheme=config.get("scheme", "ckks"),
                operation=config.get("operation", "add"),
                ciphertext_ids=config.get("ciphertext_ids", []),
                compute_params=config.get("compute_params"),
                user_id=config.get("user_id", ""),
                organization_id=config.get("organization_id", ""),
            )

        return result

    async def execute(
        self,
        db: AsyncSession,
        context: dict,
    ) -> dict:
        """
        HE 计算执行

        加密上传模式：返回密钥信息。
        计算模式：返回结果密文信息。
        """
        task_id = context.get("task_id", "")
        key_id = context.get("key_id", "")
        ciphertext_id = context.get("ciphertext_id", "")
        result_ciphertext_id = context.get("result_ciphertext_id", "")

        return {
            "task_id": task_id,
            "key_id": key_id,
            "ciphertext_id": ciphertext_id or result_ciphertext_id,
            "scheme": context.get("scheme", ""),
            "noise_budget_remaining": context.get("noise_budget_remaining", 0),
            "metrics": {},
        }

    async def cleanup(self, context: dict) -> None:
        """HE 计算无需特别清理（密钥和密文保留在存储中）"""
        logger.debug(
            f"HE cleanup: task={context.get('task_id')}, "
            f"key={context.get('key_id')}"
        )

    def get_supported_algorithms(self) -> list[str]:
        return list(he_service.HE_SCHEMES.keys())
