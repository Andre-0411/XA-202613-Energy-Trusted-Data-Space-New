"""
隐私计算统一接口层

提供 PrivacyComputeInterface 抽象基类和 ComputeResult 统一返回格式，
以及 FL/MPC/TEE/HE/DP 五种计算模式的适配器实现。

Usage:
    from app.services.privacy import get_compute_service, ComputeResult

    service = get_compute_service("FL")
    result = await service.run(db, config)
"""
from app.services.privacy.compute_interface import (
    PrivacyComputeInterface,
    ComputeResult,
)
from app.services.privacy.service_registry import (
    get_compute_service,
    list_available_services,
    SERVICE_REGISTRY,
)

__all__ = [
    "PrivacyComputeInterface",
    "ComputeResult",
    "get_compute_service",
    "list_available_services",
    "SERVICE_REGISTRY",
]
