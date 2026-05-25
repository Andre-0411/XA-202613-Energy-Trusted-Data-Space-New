"""
存证 API — /api/v1/blockchain/evidence
证据提交 / 批量提交 / 查询 / 溯源 / 验证 / 时间戳 / PDF导出
"""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.blockchain import EvidenceRecord
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.blockchain import (
    EvidenceCreate, EvidenceResponse, EvidenceBatchSubmit,
    EvidenceBatchResult, TimestampResponse, ChainVerificationResponse,
)
from app.utils.deps import get_current_user
from app.services.blockchain_evidence_service import (
    submit_evidence, get_evidence, get_evidence_chain, verify_evidence,
    batch_submit_evidence, get_timestamp_service, export_evidence_pdf,
    verify_evidence_chain_hash,
)
from app.exceptions import EvidenceError, DataNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()


# evidence_type → node_type 映射表
EVIDENCE_TYPE_MAP: dict[str, str] = {
    "data_source": "collect",
    "data_collection": "collect",
    "data_preprocess": "preprocess",
    "data_classify": "classify",
    "data_publish": "publish",
    "data_apply": "apply",
    "data_compute": "compute",
    "data_result": "result",
    "data_settle": "settle",
}


@router.get("", response_model=ApiResponse[PaginatedResponse[EvidenceResponse]])
async def list_evidence(
    node_type: Optional[str] = Query(None, description="节点类型"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """存证记录列表"""
    from app.utils.deps import get_pagination_params, PaginationParams
    from app.utils.pagination import paginate_query
    params = PaginationParams(page=1, page_size=20)
    query = select(EvidenceRecord).order_by(EvidenceRecord.created_at.desc())
    if node_type:
        query = query.where(EvidenceRecord.node_type == node_type)
    if resource_type:
        query = query.where(EvidenceRecord.resource_type == resource_type)
    result = await paginate_query(db, query, params, EvidenceResponse)
    return ApiResponse(data=result)


@router.get("/trace", response_model=ApiResponse[list[EvidenceResponse]])
async def 溯源查询_by_hash(
    hash: str = Query(..., description="存证哈希值"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """溯源查询 — 按 hash 查找完整证据链 /trace?hash=xxx"""
    # 按 data_hash 或 resource_id 查找
    conditions = [EvidenceRecord.data_hash == hash]
    try:
        resource_uuid = uuid.UUID(hash)
        conditions.append(EvidenceRecord.resource_id == resource_uuid)
    except ValueError:
        pass

    result = await db.execute(
        select(EvidenceRecord).where(or_(*conditions))
    )
    evidence = result.scalars().first()

    if not evidence:
        # 也尝试用 hash 生成 resource_id 来查找
        generated_resource_id = str(uuid.uuid5(uuid.NAMESPACE_OID, hash))
        result2 = await db.execute(
            select(EvidenceRecord).where(
                EvidenceRecord.resource_id == uuid.UUID(generated_resource_id)
            )
        )
        evidence = result2.scalars().first()

    if not evidence:
        return ApiResponse(code=2001, message="未找到对应存证记录", data=None)

    try:
        chain = await get_evidence_chain(
            db=db,
            resource_id=str(evidence.resource_id),
            resource_type=evidence.resource_type if hasattr(evidence, "resource_type") else None,
        )
        return ApiResponse(data=chain)
    except Exception as e:
        logger.error(f"Evidence chain query failed: {e}")
        return ApiResponse(code=4020, message=f"证据链查询失败: {e}", data=None)


@router.post("", response_model=ApiResponse[EvidenceResponse])
async def 提交存证(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """提交存证 — 前端发送 {evidence_hash, evidence_type, description}"""
    evidence_hash: str = body.get("evidence_hash", "")
    evidence_type: str = body.get("evidence_type", "")
    description: str = body.get("description", "")

    if not evidence_hash or not evidence_type:
        return ApiResponse(code=2003, message="evidence_hash 和 evidence_type 为必填项", data=None)

    # evidence_type → node_type 映射，未匹配则原值传入
    node_type: str = EVIDENCE_TYPE_MAP.get(evidence_type, evidence_type)

    # 用 evidence_hash 生成确定性的 resource_id
    resource_id: str = str(uuid.uuid5(uuid.NAMESPACE_OID, evidence_hash))

    evidence_create = EvidenceCreate(
        node_type=node_type,
        resource_id=resource_id,
        resource_type=evidence_type,
        data_hash=evidence_hash,
        evidence_data=body,  # 完整请求体作为存证数据
    )

    try:
        result = await submit_evidence(db=db, request=evidence_create)
        return ApiResponse(data=result)
    except EvidenceError as e:
        logger.error(f"Evidence submit failed: {e}")
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error(f"Evidence submit failed: {e}")
        return ApiResponse(code=4020, message=f"存证提交失败: {e}", data=None)


@router.post("/batch", response_model=ApiResponse[EvidenceBatchResult])
async def 批量提交存证(
    body: EvidenceBatchSubmit,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """批量存证提交 — 一次提交多条存证，部分失败不影响其他记录"""
    try:
        result = await batch_submit_evidence(db=db, batch_request=body)
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"Batch evidence submit failed: {e}")
        return ApiResponse(code=4020, message=f"批量存证失败: {e}", data=None)


@router.get("/{evidence_id}", response_model=ApiResponse[EvidenceResponse])
async def 存证详情(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """存证详情 — 按 evidence_id 查询"""
    try:
        result = await get_evidence(db=db, evidence_id=evidence_id)
        return ApiResponse(data=result)
    except DataNotFoundError:
        return ApiResponse(code=2001, message="存证记录未找到", data=None)
    except Exception as e:
        logger.warning(f"Evidence not found: {e}")
        return ApiResponse(code=2001, message="存证记录未找到", data=None)


@router.get("/{evidence_id}/verify", response_model=ApiResponse)
async def 验证存证(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """验证存证完整性 — 比对链上数据与数据库记录"""
    try:
        result = await verify_evidence(db=db, evidence_id=evidence_id)
        return ApiResponse(data=result)
    except DataNotFoundError:
        return ApiResponse(code=2001, message="存证记录未找到", data=None)
    except Exception as e:
        logger.error(f"Evidence verify failed: {e}")
        return ApiResponse(code=4020, message=f"存证验证失败: {e}", data=None)


@router.get("/{evidence_id}/timestamp", response_model=ApiResponse[TimestampResponse])
async def 存证时间戳(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """存证时间戳服务 — 获取 RFC3161 风格的可信时间戳证明"""
    try:
        result = await get_timestamp_service(db=db, evidence_id=evidence_id)
        return ApiResponse(data=result)
    except DataNotFoundError:
        return ApiResponse(code=2001, message="存证记录未找到", data=None)
    except Exception as e:
        logger.error(f"Timestamp service failed: {e}")
        return ApiResponse(code=4020, message=f"时间戳服务失败: {e}", data=None)


@router.get("/{evidence_id}/export")
async def 导出存证报告(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """导出存证报告为 PDF — 包含完整证据链、验证结果和时间戳"""
    try:
        pdf_bytes = await export_evidence_pdf(db=db, evidence_id=evidence_id)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="evidence_{evidence_id}.pdf"'
            },
        )
    except DataNotFoundError:
        return ApiResponse(code=2001, message="存证记录未找到", data=None)
    except Exception as e:
        logger.error(f"Evidence PDF export failed: {e}")
        return ApiResponse(code=4020, message=f"PDF 导出失败: {e}", data=None)


@router.get("", response_model=ApiResponse[PaginatedResponse[EvidenceResponse]])
async def 存证列表(
    evidence_type: Optional[str] = Query(None, description="存证类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """存证列表 — 按 evidence_type 筛选，分页"""
    query = select(EvidenceRecord)

    if evidence_type:
        node_type = EVIDENCE_TYPE_MAP.get(evidence_type, evidence_type)
        query = query.where(EvidenceRecord.node_type == node_type)

    query = query.order_by(EvidenceRecord.created_at.desc())

    # 计算总数
    from sqlalchemy import func
    count_query = query.with_only_columns(func.count()).order_by(None)
    total_result = await db.execute(count_query)
    total: int = total_result.scalar() or 0

    # 分页
    offset: int = (page - 1) * page_size
    page_query = query.offset(offset).limit(page_size)
    page_result = await db.execute(page_query)
    records = page_result.scalars().all()

    total_pages: int = (total + page_size - 1) // page_size if page_size > 0 else 0
    items = [EvidenceResponse.model_validate(r) for r in records]

    return ApiResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/chain/{resource_id}", response_model=ApiResponse)
async def get_evidence_chain_by_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """获取资源的完整证据链"""
    try:
        chain = await get_evidence_chain(
            db=db,
            resource_id=resource_id,
        )
        return ApiResponse(data={
            "resource_id": resource_id,
            "total_records": len(chain),
            "chain_valid": True,
            "records": chain,
        })
    except Exception as e:
        logger.error(f"Evidence chain query failed: {e}")
        return ApiResponse(code=4020, message=f"证据链查询失败: {e}", data=None)


@router.post("/chain/{resource_id}/verify", response_model=ApiResponse)
async def verify_evidence_chain(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """验证资源证据链完整性"""
    try:
        chain = await get_evidence_chain(
            db=db,
            resource_id=resource_id,
        )
        if not chain:
            return ApiResponse(code=2001, message="未找到证据链记录", data=None)

        # 验证每个存证记录
        verification_results = []
        for evidence in chain:
            try:
                result = await verify_evidence(db=db, evidence_id=evidence.id)
                verification_results.append(result)
            except Exception as e:
                verification_results.append({
                    "evidence_id": evidence.id,
                    "is_valid": False,
                    "error": str(e),
                })

        all_valid = all(r.get("is_valid", False) for r in verification_results)

        return ApiResponse(data={
            "resource_id": resource_id,
            "total_records": len(chain),
            "chain_valid": all_valid,
            "verification_results": verification_results,
        })
    except Exception as e:
        logger.error(f"Evidence chain verification failed: {e}")
        return ApiResponse(code=4020, message=f"证据链验证失败: {e}", data=None)


@router.post("/chain/{resource_id}/verify-hash", response_model=ApiResponse[ChainVerificationResponse])
async def verify_chain_hash(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """验证资源证据链的链式哈希完整性（prev_hash → chain_hash 链）"""
    try:
        result = await verify_evidence_chain_hash(db=db, resource_id=resource_id)
        return ApiResponse(data=ChainVerificationResponse(**result))
    except Exception as e:
        logger.error(f"Chain hash verification failed: {e}")
        return ApiResponse(code=4020, message=f"链式哈希验证失败: {e}", data=None)
