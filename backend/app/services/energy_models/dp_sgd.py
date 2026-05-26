"""
DP-SGD（差分隐私随机梯度下降）
在联邦学习梯度交换中注入差分隐私噪声，防止梯度泄露
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def apply_dp_sgd(
    gradient: np.ndarray,
    epsilon: float = 1.0,
    delta: float = 1e-5,
    sensitivity: float = 1.0,
    batch_size: int = 32,
    noise_type: str = "gaussian",
) -> dict:
    """
    对梯度应用 DP-SGD

    Args:
        gradient: 原始梯度向量
        epsilon: 隐私预算 ε
        delta: 失败概率 δ
        sensitivity: 梯度敏感度（裁剪阈值）
        batch_size: 批次大小
        noise_type: 噪声类型 (gaussian/laplace)

    Returns:
        包含 noisy_gradient, sigma, privacy_params 的字典
    """
    # 梯度裁剪（L2 范数裁剪）
    grad_norm = np.linalg.norm(gradient)
    if grad_norm > sensitivity:
        gradient = gradient / grad_norm * sensitivity
        clipped = True
    else:
        clipped = False

    # 计算噪声尺度
    if noise_type == "gaussian":
        # 高斯机制：σ = Δf * sqrt(2 * ln(1.25/δ)) / ε
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon
        noise = np.random.normal(0, sigma, gradient.shape)
    elif noise_type == "laplace":
        # 拉普拉斯机制：b = Δf / ε
        b = sensitivity / epsilon
        sigma = b
        noise = np.random.laplace(0, b, gradient.shape)
    else:
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / delta)) / epsilon
        noise = np.random.normal(0, sigma, gradient.shape)

    # 注入噪声
    noisy_gradient = gradient + noise / batch_size

    return {
        "noisy_gradient": noisy_gradient,
        "original_norm": round(float(grad_norm), 6),
        "clipped": clipped,
        "sigma": round(float(sigma), 6),
        "noise_norm": round(float(np.linalg.norm(noise)), 6),
        "privacy_params": {
            "epsilon": epsilon,
            "delta": delta,
            "sensitivity": sensitivity,
            "noise_type": noise_type,
        },
    }


def compute_privacy_budget(
    epsilon_per_step: float,
    delta: float,
    num_steps: int,
    composition: str = "rdp",
) -> dict:
    """
    计算总隐私预算消耗

    Args:
        epsilon_per_step: 每步隐私预算
        delta: 失败概率
        num_steps: 总步数
        composition: 组合方式 (basic/advanced/rdp)

    Returns:
        总隐私预算
    """
    if composition == "basic":
        # 基本组合定理：ε_total = n * ε
        total_epsilon = epsilon_per_step * num_steps
    elif composition == "advanced":
        # 高级组合定理（Kairouz et al. 2015）
        total_epsilon = epsilon_per_step * np.sqrt(2 * num_steps * np.log(1 / delta)) + num_steps * epsilon_per_step * (np.exp(epsilon_per_step) - 1)
    elif composition == "rdp":
        # Rényi DP 组合（更紧的界）
        alpha = 1 + 1 / (np.log(1 / epsilon_per_step) if epsilon_per_step < 1 else 1)
        if alpha > 1:
            rdp_epsilon = epsilon_per_step * num_steps / (alpha - 1) + np.log(1 / delta) / (alpha - 1)
            total_epsilon = min(rdp_epsilon, epsilon_per_step * num_steps)
        else:
            total_epsilon = epsilon_per_step * num_steps
    else:
        total_epsilon = epsilon_per_step * num_steps

    return {
        "total_epsilon": round(float(total_epsilon), 4),
        "epsilon_per_step": epsilon_per_step,
        "delta": delta,
        "num_steps": num_steps,
        "composition": composition,
        "privacy_guarantee": f"({round(total_epsilon, 2)}, {delta})-DP",
    }


def clip_gradients(gradients: list, max_norm: float = 1.0) -> list:
    """批量梯度裁剪"""
    clipped = []
    for grad in gradients:
        norm = np.linalg.norm(grad)
        if norm > max_norm:
            clipped.append(grad / norm * max_norm)
        else:
            clipped.append(grad)
    return clipped
