"""
数据资产管理服务
资产CRUD + 分类分级执行 + 发布至目录 + 边缘预处理触发 + NFT关联管理 + 统计分析
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_asset import DataAsset, DataSource
from app.models.blockchain import NftAsset
from app.schemas.data_asset import DataAssetCreate, DataAssetResponse
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PaginationParams, paginate_query
from app.services.mqtt_client import mqtt_manager
from app.exceptions import DataNotFoundError, DataValidationError, DataAlreadyExistsError

logger = logging.getLogger(__name__)

# 数据资产有效状态
VALID_STATUSES = {"draft", "classified", "published", "archived", "deleted"}

# 数据资产有效大类
VALID_CATEGORIES = {"发电", "用电", "调度", "市场", "设备状态", "地理信息"}


async def list_data_assets(
    db: AsyncSession,
    params: PaginationParams,
    category: Optional[str] = None,
    classification_level: Optional[int] = None,
    status: Optional[str] = None,
    owner_id: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> PaginatedResponse:
    """查询数据资产列表（分页+筛选）"""
    query = select(DataAsset)
    if category:
        query = query.where(DataAsset.category == category)
    if classification_level is not None:
        query = query.where(DataAsset.classification_level == classification_level)
    if status:
        query = query.where(DataAsset.status == status)
    if owner_id:
        query = query.where(DataAsset.owner_id == uuid.UUID(owner_id))
    if organization_id:
        query = query.where(DataAsset.organization_id == uuid.UUID(organization_id))

    result = await paginate_query(db, query, params, DataAssetResponse)
    return result


async def get_data_asset(
    db: AsyncSession,
    asset_id: str,
) -> DataAssetResponse:
    """获取数据资产详情"""
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")
    return DataAssetResponse.model_validate(asset)


async def create_data_asset(
    db: AsyncSession,
    request: DataAssetCreate,
    user_id: str,
) -> DataAssetResponse:
    """
    创建数据资产

    1. 校验大类
    2. 校验数据源（如有）
    3. 创建资产记录
    """
    # 1. 校验大类
    if request.category not in VALID_CATEGORIES:
        raise DataValidationError(
            f"无效的资产大类: {request.category}，允许值: {VALID_CATEGORIES}"
        )

    # 2. 校验数据源
    if request.source_id:
        source_result = await db.execute(
            select(DataSource).where(DataSource.id == uuid.UUID(request.source_id))
        )
        if not source_result.scalar_one_or_none():
            raise DataNotFoundError("关联的数据源未找到")

    # 3. 创建资产
    asset = DataAsset(
        name=request.name,
        source_id=uuid.UUID(request.source_id) if request.source_id else None,
        category=request.category,
        classification_level=request.classification_level,
        description=request.description,
        schema_def=request.schema_def,
        storage_format=request.storage_format,
        owner_id=uuid.UUID(request.owner_id),
        organization_id=uuid.UUID(request.organization_id),
        status="draft",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    logger.info(f"Data asset created: {asset.id} ({asset.name})")
    return DataAssetResponse.model_validate(asset)


async def update_data_asset(
    db: AsyncSession,
    asset_id: str,
    request: DataAssetCreate,
) -> DataAssetResponse:
    """更新数据资产"""
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    # 已发布的资产不允许修改
    if asset.status == "published":
        raise DataValidationError("已发布的资产不允许修改，请先下架")

    if request.category not in VALID_CATEGORIES:
        raise DataValidationError(f"无效的资产大类: {request.category}")

    asset.name = request.name
    asset.category = request.category
    asset.classification_level = request.classification_level
    asset.description = request.description
    asset.schema_def = request.schema_def
    asset.storage_format = request.storage_format
    if request.source_id:
        asset.source_id = uuid.UUID(request.source_id)

    await db.commit()
    await db.refresh(asset)

    logger.info(f"Data asset updated: {asset.id}")
    return DataAssetResponse.model_validate(asset)


async def delete_data_asset(
    db: AsyncSession,
    asset_id: str,
) -> None:
    """删除数据资产（软删除）"""
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    asset.status = "deleted"
    await db.commit()
    logger.info(f"Data asset deleted: {asset.id}")


async def classify_asset(
    db: AsyncSession,
    asset_id: str,
) -> dict:
    """
    执行分类分级

    调用分类分级引擎，自动判断大类和敏感级别
    """
    from app.services.classify_service import classify_and_grade

    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    # 执行分类分级
    classification_result = await classify_and_grade(
        asset_name=asset.name,
        asset_description=asset.description,
        schema_def=asset.schema_def,
        category=asset.category,
    )

    # 更新资产
    asset.category = classification_result["category"]
    asset.classification_level = classification_result["classification_level"]
    asset.status = "classified"
    await db.commit()

    logger.info(
        f"Asset classified: {asset.id} -> {asset.category}/{asset.classification_level}"
    )
    return classification_result


async def publish_asset(
    db: AsyncSession,
    asset_id: str,
) -> DataAssetResponse:
    """
    发布资产至目录

    1. 校验资产已完成分类分级
    2. 设置发布时间
    3. 更新状态
    """
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    if asset.status not in ("classified", "draft"):
        raise DataValidationError("资产状态不允许发布，需先完成分类分级")

    asset.status = "published"
    asset.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(asset)

    logger.info(f"Asset published: {asset.id}")
    return DataAssetResponse.model_validate(asset)


async def unpublish_asset(
    db: AsyncSession,
    asset_id: str,
) -> DataAssetResponse:
    """下架资产"""
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    if asset.status != "published":
        raise DataValidationError("资产未发布，无法下架")

    asset.status = "classified"
    asset.published_at = None
    await db.commit()
    await db.refresh(asset)

    logger.info(f"Asset unpublished: {asset.id}")
    return DataAssetResponse.model_validate(asset)


async def trigger_preprocess(
    db: AsyncSession,
    asset_id: str,
) -> dict:
    """
    触发边缘预处理

    通过 MQTT 向边缘节点发送预处理指令
    """
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError("数据资产未找到")

    # 查询数据源的边缘预处理配置
    preprocess_config = {}
    if asset.source_id:
        source_result = await db.execute(
            select(DataSource).where(DataSource.id == asset.source_id)
        )
        source = source_result.scalar_one_or_none()
        if source and source.edge_preprocess:
            preprocess_config = source.edge_preprocess

    # 通过 MQTT 发布预处理指令
    task_id = str(uuid.uuid4())
    mqtt_manager.publish(
        f"energy/preprocess/{asset.id}",
        task_id,
    )

    logger.info(f"Preprocess triggered for asset: {asset.id}, task: {task_id}")
    return {
        "asset_id": str(asset.id),
        "task_id": task_id,
        "status": "preprocessing",
        "preprocess_config": preprocess_config,
    }


async def get_nft_info(
    db: AsyncSession,
    asset_id: str,
) -> Optional[dict]:
    """查询资产关联的 NFT 信息"""
    result = await db.execute(
        select(NftAsset).where(NftAsset.asset_id == uuid.UUID(asset_id))
    )
    nft = result.scalar_one_or_none()
    if not nft:
        return None
    return {
        "token_id": nft.token_id,
        "owner_did": nft.owner_did,
        "creator_did": nft.creator_did,
        "evidence_hash": nft.evidence_hash,
        "certificate_url": nft.certificate_url,
        "tx_hash": nft.tx_hash,
        "block_number": nft.block_number,
    }


async def get_asset_statistics(db: AsyncSession) -> dict:
    """
    获取数据资产统计

    Returns:
        包含资产总数、各类型数量、各状态数量的字典
    """
    # 资产总数（不含已删除）
    total = (await db.execute(
        select(func.count()).select_from(DataAsset).where(
            DataAsset.status != "deleted"
        )
    )).scalar() or 0

    # 各类型数量
    category_result = await db.execute(
        select(DataAsset.category, func.count())
        .where(DataAsset.status != "deleted")
        .group_by(DataAsset.category)
    )
    by_category = {row[0]: row[1] for row in category_result.all()}

    # 各状态数量
    status_result = await db.execute(
        select(DataAsset.status, func.count())
        .group_by(DataAsset.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    return {
        "total": total,
        "by_category": by_category,
        "by_status": by_status,
    }


async def get_asset_trend(db: AsyncSession, days: int = 30) -> list[dict]:
    """
    获取数据资产增长趋势

    Args:
        db: 异步数据库会话
        days: 查询天数，默认 30

    Returns:
        每日新增资产数列表，每项包含 date 和 count
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(DataAsset.created_at).label("date"),
            func.count().label("count"),
        )
        .where(DataAsset.created_at >= cutoff)
        .group_by(func.date(DataAsset.created_at))
        .order_by(func.date(DataAsset.created_at))
    )

    return [
        {"date": str(row.date), "count": row.count}
        for row in result.all()
    ]
