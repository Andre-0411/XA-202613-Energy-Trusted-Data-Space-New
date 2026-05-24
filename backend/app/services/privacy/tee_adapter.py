"""
可信执行环境（Gramine TEE）适配器

包装 tee_service.py 的功能函数为 PrivacyComputeInterface 实现。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.privacy.compute_interface import PrivacyComputeInterface
from app.services import tee_service

logger = logging.getLogger(__name__)


class TEEComputeService(PrivacyComputeInterface):
    """Gramine TEE 可信执行环境服务适配器"""

    @property
    def engine_name(self) -> str:
        return "TEE"

    @property
    def engine_description(self) -> str:
        return "Gramine TEE 可信执行环境 - 硬件安全区内执行计算"

    async def initialize(
        self,
        db: AsyncSession,
        config: dict,
    ) -> dict:
        """
        初始化 TEE 实例

        config 需包含:
            - name: 任务名称
            - runtime: TEE 运行时 (gramine/sgx/trustzone)
            - code_ref: 代码引用
            - input_data_refs: 输入数据引用列表
            - enclave_config: 安全区配置（可选）
            - user_id: 用户 ID
            - organization_id: 组织 ID
        """
        result = await tee_service.execute_in_tee(
            db=db,
            name=config.get("name", "TEE Task"),
            runtime=config.get("runtime", "gramine"),
            code_ref=config.get("code_ref", ""),
            input_data_refs=config.get("input_data_refs", []),
            enclave_config=config.get("enclave_config"),
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
        TEE 内执行

        安全区初始化完成后，查询实例状态。
        """
        instance_id = context.get("instance_id", "")
        task_id = context.get("task_id", "")

        if instance_id:
            try:
                instance = await tee_service.get_tee_status(instance_id)
                return {
                    "task_id": task_id,
                    "instance_id": instance_id,
                    "status": instance.get("status", "creating"),
                    "runtime": instance.get("runtime", ""),
                    "mr_enclave": instance.get("mr_enclave", ""),
                    "ra_status": instance.get("ra_status", "pending"),
                    "metrics": {},
                }
            except Exception:
                pass

        return {
            "task_id": task_id,
            "instance_id": instance_id,
            "status": "submitted",
            "metrics": {},
        }

    async def cleanup(self, context: dict) -> None:
        """销毁 TEE 实例"""
        instance_id = context.get("instance_id", "")
        if instance_id:
            try:
                await tee_service.destroy_tee_instance(instance_id)
                logger.info(f"TEE instance destroyed: {instance_id}")
            except Exception as e:
                logger.warning(f"TEE instance cleanup failed: {e}")

    def get_supported_algorithms(self) -> list[str]:
        return list(tee_service.TEE_RUNTIMES.keys())
