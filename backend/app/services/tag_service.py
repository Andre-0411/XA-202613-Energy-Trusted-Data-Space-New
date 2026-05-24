"""
标签服务
标签CRUD / 按维度聚合（行业/安全/业务/格式/来源/主题）
三维标签体系（业务维度/技术维度/质量维度）
搜索/筛选功能
"""
import uuid
import logging
from typing import Optional, Any

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, AssetTag
from app.models.data_asset import DataAsset
from app.exceptions import DataNotFoundError, DataAlreadyExistsError, DataValidationError

logger = logging.getLogger(__name__)

# 标签维度定义
VALID_DIMENSIONS = {
    "industry": "行业维度",
    "security": "安全维度",
    "business": "业务维度",
    "format": "格式维度",
    "source": "来源维度",
    "topic": "主题维度",
}

# 三维标签体系维度
THREE_DIMENSIONAL_DIMENSIONS = {
    "business_dimension": "业务维度",
    "technical_dimension": "技术维度",
    "quality_dimension": "质量维度",
}

# 合并所有有效维度
ALL_VALID_DIMENSIONS = {**VALID_DIMENSIONS, **THREE_DIMENSIONAL_DIMENSIONS}

# 维度预设标签
DIMENSION_PRESET_TAGS = {
    "industry": ["电力", "煤炭", "石油", "天然气", "新能源", "核能", "储能"],
    "security": ["核心", "重要", "敏感", "公开", "内部", "机密"],
    "business": ["发电", "用电", "调度", "市场", "设备状态", "地理信息"],
    "format": ["结构化", "半结构化", "非结构化", "时序", "图像", "文本"],
    "source": ["IoT采集", "人工录入", "外部接入", "计算生成", "历史迁移"],
    "topic": ["实时监控", "统计分析", "预测模型", "合规审计", "运营管理"],
}

# 三维标签体系预设标签
THREE_DIMENSIONAL_PRESETS = {
    "business_dimension": {
        "行业": ["电力", "煤炭", "石油", "天然气", "新能源", "核能", "储能", "交通", "建筑", "工业"],
        "场景": ["发电监控", "用电分析", "电网调度", "能源交易", "设备运维", "负荷预测", "故障诊断", "能效评估"],
        "用途": ["生产运营", "科研分析", "监管合规", "市场交易", "投资决策", "风险评估"],
    },
    "technical_dimension": {
        "格式": ["JSON", "CSV", "Parquet", "Avro", "Protobuf", "XML", "时序数据", "图像", "视频"],
        "协议": ["MQTT", "DLMS", "Modbus", "IEC61850", "OPC-UA", "HTTP", "WebSocket", "CoAP"],
        "频率": ["实时", "秒级", "分钟级", "小时级", "日级", "周级", "月级", "按需"],
    },
    "quality_dimension": {
        "完整性": ["完整", "部分缺失", "关键字段缺失", "时间断档", "采样不均"],
        "准确性": ["高精度", "标准精度", "低精度", "校准中", "未校准"],
        "时效性": ["实时", "准实时", "延迟<1h", "延迟<24h", "历史数据", "归档数据"],
    },
}


async def list_tags(
    db: AsyncSession,
    dimension: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> list[dict]:
    """
    查询标签列表

    Args:
        dimension: 按维度筛选
        parent_id: 按父标签筛选

    Returns:
        标签列表
    """
    query = select(Tag)
    if dimension:
        if dimension not in ALL_VALID_DIMENSIONS:
            raise DataValidationError(
                f"无效的标签维度: {dimension}，允许值: {list(ALL_VALID_DIMENSIONS.keys())}"
            )
        query = query.where(Tag.dimension == dimension)
    if parent_id:
        query = query.where(Tag.parent_id == uuid.UUID(parent_id))

    result = await db.execute(query.order_by(Tag.dimension, Tag.name))
    tags = result.scalars().all()

    # 查询每个标签关联的资产数量
    tag_counts = await _get_tag_asset_counts(db, [str(t.id) for t in tags])

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "dimension": t.dimension,
            "parent_id": str(t.parent_id) if t.parent_id else None,
            "asset_count": tag_counts.get(str(t.id), 0),
            "created_at": str(t.created_at),
        }
        for t in tags
    ]


async def create_tag(
    db: AsyncSession,
    name: str,
    dimension: str,
    parent_id: Optional[str] = None,
) -> dict:
    """
    创建标签

    1. 校验维度有效
    2. 校验同维度下名称不重复
    3. 校验父标签存在
    4. 创建标签
    """
    # 1. 校验维度
    if dimension not in ALL_VALID_DIMENSIONS:
        raise DataValidationError(
            f"无效的标签维度: {dimension}，允许值: {list(ALL_VALID_DIMENSIONS.keys())}"
        )

    # 2. 校验名称不重复
    existing = await db.execute(
        select(Tag).where(
            Tag.name == name,
            Tag.dimension == dimension,
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError(f"标签 '{name}' 在维度 '{dimension}' 下已存在")

    # 3. 校验父标签
    if parent_id:
        parent_result = await db.execute(
            select(Tag).where(Tag.id == uuid.UUID(parent_id))
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise DataNotFoundError("父标签未找到")
        if parent.dimension != dimension:
            raise DataValidationError("父标签与子标签维度必须一致")

    # 4. 创建标签
    tag = Tag(
        name=name,
        dimension=dimension,
        parent_id=uuid.UUID(parent_id) if parent_id else None,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    logger.info(f"Tag created: {tag.id} ({name}@{dimension})")
    return {
        "id": str(tag.id),
        "name": tag.name,
        "dimension": tag.dimension,
        "parent_id": str(tag.parent_id) if tag.parent_id else None,
        "created_at": str(tag.created_at),
    }


async def delete_tag(
    db: AsyncSession,
    tag_id: str,
) -> None:
    """删除标签（同时解除资产关联）"""
    result = await db.execute(
        select(Tag).where(Tag.id == uuid.UUID(tag_id))
    )
    tag = result.scalar_one_or_none()
    if not tag:
        raise DataNotFoundError("标签未找到")

    # 删除资产关联
    asset_tags = await db.execute(
        select(AssetTag).where(AssetTag.tag_id == uuid.UUID(tag_id))
    )
    for at in asset_tags.scalars().all():
        await db.delete(at)

    # 删除标签
    await db.delete(tag)
    await db.commit()

    logger.info(f"Tag deleted: {tag_id}")


async def get_tags_by_dimension(db: AsyncSession) -> dict:
    """
    按维度聚合标签

    返回每个维度下的标签列表，包括预设标签和自定义标签
    """
    result = await db.execute(select(Tag))
    tags = result.scalars().all()

    # 按维度分组
    grouped: dict[str, list[dict]] = {}
    for t in tags:
        dim = t.dimension
        if dim not in grouped:
            grouped[dim] = []
        grouped[dim].append({
            "id": str(t.id),
            "name": t.name,
            "parent_id": str(t.parent_id) if t.parent_id else None,
        })

    # 补充维度描述和预设标签
    result_data = {}
    for dim_key, dim_name in ALL_VALID_DIMENSIONS.items():
        existing_tags = grouped.get(dim_key, [])

        # 获取预设标签
        if dim_key in DIMENSION_PRESET_TAGS:
            preset_tags = DIMENSION_PRESET_TAGS[dim_key]
        elif dim_key in THREE_DIMENSIONAL_PRESETS:
            # 三维标签的预设是嵌套结构，展平为列表
            preset_tags = []
            for category, items in THREE_DIMENSIONAL_PRESETS[dim_key].items():
                preset_tags.extend(items)
        else:
            preset_tags = []

        # 找出尚未创建的预设标签
        existing_names = {t["name"] for t in existing_tags}
        missing_presets = [
            {"name": name, "is_preset": True}
            for name in preset_tags
            if name not in existing_names
        ]

        result_data[dim_key] = {
            "name": dim_name,
            "tags": existing_tags,
            "missing_presets": missing_presets,
            "total_count": len(existing_tags),
        }

    return result_data


async def assign_tag_to_asset(
    db: AsyncSession,
    asset_id: str,
    tag_id: str,
) -> dict:
    """为资产分配标签"""
    # 校验资产
    asset_result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    if not asset_result.scalar_one_or_none():
        raise DataNotFoundError("数据资产未找到")

    # 校验标签
    tag_result = await db.execute(
        select(Tag).where(Tag.id == uuid.UUID(tag_id))
    )
    tag = tag_result.scalar_one_or_none()
    if not tag:
        raise DataNotFoundError("标签未找到")

    # 检查是否已关联
    existing = await db.execute(
        select(AssetTag).where(
            AssetTag.asset_id == uuid.UUID(asset_id),
            AssetTag.tag_id == uuid.UUID(tag_id),
        )
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("标签已关联到该资产")

    # 创建关联
    asset_tag = AssetTag(
        asset_id=uuid.UUID(asset_id),
        tag_id=uuid.UUID(tag_id),
    )
    db.add(asset_tag)
    await db.commit()

    logger.info(f"Tag {tag.name} assigned to asset {asset_id}")
    return {
        "asset_id": asset_id,
        "tag_id": tag_id,
        "tag_name": tag.name,
        "dimension": tag.dimension,
    }


async def remove_tag_from_asset(
    db: AsyncSession,
    asset_id: str,
    tag_id: str,
) -> None:
    """从资产移除标签"""
    result = await db.execute(
        select(AssetTag).where(
            AssetTag.asset_id == uuid.UUID(asset_id),
            AssetTag.tag_id == uuid.UUID(tag_id),
        )
    )
    asset_tag = result.scalar_one_or_none()
    if not asset_tag:
        raise DataNotFoundError("资产标签关联未找到")

    await db.delete(asset_tag)
    await db.commit()

    logger.info(f"Tag {tag_id} removed from asset {asset_id}")


async def _get_tag_asset_counts(
    db: AsyncSession,
    tag_ids: list[str],
) -> dict[str, int]:
    """获取标签关联的资产数量"""
    if not tag_ids:
        return {}

    counts = {}
    for tag_id in tag_ids:
        result = await db.execute(
            select(func.count(AssetTag.asset_id)).where(
                AssetTag.tag_id == uuid.UUID(tag_id)
            )
        )
        counts[tag_id] = result.scalar() or 0

    return counts


# ============================================================
# 三维标签体系相关函数
# ============================================================

async def get_three_dimensional_tags(db: AsyncSession) -> dict:
    """
    获取三维标签体系结构

    返回业务维度/技术维度/质量维度的层级结构，包含预设标签和已创建标签。
    """
    result = await db.execute(select(Tag))
    all_tags = result.scalars().all()

    # 按维度分组
    tags_by_dimension: dict[str, list[dict]] = {}
    for t in all_tags:
        dim = t.dimension
        if dim not in tags_by_dimension:
            tags_by_dimension[dim] = []
        tags_by_dimension[dim].append({
            "id": str(t.id),
            "name": t.name,
            "parent_id": str(t.parent_id) if t.parent_id else None,
            "created_at": str(t.created_at),
        })

    # 构建三维标签结构
    three_d_tags = {}
    for dim_key, dim_name in THREE_DIMENSIONAL_DIMENSIONS.items():
        presets = THREE_DIMENSIONAL_PRESETS.get(dim_key, {})
        existing = tags_by_dimension.get(dim_key, [])
        existing_names = {t["name"] for t in existing}

        # 构建分类结构
        categories = []
        for category_name, preset_items in presets.items():
            items = []
            for item_name in preset_items:
                # 检查是否已创建
                existing_tag = next(
                    (t for t in existing if t["name"] == item_name), None
                )
                items.append({
                    "name": item_name,
                    "created": existing_tag is not None,
                    "tag_id": existing_tag["id"] if existing_tag else None,
                })

            categories.append({
                "category": category_name,
                "items": items,
                "total": len(items),
                "created_count": sum(1 for i in items if i["created"]),
            })

        three_d_tags[dim_key] = {
            "dimension_name": dim_name,
            "categories": categories,
            "total_tags": len(existing),
            "total_presets": sum(len(items) for items in presets.values()),
        }

    return three_d_tags


async def search_tags(
    db: AsyncSession,
    keyword: Optional[str] = None,
    dimensions: Optional[list[str]] = None,
    asset_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    搜索/筛选标签

    支持按关键词、维度、资产ID进行筛选，返回分页结果。

    Args:
        keyword: 搜索关键词（模糊匹配标签名称）
        dimensions: 维度筛选列表
        asset_id: 资产ID（返回该资产关联的标签）
        page: 页码
        page_size: 每页大小

    Returns:
        分页标签结果
    """
    query = select(Tag)

    # 关键词筛选
    if keyword:
        query = query.where(Tag.name.ilike(f"%{keyword}%"))

    # 维度筛选
    if dimensions:
        valid_dims = [d for d in dimensions if d in ALL_VALID_DIMENSIONS]
        if valid_dims:
            query = query.where(Tag.dimension.in_(valid_dims))

    # 资产关联筛选
    if asset_id:
        asset_tag_subquery = (
            select(AssetTag.tag_id)
            .where(AssetTag.asset_id == uuid.UUID(asset_id))
            .scalar_subquery()
        )
        query = query.where(Tag.id.in_(asset_tag_subquery))

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    offset = (page - 1) * page_size
    query = query.order_by(Tag.dimension, Tag.name).offset(offset).limit(page_size)
    result = await db.execute(query)
    tags = result.scalars().all()

    # 查询资产数量
    tag_counts = await _get_tag_asset_counts(db, [str(t.id) for t in tags])

    return {
        "tags": [
            {
                "id": str(t.id),
                "name": t.name,
                "dimension": t.dimension,
                "dimension_name": ALL_VALID_DIMENSIONS.get(t.dimension, t.dimension),
                "parent_id": str(t.parent_id) if t.parent_id else None,
                "asset_count": tag_counts.get(str(t.id), 0),
                "created_at": str(t.created_at),
            }
            for t in tags
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
    }


async def get_assets_by_tags(
    db: AsyncSession,
    tag_ids: list[str],
    match_mode: str = "any",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    按标签筛选资产

    支持两种匹配模式：
    - any: 匹配任意一个标签（OR）
    - all: 匹配所有标签（AND）

    Args:
        tag_ids: 标签ID列表
        match_mode: 匹配模式（any/all）
        page: 页码
        page_size: 每页大小

    Returns:
        分页资产结果
    """
    if not tag_ids:
        return {"assets": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    tag_uuids = [uuid.UUID(tid) for tid in tag_ids]

    if match_mode == "all":
        # AND 模式：资产必须关联所有指定标签
        asset_ids_subquery = (
            select(AssetTag.asset_id)
            .where(AssetTag.tag_id.in_(tag_uuids))
            .group_by(AssetTag.asset_id)
            .having(func.count(func.distinct(AssetTag.tag_id)) == len(tag_uuids))
            .scalar_subquery()
        )
    else:
        # OR 模式：资产关联任意一个标签即可
        asset_ids_subquery = (
            select(AssetTag.asset_id)
            .where(AssetTag.tag_id.in_(tag_uuids))
            .distinct()
            .scalar_subquery()
        )

    # 查询资产
    count_query = select(func.count()).where(DataAsset.id.in_(asset_ids_subquery))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    assets_query = (
        select(DataAsset)
        .where(DataAsset.id.in_(asset_ids_subquery))
        .order_by(DataAsset.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    assets_result = await db.execute(assets_query)
    assets = assets_result.scalars().all()

    return {
        "assets": [
            {
                "id": str(a.id),
                "name": a.name,
                "description": a.description,
                "data_type": a.data_type,
                "created_at": str(a.created_at),
            }
            for a in assets
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        "match_mode": match_mode,
        "tag_ids": tag_ids,
    }


async def get_tag_statistics(db: AsyncSession) -> dict:
    """
    获取标签统计信息

    返回各维度标签数量、热门标签、标签使用趋势等。
    """
    # 各维度标签数量
    dim_counts_query = (
        select(Tag.dimension, func.count(Tag.id))
        .group_by(Tag.dimension)
    )
    dim_result = await db.execute(dim_counts_query)
    dimension_counts = {row[0]: row[1] for row in dim_result.all()}

    # 热门标签（关联资产最多的前10个）
    hot_tags_query = (
        select(
            Tag.id,
            Tag.name,
            Tag.dimension,
            func.count(AssetTag.asset_id).label("asset_count"),
        )
        .join(AssetTag, Tag.id == AssetTag.tag_id, isouter=True)
        .group_by(Tag.id, Tag.name, Tag.dimension)
        .order_by(func.count(AssetTag.asset_id).desc())
        .limit(10)
    )
    hot_result = await db.execute(hot_tags_query)
    hot_tags = [
        {
            "id": str(row[0]),
            "name": row[1],
            "dimension": row[2],
            "asset_count": row[3],
        }
        for row in hot_result.all()
    ]

    # 总标签数
    total_query = select(func.count(Tag.id))
    total_result = await db.execute(total_query)
    total_tags = total_result.scalar() or 0

    # 已使用标签数（至少关联一个资产）
    used_query = (
        select(func.count(func.distinct(AssetTag.tag_id)))
    )
    used_result = await db.execute(used_query)
    used_tags = used_result.scalar() or 0

    return {
        "total_tags": total_tags,
        "used_tags": used_tags,
        "unused_tags": total_tags - used_tags,
        "dimension_counts": dimension_counts,
        "hot_tags": hot_tags,
        "three_dimensional_dimensions": list(THREE_DIMENSIONAL_DIMENSIONS.values()),
    }


async def batch_assign_tags(
    db: AsyncSession,
    asset_id: str,
    tag_ids: list[str],
) -> dict:
    """
    批量为资产分配标签

    Args:
        asset_id: 资产ID
        tag_ids: 标签ID列表

    Returns:
        分配结果
    """
    # 校验资产
    asset_result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    if not asset_result.scalar_one_or_none():
        raise DataNotFoundError("数据资产未找到")

    assigned = []
    skipped = []
    errors = []

    for tag_id in tag_ids:
        try:
            # 校验标签
            tag_result = await db.execute(
                select(Tag).where(Tag.id == uuid.UUID(tag_id))
            )
            tag = tag_result.scalar_one_or_none()
            if not tag:
                errors.append({"tag_id": tag_id, "error": "标签未找到"})
                continue

            # 检查是否已关联
            existing = await db.execute(
                select(AssetTag).where(
                    AssetTag.asset_id == uuid.UUID(asset_id),
                    AssetTag.tag_id == uuid.UUID(tag_id),
                )
            )
            if existing.scalar_one_or_none():
                skipped.append({"tag_id": tag_id, "tag_name": tag.name})
                continue

            # 创建关联
            asset_tag = AssetTag(
                asset_id=uuid.UUID(asset_id),
                tag_id=uuid.UUID(tag_id),
            )
            db.add(asset_tag)
            assigned.append({"tag_id": tag_id, "tag_name": tag.name})

        except Exception as e:
            errors.append({"tag_id": tag_id, "error": str(e)})

    await db.commit()

    logger.info(
        f"Batch tag assignment for asset {asset_id}: "
        f"assigned={len(assigned)}, skipped={len(skipped)}, errors={len(errors)}"
    )

    return {
        "asset_id": asset_id,
        "assigned": assigned,
        "skipped": skipped,
        "errors": errors,
        "summary": {
            "total_requested": len(tag_ids),
            "assigned_count": len(assigned),
            "skipped_count": len(skipped),
            "error_count": len(errors),
        },
    }