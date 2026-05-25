"""
后台任务调度器
计算任务执行 / 超时处理 / 重试
"""
import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timezone, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class TaskScheduler:
    """后台任务调度器"""

    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_timeouts: Dict[str, int] = {}  # task_id -> timeout_seconds
        self._max_retries = 3
        self._is_running = False

    async def start(self) -> None:
        """启动调度器"""
        self._is_running = True
        logger.info("Task scheduler started")

    async def stop(self) -> None:
        """停止调度器"""
        self._is_running = False
        for task_id, task in self._running_tasks.items():
            task.cancel()
            logger.info(f"Cancelled running task: {task_id}")
        self._running_tasks.clear()
        logger.info("Task scheduler stopped")

    async def submit_task(
        self,
        task_id: str,
        coroutine_factory: Callable,
        timeout_seconds: int = 3600,
        retry_count: int = 0,
    ) -> None:
        """
        提交任务

        Args:
            task_id: 任务 ID
            coroutine_factory: 协程工厂函数
            timeout_seconds: 超时秒数
            retry_count: 当前重试次数
        """
        if task_id in self._running_tasks:
            logger.warning(f"Task {task_id} already running")
            return

        self._task_timeouts[task_id] = timeout_seconds
        task = asyncio.create_task(
            self._execute_with_timeout(task_id, coroutine_factory, timeout_seconds, retry_count)
        )
        self._running_tasks[task_id] = task

    async def _execute_with_timeout(
        self,
        task_id: str,
        coroutine_factory: Callable,
        timeout_seconds: int,
        retry_count: int,
    ) -> None:
        """带超时执行任务"""
        try:
            result = await asyncio.wait_for(
                coroutine_factory(),
                timeout=timeout_seconds,
            )
            logger.info(f"Task {task_id} completed successfully")
        except asyncio.TimeoutError:
            logger.error(f"Task {task_id} timed out after {timeout_seconds}s")
            await self._handle_timeout(task_id, coroutine_factory, retry_count)
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled")
        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            logger.error(f"Task {task_id} failed: {e}")
            await self._handle_failure(task_id, coroutine_factory, e, retry_count)
        finally:
            self._running_tasks.pop(task_id, None)
            self._task_timeouts.pop(task_id, None)

    async def _handle_timeout(
        self,
        task_id: str,
        coroutine_factory: Callable,
        retry_count: int,
    ) -> None:
        """处理任务超时"""
        if retry_count < self._max_retries:
            logger.info(f"Retrying task {task_id} (attempt {retry_count + 1})")
            await self.submit_task(
                task_id, coroutine_factory,
                self._task_timeouts.get(task_id, 3600),
                retry_count + 1,
            )
        else:
            logger.error(f"Task {task_id} exceeded max retries after timeout")

    async def _handle_failure(
        self,
        task_id: str,
        coroutine_factory: Callable,
        error: Exception,
        retry_count: int,
    ) -> None:
        """处理任务失败"""
        if retry_count < self._max_retries:
            logger.info(f"Retrying task {task_id} after error (attempt {retry_count + 1})")
            await self.submit_task(
                task_id, coroutine_factory,
                self._task_timeouts.get(task_id, 3600),
                retry_count + 1,
            )
        else:
            logger.error(f"Task {task_id} exceeded max retries: {error}")

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            self._running_tasks.pop(task_id, None)
            logger.info(f"Task {task_id} cancelled")
            return True
        return False

    def get_running_tasks(self) -> list[str]:
        """获取正在运行的任务 ID 列表"""
        return list(self._running_tasks.keys())

    def get_task_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            if task.done():
                return "completed"
            elif task.cancelled():
                return "cancelled"
            return "running"
        return None


# 全局调度器实例
task_scheduler = TaskScheduler()
