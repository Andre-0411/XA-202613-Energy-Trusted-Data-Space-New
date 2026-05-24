"""
APT 高级威胁检测 API - /api/v1/security/apt
流量异常检测 / UBA 用户行为分析 / 恶意软件签名匹配 / IOC 威胁情报 / 扫描规则管理
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import ApiResponse
from app.utils.deps import get_current_user
from app.services import apt_detection_service
from app.exceptions import DataValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# Request 模型
# ============================================================


class AptScanRequest(BaseModel):
    """APT 扫描请求"""
    scan_type: str = Field(default="full", description="扫描类型: full / quick / targeted")
    rule_ids: Optional[list[str]] = Field(default=None, description="指定规则 ID 列表（targeted 模式）")


class CreateDetectionRuleRequest(BaseModel):
    """创建检测规则请求"""
    name: str = Field(description="规则名称")
    description: str = Field(default="", description="规则描述")
    event_type: str = Field(description="事件类型: slow_penetration / lateral_movement / data_staging / c2_communication / privilege_abuse / data_exfiltration / uba")
    severity: str = Field(default="medium", description="严重级别: low / medium / high / critical")
    condition: str = Field(description="检测条件描述")
    time_window_hours: int = Field(default=24, ge=1, description="时间窗口（小时）")
    threshold: float = Field(default=1.0, ge=0, description="触发阈值")
    enabled: bool = Field(default=True, description="是否启用")


# ============================================================
# API 端点
# ============================================================


@router.get("/events", response_model=ApiResponse)
async def list_apt_events(
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    severity: Optional[str] = Query(None, description="严重级别过滤: low / medium / high / critical"),
    status: Optional[str] = Query(None, description="状态过滤: detected / investigating / resolved"),
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """APT 事件列表（含数据库 + 内存缓存）"""
    try:
        result = await apt_detection_service.list_apt_events(
            db=db,
            event_type=event_type,
            severity=severity,
            status=status,
            limit=limit,
            offset=offset,
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"查询 APT 事件失败: {e}")
        return ApiResponse(code=4000, message=f"查询失败: {e}", data=None)


@router.post("/scan", response_model=ApiResponse)
async def run_apt_scan(
    request: AptScanRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """手动触发 APT 扫描

    执行检测规则引擎 + IOC 威胁情报匹配 + 流量异常分析（full/targeted 模式）。
    """
    try:
        result = await apt_detection_service.run_apt_scan(
            db=db,
            scan_type=request.scan_type,
            rule_ids=request.rule_ids,
            user_id=user.get("user_id", ""),
        )
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"APT 扫描失败: {e}")
        return ApiResponse(code=4000, message=f"扫描失败: {e}", data=None)


@router.get("/rules", response_model=ApiResponse)
async def get_detection_rules(
    user: dict = Depends(get_current_user),
):
    """获取 APT 检测规则列表"""
    try:
        result = await apt_detection_service.get_detection_rules()
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"获取检测规则失败: {e}")
        return ApiResponse(code=4000, message=f"获取规则失败: {e}", data=None)


@router.post("/rules", response_model=ApiResponse)
async def create_detection_rule(
    request: CreateDetectionRuleRequest,
    user: dict = Depends(get_current_user),
):
    """创建自定义 APT 检测规则"""
    try:
        result = await apt_detection_service.create_detection_rule(
            name=request.name,
            event_type=request.event_type,
            severity=request.severity,
            condition=request.condition,
            description=request.description,
            time_window_hours=request.time_window_hours,
            threshold=request.threshold,
            enabled=request.enabled,
        )
        return ApiResponse(data=result)
    except DataValidationError as e:
        logger.warning(f"创建检测规则参数校验失败: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"创建检测规则失败: {e}")
        return ApiResponse(code=4000, message=f"创建规则失败: {e}", data=None)


@router.get("/ioc", response_model=ApiResponse)
async def get_threat_intel_iocs(
    ioc_type: Optional[str] = Query(None, description="IOC 类型: ip / domain / hash"),
    user: dict = Depends(get_current_user),
):
    """获取威胁情报 IOC 指标列表"""
    try:
        result = await apt_detection_service.get_threat_intel_iocs(ioc_type=ioc_type)
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"获取 IOC 列表失败: {e}")
        return ApiResponse(code=4000, message=f"获取 IOC 失败: {e}", data=None)
