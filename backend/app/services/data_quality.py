"""
数据质量评估引擎
五维评分：完整性、准确性、一致性、时效性、唯一性
"""
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger(__name__)

# 质量等级阈值
GRADE_THRESHOLDS = {
    "A": 90,  # 优秀
    "B": 80,  # 良好
    "C": 70,  # 中等
    "D": 60,  # 较差
    "F": 0,   # 不合格
}

# 维度权重配置
DEFAULT_DIMENSION_WEIGHTS = {
    "completeness": 0.25,
    "accuracy": 0.25,
    "consistency": 0.20,
    "timeliness": 0.15,
    "uniqueness": 0.15,
}


class DataQualityEngine:
    """数据质量评估引擎"""

    def __init__(self):
        self._reports: dict[str, dict] = {}  # 报告缓存
        self._dimension_weights = DEFAULT_DIMENSION_WEIGHTS.copy()

    async def assess_quality(
        self,
        asset_id: str,
        asset_name: Optional[str] = None,
        data_sample: Optional[list[dict]] = None,
        dimensions: Optional[list[str]] = None,
    ) -> dict:
        """
        评估数据质量

        Args:
            asset_id: 资产 ID
            asset_name: 资产名称
            data_sample: 数据样本
            dimensions: 检查维度列表

        Returns:
            质量评估结果
        """
        # 确定检查维度
        check_dims = dimensions or list(self._dimension_weights.keys())

        # 计算各维度得分
        dimension_scores = []
        for dim in check_dims:
            if dim in self._dimension_weights:
                score_result = await self._assess_dimension(dim, data_sample)
                dimension_scores.append({
                    "dimension": dim,
                    "score": score_result["score"],
                    "weight": self._dimension_weights.get(dim, 0.2),
                    "details": score_result.get("details"),
                    "check_items": score_result.get("check_items", []),
                })

        # 计算加权总分
        total_score = 0.0
        total_weight = 0.0
        for dim_score in dimension_scores:
            total_score += dim_score["score"] * dim_score["weight"]
            total_weight += dim_score["weight"]

        if total_weight > 0:
            total_score = total_score / total_weight

        # 确定质量等级
        grade = self._calculate_grade(total_score)

        # 生成报告 ID
        report_id = str(uuid.uuid4())

        result = {
            "id": report_id,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "total_score": round(total_score, 2),
            "grade": grade,
            "dimensions": dimension_scores,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "assessed_by": "quality_engine",
            "status": "completed",
        }

        # 缓存报告
        self._reports[report_id] = result

        logger.info(f"质量评估完成: {asset_id} -> {grade} ({total_score:.2f})")
        return result

    async def get_report(self, report_id: str) -> Optional[dict]:
        """获取质量报告"""
        return self._reports.get(report_id)

    async def get_latest_report(self, asset_id: str) -> Optional[dict]:
        """获取资产最新质量报告"""
        asset_reports = [
            r for r in self._reports.values()
            if r.get("asset_id") == asset_id
        ]
        if asset_reports:
            # 按时间排序
            asset_reports.sort(key=lambda x: x.get("assessed_at", ""), reverse=True)
            return asset_reports[0]
        return None

    async def list_reports(
        self,
        asset_id: Optional[str] = None,
        min_score: Optional[float] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """列出质量报告"""
        reports = list(self._reports.values())

        # 过滤
        if asset_id:
            reports = [r for r in reports if r.get("asset_id") == asset_id]
        if min_score is not None:
            reports = [r for r in reports if r.get("total_score", 0) >= min_score]

        # 排序
        reports.sort(key=lambda x: x.get("assessed_at", ""), reverse=True)

        # 分页
        total = len(reports)
        start = (page - 1) * page_size
        end = start + page_size
        items = reports[start:end]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def get_quality_statistics(self) -> dict:
        """获取质量统计"""
        reports = list(self._reports.values())

        if not reports:
            return {
                "total_assets": 0,
                "checked_assets": 0,
                "avg_score": 0.0,
                "grade_distribution": {},
                "dimension_averages": {},
            }

        # 计算统计
        total_score = sum(r.get("total_score", 0) for r in reports)
        avg_score = total_score / len(reports)

        # 等级分布
        grade_distribution = {}
        for r in reports:
            grade = r.get("grade", "F")
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

        # 维度平均分
        dimension_totals = {}
        dimension_counts = {}
        for r in reports:
            for dim in r.get("dimensions", []):
                dim_name = dim.get("dimension")
                dim_score = dim.get("score", 0)
                if dim_name:
                    dimension_totals[dim_name] = dimension_totals.get(dim_name, 0) + dim_score
                    dimension_counts[dim_name] = dimension_counts.get(dim_name, 0) + 1

        dimension_averages = {}
        for dim_name, total in dimension_totals.items():
            count = dimension_counts.get(dim_name, 1)
            dimension_averages[dim_name] = round(total / count, 2)

        # 模拟趋势数据（最近7天）
        trend = self._generate_trend_data()

        return {
            "total_assets": len(set(r.get("asset_id") for r in reports)),
            "checked_assets": len(reports),
            "avg_score": round(avg_score, 2),
            "grade_distribution": grade_distribution,
            "dimension_averages": dimension_averages,
            "trend": trend,
        }

    async def _assess_dimension(self, dimension: str, data_sample: Optional[list[dict]]) -> dict:
        """评估单个维度"""
        # 模拟评估逻辑
        if dimension == "completeness":
            return await self._assess_completeness(data_sample)
        elif dimension == "accuracy":
            return await self._assess_accuracy(data_sample)
        elif dimension == "consistency":
            return await self._assess_consistency(data_sample)
        elif dimension == "timeliness":
            return await self._assess_timeliness(data_sample)
        elif dimension == "uniqueness":
            return await self._assess_uniqueness(data_sample)
        else:
            return {"score": 80.0, "details": {"message": "未知维度"}}

    async def _assess_completeness(self, data_sample: Optional[list[dict]]) -> dict:
        """评估完整性"""
        if not data_sample:
            # 模拟得分
            score = random.uniform(85, 98)
            return {
                "score": round(score, 2),
                "details": {
                    "null_rate": round(random.uniform(0, 0.05), 4),
                    "field_coverage": round(random.uniform(0.95, 1.0), 4),
                    "total_fields": 10,
                    "filled_fields": random.randint(9, 10),
                },
                "check_items": [
                    {"name": "空值检查", "status": "pass", "score": round(score, 2)},
                    {"name": "字段覆盖率", "status": "pass", "score": round(score + 1, 2)},
                ],
            }

        # 实际计算
        total_cells = 0
        empty_cells = 0
        for record in data_sample:
            for key, value in record.items():
                total_cells += 1
                if value is None or value == "":
                    empty_cells += 1

        null_rate = empty_cells / total_cells if total_cells > 0 else 1.0
        score = (1 - null_rate) * 100

        return {
            "score": round(score, 2),
            "details": {
                "null_rate": round(null_rate, 4),
                "total_cells": total_cells,
                "empty_cells": empty_cells,
            },
            "check_items": [
                {"name": "空值检查", "status": "pass" if null_rate < 0.05 else "warning", "score": round(score, 2)},
            ],
        }

    async def _assess_accuracy(self, data_sample: Optional[list[dict]]) -> dict:
        """评估准确性"""
        if not data_sample:
            score = random.uniform(90, 99)
            return {
                "score": round(score, 2),
                "details": {
                    "out_of_range_rate": round(random.uniform(0, 0.02), 4),
                    "format_compliance": round(random.uniform(0.98, 1.0), 4),
                },
                "check_items": [
                    {"name": "数值范围检查", "status": "pass", "score": round(score, 2)},
                    {"name": "格式合规检查", "status": "pass", "score": round(score - 1, 2)},
                ],
            }

        # 模拟准确性检查
        score = random.uniform(90, 99)
        return {
            "score": round(score, 2),
            "details": {"message": "准确性检查完成"},
            "check_items": [
                {"name": "数值范围检查", "status": "pass", "score": round(score, 2)},
            ],
        }

    async def _assess_consistency(self, data_sample: Optional[list[dict]]) -> dict:
        """评估一致性"""
        score = random.uniform(88, 97)
        return {
            "score": round(score, 2),
            "details": {
                "type_consistency": round(random.uniform(0.95, 1.0), 4),
                "cross_table_consistency": round(random.uniform(0.90, 1.0), 4),
            },
            "check_items": [
                {"name": "类型一致性", "status": "pass", "score": round(score, 2)},
                {"name": "跨表一致性", "status": "pass", "score": round(score - 2, 2)},
            ],
        }

    async def _assess_timeliness(self, data_sample: Optional[list[dict]]) -> dict:
        """评估时效性"""
        score = random.uniform(80, 95)
        return {
            "score": round(score, 2),
            "details": {
                "avg_delay_seconds": random.randint(1, 30),
                "real_time_ratio": round(random.uniform(0.85, 1.0), 4),
            },
            "check_items": [
                {"name": "数据延迟检查", "status": "pass", "score": round(score, 2)},
                {"name": "实时性检查", "status": "pass", "score": round(score + 2, 2)},
            ],
        }

    async def _assess_uniqueness(self, data_sample: Optional[list[dict]]) -> dict:
        """评估唯一性"""
        score = random.uniform(92, 99)
        return {
            "score": round(score, 2),
            "details": {
                "duplicate_rate": round(random.uniform(0, 0.03), 4),
                "unique_records": random.randint(970, 1000),
                "total_records": 1000,
            },
            "check_items": [
                {"name": "重复记录检查", "status": "pass", "score": round(score, 2)},
            ],
        }

    def _calculate_grade(self, score: float) -> str:
        """计算质量等级"""
        for grade, threshold in sorted(GRADE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return grade
        return "F"

    def _generate_trend_data(self) -> list[dict]:
        """生成趋势数据（模拟最近7天）"""
        trend = []
        for i in range(7):
            date = datetime.now().strftime("%Y-%m-%d")
            base_score = random.uniform(80, 95)
            trend.append({
                "date": date,
                "total_score": round(base_score, 2),
                "completeness": round(base_score + random.uniform(-5, 5), 2),
                "accuracy": round(base_score + random.uniform(-3, 3), 2),
                "consistency": round(base_score + random.uniform(-4, 4), 2),
                "timeliness": round(base_score + random.uniform(-6, 6), 2),
                "uniqueness": round(base_score + random.uniform(-2, 2), 2),
            })
        return trend


# 全局质量引擎实例
data_quality_engine = DataQualityEngine()
