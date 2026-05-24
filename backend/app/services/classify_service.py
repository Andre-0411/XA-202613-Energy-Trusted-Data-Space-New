"""
分类分级引擎
自动分类：基于字段名/数据特征判断大类（发电/用电/调度/市场/设备状态/地理信息）
分级规则：核心(1)/重要(2)/敏感(3)/公开(4)，基于标签+规则引擎
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ==================== 分类规则 ====================

# 字段名关键词 -> 大类映射
CATEGORY_KEYWORD_MAP = {
    "发电": [
        "power_generation", "pv_output", "wind_speed", "solar_irradiance",
        "turbine", "generator", "发电量", "光伏", "风机", "太阳能", "火力",
        "active_power", "reactive_power", "voltage", "frequency",
    ],
    "用电": [
        "consumption", "load", "demand", "meter_reading", "energy_usage",
        "用电量", "负荷", "电表", "用电", "电量", "kwh", "billing",
        "peak_load", "valley_load", "power_factor",
    ],
    "调度": [
        "dispatch", "schedule", "grid_control", "frequency_regulation",
        "调度", "计划", "指令", "agc", "avc", "储备", "调频",
        "interchange", "tie_line", "balancing",
    ],
    "市场": [
        "price", "trade", "auction", "settlement", "market",
        "价格", "交易", "竞价", "结算", "市场", "合约", "现货",
        "bidding", "clearing", "spot_price",
    ],
    "设备状态": [
        "status", "alarm", "fault", "maintenance", "sensor",
        "状态", "告警", "故障", "维护", "传感器", "温度", "湿度",
        "vibration", "insulation", "health_index", "diagnosis",
    ],
    "地理信息": [
        "location", "coordinates", "latitude", "longitude", "gis",
        "位置", "坐标", "经纬度", "地址", "区域", "地图",
        "geojson", "boundary", "topology",
    ],
}

# 大类默认分级
CATEGORY_DEFAULT_LEVEL = {
    "发电": 2,
    "用电": 3,
    "调度": 1,
    "市场": 2,
    "设备状态": 3,
    "地理信息": 4,
}

# ==================== 分级规则 ====================

# 分级判定规则（按优先级从高到低）
LEVEL_RULES = [
    # 规则1: 调度类数据 → 核心级别
    {
        "condition": lambda ctx: ctx.get("category") == "调度",
        "level": 1,
        "reason": "调度数据涉及电网安全，属于核心级别",
    },
    # 规则2: 包含个人信息的用电数据 → 重要级别
    {
        "condition": lambda ctx: (
            ctx.get("category") == "用电"
            and _contains_personal_info(ctx.get("schema_def", {}))
        ),
        "level": 2,
        "reason": "用电数据包含个人标识信息，属于重要级别",
    },
    # 规则3: 实时采集的核心数据 → 重要级别
    {
        "condition": lambda ctx: (
            ctx.get("is_critical") is True
            and ctx.get("collection_interval_ms", 0) < 1000
        ),
        "level": 2,
        "reason": "实时核心数据，属于重要级别",
    },
    # 规则4: 包含商业敏感字段的市场数据 → 重要级别
    {
        "condition": lambda ctx: (
            ctx.get("category") == "市场"
            and _contains_commercial_info(ctx.get("schema_def", {}))
        ),
        "level": 2,
        "reason": "市场数据包含商业敏感信息，属于重要级别",
    },
    # 规则5: 设备状态含故障/告警信息 → 敏感级别
    {
        "condition": lambda ctx: (
            ctx.get("category") == "设备状态"
            and _contains_alarm_fields(ctx.get("schema_def", {}))
        ),
        "level": 2,
        "reason": "设备告警数据涉及安全风险，属于重要级别",
    },
    # 规则6: 地理位置精确到具体地址 → 敏感级别
    {
        "condition": lambda ctx: (
            ctx.get("category") == "地理信息"
            and _contains_precise_location(ctx.get("schema_def", {}))
        ),
        "level": 3,
        "reason": "精确地理信息属于敏感级别",
    },
]

# 分级标签映射
TAG_LEVEL_MAP = {
    "核心": 1,
    "机密": 1,
    "重要": 2,
    "秘密": 2,
    "敏感": 3,
    "内部": 3,
    "公开": 4,
}


async def classify_and_grade(
    asset_name: str,
    asset_description: Optional[str] = None,
    schema_def: Optional[dict] = None,
    category: Optional[str] = None,
    tags: Optional[list[str]] = None,
    is_critical: bool = False,
    collection_interval_ms: int = 5000,
) -> dict:
    """
    执行分类分级

    1. 如果已有大类，验证其合理性
    2. 如果没有大类，基于名称/描述/字段自动推断
    3. 基于规则引擎计算敏感级别
    4. 返回分类分级结果

    Args:
        asset_name: 资产名称
        asset_description: 资产描述
        schema_def: 数据 Schema 定义
        category: 已指定的大类（可选）
        tags: 标签列表（可选）
        is_critical: 是否核心数据
        collection_interval_ms: 采集间隔

    Returns:
        {
            "category": str,
            "classification_level": int,
            "confidence": float,
            "reason": str,
            "suggested_tags": list[str],
        }
    """
    # 1. 分类推断
    inferred_category, category_confidence = _infer_category(
        asset_name, asset_description, schema_def
    )

    # 使用已有分类或推断分类
    final_category = category or inferred_category
    if category and category != inferred_category:
        # 用户指定了分类但与推断不一致，降低置信度
        category_confidence = category_confidence * 0.7

    # 2. 分级计算
    context = {
        "category": final_category,
        "schema_def": schema_def or {},
        "is_critical": is_critical,
        "collection_interval_ms": collection_interval_ms,
        "tags": tags or [],
    }

    classification_level, level_reason = _calculate_level(context, tags)

    # 3. 推荐标签
    suggested_tags = _suggest_tags(final_category, classification_level, schema_def)

    return {
        "category": final_category,
        "classification_level": classification_level,
        "confidence": round(category_confidence, 2),
        "reason": level_reason,
        "suggested_tags": suggested_tags,
    }


def _infer_category(
    name: str,
    description: Optional[str],
    schema_def: Optional[dict],
) -> tuple[str, float]:
    """
    基于名称、描述和字段推断大类

    Returns:
        (category, confidence)
    """
    # 合并文本用于匹配
    text = (name or "").lower()
    if description:
        text += " " + description.lower()

    # 从 schema_def 提取字段名
    field_names = []
    if schema_def and isinstance(schema_def, dict):
        fields = schema_def.get("fields", schema_def.get("columns", []))
        for field in fields:
            if isinstance(field, dict):
                field_names.append(field.get("name", "").lower())
            elif isinstance(field, str):
                field_names.append(field.lower())

    field_text = " ".join(field_names)
    combined_text = text + " " + field_text

    # 计算每个大类的匹配分数
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORD_MAP.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in combined_text:
                score += 2 if keyword.lower() in text else 1
        scores[cat] = score

    # 取最高分的大类
    if not scores or max(scores.values()) == 0:
        return "设备状态", 0.3  # 默认分类，低置信度

    best_category = max(scores, key=scores.get)
    total_score = sum(scores.values())
    confidence = scores[best_category] / total_score if total_score > 0 else 0.3

    # 置信度下限
    confidence = max(confidence, 0.3)

    return best_category, min(confidence, 1.0)


def _calculate_level(
    context: dict,
    tags: Optional[list[str]] = None,
) -> tuple[int, str]:
    """
    基于规则引擎计算敏感级别

    Returns:
        (level, reason)
    """
    # 1. 先检查标签是否直接指定了级别
    if tags:
        for tag in tags:
            if tag in TAG_LEVEL_MAP:
                level = TAG_LEVEL_MAP[tag]
                return level, f"标签 '{tag}' 直接指定了级别 {level}"

    # 2. 按优先级遍历分级规则
    for rule in LEVEL_RULES:
        try:
            if rule["condition"](context):
                return rule["level"], rule["reason"]
        except Exception:
            continue

    # 3. 使用大类默认级别
    default_level = CATEGORY_DEFAULT_LEVEL.get(context.get("category", ""), 4)
    return default_level, f"使用大类默认级别 {default_level}"


def _suggest_tags(
    category: str,
    level: int,
    schema_def: Optional[dict],
) -> list[str]:
    """推荐标签"""
    tags = []

    # 大类标签
    tags.append(category)

    # 级别标签
    level_name_map = {1: "核心", 2: "重要", 3: "敏感", 4: "公开"}
    tags.append(level_name_map.get(level, "公开"))

    # 基于字段推荐标签
    if schema_def and isinstance(schema_def, dict):
        fields = schema_def.get("fields", schema_def.get("columns", []))
        field_names = []
        for field in fields:
            if isinstance(field, dict):
                field_names.append(field.get("name", ""))
            elif isinstance(field, str):
                field_names.append(field)

        if any("time" in f.lower() or "日期" in f for f in field_names):
            tags.append("时序数据")
        if any("id" in f.lower() or "标识" in f for f in field_names):
            tags.append("含标识符")
        if any("location" in f.lower() or "位置" in f for f in field_names):
            tags.append("含位置信息")

    return tags


def _contains_personal_info(schema_def: dict) -> bool:
    """检查 Schema 是否包含个人标识信息"""
    personal_keywords = [
        "name", "id_card", "phone", "email", "address",
        "姓名", "身份证", "电话", "邮箱", "地址", "user_id",
    ]
    field_text = str(schema_def).lower()
    return any(kw in field_text for kw in personal_keywords)


def _contains_commercial_info(schema_def: dict) -> bool:
    """检查 Schema 是否包含商业敏感信息"""
    commercial_keywords = [
        "price", "cost", "margin", "profit", "revenue",
        "价格", "成本", "利润", "收入", "报价",
    ]
    field_text = str(schema_def).lower()
    return any(kw in field_text for kw in commercial_keywords)


def _contains_alarm_fields(schema_def: dict) -> bool:
    """检查 Schema 是否包含告警相关字段"""
    alarm_keywords = [
        "alarm", "fault", "error_code", "severity",
        "告警", "故障", "错误码", "严重程度",
    ]
    field_text = str(schema_def).lower()
    return any(kw in field_text for kw in alarm_keywords)


def _contains_precise_location(schema_def: dict) -> bool:
    """检查 Schema 是否包含精确位置信息"""
    precise_keywords = [
        "latitude", "longitude", "address", "street",
        "纬度", "经度", "街道", "门牌号",
    ]
    field_text = str(schema_def).lower()
    return any(kw in field_text for kw in precise_keywords)
