"""
差分隐私服务
应用差分隐私 / DP配置管理 / 隐私预算追踪
"""
import uuid
import math
import random
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compute_task import ComputeTask
from app.exceptions import ComputeError, DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# 差分隐私机制
DP_MECHANISMS = {
    "laplace": {
        "name": "Laplace 机制",
        "description": "基于 Laplace 分布添加噪声，适用于数值型查询",
        "applicable_types": ["numeric", "count", "sum", "avg"],
    },
    "gaussian": {
        "name": "Gaussian 机制",
        "description": "基于高斯分布添加噪声，适用于 (ε,δ)-DP",
        "applicable_types": ["numeric", "count", "sum", "avg"],
    },
    "exponential": {
        "name": "Exponential 机制",
        "description": "基于指数分布选择输出，适用于非数值型查询",
        "applicable_types": ["categorical", "selection", "ranking"],
    },
    "report_noisy_max": {
        "name": "Report Noisy Max 机制",
        "description": "从多个候选项中选择最优，适用于 Top-K 查询",
        "applicable_types": ["top_k", "selection"],
    },
}

# DP 配置模板
DP_CONFIG_TEMPLATES = {
    "strict": {
        "name": "严格模式",
        "epsilon": 0.1,
        "delta": 1e-6,
        "sensitivity": 1.0,
        "mechanism": "laplace",
        "description": "隐私保护最强，数据可用性较低",
    },
    "balanced": {
        "name": "平衡模式",
        "epsilon": 1.0,
        "delta": 1e-5,
        "sensitivity": 1.0,
        "mechanism": "gaussian",
        "description": "隐私保护与数据可用性平衡",
    },
    "relaxed": {
        "name": "宽松模式",
        "epsilon": 10.0,
        "delta": 1e-4,
        "sensitivity": 1.0,
        "mechanism": "laplace",
        "description": "数据可用性较高，隐私保护较弱",
    },
    "statistical": {
        "name": "统计分析模式",
        "epsilon": 2.0,
        "delta": 1e-5,
        "sensitivity": 1.0,
        "mechanism": "gaussian",
        "description": "适用于聚合统计分析",
    },
}

# 隐私预算跟踪
_privacy_budget: dict[str, dict] = {}


async def apply_differential_privacy(
    db: AsyncSession,
    name: str,
    asset_id: str,
    mechanism: str,
    epsilon: float,
    delta: float = 1e-5,
    sensitivity: float = 1.0,
    query_type: str = "count",
    config_template: Optional[str] = None,
    user_id: str = "",
    organization_id: str = "",
) -> dict:
    """
    应用差分隐私

    1. 校验机制
    2. 校验参数
    3. 检查隐私预算
    4. 计算噪声参数
    5. 创建 ComputeTask
    6. 扣除隐私预算
    """
    # 如果指定了模板，使用模板参数
    if config_template and config_template in DP_CONFIG_TEMPLATES:
        template = DP_CONFIG_TEMPLATES[config_template]
        mechanism = template["mechanism"]
        epsilon = template["epsilon"]
        delta = template["delta"]
        sensitivity = template["sensitivity"]

    # 1. 校验机制
    if mechanism not in DP_MECHANISMS:
        raise DataValidationError(
            f"不支持的 DP 机制: {mechanism}，允许值: {list(DP_MECHANISMS.keys())}"
        )

    # 2. 校验参数
    if epsilon <= 0:
        raise DataValidationError("epsilon 必须 > 0")
    if delta < 0 or delta >= 1:
        raise DataValidationError("delta 必须在 [0, 1) 范围内")
    if sensitivity <= 0:
        raise DataValidationError("sensitivity 必须 > 0")

    # 3. 检查隐私预算
    budget = _privacy_budget.get(asset_id, {
        "total_epsilon": 10.0,
        "total_delta": 1e-3,
        "consumed_epsilon": 0.0,
        "consumed_delta": 0.0,
    })

    remaining_epsilon = budget["total_epsilon"] - budget["consumed_epsilon"]
    if epsilon > remaining_epsilon:
        raise ComputeError(
            f"隐私预算不足: 请求 epsilon={epsilon}，剩余 epsilon={remaining_epsilon:.4f}"
        )

    # 4. 计算噪声参数
    noise_params = _calculate_noise_params(mechanism, epsilon, delta, sensitivity)

    # 5. 创建 ComputeTask
    task_config = {
        "mechanism": mechanism,
        "mechanism_name": DP_MECHANISMS[mechanism]["name"],
        "epsilon": epsilon,
        "delta": delta,
        "sensitivity": sensitivity,
        "query_type": query_type,
        "noise_params": noise_params,
        "asset_id": asset_id,
        "config_template": config_template,
    }

    task = ComputeTask(
        name=name,
        task_type="DP",
        scenario="dp_application",
        config=task_config,
        input_asset_ids=[uuid.UUID(asset_id)] if len(asset_id) == 36 else [],
        status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 6. 扣除隐私预算
    budget["consumed_epsilon"] += epsilon
    budget["consumed_delta"] += delta
    budget["last_consumed_at"] = datetime.now(timezone.utc).isoformat()
    _privacy_budget[asset_id] = budget

    logger.info(
        f"DP applied: task={task.id}, mechanism={mechanism}, "
        f"ε={epsilon}, δ={delta}"
    )
    return {
        "task_id": str(task.id),
        "mechanism": mechanism,
        "mechanism_name": DP_MECHANISMS[mechanism]["name"],
        "epsilon": epsilon,
        "delta": delta,
        "sensitivity": sensitivity,
        "noise_params": noise_params,
        "privacy_budget": {
            "total_epsilon": budget["total_epsilon"],
            "consumed_epsilon": budget["consumed_epsilon"],
            "remaining_epsilon": budget["total_epsilon"] - budget["consumed_epsilon"],
        },
    }


async def list_dp_configs() -> dict:
    """查询 DP 配置列表"""
    return {
        "mechanisms": [
            {
                "id": mech_id,
                "name": info["name"],
                "description": info["description"],
                "applicable_types": info["applicable_types"],
            }
            for mech_id, info in DP_MECHANISMS.items()
        ],
        "templates": {
            template_id: {
                "name": info["name"],
                "epsilon": info["epsilon"],
                "delta": info["delta"],
                "sensitivity": info["sensitivity"],
                "mechanism": info["mechanism"],
                "description": info["description"],
            }
            for template_id, info in DP_CONFIG_TEMPLATES.items()
        },
    }


async def get_privacy_budget(
    asset_id: str,
) -> dict:
    """查询资产隐私预算"""
    budget = _privacy_budget.get(asset_id)
    if not budget:
        return {
            "asset_id": asset_id,
            "total_epsilon": 10.0,
            "total_delta": 1e-3,
            "consumed_epsilon": 0.0,
            "consumed_delta": 0.0,
            "remaining_epsilon": 10.0,
            "remaining_delta": 1e-3,
        }

    return {
        "asset_id": asset_id,
        "total_epsilon": budget["total_epsilon"],
        "total_delta": budget["total_delta"],
        "consumed_epsilon": budget["consumed_epsilon"],
        "consumed_delta": budget["consumed_delta"],
        "remaining_epsilon": budget["total_epsilon"] - budget["consumed_epsilon"],
        "remaining_delta": budget["total_delta"] - budget["consumed_delta"],
        "last_consumed_at": budget.get("last_consumed_at"),
    }


def _calculate_noise_params(
    mechanism: str,
    epsilon: float,
    delta: float,
    sensitivity: float,
) -> dict:
    """计算噪声参数"""
    if mechanism == "laplace":
        # Laplace 噪声尺度: b = sensitivity / epsilon
        scale = sensitivity / epsilon
        variance = 2 * scale * scale
        return {
            "distribution": "laplace",
            "scale": round(scale, 6),
            "variance": round(variance, 6),
            "mean": 0.0,
        }

    elif mechanism == "gaussian":
        # Gaussian 噪声标准差: σ = sensitivity * sqrt(2 * ln(1.25/δ)) / ε
        sigma = sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon
        variance = sigma * sigma
        return {
            "distribution": "gaussian",
            "sigma": round(sigma, 6),
            "variance": round(variance, 6),
            "mean": 0.0,
        }

    elif mechanism == "exponential":
        # Exponential 机制的温度参数
        temperature = 2 * sensitivity / epsilon
        return {
            "distribution": "exponential",
            "temperature": round(temperature, 6),
        }

    elif mechanism == "report_noisy_max":
        # Report Noisy Max 使用 Gumbel 噪声
        scale = 2 * sensitivity / epsilon
        return {
            "distribution": "gumbel",
            "scale": round(scale, 6),
        }

    return {"distribution": "unknown"}
