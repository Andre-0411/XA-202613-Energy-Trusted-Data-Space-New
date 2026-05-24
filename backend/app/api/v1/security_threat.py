"""
威胁检测 API - /api/v1/security/threats
威胁事件列表 + 主动检测 + 详情 + 处置 + 安全态势
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import threat_service

router = APIRouter()


class ThreatResolveRequest(BaseModel):
    """威胁处置请求"""
    resolution: str = Field(description="处置方式: resolved/false_positive/mitigated")
    description: str = Field(default="", description="处置描述")


@router.get("", response_model=ApiResponse)
async def list_threats(
    threat_type: Optional[str] = Query(None, description="威胁类型"),
    severity: Optional[str] = Query(None, description="严重级别: low/medium/high/critical"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """威胁事件列表"""
    result = await threat_service.list_threats(
        db=db,
        threat_type=threat_type,
        severity=severity,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(data=result)


@router.post("/detect", response_model=ApiResponse)
async def detect_threats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """主动威胁检测（基于规则引擎扫描异常行为）"""
    result = await threat_service.detect_threats(db=db)
    return ApiResponse(data=result)


@router.get("/dashboard", response_model=ApiResponse)
async def security_dashboard(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """安全态势仪表盘"""
    result = await threat_service.get_security_dashboard(db=db)
    return ApiResponse(data=result)


@router.get("/{threat_id}", response_model=ApiResponse)
async def get_threat(
    threat_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """威胁详情"""
    result = await threat_service.get_threat(db=db, threat_id=threat_id)
    return ApiResponse(data=result)


@router.put("/{threat_id}/resolve", response_model=ApiResponse)
async def resolve_threat(
    threat_id: str,
    request: ThreatResolveRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """处置威胁（标记为resolved/false_positive/mitigated）"""
    result = await threat_service.resolve_threat(
        db=db,
        threat_id=threat_id,
        resolution=request.resolution,
        description=request.description,
        resolved_by=user.get("user_id", ""),
    )
    return ApiResponse(data=result)
