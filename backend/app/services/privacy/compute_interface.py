"""
隐私计算统一抽象接口

PrivacyComputeInterface: 所有隐私计算引擎的抽象基类
- initialize(): 初始化计算环境
- execute(): 执行计算任务
- cleanup(): 清理资源
- get_supported_algorithms(): 返回支持的算法列表
- run(): 模板方法，统一生命周期 init → execute → cleanup

ComputeResult: 统一返回格式
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ComputeResult:
    """
    统一计算结果格式

    所有隐私计算引擎返回此格式，保证上层调用者
    无需关心底层技术差异。

    Attributes:
        success: 计算是否成功
        data: 计算结果数据（字典，包含 task_id, result 等）
        metrics: 性能指标（耗时、精度等）
        error: 错误信息（成功时为空字符串）
        engine: 计算引擎标识（FL/MPC/TEE/HE/DP）
        completed_at: 完成时间
    """
    success: bool = True
    data: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    error: str = ""
    engine: str = ""
    completed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "metrics": self.metrics,
            "error": self.error,
            "engine": self.engine,
            "completed_at": self.completed_at,
        }


class PrivacyComputeInterface(ABC):
    """
    隐私计算统一抽象接口

    所有隐私计算引擎（FL/MPC/TEE/HE/DP）必须继承此接口，
    并实现 initialize / execute / cleanup / get_supported_algorithms 方法。

    调用者通过 run() 模板方法统一调用，无需关心各引擎的生命周期差异。
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """引擎标识（FL/MPC/TEE/HE/DP）"""
        ...

    @property
    @abstractmethod
    def engine_description(self) -> str:
        """引擎描述"""
        ...

    @abstractmethod
    async def initialize(
        self,
        db: AsyncSession,
        config: dict,
    ) -> dict:
        """
        初始化计算环境

        Args:
            db: 数据库会话
            config: 计算配置（包含算法、参与方、输入数据等）

        Returns:
            初始化结果（包含 task_id、session_id 等上下文信息）
        """
        ...

    @abstractmethod
    async def execute(
        self,
        db: AsyncSession,
        context: dict,
    ) -> dict:
        """
        执行计算任务

        Args:
            db: 数据库会话
            context: 由 initialize 返回的上下文信息

        Returns:
            计算结果数据
        """
        ...

    @abstractmethod
    async def cleanup(
        self,
        context: dict,
    ) -> None:
        """
        清理计算资源

        Args:
            context: 由 initialize 返回的上下文信息
        """
        ...

    @abstractmethod
    def get_supported_algorithms(self) -> list[str]:
        """
        返回支持的算法/协议列表

        Returns:
            算法标识列表
        """
        ...

    async def run(
        self,
        db: AsyncSession,
        config: dict,
    ) -> ComputeResult:
        """
        模板方法：统一生命周期 init → execute → cleanup

        自动处理异常，保证 cleanup 总会执行。

        Args:
            db: 数据库会话
            config: 计算配置

        Returns:
            ComputeResult 统一结果
        """
        context: dict = {}
        try:
            # Phase 1: 初始化
            logger.info(f"[{self.engine_name}] Initializing compute environment")
            context = await self.initialize(db, config)
            context["_engine"] = self.engine_name

            # Phase 2: 执行
            logger.info(f"[{self.engine_name}] Executing computation")
            result_data = await self.execute(db, context)

            # Phase 3: 构建统一结果
            return ComputeResult(
                success=True,
                data=result_data,
                metrics=result_data.get("metrics", {}),
                engine=self.engine_name,
            )

        except Exception as e:
            logger.error(f"[{self.engine_name}] Computation failed: {e}")
            return ComputeResult(
                success=False,
                data=context,
                error=str(e),
                engine=self.engine_name,
            )

        finally:
            # Phase 4: 清理（保证执行）
            if context:
                try:
                    logger.info(f"[{self.engine_name}] Cleaning up resources")
                    await self.cleanup(context)
                except Exception as cleanup_err:
                    logger.warning(
                        f"[{self.engine_name}] Cleanup failed: {cleanup_err}"
                    )
