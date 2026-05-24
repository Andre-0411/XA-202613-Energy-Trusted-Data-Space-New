"""
服务申请审批 API - /api/v1/data/applications
提交申请 / 申请列表 / 申请详情 / 审批通过 / 审批拒绝 / 申请统计
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.data_asset import DataAsset
from app.models.access_log import AccessLog
from app.schemas.common import ApiResponse, PaginatedResponse
from app.utils.deps import get_current_user, get_pagination_params, PaginationParams
from app.utils.pagination import paginate_query

router = APIRouter()


# ==================== Request/Response Schemas ====================


class ApplicationCreate(BaseModel):
    """提交数据使用申请"""
    asset_id: str = Field(description="数据资产 ID")
    purpose: str = Field(description="申请用途")
    duration_days: int = Field(default=30, ge=1, le=365, description="申请使用天数")
    validity_start: Optional[str] = Field(default=None, description="有效期开始日期 (YYYY-MM-DD)")
    validity_end: Optional[str] = Field(default=None, description="有效期结束日期 (YYYY-MM-DD)")


class ApplicationApprove(BaseModel):
    """审批通过"""
    comment: Optional[str] = Field(default=None, description="审批意见")


class ApplicationReject(BaseModel):
    """审批拒绝"""
    reason: str = Field(description="拒绝原因")
    comment: Optional[str] = Field(default=None, description="审批意见")


class ApplicationResponse(BaseModel):
    """申请响应"""
    id: str
    application_no: str
    asset_id: str
    asset_name: str
    applicant_id: str
    applicant_name: Optional[str] = None
    purpose: str
    status: str
    duration_days: int
    validity_start: Optional[str] = None
    validity_end: Optional[str] = None
    approver_id: Optional[str] = None
    approver_name: Optional[str] = None
    approved_at: Optional[str] = None
    reject_reason: Optional[str] = None
    comment: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ==================== Endpoints ====================


@router.post("", response_model=ApiResponse, status_code=201)
async def create_application(
    request: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """提交数据使用申请"""
    # 校验资产存在且可用
    result = await db.execute(
        select(DataAsset).where(DataAsset.id == uuid.UUID(request.asset_id))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        return ApiResponse(code=2001, message="数据资产未找到", data=None)
    if asset.status not in ("published", "active"):
        return ApiResponse(code=2002, message="数据资产不可申请", data=None)

    # 检查是否已有待审批的申请
    existing = await db.execute(
        select(AccessLog).where(
            and_(
                AccessLog.user_id == uuid.UUID(user["user_id"]),
                AccessLog.asset_id == uuid.UUID(request.asset_id),
                AccessLog.action == "apply",
                AccessLog.result == "pending",
            )
        )
    )
    if existing.scalar_one_or_none():
        return ApiResponse(code=2003, message="您已有待审批的申请，请勿重复提交", data=None)

    # 生成申请编号
    application_no = f"DA-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"
    application_id = str(uuid.uuid4())

    # 创建申请记录
    access_log = AccessLog(
        user_id=uuid.UUID(user["user_id"]),
        asset_id=uuid.UUID(request.asset_id),
        action="apply",
        result="pending",
        details={
            "application_id": application_id,
            "application_no": application_no,
            "purpose": request.purpose,
            "duration_days": request.duration_days,
            "validity_start": request.validity_start,
            "validity_end": request.validity_end,
            "asset_name": asset.name,
            "classification_level": asset.classification_level,
        },
    )
    db.add(access_log)
    await db.commit()

    return ApiResponse(
        message="申请已提交",
        data={
            "application_id": application_id,
            "application_no": application_no,
            "asset_id": str(asset.id),
            "asset_name": asset.name,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("", response_model=ApiResponse)
async def list_applications(
    pagination: PaginationParams = Depends(get_pagination_params),
    status: Optional[str] = Query(None, description="申请状态: pending/approved/rejected/revoked"),
    scope: Optional[str] = Query("all", description="查询范围: mine/pending_approval/all"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取申请列表（支持按状态筛选）"""
    query = select(AccessLog).where(AccessLog.action == "apply")

    # 查询范围
    user_id = uuid.UUID(user["user_id"])
    user_role = user.get("role", "user")

    if scope == "mine":
        query = query.where(AccessLog.user_id == user_id)
    elif scope == "pending_approval":
        # 待我审批（需要 admin 或 data_admin 角色）
        if user_role not in ("admin", "data_admin"):
            query = query.where(AccessLog.user_id == user_id)
        else:
            query = query.where(AccessLog.result == "pending")
    # all: admin/data_admin 可看所有，其他只看自己的

    if user_role not in ("admin", "data_admin") and scope == "all":
        query = query.where(AccessLog.user_id == user_id)

    # 状态筛选
    if status:
        query = query.where(AccessLog.result == status)

    # 关键词搜索
    if keyword:
        search_term = f"%{keyword}%"
        query = query.where(
            or_(
                AccessLog.details["application_no"].as_string().ilike(search_term),
                AccessLog.details["asset_name"].as_string().ilike(search_term),
            )
        )

    # 分页查询
    count_query = select(func.count()).select_from(
        query.with_only_columns(AccessLog.id).subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (pagination.page - 1) * pagination.page_size
    query = query.order_by(AccessLog.created_at.desc() if hasattr(AccessLog, 'created_at') else AccessLog.id.desc())
    query = query.offset(offset).limit(pagination.page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # 转换为申请响应格式
    applications = []
    for log in logs:
        details = log.details or {}
        applications.append({
            "id": details.get("application_id", str(log.id)),
            "application_no": details.get("application_no", ""),
            "asset_id": str(log.asset_id),
            "asset_name": details.get("asset_name", ""),
            "applicant_id": str(log.user_id),
            "purpose": details.get("purpose", ""),
            "status": log.result,
            "duration_days": details.get("duration_days", 30),
            "validity_start": details.get("validity_start"),
            "validity_end": details.get("validity_end"),
            "approver_id": details.get("approver_id"),
            "approved_at": details.get("approved_at"),
            "reject_reason": details.get("reject_reason"),
            "comment": details.get("comment"),
            "created_at": log.created_at.isoformat() if hasattr(log, 'created_at') and log.created_at else "",
            "updated_at": details.get("updated_at", ""),
        })

    total_pages = (total + pagination.page_size - 1) // pagination.page_size if pagination.page_size > 0 else 0
    return ApiResponse(data={
        "items": applications,
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total_pages": total_pages,
    })


@router.get("/stats", response_model=ApiResponse)
async def get_application_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取申请统计"""
    user_id = uuid.UUID(user["user_id"])
    user_role = user.get("role", "user")

    # 基础查询
    if user_role in ("admin", "data_admin"):
        base_query = select(AccessLog).where(AccessLog.action == "apply")
    else:
        base_query = select(AccessLog).where(
            AccessLog.action == "apply",
            AccessLog.user_id == user_id,
        )

    # 总申请数
    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = total_result.scalar() or 0

    # 待审批数
    pending_result = await db.execute(
        select(func.count()).select_from(
            base_query.where(AccessLog.result == "pending").subquery()
        )
    )
    pending = pending_result.scalar() or 0

    # 已通过数
    approved_result = await db.execute(
        select(func.count()).select_from(
            base_query.where(AccessLog.result == "approved").subquery()
        )
    )
    approved = approved_result.scalar() or 0

    # 已拒绝数
    rejected_result = await db.execute(
        select(func.count()).select_from(
            base_query.where(AccessLog.result == "rejected").subquery()
        )
    )
    rejected = rejected_result.scalar() or 0

    return ApiResponse(data={
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
    })


@router.get("/{application_id}", response_model=ApiResponse)
async def get_application_detail(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取申请详情"""
    # 通过 details 中的 application_id 查找
    result = await db.execute(
        select(AccessLog).where(
            AccessLog.action == "apply",
            AccessLog.details["application_id"].as_string() == application_id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        return ApiResponse(code=2001, message="申请记录未找到", data=None)

    details = log.details or {}
    return ApiResponse(data={
        "id": details.get("application_id", str(log.id)),
        "application_no": details.get("application_no", ""),
        "asset_id": str(log.asset_id),
        "asset_name": details.get("asset_name", ""),
        "applicant_id": str(log.user_id),
        "purpose": details.get("purpose", ""),
        "status": log.result,
        "duration_days": details.get("duration_days", 30),
        "validity_start": details.get("validity_start"),
        "validity_end": details.get("validity_end"),
        "approver_id": details.get("approver_id"),
        "approved_at": details.get("approved_at"),
        "reject_reason": details.get("reject_reason"),
        "comment": details.get("comment"),
        "created_at": log.created_at.isoformat() if hasattr(log, 'created_at') and log.created_at else "",
        "updated_at": details.get("updated_at", ""),
    })


@router.put("/{application_id}/approve", response_model=ApiResponse)
async def approve_application(
    application_id: str,
    request: ApplicationApprove,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批通过"""
    # 权限检查
    user_role = user.get("role", "user")
    if user_role not in ("admin", "data_admin"):
        return ApiResponse(code=4003, message="权限不足，仅管理员可审批", data=None)

    # 查找申请记录
    result = await db.execute(
        select(AccessLog).where(
            AccessLog.action == "apply",
            AccessLog.details["application_id"].as_string() == application_id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        return ApiResponse(code=2001, message="申请记录未找到", data=None)

    if log.result != "pending":
        return ApiResponse(code=2002, message="该申请已被处理", data=None)

    # 更新状态
    now = datetime.now(timezone.utc)
    log.result = "approved"
    details = dict(log.details or {})
    details["approver_id"] = user["user_id"]
    details["approved_at"] = now.isoformat()
    details["comment"] = request.comment or ""
    details["updated_at"] = now.isoformat()
    log.details = details

    await db.commit()
    return ApiResponse(message="申请已通过", data={"application_id": application_id, "status": "approved"})


@router.put("/{application_id}/reject", response_model=ApiResponse)
async def reject_application(
    application_id: str,
    request: ApplicationReject,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """审批拒绝"""
    # 权限检查
    user_role = user.get("role", "user")
    if user_role not in ("admin", "data_admin"):
        return ApiResponse(code=4003, message="权限不足，仅管理员可审批", data=None)

    # 查找申请记录
    result = await db.execute(
        select(AccessLog).where(
            AccessLog.action == "apply",
            AccessLog.details["application_id"].as_string() == application_id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        return ApiResponse(code=2001, message="申请记录未找到", data=None)

    if log.result != "pending":
        return ApiResponse(code=2002, message="该申请已被处理", data=None)

    # 更新状态
    now = datetime.now(timezone.utc)
    log.result = "rejected"
    details = dict(log.details or {})
    details["approver_id"] = user["user_id"]
    details["reject_reason"] = request.reason
    details["comment"] = request.comment or ""
    details["updated_at"] = now.isoformat()
    log.details = details

    await db.commit()
    return ApiResponse(message="申请已拒绝", data={"application_id": application_id, "status": "rejected"})
