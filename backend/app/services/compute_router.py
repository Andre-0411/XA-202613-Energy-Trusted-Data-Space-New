"""
隐私计算路由服务
根据业务场景自动选择隐私计算技术路线

路由矩阵:
  发电预测 → 联邦学习 (FATE)
  交易结算 → MPC
  调度指令 → TEE
  统计分析 → 同态加密 (HE)
  默认     → 差分隐私 (DP)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 业务场景 → 技术路线路由矩阵
SCENARIO_ROUTE_MATRIX: dict[str, dict] = {
    "power_forecast": {
        "task_type": "FL",
        "engine": "FATE",
        "description": "发电预测 → 联邦学习 (FATE)",
        "default_config": {
            "algorithm": "Homo-LR",
            "num_workers": 3,
            "epochs": 10,
            "learning_rate": 0.01,
        },
        "priority": 5,
    },
    "transaction_settlement": {
        "task_type": "MPC",
        "engine": "secret-sharing",
        "description": "交易结算 → 安全多方计算 (MPC)",
        "default_config": {
            "protocol": "SPDZ",
            "parties": 2,
            "field_size": 64,
        },
        "priority": 3,
    },
    "dispatch_command": {
        "task_type": "TEE",
        "engine": "SGX",
        "description": "调度指令 → TEE (可信执行环境)",
        "default_config": {
            "enclave_type": "SGX",
            "memory_size_mb": 512,
            "sealed_storage": True,
        },
        "priority": 2,
    },
    "statistical_analysis": {
        "task_type": "HE",
        "engine": "paillier",
        "description": "统计分析 → 同态加密 (HE)",
        "default_config": {
            "scheme": "Paillier",
            "key_bits": 2048,
            "precision": 64,
        },
        "priority": 6,
    },
    "data_sharing": {
        "task_type": "DP",
        "engine": "laplace",
        "description": "数据共享 → 差分隐私 (DP)",
        "default_config": {
            "epsilon": 1.0,
            "delta": 1e-5,
            "mechanism": "laplace",
        },
        "priority": 7,
    },
}

# 技术路线能力约束
TECH_CAPABILITIES: dict[str, dict] = {
    "FL": {
        "max_participants": 10,
        "supports_model_types": ["logistic_regression", "xgboost", "nn"],
        "min_data_size_mb": 10,
        "requires_network": True,
    },
    "MPC": {
        "max_participants": 5,
        "supports_operations": ["add", "multiply", "compare"],
        "min_data_size_mb": 1,
        "requires_network": True,
    },
    "TEE": {
        "max_participants": 1,
        "supports_hardware": ["SGX", "TrustZone"],
        "min_data_size_mb": 1,
        "requires_network": False,
    },
    "HE": {
        "max_participants": 1,
        "supports_operations": ["add", "multiply"],
        "min_data_size_mb": 1,
        "requires_network": False,
    },
    "DP": {
        "max_participants": 10,
        "supports_mechanisms": ["laplace", "gaussian", "exponential"],
        "min_data_size_mb": 0,
        "requires_network": False,
    },
}


def get_route_for_scenario(scenario: str) -> dict:
    """
    根据业务场景获取推荐的技术路线

    Args:
        scenario: 业务场景标识

    Returns:
        推荐的技术路线信息

    Raises:
        ValueError: 未知的业务场景
    """
    if scenario not in SCENARIO_ROUTE_MATRIX:
        available = list(SCENARIO_ROUTE_MATRIX.keys())
        raise ValueError(
            f"未知的业务场景: {scenario}，可用场景: {available}"
        )

    route = SCENARIO_ROUTE_MATRIX[scenario]
    capabilities = TECH_CAPABILITIES.get(route["task_type"], {})

    return {
        "scenario": scenario,
        "task_type": route["task_type"],
        "engine": route["engine"],
        "description": route["description"],
        "default_config": route["default_config"],
        "priority": route["priority"],
        "capabilities": capabilities,
    }


def get_all_routes() -> list[dict]:
    """
    获取所有可用的路由配置

    Returns:
        所有场景路由列表
    """
    routes = []
    for scenario, route in SCENARIO_ROUTE_MATRIX.items():
        capabilities = TECH_CAPABILITIES.get(route["task_type"], {})
        routes.append({
            "scenario": scenario,
            "task_type": route["task_type"],
            "engine": route["engine"],
            "description": route["description"],
            "priority": route["priority"],
            "capabilities": capabilities,
        })
    return routes


def suggest_task_type(
    scenario: Optional[str] = None,
    data_size_mb: float = 0,
    num_participants: int = 1,
    requires_privacy: bool = True,
) -> dict:
    """
    智能推荐任务类型

    根据多个因素综合推荐最合适的隐私计算技术:
    - 业务场景
    - 数据规模
    - 参与方数量
    - 隐私要求

    Args:
        scenario: 业务场景（可选）
        data_size_mb: 数据规模 (MB)
        num_participants: 参与方数量
        requires_privacy: 是否强制隐私保护

    Returns:
        推荐结果
    """
    # 优先按场景匹配
    if scenario and scenario in SCENARIO_ROUTE_MATRIX:
        route = get_route_for_scenario(scenario)
        return {
            "recommended_type": route["task_type"],
            "engine": route["engine"],
            "reason": f"业务场景 '{scenario}' 匹配: {route['description']}",
            "config_template": route["default_config"],
        }

    # 按参与方数量推荐
    if num_participants > 1:
        if num_participants <= 2:
            return {
                "recommended_type": "MPC",
                "engine": "secret-sharing",
                "reason": f"参与方数量 {num_participants}，适合 MPC 安全多方计算",
                "config_template": SCENARIO_ROUTE_MATRIX["transaction_settlement"]["default_config"],
            }
        else:
            return {
                "recommended_type": "FL",
                "engine": "FATE",
                "reason": f"参与方数量 {num_participants}，适合联邦学习",
                "config_template": SCENARIO_ROUTE_MATRIX["power_forecast"]["default_config"],
            }

    # 按数据规模推荐
    if data_size_mb > 100:
        return {
            "recommended_type": "FL",
            "engine": "FATE",
            "reason": f"数据规模 {data_size_mb}MB 较大，适合联邦学习",
            "config_template": SCENARIO_ROUTE_MATRIX["power_forecast"]["default_config"],
        }

    # 默认推荐同态加密
    return {
        "recommended_type": "HE",
        "engine": "paillier",
        "reason": "默认推荐同态加密，适用于小规模统计分析",
        "config_template": SCENARIO_ROUTE_MATRIX["statistical_analysis"]["default_config"],
    }


def merge_route_config(scenario: str, user_config: dict) -> dict:
    """
    合并路由默认配置和用户自定义配置

    用户配置优先级高于默认配置。

    Args:
        scenario: 业务场景
        user_config: 用户自定义配置

    Returns:
        合并后的配置
    """
    route = get_route_for_scenario(scenario)
    merged = dict(route["default_config"])
    merged.update(user_config)

    # 确保 task_type 和 engine 不被覆盖
    merged["task_type"] = route["task_type"]
    merged["engine"] = route["engine"]

    return merged
