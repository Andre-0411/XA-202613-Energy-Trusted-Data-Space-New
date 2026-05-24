"""
隐私计算服务注册中心

提供 mode → service 实例的字典映射，
供 privacy_router.py 和上层调用者使用。
"""
import logging
from typing import Optional

from app.services.privacy.compute_interface import PrivacyComputeInterface
from app.services.privacy.fl_adapter import FLComputeService
from app.services.privacy.mpc_adapter import MPCComputeService
from app.services.privacy.tee_adapter import TEEComputeService
from app.services.privacy.he_adapter import HEComputeService
from app.services.privacy.dp_adapter import DPComputeService

logger = logging.getLogger(__name__)

# ==================== 服务注册表 ====================

SERVICE_REGISTRY: dict[str, PrivacyComputeInterface] = {
    "FL": FLComputeService(),
    "MPC": MPCComputeService(),
    "TEE": TEEComputeService(),
    "HE": HEComputeService(),
    "DP": DPComputeService(),
}


def get_compute_service(mode: str) -> Optional[PrivacyComputeInterface]:
    """
    根据计算模式获取对应的服务实例

    Args:
        mode: 计算模式标识 (FL/MPC/TEE/HE/DP)

    Returns:
        对应的 PrivacyComputeInterface 实例，未找到返回 None
    """
    service = SERVICE_REGISTRY.get(mode.upper())
    if not service:
        logger.warning(f"Unknown compute mode: {mode}")
    return service


def list_available_services() -> list[dict]:
    """
    列出所有已注册的隐私计算服务

    Returns:
        服务信息列表
    """
    services = []
    for mode, service in SERVICE_REGISTRY.items():
        services.append({
            "mode": mode,
            "engine_name": service.engine_name,
            "description": service.engine_description,
            "supported_algorithms": service.get_supported_algorithms(),
        })
    return services
