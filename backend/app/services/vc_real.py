"""
可验证凭证服务（真实实现）
===========================
基于 W3C Verifiable Credentials 标准实现，使用 SM2 签名，
并将所有凭证持久化到 VerifiableCredential/RevocationEntry 数据库模型。

功能：
- 签发 VC（Issuer 用 SM2 私钥签名）
- 验证 VC（用 Issuer 公钥验证签名 + 检查过期/撤销）
- 撤销 VC（写入 RevocationEntry 模型）
- VC 文档结构符合 W3C 标准

参考：
- W3C VC Data Model v2.0: https://www.w3.org/TR/vc-data-model-2.0/
- SM2Signature2026 签名套件
"""

import hashlib
import json
import logging
import secrets
import uuid as uuid_module
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vc_model import VerifiableCredential, RevocationEntry
from app.models.security import DidDocument
from app.services.gmssl_real import sm2_sign, sm2_verify, sm3_hexdigest

logger = logging.getLogger(__name__)


# ============================================================
# 常量
# ============================================================

VC_CONTEXT = [
    "https://www.w3.org/2018/credentials/v1",
    "https://w3id.org/security/suites/sm2-2026/v1",
]

VC_TYPE = ["VerifiableCredential"]


# ============================================================
# 数据结构
# ============================================================

@dataclass
class IssuerInfo:
    """签发者信息"""
    did: str                    # DID 标识
    name: str                   # 名称
    private_key: str            # SM2 私钥（十六进制）
    public_key: str             # SM2 公钥（十六进制）


@dataclass
class CredentialSubject:
    """凭证主体"""
    id: str                     # DID 标识
    claims: dict                # 声明内容


@dataclass
class VCProof:
    """VC 签名证明"""
    type: str = "SM2Signature2026"
    created: str = ""
    verification_method: str = ""
    proof_purpose: str = "assertionMethod"
    proof_value: str = ""


# ============================================================
# VC 签发
# ============================================================

async def issue_vc(
    db: AsyncSession,
    issuer: IssuerInfo,
    credential_subject: CredentialSubject,
    credential_type: list[str] = None,
    expiration_days: int = 365,
    additional_context: list[str] = None,
) -> dict:
    """
    签发可验证凭证（数据库持久化）

    Args:
        db: 数据库会话
        issuer: 签发者信息
        credential_subject: 凭证主体
        credential_type: 凭证类型列表
        expiration_days: 有效期（天）
        additional_context: 附加上下文

    Returns:
        完整的 VC 文档（JSON-LD 格式）
    """
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(days=expiration_days)

    # 构建 VC 文档（不含 proof）
    vc_id = f"urn:uuid:{secrets.token_hex(16)}"
    types = VC_TYPE + (credential_type or [])

    vc_document = {
        "@context": VC_CONTEXT + (additional_context or []),
        "id": vc_id,
        "type": types,
        "issuer": issuer.did,
        "issuanceDate": now.isoformat().replace("+00:00", "Z"),
        "expirationDate": expiration.isoformat().replace("+00:00", "Z"),
        "credentialSubject": {
            "id": credential_subject.id,
            **credential_subject.claims,
        },
    }

    # 签名：对 VC 文档的 canonical JSON 做 SM3 哈希，然后 SM2 签名
    canonical = _canonicalize(vc_document)
    message_hash = sm3_hexdigest(canonical.encode("utf-8"))
    signature = sm2_sign(canonical, issuer.private_key)

    # 添加 proof
    vc_document["proof"] = {
        "type": "SM2Signature2026",
        "created": now.isoformat().replace("+00:00", "Z"),
        "verificationMethod": f"{issuer.did}#keys-1",
        "proofPurpose": "assertionMethod",
        "proofValue": signature,
    }

    # 存储到数据库（过期时间存储在 document JSONB 的 expirationDate 字段中）
    vc_record = VerifiableCredential(
        document=vc_document,
        issuer_did=issuer.did,
        subject_did=credential_subject.id,
        revoked=False,
        issued_at=now,
    )
    db.add(vc_record)
    await db.commit()
    await db.refresh(vc_record)

    logger.info(f"签发 VC: {vc_id} issuer={issuer.did} subject={credential_subject.id}")
    return vc_document


async def verify_vc(
    db: AsyncSession,
    vc_document: dict,
    issuer_public_key: str,
) -> dict:
    """
    验证可验证凭证（数据库查询撤销状态）

    验证内容：
    1. SM2 签名有效性
    2. 是否已过期
    3. 是否已撤销（查询 RevocationEntry）

    Args:
        db: 数据库会话
        vc_document: VC 文档
        issuer_public_key: 签发者公钥

    Returns:
        验证结果字典
    """
    result = {
        "valid": False,
        "checks": {
            "signature": False,
            "expiration": False,
            "revocation": False,
            "structure": False,
        },
        "errors": [],
    }

    # 1. 结构检查
    try:
        required_fields = ["@context", "id", "type", "issuer", "issuanceDate", "credentialSubject", "proof"]
        for field_name in required_fields:
            if field_name not in vc_document:
                result["errors"].append(f"缺少必填字段: {field_name}")
                return result
        result["checks"]["structure"] = True
    except Exception as e:
        result["errors"].append(f"结构检查失败: {str(e)}")
        return result

    # 2. 签名验证
    try:
        proof = vc_document["proof"]
        signature = proof["proofValue"]

        # 重建不含 proof 的 VC 文档
        vc_without_proof = {k: v for k, v in vc_document.items() if k != "proof"}
        canonical = _canonicalize(vc_without_proof)

        # 验证签名
        is_valid = sm2_verify(canonical, signature, issuer_public_key)
        result["checks"]["signature"] = is_valid
        if not is_valid:
            result["errors"].append("签名验证失败")
    except Exception as e:
        result["errors"].append(f"签名验证异常: {str(e)}")

    # 3. 过期检查
    try:
        expiration_str = vc_document.get("expirationDate", "")
        if expiration_str:
            expiration_str = expiration_str.replace("Z", "+00:00")
            expiration = datetime.fromisoformat(expiration_str)
            now = datetime.now(timezone.utc)
            result["checks"]["expiration"] = now < expiration
            if now >= expiration:
                result["errors"].append("VC 已过期")
        else:
            result["checks"]["expiration"] = True
    except Exception as e:
        result["errors"].append(f"过期检查异常: {str(e)}")

    # 4. 撤销检查（查询数据库）
    vc_id = vc_document.get("id", "")
    try:
        revocation_result = await db.execute(
            select(RevocationEntry).where(RevocationEntry.vc_id == vc_id)
        )
        revocation = revocation_result.scalar_one_or_none()
        result["checks"]["revocation"] = revocation is None
        if revocation:
            result["errors"].append(f"VC 已被撤销: {revocation.reason}")
    except Exception as e:
        result["errors"].append(f"撤销检查异常: {str(e)}")

    # 综合结果
    result["valid"] = all(result["checks"].values())
    return result


# ============================================================
# VC 撤销
# ============================================================

async def revoke_vc(
    db: AsyncSession,
    vc_id: str,
    operator_did: str = "",
    reason: str = "",
) -> bool:
    """
    撤销 VC（数据库持久化）

    Args:
        db: 数据库会话
        vc_id: VC 标识
        operator_did: 操作者 DID
        reason: 撤销原因

    Returns:
        是否撤销成功
    """
    # 查找 VC 记录
    result = await db.execute(
        select(VerifiableCredential).where(VerifiableCredential.document["id"].as_string() == vc_id)
    )
    vc_record = result.scalar_one_or_none()

    if not vc_record:
        return False

    if vc_record.revoked:
        return False

    # 更新 VC 状态
    vc_record.revoked = True
    vc_record.revoked_at = datetime.now(timezone.utc)
    vc_record.revoked_by = operator_did

    # 创建撤销记录
    revocation_entry = RevocationEntry(
        vc_id=vc_id,
        reason=reason or "撤销操作",
        revoked_by=operator_did,
        revoked_at=datetime.now(timezone.utc),
    )
    db.add(revocation_entry)
    await db.commit()

    logger.info(f"撤销 VC: {vc_id} by {operator_did}")
    return True


async def is_revoked(db: AsyncSession, vc_id: str) -> bool:
    """检查 VC 是否已撤销（查询数据库）"""
    result = await db.execute(
        select(RevocationEntry).where(RevocationEntry.vc_id == vc_id)
    )
    return result.scalar_one_or_none() is not None


# ============================================================
# VC 查询
# ============================================================

async def get_vc(db: AsyncSession, vc_id: str) -> Optional[dict]:
    """获取 VC 文档（从数据库）"""
    result = await db.execute(
        select(VerifiableCredential).where(
            VerifiableCredential.document["id"].as_string() == vc_id
        )
    )
    vc_record = result.scalar_one_or_none()
    if vc_record:
        return vc_record.document
    return None


async def list_vcs(
    db: AsyncSession,
    issuer_did: Optional[str] = None,
    subject_did: Optional[str] = None,
    include_revoked: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """列出 VC（数据库查询）"""
    query = select(VerifiableCredential)
    count_query = select(func.count()).select_from(VerifiableCredential)

    if not include_revoked:
        query = query.where(VerifiableCredential.revoked == False)
        count_query = count_query.where(VerifiableCredential.revoked == False)
    if issuer_did:
        query = query.where(VerifiableCredential.issuer_did == issuer_did)
        count_query = count_query.where(VerifiableCredential.issuer_did == issuer_did)
    if subject_did:
        query = query.where(VerifiableCredential.subject_did == subject_did)
        count_query = count_query.where(VerifiableCredential.subject_did == subject_did)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(VerifiableCredential.issued_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    items = [r.document for r in records]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# VC 模板
# ============================================================

VC_TEMPLATES = {
    "EnergyLicense": {
        "name": "能源经营许可证",
        "description": "证明机构持有合法能源经营资质",
        "required_claims": ["license_type", "issuing_authority", "valid_from"],
        "optional_claims": ["scope", "restrictions"],
    },
    "DeviceCertificate": {
        "name": "设备认证证书",
        "description": "证明设备通过安全认证",
        "required_claims": ["device_type", "manufacturer", "certification_level"],
        "optional_claims": ["firmware_version", "security_features"],
    },
    "DataQualityCert": {
        "name": "数据质量证书",
        "description": "证明数据符合质量标准",
        "required_claims": ["data_source", "quality_score", "standard"],
        "optional_claims": ["test_results", "certification_scope"],
    },
    "OperatorCredential": {
        "name": "运营者凭证",
        "description": "证明运营者身份和资质",
        "required_claims": ["operator_name", "qualification", "jurisdiction"],
        "optional_claims": ["contact_info", "website"],
    },
}


async def issue_from_template(
    db: AsyncSession,
    template_name: str,
    issuer: IssuerInfo,
    subject_id: str,
    claims: dict,
    expiration_days: int = 365,
) -> dict:
    """
    使用模板签发 VC

    Args:
        db: 数据库会话
        template_name: 模板名称
        issuer: 签发者
        subject_id: 凭证主体 DID
        claims: 声明内容
        expiration_days: 有效期

    Returns:
        VC 文档
    """
    template = VC_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"未知模板: {template_name}")

    # 验证必填字段
    for required in template["required_claims"]:
        if required not in claims:
            raise ValueError(f"缺少必填声明: {required}")

    credential_subject = CredentialSubject(
        id=subject_id,
        claims=claims,
    )

    return await issue_vc(
        db=db,
        issuer=issuer,
        credential_subject=credential_subject,
        credential_type=[template_name],
        expiration_days=expiration_days,
    )


# ============================================================
# 辅助函数
# ============================================================

def _canonicalize(document: dict) -> str:
    """
    JSON-LD 规范化（简化版）

    使用 JSON 排序键 + 紧凑格式，确保相同文档产生相同字符串。
    生产环境应使用 JSON-LD Canonicalization Algorithm (JCS)。
    """
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_issuer_did(method: str = "fisco", identifier: Optional[str] = None) -> str:
    """
    生成签发者 DID

    Args:
        method: DID 方法
        identifier: 标识符（不提供则自动生成）

    Returns:
        DID 字符串
    """
    if identifier is None:
        identifier = secrets.token_hex(16)
    return f"did:{method}:{identifier}"


# ============================================================
# 便捷封装类
# ============================================================

class VCService:
    """可验证凭证服务"""

    @staticmethod
    async def issue(
        db: AsyncSession,
        issuer_did: str,
        issuer_private_key: str,
        issuer_public_key: str,
        subject_id: str,
        claims: dict,
        credential_type: list[str] = None,
        expiration_days: int = 365,
        issuer_name: str = "",
    ) -> dict:
        """签发 VC"""
        issuer = IssuerInfo(
            did=issuer_did,
            name=issuer_name,
            private_key=issuer_private_key,
            public_key=issuer_public_key,
        )
        credential_subject = CredentialSubject(id=subject_id, claims=claims)
        return await issue_vc(db, issuer, credential_subject, credential_type, expiration_days)

    @staticmethod
    async def verify(db: AsyncSession, vc_document: dict, issuer_public_key: str) -> dict:
        """验证 VC"""
        return await verify_vc(db, vc_document, issuer_public_key)

    @staticmethod
    async def revoke(db: AsyncSession, vc_id: str, operator_did: str = "", reason: str = "") -> bool:
        """撤销 VC"""
        return await revoke_vc(db, vc_id, operator_did, reason)

    @staticmethod
    def get_templates() -> dict:
        """获取可用模板"""
        return VC_TEMPLATES

    @staticmethod
    async def issue_from_template(
        db: AsyncSession,
        template_name: str,
        issuer_did: str,
        issuer_private_key: str,
        issuer_public_key: str,
        subject_id: str,
        claims: dict,
        expiration_days: int = 365,
    ) -> dict:
        """使用模板签发 VC"""
        issuer = IssuerInfo(
            did=issuer_did,
            name="",
            private_key=issuer_private_key,
            public_key=issuer_public_key,
        )
        return await issue_from_template(db, template_name, issuer, subject_id, claims, expiration_days)


# 全局实例
vc_service = VCService()
