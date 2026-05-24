"""Evidence Center API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_sync_db
from app.utils.deps import get_current_user
from app.schemas import PaginationParams, PaginatedResponse
from app.schemas.asset import AssetCreate, AssetUpdate, AssetWithOwner
from app.schemas.evidence import EvidenceWithDetail, TraceTimeline, ChainBlock, ChainVerifyResult
from app.models import User
from . import service

router = APIRouter(prefix="/api/evidence-center", tags=["存证登记中心"])


# ============ Data Asset Endpoints ============

@router.post("/asset/register", response_model=AssetWithOwner, summary="注册数据资产")
def register_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    asset = service.register_asset(db, current_user.id, asset_in)
    return service._build_asset_with_owner(asset)


@router.put("/asset/{asset_id}", response_model=AssetWithOwner, summary="更新数据资产")
def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    asset = service.update_asset(db, current_user.id, asset_id, asset_in)
    return service._build_asset_with_owner(asset)


@router.post("/asset/{asset_id}/publish", response_model=AssetWithOwner, summary="发布数据资产")
def publish_asset(
    asset_id: int,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    asset = service.publish_asset(db, current_user.id, asset_id)
    return service._build_asset_with_owner(asset)


@router.post("/asset/{asset_id}/archive", response_model=AssetWithOwner, summary="归档数据资产")
def archive_asset(
    asset_id: int,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    asset = service.archive_asset(db, current_user.id, asset_id)
    return service._build_asset_with_owner(asset)


@router.get("/asset/list", response_model=PaginatedResponse[AssetWithOwner], summary="数据资产列表")
def get_asset_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    asset_type: Optional[str] = Query(default=None, alias="type"),
    category: Optional[str] = Query(default=None),
    owner_id: Optional[int] = Query(default=None, alias="owner"),
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    filters = {}
    if status is not None:
        filters["status"] = status
    if asset_type is not None:
        filters["asset_type"] = asset_type
    if category is not None:
        filters["category"] = category
    if owner_id is not None:
        filters["owner_id"] = owner_id

    items, total = service.get_asset_list(db, pagination, filters)
    items_with_owner = [service._build_asset_with_owner(a) for a in items]
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[AssetWithOwner(**d) for d in items_with_owner],
    )


@router.get("/asset/{asset_id}", response_model=AssetWithOwner, summary="数据资产详情")
def get_asset_detail(
    asset_id: int,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    detail = service.get_asset_detail(db, asset_id)
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="数据资产不存在")
    return AssetWithOwner(**detail)


# ============ Evidence Endpoints ============

@router.post("/evidence/record", response_model=EvidenceWithDetail, summary="记录存证")
def record_evidence(
    body: dict,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    asset_id = body.get("asset_id")
    action = body.get("action")
    extra_data = body.get("extra_data")
    if not asset_id or not action:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="asset_id 和 action 为必填项")

    record = service.record_evidence(db, asset_id, current_user.id, action, extra_data)
    db.refresh(record)
    return service._build_evidence_with_detail(record)


@router.get("/evidence/list", response_model=PaginatedResponse[EvidenceWithDetail], summary="存证记录列表")
def get_evidence_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    asset_id: Optional[int] = Query(default=None),
    action: Optional[str] = Query(default=None),
    operator_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    filters = {}
    if asset_id is not None:
        filters["asset_id"] = asset_id
    if action is not None:
        filters["action"] = action
    if operator_id is not None:
        filters["operator_id"] = operator_id

    items, total = service.get_evidence_list(db, pagination, filters)
    items_with_detail = [service._build_evidence_with_detail(r) for r in items]
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[EvidenceWithDetail(**d) for d in items_with_detail],
    )


@router.get("/trace/{asset_id}", response_model=TraceTimeline, summary="资产溯源时间线")
def trace_asset(
    asset_id: int,
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    return service.trace_asset(db, asset_id)


# ============ Chain Endpoints ============

@router.get("/chain/blocks", response_model=PaginatedResponse[ChainBlock], summary="区块链区块列表")
def get_chain_blocks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = service.get_chain_blocks(db, pagination)
    return PaginatedResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/chain/verify", response_model=ChainVerifyResult, summary="区块链完整性验证")
def verify_chain(
    db: Session = Depends(get_sync_db),
    current_user: User = Depends(get_current_user),
):
    return service.verify_chain_integrity()
