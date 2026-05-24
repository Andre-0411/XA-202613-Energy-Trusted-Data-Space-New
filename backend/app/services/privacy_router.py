"""
隐私计算路由服务
根据业务场景自动选择最佳隐私计算技术
路由矩阵：联合预测→FL、安全结算→MPC、调度优化→TEE、统计查询→HE、信用评估→VFL

集成 PrivacyComputeInterface 统一接口层，通过 SERVICE_REGISTRY
实现 mode → service 实例的字典映射。
"""
import logging
from typing import Optional

from app.exceptions import DataValidationError
from app.services.privacy import get_compute_service, list_available_services, SERVICE_REGISTRY

logger = logging.getLogger(__name__)

# ==================== 路由矩阵 ====================

# 场景 → 推荐技术 / 备选技术 / 说明
ROUTING_MATRIX = {
    "联合预测": {
        "recommended": "FL",
        "alternatives": ["MPC"],
        "description": "多方联合预测，使用联邦学习在各参与方本地训练模型",
        "typical_algorithms": ["homo_lr", "homo_nn", "secureboost"],
    },
    "安全结算": {
        "recommended": "MPC",
        "alternatives": ["TEE"],
        "description": "多方安全结算，使用安全多方计算保护各方数据隐私",
        "typical_algorithms": ["secret_sharing", "garbled_circuit", "beaver_triples"],
    },
    "调度优化": {
        "recommended": "TEE",
        "alternatives": ["FL"],
        "description": "调度优化计算，在可信执行环境中进行敏感计算",
        "typical_algorithms": ["gramine", "sgx_enclave"],
    },
    "统计查询": {
        "recommended": "HE",
        "alternatives": ["DP"],
        "description": "加密数据统计查询，使用同态加密直接在密文上计算",
        "typical_algorithms": ["paillier", "ckks", "bfv"],
    },
    "信用评估": {
        "recommended": "VFL",
        "alternatives": ["MPC"],
        "description": "纵向联邦信用评估，多方特征联合建模",
        "typical_algorithms": ["hetero_lr", "hetero_nn", "hetero_secureboost"],
    },
    "数据对齐": {
        "recommended": "PSI",
        "alternatives": ["MPC"],
        "description": "隐私集合求交，多方数据对齐不泄露各自数据集",
        "typical_algorithms": ["rsa_psi", "ecdh_psi", "kkrt_psi"],
    },
    "联合建模": {
        "recommended": "FL",
        "alternatives": ["MPC", "TEE"],
        "description": "多方联合建模训练",
        "typical_algorithms": ["homo_lr", "hetero_lr", "secureboost"],
    },
    "隐私分析": {
        "recommended": "HE",
        "alternatives": ["DP", "MPC"],
        "description": "隐私保护数据分析",
        "typical_algorithms": ["paillier", "ckks"],
    },
    # 能源行业专用场景
    "负荷预测": {
        "recommended": "FL",
        "alternatives": ["MPC", "TEE"],
        "description": "多方联合负荷预测，各节点本地训练后聚合，保护用户用电隐私",
        "typical_algorithms": ["homo_lr", "homo_nn", "secureboost", "fed_avg"],
    },
    "价格协商": {
        "recommended": "MPC",
        "alternatives": ["TEE"],
        "description": "多方安全电价协商，各方报价不泄露，仅输出协商结果",
        "typical_algorithms": ["secret_sharing", "garbled_circuit", "beaver_triples", "aby3"],
    },
    "碳排放": {
        "recommended": "TEE",
        "alternatives": ["HE", "MPC"],
        "description": "碳排放数据可信计算，在安全区内完成碳指标核算与验证",
        "typical_algorithms": ["gramine", "sgx_enclave", "trustzone"],
    },
    "安全审计": {
        "recommended": "HE",
        "alternatives": ["DP"],
        "description": "加密数据安全审计，使用同态加密对密文数据进行合规审计",
        "typical_algorithms": ["ckks", "bfv", "bgv"],
    },
}

# 技术描述
TECHNOLOGY_INFO = {
    "FL": {
        "name": "联邦学习 (Federated Learning)",
        "short_name": "FL",
        "description": "多方协作训练模型，数据不出本地",
        "strengths": ["保护原始数据", "支持复杂模型", "适合大规模数据"],
        "weaknesses": ["通信开销大", "需多次迭代", "模型精度可能略低"],
    },
    "VFL": {
        "name": "纵向联邦学习 (Vertical FL)",
        "short_name": "VFL",
        "description": "多方特征联合建模，适用于特征不同但样本重叠的场景",
        "strengths": ["特征互补", "标签方主导", "支持复杂模型"],
        "weaknesses": ["需要样本对齐", "通信开销较大"],
    },
    "MPC": {
        "name": "安全多方计算 (Secure Multi-Party Computation)",
        "short_name": "MPC",
        "description": "多方协同计算，各方输入均被保护",
        "strengths": ["信息论安全", "精确计算", "无需可信第三方"],
        "weaknesses": ["通信开销大", "计算复杂度高", "参与方数量受限"],
    },
    "TEE": {
        "name": "可信执行环境 (Trusted Execution Environment)",
        "short_name": "TEE",
        "description": "在硬件安全区内执行计算，数据在使用过程中被保护",
        "strengths": ["高性能", "通用计算", "硬件级安全"],
        "weaknesses": ["依赖特定硬件", "侧信道风险", "需远程证明"],
    },
    "HE": {
        "name": "同态加密 (Homomorphic Encryption)",
        "short_name": "HE",
        "description": "在密文上直接计算，结果解密后与明文计算一致",
        "strengths": ["密码学安全", "无需交互", "适合统计查询"],
        "weaknesses": ["计算开销极大", "仅支持有限运算", "密文膨胀"],
    },
    "DP": {
        "name": "差分隐私 (Differential Privacy)",
        "short_name": "DP",
        "description": "通过添加噪声保护个体隐私",
        "strengths": ["数学可证明", "可量化隐私", "简单高效"],
        "weaknesses": ["精度-隐私权衡", "不适合小数据集"],
    },
    "PSI": {
        "name": "隐私集合求交 (Private Set Intersection)",
        "short_name": "PSI",
        "description": "求多方数据集的交集，不泄露非交集部分",
        "strengths": ["精确求交", "不泄露非交集", "高效"],
        "weaknesses": ["仅支持集合运算", "通信开销与集合大小相关"],
    },
}

# 技术可用性（各引擎是否就绪）
_engine_status: dict[str, bool] = {
    "FL": True,       # FATE 集成
    "VFL": True,      # FATE 纵向
    "MPC": True,      # MPC 服务
    "TEE": True,      # Gramine TEE
    "HE": True,       # 同态加密
    "DP": True,       # 差分隐私
    "PSI": True,      # PSI
}


# ==================== 路由接口 ====================

async def route_task(
    task_description: str,
    data_sensitivity: str = "high",
    participants: int = 2,
    scenario: Optional[str] = None,
    requirements: Optional[dict] = None,
) -> dict:
    """
    隐私计算技术路由推荐

    根据业务场景、数据敏感度、参与方数量自动推荐最佳技术方案

    Args:
        task_description: 任务描述（自然语言）
        data_sensitivity: 数据敏感度 ("low", "medium", "high", "critical")
        participants: 参与方数量
        scenario: 业务场景（可选，自动推断）
        requirements: 额外需求（可选）

    Returns:
        {
            "technology": 推荐技术,
            "technology_info": 技术详情,
            "config": 建议配置,
            "alternatives": 备选方案,
            "reasoning": 推荐理由,
        }
    """
    # 1. 自动推断场景
    if not scenario:
        scenario = _infer_scenario(task_description)

    # 2. 获取路由推荐
    route_info = ROUTING_MATRIX.get(scenario)
    if not route_info:
        # 默认推荐 FL
        route_info = ROUTING_MATRIX["联合建模"]

    recommended_tech = route_info["recommended"]
    alternatives = route_info["alternatives"]

    # 3. 检查技术可用性
    available_tech = recommended_tech
    if not _is_engine_available(recommended_tech):
        # 推荐技术不可用，尝试备选
        for alt in alternatives:
            if _is_engine_available(alt):
                available_tech = alt
                break
        else:
            # 所有技术都不可用
            return {
                "technology": None,
                "error": "当前无可用的隐私计算引擎",
                "scenario": scenario,
                "requested_technology": recommended_tech,
            }

    # 4. 生成建议配置
    config = _generate_tech_config(available_tech, participants, data_sensitivity, requirements)

    # 5. 推荐理由
    reasoning = _generate_reasoning(
        scenario, available_tech, data_sensitivity, participants
    )

    tech_info = TECHNOLOGY_INFO.get(available_tech, {})

    result = {
        "technology": available_tech,
        "technology_name": tech_info.get("name", available_tech),
        "scenario": scenario,
        "scenario_description": route_info.get("description", ""),
        "technology_info": tech_info,
        "config": config,
        "alternatives": [
            {
                "technology": alt,
                "technology_name": TECHNOLOGY_INFO.get(alt, {}).get("name", alt),
                "available": _is_engine_available(alt),
            }
            for alt in alternatives
        ],
        "reasoning": reasoning,
    }

    logger.info(
        f"隐私计算路由: scenario={scenario}, recommended={available_tech}, "
        f"sensitivity={data_sensitivity}, participants={participants}"
    )
    return result


async def list_technologies() -> dict:
    """列出所有隐私计算技术及可用状态"""
    technologies = []
    for tech_id, info in TECHNOLOGY_INFO.items():
        technologies.append({
            "technology": tech_id,
            "name": info["name"],
            "description": info["description"],
            "strengths": info["strengths"],
            "weaknesses": info["weaknesses"],
            "available": _is_engine_available(tech_id),
        })
    return {"technologies": technologies}


async def list_scenarios() -> dict:
    """列出所有支持的业务场景"""
    scenarios = []
    for scenario_id, info in ROUTING_MATRIX.items():
        scenarios.append({
            "scenario": scenario_id,
            "description": info["description"],
            "recommended_technology": info["recommended"],
            "alternatives": info["alternatives"],
            "typical_algorithms": info["typical_algorithms"],
        })
    return {"scenarios": scenarios}


async def check_engine_status() -> dict:
    """检查各隐私计算引擎状态（使用统一注册表）"""
    engines = {}
    for tech, available in _engine_status.items():
        info = TECHNOLOGY_INFO.get(tech, {})
        engines[tech] = {
            "available": available,
            "name": info.get("name", tech),
        }
        # 如果注册表中有对应服务，附加支持的算法
        service = get_compute_service(tech)
        if service:
            engines[tech]["supported_algorithms"] = service.get_supported_algorithms()
            engines[tech]["interface_available"] = True
        else:
            engines[tech]["interface_available"] = False
    return {"engines": engines}


async def execute_privacy_compute(
    mode: str,
    config: dict,
    db=None,
) -> dict:
    """
    通过统一接口执行隐私计算

    使用 PrivacyComputeInterface 的 run() 模板方法，
    自动处理 init → execute → cleanup 生命周期。

    Args:
        mode: 计算模式 (FL/MPC/TEE/HE/DP)
        config: 计算配置（传递给对应引擎的 initialize）
        db: 数据库会话（AsyncSession）

    Returns:
        ComputeResult.to_dict() 格式的统一结果
    """
    service = get_compute_service(mode)
    if not service:
        return {
            "success": False,
            "error": f"不支持的计算模式: {mode}，允许值: {list(SERVICE_REGISTRY.keys())}",
            "engine": mode,
        }

    if db is None:
        return {
            "success": False,
            "error": "数据库会话 (db) 不能为空",
            "engine": mode,
        }

    result = await service.run(db, config)
    return result.to_dict()


def update_engine_status(technology: str, available: bool) -> None:
    """更新引擎可用状态"""
    if technology in _engine_status:
        _engine_status[technology] = available
        logger.info(f"引擎状态更新: {technology} -> {'可用' if available else '不可用'}")


# ==================== 辅助函数 ====================

def _infer_scenario(description: str) -> str:
    """从任务描述中推断业务场景"""
    description_lower = description.lower()

    # 关键词匹配
    keyword_mapping = {
        "联合预测": ["预测", "forecast", "predict", "发电", "功率"],
        "安全结算": ["结算", "settle", "payment", "账单", "计费"],
        "调度优化": ["调度", "dispatch", "optimize", "优化", "排程"],
        "统计查询": ["统计", "statistic", "aggregate", "汇总", "平均"],
        "信用评估": ["信用", "credit", "评估", "评分", "风险"],
        "数据对齐": ["对齐", "align", "求交", "intersection", "匹配"],
        "联合建模": ["建模", "model", "训练", "train", "学习"],
        "隐私分析": ["分析", "analysis", "隐私", "privacy"],
        # 能源行业关键词
        "负荷预测": ["负荷", "load", "用电", "需求", "需求侧", "demand", "电量预测"],
        "价格协商": ["价格", "price", "电价", "协商", "negotiate", "交易", "trade", "market"],
        "碳排放": ["碳", "carbon", "排放", "emission", "二氧化碳", "co2", "碳指标", "碳交易"],
        "安全审计": ["审计", "audit", "合规", "compliance", "监管", "supervise"],
    }

    for scenario, keywords in keyword_mapping.items():
        for keyword in keywords:
            if keyword in description_lower:
                return scenario

    return "联合建模"  # 默认


def _is_engine_available(technology: str) -> bool:
    """检查指定技术引擎是否可用"""
    return _engine_status.get(technology, False)


def _generate_tech_config(
    technology: str,
    participants: int,
    sensitivity: str,
    requirements: Optional[dict] = None,
) -> dict:
    """生成技术建议配置"""
    req = requirements or {}

    base_config = {
        "participants": participants,
        "data_sensitivity": sensitivity,
    }

    if technology in ("FL", "VFL"):
        base_config.update({
            "algorithm": req.get("algorithm", "homo_lr" if technology == "FL" else "hetero_lr"),
            "epochs": req.get("epochs", 10),
            "learning_rate": req.get("learning_rate", 0.1),
            "batch_size": req.get("batch_size", -1),
            "secure_aggregation": True,
            "differential_privacy": sensitivity in ("high", "critical"),
            "dp_epsilon": 1.0 if sensitivity in ("high", "critical") else None,
        })
    elif technology == "MPC":
        base_config.update({
            "protocol": req.get("protocol", "secret_sharing"),
            "security_level": 128,
            "fixed_point_precision": 16,
            "offline_phase": "beaver_triples",
        })
    elif technology == "TEE":
        base_config.update({
            "runtime": req.get("runtime", "gramine"),
            "remote_attestation": True,
            "memory_encryption": True,
            "max_memory_mb": req.get("max_memory_mb", 4096),
        })
    elif technology == "HE":
        base_config.update({
            "scheme": req.get("scheme", "paillier"),
            "key_size": 2048 if sensitivity == "critical" else 1024,
            "precision_bits": req.get("precision_bits", 32),
        })
    elif technology == "DP":
        base_config.update({
            "mechanism": req.get("mechanism", "laplace"),
            "epsilon": req.get("epsilon", 1.0),
            "delta": req.get("delta", 1e-5),
            "sensitivity": req.get("sensitivity", 1.0),
        })
    elif technology == "PSI":
        base_config.update({
            "protocol": req.get("protocol", "rsa_psi"),
            "input_type": req.get("input_type", "string"),
            "hash_function": "sha256",
        })

    return base_config


def _generate_reasoning(
    scenario: str,
    technology: str,
    sensitivity: str,
    participants: int,
) -> str:
    """生成推荐理由"""
    tech_info = TECHNOLOGY_INFO.get(technology, {})
    tech_name = tech_info.get("name", technology)

    reasons = []

    # 场景匹配
    route = ROUTING_MATRIX.get(scenario, {})
    if technology == route.get("recommended"):
        reasons.append(f"场景「{scenario}」的首选推荐技术")
    else:
        reasons.append(f"场景「{scenario}」的首选技术不可用，{tech_name} 为最佳替代")

    # 数据敏感度
    if sensitivity in ("high", "critical"):
        reasons.append(f"数据敏感度为「{sensitivity}」，{tech_name} 提供强隐私保护")

    # 参与方数量
    if participants > 3 and technology in ("MPC",):
        reasons.append(f"参与方数量({participants})较多，通信开销需关注")
    elif participants >= 2:
        reasons.append(f"支持 {participants} 方协作计算")

    return "；".join(reasons) + "。"
