"""Evidence center business logic."""

import hashlib
import json
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import DataAsset, EvidenceRecord, User, Organization
from app.schemas.asset import AssetCreate, AssetUpdate
from app.schemas.evidence import EvidenceWithDetail, TraceTimeline, TraceEvent, ChainBlock, ChainVerifyResult
from app.modules.module_base import BaseService
from .blockchain import init_chain, submit_block, get_latest_block, get_block, get_chain, verify_chain

# Try gmssl for SM3, fall back to SHA256
try:
    from gmssl import sm3, func as sm3_func

    def _sm3_hash(data: bytes) -> str:
        return sm3.sm3_hash(sm3_func.bytes_to_list(data))

except ImportError:

    def _sm3_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


asset_service = BaseService(DataAsset)
evidence_service = BaseService(EvidenceRecord)


def _build_asset_with_owner(asset: DataAsset) -> dict:
    """Build dict with owner_name for AssetWithOwner schema."""
    data = {
        "id": asset.id,
        "name": asset.name,
        "description": asset.description,
        "asset_type": asset.asset_type,
        "category": asset.category,
        "owner_id": asset.owner_id,
        "did": asset.did,
        "metadata": asset.asset_metadata,
        "data_hash": asset.data_hash,
        "size_bytes": asset.size_bytes,
        "record_count": asset.record_count,
        "status": asset.status,
        "created_by": asset.created_by,
        "created_at": asset.created_at,
        "owner_name": None,
    }
    if asset.owner:
        data["owner_name"] = asset.owner.name
    return data


def register_asset(db: Session, user_id: int, asset_in: AssetCreate) -> DataAsset:
    """Create asset, hash metadata with SM3, create genesis evidence on blockchain."""
    init_chain()

    metadata_str = json.dumps(asset_in.metadata or {}, sort_keys=True, ensure_ascii=False)
    data_hash = _sm3_hash(metadata_str.encode("utf-8"))

    asset = DataAsset(
        name=asset_in.name,
        description=asset_in.description,
        asset_type=asset_in.asset_type,
        category=asset_in.category,
        owner_id=user_id,
        did=asset_in.did,
        metadata=asset_in.metadata,
        data_hash=data_hash,
        size_bytes=asset_in.size_bytes,
        record_count=asset_in.record_count,
        status="draft",
        created_by=user_id,
    )
    db.add(asset)
    db.flush()

    record_evidence(db, asset.id, user_id, "register", {"asset_name": asset.name})
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(db: Session, user_id: int, asset_id: int, asset_in: AssetUpdate) -> DataAsset:
    """Update asset and record evidence on blockchain."""
    asset = asset_service.get_or_404(db, asset_id, "数据资产不存在")

    update_data = asset_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    if asset_in.metadata is not None:
        metadata_str = json.dumps(asset_in.metadata, sort_keys=True, ensure_ascii=False)
        asset.data_hash = _sm3_hash(metadata_str.encode("utf-8"))

    db.flush()
    record_evidence(db, asset_id, user_id, "update", update_data)
    db.commit()
    db.refresh(asset)
    return asset


def publish_asset(db: Session, user_id: int, asset_id: int) -> DataAsset:
    """Change status to published and record on blockchain."""
    asset = asset_service.get_or_404(db, asset_id, "数据资产不存在")
    if asset.status != "draft":
        raise ValueError("只有草稿状态的数据资产可以发布")
    asset.status = "published"
    db.flush()
    record_evidence(db, asset_id, user_id, "publish")
    db.commit()
    db.refresh(asset)
    return asset


def archive_asset(db: Session, user_id: int, asset_id: int) -> DataAsset:
    """Change status to archived."""
    asset = asset_service.get_or_404(db, asset_id, "数据资产不存在")
    asset.status = "archived"
    db.commit()
    db.refresh(asset)
    return asset


def get_asset_list(db: Session, pagination, filters: dict = None) -> tuple[list, int]:
    """List assets with filters."""
    return asset_service.get_list(db, pagination, filters, order_by="created_at", order_desc=True)


def get_asset_detail(db: Session, asset_id: int) -> Optional[dict]:
    """Get asset with owner name."""
    asset = db.query(DataAsset).filter(DataAsset.id == asset_id).first()
    if not asset:
        return None
    return _build_asset_with_owner(asset)


def record_evidence(
    db: Session, asset_id: int, operator_id: int, action: str, extra_data: dict = None
) -> EvidenceRecord:
    """Create evidence: compute data_hash, submit to blockchain, store record."""
    init_chain()

    evidence_data = json.dumps(
        {"asset_id": asset_id, "action": action, "operator_id": operator_id, "extra": extra_data or {}},
        sort_keys=True,
        ensure_ascii=False,
    )
    data_hash = hashlib.sha256(evidence_data.encode("utf-8")).hexdigest()

    latest_block = get_latest_block()
    if latest_block:
        prev_hash = latest_block["hash"]
        prev_height = latest_block["height"]
    else:
        prev_hash = "0" * 64
        prev_height = -1

    block = submit_block(evidence_data)

    record = EvidenceRecord(
        asset_id=asset_id,
        action=action,
        operator_id=operator_id,
        data_hash=data_hash,
        block_height=block["height"],
        prev_hash=prev_hash,
        block_hash=block["hash"],
        extra_data=extra_data,
    )
    db.add(record)
    db.flush()
    return record


def get_evidence_list(db: Session, pagination, filters: dict = None) -> tuple[list, int]:
    """List evidence records."""
    return evidence_service.get_list(db, pagination, filters, order_by="timestamp", order_desc=True)


def _build_evidence_with_detail(record: EvidenceRecord) -> dict:
    """Build dict for EvidenceWithDetail schema."""
    data = {
        "id": record.id,
        "asset_id": record.asset_id,
        "action": record.action,
        "operator_id": record.operator_id,
        "data_hash": record.data_hash,
        "block_height": record.block_height,
        "prev_hash": record.prev_hash,
        "block_hash": record.block_hash,
        "timestamp": record.timestamp,
        "extra_data": record.extra_data,
        "operator_name": None,
        "asset_name": None,
    }
    if record.asset:
        data["asset_name"] = record.asset.name
    return data


def trace_asset(db: Session, asset_id: int) -> TraceTimeline:
    """Get all evidence records for an asset and build timeline."""
    asset = asset_service.get_or_404(db, asset_id, "数据资产不存在")

    records = (
        db.query(EvidenceRecord)
        .filter(EvidenceRecord.asset_id == asset_id)
        .order_by(EvidenceRecord.timestamp.asc())
        .all()
    )

    events = []
    for r in records:
        operator = db.query(User).filter(User.id == r.operator_id).first()
        operator_name = operator.real_name or operator.username if operator else f"用户{r.operator_id}"
        events.append(
            TraceEvent(
                evidence_id=r.id,
                action=r.action,
                operator_name=operator_name,
                data_hash=r.data_hash,
                block_height=r.block_height,
                timestamp=r.timestamp,
                extra_data=r.extra_data,
            )
        )

    return TraceTimeline(asset_id=asset.id, asset_name=asset.name, total_events=len(events), events=events)


def get_chain_blocks(db: Session, pagination) -> tuple[list, int]:
    """Get blockchain blocks with evidence counts."""
    all_blocks = get_chain()
    total = len(all_blocks)

    # Count evidence per block height
    evidence_counts = (
        db.query(EvidenceRecord.block_height, func.count(EvidenceRecord.id))
        .group_by(EvidenceRecord.block_height)
        .all()
    )
    count_map = {bh: cnt for bh, cnt in evidence_counts}

    # Get evidences for each block
    all_evidences = db.query(EvidenceRecord).all()
    evidence_by_block = {}
    for ev in all_evidences:
        evidence_by_block.setdefault(ev.block_height, []).append(ev)

    blocks_out = []
    for blk in all_blocks:
        height = blk["height"]
        evidences = evidence_by_block.get(height, [])
        blocks_out.append(
            ChainBlock(
                block_height=height,
                block_hash=blk["hash"],
                prev_hash=blk["prev_hash"],
                evidence_count=count_map.get(height, 0),
                timestamp=blk["timestamp"],
                evidences=[
                    {
                        "id": ev.id,
                        "asset_id": ev.asset_id,
                        "action": ev.action,
                        "operator_id": ev.operator_id,
                        "data_hash": ev.data_hash,
                        "block_height": ev.block_height,
                        "prev_hash": ev.prev_hash,
                        "block_hash": ev.block_hash,
                        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                        "extra_data": ev.extra_data,
                    }
                    for ev in evidences
                ],
            )
        )

    # Pagination
    page = pagination.page
    page_size = pagination.page_size
    paginated = blocks_out[(page - 1) * page_size : page * page_size]
    return paginated, total


def verify_chain_integrity() -> ChainVerifyResult:
    """Verify blockchain integrity."""
    result = verify_chain()
    return ChainVerifyResult(
        is_valid=result["is_valid"],
        total_blocks=result["total_blocks"],
        checked_blocks=result["checked_blocks"],
        invalid_blocks=result["invalid_blocks"],
    )
