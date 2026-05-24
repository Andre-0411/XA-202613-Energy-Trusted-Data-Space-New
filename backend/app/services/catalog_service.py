"""
数据目录服务
目录浏览（分页+筛选）/ 搜索/全文检索 / 脱敏预览 / 申请使用 / 评价反馈
"""
import uuid
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_asset import DataAsset, Metadata
from app.models.tag import Tag, AssetTag
from app.models.access_log import AccessLog
from app.schemas.data_asset import DataAssetResponse
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)

# 敏感字段关键词（用于脱敏）
SENSITIVE_FIELD_PATTERNS = [
    re.compile(r"(name|姓名)", re.IGNORECASE),
    re.compile(r"(phone|mobile|tel|电话|手机)", re.IGNORECASE),
    re.compile(r"(id_card|身份证|sfz)", re.IGNORECASE),
    re.compile(r"(email|邮箱)", re.IGNORECASE),
    re.compile(r"(address|地址)", re.IGNORECASE),
    re.compile(r"(location|位置|坐标)", re.IGNORECASE),
    re.compile(r"(password|密码|secret)", re.IGNORECASE),
    re.compile(r"(bank|银行|account|账号)", re.IGNORECASE),
]

# 预览最大行数
PREVIEW_MAX_ROWS = 10


async def browse_catalog(
    db: AsyncSession,
    params: PaginationParams,
    category: Optional[str] = None,
    classification_level: Optional[int] = None,
    organization_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> PaginatedResponse:
    """
    浏览数据目录

    只返回已发布的资产，支持按大类/级别/组织/标签筛选
    """
    query = select(DataAsset).where(DataAsset.status == "published")

    # 按大类筛选
    if category:
        query = query.where(DataAsset.category == category)

    # 按敏感级别筛选
    if classification_level is not None:
        query = query.where(DataAsset.classification_level == classification_level)

    # 按组织筛选
    if organization_id:
        query = query.where(DataAsset.organization_id == uuid.UUID(organization_id))

    # 按标签筛选
    if tags:
        tag_subquery = (
            select(AssetTag.asset_id)
            .join(Tag, AssetTag.tag_id == Tag.id)
            .where(Tag.name.in_(tags))
        )
        query = query.where(DataAsset.id.in_(tag_subquery))

    result = await paginate_query(db, query, params, DataAssetResponse)
    return result


async def search_catalog(
    db: AsyncSession,
    params: PaginationParams,
    q: str = "",
    category: Optional[str] = None,
    classification_level: Optional[int] = None,
    min_level: Optional[int] = None,
    max_level: Optional[int] = None,
) -> PaginatedResponse:
    """
    搜索/全文检索

    支持名称/描述模糊搜索 + 大类/级别筛选
    """
    query = select(DataAsset).where(DataAsset.status == "published")

    # 全文搜索
    if q:
        search_term = f"%{q}%"
        query = query.where(
            or_(
                DataAsset.name.ilike(search_term),
                DataAsset.description.ilike(search_term),
            )
        )

    # 大类筛选
    if category:
        query = query.where(DataAsset.category == category)

    # 级别范围筛选
    if classification_level is not None:
        query = query.where(DataAsset.classification_level == classification_level)
    if min_level is not None:
        query = query.where(DataAsset.classification_level >= min_level)
    if max_level is not None:
        query = query.where(DataAsset.classification_level <= max_level)

    result = await paginate_query(db, query, params, DataAssetResponse)
    return result


async def get_search_suggestions(
    db: AsyncSession,
    keyword: str,
    limit: int = 10,
) -> list[dict]:
    """
    搜索建议（自动补全）

    基于已有资产名称和标签，返回匹配的搜索建议。
    按匹配度排序，返回关键词、所属分类、匹配数量。
    """
    search_term = f"%{keyword}%"

    # 从资产名称中获取建议
    name_query = (
        select(
            DataAsset.name.label("keyword"),
            DataAsset.category,
        )
        .where(
            DataAsset.status == "published",
            DataAsset.name.ilike(search_term),
        )
        .limit(limit)
    )
    name_result = await db.execute(name_query)
    name_rows = name_result.all()

    # 从标签中获取建议
    tag_query = (
        select(
            Tag.name.label("keyword"),
        )
        .where(Tag.name.ilike(search_term))
        .limit(limit)
    )
    tag_result = await db.execute(tag_query)
    tag_rows = tag_result.all()

    # 合并去重
    suggestions = []
    seen = set()

    for row in name_rows:
        if row.keyword not in seen:
            seen.add(row.keyword)
            suggestions.append({
                "keyword": row.keyword,
                "category": row.category,
                "count": 1,
            })

    for row in tag_rows:
        if row.keyword not in seen:
            seen.add(row.keyword)
            suggestions.append({
                "keyword": row.keyword,
                "category": None,
                "count": 0,
            })

    return suggestions[:limit]


async def preview_asset(
    db: AsyncSession,
    asset_id: str,
    user_id: str,
) -> dict:
    """
    脱敏预览

    1. 校验资产已发布
    2. 获取资产的元数据和 Schema
    3. 生成脱敏预览数据（最多10行，敏感字段掩码）
    4. 记录访问日志
    """
    # 1. 校验资产
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")
    if asset.status != "published":
        raise DataValidationError("资产未发布，无法预览")

    # 2. 获取元数据
    meta_result = await db.execute(
        select(Metadata).where(Metadata.asset_id == uuid.UUID(asset_id))
    )
    metadata = meta_result.scalar_one_or_none()

    # 3. 生成脱敏预览
    schema_def = asset.schema_def or {}
    masked_schema = _mask_sensitive_fields(schema_def)

    # 生成示例预览行
    preview_rows = _generate_preview_rows(masked_schema, asset.record_count)

    # 4. 记录访问日志
    access_log = AccessLog(
        user_id=uuid.UUID(user_id),
        asset_id=uuid.UUID(asset_id),
        action="preview",
        result="success",
        details={"method": "catalog_preview"},
    )
    db.add(access_log)
    await db.commit()

    return {
        "asset_id": str(asset.id),
        "name": asset.name,
        "category": asset.category,
        "classification_level": asset.classification_level,
        "description": asset.description,
        "schema": masked_schema,
        "preview_rows": preview_rows,
        "total_rows": asset.record_count,
        "storage_format": asset.storage_format,
        "standard": metadata.standard if metadata else None,
        "preview_limit": PREVIEW_MAX_ROWS,
    }


async def apply_for_access(
    db: AsyncSession,
    asset_id: str,
    user_id: str,
    purpose: str = "",
    duration_days: int = 30,
) -> dict:
    """
    申请使用

    1. 校验资产已发布
    2. 检查是否已有待审批的申请
    3. 创建访问申请记录
    4. 记录访问日志
    """
    # 1. 校验资产
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")
    if asset.status != "published":
        raise DataValidationError("资产未发布，无法申请")

    # 2. 检查重复申请
    existing = await db.execute(
        select(AccessLog).where(
            and_(
                AccessLog.user_id == uuid.UUID(user_id),
                AccessLog.asset_id == uuid.UUID(asset_id),
                AccessLog.action == "apply",
                AccessLog.result == "pending",
            )
        )
    )
    if existing.scalar_one_or_none():
        raise DataValidationError("您已有待审批的申请，请勿重复提交")

    # 3. 创建申请记录
    application_id = str(uuid.uuid4())
    access_log = AccessLog(
        user_id=uuid.UUID(user_id),
        asset_id=uuid.UUID(asset_id),
        action="apply",
        result="pending",
        details={
            "application_id": application_id,
            "purpose": purpose,
            "duration_days": duration_days,
            "asset_name": asset.name,
            "classification_level": asset.classification_level,
        },
    )
    db.add(access_log)
    await db.commit()

    logger.info(
        f"Access application: user={user_id}, asset={asset_id}, app={application_id}"
    )
    return {
        "application_id": application_id,
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "status": "pending",
        "purpose": purpose,
        "duration_days": duration_days,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }


async def submit_feedback(
    db: AsyncSession,
    asset_id: str,
    user_id: str,
    rating: int,
    comment: str = "",
) -> dict:
    """
    评价反馈

    1. 校验评分范围
    2. 记录反馈
    """
    # 校验评分
    if not 1 <= rating <= 5:
        raise DataValidationError("评分范围应为 1-5")

    # 校验资产
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    # 记录反馈
    feedback_id = str(uuid.uuid4())
    access_log = AccessLog(
        user_id=uuid.UUID(user_id),
        asset_id=uuid.UUID(asset_id),
        action="feedback",
        result="success",
        details={
            "feedback_id": feedback_id,
            "rating": rating,
            "comment": comment,
            "asset_name": asset.name,
        },
    )
    db.add(access_log)
    await db.commit()

    logger.info(f"Feedback submitted: asset={asset_id}, rating={rating}")
    return {
        "feedback_id": feedback_id,
        "asset_id": str(asset.id),
        "rating": rating,
        "comment": comment,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_asset_tags(
    db: AsyncSession,
    asset_id: str,
) -> list[dict]:
    """获取资产的标签列表"""
    result = await db.execute(
        select(Tag)
        .join(AssetTag, AssetTag.tag_id == Tag.id)
        .where(AssetTag.asset_id == uuid.UUID(asset_id))
    )
    tags = result.scalars().all()
    return [
        {"id": str(t.id), "name": t.name, "dimension": t.dimension}
        for t in tags
    ]


def _mask_sensitive_fields(schema_def: dict) -> dict:
    """
    对 Schema 中的敏感字段进行脱敏处理

    将敏感字段标记为 masked，前端根据此标记显示 ***
    """
    if not schema_def:
        return schema_def

    masked = dict(schema_def)
    fields = masked.get("fields", masked.get("columns", []))

    if isinstance(fields, list):
        new_fields = []
        for field in fields:
            if isinstance(field, dict):
                field_name = field.get("name", "")
                if _is_sensitive_field(field_name):
                    masked_field = dict(field)
                    masked_field["masked"] = True
                    masked_field["sample"] = "***"
                    new_fields.append(masked_field)
                else:
                    new_fields.append(field)
            else:
                new_fields.append(field)
        masked["fields"] = new_fields

    return masked


def _is_sensitive_field(field_name: str) -> bool:
    """判断字段名是否为敏感字段"""
    for pattern in SENSITIVE_FIELD_PATTERNS:
        if pattern.search(field_name):
            return True
    return False


def _generate_preview_rows(schema_def: dict, total_count: int) -> list[dict]:
    """
    生成预览示例行

    基于 Schema 定义生成带脱敏标记的示例数据
    """
    fields = schema_def.get("fields", schema_def.get("columns", []))
    if not fields:
        return []

    rows = []
    for i in range(min(PREVIEW_MAX_ROWS, max(total_count, 3))):
        row = {}
        for field in fields:
            if isinstance(field, dict):
                name = field.get("name", f"col_{i}")
                if field.get("masked"):
                    row[name] = "***"
                else:
                    field_type = field.get("type", "string")
                    row[name] = _sample_value(field_type, i)
            else:
                row[str(field)] = f"sample_{i}"
        rows.append(row)

    return rows


def _sample_value(field_type: str, index: int) -> str:
    """根据字段类型生成示例值"""
    type_samples = {
        "string": f"示例文本_{index}",
        "integer": str(index * 10),
        "float": f"{index * 1.5:.2f}",
        "number": str(index * 100),
        "boolean": "true" if index % 2 == 0 else "false",
        "datetime": f"2025-01-{(index % 28) + 1:02d}T00:00:00Z",
        "date": f"2025-01-{(index % 28) + 1:02d}",
        "timestamp": str(1700000000 + index * 3600),
    }
    return type_samples.get(field_type.lower(), f"sample_{index}")
