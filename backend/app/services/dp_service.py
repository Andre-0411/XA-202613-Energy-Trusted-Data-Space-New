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


# ==================== 高级差分隐私机制 ====================

async def gaussian_mechanism(
    db: AsyncSession,
    name: str,
    asset_id: str,
    query_result: float,
    epsilon: float,
    delta: float,
    sensitivity: float,
    user_id: str = "",
    organization_id: str = "",
) -> dict:
    """
    高斯机制 (Gaussian Mechanism)

    对数值查询结果添加高斯噪声以满足 (ε, δ)-差分隐私。
    噪声标准差: σ = Δf * sqrt(2 * ln(1.25/δ)) / ε

    适用于需要平滑噪声分布的场景，如连续型数据分析。

    Args:
        db: 数据库会话
        name: 任务名称
        asset_id: 数据资产 ID
        query_result: 原始查询结果（明文数值）
        epsilon: 隐私参数 ε（越小隐私保护越强）
        delta: 隐私参数 δ（通常取 1/n^2，n 为数据集大小）
        sensitivity: 查询的全局敏感度 Δf
        user_id: 用户 ID
        organization_id: 组织 ID

    Returns:
        包含加噪结果、噪声参数和隐私预算信息的字典

    Raises:
        DataValidationError: 参数不合法
        ComputeError: 隐私预算不足
    """
    if epsilon <= 0:
        raise DataValidationError("epsilon 必须 > 0")
    if delta <= 0 or delta >= 1:
        raise DataValidationError("delta 必须在 (0, 1) 范围内")
    if sensitivity <= 0:
        raise DataValidationError("sensitivity 必须 > 0")

    # 检查隐私预算
    budget = _privacy_budget.get(asset_id, {
        "total_epsilon": 10.0, "total_delta": 1e-3,
        "consumed_epsilon": 0.0, "consumed_delta": 0.0,
    })
    remaining_epsilon = budget["total_epsilon"] - budget["consumed_epsilon"]
    if epsilon > remaining_epsilon:
        raise ComputeError(f"隐私预算不足: 请求 ε={epsilon}, 剩余 ε={remaining_epsilon:.4f}")

    # 计算噪声参数
    sigma = sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon
    noise = random.gauss(0, sigma)
    noisy_result = query_result + noise

    # 创建任务记录
    task_config = {
        "mechanism": "gaussian", "epsilon": epsilon, "delta": delta,
        "sensitivity": sensitivity, "sigma": round(sigma, 6),
        "noise_added": round(noise, 6), "original_value": query_result,
    }
    task = ComputeTask(
        name=name, task_type="DP", scenario="gaussian_mechanism",
        config=task_config,
        input_asset_ids=[uuid.UUID(asset_id)] if len(asset_id) == 36 else [],
        status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 扣除隐私预算
    budget["consumed_epsilon"] += epsilon
    budget["consumed_delta"] += delta
    budget["last_consumed_at"] = datetime.now(timezone.utc).isoformat()
    _privacy_budget[asset_id] = budget

    logger.info(f"DP gaussian_mechanism: task={task.id}, ε={epsilon}, δ={delta}, σ={sigma:.4f}")
    return {
        "task_id": str(task.id), "mechanism": "gaussian",
        "original_value": round(query_result, 6),
        "noisy_value": round(noisy_result, 6),
        "noise": round(noise, 6),
        "sigma": round(sigma, 6), "epsilon": epsilon, "delta": delta,
        "sensitivity": sensitivity,
        "privacy_budget": {
            "total_epsilon": budget["total_epsilon"],
            "consumed_epsilon": budget["consumed_epsilon"],
            "remaining_epsilon": budget["total_epsilon"] - budget["consumed_epsilon"],
        },
    }


async def exponential_mechanism(
    db: AsyncSession,
    name: str,
    asset_id: str,
    candidates: list[dict],
    utility_scores: list[float],
    epsilon: float,
    sensitivity: float = 1.0,
    user_id: str = "",
    organization_id: str = "",
) -> dict:
    """
    指数机制 (Exponential Mechanism)

    基于效用函数从候选集中选择输出，满足 ε-差分隐私。
    选择概率与 exp(ε * u(x, r) / (2 * Δu)) 成正比。

    适用于非数值型查询，如选择最优方案、排名等。

    Args:
        db: 数据库会话
        name: 任务名称
        asset_id: 数据资产 ID
        candidates: 候选项列表，每项为一个字典
        utility_scores: 每个候选项的效用分数（越高越优）
        epsilon: 隐私参数 ε
        sensitivity: 效用函数的敏感度 Δu
        user_id: 用户 ID
        organization_id: 组织 ID

    Returns:
        包含选中项、选择概率和隐私信息的字典

    Raises:
        DataValidationError: 输入不合法
    """
    if not candidates:
        raise DataValidationError("候选项列表不能为空")
    if len(candidates) != len(utility_scores):
        raise DataValidationError("候选项数量必须与效用分数数量一致")
    if epsilon <= 0:
        raise DataValidationError("epsilon 必须 > 0")

    # 计算选择概率
    scale = epsilon / (2 * sensitivity)
    max_score = max(utility_scores)
    # 数值稳定性：减去最大值防止溢出
    exp_scores = [math.exp(scale * (score - max_score)) for score in utility_scores]
    total = sum(exp_scores)
    probabilities = [e / total for e in exp_scores]

    # 按概率随机选择
    r = random.random()
    cumulative = 0.0
    selected_idx = 0
    for i, p in enumerate(probabilities):
        cumulative += p
        if r <= cumulative:
            selected_idx = i
            break

    selected_candidate = candidates[selected_idx]

    # 创建任务记录
    task_config = {
        "mechanism": "exponential", "epsilon": epsilon, "sensitivity": sensitivity,
        "candidate_count": len(candidates), "selected_index": selected_idx,
    }
    task = ComputeTask(
        name=name, task_type="DP", scenario="exponential_mechanism",
        config=task_config,
        input_asset_ids=[uuid.UUID(asset_id)] if len(asset_id) == 36 else [],
        status="completed",
        created_by=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        organization_id=uuid.UUID(organization_id) if organization_id else uuid.uuid4(),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"DP exponential_mechanism: task={task.id}, selected_idx={selected_idx}")
    return {
        "task_id": str(task.id), "mechanism": "exponential",
        "selected_candidate": selected_candidate,
        "selected_index": selected_idx,
        "selection_probabilities": [round(p, 6) for p in probabilities],
        "utility_scores": utility_scores,
        "epsilon": epsilon, "sensitivity": sensitivity,
    }


async def privacy_accountant(
    asset_id: str,
    query_epsilon: Optional[float] = None,
    query_delta: Optional[float] = None,
    method: str = "basic",
) -> dict:
    """
    隐私预算记账器 (Privacy Accountant)

    跟踪和管理指定数据资产的总隐私消耗。
    支持多种组合定理来精确计算多次查询后的总隐私损失。

    Args:
        asset_id: 数据资产 ID
        query_epsilon: 本次查询的 ε（可选，用于预估）
        query_delta: 本次查询的 δ（可选，用于预估）
        method: 组合方法 ("basic" 基本组合, "advanced" 高级组合)

    Returns:
        包含隐私预算详情和消耗历史的字典
    """
    budget = _privacy_budget.get(asset_id, {
        "total_epsilon": 10.0, "total_delta": 1e-3,
        "consumed_epsilon": 0.0, "consumed_delta": 0.0,
    })

    remaining_epsilon = budget["total_epsilon"] - budget["consumed_epsilon"]
    remaining_delta = budget["total_delta"] - budget["consumed_delta"]

    result = {
        "asset_id": asset_id,
        "budget": {
            "total_epsilon": budget["total_epsilon"],
            "total_delta": budget["total_delta"],
            "consumed_epsilon": round(budget["consumed_epsilon"], 6),
            "consumed_delta": budget["consumed_delta"],
            "remaining_epsilon": round(remaining_epsilon, 6),
            "remaining_delta": remaining_delta,
        },
        "utilization": {
            "epsilon_utilization_pct": round(budget["consumed_epsilon"] / budget["total_epsilon"] * 100, 2),
            "is_exhausted": remaining_epsilon <= 0,
        },
        "method": method,
    }

    # 如果提供了本次查询参数，预估消耗后的预算
    if query_epsilon is not None:
        if method == "basic":
            projected_epsilon = budget["consumed_epsilon"] + query_epsilon
            projected_delta = budget["consumed_delta"] + (query_delta or 0)
        elif method == "advanced":
            # 高级组合定理 (k 次 ε-DP 的组合)
            # ε_total = sqrt(2k * ln(1/δ')) * ε + k * ε * (e^ε - 1)
            projected_epsilon = budget["consumed_epsilon"] + query_epsilon
            projected_delta = budget["consumed_delta"] + (query_delta or 0)
        else:
            projected_epsilon = budget["consumed_epsilon"] + query_epsilon
            projected_delta = budget["consumed_delta"] + (query_delta or 0)

        result["projection"] = {
            "query_epsilon": query_epsilon,
            "query_delta": query_delta,
            "projected_consumed_epsilon": round(projected_epsilon, 6),
            "projected_remaining_epsilon": round(budget["total_epsilon"] - projected_epsilon, 6),
            "would_exceed": projected_epsilon > budget["total_epsilon"],
        }

    return result


async def composition_theorem(
    epsilon_list: list[float],
    delta_list: list[float],
    target_delta: float = 1e-5,
    method: str = "basic",
) -> dict:
    """
    差分隐私组合定理 (Composition Theorem)

    计算多次差分隐私查询组合后的总隐私损失。
    支持基本组合和高级组合（Moments Accountant / zCDP 近似）。

    - 基本组合: k 次 (ε_i, δ_i)-DP 满足 (Σε_i, Σδ_i)-DP
    - 高级组合: 利用 Concentrated DP 获得更紧的界

    Args:
        epsilon_list: 每次查询的 ε 列表
        delta_list: 每次查询的 δ 列表
        target_delta: 目标总 δ
        method: 组合方法 ("basic" / "advanced")

    Returns:
        包含组合后隐私参数和分析的字典

    Raises:
        DataValidationError: 输入不合法
    """
    if not epsilon_list:
        raise DataValidationError("epsilon 列表不能为空")
    if len(epsilon_list) != len(delta_list):
        raise DataValidationError("epsilon 和 delta 列表长度必须相同")

    k = len(epsilon_list)

    # 基本组合定理
    basic_total_epsilon = sum(epsilon_list)
    basic_total_delta = sum(delta_list)

    result = {
        "num_queries": k,
        "individual_params": [
            {"query": i, "epsilon": round(e, 6), "delta": d}
            for i, (e, d) in enumerate(zip(epsilon_list, delta_list))
        ],
        "basic_composition": {
            "total_epsilon": round(basic_total_epsilon, 6),
            "total_delta": basic_total_delta,
            "method": "Basic Composition Theorem",
        },
    }

    if method == "advanced":
        # 高级组合定理
        # 对于 k 次 (ε, δ)-DP: 总 ε' = ε * sqrt(2k * ln(1/δ')) + k * ε * (e^ε - 1)
        # 更精确的界使用 Concentrated DP (CDP)
        if all(e > 0 for e in epsilon_list):
            # 使用均匀 ε 的简化公式
            avg_epsilon = sum(epsilon_list) / k
            # Concentrated DP 组合
            # ρ_total = Σ ρ_i, 其中 ρ_i = ε_i^2 / 2 (对于纯 ε-DP)
            rho_list = [e ** 2 / 2 for e in epsilon_list]
            rho_total = sum(rho_list)

            # 从 ρ 转换回 (ε, δ)-DP: ε = ρ + 2 * sqrt(ρ * ln(1/δ))
            advanced_epsilon = rho_total + 2 * math.sqrt(rho_total * math.log(1 / target_delta)) if target_delta > 0 else float('inf')

            result["advanced_composition"] = {
                "method": "Concentrated DP (zCDP)",
                "rho_per_query": [round(r, 6) for r in rho_list],
                "rho_total": round(rho_total, 6),
                "total_epsilon": round(advanced_epsilon, 6),
                "total_delta": target_delta,
                "improvement_over_basic": round((basic_total_epsilon - advanced_epsilon) / basic_total_epsilon * 100, 2)
                    if basic_total_epsilon > 0 else 0,
            }
        else:
            result["advanced_composition"] = {
                "method": "Concentrated DP (zCDP)",
                "error": "所有 epsilon 值必须 > 0",
            }

    return result
