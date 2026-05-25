"""
系统信息 API
提供系统版本、环境、功能模块、统计数据等信息
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/info", summary="获取系统信息")
async def get_system_info(db: AsyncSession = Depends(get_db)):
    """
    获取系统信息

    返回系统版本、运行环境、启用的功能模块及各模块统计数据。
    """
    from app.models.data_asset import DataAsset
    from app.models.user import User, Organization
    from app.models.compute_task import ComputeTask
    from app.models.blockchain import BlockchainTransaction, EvidenceRecord
    from app.models.service import BillingRecord

    # 各模块统计
    assets_count = (await db.execute(
        select(func.count()).select_from(DataAsset).where(DataAsset.status != "deleted")
    )).scalar() or 0

    users_count = (await db.execute(
        select(func.count()).select_from(User).where(User.status == "active")
    )).scalar() or 0

    orgs_count = (await db.execute(
        select(func.count()).select_from(Organization).where(Organization.status == "active")
    )).scalar() or 0

    tasks_count = (await db.execute(
        select(func.count()).select_from(ComputeTask)
    )).scalar() or 0

    bc_tx_count = (await db.execute(
        select(func.count()).select_from(BlockchainTransaction)
    )).scalar() or 0

    evidences_count = (await db.execute(
        select(func.count()).select_from(EvidenceRecord)
    )).scalar() or 0

    return {
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "features": [
            "blockchain",
            "privacy_compute",
            "ai_agent",
            "mqtt_collect",
            "data_catalog",
            "evidence_center",
            "cross_chain",
        ],
        "stats": {
            "data_assets": assets_count,
            "active_users": users_count,
            "organizations": orgs_count,
            "compute_tasks": tasks_count,
            "blockchain_transactions": bc_tx_count,
            "evidences": evidences_count,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
