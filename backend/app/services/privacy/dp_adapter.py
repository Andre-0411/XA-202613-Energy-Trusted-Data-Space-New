"""
差分隐私适配器

包装 dp_service.py 的功能函数为 PrivacyComputeInterface 实现。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.privacy.compute_interface import PrivacyComputeInterface
from app.services import dp_service

logger = logging.getLogger(__name__)


class DPComputeService(PrivacyComputeInterface):
    """差分隐私计算服务适配器"""

    @property
    def engine_name(self) -> str:
        return "DP"

    @property
    def engine_description(self) -> str:
        return "差分隐私 - 通过添加噪声保护个体隐私，数学可证明"

    async def initialize(
        self,
        db: AsyncSession,
        config: dict,
    ) -> dict:
        """
        初始化 DP 计算

        config 需包含:
            - name: 任务名称
            - asset_id: 数据资产 ID
            - mechanism: DP 机制 (laplace/gaussian/exponential/report_noisy_max)
            - epsilon: 隐私预算 epsilon
            - delta: 隐私预算 delta（可选）
            - sensitivity: 数据敏感度（可选）
            - query_type: 查询类型（可选）
            - config_template: 配置模板（可选，优先级高于单独参数）
            - user_id: 用户 ID
            - organization_id: 组织 ID
        """
        result = await dp_service.apply_differential_privacy(
            db=db,
            name=config.get("name", "DP Task"),
            asset_id=config.get("asset_id", ""),
            mechanism=config.get("mechanism", "laplace"),
            epsilon=config.get("epsilon", 1.0),
            delta=config.get("delta", 1e-5),
            sensitivity=config.get("sensitivity", 1.0),
            query_type=config.get("query_type", "count"),
            config_template=config.get("config_template"),
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
        DP 计算执行

        DP 是立即完成的（添加噪声），此处返回噪声参数和预算信息。
        """
        task_id = context.get("task_id", "")
        asset_id = context.get("privacy_budget", {}).get("asset_id", "")

        # 查询最新隐私预算
        budget_info = {}
        if asset_id:
            try:
                budget_info = await dp_service.get_privacy_budget(asset_id)
            except Exception:
                pass

        return {
            "task_id": task_id,
            "mechanism": context.get("mechanism", ""),
            "epsilon": context.get("epsilon", 0),
            "delta": context.get("delta", 0),
            "noise_params": context.get("noise_params", {}),
            "privacy_budget": budget_info or context.get("privacy_budget", {}),
            "metrics": {},
        }

    async def cleanup(self, context: dict) -> None:
        """DP 无需资源清理"""
        logger.debug(
            f"DP cleanup: task={context.get('task_id')}, "
            f"mechanism={context.get('mechanism')}"
        )

    def get_supported_algorithms(self) -> list[str]:
        return list(dp_service.DP_MECHANISMS.keys())
