"""
数据分类引擎
自动分类、敏感级别判定、SM3 哈希指纹
"""
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger(__name__)

# 分类规则配置
CLASSIFICATION_RULES = [
    # 发电数据
    {
        "rule_id": "rule_power_output",
        "name": "发电量数据分类",
        "category": "发电",
        "keywords": ["power_output", "发电量", "发电功率", "上网电量"],
        "sensitivity_level": 2,  # 重要
        "auto_classify": True,
        "priority": 10,
    },
    {
        "rule_id": "rule_wind_speed",
        "name": "风速数据分类",
        "category": "发电",
        "keywords": ["wind_speed", "风速", "风向"],
        "sensitivity_level": 3,  # 敏感
        "auto_classify": True,
        "priority": 8,
    },
    {
        "rule_id": "rule_irradiance",
        "name": "辐照度数据分类",
        "category": "发电",
        "keywords": ["irradiance", "辐照度", "光照强度"],
        "sensitivity_level": 3,  # 敏感
        "auto_classify": True,
        "priority": 8,
    },
    # 用电数据
    {
        "rule_id": "rule_consumption",
        "name": "用电量数据分类",
        "category": "用电",
        "keywords": ["consumption", "用电量", "用电负荷", "用电功率", "meter_reading"],
        "sensitivity_level": 2,  # 重要
        "auto_classify": True,
        "priority": 10,
    },
    {
        "rule_id": "rule_demand",
        "name": "需量数据分类",
        "category": "用电",
        "keywords": ["demand", "需量", "最大需量", "peak_demand", "负荷曲线"],
        "sensitivity_level": 2,  # 重要
        "auto_classify": True,
        "priority": 9,
    },
    {
        "rule_id": "rule_tariff",
        "name": "电价数据分类",
        "category": "用电",
        "keywords": ["tariff", "电价", "峰谷电价", "阶梯电价", "电费"],
        "sensitivity_level": 1,  # 核心
        "auto_classify": True,
        "priority": 12,
    },
    {
        "rule_id": "rule_smart_meter",
        "name": "智能电表数据分类",
        "category": "用电",
        "keywords": ["smart_meter", "智能电表", "电表读数", "obis", "dlms_meter"],
        "sensitivity_level": 3,  # 敏感
        "auto_classify": True,
        "priority": 8,
    },
    # 调度数据
    {
        "rule_id": "rule_dispatch",
        "name": "调度指令分类",
        "category": "调度",
        "keywords": ["dispatch", "调度", "调度指令", "调度计划", "agc"],
        "sensitivity_level": 1,  # 核心
        "auto_classify": True,
        "priority": 15,
    },
    {
        "rule_id": "rule_load_balance",
        "name": "负荷平衡分类",
        "category": "调度",
        "keywords": ["load_balance", "负荷平衡", "功率平衡", "电网频率", "调频"],
        "sensitivity_level": 1,  # 核心
        "auto_classify": True,
        "priority": 14,
    },
    {
        "rule_id": "rule_grid_topology",
        "name": "电网拓扑分类",
        "category": "调度",
        "keywords": ["topology", "拓扑", "电网结构", "线路", "变电站", "母线"],
        "sensitivity_level": 2,  # 重要
        "auto_classify": True,
        "priority": 12,
    },
    {
        "rule_id": "rule_reserve",
        "name": "备用容量分类",
        "category": "调度",
        "keywords": ["reserve", "备用", "旋转备用", "调峰", "调频备用"],
        "sensitivity_level": 2,  # 重要
        "auto_classify": True,
        "priority": 11,
    },
    # 设备状态数据
    {
        "rule_id": "rule_temperature",
        "name": "温度数据分类",
        "category": "设备状态",
        "keywords": ["temperature", "温度", "panel_temperature"],
        "sensitivity_level": 4,  # 公开
        "auto_classify": True,
        "priority": 5,
    },
    {
        "rule_id": "rule_vibration",
        "name": "振动数据分类",
        "category": "设备状态",
        "keywords": ["vibration", "振动", "震动"],
        "sensitivity_level": 3,  # 敏感
        "auto_classify": True,
        "priority": 6,
    },
    {
        "rule_id": "rule_rotation_speed",
        "name": "转速数据分类",
        "category": "设备状态",
        "keywords": ["rotation_speed", "转速", "rpm"],
        "sensitivity_level": 4,  # 公开
        "auto_classify": True,
        "priority": 5,
    },
    # 电气参数
    {
        "rule_id": "rule_voltage",
        "name": "电压数据分类",
        "category": "设备状态",
        "keywords": ["voltage", "电压"],
        "sensitivity_level": 3,  # 敏感
        "auto_classify": True,
        "priority": 7,
    },
    {
        "rule_id": "rule_current",
        "name": "电流数据分类",
        "category": "设备状态",
        "keywords": ["current", "电流"],
        "sensitivity_level": 3,  # 敏感
        "auto_classify": True,
        "priority": 7,
    },
    # 市场数据
    {
        "rule_id": "rule_market_price",
        "name": "市场价格分类",
        "category": "市场",
        "keywords": ["price", "电价", "市场价格", "交易价格", "clearing_price"],
        "sensitivity_level": 1,  # 核心
        "auto_classify": True,
        "priority": 15,
    },
    {
        "rule_id": "rule_market_trade",
        "name": "市场交易分类",
        "category": "市场",
        "keywords": ["trade", "交易", "撮合", "竞价", "挂牌", "双边协商"],
        "sensitivity_level": 1,  # 核心
        "auto_classify": True,
        "priority": 14,
    },
    {
        "rule_id": "rule_market_settlement",
        "name": "市场结算分类",
        "category": "市场",
        "keywords": ["settlement", "结算", "清算", "偏差考核"],
        "sensitivity_level": 1,  # 核心
        "auto_classify": True,
        "priority": 13,
    },
    # 地理信息
    {
        "rule_id": "rule_location",
        "name": "地理位置分类",
        "category": "地理信息",
        "keywords": ["location", "经纬度", "坐标", "地址", "longitude", "latitude"],
        "sensitivity_level": 2,  # 重要
        "auto_classify": True,
        "priority": 12,
    },
    {
        "rule_id": "rule_gis",
        "name": "GIS数据分类",
        "category": "地理信息",
        "keywords": ["gis", "地理信息", "地图", "区域", "gis_data"],
        "sensitivity_level": 2,  # 重要
        "auto_classify": True,
        "priority": 11,
    },
]

# 敏感级别标签映射
SENSITIVITY_LABELS = {
    1: "核心",
    2: "重要",
    3: "敏感",
    4: "公开",
}


class DataClassifier:
    """数据分类引擎"""

    def __init__(self):
        self._rules = CLASSIFICATION_RULES
        self._classification_cache: dict[str, dict] = {}

    async def classify_data(
        self,
        data_name: str,
        data_description: Optional[str] = None,
        data_fields: Optional[list[str]] = None,
        category_hint: Optional[str] = None,
    ) -> dict:
        """
        自动分类数据

        Args:
            data_name: 数据名称
            data_description: 数据描述
            data_fields: 数据字段列表
            category_hint: 分类提示

        Returns:
            分类结果
        """
        # 构建搜索文本
        search_text = f"{data_name} {data_description or ''}"
        if data_fields:
            search_text += " " + " ".join(data_fields)

        # 匹配规则
        matched_rules = []
        for rule in self._rules:
            score = self._calculate_match_score(search_text, rule["keywords"])
            if score > 0:
                matched_rules.append({
                    "rule": rule,
                    "score": score,
                })

        # 按优先级和匹配度排序
        matched_rules.sort(
            key=lambda x: (x["rule"]["priority"], x["score"]),
            reverse=True
        )

        # 确定分类结果
        if matched_rules:
            best_match = matched_rules[0]
            category = best_match["rule"]["category"]
            sensitivity_level = best_match["rule"]["sensitivity_level"]
            confidence = min(best_match["score"] / 100, 1.0)
        else:
            # 默认分类
            category = category_hint or "其他"
            sensitivity_level = 4  # 默认公开
            confidence = 0.5

        # 生成 SM3 哈希指纹
        sm3_hash = self._generate_sm3_hash(data_name, data_fields)

        result = {
            "category": category,
            "classification_level": sensitivity_level,
            "sensitivity_label": SENSITIVITY_LABELS.get(sensitivity_level, "公开"),
            "sm3_hash": sm3_hash,
            "confidence": confidence,
            "matched_rules": [
                {
                    "rule_id": m["rule"]["rule_id"],
                    "rule_name": m["rule"]["name"],
                    "score": m["score"],
                }
                for m in matched_rules[:3]  # 最多返回3个匹配规则
            ],
            "classified_at": datetime.now(timezone.utc).isoformat(),
            "classified_by": "auto_classifier",
        }

        # 缓存结果
        cache_key = f"{data_name}:{category_hint}"
        self._classification_cache[cache_key] = result

        logger.info(f"数据分类完成: {data_name} -> {category}/{SENSITIVITY_LABELS.get(sensitivity_level)}")
        return result

    async def classify_batch(self, data_items: list[dict]) -> list[dict]:
        """
        批量分类

        Args:
            data_items: 数据项列表，每项包含 name, description, fields 等

        Returns:
            分类结果列表
        """
        results = []
        for item in data_items:
            result = await self.classify_data(
                data_name=item.get("name", ""),
                data_description=item.get("description"),
                data_fields=item.get("fields"),
                category_hint=item.get("category_hint"),
            )
            results.append(result)
        return results

    async def get_classification_rules(self) -> list[dict]:
        """获取所有分类规则"""
        return self._rules

    async def add_classification_rule(self, rule: dict) -> dict:
        """添加分类规则"""
        rule_id = rule.get("rule_id", f"rule_custom_{len(self._rules) + 1}")
        rule["rule_id"] = rule_id
        self._rules.append(rule)
        logger.info(f"添加分类规则: {rule_id}")
        return rule

    async def verify_integrity(self, data_name: str, data_fields: list[str], expected_hash: str) -> bool:
        """
        验证数据完整性

        Args:
            data_name: 数据名称
            data_fields: 数据字段
            expected_hash: 期望的 SM3 哈希值

        Returns:
            是否完整
        """
        current_hash = self._generate_sm3_hash(data_name, data_fields)
        return current_hash == expected_hash

    def _calculate_match_score(self, text: str, keywords: list[str]) -> float:
        """计算匹配分数"""
        score = 0.0
        text_lower = text.lower()

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                # 完全匹配得分更高
                if keyword_lower == text_lower:
                    score += 100
                else:
                    # 部分匹配
                    count = text_lower.count(keyword_lower)
                    score += count * 20

        return score

    def _generate_sm3_hash(self, data_name: str, data_fields: Optional[list[str]] = None) -> str:
        """
        生成 SM3 哈希指纹

        使用 gmssl 库的 SM3 算法（如果可用），否则使用 SHA256 模拟
        """
        # 构建待哈希数据
        hash_input = data_name
        if data_fields:
            hash_input += ":" + ",".join(sorted(data_fields))

        try:
            # 尝试使用 gmssl 的 SM3
            from gmssl import sm3, func
            data_bytes = hash_input.encode('utf-8')
            hash_hex = sm3.sm3_hash(func.bytes_to_list(data_bytes))
            return f"sm3:{hash_hex}"
        except ImportError:
            # 降级为 SHA256 模拟
            logger.warning("gmssl 未安装，使用 SHA256 模拟 SM3")
            hash_hex = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
            return f"sm3_simulated:{hash_hex}"

    def get_sensitivity_label(self, level: int) -> str:
        """获取敏感级别标签"""
        return SENSITIVITY_LABELS.get(level, "公开")

    def get_category_stats(self) -> dict:
        """获取分类统计"""
        stats = {}
        for rule in self._rules:
            category = rule["category"]
            if category not in stats:
                stats[category] = {
                    "rule_count": 0,
                    "levels": {},
                }
            stats[category]["rule_count"] += 1
            level = rule["sensitivity_level"]
            stats[category]["levels"][level] = \
                stats[category]["levels"].get(level, 0) + 1
        return stats


# 全局分类器实例
data_classifier = DataClassifier()


# ==================== 模块级便捷函数 ====================

def classify_dataset(
    dataset_name: str,
    dataset_description: Optional[str] = None,
    schema_def: Optional[dict] = None,
    record_count: int = 0,
    is_realtime: bool = False,
    data_format: Optional[str] = None,
    collection_interval_ms: Optional[int] = None,
    existing_category: Optional[str] = None,
    existing_tags: Optional[list[str]] = None,
) -> dict:
    """
    模块级数据集分类函数（同步包装）

    将数据集信息映射到 DataClassifier.classify_data 的参数，
    并基于记录数、实时性等因素调整分类级别。
    """
    import asyncio

    # 提取字段列表
    data_fields: list[str] = []
    if schema_def:
        fields = schema_def.get("fields", [])
        if isinstance(fields, list):
            for f in fields:
                if isinstance(f, str):
                    data_fields.append(f)
                elif isinstance(f, dict):
                    data_fields.append(f.get("name", ""))

    # 构建搜索文本（额外关键词）
    extra_text = ""
    if is_realtime:
        extra_text += " 实时数据 real_time"
    if data_format:
        extra_text += f" {data_format}"
    if existing_tags:
        extra_text += " " + " ".join(existing_tags)

    # 调用异步分类器
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass

    if loop and loop.is_running():
        # 已有事件循环，创建新任务
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                data_classifier.classify_data(
                    data_name=f"{dataset_name} {extra_text}",
                    data_description=dataset_description,
                    data_fields=data_fields,
                    category_hint=existing_category,
                ),
            )
            result = future.result(timeout=5)
    else:
        result = asyncio.run(data_classifier.classify_data(
            data_name=f"{dataset_name} {extra_text}",
            data_description=dataset_description,
            data_fields=data_fields,
            category_hint=existing_category,
        ))

    # 基于记录数和实时性调整级别
    level = result["classification_level"]
    if record_count > 1_000_000:
        level = min(level, 2)  # 大数据集至少重要级别
    if is_realtime and record_count > 10_000:
        level = min(level, 2)

    result["classification_level"] = level
    result["sensitivity_label"] = SENSITIVITY_LABELS.get(level, "公开")

    # 补充额外信息
    result["record_count"] = record_count
    result["is_realtime"] = is_realtime
    result["data_format"] = data_format
    result["collection_interval_ms"] = collection_interval_ms

    return result


def get_classification_rules() -> list[dict]:
    """
    模块级获取分类规则函数

    返回所有分类规则列表，供 API 端点调用。
    """
    return data_classifier._rules
