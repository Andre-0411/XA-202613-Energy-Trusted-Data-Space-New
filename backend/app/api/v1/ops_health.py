"""
故障自愈与健康检查 API - /api/v1/ops/health
增强健康检查 + 依赖项检查 + 自动重启配置 + 重启脚本生成
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from app.utils.deps import get_current_user
from app.services import health_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/check", summary="完整健康检查")
async def full_health_check(
    user: dict = Depends(get_current_user),
):
    """
    执行完整健康检查

    包含系统资源、应用状态、数据库、缓存、依赖服务。
    如果整体状态为 critical 且自动重启启用，将触发自愈流程。
    """
    result = await health_service.run_full_health_check()
    return result


@router.get("/history", summary="健康检查历史")
async def get_health_history(
    limit: int = Query(default=50, description="返回数量"),
    user: dict = Depends(get_current_user),
):
    """获取最近的健康检查历史记录"""
    history = await health_service.get_health_history(limit=limit)
    return {"history": history, "total": len(history)}


@router.get("/healing-actions", summary="自愈操作日志")
async def get_healing_actions(
    limit: int = Query(default=50, description="返回数量"),
    user: dict = Depends(get_current_user),
):
    """获取自愈操作日志（自动重启记录）"""
    actions = await health_service.get_healing_actions(limit=limit)
    return {"actions": actions, "total": len(actions)}


@router.get("/dependencies", summary="依赖服务检查")
async def check_dependencies(
    user: dict = Depends(get_current_user),
):
    """检查所有配置的依赖服务状态"""
    results = await health_service.check_all_dependencies()
    return {"dependencies": results, "total": len(results)}


@router.get("/config", summary="获取自愈配置")
async def get_healing_config(
    user: dict = Depends(get_current_user),
):
    """获取当前自愈策略配置"""
    config = await health_service.get_healing_config()
    return config


@router.put("/config", summary="更新自愈配置")
async def update_healing_config(
    config: dict,
    user: dict = Depends(get_current_user),
):
    """
    更新自愈策略配置

    可配置项:
    - max_restart_attempts: 最大重启尝试次数
    - restart_cooldown_seconds: 重启冷却时间（秒）
    - health_check_interval_seconds: 健康检查间隔（秒）
    - auto_restart_enabled: 是否启用自动重启
    - notify_on_restart: 重启时是否通知
    """
    result = await health_service.update_healing_config(config)
    return result


@router.get("/dependencies/config", summary="列出依赖服务配置")
async def list_dependency_configs(
    user: dict = Depends(get_current_user),
):
    """列出所有配置的依赖服务"""
    configs = await health_service.list_dependency_configs()
    return {"dependencies": configs, "total": len(configs)}


@router.post("/dependencies/config", summary="添加依赖服务配置")
async def add_dependency_config(
    service_key: str = Query(description="服务标识键"),
    config: dict = {},
    user: dict = Depends(get_current_user),
):
    """
    添加依赖服务配置

    配置项:
    - name: 服务名称
    - type: 类型（database/cache/mq/other）
    - check_command: 健康检查命令
    - check_args: 命令参数列表
    - restart_command: 重启命令
    - critical: 是否为关键服务
    - timeout: 检查超时（秒）
    """
    result = await health_service.add_dependency_config(service_key, config)
    return {"service_key": service_key, "config": result}


@router.get(
    "/restart-script",
    response_class=PlainTextResponse,
    summary="获取自动重启脚本",
)
async def get_restart_script(
    user: dict = Depends(get_current_user),
):
    """
    获取自动生成的自动重启 Shell 脚本

    可部署到 crontab 中定期执行。
    """
    script = await health_service.generate_restart_script()
    return script
