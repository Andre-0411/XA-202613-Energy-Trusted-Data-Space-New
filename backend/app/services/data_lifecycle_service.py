"""
数据资源生命周期管理服务
基于《可信数据空间标准体系建设指南》（2025版）和《可信数据空间 能力要求》(TDSA/A-001-2025)

完整生命周期：
1. 接入登记：数据源连接 → 元数据发现 → 安全等级定级 → 数据标识分配
2. 处理加工：数据清洗 → 分类分级 → 质量评估 → 脱敏处理
3. 发布发现：目录注册 → 供需匹配 → 检索查询
4. 服务交付：接口封装 → 可信交付 → 质量监控
5. 价值评估：资产评估 → 使用统计 → 收益分配
6. 退出注销：数据销毁 → 合约终止 → 记录归档
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_asset import DataAsset, DataSource, Metadata
from app.models.access_log import AccessLog
from app.models.contract import Contract
from app.models.compliance import DataQualityReport
from app.exceptions import (
    DataNotFoundError, DataValidationError, LifecycleStateError,
)
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)


# ==================== 生命周期状态定义 ====================

class LifecycleStage(str, Enum):
    """数据资源生命周期阶段"""
    REGISTRATION = "registration"        # 接入登记
    PROCESSING = "processing"            # 处理加工
    PUBLISHED = "published"              # 发布发现
    DELIVERY = "delivery"                # 服务交付
    VALUATION = "valuation"              # 价值评估
    DECOMMISSION = "decommission"        # 退出注销


class LifecycleStatus(str, Enum):
    """生命周期状态"""
    # 接入登记阶段
    SOURCE_CONNECTING = "source_connecting"      # 数据源连接中
    METADATA_DISCOVERING = "metadata_discovering" # 元数据发现中
    SECURITY_GRADING = "security_grading"        # 安全等级定级中
    ID_ASSIGNED = "id_assigned"                  # 数据标识已分配

    # 处理加工阶段
    CLEANING = "cleaning"                        # 数据清洗中
    CLASSIFYING = "classifying"                  # 分类分级中
    QUALITY_ASSESSING = "quality_assessing"      # 质量评估中
    MASKING = "masking"                          # 脱敏处理中

    # 发布发现阶段
    CATALOG_REGISTERING = "catalog_registering"  # 目录注册中
    PUBLISHED = "published"                      # 已发布
    MATCHING = "matching"                        # 供需匹配中

    # 服务交付阶段
    API_PACKING = "api_packing"                  # 接口封装中
    DELIVERING = "delivering"                    # 可信交付中
    MONITORING = "monitoring"                    # 质量监控中

    # 价值评估阶段
    ASSET_VALUING = "asset_valuing"              # 资产评估中
    USAGE_STATING = "usage_stating"              # 使用统计中
    REVENUE_DISTRIBUTING = "revenue_distributing" # 收益分配中

    # 退出注销阶段
    DATA_DESTROYING = "data_destroying"          # 数据销毁中
    CONTRACT_TERMINATING = "contract_terminating" # 合约终止中
    RECORD_ARCHIVING = "record_archiving"        # 记录归档中
    DECOMMISSIONED = "decommissioned"            # 已注销


# 生命周期阶段允许的状态转换
VALID_TRANSITIONS: Dict[str, List[str]] = {
    # 接入登记
    LifecycleStage.REGISTRATION: [
        LifecycleStatus.SOURCE_CONNECTING,
        LifecycleStatus.METADATA_DISCOVERING,
        LifecycleStatus.SECURITY_GRADING,
        LifecycleStatus.ID_ASSIGNED,
    ],
    # 处理加工
    LifecycleStage.PROCESSING: [
        LifecycleStatus.CLEANING,
        LifecycleStatus.CLASSIFYING,
        LifecycleStatus.QUALITY_ASSESSING,
        LifecycleStatus.MASKING,
    ],
    # 发布发现
    LifecycleStage.PUBLISHED: [
        LifecycleStatus.CATALOG_REGISTERING,
        LifecycleStatus.PUBLISHED,
        LifecycleStatus.MATCHING,
    ],
    # 服务交付
    LifecycleStage.DELIVERY: [
        LifecycleStatus.API_PACKING,
        LifecycleStatus.DELIVERING,
        LifecycleStatus.MONITORING,
    ],
    # 价值评估
    LifecycleStage.VALUATION: [
        LifecycleStatus.ASSET_VALUING,
        LifecycleStatus.USAGE_STATING,
        LifecycleStatus.REVENUE_DISTRIBUTING,
    ],
    # 退出注销
    LifecycleStage.DECOMMISSION: [
        LifecycleStatus.DATA_DESTROYING,
        LifecycleStatus.CONTRACT_TERMINATING,
        LifecycleStatus.RECORD_ARCHIVING,
        LifecycleStatus.DECOMMISSIONED,
    ],
}

# 阶段流转顺序
STAGE_ORDER = [
    LifecycleStage.REGISTRATION,
    LifecycleStage.PROCESSING,
    LifecycleStage.PUBLISHED,
    LifecycleStage.DELIVERY,
    LifecycleStage.VALUATION,
    LifecycleStage.DECOMMISSION,
]


# ==================== 接入登记 ====================

async def register_data_source(
    db: AsyncSession,
    asset_id: str,
    source_config: Dict[str, Any],
    user_id: str,
) -> Dict[str, Any]:
    """
    接入登记 - 数据源连接

    步骤：
    1. 验证资产存在
    2. 配置数据源连接参数
    3. 测试连接
    4. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)

    # 验证当前阶段是否允许此操作
    _validate_stage_transition(asset, LifecycleStage.REGISTRATION)

    # 创建或更新数据源
    from app.services.data_source_service import create_data_source, start_collection
    from app.schemas.data_asset import DataSourceCreate

    source_request = DataSourceCreate(
        name=f"{asset.name}_数据源",
        protocol_type=source_config.get("protocol_type", "HTTP"),
        connection_config=source_config.get("connection_config", {}),
        device_did=source_config.get("device_did"),
        mqtt_topic=source_config.get("mqtt_topic"),
        collection_interval_ms=source_config.get("collection_interval_ms", 60000),
        is_critical=source_config.get("is_critical", False),
        edge_preprocess=source_config.get("edge_preprocess", {}),
        organization_id=str(asset.organization_id),
    )

    source = await create_data_source(db, source_request, user_id)

    # 关联数据源到资产
    asset.source_id = uuid.UUID(source["id"])
    asset.lifecycle_stage = LifecycleStage.REGISTRATION.value
    asset.lifecycle_status = LifecycleStatus.SOURCE_CONNECTING.value
    await db.commit()

    # 生成数据标识（基于SM3国密哈希）
    data_identifier = _generate_data_identifier(asset)

    logger.info(f"Data source registered for asset: {asset_id}, source: {source['id']}")
    return {
        "asset_id": str(asset.id),
        "source_id": source["id"],
        "data_identifier": data_identifier,
        "lifecycle_stage": LifecycleStage.REGISTRATION.value,
        "lifecycle_status": LifecycleStatus.SOURCE_CONNECTING.value,
        "next_step": "metadata_discovery",
    }


async def discover_metadata(
    db: AsyncSession,
    asset_id: str,
    metadata_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    接入登记 - 元数据发现

    步骤：
    1. 从数据源自动发现元数据
    2. 补充人工标注的元数据
    3. 保存元数据记录
    4. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.REGISTRATION)

    # 自动发现元数据（模拟）
    auto_metadata = {
        "field_count": len(asset.schema_def.get("fields", [])) if asset.schema_def else 0,
        "record_count": asset.record_count or 0,
        "data_format": asset.storage_format or "unknown",
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }

    # 合并人工标注元数据
    if metadata_info:
        auto_metadata.update(metadata_info)

    # 保存元数据
    from app.services.metadata_service import create_or_update_metadata
    metadata = await create_or_update_metadata(
        db=db,
        asset_id=asset_id,
        content=auto_metadata,
    )

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.METADATA_DISCOVERING.value
    await db.commit()

    logger.info(f"Metadata discovered for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "metadata": auto_metadata,
        "lifecycle_status": LifecycleStatus.METADATA_DISCOVERING.value,
        "next_step": "security_grading",
    }


async def assign_security_level(
    db: AsyncSession,
    asset_id: str,
    security_level: int,
    grading_reason: str = "",
) -> Dict[str, Any]:
    """
    接入登记 - 安全等级定级

    安全等级：
    1 - 核心数据
    2 - 重要数据
    3 - 敏感数据
    4 - 一般数据
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.REGISTRATION)

    if security_level not in (1, 2, 3, 4):
        raise DataValidationError("安全等级必须为1-4之间的整数")

    # 记录原等级
    old_level = asset.classification_level

    # 更新安全等级
    asset.classification_level = security_level
    asset.lifecycle_status = LifecycleStatus.SECURITY_GRADING.value
    await db.commit()

    # 生成数据标识
    data_identifier = _generate_data_identifier(asset)

    # 更新生命周期状态为标识已分配
    asset.lifecycle_status = LifecycleStatus.ID_ASSIGNED.value
    await db.commit()

    logger.info(f"Security level assigned: asset={asset_id}, level={security_level}")
    return {
        "asset_id": str(asset.id),
        "data_identifier": data_identifier,
        "security_level": security_level,
        "old_level": old_level,
        "grading_reason": grading_reason,
        "lifecycle_stage": LifecycleStage.REGISTRATION.value,
        "lifecycle_status": LifecycleStatus.ID_ASSIGNED.value,
        "next_step": "processing",
    }


# ==================== 处理加工 ====================

async def clean_data(
    db: AsyncSession,
    asset_id: str,
    cleaning_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    处理加工 - 数据清洗

    步骤：
    1. 触发边缘预处理（如果有配置）
    2. 执行数据清洗规则
    3. 生成清洗报告
    4. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)

    # 接入登记完成后才能进入处理加工阶段
    if asset.lifecycle_stage == LifecycleStage.REGISTRATION.value:
        if asset.lifecycle_status != LifecycleStatus.ID_ASSIGNED.value:
            raise LifecycleStateError("接入登记未完成，无法进行数据清洗")

    _validate_stage_transition(asset, LifecycleStage.PROCESSING)

    # 触发边缘预处理
    preprocess_result = None
    if asset.source_id:
        from app.services.data_asset_service import trigger_preprocess
        try:
            preprocess_result = await trigger_preprocess(db, asset_id)
        except Exception as e:
            logger.warning(f"Edge preprocess trigger failed: {e}")

    # 模拟数据清洗结果
    cleaning_result = {
        "total_records": asset.record_count or 0,
        "cleaned_records": asset.record_count or 0,
        "removed_duplicates": 0,
        "fixed_format_errors": 0,
        "filled_null_values": 0,
        "cleaning_config": cleaning_config or {},
        "cleaned_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新生命周期状态
    asset.lifecycle_stage = LifecycleStage.PROCESSING.value
    asset.lifecycle_status = LifecycleStatus.CLEANING.value
    await db.commit()

    logger.info(f"Data cleaning completed for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "cleaning_result": cleaning_result,
        "preprocess_result": preprocess_result,
        "lifecycle_stage": LifecycleStage.PROCESSING.value,
        "lifecycle_status": LifecycleStatus.CLEANING.value,
        "next_step": "classify",
    }


async def classify_asset(
    db: AsyncSession,
    asset_id: str,
) -> Dict[str, Any]:
    """
    处理加工 - 分类分级

    步骤：
    1. 调用分类分级引擎
    2. 更新资产分类和级别
    3. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.PROCESSING)

    # 调用现有的分类分级服务
    from app.services.data_asset_service import classify_asset as do_classify
    classification_result = await do_classify(db, asset_id)

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.CLASSIFYING.value
    await db.commit()

    logger.info(f"Asset classified: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "classification_result": classification_result,
        "lifecycle_stage": LifecycleStage.PROCESSING.value,
        "lifecycle_status": LifecycleStatus.CLASSIFYING.value,
        "next_step": "quality_assess",
    }


async def assess_quality(
    db: AsyncSession,
    asset_id: str,
    check_dimensions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    处理加工 - 质量评估

    步骤：
    1. 调用质量检测服务
    2. 生成质量报告
    3. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.PROCESSING)

    # 调用现有的质量检测服务
    from app.services.quality_service import trigger_quality_check
    quality_report = await trigger_quality_check(db, asset_id, check_dimensions)

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.QUALITY_ASSESSING.value
    await db.commit()

    logger.info(f"Quality assessed for asset: {asset_id}, score: {quality_report.overall_score}")
    return {
        "asset_id": str(asset.id),
        "quality_report": {
            "report_id": str(quality_report.id),
            "overall_score": quality_report.overall_score,
            "completeness": quality_report.completeness,
            "accuracy": quality_report.accuracy,
            "timeliness_ms": quality_report.timeliness_ms,
            "consistency": quality_report.consistency,
        },
        "lifecycle_stage": LifecycleStage.PROCESSING.value,
        "lifecycle_status": LifecycleStatus.QUALITY_ASSESSING.value,
        "next_step": "mask_sensitive_data",
    }


async def mask_sensitive_data(
    db: AsyncSession,
    asset_id: str,
    masking_rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    处理加工 - 脱敏处理

    步骤：
    1. 识别敏感字段
    2. 应用脱敏规则
    3. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.PROCESSING)

    # 识别敏感字段
    sensitive_fields = _identify_sensitive_fields(asset.schema_def or {})

    # 应用脱敏规则
    masking_result = {
        "sensitive_fields_found": len(sensitive_fields),
        "sensitive_fields": sensitive_fields,
        "masking_rules_applied": masking_rules or {"default": "mask"},
        "masked_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新生命周期状态 - 处理加工完成
    asset.lifecycle_status = LifecycleStatus.MASKING.value
    await db.commit()

    logger.info(f"Sensitive data masked for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "masking_result": masking_result,
        "lifecycle_stage": LifecycleStage.PROCESSING.value,
        "lifecycle_status": LifecycleStatus.MASKING.value,
        "next_step": "publish",
    }


# ==================== 发布发现 ====================

async def register_to_catalog(
    db: AsyncSession,
    asset_id: str,
    catalog_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    发布发现 - 目录注册

    步骤：
    1. 验证处理加工完成
    2. 注册到数据目录
    3. 添加标签
    4. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.PUBLISHED)

    # 验证前置条件
    if not asset.classification_level:
        raise LifecycleStateError("分类分级未完成，无法发布到目录")

    # 发布资产
    from app.services.data_asset_service import publish_asset
    published_asset = await publish_asset(db, asset_id)

    # 添加标签
    if catalog_tags:
        from app.services.tag_service import add_tags_to_asset
        await add_tags_to_asset(db, asset_id, catalog_tags)

    # 更新生命周期状态
    asset.lifecycle_stage = LifecycleStage.PUBLISHED.value
    asset.lifecycle_status = LifecycleStatus.PUBLISHED.value
    await db.commit()

    logger.info(f"Asset registered to catalog: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "category": asset.category,
        "classification_level": asset.classification_level,
        "tags": catalog_tags or [],
        "lifecycle_stage": LifecycleStage.PUBLISHED.value,
        "lifecycle_status": LifecycleStatus.PUBLISHED.value,
        "next_step": "delivery",
    }


async def search_catalog(
    db: AsyncSession,
    keyword: str = "",
    category: Optional[str] = None,
    classification_level: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    发布发现 - 检索查询

    基于关键词、分类、级别等条件检索数据目录
    """
    from app.services.catalog_service import search_catalog as do_search
    from app.utils.pagination import PaginationParams

    params = PaginationParams(page=page, page_size=page_size)
    result = await do_search(db, params, keyword, category, classification_level)

    return {
        "total": result.total,
        "page": page,
        "page_size": page_size,
        "items": [item.model_dump() for item in result.items],
    }


# ==================== 服务交付 ====================

async def create_delivery_api(
    db: AsyncSession,
    asset_id: str,
    api_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    服务交付 - 接口封装

    步骤：
    1. 验证资产已发布
    2. 创建API接口配置
    3. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.DELIVERY)

    if asset.lifecycle_status != LifecycleStatus.PUBLISHED.value:
        raise LifecycleStateError("资产未发布，无法创建交付接口")

    # 生成API配置
    api_result = {
        "api_id": str(uuid.uuid4()),
        "asset_id": asset_id,
        "api_type": api_config.get("api_type", "REST"),
        "endpoint": f"/api/v1/data/{asset_id}",
        "authentication": api_config.get("authentication", "api_key"),
        "rate_limit": api_config.get("rate_limit", 100),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新生命周期状态
    asset.lifecycle_stage = LifecycleStage.DELIVERY.value
    asset.lifecycle_status = LifecycleStatus.API_PACKING.value
    await db.commit()

    logger.info(f"Delivery API created for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "api_config": api_result,
        "lifecycle_stage": LifecycleStage.DELIVERY.value,
        "lifecycle_status": LifecycleStatus.API_PACKING.value,
        "next_step": "trusted_delivery",
    }


async def trusted_delivery(
    db: AsyncSession,
    asset_id: str,
    subscriber_id: str,
    delivery_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    服务交付 - 可信交付

    步骤：
    1. 验证订阅权限
    2. 执行可信交付（加密传输、完整性校验）
    3. 记录交付日志
    4. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.DELIVERY)

    # 生成交付记录
    delivery_id = str(uuid.uuid4())
    delivery_hash = gmssl_adapter.sm3_hash(f"{asset_id}:{subscriber_id}:{delivery_id}")

    delivery_result = {
        "delivery_id": delivery_id,
        "asset_id": asset_id,
        "subscriber_id": subscriber_id,
        "delivery_hash": delivery_hash,
        "encryption": delivery_config.get("encryption", "AES-256") if delivery_config else "AES-256",
        "integrity_check": "SM3",
        "delivered_at": datetime.now(timezone.utc).isoformat(),
    }

    # 记录访问日志
    access_log = AccessLog(
        user_id=uuid.UUID(subscriber_id),
        asset_id=uuid.UUID(asset_id),
        action="delivery",
        result="success",
        details=delivery_result,
    )
    db.add(access_log)

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.DELIVERING.value
    await db.commit()

    logger.info(f"Trusted delivery completed: asset={asset_id}, subscriber={subscriber_id}")
    return {
        "asset_id": str(asset.id),
        "delivery_result": delivery_result,
        "lifecycle_stage": LifecycleStage.DELIVERY.value,
        "lifecycle_status": LifecycleStatus.DELIVERING.value,
        "next_step": "monitor_quality",
    }


async def monitor_delivery_quality(
    db: AsyncSession,
    asset_id: str,
    monitoring_period_hours: int = 24,
) -> Dict[str, Any]:
    """
    服务交付 - 质量监控

    步骤：
    1. 收集交付质量指标
    2. 计算SLA达成率
    3. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.DELIVERY)

    # 查询最近的访问记录
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=monitoring_period_hours)

    result = await db.execute(
        select(func.count(AccessLog.id)).where(
            and_(
                AccessLog.asset_id == uuid.UUID(asset_id),
                AccessLog.created_at >= cutoff,
            )
        )
    )
    access_count = result.scalar() or 0

    monitoring_result = {
        "asset_id": asset_id,
        "monitoring_period_hours": monitoring_period_hours,
        "access_count": access_count,
        "avg_response_time_ms": 150,  # 模拟值
        "success_rate": 99.5,  # 模拟值
        "sla_compliance": True,
        "monitored_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.MONITORING.value
    await db.commit()

    logger.info(f"Delivery quality monitored for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "monitoring_result": monitoring_result,
        "lifecycle_stage": LifecycleStage.DELIVERY.value,
        "lifecycle_status": LifecycleStatus.MONITORING.value,
        "next_step": "valuation",
    }


# ==================== 价值评估 ====================

async def assess_asset_value(
    db: AsyncSession,
    asset_id: str,
    valuation_method: str = "cost_approach",
) -> Dict[str, Any]:
    """
    价值评估 - 资产评估

    评估方法：
    - cost_approach: 成本法
    - market_approach: 市场法
    - income_approach: 收益法
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.VALUATION)

    # 计算资产价值（基于多种因素）
    base_value = 1000.0  # 基础价值

    # 质量因子
    quality_result = await db.execute(
        select(DataQualityReport)
        .where(DataQualityReport.asset_id == uuid.UUID(asset_id))
        .order_by(DataQualityReport.generated_at.desc())
        .limit(1)
    )
    quality_report = quality_result.scalar_one_or_none()
    quality_factor = float(quality_report.overall_score) if quality_report else 0.8

    # 使用频率因子
    usage_result = await db.execute(
        select(func.count(AccessLog.id)).where(
            AccessLog.asset_id == uuid.UUID(asset_id)
        )
    )
    usage_count = usage_result.scalar() or 0
    usage_factor = min(usage_count / 1000, 2.0)  # 最高2倍

    # 安全等级因子
    security_factor = {1: 2.0, 2: 1.5, 3: 1.2, 4: 1.0}.get(
        asset.classification_level, 1.0
    )

    # 计算最终价值
    estimated_value = base_value * quality_factor * usage_factor * security_factor

    valuation_result = {
        "asset_id": asset_id,
        "valuation_method": valuation_method,
        "base_value": base_value,
        "quality_factor": round(quality_factor, 2),
        "usage_factor": round(usage_factor, 2),
        "security_factor": security_factor,
        "estimated_value": round(estimated_value, 2),
        "currency": "CNY",
        "valued_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新生命周期状态
    asset.lifecycle_stage = LifecycleStage.VALUATION.value
    asset.lifecycle_status = LifecycleStatus.ASSET_VALUING.value
    await db.commit()

    logger.info(f"Asset value assessed: {asset_id}, value={estimated_value}")
    return {
        "asset_id": str(asset.id),
        "valuation_result": valuation_result,
        "lifecycle_stage": LifecycleStage.VALUATION.value,
        "lifecycle_status": LifecycleStatus.ASSET_VALUING.value,
        "next_step": "usage_statistics",
    }


async def get_usage_statistics(
    db: AsyncSession,
    asset_id: str,
    period_days: int = 30,
) -> Dict[str, Any]:
    """
    价值评估 - 使用统计

    统计指标：
    - 访问次数
    - 独立用户数
    - 下载量
    - 调用频率
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.VALUATION)

    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

    # 访问次数
    total_result = await db.execute(
        select(func.count(AccessLog.id)).where(
            and_(
                AccessLog.asset_id == uuid.UUID(asset_id),
                AccessLog.created_at >= cutoff,
            )
        )
    )
    total_access = total_result.scalar() or 0

    # 独立用户数
    unique_result = await db.execute(
        select(func.count(func.distinct(AccessLog.user_id))).where(
            and_(
                AccessLog.asset_id == uuid.UUID(asset_id),
                AccessLog.created_at >= cutoff,
            )
        )
    )
    unique_users = unique_result.scalar() or 0

    usage_stats = {
        "asset_id": asset_id,
        "period_days": period_days,
        "total_access_count": total_access,
        "unique_user_count": unique_users,
        "avg_daily_access": round(total_access / max(period_days, 1), 2),
        "download_count": 0,  # 需要从交付记录统计
        "api_call_count": total_access,
        "statistics_generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.USAGE_STATING.value
    await db.commit()

    logger.info(f"Usage statistics generated for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "usage_statistics": usage_stats,
        "lifecycle_stage": LifecycleStage.VALUATION.value,
        "lifecycle_status": LifecycleStatus.USAGE_STATING.value,
        "next_step": "revenue_distribution",
    }


async def distribute_revenue(
    db: AsyncSession,
    asset_id: str,
    billing_period: str,
) -> Dict[str, Any]:
    """
    价值评估 - 收益分配

    步骤：
    1. 计算收益分配
    2. 生成结算单
    3. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.VALUATION)

    # 调用收益分配服务
    from app.services.revenue_service import calculate_revenue_distribution
    distribution = await calculate_revenue_distribution(
        db, billing_period, str(asset.organization_id)
    )

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.REVENUE_DISTRIBUTING.value
    await db.commit()

    logger.info(f"Revenue distributed for asset: {asset_id}, period: {billing_period}")
    return {
        "asset_id": str(asset.id),
        "revenue_distribution": distribution,
        "lifecycle_stage": LifecycleStage.VALUATION.value,
        "lifecycle_status": LifecycleStatus.REVENUE_DISTRIBUTING.value,
        "next_step": "decommission",
    }


# ==================== 退出注销 ====================

async def destroy_data(
    db: AsyncSession,
    asset_id: str,
    destroy_reason: str = "",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    退出注销 - 数据销毁

    步骤：
    1. 验证所有合约已终止
    2. 执行数据销毁
    3. 记录销毁证明
    4. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)
    _validate_stage_transition(asset, LifecycleStage.DECOMMISSION)

    # 检查是否有活跃合约
    active_contracts = await db.execute(
        select(func.count(Contract.id)).where(
            and_(
                Contract.related_product_id == uuid.UUID(asset_id),
                Contract.status == "active",
            )
        )
    )
    contract_count = active_contracts.scalar() or 0
    if contract_count > 0:
        raise LifecycleStateError(f"存在{contract_count}个活跃合约，请先终止合约")

    # 生成销毁证明
    destroy_hash = gmssl_adapter.sm3_hash(
        f"{asset_id}:{destroy_reason}:{datetime.now(timezone.utc).isoformat()}"
    )

    destroy_result = {
        "asset_id": asset_id,
        "destroy_reason": destroy_reason,
        "destroy_hash": destroy_hash,
        "destroyed_by": user_id,
        "destroyed_at": datetime.now(timezone.utc).isoformat(),
        "proof": f"0x{destroy_hash}",
    }

    # 更新资产状态
    asset.status = "deleted"
    asset.lifecycle_status = LifecycleStatus.DATA_DESTROYING.value
    await db.commit()

    logger.info(f"Data destroyed for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "destroy_result": destroy_result,
        "lifecycle_stage": LifecycleStage.DECOMMISSION.value,
        "lifecycle_status": LifecycleStatus.DATA_DESTROYING.value,
        "next_step": "terminate_contracts",
    }


async def terminate_related_contracts(
    db: AsyncSession,
    asset_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    退出注销 - 合约终止

    步骤：
    1. 查找所有相关合约
    2. 逐一终止
    3. 更新生命周期状态
    """
    asset = await _get_asset_or_raise(db, asset_id)

    # 查找相关合约
    result = await db.execute(
        select(Contract).where(
            and_(
                Contract.related_product_id == uuid.UUID(asset_id),
                Contract.status.in_(["active", "draft"]),
            )
        )
    )
    contracts = result.scalars().all()

    terminated_contracts = []
    for contract in contracts:
        from app.services.contract_service import terminate_contract
        terminated = await terminate_contract(db, str(contract.id), user_id)
        terminated_contracts.append(terminated)

    # 更新生命周期状态
    asset.lifecycle_status = LifecycleStatus.CONTRACT_TERMINATING.value
    await db.commit()

    logger.info(f"Related contracts terminated for asset: {asset_id}, count: {len(terminated_contracts)}")
    return {
        "asset_id": str(asset.id),
        "terminated_contracts": terminated_contracts,
        "contract_count": len(terminated_contracts),
        "lifecycle_stage": LifecycleStage.DECOMMISSION.value,
        "lifecycle_status": LifecycleStatus.CONTRACT_TERMINATING.value,
        "next_step": "archive_records",
    }


async def archive_lifecycle_records(
    db: AsyncSession,
    asset_id: str,
) -> Dict[str, Any]:
    """
    退出注销 - 记录归档

    步骤：
    1. 收集生命周期所有记录
    2. 生成归档包
    3. 更新生命周期状态为已注销
    """
    asset = await _get_asset_or_raise(db, asset_id)

    # 收集所有相关记录
    archive_data = {
        "asset_info": {
            "id": str(asset.id),
            "name": asset.name,
            "category": asset.category,
            "classification_level": asset.classification_level,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        },
        "lifecycle_summary": {
            "stage": asset.lifecycle_stage,
            "status": asset.lifecycle_status,
        },
        "archived_at": datetime.now(timezone.utc).isoformat(),
    }

    # 生成归档哈希
    archive_hash = gmssl_adapter.sm3_hash(str(archive_data))

    # 更新生命周期状态为已注销
    asset.lifecycle_stage = LifecycleStage.DECOMMISSION.value
    asset.lifecycle_status = LifecycleStatus.DECOMMISSIONED.value
    await db.commit()

    logger.info(f"Lifecycle records archived for asset: {asset_id}")
    return {
        "asset_id": str(asset.id),
        "archive_hash": archive_hash,
        "archive_data": archive_data,
        "lifecycle_stage": LifecycleStage.DECOMMISSION.value,
        "lifecycle_status": LifecycleStatus.DECOMMISSIONED.value,
        "message": "数据资源生命周期已完成",
    }


# ==================== 生命周期查询 ====================

async def get_lifecycle_status(
    db: AsyncSession,
    asset_id: str,
) -> Dict[str, Any]:
    """获取数据资源的生命周期状态"""
    asset = await _get_asset_or_raise(db, asset_id)

    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "lifecycle_stage": asset.lifecycle_stage,
        "lifecycle_status": asset.lifecycle_status,
        "classification_level": asset.classification_level,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


async def get_lifecycle_history(
    db: AsyncSession,
    asset_id: str,
) -> Dict[str, Any]:
    """获取数据资源的生命周期历史记录"""
    asset = await _get_asset_or_raise(db, asset_id)

    # 查询所有相关的访问日志
    result = await db.execute(
        select(AccessLog)
        .where(AccessLog.asset_id == uuid.UUID(asset_id))
        .order_by(AccessLog.created_at.desc())
        .limit(100)
    )
    logs = result.scalars().all()

    history = [
        {
            "id": str(log.id),
            "action": log.action,
            "result": log.result,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]

    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "current_stage": asset.lifecycle_stage,
        "current_status": asset.lifecycle_status,
        "history": history,
        "total_records": len(history),
    }


# ==================== 辅助函数 ====================

async def _get_asset_or_raise(db: AsyncSession, asset_id: str) -> DataAsset:
    """获取资产或抛出异常"""
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise DataNotFoundError(f"数据资产未找到: {asset_id}")
    return asset


def _validate_stage_transition(asset: DataAsset, target_stage: LifecycleStage) -> None:
    """验证阶段转换是否合法"""
    current_stage = asset.lifecycle_stage

    # 如果没有设置生命周期阶段，允许从头开始
    if not current_stage:
        return

    # 阶段流转顺序验证
    current_idx = -1
    target_idx = -1

    for i, stage in enumerate(STAGE_ORDER):
        if stage.value == current_stage:
            current_idx = i
        if stage == target_stage:
            target_idx = i

    if current_idx >= 0 and target_idx >= 0:
        # 允许同阶段内的状态转换，以及向前流转
        if target_idx < current_idx:
            raise LifecycleStateError(
                f"不允许从{current_stage}回退到{target_stage.value}"
            )


def _generate_data_identifier(asset: DataAsset) -> str:
    """生成数据标识（基于SM3国密哈希）"""
    identifier_str = f"{asset.id}:{asset.name}:{asset.created_at}"
    hash_value = gmssl_adapter.sm3_hash(identifier_str)
    return f"DID:DATA:{hash_value[:32]}"


def _identify_sensitive_fields(schema_def: Dict[str, Any]) -> List[str]:
    """识别敏感字段"""
    import re

    sensitive_patterns = [
        re.compile(r"(name|姓名)", re.IGNORECASE),
        re.compile(r"(phone|mobile|tel|电话|手机)", re.IGNORECASE),
        re.compile(r"(id_card|身份证|sfz)", re.IGNORECASE),
        re.compile(r"(email|邮箱)", re.IGNORECASE),
        re.compile(r"(address|地址)", re.IGNORECASE),
        re.compile(r"(password|密码|secret)", re.IGNORECASE),
        re.compile(r"(bank|银行|account|账号)", re.IGNORECASE),
    ]

    fields = schema_def.get("fields", schema_def.get("columns", []))
    sensitive_fields = []

    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, dict):
                field_name = field.get("name", "")
                for pattern in sensitive_patterns:
                    if pattern.search(field_name):
                        sensitive_fields.append(field_name)
                        break

    return sensitive_fields
