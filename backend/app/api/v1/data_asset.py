"""数据资产 API - /api/v1/data/assets"""
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.data_asset import DataAsset, DataAssetRating, DataSource
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.data_asset import (
    DataAssetCreate, DataAssetResponse,
    DataAssetRatingCreate, DataAssetRatingResponse, RatingStatisticsResponse,
)
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.utils.pagination import paginate_query

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ApiResponse[PaginatedResponse[DataAssetResponse]])
async def list_data_assets(pagination: PaginationParams = Depends(get_pagination_params), db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """资产列表"""
    query = select(DataAsset)
    result = await paginate_query(db, query, pagination, DataAssetResponse)
    return ApiResponse(data=result)


@router.post("", response_model=ApiResponse[DataAssetResponse], status_code=201)
async def create_data_asset(request: DataAssetCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """
    创建资产

    创建数据资产后自动触发原创性证明流程:
    1. 计算数据 SM3 哈希
    2. 创建区块链存证记录 (collect 节点)
    3. 记录首次上传时间戳
    """
    asset = DataAsset(
        name=request.name, source_id=uuid.UUID(request.source_id) if request.source_id else None,
        category=request.category, classification_level=request.classification_level,
        description=request.description, schema_def=request.schema_def,
        storage_format=request.storage_format, owner_id=uuid.UUID(request.owner_id),
        organization_id=uuid.UUID(request.organization_id),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    # 自动创建原创性证明存证
    try:
        from app.services.blockchain_evidence_service import submit_evidence
        from app.schemas.blockchain import EvidenceCreate
        from app.core.gmssl_adapter import gmssl_adapter

        # 计算数据资产哈希
        hash_input = f"{asset.name}:{asset.category}:{asset.classification_level}:{asset.storage_format}"
        if asset.schema_def:
            hash_input += f":{asset.schema_def}"
        data_hash = gmssl_adapter.sm3_hash(hash_input)

        evidence_request = EvidenceCreate(
            node_type="collect",
            resource_id=str(asset.id),
            resource_type="data_asset",
            data_hash=data_hash,
            evidence_data={
                "asset_name": asset.name,
                "category": asset.category,
                "classification_level": asset.classification_level,
                "storage_format": asset.storage_format,
                "owner_id": str(asset.owner_id),
                "organization_id": str(asset.organization_id),
                "first_upload_at": datetime.now(timezone.utc).isoformat(),
                "created_by": user.get("user_id"),
            },
        )
        await submit_evidence(db, evidence_request)
        logger.info(f"原创性证明创建成功: asset_id={asset.id}, data_hash={data_hash}")
    except Exception as e:
        # 存证失败不阻塞资产创建
        logger.warning(f"原创性证明创建失败（不阻塞资产创建）: asset_id={asset.id}, error={e}")

    # 自动触发数据处理流水线
    try:
        from app.services.data_pipeline_service import run_data_pipeline
        user_id = user.get("user_id", "")
        org_id = user.get("organization_id", str(asset.organization_id))
        pipeline_result = await run_data_pipeline(
            db=db, asset=asset, user_id=user_id, org_id=org_id,
        )
        logger.info(f"数据处理流水线完成: asset_id={asset.id}, status={pipeline_result.get('overall_status')}")
    except Exception as e:
        logger.warning(f"数据处理流水线失败（不阻塞资产创建）: asset_id={asset.id}, error={e}")

    return ApiResponse(data=DataAssetResponse.model_validate(asset))


@router.get("/{asset_id}", response_model=ApiResponse[DataAssetResponse])
async def get_data_asset(asset_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """资产详情"""
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)
    return ApiResponse(data=DataAssetResponse.model_validate(asset))


@router.put("/{asset_id}", response_model=ApiResponse[DataAssetResponse])
async def update_data_asset(asset_id: str, request: DataAssetCreate, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """更新资产（仅所有者或管理员可操作）"""
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)
    # C6修复：检查所有权或管理员权限
    user_role = user.get("role", "")
    user_id = str(user.get("user_id", ""))
    if str(asset.created_by) != user_id and user_role not in ("admin", "operator"):
        return ApiResponse(code=4003, message="无权修改此资产", data=None)
    for k, v in request.model_dump(exclude_unset=True).items():
        setattr(asset, k, v)
    await db.commit()
    await db.refresh(asset)
    return ApiResponse(data=DataAssetResponse.model_validate(asset))


@router.delete("/{asset_id}", response_model=ApiResponse)
async def delete_data_asset(asset_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """删除资产（仅所有者或管理员可操作）"""
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)
    # C6修复：检查所有权或管理员权限
    user_role = user.get("role", "")
    user_id = str(user.get("user_id", ""))
    if str(asset.created_by) != user_id and user_role not in ("admin", "operator"):
        return ApiResponse(code=4003, message="无权删除此资产", data=None)
    asset.status = "deleted"
    await db.commit()
    return ApiResponse(message="已删除")


@router.post("/{asset_id}/classify", response_model=ApiResponse)
async def classify_asset(asset_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """执行分类分级 - 使用增强分类引擎"""
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    # 使用增强分类引擎
    from app.services.classify_service import classify_and_grade
    from app.services.data_classifier import classify_by_field_types

    classification_result = await classify_and_grade(
        asset_name=asset.name,
        asset_description=asset.description,
        schema_def=asset.schema_def,
        category=asset.category,
    )

    # 基于字段类型的分级
    field_type_result = classify_by_field_types(asset.schema_def or {})

    # 更新资产分类信息
    asset.category = classification_result["category"]
    asset.classification_level = classification_result["classification_level"]
    asset.status = "classified"
    await db.commit()
    await db.refresh(asset)

    return ApiResponse(data={
        "asset_id": asset_id,
        "category": classification_result["category"],
        "classification_level": classification_result["classification_level"],
        "confidence": classification_result["confidence"],
        "reason": classification_result["reason"],
        "suggested_tags": classification_result.get("suggested_tags", []),
        "field_type_analysis": field_type_result,
        "review_status": "auto_classified",
    })


class ClassificationReviewRequest(BaseModel):
    """分类审核确认请求"""
    confirmed_category: str = Field(description="确认的大类: 发电/用电/调度/市场/设备状态/地理信息")
    confirmed_level: int = Field(ge=1, le=4, description="确认的安全级别: 1核心/2重要/3一般/4公开")
    review_comment: Optional[str] = Field(default=None, max_length=500, description="审核意见")


class ClassificationOverrideRequest(BaseModel):
    """分级覆盖请求"""
    new_category: str = Field(description="新的大类")
    new_level: int = Field(ge=1, le=4, description="新的安全级别")
    override_reason: str = Field(min_length=5, max_length=500, description="覆盖原因（必填，不少于5字）")


@router.post("/{asset_id}/classify/review", response_model=ApiResponse)
async def review_classification(
    asset_id: str,
    request: ClassificationReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    人工审核确认分类分级结果

    审核人确认自动分类结果的准确性，可以原样确认或修改分类和级别。
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    # 更新资产分类
    asset.category = request.confirmed_category
    asset.classification_level = request.confirmed_level
    asset.status = "classified"
    await db.commit()
    await db.refresh(asset)

    from app.services.data_classifier import confirm_classification
    review_result = await confirm_classification(
        asset_id=asset_id,
        confirmed_category=request.confirmed_category,
        confirmed_level=request.confirmed_level,
        reviewer_id=user.get("user_id", ""),
        review_comment=request.review_comment,
    )

    logger.info(f"分类审核确认: asset_id={asset_id}, user={user.get('user_id')}")
    return ApiResponse(data=review_result)


@router.post("/{asset_id}/classify/override", response_model=ApiResponse)
async def override_classification(
    asset_id: str,
    request: ClassificationOverrideRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    人工覆盖分级结果

    当自动分类不准确时，允许人工覆盖分类和安全级别。
    必须提供覆盖原因。
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    # 更新资产分类
    old_category = asset.category
    old_level = asset.classification_level
    asset.category = request.new_category
    asset.classification_level = request.new_level
    asset.status = "classified"
    await db.commit()
    await db.refresh(asset)

    from app.services.data_classifier import override_classification
    override_result = await override_classification(
        asset_id=asset_id,
        new_category=request.new_category,
        new_level=request.new_level,
        override_reason=request.override_reason,
        operator_id=user.get("user_id", ""),
    )

    override_result["old_category"] = old_category
    override_result["old_level"] = old_level

    logger.info(f"分级覆盖: asset_id={asset_id}, {old_category}/{old_level} -> {request.new_category}/{request.new_level}")
    return ApiResponse(data=override_result)


@router.post("/{asset_id}/publish", response_model=ApiResponse)
async def publish_asset(asset_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """发布至目录"""
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)
    asset.status = "published"
    asset.published_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse(message="已发布至目录")


@router.post("/{asset_id}/preprocess", response_model=ApiResponse)
async def preprocess_asset(asset_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """触发边缘预处理"""
    return ApiResponse(data={"asset_id": asset_id, "status": "preprocessing"})


# ==================== 脱敏数据预览端点 ====================

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
            masked[key] = value[0] + "*" * (len(value) - 2) + value[-1]
        else:
            masked[key] = value
    return masked


async def _generate_preview_records(
    asset: DataAsset,
    limit: int,
    db: AsyncSession,
) -> tuple[list[dict], str]:
    """
    获取数据资产的预览记录

    如果资产关联了数据源，从数据源查询真实数据并脱敏返回；
    否则返回空列表和提示信息。

    Args:
        asset: 数据资产对象
        limit: 返回记录上限
        db: 数据库会话

    Returns:
        (records, message): 记录列表和提示信息
    """
    # 检查资产是否关联了数据源
    if not asset.source_id:
        return [], "该资产未关联数据源，暂无预览数据"

    # 查询关联的数据源是否存在
    source_result = await db.execute(
        select(DataSource).where(DataSource.id == asset.source_id)
    )
    source = source_result.scalar_one_or_none()
    if not source:
        return [], "关联数据源不存在或已删除"

    # 检查数据源状态
    if source.status != "active":
        return [], f"数据源状态异常: {source.status}，无法获取预览数据"

    # 检查资产是否有记录
    if not asset.record_count or asset.record_count == 0:
        return [], "数据源暂无记录，请等待数据采集完成后重试"

    # 如果有关联的元数据，基于 schema_def 生成字段结构描述（不含模拟数据）
    schema_def = asset.schema_def or {}
    fields = schema_def.get("fields", schema_def.get("columns", []))
    if fields and isinstance(fields, list) and len(fields) > 0:
        # 返回 Schema 描述信息而非模拟数据
        schema_records = []
        for field in fields[:limit]:
            if isinstance(field, dict):
                schema_records.append({
                    "field_name": field.get("name", "unknown"),
                    "field_type": field.get("type", "unknown"),
                    "description": field.get("description", ""),
                    "required": field.get("required", False),
                })
        return schema_records, "数据源暂未对接实时数据查询，显示 Schema 字段定义"

    return [], "数据源已关联但暂未配置 Schema，无法生成预览"


@router.get("/{asset_id}/preview", response_model=ApiResponse)
async def preview_asset_data(
    asset_id: str,
    limit: int = Query(10, ge=1, le=10, description="预览条数（最多10条）"),
    format: str = Query("json", description="预览格式: json/csv/timeseries"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    脱敏数据预览

    返回数据资产的脱敏预览数据（最多10条），支持三种格式:
    - json: 标准JSON格式
    - csv: CSV表格格式
    - timeseries: 时间序列格式

    敏感字段（如身份证、手机号、邮箱等）会被脱敏处理。
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    records, preview_message = await _generate_preview_records(asset, limit, db)

    if format == "csv":
        # CSV 格式：返回表头和行数据
        if records:
            headers = list(records[0].keys())
            rows = [list(r.values()) for r in records]
            return ApiResponse(data={
                "asset_id": asset_id,
                "format": "csv",
                "headers": headers,
                "rows": rows,
                "total_available": asset.record_count or 0,
                "showing": len(records),
                "message": preview_message,
            })
        return ApiResponse(data={
            "asset_id": asset_id,
            "format": "csv",
            "headers": [],
            "rows": [],
            "total_available": 0,
            "showing": 0,
            "message": preview_message,
        })
    elif format == "timeseries":
        # 时间序列格式：提取时间戳和数值字段
        series = []
        for r in records:
            ts_point = {"timestamp": r.get("timestamp", "")}
            for k, v in r.items():
                if k != "timestamp" and k != "record_id" and isinstance(v, (int, float)):
                    ts_point[k] = v
            series.append(ts_point)
        return ApiResponse(data={
            "asset_id": asset_id,
            "format": "timeseries",
            "series": series,
            "total_available": asset.record_count or 0,
            "showing": len(series),
            "message": preview_message,
        })
    else:
        # JSON 格式（默认）
        return ApiResponse(data={
            "asset_id": asset_id,
            "format": "json",
            "records": records,
            "total_available": asset.record_count or 0,
            "showing": len(records),
            "masked_fields": _SENSITIVE_KEYWORDS,
            "message": preview_message,
        })


# ==================== 数据资产评价/反馈端点 ====================


@router.post("/{asset_id}/ratings", response_model=ApiResponse[DataAssetRatingResponse], status_code=201)
async def create_asset_rating(
    asset_id: str,
    request: DataAssetRatingCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    提交数据资产评价

    对指定数据资产进行评分（1-5分）和评论，支持添加评价标签。
    每个用户对同一资产只能评价一次（更新已有评价）。
    """
    # 验证资产存在
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    user_id = uuid.UUID(user.get("user_id", str(uuid.uuid4())))

    # 检查是否已评价（同一用户对同一资产）
    existing = await db.execute(
        select(DataAssetRating).where(
            DataAssetRating.asset_id == uuid.UUID(asset_id),
            DataAssetRating.user_id == user_id,
        )
    )
    existing_rating = existing.scalar_one_or_none()

    if existing_rating:
        # 更新已有评价
        existing_rating.rating = request.rating
        existing_rating.comment = request.comment
        existing_rating.tags = request.tags or []
        existing_rating.user_name = request.user_name or user.get("username", "匿名用户")
        await db.commit()
        await db.refresh(existing_rating)
        logger.info(f"评价已更新: asset_id={asset_id}, user_id={user_id}, rating={request.rating}")
        return ApiResponse(data=DataAssetRatingResponse.model_validate(existing_rating))

    # 创建新评价
    rating = DataAssetRating(
        asset_id=uuid.UUID(asset_id),
        user_id=user_id,
        user_name=request.user_name or user.get("username", "匿名用户"),
        rating=request.rating,
        comment=request.comment,
        tags=request.tags or [],
    )
    db.add(rating)
    await db.commit()
    await db.refresh(rating)

    logger.info(f"评价已创建: asset_id={asset_id}, user_id={user_id}, rating={request.rating}")
    return ApiResponse(data=DataAssetRatingResponse.model_validate(rating))


@router.get("/{asset_id}/ratings", response_model=ApiResponse[RatingStatisticsResponse])
async def get_asset_ratings(
    asset_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    获取数据资产的评价列表和统计

    返回评价列表、平均评分、评分分布等统计信息。
    """
    # 验证资产存在
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    # 统计查询
    stats_result = await db.execute(
        select(
            func.count(DataAssetRating.id).label("total"),
            func.coalesce(func.avg(DataAssetRating.rating), 0).label("avg_rating"),
        ).where(DataAssetRating.asset_id == uuid.UUID(asset_id))
    )
    stats_row = stats_result.one()
    total = stats_row.total
    avg_rating = float(stats_row.avg_rating) if stats_row.avg_rating else 0.0

    # 评分分布
    dist_result = await db.execute(
        select(
            DataAssetRating.rating,
            func.count(DataAssetRating.id).label("count"),
        ).where(
            DataAssetRating.asset_id == uuid.UUID(asset_id)
        ).group_by(DataAssetRating.rating)
    )
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for row in dist_result.all():
        rating_distribution[row.rating] = row.count

    # 分页查询最近评价
    offset = (page - 1) * page_size
    ratings_result = await db.execute(
        select(DataAssetRating).where(
            DataAssetRating.asset_id == uuid.UUID(asset_id)
        ).order_by(
            DataAssetRating.created_at.desc()
        ).offset(offset).limit(page_size)
    )
    recent = [
        DataAssetRatingResponse.model_validate(r)
        for r in ratings_result.scalars().all()
    ]

    return ApiResponse(data=RatingStatisticsResponse(
        asset_id=asset_id,
        total_ratings=total,
        avg_rating=round(avg_rating, 1),
        rating_distribution=rating_distribution,
        recent_ratings=recent,
    ))


@router.get("/{asset_id}/originality-proof", response_model=ApiResponse)
async def get_originality_proof(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    获取数据资产的原创性证明

    查询该资产的区块链存证记录，包括首次上传时间、
    数据哈希、交易哈希等信息。
    """
    from app.services.blockchain_evidence_service import get_evidence_chain

    # 验证资产存在
    result = await db.execute(select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id)))
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="资产未找到", data=None)

    try:
        evidence_chain = await get_evidence_chain(db, asset_id, "data_asset")
        return ApiResponse(data={
            "asset_id": asset_id,
            "asset_name": asset.name,
            "evidence_chain": [e.model_dump() for e in evidence_chain],
            "total_evidence_nodes": len(evidence_chain),
            "has_collect_evidence": any(e.node_type == "collect" for e in evidence_chain),
        })
    except Exception as e:
        logger.warning(f"查询原创性证明失败: {e}")
        return ApiResponse(data={
            "asset_id": asset_id,
            "asset_name": asset.name,
            "evidence_chain": [],
            "total_evidence_nodes": 0,
            "has_collect_evidence": False,
            "error": str(e),
        })
