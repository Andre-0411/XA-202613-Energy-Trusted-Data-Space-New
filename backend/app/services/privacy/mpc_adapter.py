"""
安全多方计算（MP-SPDZ）适配器

包装 mpc_service.py 的功能函数为 PrivacyComputeInterface 实现。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.privacy.compute_interface import PrivacyComputeInterface
from app.services import mpc_service

logger = logging.getLogger(__name__)


class MPCComputeService(PrivacyComputeInterface):
    """MP-SPDZ 安全多方计算服务适配器"""

    @property
    def engine_name(self) -> str:
        return "MPC"

    @property
    def engine_description(self) -> str:
        return "MP-SPDZ 安全多方计算 - 多方协同计算，各方输入均被保护"

    async def initialize(
        self,
        db: AsyncSession,
        config: dict,
    ) -> dict:
        """
        初始化 MPC 计算会话

        config 需包含:
            - name: 任务名称
            - protocol: MPC 协议 (spdz/psn/aby3/falcon/chaiguru/malicious-sha2)
            - participants: 参与方列表
            - computation_config: 计算配置（circuit/function）
            - input_asset_ids: 输入资产 ID 列表（可选）
            - user_id: 用户 ID
            - organization_id: 组织 ID
        """
        result = await mpc_service.submit_mpc_computation(
            db=db,
            name=config.get("name", "MPC Task"),
            protocol=config.get("protocol", "spdz"),
            participants=config.get("participants", []),
            computation_config=config.get("computation_config", {}),
            input_asset_ids=config.get("input_asset_ids", []),
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
        执行 MPC 计算

        MPC 计算是分布式的，此处查询会话状态。
        """
        session_id = context.get("session_id", "")
        task_id = context.get("task_id", "")

        if session_id:
            try:
                session = await mpc_service.get_session_status(session_id)
                return {
                    "task_id": task_id,
                    "session_id": session_id,
                    "status": session.get("status", "initialized"),
                    "protocol": session.get("protocol", ""),
                    "party_endpoints": session.get("party_endpoints", {}),
                    "metrics": {},
                }
            except Exception:
                pass

        return {
            "task_id": task_id,
            "session_id": session_id,
            "status": "submitted",
            "metrics": {},
        }

    async def cleanup(self, context: dict) -> None:
        """MPC 会话资源清理"""
        logger.debug(
            f"MPC cleanup: session={context.get('session_id')}, "
            f"task={context.get('task_id')}"
        )

    def get_supported_algorithms(self) -> list[str]:
        return list(mpc_service.MPC_PROTOCOLS.keys())
