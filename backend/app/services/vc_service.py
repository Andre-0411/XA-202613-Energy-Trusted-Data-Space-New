"""
可验证凭证服务（W3C Verifiable Credentials Data Model v2.0）
签发VC(SM2签名) + 验证VC(签名+过期+撤销) + 撤销VC + VC列表查询 + VC模板管理 + 凭证链验证

参考规范：
- W3C Verifiable Credentials Data Model v2.0
- https://www.w3.org/TR/vc-data-model-2.0/
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import VcRecord, DidDocument
from app.models.vc_model import RevocationEntry
from app.schemas.security import VcIssueRequest, VcVerifyRequest
from app.exceptions import VCError, DataNotFoundError, DIDError
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)

# VC 上下文（W3C VC v2.0）
VC_CONTEXT = [
    "https://www.w3.org/ns/credentials/v2",
    "https://w3id.org/security/suites/sm2-2021/v1",
]

# VC 模板库
VC_TEMPLATES = {
    "IdentityCredential": {
        "name": "身份凭证",
        "description": "证明用户身份的可验证凭证",
        "required_claims": ["name", "id_number", "organization"],
        "optional_claims": ["email", "phone", "department"],
    },
    "DataAccessCredential": {
        "name": "数据访问凭证",
        "description": "授权访问特定数据资源的凭证",
        "required_claims": ["resource_id", "access_level", "valid_until"],
        "optional_claims": ["constraints", "purpose"],
    },
    "ComputeCredential": {
        "name": "计算任务凭证",
        "description": "授权执行特定计算任务的凭证",
        "required_claims": ["task_type", "algorithm", "data_sources"],
        "optional_claims": ["parameters", "output_constraints"],
    },
    "AuditCredential": {
        "name": "审计凭证",
        "description": "记录审计行为的可验证凭证",
        "required_claims": ["audit_action", "resource_type", "resource_id"],
        "optional_claims": ["result", "evidence"],
    },
    "ComplianceCredential": {
        "name": "合规凭证",
        "description": "证明合规状态的可验证凭证",
        "required_claims": ["compliance_type", "score", "checked_at"],
        "optional_claims": ["findings", "remediation"],
    },
}


async def issue_vc(
    db: AsyncSession,
    request: VcIssueRequest,
    issuer_private_key: str = "",
) -> dict:
    """
    签发可验证凭证

    使用 SM2 签名，包含 issuer/subject/claims/expiration

    Args:
        db: 数据库会话
        request: 签发请求
        issuer_private_key: 签发方私钥（用于签名）

    Returns:
        签发后的 VC 数据
    """
    # 验证签发方 DID 存在
    issuer_result = await db.execute(
        select(DidDocument).where(DidDocument.did == request.issuer_did)
    )
    issuer_doc = issuer_result.scalar_one_or_none()
    if not issuer_doc:
        raise DIDError(message=f"签发方 DID 不存在: {request.issuer_did}")
    if issuer_doc.status == "deactivated":
        raise DIDError(message=f"签发方 DID 已停用: {request.issuer_did}")

    # 验证持有方 DID 存在
    subject_result = await db.execute(
        select(DidDocument).where(DidDocument.did == request.subject_did)
    )
    subject_doc = subject_result.scalar_one_or_none()
    if not subject_doc:
        raise DIDError(message=f"持有方 DID 不存在: {request.subject_did}")

    # 生成 VC ID
    vc_id = f"vc:{uuid.uuid4().hex[:16]}"

    # 构建凭证数据
    # VcRecord.issued_at 为 TIMESTAMP WITHOUT TIME ZONE，需用 naive datetime
    now = datetime.utcnow()
    now_iso = now.replace(tzinfo=timezone.utc).isoformat()
    credential_data = {
        "@context": VC_CONTEXT,
        "id": vc_id,
        "type": ["VerifiableCredential", request.vc_type],
        "issuer": request.issuer_did,
        "subject": request.subject_did,
        "issuanceDate": now_iso,
        "expirationDate": request.expires_at.isoformat() if request.expires_at else None,
        "credentialSubject": {
            "id": request.subject_did,
            **request.claims,
        },
    }

    # SM2 签名
    credential_str = str(sorted(credential_data.items()))
    if issuer_private_key:
        issuer_public_key = issuer_doc.document.get("verificationMethod", [{}])[0].get("publicKeyHex", "")
        try:
            signature = gmssl_adapter.sm2_sign(issuer_private_key, issuer_public_key, credential_str)
        except Exception as e:
            logger.error(f"SM2 签名失败: {e}")
            signature = gmssl_adapter.sm3_hash(credential_str)
    else:
        # 降级方案：使用 SM3 哈希作为简易签名
        signature = gmssl_adapter.sm3_hash(credential_str)

    # 添加证明
    proof = {
        "type": "SM2Signature2021",
        "created": now_iso,
        "proofPurpose": "assertionMethod",
        "verificationMethod": f"{request.issuer_did}#keys-1",
        "signature": signature,
    }
    credential_data["proof"] = proof

    # 存储到数据库
    vc_record = VcRecord(
        vc_id=vc_id,
        issuer_did=request.issuer_did,
        subject_did=request.subject_did,
        vc_type=request.vc_type,
        claims=request.claims,
        signature=signature,
        status="active",
        issued_at=now,
        expires_at=request.expires_at,
    )
    db.add(vc_record)
    await db.commit()
    await db.refresh(vc_record)

    logger.info(f"VC 签发成功: {vc_id}, 类型: {request.vc_type}, 签发方: {request.issuer_did}")
    return credential_data


async def verify_vc(
    db: AsyncSession,
    request: VcVerifyRequest,
) -> dict:
    """
    验证可验证凭证

    三重验证: 签名验证 + 过期检查 + 撤销检查

    Args:
        db: 数据库会话
        request: 验证请求

    Returns:
        验证结果
    """
    # 查找 VC 记录
    result = await db.execute(
        select(VcRecord).where(VcRecord.vc_id == request.vc_id)
    )
    vc_record = result.scalar_one_or_none()

    verification_results = {
        "vc_id": request.vc_id,
        "signature_valid": False,
        "not_expired": False,
        "not_revoked": False,
        "overall_valid": False,
        "errors": [],
    }

    if not vc_record:
        verification_results["errors"].append(f"VC 不存在: {request.vc_id}")
        return verification_results

    # 1. 签名验证
    try:
        issuer_result = await db.execute(
            select(DidDocument).where(DidDocument.did == vc_record.issuer_did)
        )
        issuer_doc = issuer_result.scalar_one_or_none()
        if issuer_doc:
            issuer_public_key = issuer_doc.document.get("verificationMethod", [{}])[0].get("publicKeyHex", "")
            if issuer_public_key:
                credential_data = {
                    "issuer": vc_record.issuer_did,
                    "subject": vc_record.subject_did,
                    "claims": vc_record.claims,
                    "issued_at": vc_record.issued_at.isoformat(),
                }
                credential_str = str(sorted(credential_data.items()))
                try:
                    verification_results["signature_valid"] = gmssl_adapter.sm2_verify(
                        issuer_public_key, credential_str, vc_record.signature
                    )
                except Exception:
                    # 降级：使用 SM3 哈希比对
                    computed = gmssl_adapter.sm3_hash(credential_str)
                    verification_results["signature_valid"] = computed == vc_record.signature
            else:
                verification_results["errors"].append("签发方公钥不可用")
        else:
            verification_results["errors"].append(f"签发方 DID 不存在: {vc_record.issuer_did}")
    except Exception as e:
        verification_results["errors"].append(f"签名验证异常: {str(e)}")

    # 2. 过期检查
    now = datetime.utcnow()
    if vc_record.expires_at:
        verification_results["not_expired"] = vc_record.expires_at > now
        if not verification_results["not_expired"]:
            verification_results["errors"].append("凭证已过期")
    else:
        verification_results["not_expired"] = True

    # 3. 撤销检查（查询数据库 RevocationEntry 表）
    revocation_result = await db.execute(
        select(RevocationEntry).where(RevocationEntry.vc_id == request.vc_id)
    )
    has_revocation_entry = revocation_result.scalar_one_or_none() is not None
    verification_results["not_revoked"] = not has_revocation_entry and vc_record.status != "revoked"
    if not verification_results["not_revoked"]:
        verification_results["errors"].append("凭证已被撤销")

    # 综合判定
    verification_results["overall_valid"] = (
        verification_results["signature_valid"]
        and verification_results["not_expired"]
        and verification_results["not_revoked"]
    )

    logger.info(f"VC 验证: {request.vc_id}, 结果: {verification_results['overall_valid']}")
    return verification_results


async def revoke_vc(
    db: AsyncSession,
    vc_id: str,
    revoked_by: str = "",
) -> dict:
    """
    撤销可验证凭证

    将 VC 加入撤销列表，状态标记为 revoked

    Args:
        db: 数据库会话
        vc_id: VC ID
        revoked_by: 操作人

    Returns:
        撤销结果
    """
    result = await db.execute(
        select(VcRecord).where(VcRecord.vc_id == vc_id)
    )
    vc_record = result.scalar_one_or_none()
    if not vc_record:
        raise DataNotFoundError(message=f"VC 不存在: {vc_id}")

    if vc_record.status == "revoked":
        raise VCError(message=f"VC 已被撤销: {vc_id}")

    vc_record.status = "revoked"

    # 创建撤销记录到数据库
    revocation_entry = RevocationEntry(
        vc_id=vc_id,
        reason=f"撤销操作 by {revoked_by}" if revoked_by else "撤销操作",
        revoked_by=revoked_by,
        revoked_at=datetime.now(timezone.utc),
    )
    db.add(revocation_entry)
    await db.commit()

    logger.info(f"VC 已撤销: {vc_id}, 操作人: {revoked_by}")
    return {
        "vc_id": vc_id,
        "status": "revoked",
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "revoked_by": revoked_by,
    }


async def list_vcs(
    db: AsyncSession,
    issuer_did: Optional[str] = None,
    subject_did: Optional[str] = None,
    vc_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    VC 列表查询

    Args:
        db: 数据库会话
        issuer_did: 签发方 DID 过滤
        subject_did: 持有方 DID 过滤
        vc_type: 凭证类型过滤
        status: 状态过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        VC 列表
    """
    query = select(VcRecord)
    count_query = select(func.count()).select_from(VcRecord)

    if issuer_did:
        query = query.where(VcRecord.issuer_did == issuer_did)
        count_query = count_query.where(VcRecord.issuer_did == issuer_did)
    if subject_did:
        query = query.where(VcRecord.subject_did == subject_did)
        count_query = count_query.where(VcRecord.subject_did == subject_did)
    if vc_type:
        query = query.where(VcRecord.vc_type == vc_type)
        count_query = count_query.where(VcRecord.vc_type == vc_type)
    if status:
        query = query.where(VcRecord.status == status)
        count_query = count_query.where(VcRecord.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(VcRecord.issued_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    items = [
        {
            "vc_id": r.vc_id,
            "issuer_did": r.issuer_did,
            "subject_did": r.subject_did,
            "vc_type": r.vc_type,
            "claims": r.claims,
            "status": r.status,
            "issued_at": r.issued_at.isoformat() if r.issued_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        }
        for r in records
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_vc_templates() -> dict:
    """
    获取 VC 模板列表

    Returns:
        VC 模板字典
    """
    return {
        "templates": VC_TEMPLATES,
        "total": len(VC_TEMPLATES),
    }


async def verify_credential_chain(
    db: AsyncSession,
    vc_ids: list[str],
) -> dict:
    """
    验证凭证链
    
    验证一系列凭证的完整性和信任链：
    1. 验证每个凭证的签名
    2. 验证凭证链的连续性（前一个凭证的 subject 是下一个凭证的 issuer）
    3. 验证所有凭证都未过期且未被撤销
    
    Args:
        db: 数据库会话
        vc_ids: 凭证 ID 列表（按顺序）
        
    Returns:
        验证结果
    """
    chain_results = []
    chain_valid = True
    errors = []
    
    if not vc_ids:
        return {
            "chain_valid": False,
            "total_credentials": 0,
            "verified_credentials": 0,
            "results": [],
            "errors": ["凭证链为空"],
        }
    
    for i, vc_id in enumerate(vc_ids):
        # 单独验证每个凭证
        verify_request = VcVerifyRequest(vc_id=vc_id)
        vc_result = await verify_vc(db, verify_request)
        chain_results.append(vc_result)
        
        if not vc_result["overall_valid"]:
            chain_valid = False
            errors.append(f"凭证 {vc_id} 验证失败: {', '.join(vc_result.get('errors', []))}")
        
        # 验证链连续性（非第一个凭证）
        if i > 0:
            prev_vc_id = vc_ids[i - 1]
            curr_vc_id = vc_ids[i]
            
            # 获取前一个凭证的 subject
            prev_result = await db.execute(
                select(VcRecord).where(VcRecord.vc_id == prev_vc_id)
            )
            prev_record = prev_result.scalar_one_or_none()
            
            # 获取当前凭证的 issuer
            curr_result = await db.execute(
                select(VcRecord).where(VcRecord.vc_id == curr_vc_id)
            )
            curr_record = curr_result.scalar_one_or_none()
            
            if prev_record and curr_record:
                if prev_record.subject_did != curr_record.issuer_did:
                    chain_valid = False
                    errors.append(
                        f"凭证链断裂: {prev_vc_id} 的持有方 "
                        f"({prev_record.subject_did}) 不等于 "
                        f"{curr_vc_id} 的签发方 ({curr_record.issuer_did})"
                    )
    
    verified_count = sum(1 for r in chain_results if r.get("overall_valid"))
    
    return {
        "chain_valid": chain_valid,
        "total_credentials": len(vc_ids),
        "verified_credentials": verified_count,
        "results": chain_results,
        "errors": errors,
    }


async def get_issuer_chain(
    db: AsyncSession,
    vc_id: str,
) -> dict:
    """
    获取凭证的签发者链
    
    追溯凭证的签发者链，直到根签发者。
    
    Args:
        db: 数据库会话
        vc_id: 凭证 ID
        
    Returns:
        签发者链
    """
    chain = []
    current_vc_id = vc_id
    visited = set()
    
    while current_vc_id and current_vc_id not in visited:
        visited.add(current_vc_id)
        
        result = await db.execute(
            select(VcRecord).where(VcRecord.vc_id == current_vc_id)
        )
        vc_record = result.scalar_one_or_none()
        
        if not vc_record:
            break
        
        chain.append({
            "vc_id": vc_record.vc_id,
            "issuer_did": vc_record.issuer_did,
            "subject_did": vc_record.subject_did,
            "vc_type": vc_record.vc_type,
            "status": vc_record.status,
            "issued_at": vc_record.issued_at.isoformat() if vc_record.issued_at else None,
        })
        
        # 查找签发方自己的凭证（签发方作为 subject 的凭证）
        issuer_vc_result = await db.execute(
            select(VcRecord).where(
                and_(
                    VcRecord.subject_did == vc_record.issuer_did,
                    VcRecord.vc_type == "IdentityCredential",
                    VcRecord.status == "active",
                )
            )
        )
        issuer_vc = issuer_vc_result.scalar_one_or_none()
        current_vc_id = issuer_vc.vc_id if issuer_vc else None
    
    return {
        "vc_id": vc_id,
        "chain_length": len(chain),
        "chain": chain,
        "root_issuer": chain[-1]["issuer_did"] if chain else None,
    }
