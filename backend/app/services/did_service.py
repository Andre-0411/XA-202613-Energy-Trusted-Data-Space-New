"""
DID 身份服务
创建DID(did:tds:{method-specific-id}) + 解析DID Document + 更新DID Document + 停用DID + DID列表查询

DID 格式: did:tds:{method-specific-id}
- method-specific-id: SM3 哈希的前 16 位十六进制
- 示例: did:tds:a1b2c3d4e5f6a7b8
"""
import uuid
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import DidDocument
from app.schemas.security import DidCreate, DidResponse
from app.exceptions import DIDError, DataNotFoundError, DataAlreadyExistsError
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)

DID_METHOD_PREFIX = "did:tds"
DID_CONTEXT = "https://www.w3.org/ns/did/v1"


async def _register_did_on_chain(did: str, public_key: str) -> bool:
    """将 DID 注册到 FISCO BCOS IdentityRegistry 合约 (非阻塞)"""
    try:
        from app.core.fisco_web3_client import get_fisco_web3_client
        from app.core.contract_registry import get_contract_registry
        client = get_fisco_web3_client()
        if not client or not client.is_connected:
            return False
        registry = get_contract_registry()
        info = registry.get_contract("IdentityRegistry")
        if not info or not info.address:
            return False
        pk_hash = gmssl_adapter.sm3_hash(public_key)
        await client.call_contract_method(info.address, info.abi, "registerDid", [did, pk_hash])
        logger.info(f"DID on-chain: {did}")
        return True
    except Exception as e:
        logger.debug(f"DID chain reg skipped: {e}")
        return False


def _generate_method_specific_id(public_key: str) -> str:
    """
    根据 SM2 公钥生成 DID method-specific-id

    对公钥做 SM3 哈希后取前 16 位十六进制作为 method-specific-id

    Args:
        public_key: SM2 公钥（十六进制）

    Returns:
        method-specific-id 字符串（16位十六进制）
    """
    pk_hash = gmssl_adapter.sm3_hash(public_key)
    return pk_hash[:16]


def _build_did_document(
    did: str,
    public_key: str,
    controller: Optional[str] = None,
    service_endpoints: Optional[list[dict]] = None,
    authentication_methods: Optional[list[dict]] = None,
) -> dict:
    """
    构建 W3C DID Document

    Args:
        did: DID 标识符
        public_key: SM2 公钥
        controller: 控制者 DID
        service_endpoints: 服务端点列表
        authentication_methods: 认证方法列表

    Returns:
        DID Document 字典
    """
    key_id = f"{did}#keys-1"

    document = {
        "@context": [DID_CONTEXT, "https://w3id.org/security/suites/sm2-2021/v1"],
        "id": did,
        "controller": controller or did,
        "verificationMethod": [
            {
                "id": key_id,
                "type": "SM2VerificationKey2021",
                "controller": controller or did,
                "publicKeyHex": public_key,
            }
        ],
        "authentication": [
            key_id
        ],
        "service": service_endpoints or [
            {
                "id": f"{did}#energy-data-service",
                "type": "EnergyDataService",
                "serviceEndpoint": "https://energy-dataspace.example.com/api/v1",
            }
        ],
    }

    if authentication_methods:
        document["authentication"] = [
            key_id,
            *[m.get("id", "") for m in authentication_methods if m.get("id")]
        ]
        document["verificationMethod"].extend(authentication_methods)

    return document


async def create_did(
    db: AsyncSession,
    request: DidCreate,
    user_id: str = "",
) -> DidResponse:
    """
    创建 DID

    格式: did:tds:{method-specific-id}，关联 SM2 公钥，生成 W3C DID Document
    method-specific-id 为 SM3 哈希的前 16 位十六进制

    Args:
        db: 数据库会话
        request: 创建请求
        user_id: 创建人 ID

    Returns:
        DID 响应
    """
    # 生成 method-specific-id（SM3 哈希前 16 位）
    method_specific_id = _generate_method_specific_id(request.public_key)
    did = f"{DID_METHOD_PREFIX}:{method_specific_id}"

    # 检查 DID 唯一性
    existing = await db.execute(
        select(DidDocument).where(DidDocument.did == did)
    )
    if existing.scalar_one_or_none():
        raise DataAlreadyExistsError(message=f"DID 已存在: {did}")

    # 构建 DID Document
    document = _build_did_document(
        did=did,
        public_key=request.public_key,
        controller=request.controller,
    )

    # 存储 DID Document
    did_doc = DidDocument(
        did=did,
        method=request.method,
        document=document,
        controller=request.controller or did,
        status="active",
    )
    db.add(did_doc)
    await db.commit()
    await db.refresh(did_doc)

    logger.info(f"DID 创建成功: {did}, 创建人: {user_id}")

    # 链上注册 (非阻塞)
    await _register_did_on_chain(did, request.public_key)

    return DidResponse.model_validate(did_doc)


async def resolve_did(
    db: AsyncSession,
    did: str,
) -> dict:
    """
    解析 DID Document

    返回完整的 DID Document，包括公钥、服务端点、认证方法

    Args:
        db: 数据库会话
        did: DID 标识符

    Returns:
        DID Document
    """
    result = await db.execute(
        select(DidDocument).where(DidDocument.did == did)
    )
    did_doc = result.scalar_one_or_none()
    if not did_doc:
        raise DataNotFoundError(message=f"DID 不存在: {did}")

    if did_doc.status == "deactivated":
        logger.warning(f"访问已停用的 DID: {did}")

    return {
        "did": did_doc.did,
        "method": did_doc.method,
        "status": did_doc.status,
        "document": did_doc.document,
        "controller": did_doc.controller,
        "created_at": did_doc.created_at.isoformat() if did_doc.created_at else None,
        "deactivated": did_doc.status == "deactivated",
    }


async def update_did_document(
    db: AsyncSession,
    did: str,
    service_endpoints: Optional[list[dict]] = None,
    add_authentication: Optional[list[dict]] = None,
    remove_authentication: Optional[list[str]] = None,
) -> DidResponse:
    """
    更新 DID Document

    支持添加/移除认证方法、更新服务端点

    Args:
        db: 数据库会话
        did: DID 标识符
        service_endpoints: 新的服务端点列表
        add_authentication: 添加的认证方法
        remove_authentication: 移除的认证方法 ID 列表

    Returns:
        更新后的 DID 响应
    """
    result = await db.execute(
        select(DidDocument).where(DidDocument.did == did)
    )
    did_doc = result.scalar_one_or_none()
    if not did_doc:
        raise DataNotFoundError(message=f"DID 不存在: {did}")

    if did_doc.status == "deactivated":
        raise DIDError(message=f"DID 已停用，无法更新: {did}")

    document = did_doc.document.copy()

    # 更新服务端点
    if service_endpoints is not None:
        document["service"] = service_endpoints

    # 添加认证方法
    if add_authentication:
        existing_vm = document.get("verificationMethod", [])
        existing_auth = document.get("authentication", [])
        for method in add_authentication:
            existing_vm.append(method)
            if method.get("id"):
                existing_auth.append(method["id"])
        document["verificationMethod"] = existing_vm
        document["authentication"] = existing_auth

    # 移除认证方法
    if remove_authentication:
        document["verificationMethod"] = [
            vm for vm in document.get("verificationMethod", [])
            if vm.get("id") not in remove_authentication
        ]
        document["authentication"] = [
            auth for auth in document.get("authentication", [])
            if auth not in remove_authentication
        ]

    did_doc.document = document
    await db.commit()
    await db.refresh(did_doc)

    logger.info(f"DID Document 更新成功: {did}")
    return DidResponse.model_validate(did_doc)


async def deactivate_did(
    db: AsyncSession,
    did: str,
    user_id: str = "",
) -> dict:
    """
    停用 DID

    将 DID 状态标记为 deactivated，不可逆

    Args:
        db: 数据库会话
        did: DID 标识符
        user_id: 操作人 ID

    Returns:
        停用结果
    """
    result = await db.execute(
        select(DidDocument).where(DidDocument.did == did)
    )
    did_doc = result.scalar_one_or_none()
    if not did_doc:
        raise DataNotFoundError(message=f"DID 不存在: {did}")

    if did_doc.status == "deactivated":
        raise DIDError(message=f"DID 已处于停用状态: {did}")

    did_doc.status = "deactivated"

    # 更新文档中的停用标记
    document = did_doc.document.copy()
    document["deactivated"] = True
    did_doc.document = document

    await db.commit()

    logger.info(f"DID 已停用: {did}, 操作人: {user_id}")
    return {
        "did": did,
        "status": "deactivated",
        "deactivated_at": datetime.now(timezone.utc).isoformat(),
        "deactivated_by": user_id,
    }


def extract_public_key(
    did_document: dict,
    purpose: str = "authentication",
) -> str:
    """
    从 DID Document 中提取指定用途的 SM2 公钥

    Args:
        did_document: W3C DID Document 字典
        purpose: 公钥用途，可选值:
            - "authentication": 用于身份认证/签名验证
            - "assertion": 用于断言/声明签名
            - "key_agreement": 用于密钥协商

    Returns:
        SM2 公钥（十六进制字符串）

    Raises:
        DIDError: 未找到匹配的公钥
    """
    verification_methods = did_document.get("verificationMethod", [])

    if not verification_methods:
        raise DIDError(message="DID Document 中无 verificationMethod")

    # 根据 purpose 确定目标 key ID
    auth_ids: list[str] = []
    if purpose == "authentication":
        auth_ids = did_document.get("authentication", [])
    elif purpose == "assertion":
        auth_ids = did_document.get("assertionMethod", [])
    elif purpose == "key_agreement":
        auth_ids = did_document.get("keyAgreement", [])
    else:
        raise DIDError(message=f"不支持的公钥用途: {purpose}")

    # 如果 purpose 列表为空或只含字符串引用，尝试匹配
    if auth_ids:
        # authentication 列表中的 ID 可能是字符串引用或嵌入式方法
        for auth_id in auth_ids:
            if isinstance(auth_id, str):
                # 字符串引用 → 从 verificationMethod 中查找
                for vm in verification_methods:
                    if vm.get("id") == auth_id:
                        pk = vm.get("publicKeyHex", "")
                        if pk:
                            return pk
            elif isinstance(auth_id, dict):
                # 嵌入式方法
                pk = auth_id.get("publicKeyHex", "")
                if pk:
                    return pk

    # 回退：使用第一个 verificationMethod 的公钥
    for vm in verification_methods:
        if vm.get("type") in ("SM2VerificationKey2021", "EcdsaSecp256k1VerificationKey2019"):
            pk = vm.get("publicKeyHex", "")
            if pk:
                return pk

    # 最终回退：使用任何可用的公钥
    if verification_methods:
        pk = verification_methods[0].get("publicKeyHex", "")
        if pk:
            return pk

    raise DIDError(message=f"DID Document 中未找到 purpose='{purpose}' 对应的 SM2 公钥")


async def list_dids(
    db: AsyncSession,
    method: Optional[str] = None,
    status: Optional[str] = None,
    controller: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    DID 列表查询

    Args:
        db: 数据库会话
        method: DID 方法过滤
        status: 状态过滤
        controller: 控制者过滤
        limit: 分页大小
        offset: 偏移量

    Returns:
        DID 列表
    """
    query = select(DidDocument)

    if method:
        query = query.where(DidDocument.method == method)
    if status:
        query = query.where(DidDocument.status == status)
    if controller:
        query = query.where(DidDocument.controller == controller)

    # 计算总数
    from sqlalchemy import func
    count_query = select(func.count()).select_from(DidDocument)
    if method:
        count_query = count_query.where(DidDocument.method == method)
    if status:
        count_query = count_query.where(DidDocument.status == status)
    if controller:
        count_query = count_query.where(DidDocument.controller == controller)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DidDocument.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    dids = result.scalars().all()

    items = [
        {
            "did": d.did,
            "method": d.method,
            "status": d.status,
            "controller": d.controller,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in dids
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def resolve(
    db: AsyncSession,
    did: str,
) -> dict:
    """
    解析 DID 并返回完整 DID Document

    便捷方法：直接返回 W3C DID Document 内容，
    供签名验证等场景使用。

    Args:
        db: 数据库会话
        did: DID 标识符

    Returns:
        W3C DID Document 字典
    """
    result = await resolve_did(db, did)
    return result.get("document", {})
