"""
四级安全等级防护矩阵服务

安全等级定义:
- 一级（核心/机密）: SM4加密 + SM2签名 + 双因素认证 + 全程审计 + 人工审批
- 二级（重要/敏感）: SM4加密 + SM2签名 + MFA + 审计日志
- 三级（一般/内部）: SM3哈希 + 基础认证 + 操作日志
- 四级（公开）: 无特殊要求

功能:
- 安全等级查询接口
- 防护策略自动匹配
- 资源安全等级设置
- 合规性检查
- 能源领域特定的自动分级规则
- 公开/内部/敏感/机密 标签映射
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    DataNotFoundError,
    DataValidationError,
    SecurityError,
)

logger = logging.getLogger(__name__)

# ==================== 安全等级定义 ====================

SECURITY_LEVELS = {
    1: {
        "level": 1,
        "name": "核心",
        "classification_label": "机密",
        "description": "最高安全等级，适用于核心业务数据和关键系统组件",
        "color": "#FF0000",
        "policies": {
            "encryption": {
                "algorithm": "SM4",
                "key_length": 128,
                "mode": "CBC",
                "required": True,
                "description": "SM4 国密对称加密，密钥长度 128 位",
                "key_rotation_days": 30,
            },
            "signature": {
                "algorithm": "SM2",
                "required": True,
                "description": "SM2 国密非对称签名",
                "sign_all_operations": True,
            },
            "authentication": {
                "type": "two_factor",
                "required": True,
                "description": "双因素认证（密码 + 动态令牌/生物识别）",
                "methods": ["password", "totp", "biometric"],
            },
            "audit": {
                "level": "full",
                "required": True,
                "description": "全程审计，记录所有操作及数据流转",
                "retention_days": 365,
                "real_time_alert": True,
            },
            "access_control": {
                "type": "manual_approval",
                "required": True,
                "description": "人工审批，每次访问需管理员审批",
                "approval_workflow": True,
                "max_approvals_per_session": 1,
            },
            "data_handling": {
                "watermark": True,
                "dlp_scan": True,
                "export_restricted": True,
                "copy_restricted": True,
                "description": "数据水印、DLP扫描、禁止导出/复制",
            },
        },
    },
    2: {
        "level": 2,
        "name": "重要",
        "classification_label": "敏感",
        "description": "重要安全等级，适用于业务关键数据和重要服务",
        "color": "#FF8C00",
        "policies": {
            "encryption": {
                "algorithm": "SM4",
                "key_length": 128,
                "mode": "CBC",
                "required": True,
                "description": "SM4 国密对称加密",
                "key_rotation_days": 90,
            },
            "signature": {
                "algorithm": "SM2",
                "required": True,
                "description": "SM2 国密非对称签名",
                "sign_critical_ops": True,
            },
            "authentication": {
                "type": "mfa",
                "required": True,
                "description": "多因素认证（MFA）",
                "methods": ["password", "totp"],
            },
            "audit": {
                "level": "detailed",
                "required": True,
                "description": "审计日志，记录关键操作",
                "retention_days": 180,
                "real_time_alert": False,
            },
            "access_control": {
                "type": "rbac",
                "required": True,
                "description": "基于角色的访问控制",
                "approval_workflow": False,
            },
            "data_handling": {
                "watermark": False,
                "dlp_scan": True,
                "export_restricted": False,
                "copy_restricted": False,
                "description": "DLP 扫描，导出需审批",
            },
        },
    },
    3: {
        "level": 3,
        "name": "一般",
        "classification_label": "内部",
        "description": "一般安全等级，适用于常规业务数据",
        "color": "#4169E1",
        "policies": {
            "encryption": {
                "algorithm": "SM3",
                "key_length": 256,
                "mode": "HASH",
                "required": False,
                "description": "SM3 哈希校验，确保数据完整性",
                "key_rotation_days": 0,
            },
            "signature": {
                "algorithm": "",
                "required": False,
                "description": "无签名要求",
                "sign_critical_ops": False,
            },
            "authentication": {
                "type": "basic",
                "required": True,
                "description": "基础认证（用户名/密码）",
                "methods": ["password"],
            },
            "audit": {
                "level": "basic",
                "required": True,
                "description": "操作日志",
                "retention_days": 90,
                "real_time_alert": False,
            },
            "access_control": {
                "type": "basic",
                "required": True,
                "description": "基础访问控制",
                "approval_workflow": False,
            },
            "data_handling": {
                "watermark": False,
                "dlp_scan": False,
                "export_restricted": False,
                "copy_restricted": False,
                "description": "无特殊数据处理要求",
            },
        },
    },
    4: {
        "level": 4,
        "name": "公开",
        "classification_label": "公开",
        "description": "公开安全等级，适用于公开数据和非敏感信息",
        "color": "#32CD32",
        "policies": {
            "encryption": {
                "algorithm": "",
                "key_length": 0,
                "mode": "",
                "required": False,
                "description": "无加密要求",
                "key_rotation_days": 0,
            },
            "signature": {
                "algorithm": "",
                "required": False,
                "description": "无签名要求",
                "sign_critical_ops": False,
            },
            "authentication": {
                "type": "anonymous",
                "required": False,
                "description": "无需认证",
                "methods": [],
            },
            "audit": {
                "level": "none",
                "required": False,
                "description": "无审计要求",
                "retention_days": 0,
                "real_time_alert": False,
            },
            "access_control": {
                "type": "public",
                "required": False,
                "description": "公开访问",
                "approval_workflow": False,
            },
            "data_handling": {
                "watermark": False,
                "dlp_scan": False,
                "export_restricted": False,
                "copy_restricted": False,
                "description": "无特殊要求",
            },
        },
    },
}

# 分类标签到安全等级的映射
CLASSIFICATION_LABEL_TO_LEVEL = {
    "机密": 1,
    "核心": 1,
    "敏感": 2,
    "重要": 2,
    "内部": 3,
    "一般": 3,
    "公开": 4,
}

# 资源类型到默认安全等级的映射
DEFAULT_LEVEL_MAPPING = {
    "core_data": 1,
    "financial_data": 1,
    "user_credentials": 1,
    "encryption_keys": 1,
    "business_data": 2,
    "user_data": 2,
    "api_data": 2,
    "analytics_data": 3,
    "log_data": 3,
    "metadata": 3,
    "public_info": 4,
    "open_data": 4,
    "documentation": 4,
}

# ==================== 能源领域安全分级规则 ====================

# 能源数据敏感关键词（基于数据名称/描述自动分级）
_ENERGY_SENSITIVE_KEYWORDS = {
    1: {  # 核心/机密
        "patterns": [
            r"密钥", r"证书", r"私钥", r"加密机", r"HSM",
            r"调度指令", r"控制命令", r"继电保护", r"安全自动装置",
            r"用户密码", r"认证凭据", r"登录信息",
            r"财务核心", r"合同原件",
            r"电网拓扑.*核心", r"发电计划.*正式",
        ],
        "keywords": [
            "加密密钥", "数字证书", "私钥文件", "HSM密钥",
            "调度控制", "AGC指令", "AVC指令", "安全稳定控制",
            "用户密码", "认证令牌", "API密钥",
            "继电保护定值", "安全自动装置参数",
        ],
    },
    2: {  # 重要/敏感
        "patterns": [
            r"用户信息", r"个人信息", r"PII", r"身份证",
            r"企业.*财务", r"交易记录", r"结算",
            r"实时.*运行", r"SCADA", r"EMS",
            r"电价", r"电费", r"用电量.*明细",
            r"设备.*型号", r"参数.*配置",
        ],
        "keywords": [
            "用户数据", "个人信息", "客户信息",
            "交易记录", "结算数据", "电费账单",
            "SCADA数据", "EMS数据", "实时运行数据",
            "电价信息", "电力交易", "市场出清",
            "设备参数", "设备配置",
        ],
    },
    3: {  # 一般/内部
        "patterns": [
            r"统计.*报表", r"汇总", r"分析.*报告",
            r"设备.*状态", r"巡检", r"运维",
            r"历史.*数据", r"归档",
            r"天气", r"气象",
            r"地理信息", r"GIS",
        ],
        "keywords": [
            "统计报表", "汇总数据", "分析报告",
            "设备状态", "巡检记录", "运维日志",
            "历史数据", "归档数据",
            "天气数据", "气象数据",
            "地理信息", "GIS数据",
        ],
    },
    4: {  # 公开
        "patterns": [
            r"公开", r"公告", r"新闻",
            r"政策", r"法规", r"标准",
            r"行业.*报告", r"研究.*报告",
            r"新能源.*装机", r"发电量.*统计",
        ],
        "keywords": [
            "公开数据", "公告信息", "新闻资讯",
            "政策法规", "行业标准",
            "行业报告", "研究报告",
            "装机容量统计", "发电量统计",
            "公开信息", "开放数据",
        ],
    },
}

# 能源数据分类到安全等级的默认映射
_ENERGY_CATEGORY_SECURITY_MAP = {
    "发电": {
        "实时": 2,
        "历史": 3,
        "统计": 3,
        "计划": 2,
    },
    "用电": {
        "实时": 2,
        "明细": 2,
        "统计": 3,
        "公开": 4,
    },
    "调度": {
        "指令": 1,
        "实时": 1,
        "计划": 2,
        "统计": 3,
    },
    "市场": {
        "交易": 2,
        "结算": 2,
        "报价": 2,
        "统计": 3,
    },
    "设备状态": {
        "实时": 2,
        "历史": 3,
        "统计": 3,
    },
    "地理信息": {
        "精确": 2,
        "粗略": 3,
        "公开": 4,
    },
}


def get_all_levels() -> list[dict]:
    """
    获取所有安全等级信息

    Returns:
        安全等级列表
    """
    return [
        {
            "level": info["level"],
            "name": info["name"],
            "classification_label": info.get("classification_label", ""),
            "description": info["description"],
            "color": info["color"],
            "policies": info["policies"],
        }
        for info in SECURITY_LEVELS.values()
    ]


def get_level_policies(level: int) -> dict:
    """
    获取指定等级的防护策略

    Args:
        level: 安全等级（1-4）

    Returns:
        防护策略详情
    """
    if level not in SECURITY_LEVELS:
        raise DataValidationError(
            message=f"无效的安全等级: {level}，有效范围: 1-4"
        )

    level_info = SECURITY_LEVELS[level]
    return {
        "level": level_info["level"],
        "name": level_info["name"],
        "classification_label": level_info.get("classification_label", ""),
        "encryption": level_info["policies"]["encryption"],
        "signature": level_info["policies"]["signature"],
        "authentication": level_info["policies"]["authentication"],
        "audit": level_info["policies"]["audit"],
        "access_control": level_info["policies"]["access_control"],
        "data_handling": level_info["policies"]["data_handling"],
    }


def get_classification_mapping() -> dict:
    """
    获取分类标签到安全等级的映射

    Returns:
        分类标签映射
    """
    return {
        "label_to_level": CLASSIFICATION_LABEL_TO_LEVEL,
        "level_to_labels": {
            1: ["核心", "机密"],
            2: ["重要", "敏感"],
            3: ["一般", "内部"],
            4: ["公开"],
        },
        "levels": [
            {
                "level": level,
                "name": info["name"],
                "classification_label": info.get("classification_label", ""),
                "description": info["description"],
            }
            for level, info in SECURITY_LEVELS.items()
        ],
    }


def auto_grade_security(
    data_name: str,
    data_description: Optional[str] = None,
    data_category: Optional[str] = None,
    data_subcategory: Optional[str] = None,
    has_pii: bool = False,
    is_realtime: bool = False,
    data_size: int = 0,
    existing_tags: Optional[list[str]] = None,
) -> dict:
    """
    自动安全分级

    基于能源领域规则自动判断数据的安全等级。

    Args:
        data_name: 数据名称
        data_description: 数据描述
        data_category: 数据分类（发电/用电/调度/市场/设备状态/地理信息）
        data_subcategory: 数据子分类
        has_pii: 是否包含个人信息
        is_realtime: 是否实时数据
        data_size: 数据大小
        existing_tags: 已有标签

    Returns:
        分级结果
    """
    # 初始化评分矩阵
    scores = {1: 0, 2: 0, 3: 0, 4: 0}
    reasons = {1: [], 2: [], 3: [], 4: []}
    matched_rules = []

    # 1. 基于关键词匹配
    text = f"{data_name} {data_description or ''}"
    for level, rules in _ENERGY_SENSITIVE_KEYWORDS.items():
        for pattern in rules["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                scores[level] += 3
                reasons[level].append(f"关键词匹配: {pattern}")
                matched_rules.append({"type": "keyword", "pattern": pattern, "level": level})
                break  # 每个等级只匹配一次

        for keyword in rules["keywords"]:
            if keyword in text:
                scores[level] += 2
                reasons[level].append(f"关键词命中: {keyword}")
                matched_rules.append({"type": "keyword", "keyword": keyword, "level": level})
                break

    # 2. 基于数据分类映射
    if data_category and data_subcategory:
        category_rules = _ENERGY_CATEGORY_SECURITY_MAP.get(data_category, {})
        if data_subcategory in category_rules:
            mapped_level = category_rules[data_subcategory]
            scores[mapped_level] += 5
            reasons[mapped_level].append(f"分类映射: {data_category}/{data_subcategory} → L{mapped_level}")
            matched_rules.append({
                "type": "category",
                "category": data_category,
                "subcategory": data_subcategory,
                "level": mapped_level,
            })
    elif data_category:
        # 仅主分类时，取该分类的默认等级
        category_rules = _ENERGY_CATEGORY_SECURITY_MAP.get(data_category, {})
        if category_rules:
            default_level = min(category_rules.values())  # 取最高等级作为默认
            scores[default_level] += 3
            reasons[default_level].append(f"分类默认: {data_category} → L{default_level}")

    # 3. PII 数据提升等级
    if has_pii:
        scores[2] += 4
        reasons[2].append("包含个人信息(PII)")
        matched_rules.append({"type": "pii", "level": 2})

    # 4. 实时数据提升等级
    if is_realtime:
        scores[2] += 2
        reasons[2].append("实时数据，时效性敏感")
        matched_rules.append({"type": "realtime", "level": 2})

    # 5. 大数据量提升等级
    if data_size > 10_000_000:
        scores[2] += 2
        reasons[2].append("大数据量（>10M条），影响范围广")
        matched_rules.append({"type": "large_dataset", "level": 2})
    elif data_size > 1_000_000:
        scores[3] += 1
        reasons[3].append("数据量较大（>1M条）")

    # 6. 已有标签匹配
    if existing_tags:
        for tag in existing_tags:
            if tag in CLASSIFICATION_LABEL_TO_LEVEL:
                tag_level = CLASSIFICATION_LABEL_TO_LEVEL[tag]
                scores[tag_level] += 5
                reasons[tag_level].append(f"已有标签: {tag}")
                matched_rules.append({"type": "tag", "tag": tag, "level": tag_level})

    # 7. 默认等级（无任何匹配时为3级/一般）
    if sum(scores.values()) == 0:
        scores[3] += 1
        reasons[3].append("无特殊规则匹配，默认一般等级")

    # 确定最终等级（得分最高的等级）
    final_level = max(scores, key=lambda k: scores[k])

    # 构建结果
    level_info = SECURITY_LEVELS[final_level]
    result = {
        "level": final_level,
        "name": level_info["name"],
        "classification_label": level_info.get("classification_label", ""),
        "description": level_info["description"],
        "color": level_info["color"],
        "confidence": min(scores[final_level] / 10.0, 1.0),
        "scores": scores,
        "reasons": reasons[final_level],
        "all_reasons": reasons,
        "matched_rules": matched_rules,
        "policies": level_info["policies"],
        "graded_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        f"Auto security grading: {data_name} → L{final_level}({level_info['name']}/{level_info.get('classification_label', '')}), "
        f"score={scores[final_level]}, confidence={result['confidence']:.2f}"
    )

    return result


def check_resource_security(
    resource_type: str,
    resource_id: str,
    context: Optional[dict] = None,
) -> dict:
    """
    检查资源安全等级要求

    根据资源类型和上下文自动判断应适用的安全等级，
    并检查当前防护措施是否满足要求。

    Args:
        resource_type: 资源类型
        resource_id: 资源 ID
        context: 附加上下文

    Returns:
        安全检查结果
    """
    ctx = context or {}

    # 根据资源类型和上下文推断安全等级
    inferred_level = _infer_security_level(resource_type, ctx)
    level_info = SECURITY_LEVELS[inferred_level]
    policies = level_info["policies"]

    # 收集必须的安全措施
    required_measures = []
    if policies["encryption"]["required"]:
        required_measures.append(f"加密: {policies['encryption']['description']}")
    if policies["signature"]["required"]:
        required_measures.append(f"签名: {policies['signature']['description']}")
    if policies["authentication"]["required"]:
        required_measures.append(f"认证: {policies['authentication']['description']}")
    if policies["audit"]["required"]:
        required_measures.append(f"审计: {policies['audit']['description']}")
    if policies["access_control"]["required"]:
        required_measures.append(f"访问控制: {policies['access_control']['description']}")

    # 检查已实施的安全措施（基于 context）
    current_measures = ctx.get("current_measures", [])
    missing_measures = []
    for measure in required_measures:
        measure_key = measure.split(":")[0].strip()
        if not any(m.startswith(measure_key) for m in current_measures):
            missing_measures.append(measure)

    # 判断合规状态
    if not missing_measures:
        compliance_status = "compliant"
    elif len(missing_measures) < len(required_measures):
        compliance_status = "partial"
    else:
        compliance_status = "non_compliant"

    # 生成建议
    recommendations = _generate_recommendations(
        inferred_level, missing_measures
    )

    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "current_level": inferred_level,
        "level_name": level_info["name"],
        "classification_label": level_info.get("classification_label", ""),
        "required_measures": required_measures,
        "compliance_status": compliance_status,
        "missing_measures": missing_measures,
        "recommendations": recommendations,
        "checked_at": datetime.now(timezone.utc),
    }


def set_resource_security_level(
    resource_id: str,
    level: int,
    reason: Optional[str] = None,
    operator: Optional[str] = None,
) -> dict:
    """
    设置资源安全等级

    Args:
        resource_id: 资源 ID
        level: 安全等级（1-4）
        reason: 设置原因
        operator: 操作人

    Returns:
        设置结果
    """
    if level not in SECURITY_LEVELS:
        raise DataValidationError(
            message=f"无效的安全等级: {level}，有效范围: 1-4"
        )

    level_info = SECURITY_LEVELS[level]

    logger.info(
        f"资源安全等级设置: resource_id={resource_id}, "
        f"level={level}({level_info['name']}/{level_info.get('classification_label', '')}), "
        f"operator={operator}, reason={reason}"
    )

    return {
        "resource_id": resource_id,
        "level": level,
        "level_name": level_info["name"],
        "classification_label": level_info.get("classification_label", ""),
        "policies_applied": list(level_info["policies"].keys()),
        "reason": reason,
        "operator": operator,
        "set_at": datetime.now(timezone.utc),
    }


def _infer_security_level(resource_type: str, context: dict) -> int:
    """
    根据资源类型和上下文推断安全等级

    Args:
        resource_type: 资源类型
        context: 上下文信息

    Returns:
        推断的安全等级（1-4）
    """
    # 优先使用显式指定的等级
    if "security_level" in context:
        return int(context["security_level"])

    # 优先使用分类标签映射
    if "classification_label" in context:
        label = context["classification_label"]
        if label in CLASSIFICATION_LABEL_TO_LEVEL:
            return CLASSIFICATION_LABEL_TO_LEVEL[label]

    # 根据资源类型推断
    base_level = DEFAULT_LEVEL_MAPPING.get(resource_type, 3)

    # 根据上下文特征调整
    sensitivity_tags = context.get("sensitivity_tags", [])
    if "critical" in sensitivity_tags or "classified" in sensitivity_tags:
        base_level = min(base_level, 1)
    elif "confidential" in sensitivity_tags or "sensitive" in sensitivity_tags:
        base_level = min(base_level, 2)
    elif "internal" in sensitivity_tags:
        base_level = min(base_level, 3)

    # 能源领域标签调整
    energy_tags = context.get("energy_tags", [])
    if "调度" in energy_tags or "控制" in energy_tags:
        base_level = min(base_level, 1)
    elif "交易" in energy_tags or "结算" in energy_tags:
        base_level = min(base_level, 2)

    # 数据量调整（大数据集提高保护级别）
    data_size = context.get("data_size", 0)
    if data_size > 1_000_000:
        base_level = min(base_level, 2)

    # 含有 PII 数据
    has_pii = context.get("has_pii", False)
    if has_pii:
        base_level = min(base_level, 2)

    # 实时数据
    is_realtime = context.get("is_realtime", False)
    if is_realtime:
        base_level = min(base_level, 2)

    return base_level


def _generate_recommendations(level: int, missing_measures: list[str]) -> list[str]:
    """
    生成安全改进建议

    Args:
        level: 安全等级
        missing_measures: 缺失的安全措施

    Returns:
        建议列表
    """
    recommendations = []
    level_info = SECURITY_LEVELS[level]

    if not missing_measures:
        recommendations.append(f"当前安全措施已满足{level_info['name']}等级要求")
        return recommendations

    for measure in missing_measures:
        if "加密" in measure:
            if level == 1:
                recommendations.append(
                    "建议启用 SM4 国密加密，使用 HSM 管理加密密钥"
                )
            elif level == 2:
                recommendations.append(
                    "建议启用 SM4 加密保护敏感数据"
                )
        elif "签名" in measure:
            recommendations.append(
                "建议使用 SM2 数字签名确保数据不可抵赖性"
            )
        elif "认证" in measure:
            if level == 1:
                recommendations.append(
                    "建议启用双因素认证（TOTP + 密码），或接入生物识别"
                )
            elif level == 2:
                recommendations.append(
                    "建议启用 MFA 多因素认证"
                )
            else:
                recommendations.append(
                    "建议启用基础用户名/密码认证"
                )
        elif "审计" in measure:
            retention = level_info["policies"]["audit"]["retention_days"]
            recommendations.append(
                f"建议开启审计日志功能，保留期限不少于 {retention} 天"
            )
        elif "访问控制" in measure:
            if level == 1:
                recommendations.append(
                    "建议配置人工审批流程，敏感操作需管理员批准"
                )
            else:
                recommendations.append(
                    "建议配置基于角色的访问控制（RBAC）策略"
                )

    return recommendations


# ==================== 模块级别便捷函数 ====================


def get_security_levels_info() -> list[dict]:
    """
    获取所有安全等级信息（模块级便捷函数）

    Returns:
        安全等级列表，包含等级、名称、分类标签、描述、颜色
    """
    return get_all_levels()


def auto_classify_security_level(
    data_name: str,
    data_description: Optional[str] = None,
    data_category: Optional[str] = None,
    has_pii: bool = False,
) -> dict:
    """
    自动分类安全等级（模块级便捷函数）

    Args:
        data_name: 数据名称
        data_description: 数据描述
        data_category: 数据分类
        has_pii: 是否包含PII

    Returns:
        分级结果（level, name, classification_label）
    """
    result = auto_grade_security(
        data_name=data_name,
        data_description=data_description,
        data_category=data_category,
        has_pii=has_pii,
    )
    return {
        "level": result["level"],
        "name": result["name"],
        "classification_label": result["classification_label"],
        "confidence": result["confidence"],
        "reasons": result["reasons"],
    }
