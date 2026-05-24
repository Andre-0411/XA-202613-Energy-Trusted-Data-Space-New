"""
元数据管理服务
元数据CRUD（遵循 GB/T 36073-2018）/ 血缘关系查询（图结构）/ 版本管理
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_asset import Metadata, DataAsset
from app.schemas.data_asset import MetadataCreate, MetadataResponse
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.exceptions import DataNotFoundError, DataAlreadyExistsError, DataValidationError

logger = logging.getLogger(__name__)

# GB/T 36073-2018 元数据核心字段
GB36073_REQUIRED_FIELDS = [
    "identifier",     # 唯一标识符
    "title",          # 数据集标题
    "creator",        # 创建者
    "subject",        # 主题
    "description",    # 描述
    "publisher",      # 发布者
    "date",           # 日期
    "type",           # 类型
    "format",         # 格式
]

# GB/T 36073-2018 可选字段
GB36073_OPTIONAL_FIELDS = [
    "contributor",    # 贡献者
    "source",         # 来源
    "language",       # 语言
    "relation",       # 关联
    "coverage",       # 覆盖范围
    "rights",         # 权限
    "spatial",        # 空间范围
    "temporal",       # 时间范围
    "accuracy",       # 精度
    "lineage",        # 血缘
]


async def list_metadata(
    db: AsyncSession,
    params: PaginationParams,
    asset_id: Optional[str] = None,
    standard: Optional[str] = None,
) -> PaginatedResponse:
    """查询元数据列表"""
    query = select(Metadata)
    if asset_id:
        query = query.where(Metadata.asset_id == uuid.UUID(asset_id))
    if standard:
        query = query.where(Metadata.standard == standard)

    result = await paginate_query(db, query, params, MetadataResponse)
    return result


async def get_metadata(
    db: AsyncSession,
    metadata_id: str,
) -> MetadataResponse:
    """获取元数据详情"""
    result = await db.execute(
        select(Metadata).where(Metadata.id == uuid.UUID(metadata_id))
    )
    meta = result.scalar_one_or_none()
    if not meta:
        raise DataNotFoundError("元数据未找到")
    return MetadataResponse.model_validate(meta)


async def create_metadata(
    db: AsyncSession,
    request: MetadataCreate,
    user_id: str,
) -> MetadataResponse:
    """
    创建元数据

    1. 校验关联资产存在
    2. 校验不重复创建
    3. 验证 GB/T 36073-2018 核心字段
    4. 创建元数据记录
    """
    # 1. 校验资产
    asset_result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(request.asset_id))
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("关联的数据资产未找到")

    # 2. 校验不重复（一个资产只有一条元数据）
    existing = await db.execute(
        select(Metadata).where(Metadata.asset_id == uuid.UUID(request.asset_id))
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError("该资产已有元数据，请使用更新接口")

    # 3. 验证核心字段（非强制，但记录警告）
    content = request.content
    missing_core = [f for f in GB36073_REQUIRED_FIELDS if f not in content]
    if missing_core:
        logger.warning(
            f"Metadata for asset {request.asset_id} missing GB/T 36073 core fields: {missing_core}"
        )

    # 4. 创建元数据
    meta = Metadata(
        asset_id=uuid.UUID(request.asset_id),
        standard=request.standard,
        content=request.content,
        lineage_graph=request.lineage_graph,
        version=1,
        created_by=uuid.UUID(user_id),
    )
    db.add(meta)
    await db.commit()
    await db.refresh(meta)

    logger.info(f"Metadata created: {meta.id} for asset {request.asset_id}")
    return MetadataResponse.model_validate(meta)


async def update_metadata(
    db: AsyncSession,
    metadata_id: str,
    request: MetadataCreate,
    user_id: str,
) -> MetadataResponse:
    """
    更新元数据（自动版本管理）

    1. 保存当前版本作为历史
    2. 递增版本号
    3. 更新内容
    """
    result = await db.execute(
        select(Metadata).where(Metadata.id == uuid.UUID(metadata_id))
    )
    meta = result.scalar_one_or_none()
    if not meta:
        raise DataNotFoundError("元数据未找到")

    # 保存旧版本信息到历史
    previous_version_id = meta.id
    old_version = meta.version

    # 更新元数据
    meta.content = request.content
    if request.lineage_graph is not None:
        meta.lineage_graph = request.lineage_graph
    if request.standard:
        meta.standard = request.standard
    meta.version = old_version + 1
    meta.previous_version_id = previous_version_id
    meta.created_by = uuid.UUID(user_id)

    await db.commit()
    await db.refresh(meta)

    logger.info(f"Metadata updated: {meta.id}, version {old_version} -> {meta.version}")
    return MetadataResponse.model_validate(meta)


async def get_lineage(
    db: AsyncSession,
    metadata_id: str,
) -> dict:
    """
    获取血缘关系可视化数据

    返回图结构的 nodes 和 edges，用于前端渲染血缘图

    节点类型:
    - source: 数据源
    - asset: 数据资产
    - process: 处理过程
    - output: 输出资产
    """
    result = await db.execute(
        select(Metadata).where(Metadata.id == uuid.UUID(metadata_id))
    )
    meta = result.scalar_one_or_none()
    if not meta:
        raise DataNotFoundError("元数据未找到")

    # 如果有血缘图数据，直接返回
    if meta.lineage_graph:
        lineage = meta.lineage_graph
        # 确保结构完整
        if "nodes" not in lineage:
            lineage["nodes"] = []
        if "edges" not in lineage:
            lineage["edges"] = []
        return lineage

    # 如果没有血缘图，基于关联资产构建基础血缘
    nodes = []
    edges = []

    # 查询关联资产
    asset_result = await db.execute(
        select(DataAsset).where(DataAsset.id == meta.asset_id)
    )
    asset = asset_result.scalar_one_or_none()

    if asset:
        # 添加当前资产节点
        nodes.append({
            "id": str(asset.id),
            "type": "asset",
            "label": asset.name,
            "category": asset.category,
            "classification_level": asset.classification_level,
        })

        # 如果有数据源，添加数据源节点和边
        if asset.source_id:
            source_result = await db.execute(
                select(DataAsset).where(DataAsset.id == asset.source_id)
            )
            source = source_result.scalar_one_or_none()
            if source:
                nodes.append({
                    "id": str(source.id),
                    "type": "source",
                    "label": source.name,
                    "category": source.category,
                })
                edges.append({
                    "source": str(source.id),
                    "target": str(asset.id),
                    "type": "derives_from",
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata_id": str(meta.id),
        "asset_id": str(meta.asset_id),
        "version": meta.version,
    }


async def get_versions(
    db: AsyncSession,
    metadata_id: str,
) -> dict:
    """
    获取元数据版本列表

    通过 previous_version_id 链回溯所有历史版本
    """
    result = await db.execute(
        select(Metadata).where(Metadata.id == uuid.UUID(metadata_id))
    )
    meta = result.scalar_one_or_none()
    if not meta:
        raise DataNotFoundError("元数据未找到")

    # 从当前版本回溯历史版本
    versions = []
    current = meta
    while current:
        versions.append({
            "id": str(current.id),
            "version": current.version,
            "created_by": str(current.created_by) if current.created_by else None,
            "created_at": str(current.created_at),
            "is_current": current.id == meta.id,
        })

        # 回溯到前一版本
        if current.previous_version_id:
            prev_result = await db.execute(
                select(Metadata).where(Metadata.id == current.previous_version_id)
            )
            current = prev_result.scalar_one_or_none()
        else:
            break

    return {
        "metadata_id": str(meta.id),
        "asset_id": str(meta.asset_id),
        "current_version": meta.version,
        "versions": versions,
        "total_versions": len(versions),
    }


async def get_metadata_by_asset(
    db: AsyncSession,
    asset_id: str,
) -> Optional[MetadataResponse]:
    """根据资产ID获取元数据"""
    result = await db.execute(
        select(Metadata).where(Metadata.asset_id == uuid.UUID(asset_id))
    )
    meta = result.scalar_one_or_none()
    if not meta:
        return None
    return MetadataResponse.model_validate(meta)


def validate_gb36073(content: dict) -> dict:
    """
    验证元数据是否符合 GB/T 36073-2018

    Returns:
        {
            "is_valid": bool,
            "missing_required": list[str],
            "present_optional": list[str],
            "compliance_score": float,
        }
    """
    missing_required = [f for f in GB36073_REQUIRED_FIELDS if f not in content]
    present_optional = [f for f in GB36073_OPTIONAL_FIELDS if f in content]

    total_fields = len(GB36073_REQUIRED_FIELDS) + len(GB36073_OPTIONAL_FIELDS)
    present_fields = (len(GB36073_REQUIRED_FIELDS) - len(missing_required)) + len(present_optional)
    compliance_score = present_fields / total_fields if total_fields > 0 else 0.0

    return {
        "is_valid": len(missing_required) == 0,
        "missing_required": missing_required,
        "present_optional": present_optional,
        "compliance_score": round(compliance_score, 4),
    }
