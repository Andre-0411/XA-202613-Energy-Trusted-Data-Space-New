"""
区块链存证服务
8 节点证据链: 收集→预处理→分类→发布→申请→计算→结果→结算
通过 UsageLogger 合约实现链式哈希存证

增强功能:
- 批量存证提交
- RFC3161 时间戳服务
- PDF 导出
"""
import asyncio
import uuid
import time
import io
import json
import logging
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blockchain import EvidenceRecord, BlockchainTransaction
from app.core.fisco_client import fisco_client
from app.core.contract_registry import get_contract_registry
from app.core.gmssl_adapter import gmssl_adapter
from app.exceptions import EvidenceError, DataNotFoundError
from app.schemas.blockchain import (
    EvidenceCreate, EvidenceResponse, EvidenceBatchSubmit,
    EvidenceBatchResult, TimestampResponse,
)

logger = logging.getLogger(__name__)

# 全链路证据链节点类型 (12 节点完整覆盖)
EVIDENCE_NODE_TYPES = [
    "collect",       # 采集
    "preprocess",    # 预处理
    "classify",      # 分类分级
    "publish",       # 发布至目录
    "apply",         # 使用申请
    "approve",       # 审批
    "compute",       # 可信计算
    "result",        # 计算结果
    "export",        # 数据导出
    "settle",        # 链上结算
    "destroy",       # 数据销毁
    "audit",         # 审计追溯
]


def _bytes_to_hex(data: str) -> str:
    """将字符串转为 bytes32 十六进制表示（使用 SM3 国密哈希）"""
    if data.startswith("0x") and len(data) == 66:
        return data
    h = gmssl_adapter.sm3_hash(data)
    return f"0x{h}"


async def submit_evidence(
    db: AsyncSession,
    request: EvidenceCreate,
) -> EvidenceResponse:
    """
    提交存证（增强版：支持链式哈希）

    流程:
    1. 校验节点类型
    2. 计算前序哈希 (prev_hash) 和链式哈希 (chain_hash)
    3. 调用 UsageLogger 合约 logUsage 方法
    4. 记录存证与交易
    """
    # 1. 校验节点类型
    if request.node_type not in EVIDENCE_NODE_TYPES:
        raise EvidenceError(f"无效的存证节点类型: {request.node_type}，允许值: {EVIDENCE_NODE_TYPES}")

    # 2. 计算链式哈希
    prev_hash = None
    chain_hash = None
    try:
        # 查询该资源的最新存证记录
        latest_result = await db.execute(
            select(EvidenceRecord)
            .where(EvidenceRecord.resource_id == uuid.UUID(request.resource_id))
            .order_by(EvidenceRecord.timestamp.desc())
            .limit(1)
        )
        latest_record = latest_result.scalar_one_or_none()
        if latest_record:
            prev_hash = latest_record.chain_hash or latest_record.data_hash
            # chain_hash = SM3(prev_hash + current_data_hash)
            chain_hash = gmssl_adapter.sm3_hash(f"{prev_hash}:{request.data_hash}")
        else:
            # 第一条记录，chain_hash = data_hash
            chain_hash = request.data_hash
    except Exception as e:
        logger.warning(f"Chain hash computation failed: {e}")
        chain_hash = request.data_hash

    # 3. 链上存证 - 优先使用 UsageLogger 合约
    tx_hash = ""
    block_number = None

    registry = get_contract_registry()
    usage_logger_info = registry.get_contract("UsageLogger")

    if usage_logger_info and usage_logger_info.abi:
        from app.core.fisco_web3_client import get_fisco_client
        web3_client = get_fisco_client()
        if web3_client.is_connected:
            try:
                # 将 data_hash 转为 bytes32
                data_hash_bytes = bytes.fromhex(request.data_hash.replace("0x", "")) if request.data_hash else b'\x00' * 32
                if len(data_hash_bytes) < 32:
                    data_hash_bytes = data_hash_bytes.ljust(32, b'\x00')
                data_hash_b32 = bytes(data_hash_bytes[:32])

                # evidence_data 编码为 bytes
                evidence_bytes = request.evidence_data.encode("utf-8") if isinstance(request.evidence_data, str) else str(request.evidence_data).encode("utf-8")

                receipt = await asyncio.to_thread(
                    web3_client.send_transaction,
                    address=usage_logger_info.address,
                    abi=usage_logger_info.abi,
                    method="logUsage",
                    args=[
                        request.node_type,
                        request.resource_id,
                        request.resource_type,
                        data_hash_b32,
                        evidence_bytes,
                    ],
                )
                tx_hash = receipt.get("tx_hash", "")
                block_number = receipt.get("block_number")
            except Exception as e:
                logger.warning(f"UsageLogger contract call failed, falling back: {e}")

    # 回退到原有 fisco_client
    if not tx_hash:
        try:
            chain_result = await fisco_client.submit_evidence({
                "nodeType": request.node_type,
                "resourceId": request.resource_id,
                "resourceType": request.resource_type,
                "dataHash": request.data_hash,
                "evidenceData": request.evidence_data,
            })
            tx_hash = chain_result.get("transactionHash", "")
            block_number = chain_result.get("blockNumber")
        except Exception as e:
            logger.error(f"Evidence chain call failed: {e}")
            raise EvidenceError(f"链上存证失败: {e}")

    # 4. 记录存证（含链式哈希）
    evidence = EvidenceRecord(
        node_type=request.node_type,
        resource_id=uuid.UUID(request.resource_id),
        resource_type=request.resource_type,
        data_hash=request.data_hash,
        schema_version="v1.0",
        evidence_data=request.evidence_data,
        tx_hash=tx_hash,
        block_number=block_number,
        timestamp=int(time.time()),
        prev_hash=prev_hash,
        chain_hash=chain_hash,
        operator_did=request.operator_did,
        operator_signature=request.operator_signature,
    )
    db.add(evidence)

    # 5. 记录交易
    tx_record = BlockchainTransaction(
        tx_hash=tx_hash,
        contract_address=usage_logger_info.address if usage_logger_info else "UsageLogger",
        method="logUsage",
        params={
            "nodeType": request.node_type,
            "resourceId": request.resource_id,
            "dataHash": request.data_hash,
            "chainHash": chain_hash,
        },
        block_number=block_number,
        status="confirmed",
    )
    db.add(tx_record)
    await db.commit()
    await db.refresh(evidence)

    return EvidenceResponse.model_validate(evidence)


async def get_evidence(
    db: AsyncSession,
    evidence_id: str,
) -> EvidenceResponse:
    """查询存证记录"""
    result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == uuid.UUID(evidence_id))
    )
    evidence = result.scalar_one_or_none()
    if not evidence:
        raise DataNotFoundError("存证记录未找到")
    return EvidenceResponse.model_validate(evidence)


async def get_evidence_chain(
    db: AsyncSession,
    resource_id: str,
    resource_type: Optional[str] = None,
) -> list[EvidenceResponse]:
    """
    查询资源的完整证据链

    按 8 节点顺序排列，展示从采集到结算的全链路
    """
    query = select(EvidenceRecord).where(
        EvidenceRecord.resource_id == uuid.UUID(resource_id)
    )
    if resource_type:
        query = query.where(EvidenceRecord.resource_type == resource_type)

    # 按证据链节点顺序排序
    result = await db.execute(query)
    records = result.scalars().all()

    # 按 EVIDENCE_NODE_TYPES 顺序排序
    type_order = {t: i for i, t in enumerate(EVIDENCE_NODE_TYPES)}
    records_sorted = sorted(records, key=lambda r: type_order.get(r.node_type, 99))

    return [EvidenceResponse.model_validate(r) for r in records_sorted]


async def verify_evidence(
    db: AsyncSession,
    evidence_id: str,
) -> dict:
    """
    验证存证完整性

    1. 从数据库获取存证记录
    2. 从链上获取对应交易回执
    3. 比对数据哈希
    """
    result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == uuid.UUID(evidence_id))
    )
    evidence = result.scalar_one_or_none()
    if not evidence:
        raise DataNotFoundError("存证记录未找到")

    # 从链上验证
    chain_confirmed = False
    try:
        from app.core.fisco_web3_client import get_fisco_client
        web3_client = get_fisco_client()
        if web3_client.is_connected:
            receipt = await asyncio.to_thread(
                web3_client.get_transaction_receipt, evidence.tx_hash
            )
            chain_confirmed = receipt.get("status") == 1
        else:
            receipt = await fisco_client.get_transaction_receipt(evidence.tx_hash)
            chain_confirmed = receipt.get("status") == "0x0"
    except Exception as e:
        logger.warning(f"Chain verification failed: {e}")

    # 重新计算哈希
    computed_hash = gmssl_adapter.sm3_hash(str(evidence.evidence_data))
    hash_match = computed_hash == evidence.data_hash

    return {
        "evidence_id": evidence_id,
        "tx_hash": evidence.tx_hash,
        "chain_confirmed": chain_confirmed,
        "hash_match": hash_match,
        "computed_hash": computed_hash,
        "stored_hash": evidence.data_hash,
        "is_valid": chain_confirmed and hash_match,
    }


async def get_evidence_chain_from_chain(
    resource_id: str,
) -> dict:
    """
    从链上直接查询资源的存证记录列表

    通过 UsageLogger 合约的 getRecordsByResource 方法查询
    """
    registry = get_contract_registry()
    usage_logger_info = registry.get_contract("UsageLogger")

    if not usage_logger_info or not usage_logger_info.abi:
        raise EvidenceError("UsageLogger 合约未部署")

    from app.core.fisco_web3_client import get_fisco_client
    web3_client = get_fisco_client()

    if not web3_client.is_connected:
        raise EvidenceError("未连接到区块链节点")

    try:
        record_ids = await asyncio.to_thread(
            web3_client.call_contract,
            address=usage_logger_info.address,
            abi=usage_logger_info.abi,
            method="getRecordsByResource",
            args=[resource_id],
        )

        # 获取每条记录详情
        records = []
        for record_id in record_ids:
            try:
                record = await asyncio.to_thread(
                    web3_client.call_contract,
                    address=usage_logger_info.address,
                    abi=usage_logger_info.abi,
                    method="getRecord",
                    args=[record_id],
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to get record {record_id.hex()}: {e}")

        return {
            "resource_id": resource_id,
            "record_count": len(records),
            "records": records,
        }
    except Exception as e:
        logger.error(f"Chain evidence query failed: {e}")
        raise EvidenceError(f"链上存证查询失败: {e}")


# ==================== 链式哈希验证 ====================


async def verify_evidence_chain_hash(
    db: AsyncSession,
    resource_id: str,
    resource_type: Optional[str] = None,
) -> dict:
    """
    验证资源证据链的链式哈希完整性

    检查每条记录的 prev_hash 是否指向前一条记录的 chain_hash/data_hash。

    Args:
        db: 异步数据库会话
        resource_id: 资源 ID
        resource_type: 资源类型（可选过滤）

    Returns:
        验证结果
    """
    chain = await get_evidence_chain(db, resource_id, resource_type)

    if not chain:
        return {
            "resource_id": resource_id,
            "chain_length": 0,
            "is_valid": True,
            "invalid_nodes": [],
            "chain_records": [],
        }

    invalid_nodes = []
    for i in range(1, len(chain)):
        current = chain[i]
        previous = chain[i - 1]

        # 前一条的 chain_hash 或 data_hash
        expected_prev = previous.chain_hash or previous.data_hash
        if current.prev_hash and current.prev_hash != expected_prev:
            invalid_nodes.append({
                "index": i,
                "evidence_id": current.id,
                "node_type": current.node_type,
                "expected_prev_hash": expected_prev,
                "actual_prev_hash": current.prev_hash,
                "error": "prev_hash 不匹配",
            })

    return {
        "resource_id": resource_id,
        "chain_length": len(chain),
        "is_valid": len(invalid_nodes) == 0,
        "invalid_nodes": invalid_nodes,
        "chain_records": chain,
    }


# ==================== 增强功能 ====================


async def batch_submit_evidence(
    db: AsyncSession,
    batch_request: EvidenceBatchSubmit,
) -> EvidenceBatchResult:
    """
    批量存证提交

    批量处理多条存证请求，每条独立执行链上存证。
    部分失败不影响其他记录。

    Args:
        db: 异步数据库会话
        batch_request: 批量存证请求

    Returns:
        批量存证结果，包含成功/失败统计和每条记录的详情
    """
    total: int = len(batch_request.items)
    success_count: int = 0
    failure_count: int = 0
    results: list[dict] = []

    for idx, item in enumerate(batch_request.items):
        try:
            result = await submit_evidence(db=db, request=item)
            success_count += 1
            results.append({
                "index": idx,
                "status": "success",
                "evidence_id": result.id,
                "tx_hash": result.tx_hash,
                "node_type": item.node_type,
                "resource_id": item.resource_id,
            })
        except Exception as e:
            failure_count += 1
            logger.error(f"Batch evidence submit failed at index {idx}: {e}")
            results.append({
                "index": idx,
                "status": "failed",
                "error": str(e),
                "node_type": item.node_type,
                "resource_id": item.resource_id,
            })

    return EvidenceBatchResult(
        total=total,
        success_count=success_count,
        failure_count=failure_count,
        results=results,
    )


async def get_timestamp_service(
    db: AsyncSession,
    evidence_id: str,
) -> TimestampResponse:
    """
    存证时间戳服务（RFC3161 风格）

    为指定存证记录生成可信时间戳证明，包含:
    - 存证创建时间
    - 链上区块时间和区块高度
    - SM3 时间戳哈希（TSA 印章）
    - 验证状态

    Args:
        db: 异步数据库会话
        evidence_id: 存证记录 ID

    Returns:
        时间戳响应
    """
    result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.id == uuid.UUID(evidence_id))
    )
    evidence = result.scalar_one_or_none()
    if not evidence:
        raise DataNotFoundError("存证记录未找到")

    # 获取链上区块时间
    chain_time: Optional[str] = None
    block_number: Optional[int] = evidence.block_number

    if block_number:
        try:
            from app.core.fisco_web3_client import get_fisco_client
            web3_client = get_fisco_client()
            if web3_client.is_connected:
                block_data = await asyncio.to_thread(
                    web3_client.get_block_by_number, block_number
                )
                if block_data and "timestamp" in block_data:
                    ts = block_data["timestamp"]
                    if isinstance(ts, str):
                        ts = int(ts, 16) if ts.startswith("0x") else int(ts)
                    chain_time = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except Exception as e:
            logger.warning(f"Failed to get block timestamp: {e}")

    # 生成 TSA 印章哈希
    tsa_input = json.dumps({
        "evidence_id": evidence_id,
        "tx_hash": evidence.tx_hash,
        "block_number": evidence.block_number,
        "data_hash": evidence.data_hash,
        "timestamp": evidence.timestamp,
    }, sort_keys=True)
    tsa_hash: str = gmssl_adapter.sm3_hash(tsa_input)

    # 验证状态
    verification = await verify_evidence(db=db, evidence_id=evidence_id)

    return TimestampResponse(
        evidence_id=evidence_id,
        tx_hash=evidence.tx_hash,
        block_number=evidence.block_number,
        evidence_timestamp=evidence.timestamp,
        chain_timestamp=chain_time,
        tsa_hash=tsa_hash,
        tsa_version="v1.0",
        is_valid=verification.get("is_valid", False),
        chain_confirmed=verification.get("chain_confirmed", False),
        hash_match=verification.get("hash_match", False),
    )


async def export_evidence_pdf(
    db: AsyncSession,
    evidence_id: str,
) -> bytes:
    """
    导出存证报告为 PDF

    生成包含以下内容的 PDF 文件:
    - 存证基本信息
    - 数据哈希和区块链信息
    - 证据链溯源
    - 验证结果
    - 时间戳证明

    Args:
        db: 异步数据库会话
        evidence_id: 存证记录 ID

    Returns:
        PDF 文件字节数据

    Raises:
        DataNotFoundError: 存证记录不存在
        EvidenceError: PDF 生成失败
    """
    # 1. 获取存证详情
    evidence = await get_evidence(db=db, evidence_id=evidence_id)

    # 2. 获取证据链
    chain: list[EvidenceResponse] = []
    try:
        chain = await get_evidence_chain(
            db=db,
            resource_id=str(evidence.resource_id),
        )
    except Exception as e:
        logger.warning(f"Failed to get evidence chain for PDF export: {e}")

    # 3. 验证存证
    verification: dict = {}
    try:
        verification = await verify_evidence(db=db, evidence_id=evidence_id)
    except Exception as e:
        logger.warning(f"Failed to verify evidence for PDF export: {e}")

    # 4. 获取时间戳
    timestamp_info: Optional[TimestampResponse] = None
    try:
        timestamp_info = await get_timestamp_service(db=db, evidence_id=evidence_id)
    except Exception as e:
        logger.warning(f"Failed to get timestamp for PDF export: {e}")

    # 5. 生成 PDF（使用 reportlab，如果不可用则降级为 HTML）
    try:
        return _generate_evidence_pdf(
            evidence=evidence,
            chain=chain,
            verification=verification,
            timestamp_info=timestamp_info,
        )
    except ImportError:
        logger.warning("reportlab not available, generating HTML report instead")
        return _generate_evidence_html_bytes(
            evidence=evidence,
            chain=chain,
            verification=verification,
            timestamp_info=timestamp_info,
        )


def _generate_evidence_pdf(
    evidence: EvidenceResponse,
    chain: list[EvidenceResponse],
    verification: dict,
    timestamp_info: Optional[TimestampResponse],
) -> bytes:
    """
    使用 reportlab 生成存证 PDF

    Args:
        evidence: 存证响应
        chain: 证据链列表
        verification: 验证结果
        timestamp_info: 时间戳信息

    Returns:
        PDF 字节数据
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # 尝试注册中文字体
    _register_chinese_font()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    # 自定义样式
    title_style = ParagraphStyle(
        "EvidenceTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "EvidenceHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
    )
    normal_style = styles["Normal"]

    elements: list = []

    # 标题
    elements.append(Paragraph("Blockchain Evidence Report", title_style))
    elements.append(Paragraph("区块链存证报告", title_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 8 * mm))

    # 基本信息表
    elements.append(Paragraph("Evidence Details / 存证信息", heading_style))
    basic_data = [
        ["Evidence ID", evidence.id],
        ["Node Type", evidence.node_type],
        ["Resource ID", str(evidence.resource_id)],
        ["Resource Type", evidence.resource_type],
        ["Data Hash (SM3)", evidence.data_hash],
        ["Schema Version", evidence.schema_version],
        ["Tx Hash", evidence.tx_hash],
        ["Block Number", str(evidence.block_number) if evidence.block_number else "N/A"],
        ["Timestamp", str(evidence.timestamp)],
        ["Created At", str(evidence.created_at)],
    ]
    basic_table = Table(basic_data, colWidths=[120, 340])
    basic_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP", (0, 0), (-1, -1), True),
    ]))
    elements.append(basic_table)
    elements.append(Spacer(1, 6 * mm))

    # 验证结果
    elements.append(Paragraph("Verification Result / 验证结果", heading_style))
    if verification:
        verify_data = [
            ["Chain Confirmed", "Yes" if verification.get("chain_confirmed") else "No"],
            ["Hash Match", "Yes" if verification.get("hash_match") else "No"],
            ["Is Valid", "Yes" if verification.get("is_valid") else "No"],
            ["Computed Hash", verification.get("computed_hash", "N/A")],
            ["Stored Hash", verification.get("stored_hash", "N/A")],
        ]
        verify_table = Table(verify_data, colWidths=[120, 340])
        verify_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(verify_table)
    else:
        elements.append(Paragraph("Verification data not available", normal_style))
    elements.append(Spacer(1, 6 * mm))

    # 时间戳证明
    if timestamp_info:
        elements.append(Paragraph("Timestamp Attestation / 时间戳证明", heading_style))
        ts_data = [
            ["TSA Hash", timestamp_info.tsa_hash],
            ["TSA Version", timestamp_info.tsa_version],
            ["Evidence Timestamp", str(timestamp_info.evidence_timestamp)],
            ["Chain Timestamp", str(timestamp_info.chain_timestamp) if timestamp_info.chain_timestamp else "N/A"],
            ["Block Number", str(timestamp_info.block_number) if timestamp_info.block_number else "N/A"],
        ]
        ts_table = Table(ts_data, colWidths=[120, 340])
        ts_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        elements.append(ts_table)
        elements.append(Spacer(1, 6 * mm))

    # 证据链
    if chain:
        elements.append(Paragraph("Evidence Chain / 证据链", heading_style))
        chain_data = [["#", "Node Type", "Resource ID", "Tx Hash", "Timestamp"]]
        for i, item in enumerate(chain):
            chain_data.append([
                str(i + 1),
                item.node_type,
                str(item.resource_id)[:16] + "...",
                item.tx_hash[:16] + "..." if item.tx_hash else "N/A",
                str(item.timestamp),
            ])
        chain_table = Table(chain_data, colWidths=[25, 80, 100, 130, 100])
        chain_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ]))
        elements.append(chain_table)

    # 页脚
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    footer_text = (
        f"Generated at {datetime.now(timezone.utc).isoformat()} | "
        f"Energy Trusted Data Space | Blockchain Evidence Service"
    )
    elements.append(Paragraph(footer_text, ParagraphStyle("Footer", fontSize=8, textColor=colors.grey)))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _register_chinese_font() -> None:
    """注册中文字体（如果可用），注册失败不影响默认字体"""
    import os
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simsun.ttc",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
                return
            except Exception:
                continue


def _generate_evidence_html_bytes(
    evidence: EvidenceResponse,
    chain: list[EvidenceResponse],
    verification: dict,
    timestamp_info: Optional[TimestampResponse],
) -> bytes:
    """
    降级方案：生成 HTML 格式的存证报告（当 reportlab 不可用时）

    Args:
        evidence: 存证响应
        chain: 证据链列表
        verification: 验证结果
        timestamp_info: 时间戳信息

    Returns:
        HTML 字节数据
    """
    chain_rows = ""
    for i, item in enumerate(chain):
        chain_rows += (
            f"<tr><td>{i + 1}</td><td>{item.node_type}</td>"
            f"<td>{str(item.resource_id)[:20]}...</td>"
            f"<td>{item.tx_hash[:20]}...</td>"
            f"<td>{item.timestamp}</td></tr>\n"
        )

    verify_status = "PASS" if verification.get("is_valid") else "FAIL"
    verify_color = "#28a745" if verification.get("is_valid") else "#dc3545"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Blockchain Evidence Report</title>
<style>
body {{ font-family: sans-serif; margin: 20px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }}
th {{ background: #4472C4; color: white; }}
.label {{ background: #f0f0f0; font-weight: bold; width: 160px; }}
h1 {{ color: #333; border-bottom: 2px solid #4472C4; padding-bottom: 8px; }}
.status {{ display: inline-block; padding: 4px 12px; border-radius: 4px; color: white; background: {verify_color}; }}
</style></head><body>
<h1>Blockchain Evidence Report / 区块链存证报告</h1>
<h2>Evidence Details / 存证信息</h2>
<table>
<tr><td class="label">Evidence ID</td><td>{evidence.id}</td></tr>
<tr><td class="label">Node Type</td><td>{evidence.node_type}</td></tr>
<tr><td class="label">Resource ID</td><td>{evidence.resource_id}</td></tr>
<tr><td class="label">Resource Type</td><td>{evidence.resource_type}</td></tr>
<tr><td class="label">Data Hash (SM3)</td><td>{evidence.data_hash}</td></tr>
<tr><td class="label">Tx Hash</td><td>{evidence.tx_hash}</td></tr>
<tr><td class="label">Block Number</td><td>{evidence.block_number or 'N/A'}</td></tr>
<tr><td class="label">Timestamp</td><td>{evidence.timestamp}</td></tr>
<tr><td class="label">Created At</td><td>{evidence.created_at}</td></tr>
</table>

<h2>Verification Result / 验证结果</h2>
<table>
<tr><td class="label">Status</td><td><span class="status">{verify_status}</span></td></tr>
<tr><td class="label">Chain Confirmed</td><td>{'Yes' if verification.get('chain_confirmed') else 'No'}</td></tr>
<tr><td class="label">Hash Match</td><td>{'Yes' if verification.get('hash_match') else 'No'}</td></tr>
<tr><td class="label">Computed Hash</td><td>{verification.get('computed_hash', 'N/A')}</td></tr>
</table>"""

    if timestamp_info:
        html += f"""
<h2>Timestamp Attestation / 时间戳证明</h2>
<table>
<tr><td class="label">TSA Hash</td><td>{timestamp_info.tsa_hash}</td></tr>
<tr><td class="label">TSA Version</td><td>{timestamp_info.tsa_version}</td></tr>
<tr><td class="label">Evidence Timestamp</td><td>{timestamp_info.evidence_timestamp}</td></tr>
<tr><td class="label">Chain Timestamp</td><td>{timestamp_info.chain_timestamp or 'N/A'}</td></tr>
</table>"""

    if chain:
        html += f"""
<h2>Evidence Chain / 证据链</h2>
<table>
<tr><th>#</th><th>Node Type</th><th>Resource ID</th><th>Tx Hash</th><th>Timestamp</th></tr>
{chain_rows}
</table>"""

    html += f"""
<hr><p style="font-size:11px;color:#888;">
Generated at {datetime.now(timezone.utc).isoformat()} |
Energy Trusted Data Space | Blockchain Evidence Service
</p></body></html>"""

    return html.encode("utf-8")
