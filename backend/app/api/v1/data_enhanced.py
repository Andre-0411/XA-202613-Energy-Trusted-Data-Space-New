"""
数据增强 API — /api/v1/data
============================
提供数据自动分级、质量检测、血缘追踪、数据预览、评价反馈、版本管理、边缘预处理、断线续传等增强功能

端点列表：
- POST   /classify              — 对数据集进行自动分类分级
- GET    /classification-rules  — 获取分类规则列表
- POST   /quality/check         — 触发数据质量检测
- GET    /quality/report/{id}   — 获取质量检测报告
- GET    /quality/statistics    — 质量统计概览
- GET    /lineage/{id}          — 获取数据血缘图
- GET    /lineage/{id}/versions — 获取版本历史
- POST   /lineage/record        — 记录血缘事件
- GET    /preview/{id}          — 脱敏数据预览（最多10条）
- POST   /evaluate              — 数据集评价/反馈
- GET    /evaluate/{id}         — 获取数据集评价
- POST   /versions              — 创建数据版本
- GET    /versions/{dataset_id} — 获取版本历史
- GET    /version/{version_id}  — 获取版本详情
- POST   /versions/compare      — 对比两个版本
- POST   /versions/rollback     — 回滚到指定版本
- POST   /versions/tag          — 为版本添加标签
- GET    /versions/{dataset_id}/tags — 获取版本标签
- GET    /versions/{dataset_id}/statistics — 获取版本统计
- POST   /preprocess            — 边缘预处理（格式转换+压缩+异常过滤）
- POST   /preprocess/schema     — 注册数据集Schema
- POST   /preprocess/anomaly-rule — 添加异常检测规则
- POST   /preprocess/batch      — 数据批量打包
- POST   /offline/enqueue       — 离线消息入队
- GET    /offline/statistics    — 断线续传统计
- POST   /offline/acknowledge/{id} — 确认消息已收到
- POST   /offline/status        — 设置连接状态
- DELETE /offline/clear         — 清空离线队列
"""
import uuid
import logging
import copy
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field

from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# 请求/响应 Schema
# ============================================================


class ClassifyRequest(BaseModel):
    """分类分级请求"""
    dataset_name: str = Field(..., description="数据集名称")
    dataset_description: Optional[str] = Field(None, description="数据集描述")
    schema_def: Optional[dict] = Field(None, description="数据 Schema 定义")
    record_count: int = Field(0, description="记录数量")
    is_realtime: bool = Field(False, description="是否实时数据")
    data_format: Optional[str] = Field(None, description="数据格式（csv/json/parquet）")
    collection_interval_ms: Optional[int] = Field(None, description="采集间隔（毫秒）")
    existing_category: Optional[str] = Field(None, description="已有分类")
    existing_tags: Optional[list[str]] = Field(None, description="已有标签")


class QualityCheckRequest(BaseModel):
    """质量检测请求"""
    dataset_id: str = Field(..., description="数据集ID")
    data: list[dict] = Field(..., description="待检测数据")
    schema_def: Optional[dict] = Field(None, description="数据 Schema 定义")
    critical_fields: Optional[list[str]] = Field(None, description="关键字段列表")
    data_type: str = Field("batch", description="数据类型（realtime/near_realtime/batch）")
    expected_interval_ms: Optional[int] = Field(None, description="期望采集间隔（毫秒）")


class LineageEventRequest(BaseModel):
    """血缘事件记录请求"""
    dataset_id: str = Field(..., description="数据集ID")
    event_type: str = Field(..., description="事件类型描述")
    source_nodes: Optional[list[dict]] = Field(None, description="源节点列表")
    target_node: Optional[dict] = Field(None, description="目标节点")
    operation: str = Field("transform", description="操作类型（collect/transform/store/query）")
    metadata: Optional[dict] = Field(None, description="附加元数据")


class EvaluateRequest(BaseModel):
    """数据集评价请求"""
    dataset_id: str = Field(..., description="数据集ID")
    user_name: Optional[str] = Field(None, description="评价用户")
    rating: int = Field(..., ge=1, le=5, description="评分（1-5）")
    comment: Optional[str] = Field(None, description="评价内容")
    tags: Optional[list[str]] = Field(None, description="评价标签")


# ============================================================
# 内存存储（演示用，生产环境应使用数据库）
# ============================================================

# 质量报告存储
_quality_reports: dict[str, dict] = {}

# 评价存储
_evaluations: dict[str, list[dict]] = {}

# 数据预览缓存
_preview_cache: dict[str, dict] = {}


# ============================================================
# 分类分级端点
# ============================================================

@router.post("/classify")
async def classify_dataset(req: ClassifyRequest,
    user: dict = Depends(get_current_user)):
    """
    对数据集进行自动分类分级

    基于关键词匹配、字段类型、数据量级等多维度规则，
    自动识别数据集所属分类和安全等级。
    """
    from app.services.data_classifier import classify_dataset, get_classification_rules

    result = classify_dataset(
        dataset_name=req.dataset_name,
        dataset_description=req.dataset_description,
        schema_def=req.schema_def,
        record_count=req.record_count,
        is_realtime=req.is_realtime,
        data_format=req.data_format,
        collection_interval_ms=req.collection_interval_ms,
        existing_category=req.existing_category,
        existing_tags=req.existing_tags,
    )
    return ApiResponse(data=result)


@router.get("/classification-rules")
async def get_classification_rules(user: dict = Depends(get_current_user)):
    """
    获取分类规则列表

    返回所有分类规则，包括关键词匹配规则、字段类型推断规则、
    安全等级提升规则等，供前端展示和管理。
    """
    from app.services.data_classifier import get_classification_rules as get_rules
    rules = get_rules()
    return ApiResponse(data={
        "rules": rules,
        "total": len(rules),
    })


class ClassifyBatchItem(BaseModel):
    """批量分类单项"""
    name: str = Field(..., description="数据集名称")
    description: Optional[str] = Field(None, description="数据集描述")
    fields: Optional[list[str]] = Field(None, description="字段列表")
    category_hint: Optional[str] = Field(None, description="分类提示")


class ClassifyBatchRequest(BaseModel):
    """批量分类请求"""
    items: list[ClassifyBatchItem] = Field(..., description="待分类数据集列表")


@router.post("/classify/batch")
async def classify_batch(req: ClassifyBatchRequest,
    user: dict = Depends(get_current_user)):
    """
    批量分类分级

    对多个数据集进行自动分类分级，返回每个数据集的分类结果。
    """
    from app.services.data_classifier import classify_dataset

    results = []
    for item in req.items:
        result = classify_dataset(
            dataset_name=item.name,
            dataset_description=item.description,
            schema_def={"fields": item.fields} if item.fields else None,
            existing_category=item.category_hint,
        )
        results.append(result)

    return ApiResponse(data=results)


class VerifyIntegrityRequest(BaseModel):
    """完整性验证请求"""
    data_name: str = Field(..., description="数据名称")
    data_fields: list[str] = Field(..., description="数据字段列表")
    expected_hash: str = Field(..., description="期望的哈希值")


@router.post("/classify/verify")
async def verify_integrity(req: VerifyIntegrityRequest,
    user: dict = Depends(get_current_user)):
    """
    验证数据完整性

    计算数据字段的 SM3 哈希，与期望哈希对比验证完整性。
    """
    from app.core.gmssl_adapter import gmssl_adapter

    # 计算实际哈希
    fields_str = "|".join(sorted(req.data_fields))
    actual_hash = gmssl_adapter.sm3_hash(fields_str)

    valid = actual_hash == req.expected_hash

    return ApiResponse(data={
        "valid": valid,
        "expected_hash": req.expected_hash,
        "actual_hash": actual_hash,
        "data_name": req.data_name,
    })


# ============================================================
# 质量检测端点
# ============================================================

@router.post("/quality/check")
async def trigger_quality_check(req: QualityCheckRequest,
    user: dict = Depends(get_current_user)):
    """
    触发数据质量检测

    对传入数据进行完整性、时效性、准确性、一致性四维度检测，
    返回综合评分和详细检测报告。
    """
    from app.services.data_quality import check_quality

    report = check_quality(
        data=req.data,
        schema_def=req.schema_def,
        critical_fields=req.critical_fields,
        data_type=req.data_type,
        expected_interval_ms=req.expected_interval_ms,
    )

    # 存储报告
    report_id = str(uuid.uuid4())
    report["report_id"] = report_id
    report["dataset_id"] = req.dataset_id
    _quality_reports[report_id] = report
    # 按 dataset_id 也存储一份（保留最新）
    _quality_reports[f"latest:{req.dataset_id}"] = report

    return ApiResponse(data=report)


@router.get("/quality/report/{dataset_id}")
async def get_quality_report(dataset_id: str,
    user: dict = Depends(get_current_user)):
    """
    获取数据集的质量检测报告

    返回最近一次质量检测的完整报告，包含各维度得分、
    问题明细和改进建议。
    """
    report = _quality_reports.get(f"latest:{dataset_id}")
    if not report:
        return ApiResponse(code=2001, message="该数据集暂无质量检测报告", data=None)
    return ApiResponse(data=report)


@router.get("/quality/statistics")
async def get_quality_statistics(user: dict = Depends(get_current_user)):
    """
    质量统计概览

    返回所有数据集的质量统计信息，包括各等级分布、
    平均得分、问题类型分布等。
    """
    from app.services.data_quality import generate_report_summary

    # 汇总所有报告（排除 latest: 前缀的缓存）
    all_reports = [
        v for k, v in _quality_reports.items()
        if not k.startswith("latest:")
    ]

    if not all_reports:
        return ApiResponse(data={
            "total_datasets": 0,
            "avg_score": 0,
            "grade_distribution": {},
            "dimension_averages": {},
            "top_issues": [],
        })

    # 质量等级分布
    grade_dist = {}
    for report in all_reports:
        grade = report.get("grade", "D")
        grade_dist[grade] = grade_dist.get(grade, 0) + 1

    # 平均得分
    avg_score = sum(r.get("overall_score", 0) for r in all_reports) / len(all_reports)

    # 各维度平均分
    dim_totals = {"completeness": 0, "timeliness": 0, "accuracy": 0, "consistency": 0}
    for report in all_reports:
        dims = report.get("dimensions", {})
        for dim in dim_totals:
            dim_totals[dim] += dims.get(dim, {}).get("score", 0)
    dim_averages = {dim: round(total / len(all_reports), 1) for dim, total in dim_totals.items()}

    # 问题类型分布
    issue_types = {}
    for report in all_reports:
        for issue in report.get("issues", []):
            dim = issue.get("dimension", "unknown")
            issue_types[dim] = issue_types.get(dim, 0) + 1

    return ApiResponse(data={
        "total_datasets": len(all_reports),
        "avg_score": round(avg_score, 1),
        "grade_distribution": grade_dist,
        "dimension_averages": dim_averages,
        "issue_distribution": issue_types,
    })


# ============================================================
# 血缘追踪端点
# ============================================================

@router.get("/lineage/{dataset_id}")
async def get_lineage_graph(dataset_id: str,
    user: dict = Depends(get_current_user)):
    """
    获取数据血缘图

    返回指定数据集的完整血缘图谱，数据结构适配前端 ECharts graph 类型，
    包含节点（nodes）和连线（links）。
    """
    from app.services.data_lineage import get_lineage_store

    store = get_lineage_store()
    graph = store.get_lineage_graph(dataset_id)

    if not graph["nodes"]:
        return ApiResponse(code=2001, message="该数据集暂无血缘数据", data=None)

    return ApiResponse(data=graph)


@router.get("/lineage/{dataset_id}/versions")
async def get_lineage_versions(dataset_id: str,
    user: dict = Depends(get_current_user)):
    """
    获取数据集的版本历史

    返回数据集的所有版本记录，按时间倒序排列。
    """
    from app.services.data_lineage import get_lineage_store

    store = get_lineage_store()
    versions = store.get_versions(dataset_id)

    return ApiResponse(data={
        "dataset_id": dataset_id,
        "versions": versions,
        "total": len(versions),
    })


@router.post("/lineage/record")
async def record_lineage_event(req: LineageEventRequest,
    user: dict = Depends(get_current_user)):
    """
    记录血缘事件

    记录数据从一个或多个源节点到目标节点的血缘关系，
    用于构建完整的数据血缘图谱。
    """
    from app.services.data_lineage import get_lineage_store

    store = get_lineage_store()
    event = store.record_lineage_event(
        dataset_id=req.dataset_id,
        event_type=req.event_type,
        source_nodes=req.source_nodes,
        target_node=req.target_node,
        operation=req.operation,
        metadata=req.metadata,
    )
    return ApiResponse(data=event)


@router.get("/lineage/{dataset_id}/trace")
async def trace_lineage(
    dataset_id: str,
    direction: str = Query("forward", description="追踪方向：forward=溯源, backward=追踪"),
    node_id: Optional[str] = Query(None, description="起始节点ID（不指定则使用数据集关联的首个节点）"),
    max_depth: int = Query(10, ge=1, le=50, description="最大追踪深度"),
):
    """
    数据血缘追踪

    - forward: 正向溯源，追踪数据从哪来
    - backward: 反向追踪，追踪数据去了哪
    """
    from app.services.data_lineage import get_lineage_store

    store = get_lineage_store()

    # 如果未指定节点，从数据集关联的边中找一个起始节点
    if not node_id:
        graph = store.get_lineage_graph(dataset_id)
        if not graph["nodes"]:
            return ApiResponse(code=2001, message="该数据集暂无血缘数据", data=None)
        node_id = graph["nodes"][0]["id"]

    if direction == "forward":
        result = store.trace_forward(node_id, max_depth)
    else:
        result = store.trace_backward(node_id, max_depth)

    return ApiResponse(data=result)


# ============================================================
# 数据预览端点
# ============================================================

@router.get("/preview/{dataset_id}")
async def preview_dataset(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=10, description="预览条数（最多10条）"),
):
    """
    脱敏数据预览

    返回数据集的脱敏预览数据（最多10条），用于数据质量快速查看。
    敏感字段（如身份证、手机号、邮箱等）会被脱敏处理。
    """
    # 模拟数据预览（实际应从数据库或数据源获取）
    preview_data = _preview_cache.get(dataset_id)
    if not preview_data:
        # 生成模拟预览数据
        preview_data = _generate_mock_preview(dataset_id)
        _preview_cache[dataset_id] = preview_data

    records = preview_data.get("records", [])[:limit]
    masked_records = [_mask_sensitive_fields(r) for r in records]

    return ApiResponse(data={
        "dataset_id": dataset_id,
        "records": masked_records,
        "total_available": preview_data.get("total", 0),
        "showing": len(masked_records),
        "masked_fields": _get_masked_field_names(),
    })


# ============================================================
# 评价反馈端点
# ============================================================

@router.post("/evaluate")
async def evaluate_dataset(req: EvaluateRequest,
    user: dict = Depends(get_current_user)):
    """
    提交数据集评价/反馈

    用户可以对数据集进行评分和评论，支持添加评价标签。
    """
    evaluation = {
        "evaluation_id": str(uuid.uuid4()),
        "dataset_id": req.dataset_id,
        "user_name": req.user_name or "匿名用户",
        "rating": req.rating,
        "comment": req.comment or "",
        "tags": req.tags or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if req.dataset_id not in _evaluations:
        _evaluations[req.dataset_id] = []
    _evaluations[req.dataset_id].append(evaluation)

    logger.info("数据集评价: dataset=%s, rating=%d", req.dataset_id, req.rating)

    return ApiResponse(data=evaluation)


@router.get("/evaluate/{dataset_id}")
async def get_dataset_evaluations(
    dataset_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
):
    """
    获取数据集的评价列表

    返回评价列表、平均评分、评分分布等统计信息。
    """
    evaluations = _evaluations.get(dataset_id, [])

    # 统计
    total = len(evaluations)
    avg_rating = sum(e["rating"] for e in evaluations) / total if total > 0 else 0

    # 评分分布
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for e in evaluations:
        rating_dist[e["rating"]] = rating_dist.get(e["rating"], 0) + 1

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    paginated = evaluations[start:end]

    return ApiResponse(data={
        "dataset_id": dataset_id,
        "evaluations": paginated,
        "total": total,
        "avg_rating": round(avg_rating, 1),
        "rating_distribution": rating_dist,
        "page": page,
        "page_size": page_size,
    })


# ============================================================
# 辅助函数
# ============================================================

# 敏感字段关键词
_SENSITIVE_KEYWORDS = [
    "id_card", "身份证", "phone", "电话", "手机",
    "email", "邮箱", "address", "地址", "name", "姓名",
    "password", "密码", "bank", "银行", "account", "账号",
]


def _mask_sensitive_fields(record: dict) -> dict:
    """对记录中的敏感字段进行脱敏"""
    masked = {}
    for key, value in record.items():
        is_sensitive = any(kw in key.lower() for kw in _SENSITIVE_KEYWORDS)
        if is_sensitive and isinstance(value, str) and len(value) > 2:
            # 保留首尾各1个字符，中间用*替换
            masked[key] = value[0] + "*" * (len(value) - 2) + value[-1]
        else:
            masked[key] = value
    return masked


def _get_masked_field_names() -> list[str]:
    """获取被脱敏的字段名列表"""
    return _SENSITIVE_KEYWORDS


def _generate_mock_preview(dataset_id: str) -> dict:
    """生成模拟预览数据"""
    records = []
    for i in range(10):
        records.append({
            "id": f"REC-{dataset_id[:8]}-{i:04d}",
            "timestamp": "2025-01-15T10:00:00Z",
            "device_id": f"DEV-{i:03d}",
            "power_output": round(100 + i * 15.5, 2),
            "voltage": round(220 + i * 0.5, 1),
            "temperature": round(25 + i * 1.2, 1),
            "status": "normal" if i % 3 != 0 else "warning",
        })
    return {"records": records, "total": 1000}


# ============================================================
# 版本管理端点
# ============================================================

class CreateVersionRequest(BaseModel):
    """创建版本请求"""
    dataset_id: str = Field(..., description="数据集ID")
    description: str = Field("", description="版本描述")
    created_by: str = Field("system", description="创建者")
    record_count: int = Field(0, description="记录数量")
    file_size_bytes: int = Field(0, description="文件大小（字节）")
    tags: Optional[list[str]] = Field(None, description="版本标签")


class CompareVersionsRequest(BaseModel):
    """版本对比请求"""
    version_id_a: str = Field(..., description="版本A ID")
    version_id_b: str = Field(..., description="版本B ID")


class RollbackRequest(BaseModel):
    """版本回滚请求"""
    dataset_id: str = Field(..., description="数据集ID")
    target_version_id: str = Field(..., description="目标版本ID")
    created_by: str = Field("system", description="操作者")
    reason: str = Field("", description="回滚原因")


class AddVersionTagRequest(BaseModel):
    """添加版本标签请求"""
    dataset_id: str = Field(..., description="数据集ID")
    version_id: str = Field(..., description="版本ID")
    tag_name: str = Field(..., description="标签名称")
    description: str = Field("", description="标签描述")
    created_by: str = Field("system", description="创建者")


@router.post("/versions")
async def create_version(req: CreateVersionRequest,
    user: dict = Depends(get_current_user)):
    """创建数据版本"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    version = store.create_version(
        dataset_id=req.dataset_id,
        description=req.description,
        created_by=req.created_by,
        record_count=req.record_count,
        file_size_bytes=req.file_size_bytes,
        tags=req.tags,
    )
    return ApiResponse(data=store._version_to_dict(version))


@router.get("/versions/{dataset_id}")
async def get_version_history(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取数据集的版本历史"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    result = store.get_versions(dataset_id, page=page, page_size=page_size)
    return ApiResponse(data=result)


@router.get("/version/{version_id}")
async def get_version_detail(version_id: str,
    user: dict = Depends(get_current_user)):
    """获取版本详情"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    version = store.get_version(version_id)
    if not version:
        return ApiResponse(code=2001, message="版本不存在", data=None)
    return ApiResponse(data=version)


@router.post("/versions/compare")
async def compare_versions(req: CompareVersionsRequest,
    user: dict = Depends(get_current_user)):
    """对比两个版本"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    diff = store.compare_versions(req.version_id_a, req.version_id_b)
    return ApiResponse(data=diff)


@router.post("/versions/rollback")
async def rollback_version(req: RollbackRequest,
    user: dict = Depends(get_current_user)):
    """回滚到指定版本"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    version = store.rollback_to_version(
        dataset_id=req.dataset_id,
        target_version_id=req.target_version_id,
        created_by=req.created_by,
        reason=req.reason,
    )
    if not version:
        return ApiResponse(code=2001, message="回滚失败：目标版本不存在", data=None)
    return ApiResponse(data=store._version_to_dict(version))


@router.post("/versions/tag")
async def add_version_tag(req: AddVersionTagRequest,
    user: dict = Depends(get_current_user)):
    """为版本添加标签"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    tag = store.add_tag(
        dataset_id=req.dataset_id,
        version_id=req.version_id,
        tag_name=req.tag_name,
        description=req.description,
        created_by=req.created_by,
    )
    if not tag:
        return ApiResponse(code=2001, message="添加标签失败：版本不存在", data=None)
    return ApiResponse(data={
        "tag_id": tag.tag_id,
        "version_id": tag.version_id,
        "tag_name": tag.tag_name,
        "description": tag.description,
        "created_by": tag.created_by,
        "created_at": tag.created_at,
    })


@router.get("/versions/{dataset_id}/tags")
async def get_version_tags(dataset_id: str,
    user: dict = Depends(get_current_user)):
    """获取数据集的版本标签"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    tags = store.get_tags(dataset_id)
    return ApiResponse(data={"dataset_id": dataset_id, "tags": tags, "total": len(tags)})


@router.get("/versions/{dataset_id}/statistics")
async def get_version_statistics(dataset_id: str,
    user: dict = Depends(get_current_user)):
    """获取版本统计"""
    from app.services.data_version_service import get_version_store

    store = get_version_store()
    stats = store.get_statistics(dataset_id)
    return ApiResponse(data=stats)


# ============================================================
# 边缘预处理端点
# ============================================================

class PreprocessRequest(BaseModel):
    """边缘预处理请求"""
    dataset_id: str = Field(..., description="数据集ID")
    data: list[dict] = Field(..., description="待处理数据")
    source_format: str = Field("json", description="源格式（json/csv/parquet）")
    target_format: str = Field("json", description="目标格式")
    compression: str = Field("none", description="压缩类型（none/gzip/zlib）")
    enable_anomaly_detection: bool = Field(True, description="是否启用异常检测")
    enable_normalization: bool = Field(True, description="是否启用标准化")
    schema_fields: Optional[list[dict]] = Field(None, description="字段Schema定义")


class SchemaRegisterRequest(BaseModel):
    """Schema注册请求"""
    dataset_id: str = Field(..., description="数据集ID")
    fields: list[dict] = Field(..., description="字段定义列表")


class AnomalyRuleRequest(BaseModel):
    """异常规则请求"""
    dataset_id: str = Field(..., description="数据集ID")
    field_name: str = Field(..., description="字段名")
    anomaly_type: str = Field(..., description="异常类型")
    threshold: Optional[float] = Field(None, description="阈值")
    description: str = Field("", description="描述")
    action: str = Field("flag", description="处理方式（flag/remove/interpolate）")


@router.post("/preprocess")
async def preprocess_data(req: PreprocessRequest,
    user: dict = Depends(get_current_user)):
    """
    边缘预处理

    对数据进行格式转换、压缩、异常过滤等预处理操作。
    """
    from app.services.edge_preprocessor import (
        get_edge_preprocessor, DataFormat, CompressionType, FieldSchema
    )

    preprocessor = get_edge_preprocessor()

    # 注册 Schema（如果提供）
    if req.schema_fields:
        fields = []
        for f in req.schema_fields:
            fields.append(FieldSchema(
                name=f.get("name", ""),
                data_type=f.get("data_type", "string"),
                unit=f.get("unit"),
                min_value=f.get("min_value"),
                max_value=f.get("max_value"),
                required=f.get("required", False),
                description=f.get("description"),
            ))
        preprocessor.register_schema(req.dataset_id, fields)

    # 格式映射
    format_map = {"json": DataFormat.JSON, "csv": DataFormat.CSV, "parquet": DataFormat.PARQUET}
    compression_map = {"none": CompressionType.NONE, "gzip": CompressionType.GZIP, "zlib": CompressionType.ZLIB}

    result = preprocessor.preprocess(
        data=req.data,
        dataset_id=req.dataset_id,
        source_format=format_map.get(req.source_format, DataFormat.JSON),
        target_format=format_map.get(req.target_format, DataFormat.JSON),
        compression=compression_map.get(req.compression, CompressionType.NONE),
        enable_anomaly_detection=req.enable_anomaly_detection,
        enable_normalization=req.enable_normalization,
    )

    return ApiResponse(data={
        "original_count": result.original_count,
        "processed_count": result.processed_count,
        "removed_count": result.removed_count,
        "anomaly_count": result.anomaly_count,
        "anomalies": result.anomalies,
        "format_converted": result.format_converted,
        "compressed": result.compressed,
        "compression_ratio": round(result.compression_ratio, 4),
        "processing_time_ms": result.processing_time_ms,
        "data_size_bytes": len(result.processed_data) if result.processed_data else 0,
    })


@router.post("/preprocess/schema")
async def register_schema(req: SchemaRegisterRequest,
    user: dict = Depends(get_current_user)):
    """注册数据集 Schema"""
    from app.services.edge_preprocessor import get_edge_preprocessor, FieldSchema

    preprocessor = get_edge_preprocessor()
    fields = []
    for f in req.fields:
        fields.append(FieldSchema(
            name=f.get("name", ""),
            data_type=f.get("data_type", "string"),
            unit=f.get("unit"),
            min_value=f.get("min_value"),
            max_value=f.get("max_value"),
            required=f.get("required", False),
            description=f.get("description"),
        ))

    preprocessor.register_schema(req.dataset_id, fields)
    return ApiResponse(data={"dataset_id": req.dataset_id, "fields_count": len(fields)})


@router.post("/preprocess/anomaly-rule")
async def add_anomaly_rule(req: AnomalyRuleRequest,
    user: dict = Depends(get_current_user)):
    """添加异常检测规则"""
    from app.services.edge_preprocessor import get_edge_preprocessor, AnomalyRule, AnomalyType

    preprocessor = get_edge_preprocessor()
    rule = AnomalyRule(
        field_name=req.field_name,
        anomaly_type=AnomalyType(req.anomaly_type),
        threshold=req.threshold,
        description=req.description,
        action=req.action,
    )
    preprocessor.add_anomaly_rule(req.dataset_id, rule)
    return ApiResponse(data={"message": "规则添加成功", "dataset_id": req.dataset_id})


@router.post("/preprocess/batch")
async def batch_data(
    data: list[dict],
    batch_size: int = Query(100, ge=10, le=1000, description="批次大小"),
):
    """数据批量打包"""
    from app.services.edge_preprocessor import get_edge_preprocessor

    preprocessor = get_edge_preprocessor()
    batches = preprocessor.batch_pack(data, batch_size=batch_size)
    return ApiResponse(data={
        "total_records": len(data),
        "batch_size": batch_size,
        "batch_count": len(batches),
        "batches": batches,
    })


# ============================================================
# 断线续传端点
# ============================================================

class OfflineEnqueueRequest(BaseModel):
    """离线消息入队请求"""
    topic: str = Field(..., description="MQTT主题")
    payload: dict = Field(..., description="消息内容")
    qos: int = Field(1, ge=0, le=2, description="QoS等级")
    priority: int = Field(1, ge=0, le=3, description="优先级（0=低 1=普通 2=高 3=紧急）")
    metadata: Optional[dict] = Field(None, description="附加元数据")


@router.post("/offline/enqueue")
async def enqueue_offline_message(req: OfflineEnqueueRequest,
    user: dict = Depends(get_current_user)):
    """
    离线消息入队

    将消息缓存到离线队列，连接恢复后自动补传。
    """
    from app.services.offline_relay import get_offline_relay, MessagePriority

    relay = get_offline_relay()
    priority = MessagePriority(req.priority)

    message_id = relay.enqueue(
        topic=req.topic,
        payload=req.payload,
        qos=req.qos,
        priority=priority,
        metadata=req.metadata,
    )

    if message_id:
        return ApiResponse(data={
            "message_id": message_id,
            "queued": not relay.is_connected,
            "is_connected": relay.is_connected,
        })
    else:
        return ApiResponse(data={
            "message_id": None,
            "queued": False,
            "reason": "消息重复或队列已满",
        })


@router.get("/offline/statistics")
async def get_offline_statistics(user: dict = Depends(get_current_user)):
    """获取断线续传统计"""
    from app.services.offline_relay import get_offline_relay

    relay = get_offline_relay()
    stats = relay.get_statistics()
    return ApiResponse(data=stats)


@router.post("/offline/acknowledge/{message_id}")
async def acknowledge_message(message_id: str,
    user: dict = Depends(get_current_user)):
    """确认消息已收到"""
    from app.services.offline_relay import get_offline_relay

    relay = get_offline_relay()
    relay.acknowledge(message_id)
    return ApiResponse(data={"message_id": message_id, "status": "acknowledged"})


@router.post("/offline/status")
async def set_connection_status(connected: bool = Query(..., description="连接状态")):
    """设置连接状态（用于模拟断线/恢复）"""
    from app.services.offline_relay import get_offline_relay

    relay = get_offline_relay()
    relay.set_connected(connected)
    return ApiResponse(data={
        "is_connected": relay.is_connected,
        "pending_count": relay.get_pending_count(),
    })


@router.delete("/offline/clear")
async def clear_offline_queue(user: dict = Depends(get_current_user)):
    """清空离线队列"""
    from app.services.offline_relay import get_offline_relay

    relay = get_offline_relay()
    cleared = relay.clear_all()
    return ApiResponse(data={"cleared": cleared})
