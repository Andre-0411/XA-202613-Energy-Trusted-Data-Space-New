"""
数据搜索服务
全文搜索、多维筛选、搜索建议
"""
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger(__name__)

# 模拟数据目录（用于搜索）
MOCK_CATALOG = [
    {
        "id": "catalog_001",
        "name": "华能集团锡林郭勒风场发电量数据",
        "description": "华能集团内蒙古锡林郭勒风场2024年实时发电量数据，包含功率输出、风速、温度等参数",
        "category": "发电",
        "subcategory": "风电",
        "classification_level": 2,
        "sensitivity_label": "重要",
        "owner_name": "华能集团",
        "organization_name": "华能集团",
        "record_count": 1250000,
        "size_bytes": 5368709120,
        "storage_format": "parquet",
        "tags": ["风电", "发电量", "实时数据", "内蒙古"],
        "avg_rating": 4.5,
        "rating_count": 128,
        "published_at": "2024-01-15T08:00:00Z",
        "status": "published",
    },
    {
        "id": "catalog_002",
        "name": "大唐集团赤峰风场设备状态数据",
        "description": "大唐集团内蒙古赤峰风场设备运行状态数据，包含振动、转速、温度等参数",
        "category": "设备状态",
        "subcategory": "风机状态",
        "classification_level": 3,
        "sensitivity_label": "敏感",
        "owner_name": "大唐集团",
        "organization_name": "大唐集团",
        "record_count": 890000,
        "size_bytes": 3221225472,
        "storage_format": "parquet",
        "tags": ["设备状态", "风机", "振动", "赤峰"],
        "avg_rating": 4.2,
        "rating_count": 85,
        "published_at": "2024-02-20T10:00:00Z",
        "status": "published",
    },
    {
        "id": "catalog_003",
        "name": "华电集团张北风场气象数据",
        "description": "华电集团河北张北风场气象监测数据，包含风速、风向、温度、湿度等",
        "category": "发电",
        "subcategory": "气象数据",
        "classification_level": 3,
        "sensitivity_label": "敏感",
        "owner_name": "华电集团",
        "organization_name": "华电集团",
        "record_count": 2100000,
        "size_bytes": 8589934592,
        "storage_format": "parquet",
        "tags": ["气象", "风速", "张北", "监测"],
        "avg_rating": 4.7,
        "rating_count": 156,
        "published_at": "2024-03-10T09:00:00Z",
        "status": "published",
    },
    {
        "id": "catalog_004",
        "name": "国家能源集团格尔木光伏发电数据",
        "description": "国家能源集团青海格尔木光伏电站发电数据，包含功率输出、辐照度、面板温度等",
        "category": "发电",
        "subcategory": "光伏发电",
        "classification_level": 2,
        "sensitivity_label": "重要",
        "owner_name": "国家能源集团",
        "organization_name": "国家能源集团",
        "record_count": 1800000,
        "size_bytes": 6442450944,
        "storage_format": "parquet",
        "tags": ["光伏", "发电量", "格尔木", "实时数据"],
        "avg_rating": 4.6,
        "rating_count": 142,
        "published_at": "2024-01-25T11:00:00Z",
        "status": "published",
    },
    {
        "id": "catalog_005",
        "name": "国电投酒泉风场电网接入数据",
        "description": "国电投甘肃酒泉风场电网接入数据，包含上网电量、电压、电流等参数",
        "category": "调度",
        "subcategory": "电网接入",
        "classification_level": 1,
        "sensitivity_label": "核心",
        "owner_name": "国电投",
        "organization_name": "国电投",
        "record_count": 950000,
        "size_bytes": 4294967296,
        "storage_format": "parquet",
        "tags": ["电网", "接入", "酒泉", "上网电量"],
        "avg_rating": 4.8,
        "rating_count": 168,
        "published_at": "2024-02-15T08:30:00Z",
        "status": "published",
    },
    {
        "id": "catalog_006",
        "name": "电力市场交易价格数据",
        "description": "全国电力市场2024年交易价格数据，包含日前市场、实时市场、合约市场等",
        "category": "市场",
        "subcategory": "交易价格",
        "classification_level": 1,
        "sensitivity_label": "核心",
        "owner_name": "电力交易中心",
        "organization_name": "国家电网",
        "record_count": 5000000,
        "size_bytes": 10737418240,
        "storage_format": "parquet",
        "tags": ["市场", "价格", "交易", "电力市场"],
        "avg_rating": 4.9,
        "rating_count": 256,
        "published_at": "2024-01-01T00:00:00Z",
        "status": "published",
    },
]


class DataSearchService:
    """数据搜索服务"""

    def __init__(self):
        self._catalog = MOCK_CATALOG.copy()
        self._search_history: list[dict] = []

    async def search(
        self,
        keyword: str = "",
        category: Optional[str] = None,
        classification_level: Optional[int] = None,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None,
        organization_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        搜索数据目录

        Args:
            keyword: 搜索关键词
            category: 数据大类筛选
            classification_level: 敏感级别筛选
            min_level: 最低敏感级别
            max_level: 最高敏感级别
            organization_id: 组织 ID 筛选
            tags: 标签筛选
            status: 状态筛选
            date_from: 开始日期
            date_to: 结束日期
            sort_by: 排序方式
            sort_order: 排序方向
            page: 页码
            page_size: 每页大小

        Returns:
            搜索结果
        """
        start_time = time.time()

        # 过滤
        results = self._catalog.copy()

        # 关键词搜索
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                item for item in results
                if keyword_lower in item["name"].lower()
                or keyword_lower in (item.get("description") or "").lower()
                or any(keyword_lower in tag.lower() for tag in item.get("tags", []))
            ]

        # 类别筛选
        if category:
            results = [item for item in results if item.get("category") == category]

        # 敏感级别筛选
        if classification_level is not None:
            results = [item for item in results if item.get("classification_level") == classification_level]

        # 敏感级别范围
        if min_level is not None:
            results = [item for item in results if item.get("classification_level", 4) >= min_level]
        if max_level is not None:
            results = [item for item in results if item.get("classification_level", 4) <= max_level]

        # 组织筛选
        if organization_id:
            results = [item for item in results if item.get("organization_name") == organization_id]

        # 标签筛选
        if tags:
            results = [
                item for item in results
                if any(tag in item.get("tags", []) for tag in tags)
            ]

        # 状态筛选
        if status:
            results = [item for item in results if item.get("status") == status]

        # 计算相关性得分
        if keyword:
            for item in results:
                item["relevance_score"] = self._calculate_relevance(item, keyword)
                item["highlight"] = self._generate_highlight(item, keyword)
        else:
            for item in results:
                item["relevance_score"] = 1.0
                item["highlight"] = None

        # 排序
        if sort_by == "relevance":
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=(sort_order == "desc"))
        elif sort_by == "date":
            results.sort(key=lambda x: x.get("published_at", ""), reverse=(sort_order == "desc"))
        elif sort_by == "rating":
            results.sort(key=lambda x: x.get("avg_rating", 0), reverse=(sort_order == "desc"))
        elif sort_by == "size":
            results.sort(key=lambda x: x.get("size_bytes", 0), reverse=(sort_order == "desc"))

        # 分页
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        items = results[start:end]

        # 计算分面统计
        facets = self._calculate_facets(self._catalog)

        query_time_ms = (time.time() - start_time) * 1000

        # 记录搜索历史
        self._search_history.append({
            "keyword": keyword,
            "category": category,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result_count": total,
        })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "items": items,
            "facets": facets,
            "query_time_ms": round(query_time_ms, 2),
        }

    async def get_suggestions(self, keyword: str, limit: int = 10) -> list[dict]:
        """获取搜索建议"""
        if not keyword:
            return []

        keyword_lower = keyword.lower()
        suggestions = []

        # 从目录名称中提取建议
        seen = set()
        for item in self._catalog:
            name = item["name"]
            if keyword_lower in name.lower():
                if name not in seen:
                    suggestions.append({
                        "keyword": name,
                        "category": item.get("category"),
                        "count": item.get("record_count", 0),
                    })
                    seen.add(name)

        # 从标签中提取建议
        for item in self._catalog:
            for tag in item.get("tags", []):
                if keyword_lower in tag.lower() and tag not in seen:
                    suggestions.append({
                        "keyword": tag,
                        "category": item.get("category"),
                        "count": 1,
                    })
                    seen.add(tag)

        return suggestions[:limit]

    async def get_lineage_graph(self, asset_id: str) -> dict:
        """获取数据血缘图"""
        # 模拟血缘图数据
        nodes = [
            {"id": "ds_001", "name": "华能风场MQTT数据源", "type": "datasource", "metadata": {"protocol": "MQTT"}},
            {"id": "ds_002", "name": "大唐风场MQTT数据源", "type": "datasource", "metadata": {"protocol": "MQTT"}},
            {"id": "asset_001", "name": "风电发电量数据集", "type": "asset", "metadata": {"category": "发电"}},
            {"id": "asset_002", "name": "设备状态数据集", "type": "asset", "metadata": {"category": "设备状态"}},
            {"id": "task_001", "name": "数据清洗任务", "type": "task", "metadata": {"schedule": "daily"}},
            {"id": "task_002", "name": "质量检查任务", "type": "task", "metadata": {"schedule": "hourly"}},
        ]

        edges = [
            {"source": "ds_001", "target": "asset_001", "label": "采集"},
            {"source": "ds_002", "target": "asset_002", "label": "采集"},
            {"source": "asset_001", "target": "task_001", "label": "输入"},
            {"source": "asset_002", "target": "task_001", "label": "输入"},
            {"source": "task_001", "target": "task_002", "label": "触发"},
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "center_node_id": asset_id,
        }

    def _calculate_relevance(self, item: dict, keyword: str) -> float:
        """计算相关性得分"""
        score = 0.0
        keyword_lower = keyword.lower()

        # 名称匹配
        if keyword_lower in item["name"].lower():
            score += 100

        # 描述匹配
        if keyword_lower in (item.get("description") or "").lower():
            score += 50

        # 标签匹配
        for tag in item.get("tags", []):
            if keyword_lower in tag.lower():
                score += 30

        # 评分加权
        score += item.get("avg_rating", 0) * 10

        return score

    def _generate_highlight(self, item: dict, keyword: str) -> Optional[str]:
        """生成高亮摘要"""
        description = item.get("description", "")
        if not description:
            return None

        keyword_lower = keyword.lower()
        desc_lower = description.lower()

        # 找到关键词位置
        pos = desc_lower.find(keyword_lower)
        if pos == -1:
            return description[:100] + "..." if len(description) > 100 else description

        # 提取上下文
        start = max(0, pos - 50)
        end = min(len(description), pos + len(keyword) + 50)
        snippet = description[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(description):
            snippet = snippet + "..."

        return snippet

    def _calculate_facets(self, items: list[dict]) -> dict:
        """计算分面统计"""
        categories = {}
        classification_levels = {}
        organizations = {}
        tags = {}

        for item in items:
            # 类别统计
            category = item.get("category", "其他")
            categories[category] = categories.get(category, 0) + 1

            # 敏感级别统计
            level = item.get("classification_level", 4)
            level_label = {1: "核心", 2: "重要", 3: "敏感", 4: "公开"}.get(level, "公开")
            classification_levels[level_label] = classification_levels.get(level_label, 0) + 1

            # 组织统计
            org = item.get("organization_name", "未知")
            organizations[org] = organizations.get(org, 0) + 1

            # 标签统计
            for tag in item.get("tags", []):
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "categories": categories,
            "classification_levels": classification_levels,
            "organizations": organizations,
            "tags": tags,
        }


# 全局搜索服务实例
data_search_service = DataSearchService()
