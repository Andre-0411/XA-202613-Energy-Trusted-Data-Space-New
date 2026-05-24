"""
安全增强 API - /api/v1/security
================================
提供国密算法（SM2/SM3/SM4）、零知识证明、可验证凭证、密钥管理的完整 API。

端点列表：
- SM2: generate, sign, verify
- SM3: hash
- SM4: encrypt, decrypt
- ZKP: data-proof, identity-proof, range-proof
- VC: issue, verify
- Keys: generate, rotate, shamir-split, shamir-recover, audit
"""

import base64
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.schemas.common import ApiResponse
from app.services.gmssl_real import (
    sm2_generate_keypair,
    sm2_sign,
    sm2_verify,
    sm3_hash,
    sm3_hexdigest,
    sm4_cbc_encrypt,
    sm4_cbc_decrypt,
    sm4_generate_key,
    sm4_generate_iv,
)
from app.services.zkp_real import zkp_service
from app.services.vc_real import vc_service, generate_issuer_did
from app.services.key_manager import key_manager
from app.utils.deps import get_current_user
from fastapi import Depends

router = APIRouter()


# ==================== 通用响应封装 ====================

def success(data=None, message="success"):
    """成功响应"""
    return ApiResponse(code=0, message=message, data=data)


def error(message: str, code: int = -1):
    """错误响应"""
    raise HTTPException(status_code=400, detail={"code": code, "message": message})


# ==================== SM2 请求/响应模型 ====================

class Sm2GenerateResponse(BaseModel):
    """SM2 密钥对生成响应"""
    private_key: str = Field(description="SM2 私钥（十六进制）")
    public_key: str = Field(description="SM2 公钥（十六进制）")


class Sm2SignRequest(BaseModel):
    """SM2 签名请求"""
    private_key: str = Field(description="SM2 私钥（十六进制）")
    message: str = Field(description="待签名消息")


class Sm2SignResponse(BaseModel):
    """SM2 签名响应"""
    signature: str = Field(description="签名值（十六进制 DER 编码）")
    message_hash: str = Field(description="消息的 SM3 哈希值")


class Sm2VerifyRequest(BaseModel):
    """SM2 验签请求"""
    public_key: str = Field(description="SM2 公钥（十六进制）")
    message: str = Field(description="原始消息")
    signature: str = Field(description="签名值（十六进制 DER 编码）")


class Sm2VerifyResponse(BaseModel):
    """SM2 验签响应"""
    valid: bool = Field(description="验签结果")


# ==================== SM3 请求/响应模型 ====================

class Sm3HashRequest(BaseModel):
    """SM3 哈希请求"""
    data: str = Field(description="待哈希数据")


class Sm3HashResponse(BaseModel):
    """SM3 哈希响应"""
    hash_hex: str = Field(description="SM3 哈希值（十六进制）")
    hash_bytes: str = Field(description="SM3 哈希值（Base64 编码）")
    length: int = Field(description="哈希长度（字节）")


# ==================== SM4 请求/响应模型 ====================

class Sm4EncryptRequest(BaseModel):
    """SM4 加密请求"""
    plaintext: str = Field(description="明文")
    key: Optional[str] = Field(default=None, description="SM4 密钥（十六进制，32字符）。不提供则自动生成")
    iv: Optional[str] = Field(default=None, description="SM4 IV（十六进制，32字符）。不提供则自动生成")


class Sm4EncryptResponse(BaseModel):
    """SM4 加密响应"""
    ciphertext: str = Field(description="密文（十六进制）")
    key: str = Field(description="使用的密钥（十六进制）")
    iv: str = Field(description="使用的 IV（十六进制）")


class Sm4DecryptRequest(BaseModel):
    """SM4 解密请求"""
    ciphertext: str = Field(description="密文（十六进制）")
    key: str = Field(description="SM4 密钥（十六进制）")
    iv: str = Field(description="SM4 IV（十六进制）")


class Sm4DecryptResponse(BaseModel):
    """SM4 解密响应"""
    plaintext: str = Field(description="明文")


# ==================== ZKP 请求/响应模型 ====================

class ZkpDataProofRequest(BaseModel):
    """数据源头真实性证明请求"""
    secret: str = Field(description="设备私钥（十六进制大整数）")
    public_key: Optional[str] = Field(default=None, description="设备公钥（十六进制大整数）")


class ZkpDataProofVerifyRequest(BaseModel):
    """数据源头真实性证明验证请求"""
    public_key: str = Field(description="公钥（十六进制大整数）")
    proof: dict = Field(description="证明数据")


class ZkpIdentityProofRequest(BaseModel):
    """身份属性证明请求"""
    attribute_value: int = Field(description="属性值")
    blinding_factor: Optional[str] = Field(default=None, description="盲化因子（十六进制）")


class ZkpIdentityProofVerifyRequest(BaseModel):
    """身份属性证明验证请求"""
    commitment: str = Field(description="承诺值（十六进制）")
    proof: dict = Field(description="证明数据")


class ZkpRangeProofRequest(BaseModel):
    """数据范围证明请求"""
    value: int = Field(description="要证明的值")
    min_val: int = Field(description="范围下限")
    max_val: int = Field(description="范围上限")


class ZkpRangeProofVerifyRequest(BaseModel):
    """数据范围证明验证请求"""
    proof: dict = Field(description="范围证明数据")
    min_val: int = Field(description="范围下限")
    max_val: int = Field(description="范围上限")


# ==================== VC 请求/响应模型 ====================

class VcIssueRequest(BaseModel):
    """签发可验证凭证请求"""
    issuer_did: str = Field(description="签发者 DID")
    issuer_private_key: str = Field(description="签发者 SM2 私钥")
    issuer_public_key: str = Field(description="签发者 SM2 公钥")
    subject_id: str = Field(description="凭证主体 DID")
    claims: dict = Field(description="声明内容")
    credential_type: Optional[list[str]] = Field(default=None, description="凭证类型")
    expiration_days: int = Field(default=365, description="有效期（天）")


class VcVerifyRequest(BaseModel):
    """验证可验证凭证请求"""
    vc_document: dict = Field(description="VC 文档")
    issuer_public_key: str = Field(description="签发者 SM2 公钥")


# ==================== 密钥管理请求/响应模型 ====================

class KeyGenerateRequest(BaseModel):
    """生成密钥请求"""
    key_level: str = Field(description="密钥层级：root/org/user")
    owner_id: str = Field(description="所有者标识")
    parent_key_id: Optional[str] = Field(default=None, description="父密钥 ID（非根密钥必填）")
    metadata: Optional[dict] = Field(default=None, description="附加元数据")


class KeyRotateRequest(BaseModel):
    """密钥轮换请求"""
    key_id: str = Field(description="要轮换的密钥 ID")
    operator_id: str = Field(description="操作者 ID")


class ShamirSplitRequest(BaseModel):
    """Shamir 秘密分割请求"""
    secret: str = Field(description="要分割的秘密（十六进制）")
    total_shares: int = Field(default=5, description="总份额数")
    threshold: int = Field(default=3, description="恢复阈值")


class ShamirRecoverRequest(BaseModel):
    """Shamir 秘密恢复请求"""
    shares: list[dict] = Field(description="份额列表")


# ================================================================
# SM2 端点
# ================================================================

@router.post("/sm2/generate", response_model=ApiResponse[Sm2GenerateResponse], summary="生成 SM2 密钥对")
async def api_sm2_generate(user: dict = Depends(get_current_user)):
    """
    生成 SM2 椭圆曲线密钥对。

    返回十六进制格式的私钥和公钥，可直接用于签名和验签操作。
    """
    private_key, public_key = sm2_generate_keypair()
    return success(Sm2GenerateResponse(
        private_key=private_key,
        public_key=public_key,
    ))


@router.post("/sm2/sign", response_model=ApiResponse[Sm2SignResponse], summary="SM2 签名")
async def api_sm2_sign(req: Sm2SignRequest, user: dict = Depends(get_current_user)):
    """
    使用 SM2 私钥对消息进行签名。

    内部流程：先对消息做 SM3 哈希，再用 SM2 私钥签名。
    返回 DER 编码的十六进制签名值。
    """
    try:
        msg_hash = sm3_hexdigest(req.message.encode("utf-8"))
        signature = sm2_sign(req.message, req.private_key)
        return success(Sm2SignResponse(
            signature=signature,
            message_hash=msg_hash,
        ))
    except Exception as e:
        error(f"SM2 签名失败: {str(e)}")


@router.post("/sm2/verify", response_model=ApiResponse[Sm2VerifyResponse], summary="SM2 验签")
async def api_sm2_verify(req: Sm2VerifyRequest, user: dict = Depends(get_current_user)):
    """
    使用 SM2 公钥验证签名。

    返回验签结果：true 表示签名有效，false 表示签名无效。
    """
    try:
        valid = sm2_verify(req.message, req.signature, req.public_key)
        return success(Sm2VerifyResponse(valid=valid))
    except Exception as e:
        error(f"SM2 验签失败: {str(e)}")


# ================================================================
# SM3 端点
# ================================================================

@router.post("/sm3/hash", response_model=ApiResponse[Sm3HashResponse], summary="SM3 哈希")
async def api_sm3_hash(req: Sm3HashRequest, user: dict = Depends(get_current_user)):
    """
    计算数据的 SM3 杂凑值。

    SM3 是国密标准哈希算法，输出 256 位（32 字节）摘要。
    """
    try:
        data_bytes = req.data.encode("utf-8")
        hash_bytes = sm3_hash(data_bytes)
        hash_hex = hash_bytes.hex()
        hash_b64 = base64.b64encode(hash_bytes).decode("ascii")
        return success(Sm3HashResponse(
            hash_hex=hash_hex,
            hash_bytes=hash_b64,
            length=len(hash_bytes),
        ))
    except Exception as e:
        error(f"SM3 哈希失败: {str(e)}")


# ================================================================
# SM4 端点
# ================================================================

@router.post("/sm4/encrypt", response_model=ApiResponse[Sm4EncryptResponse], summary="SM4 加密")
async def api_sm4_encrypt(req: Sm4EncryptRequest, user: dict = Depends(get_current_user)):
    """
    使用 SM4 CBC 模式加密数据。

    如果不提供密钥和 IV，会自动生成随机值。
    使用 PKCS7 填充，密文为十六进制格式。
    """
    try:
        # 处理密钥
        if req.key:
            key = bytes.fromhex(req.key)
            if len(key) != 16:
                error("SM4 密钥长度必须为 16 字节（32 个十六进制字符）")
        else:
            key = sm4_generate_key()

        # 处理 IV
        if req.iv:
            iv = bytes.fromhex(req.iv)
            if len(iv) != 16:
                error("SM4 IV 长度必须为 16 字节（32 个十六进制字符）")
        else:
            iv = sm4_generate_iv()

        # 加密
        plaintext = req.plaintext.encode("utf-8")
        ciphertext = sm4_cbc_encrypt(plaintext, key, iv)

        return success(Sm4EncryptResponse(
            ciphertext=ciphertext.hex(),
            key=key.hex(),
            iv=iv.hex(),
        ))
    except Exception as e:
        error(f"SM4 加密失败: {str(e)}")


@router.post("/sm4/decrypt", response_model=ApiResponse[Sm4DecryptResponse], summary="SM4 解密")
async def api_sm4_decrypt(req: Sm4DecryptRequest, user: dict = Depends(get_current_user)):
    """
    使用 SM4 CBC 模式解密数据。

    输入密文、密钥和 IV 均为十六进制格式。
    """
    try:
        key = bytes.fromhex(req.key)
        iv = bytes.fromhex(req.iv)
        ciphertext = bytes.fromhex(req.ciphertext)

        plaintext = sm4_cbc_decrypt(ciphertext, key, iv)

        return success(Sm4DecryptResponse(
            plaintext=plaintext.decode("utf-8"),
        ))
    except Exception as e:
        error(f"SM4 解密失败: {str(e)}")


# ================================================================
# ZKP 端点
# ================================================================

@router.post("/zkp/data-proof", summary="数据源头真实性证明")
async def api_zkp_data_proof(req: ZkpDataProofRequest, user: dict = Depends(get_current_user)):
    """
    生成数据源头真实性零知识证明。

    使用 Schnorr 协议证明"我知道设备私钥"而不暴露私钥本身。
    适用于 IoT 设备数据上报场景。
    """
    try:
        secret_int = int(req.secret, 16)
        public_key_int = int(req.public_key, 16) if req.public_key else None
        proof = zkp_service.generate_data_proof(secret_int, public_key_int)
        return success(proof)
    except Exception as e:
        error(f"生成数据证明失败: {str(e)}")


@router.post("/zkp/data-proof/verify", summary="验证数据源头真实性证明")
async def api_zkp_data_proof_verify(req: ZkpDataProofVerifyRequest, user: dict = Depends(get_current_user)):
    """
    验证数据源头真实性零知识证明。

    验证证明者确实拥有对应私钥，但不会泄露私钥信息。
    """
    try:
        public_key_int = int(req.public_key, 16)
        valid = zkp_service.verify_data_proof(public_key_int, req.proof)
        return success({"valid": valid})
    except Exception as e:
        error(f"验证数据证明失败: {str(e)}")


@router.post("/zkp/identity-proof", summary="身份属性证明")
async def api_zkp_identity_proof(req: ZkpIdentityProofRequest, user: dict = Depends(get_current_user)):
    """
    生成身份属性零知识证明。

    使用 Pedersen 承诺方案证明"我持有某属性值"而不暴露具体值。
    适用于资质验证、KYC 等场景。
    """
    try:
        blinding = int(req.blinding_factor, 16) if req.blinding_factor else None
        result = zkp_service.prove_attribute(req.attribute_value, blinding)
        return success(result)
    except Exception as e:
        error(f"生成身份证明失败: {str(e)}")


@router.post("/zkp/identity-proof/verify", summary="验证身份属性证明")
async def api_zkp_identity_proof_verify(req: ZkpIdentityProofVerifyRequest, user: dict = Depends(get_current_user)):
    """
    验证身份属性零知识证明。

    验证承诺对应的属性值有效，但不暴露具体值。
    """
    try:
        commitment_int = int(req.commitment, 16)
        valid = zkp_service.verify_attribute(commitment_int, req.proof)
        return success({"valid": valid})
    except Exception as e:
        error(f"验证身份证明失败: {str(e)}")


@router.post("/zkp/range-proof", summary="数据范围证明")
async def api_zkp_range_proof(req: ZkpRangeProofRequest, user: dict = Depends(get_current_user)):
    """
    生成数据范围零知识证明。

    证明"数据值在指定范围内"而不暴露具体数值。
    适用于价格区间验证、电量范围确认等场景。
    """
    try:
        result = zkp_service.prove_range(req.value, req.min_val, req.max_val)
        return success(result)
    except Exception as e:
        error(f"生成范围证明失败: {str(e)}")


@router.post("/zkp/range-proof/verify", summary="验证数据范围证明")
async def api_zkp_range_proof_verify(req: ZkpRangeProofVerifyRequest, user: dict = Depends(get_current_user)):
    """
    验证数据范围零知识证明。

    确认数据确实在声明的范围内，同时不泄露数据具体值。
    """
    try:
        valid = zkp_service.verify_range_proof(req.proof, req.min_val, req.max_val)
        return success({"valid": valid})
    except Exception as e:
        error(f"验证范围证明失败: {str(e)}")


# ================================================================
# VC 端点
# ================================================================

@router.post("/vc/issue", summary="签发可验证凭证")
async def api_vc_issue(req: VcIssueRequest, user: dict = Depends(get_current_user)):
    """
    签发 W3C 标准可验证凭证（Verifiable Credential）。

    签发者使用 SM2 私钥签名，生成包含 proof 的标准化 VC 文档。
    支持自定义凭证类型和声明内容。
    """
    try:
        vc_document = vc_service.issue(
            issuer_did=req.issuer_did,
            issuer_private_key=req.issuer_private_key,
            issuer_public_key=req.issuer_public_key,
            subject_id=req.subject_id,
            claims=req.claims,
            credential_type=req.credential_type,
            expiration_days=req.expiration_days,
        )
        return success(vc_document)
    except Exception as e:
        error(f"签发 VC 失败: {str(e)}")


@router.post("/vc/verify", summary="验证可验证凭证")
async def api_vc_verify(req: VcVerifyRequest, user: dict = Depends(get_current_user)):
    """
    验证可验证凭证的有效性。

    检查内容：
    - SM2 签名有效性
    - 凭证是否过期
    - 凭证是否被撤销
    """
    try:
        result = vc_service.verify(req.vc_document, req.issuer_public_key)
        return success(result)
    except Exception as e:
        error(f"验证 VC 失败: {str(e)}")


# ================================================================
# 密钥管理端点
# ================================================================

@router.post("/keys/generate", summary="生成密钥")
async def api_keys_generate(req: KeyGenerateRequest, user: dict = Depends(get_current_user)):
    """
    生成新密钥。

    支持三层密钥体系：
    - root: 根密钥（主密钥）
    - org: 机构密钥（需指定父密钥）
    - user: 用户密钥（需指定父密钥）
    """
    try:
        result = key_manager.generate_key(
            key_level=req.key_level,
            owner_id=req.owner_id,
            parent_key_id=req.parent_key_id,
            metadata=req.metadata,
        )
        return success(result)
    except Exception as e:
        error(f"生成密钥失败: {str(e)}")


@router.post("/keys/rotate", summary="密钥轮换")
async def api_keys_rotate(req: KeyRotateRequest, user: dict = Depends(get_current_user)):
    """
    密钥轮换。

    将旧密钥标记为归档状态，生成新密钥继承原有属性。
    所有操作记录到审计日志。
    """
    try:
        result = key_manager.rotate_key(req.key_id, req.operator_id)
        return success(result)
    except Exception as e:
        error(f"密钥轮换失败: {str(e)}")


@router.post("/keys/shamir-split", summary="Shamir 秘密分割")
async def api_keys_shamir_split(req: ShamirSplitRequest, user: dict = Depends(get_current_user)):
    """
    Shamir 秘密共享分割。

    将秘密分割为多份，任意达到阈值的份额可恢复原始秘密。
    默认 5 份中需 3 份恢复（3-of-5 方案）。
    """
    try:
        shares = key_manager.shamir_split(
            secret_hex=req.secret,
            total_shares=req.total_shares,
            threshold=req.threshold,
        )
        return success({
            "shares": shares,
            "total_shares": req.total_shares,
            "threshold": req.threshold,
        })
    except Exception as e:
        error(f"Shamir 分割失败: {str(e)}")


@router.post("/keys/shamir-recover", summary="Shamir 秘密恢复")
async def api_keys_shamir_recover(req: ShamirRecoverRequest, user: dict = Depends(get_current_user)):
    """
    Shamir 秘密共享恢复。

    使用足够数量的份额恢复原始秘密。
    至少需要 threshold 个份额。
    """
    try:
        secret = key_manager.shamir_recover(req.shares)
        return success({
            "secret": secret,
            "shares_used": len(req.shares),
        })
    except Exception as e:
        error(f"Shamir 恢复失败: {str(e)}")


@router.get("/keys/audit", summary="密钥使用审计日志")
async def api_keys_audit(
    key_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    """
    查询密钥使用审计日志。

    支持按密钥 ID 和操作类型过滤。
    日志记录包括：密钥生成、轮换、撤销、Shamir 操作等。
    """
    try:
        logs = key_manager.get_audit_logs(key_id=key_id, action=action, limit=limit)
        return success({
            "logs": logs,
            "total": len(logs),
        })
    except Exception as e:
        error(f"查询审计日志失败: {str(e)}")
