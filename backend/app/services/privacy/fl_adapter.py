"""
联邦学习（FATE）适配器

包装 fl_service.py 的功能函数为 PrivacyComputeInterface 实现。
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.privacy.compute_interface import PrivacyComputeInterface
from app.services import fl_service

logger = logging.getLogger(__name__)


class FLComputeService(PrivacyComputeInterface):
    """FATE 联邦学习计算服务适配器"""

    @property
    def engine_name(self) -> str:
        return "FL"

    @property
    def engine_description(self) -> str:
        return "FATE 联邦学习 - 多方协作训练模型，数据不出本地"

    async def initialize(
        self,
        db: AsyncSession,
        config: dict,
    ) -> dict:
        """
        初始化 FL 训练任务

        config 需包含:
            - name: 任务名称
            - algorithm: 算法标识 (lr/secureboost/nn/fm/svd/kmeans)
            - participants: 参与方 DID 列表
            - dataset_config: 数据集配置
            - model_params: 模型参数（可选）
            - user_id: 用户 ID
            - organization_id: 组织 ID
        """
        result = await fl_service.submit_fl_training(
            db=db,
            name=config.get("name", "FL Task"),
            algorithm=config.get("algorithm", "lr"),
            participants=config.get("participants", []),
            dataset_config=config.get("dataset_config", {}),
            model_params=config.get("model_params"),
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
        执行 FL 训练

        在 FATE 引擎提交后，训练是异步进行的。
        此处获取模型当前状态和指标。
        """
        model_id = context.get("model_id", "")
        task_id = context.get("task_id", "")

        if model_id:
            try:
                model = await fl_service.get_model(db, model_id)
                return {
                    "task_id": task_id,
                    "model_id": model_id,
                    "status": model.get("status", "training"),
                    "metrics": model.get("metrics", {}),
                }
            except Exception:
                pass

        return {
            "task_id": task_id,
            "model_id": model_id,
            "status": "submitted",
            "metrics": {},
        }

    async def cleanup(self, context: dict) -> None:
        """FL 任务无需额外清理（模型保留在存储中）"""
        logger.debug(
            f"FL cleanup: task={context.get('task_id')}, "
            f"model={context.get('model_id')}"
        )

    def get_supported_algorithms(self) -> list[str]:
        return list(fl_service.FATE_ALGORITHMS.keys())
