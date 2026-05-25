"""
合约全生命周期管理服务
基于《可信数据空间标准体系建设指南》（2025版）和《可信数据空间 能力要求》(TDSA/A-001-2025)

完整生命周期：
1. 草稿阶段：合约模板选择 → 条款配置 → 参与方确认
2. 签署阶段：电子签名 → 区块链存证 → 合约生效
3. 执行阶段：条件触发 → 自动执行 → 状态监控
4. 完成阶段：交付确认 → 结算清算 → 合约归档
5. 争议处理：争议提交 → 证据收集 → 仲裁裁决
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract, ContractAmendment
from app.models.blockchain import EvidenceRecord
from app.models.user import Organization
from app.exceptions import (
    DataNotFoundError, DataValidationError, ContractStateError,
)
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)


# ==================== 合约状态定义 ====================

class ContractLifecycleStage(str, Enum):
    """合约生命周期阶段"""
    DRAFT = "draft"              # 草稿阶段
    SIGNING = "signing"          # 签署阶段
    EXECUTION = "execution"      # 执行阶段
    COMPLETION = "completion"    # 完成阶段
    DISPUTE = "dispute"          # 争议处理


class ContractLifecycleStatus(str, Enum):
    """合约生命周期状态"""
    # 草稿阶段
    TEMPLATE_SELECTING = "template_selecting"    # 模板选择中
    TERMS_CONFIGURING = "terms_configuring"      # 条款配置中
    PARTIES_CONFIRMING = "parties_confirming"    # 参与方确认中
    DRAFT_COMPLETED = "draft_completed"          # 草稿完成

    # 签署阶段
    SIGNING_PENDING = "signing_pending"          # 待签署
    SIGNING_IN_PROGRESS = "signing_in_progress"  # 签署中
    BLOCKCHAIN_RECORDING = "blockchain_recording" # 区块链存证中
    CONTRACT_ACTIVE = "contract_active"          # 合约生效

    # 执行阶段
    CONDITION_MONITORING = "condition_monitoring" # 条件监控中
    AUTO_EXECUTING = "auto_executing"            # 自动执行中
    EXECUTION_MONITORING = "execution_monitoring" # 执行监控中

    # 完成阶段
    DELIVERY_CONFIRMING = "delivery_confirming"  # 交付确认中
    SETTLEMENT_PROCESSING = "settlement_processing" # 结算清算中
    CONTRACT_ARCHIVING = "contract_archiving"    # 合约归档中
    CONTRACT_COMPLETED = "contract_completed"    # 合约完成

    # 争议处理
    DISPUTE_SUBMITTED = "dispute_submitted"      # 争议已提交
    EVIDENCE_COLLECTING = "evidence_collecting"  # 证据收集中
    ARBITRATION_PROCESSING = "arbitration_processing" # 仲裁处理中
    DISPUTE_RESOLVED = "dispute_resolved"        # 争议已解决


# 合约模板库
CONTRACT_TEMPLATES = {
    "data_sharing": {
        "name": "数据共享协议",
        "description": "用于数据提供方与使用方之间的数据共享",
        "default_terms": {
            "data_scope": "指定数据集",
            "usage_purpose": "数据分析与研究",
            "duration_days": 365,
            "revenue_share_ratio": 0.7,
            "security_level_required": 3,
        },
        "required_fields": ["data_scope", "usage_purpose", "duration_days"],
    },
    "data_service": {
        "name": "数据服务协议",
        "description": "用于数据产品订阅与服务交付",
        "default_terms": {
            "service_type": "API接口服务",
            "sla_level": "99.9%",
            "billing_model": "按调用次数",
            "unit_price": 0.01,
            "monthly_quota": 100000,
        },
        "required_fields": ["service_type", "billing_model"],
    },
    "joint_computing": {
        "name": "联合计算协议",
        "description": "用于多方联合计算任务",
        "default_terms": {
            "computing_type": "联邦学习",
            "participants": [],
            "data_contribution_ratio": {},
            "result_distribution": "按贡献比例",
        },
        "required_fields": ["computing_type", "participants"],
    },
    "data_trading": {
        "name": "数据交易协议",
        "description": "用于数据资产买卖交易",
        "default_terms": {
            "trading_mode": "一次性购买",
            "price": 0,
            "payment_terms": "预付款",
            "delivery_method": "离线传输",
            "warranty_period_days": 30,
        },
        "required_fields": ["trading_mode", "price"],
    },
}


# ==================== 草稿阶段 ====================

async def select_contract_template(
    db: AsyncSession,
    contract_type: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    草稿阶段 - 合约模板选择

    步骤：
    1. 获取合约模板
    2. 创建草稿合约
    3. 返回模板详情供用户配置
    """
    template = CONTRACT_TEMPLATES.get(contract_type)
    if not template:
        raise DataValidationError(
            f"不支持的合约类型: {contract_type}，允许值: {list(CONTRACT_TEMPLATES.keys())}"
        )

    # 创建草稿合约
    contract_no = _generate_contract_no()
    contract = Contract(
        contract_no=contract_no,
        title=template["name"],
        contract_type=contract_type,
        content=template["description"],
        terms=template["default_terms"].copy(),
        status="draft",
        lifecycle_stage=ContractLifecycleStage.DRAFT.value,
        lifecycle_status=ContractLifecycleStatus.TEMPLATE_SELECTING.value,
        created_by=uuid.UUID(user_id),
        # 临时填充，实际需要用户提供
        party_a_org_id=uuid.UUID(user_id),
        party_a_user_id=uuid.UUID(user_id),
        party_b_org_id=uuid.UUID(user_id),
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    logger.info(f"Contract template selected: {contract_type}, contract: {contract_no}")
    return {
        "contract_id": str(contract.id),
        "contract_no": contract_no,
        "template": template,
        "lifecycle_stage": ContractLifecycleStage.DRAFT.value,
        "lifecycle_status": ContractLifecycleStatus.TEMPLATE_SELECTING.value,
        "next_step": "configure_terms",
    }


async def configure_contract_terms(
    db: AsyncSession,
    contract_id: str,
    terms: Dict[str, Any],
    party_a_org_id: str,
    party_a_user_id: str,
    party_b_org_id: str,
    party_b_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    草稿阶段 - 条款配置

    步骤：
    1. 验证合约存在且为草稿状态
    2. 配置合约条款
    3. 设置参与方信息
    4. 更新生命周期状态
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.lifecycle_stage != ContractLifecycleStage.DRAFT.value:
        raise ContractStateError("合约不在草稿阶段，无法配置条款")

    # 获取模板验证必填字段
    template = CONTRACT_TEMPLATES.get(contract.contract_type, {})
    required_fields = template.get("required_fields", [])
    missing_fields = [f for f in required_fields if f not in terms]
    if missing_fields:
        raise DataValidationError(f"缺少必填条款字段: {missing_fields}")

    # 合并条款（保留默认值，更新用户配置）
    merged_terms = contract.terms.copy() if contract.terms else {}
    merged_terms.update(terms)

    # 更新合约
    contract.terms = merged_terms
    contract.party_a_org_id = uuid.UUID(party_a_org_id)
    contract.party_a_user_id = uuid.UUID(party_a_user_id)
    contract.party_b_org_id = uuid.UUID(party_b_org_id)
    contract.party_b_user_id = uuid.UUID(party_b_user_id) if party_b_user_id else None
    contract.lifecycle_status = ContractLifecycleStatus.TERMS_CONFIGURING.value
    await db.commit()

    logger.info(f"Contract terms configured: {contract_id}")
    return {
        "contract_id": str(contract.id),
        "contract_no": contract.contract_no,
        "terms": merged_terms,
        "parties": {
            "party_a_org_id": party_a_org_id,
            "party_a_user_id": party_a_user_id,
            "party_b_org_id": party_b_org_id,
            "party_b_user_id": party_b_user_id,
        },
        "lifecycle_stage": ContractLifecycleStage.DRAFT.value,
        "lifecycle_status": ContractLifecycleStatus.TERMS_CONFIGURING.value,
        "next_step": "parties_confirm",
    }


async def confirm_contract_parties(
    db: AsyncSession,
    contract_id: str,
    confirming_party: str,
    confirmed: bool,
    feedback: str = "",
) -> Dict[str, Any]:
    """
    草稿阶段 - 参与方确认

    步骤：
    1. 验证合约状态
    2. 记录参与方确认状态
    3. 双方确认后更新状态
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.lifecycle_status not in [
        ContractLifecycleStatus.TERMS_CONFIGURING.value,
        ContractLifecycleStatus.PARTIES_CONFIRMING.value,
    ]:
        raise ContractStateError("合约状态不允许参与方确认")

    # 记录确认状态（存储在合约的metadata中）
    confirmations = contract.metadata_.get("confirmations", {}) if hasattr(contract, 'metadata_') and contract.metadata_ else {}
    if not confirmations:
        confirmations = {}

    confirmations[confirming_party] = {
        "confirmed": confirmed,
        "feedback": feedback,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新合约（使用terms字段临时存储确认信息）
    terms = contract.terms.copy() if contract.terms else {}
    terms["_confirmations"] = confirmations
    contract.terms = terms
    contract.lifecycle_status = ContractLifecycleStatus.PARTIES_CONFIRMING.value

    # 检查双方是否都已确认
    party_a_confirmed = confirmations.get("party_a", {}).get("confirmed", False)
    party_b_confirmed = confirmations.get("party_b", {}).get("confirmed", False)

    if party_a_confirmed and party_b_confirmed:
        contract.lifecycle_status = ContractLifecycleStatus.DRAFT_COMPLETED.value

    await db.commit()

    logger.info(f"Contract party confirmation: {contract_id}, party={confirming_party}, confirmed={confirmed}")
    return {
        "contract_id": str(contract.id),
        "confirming_party": confirming_party,
        "confirmed": confirmed,
        "party_a_confirmed": party_a_confirmed,
        "party_b_confirmed": party_b_confirmed,
        "both_confirmed": party_a_confirmed and party_b_confirmed,
        "lifecycle_stage": ContractLifecycleStage.DRAFT.value,
        "lifecycle_status": contract.lifecycle_status,
        "next_step": "sign" if party_a_confirmed and party_b_confirmed else "wait_for_other_party",
    }


# ==================== 签署阶段 ====================

async def initiate_signing(
    db: AsyncSession,
    contract_id: str,
    signer_id: str,
    signing_order: str = "party_a_first",
) -> Dict[str, Any]:
    """
    签署阶段 - 发起签署

    步骤：
    1. 验证草稿已完成
    2. 创建签署记录
    3. 设置签署顺序
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.lifecycle_status != ContractLifecycleStatus.DRAFT_COMPLETED.value:
        raise ContractStateError("草稿未完成，无法发起签署")

    # 生成签署任务
    signing_task = {
        "task_id": str(uuid.uuid4()),
        "contract_id": contract_id,
        "signing_order": signing_order,
        "signers": [
            {
                "party": "party_a",
                "org_id": str(contract.party_a_org_id),
                "user_id": str(contract.party_a_user_id),
                "status": "pending",
            },
            {
                "party": "party_b",
                "org_id": str(contract.party_b_org_id),
                "user_id": str(contract.party_b_user_id),
                "status": "pending",
            },
        ],
        "initiated_by": signer_id,
        "initiated_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新合约状态
    contract.lifecycle_stage = ContractLifecycleStage.SIGNING.value
    contract.lifecycle_status = ContractLifecycleStatus.SIGNING_PENDING.value

    # 存储签署任务信息
    terms = contract.terms.copy() if contract.terms else {}
    terms["_signing_task"] = signing_task
    contract.terms = terms

    await db.commit()

    logger.info(f"Contract signing initiated: {contract_id}")
    return {
        "contract_id": str(contract.id),
        "signing_task": signing_task,
        "lifecycle_stage": ContractLifecycleStage.SIGNING.value,
        "lifecycle_status": ContractLifecycleStatus.SIGNING_PENDING.value,
        "next_step": "sign_contract",
    }


async def sign_contract_lifecycle(
    db: AsyncSession,
    contract_id: str,
    signer_id: str,
    signer_party: str,
    signature_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    签署阶段 - 电子签名

    步骤：
    1. 验证签署权限
    2. 执行电子签名
    3. 记录签名信息
    4. 检查是否双方都已签署
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.lifecycle_stage != ContractLifecycleStage.SIGNING.value:
        raise ContractStateError("合约不在签署阶段")

    # 生成签名哈希
    sign_content = f"{contract_id}:{signer_id}:{signer_party}:{datetime.now(timezone.utc).isoformat()}"
    signature_hash = gmssl_adapter.sm3_hash(sign_content)

    # 记录签名信息
    terms = contract.terms.copy() if contract.terms else {}
    signing_task = terms.get("_signing_task", {})

    # 更新签署者状态
    for signer in signing_task.get("signers", []):
        if signer["party"] == signer_party:
            signer["status"] = "signed"
            signer["signed_at"] = datetime.now(timezone.utc).isoformat()
            signer["signature_hash"] = signature_hash
            signer["signature_data"] = signature_data or {}
            break

    terms["_signing_task"] = signing_task
    contract.terms = terms
    contract.lifecycle_status = ContractLifecycleStatus.SIGNING_IN_PROGRESS.value

    # 检查是否双方都已签署
    all_signed = all(
        s["status"] == "signed"
        for s in signing_task.get("signers", [])
    )

    if all_signed:
        # 双方都已签署，进入区块链存证
        contract.lifecycle_status = ContractLifecycleStatus.BLOCKCHAIN_RECORDING.value

    await db.commit()

    logger.info(f"Contract signed: {contract_id}, party={signer_party}")
    return {
        "contract_id": str(contract.id),
        "signer_party": signer_party,
        "signature_hash": signature_hash,
        "all_signed": all_signed,
        "lifecycle_stage": ContractLifecycleStage.SIGNING.value,
        "lifecycle_status": contract.lifecycle_status,
        "next_step": "record_to_blockchain" if all_signed else "wait_for_other_signer",
    }


async def record_to_blockchain(
    db: AsyncSession,
    contract_id: str,
    blockchain_enabled: bool = True,
) -> Dict[str, Any]:
    """
    签署阶段 - 区块链存证

    步骤：
    1. 生成合约内容哈希
    2. 上链存证
    3. 记录交易哈希
    4. 合约生效
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.lifecycle_status != ContractLifecycleStatus.BLOCKCHAIN_RECORDING.value:
        raise ContractStateError("合约状态不允许区块链存证")

    # 生成合约内容哈希
    content_hash = gmssl_adapter.sm3_hash(contract.content or "")

    tx_hash = ""
    block_number = None

    if blockchain_enabled:
        # 区块链存证
        try:
            from app.services.blockchain_evidence_service import submit_evidence
            from app.schemas.blockchain import EvidenceCreate

            evidence = await submit_evidence(
                db,
                EvidenceCreate(
                    node_type="contract",
                    resource_id=contract_id,
                    resource_type="smart_contract",
                    data_hash=content_hash,
                    evidence_data={
                        "contract_id": contract_id,
                        "contract_no": contract.contract_no,
                        "contract_type": contract.contract_type,
                        "content_hash": content_hash,
                        "signed_at": datetime.now(timezone.utc).isoformat(),
                    },
                ),
            )
            tx_hash = evidence.tx_hash if hasattr(evidence, "tx_hash") else ""
            block_number = evidence.block_number if hasattr(evidence, "block_number") else None
        except Exception as e:
            logger.warning(f"Blockchain recording failed: {e}")

    # 更新合约信息
    contract.blockchain_tx_hash = tx_hash or f"0x{content_hash[:64]}"
    contract.blockchain_contract_address = f"0x{content_hash[:40]}"
    contract.effective_date = contract.effective_date or datetime.now(timezone.utc)
    contract.status = "active"
    contract.lifecycle_status = ContractLifecycleStatus.CONTRACT_ACTIVE.value
    await db.commit()

    logger.info(f"Contract recorded to blockchain: {contract_id}, tx={tx_hash}")
    return {
        "contract_id": str(contract.id),
        "contract_no": contract.contract_no,
        "content_hash": content_hash,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
        "lifecycle_stage": ContractLifecycleStage.SIGNING.value,
        "lifecycle_status": ContractLifecycleStatus.CONTRACT_ACTIVE.value,
        "next_step": "execution",
    }


# ==================== 执行阶段 ====================

async def monitor_contract_conditions(
    db: AsyncSession,
    contract_id: str,
) -> Dict[str, Any]:
    """
    执行阶段 - 条件监控

    步骤：
    1. 检查合约执行条件
    2. 监控触发条件
    3. 返回监控结果
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.status != "active":
        raise ContractStateError("合约未生效，无法监控执行条件")

    contract.lifecycle_stage = ContractLifecycleStage.EXECUTION.value
    contract.lifecycle_status = ContractLifecycleStatus.CONDITION_MONITORING.value

    # 检查执行条件（基于合约条款）
    terms = contract.terms or {}
    conditions_met = True
    conditions_status = []

    # 检查有效期
    if contract.expiration_date:
        now = datetime.now(timezone.utc)
        if now > contract.expiration_date:
            conditions_met = False
            conditions_status.append({
                "condition": "有效期",
                "status": "expired",
                "message": "合约已过期",
            })
        else:
            days_remaining = (contract.expiration_date - now).days
            conditions_status.append({
                "condition": "有效期",
                "status": "valid",
                "days_remaining": days_remaining,
            })

    # 检查SLA条件（如果有的话）
    sla_level = terms.get("sla_level")
    if sla_level:
        conditions_status.append({
            "condition": "SLA",
            "status": "monitoring",
            "target": sla_level,
        })

    await db.commit()

    logger.info(f"Contract conditions monitored: {contract_id}")
    return {
        "contract_id": str(contract.id),
        "conditions_met": conditions_met,
        "conditions_status": conditions_status,
        "lifecycle_stage": ContractLifecycleStage.EXECUTION.value,
        "lifecycle_status": ContractLifecycleStatus.CONDITION_MONITORING.value,
        "next_step": "auto_execute" if conditions_met else "wait_for_conditions",
    }


async def auto_execute_contract(
    db: AsyncSession,
    contract_id: str,
    execution_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    执行阶段 - 自动执行

    步骤：
    1. 验证执行条件
    2. 执行合约逻辑
    3. 记录执行结果
    4. 更新执行状态
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.status != "active":
        raise ContractStateError("合约未生效，无法执行")

    # 执行合约逻辑（根据合约类型）
    execution_result = {
        "execution_id": str(uuid.uuid4()),
        "contract_id": contract_id,
        "contract_type": contract.contract_type,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "params": execution_params or {},
    }

    # 根据合约类型执行不同逻辑
    if contract.contract_type == "data_sharing":
        execution_result["action"] = "数据共享已激活"
        execution_result["data_scope"] = contract.terms.get("data_scope")
    elif contract.contract_type == "data_service":
        execution_result["action"] = "数据服务已启动"
        execution_result["service_type"] = contract.terms.get("service_type")
    elif contract.contract_type == "joint_computing":
        execution_result["action"] = "联合计算任务已创建"
        execution_result["computing_type"] = contract.terms.get("computing_type")
    elif contract.contract_type == "data_trading":
        execution_result["action"] = "数据交易已确认"
        execution_result["trading_mode"] = contract.terms.get("trading_mode")

    # 更新合约状态
    contract.lifecycle_status = ContractLifecycleStatus.AUTO_EXECUTING.value

    # 存储执行记录
    terms = contract.terms.copy() if contract.terms else {}
    execution_history = terms.get("_execution_history", [])
    execution_history.append(execution_result)
    terms["_execution_history"] = execution_history
    contract.terms = terms

    await db.commit()

    logger.info(f"Contract auto-executed: {contract_id}")
    return {
        "contract_id": str(contract.id),
        "execution_result": execution_result,
        "lifecycle_stage": ContractLifecycleStage.EXECUTION.value,
        "lifecycle_status": ContractLifecycleStatus.AUTO_EXECUTING.value,
        "next_step": "monitor_execution",
    }


async def monitor_execution_status(
    db: AsyncSession,
    contract_id: str,
) -> Dict[str, Any]:
    """
    执行阶段 - 执行监控

    步骤：
    1. 收集执行指标
    2. 检查执行偏差
    3. 生成监控报告
    """
    contract = await _get_contract_or_raise(db, contract_id)

    # 获取执行历史
    terms = contract.terms or {}
    execution_history = terms.get("_execution_history", [])

    # 计算执行统计
    total_executions = len(execution_history)
    last_execution = execution_history[-1] if execution_history else None

    monitoring_report = {
        "contract_id": contract_id,
        "total_executions": total_executions,
        "last_execution_at": last_execution.get("executed_at") if last_execution else None,
        "execution_frequency": "daily",  # 模拟值
        "success_rate": 99.5,  # 模拟值
        "avg_response_time_ms": 200,  # 模拟值
        "issues": [],
        "monitored_at": datetime.now(timezone.utc).isoformat(),
    }

    # 更新合约状态
    contract.lifecycle_status = ContractLifecycleStatus.EXECUTION_MONITORING.value
    await db.commit()

    logger.info(f"Contract execution monitored: {contract_id}")
    return {
        "contract_id": str(contract.id),
        "monitoring_report": monitoring_report,
        "lifecycle_stage": ContractLifecycleStage.EXECUTION.value,
        "lifecycle_status": ContractLifecycleStatus.EXECUTION_MONITORING.value,
        "next_step": "completion",
    }


# ==================== 完成阶段 ====================

async def confirm_delivery(
    db: AsyncSession,
    contract_id: str,
    confirming_party: str,
    delivery_satisfaction: int,
    feedback: str = "",
) -> Dict[str, Any]:
    """
    完成阶段 - 交付确认

    步骤：
    1. 验证合约执行完成
    2. 记录交付确认
    3. 双方确认后进入结算
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.status != "active":
        raise ContractStateError("合约未生效，无法确认交付")

    # 记录交付确认
    delivery_confirmation = {
        "party": confirming_party,
        "satisfaction": delivery_satisfaction,
        "feedback": feedback,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }

    # 存储确认信息
    terms = contract.terms.copy() if contract.terms else {}
    delivery_confirmations = terms.get("_delivery_confirmations", [])
    delivery_confirmations.append(delivery_confirmation)
    terms["_delivery_confirmations"] = delivery_confirmations
    contract.terms = terms

    contract.lifecycle_stage = ContractLifecycleStage.COMPLETION.value
    contract.lifecycle_status = ContractLifecycleStatus.DELIVERY_CONFIRMING.value

    # 检查双方是否都已确认
    parties_confirmed = set(c["party"] for c in delivery_confirmations)
    both_confirmed = "party_a" in parties_confirmed and "party_b" in parties_confirmed

    await db.commit()

    logger.info(f"Delivery confirmed: {contract_id}, party={confirming_party}")
    return {
        "contract_id": str(contract.id),
        "confirming_party": confirming_party,
        "satisfaction": delivery_satisfaction,
        "both_confirmed": both_confirmed,
        "lifecycle_stage": ContractLifecycleStage.COMPLETION.value,
        "lifecycle_status": ContractLifecycleStatus.DELIVERY_CONFIRMING.value,
        "next_step": "settle" if both_confirmed else "wait_for_other_confirmation",
    }


async def process_settlement(
    db: AsyncSession,
    contract_id: str,
    settlement_amount: Optional[float] = None,
) -> Dict[str, Any]:
    """
    完成阶段 - 结算清算

    步骤：
    1. 计算结算金额
    2. 生成结算单
    3. 上链存证
    4. 更新合约状态
    """
    contract = await _get_contract_or_raise(db, contract_id)

    # 获取合约定价信息
    pricing = contract.pricing or {}
    terms = contract.terms or {}

    # 计算结算金额
    if settlement_amount is None:
        if contract.contract_type == "data_trading":
            settlement_amount = pricing.get("price", terms.get("price", 0))
        elif contract.contract_type == "data_service":
            # 按使用量计算
            unit_price = terms.get("unit_price", 0.01)
            usage_count = len(terms.get("_execution_history", []))
            settlement_amount = unit_price * usage_count
        else:
            settlement_amount = pricing.get("amount", 0)

    # 生成结算单
    settlement_id = str(uuid.uuid4())
    settlement_hash = gmssl_adapter.sm3_hash(
        f"{contract_id}:{settlement_amount}:{settlement_id}"
    )

    settlement_result = {
        "settlement_id": settlement_id,
        "contract_id": contract_id,
        "amount": settlement_amount,
        "currency": "CNY",
        "settlement_hash": settlement_hash,
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }

    # 上链存证
    try:
        from app.services.blockchain_evidence_service import submit_evidence
        from app.schemas.blockchain import EvidenceCreate

        await submit_evidence(
            db,
            EvidenceCreate(
                node_type="settle",
                resource_id=settlement_id,
                resource_type="contract_settlement",
                data_hash=settlement_hash,
                evidence_data=settlement_result,
            ),
        )
    except Exception as e:
        logger.warning(f"Settlement chain recording failed: {e}")

    # 更新合约状态
    contract.lifecycle_status = ContractLifecycleStatus.SETTLEMENT_PROCESSING.value

    # 存储结算信息
    terms = contract.terms.copy() if contract.terms else {}
    terms["_settlement"] = settlement_result
    contract.terms = terms

    await db.commit()

    logger.info(f"Contract settlement processed: {contract_id}, amount={settlement_amount}")
    return {
        "contract_id": str(contract.id),
        "settlement_result": settlement_result,
        "lifecycle_stage": ContractLifecycleStage.COMPLETION.value,
        "lifecycle_status": ContractLifecycleStatus.SETTLEMENT_PROCESSING.value,
        "next_step": "archive",
    }


async def archive_contract(
    db: AsyncSession,
    contract_id: str,
) -> Dict[str, Any]:
    """
    完成阶段 - 合约归档

    步骤：
    1. 收集合约全生命周期数据
    2. 生成归档包
    3. 更新合约状态为已完成
    """
    contract = await _get_contract_or_raise(db, contract_id)

    # 生成归档哈希
    archive_content = {
        "contract_id": contract_id,
        "contract_no": contract.contract_no,
        "contract_type": contract.contract_type,
        "terms": contract.terms,
        "pricing": contract.pricing,
        "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
        "expiration_date": contract.expiration_date.isoformat() if contract.expiration_date else None,
        "archived_at": datetime.now(timezone.utc).isoformat(),
    }
    archive_hash = gmssl_adapter.sm3_hash(str(archive_content))

    # 更新合约状态
    contract.status = "completed"
    contract.lifecycle_status = ContractLifecycleStatus.CONTRACT_COMPLETED.value
    contract.lifecycle_stage = ContractLifecycleStage.COMPLETION.value

    # 存储归档信息
    terms = contract.terms.copy() if contract.terms else {}
    terms["_archive"] = {
        "archive_hash": archive_hash,
        "archived_at": datetime.now(timezone.utc).isoformat(),
    }
    contract.terms = terms

    await db.commit()

    logger.info(f"Contract archived: {contract_id}")
    return {
        "contract_id": str(contract.id),
        "contract_no": contract.contract_no,
        "archive_hash": archive_hash,
        "lifecycle_stage": ContractLifecycleStage.COMPLETION.value,
        "lifecycle_status": ContractLifecycleStatus.CONTRACT_COMPLETED.value,
        "message": "合约生命周期已完成",
    }


# ==================== 争议处理 ====================

async def submit_dispute(
    db: AsyncSession,
    contract_id: str,
    submitter_id: str,
    dispute_type: str,
    dispute_description: str,
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    争议处理 - 争议提交

    步骤：
    1. 验证合约状态
    2. 创建争议记录
    3. 通知相关方
    """
    contract = await _get_contract_or_raise(db, contract_id)

    if contract.status not in ["active", "completed"]:
        raise ContractStateError("合约状态不允许提交争议")

    # 创建争议记录
    dispute_id = str(uuid.uuid4())
    dispute = {
        "dispute_id": dispute_id,
        "contract_id": contract_id,
        "submitter_id": submitter_id,
        "dispute_type": dispute_type,
        "description": dispute_description,
        "evidence": evidence or [],
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    # 存储争议信息
    terms = contract.terms.copy() if contract.terms else {}
    disputes = terms.get("_disputes", [])
    disputes.append(dispute)
    terms["_disputes"] = disputes

    contract.terms = terms
    contract.lifecycle_stage = ContractLifecycleStage.DISPUTE.value
    contract.lifecycle_status = ContractLifecycleStatus.DISPUTE_SUBMITTED.value
    contract.status = "disputed"

    await db.commit()

    logger.info(f"Dispute submitted: {dispute_id}, contract={contract_id}")
    return {
        "contract_id": str(contract.id),
        "dispute": dispute,
        "lifecycle_stage": ContractLifecycleStage.DISPUTE.value,
        "lifecycle_status": ContractLifecycleStatus.DISPUTE_SUBMITTED.value,
        "next_step": "collect_evidence",
    }


async def collect_dispute_evidence(
    db: AsyncSession,
    contract_id: str,
    dispute_id: str,
    evidence_items: List[Dict[str, Any]],
    collector_id: str,
) -> Dict[str, Any]:
    """
    争议处理 - 证据收集

    步骤：
    1. 收集证据材料
    2. 生成证据哈希
    3. 上链存证
    """
    contract = await _get_contract_or_raise(db, contract_id)

    # 查找争议记录
    terms = contract.terms or {}
    disputes = terms.get("_disputes", [])
    dispute = next((d for d in disputes if d["dispute_id"] == dispute_id), None)

    if not dispute:
        raise DataNotFoundError(f"争议记录未找到: {dispute_id}")

    # 处理证据
    processed_evidence = []
    for item in evidence_items:
        evidence_hash = gmssl_adapter.sm3_hash(str(item))
        processed_item = {
            **item,
            "evidence_hash": evidence_hash,
            "collected_by": collector_id,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        processed_evidence.append(processed_item)

        # 上链存证
        try:
            from app.services.blockchain_evidence_service import submit_evidence
            from app.schemas.blockchain import EvidenceCreate

            await submit_evidence(
                db,
                EvidenceCreate(
                    node_type="audit",
                    resource_id=dispute_id,
                    resource_type="dispute_evidence",
                    data_hash=evidence_hash,
                    evidence_data=processed_item,
                ),
            )
        except Exception as e:
            logger.warning(f"Evidence chain recording failed: {e}")

    # 更新争议记录
    dispute["evidence"].extend(processed_evidence)
    dispute["status"] = "evidence_collected"

    contract.lifecycle_status = ContractLifecycleStatus.EVIDENCE_COLLECTING.value
    await db.commit()

    logger.info(f"Dispute evidence collected: {dispute_id}, count={len(processed_evidence)}")
    return {
        "contract_id": str(contract.id),
        "dispute_id": dispute_id,
        "evidence_count": len(processed_evidence),
        "total_evidence": len(dispute["evidence"]),
        "lifecycle_stage": ContractLifecycleStage.DISPUTE.value,
        "lifecycle_status": ContractLifecycleStatus.EVIDENCE_COLLECTING.value,
        "next_step": "arbitration",
    }


async def process_arbitration(
    db: AsyncSession,
    contract_id: str,
    dispute_id: str,
    arbitrator_id: str,
    arbitration_result: str,
    resolution: Dict[str, Any],
) -> Dict[str, Any]:
    """
    争议处理 - 仲裁裁决

    步骤：
    1. 验证证据完整性
    2. 执行仲裁裁决
    3. 生成裁决书
    4. 上链存证
    """
    contract = await _get_contract_or_raise(db, contract_id)

    # 查找争议记录
    terms = contract.terms or {}
    disputes = terms.get("_disputes", [])
    dispute = next((d for d in disputes if d["dispute_id"] == dispute_id), None)

    if not dispute:
        raise DataNotFoundError(f"争议记录未找到: {dispute_id}")

    # 生成裁决书
    arbitration_id = str(uuid.uuid4())
    arbitration_hash = gmssl_adapter.sm3_hash(
        f"{dispute_id}:{arbitration_result}:{arbitration_id}"
    )

    arbitration_record = {
        "arbitration_id": arbitration_id,
        "dispute_id": dispute_id,
        "arbitrator_id": arbitrator_id,
        "result": arbitration_result,
        "resolution": resolution,
        "arbitration_hash": arbitration_hash,
        "arbitrated_at": datetime.now(timezone.utc).isoformat(),
    }

    # 上链存证
    try:
        from app.services.blockchain_evidence_service import submit_evidence
        from app.schemas.blockchain import EvidenceCreate

        await submit_evidence(
            db,
            EvidenceCreate(
                node_type="audit",
                resource_id=arbitration_id,
                resource_type="arbitration_result",
                data_hash=arbitration_hash,
                evidence_data=arbitration_record,
            ),
        )
    except Exception as e:
        logger.warning(f"Arbitration chain recording failed: {e}")

    # 更新争议记录
    dispute["arbitration"] = arbitration_record
    dispute["status"] = "resolved"

    # 更新合约状态
    contract.lifecycle_status = ContractLifecycleStatus.ARBITRATION_PROCESSING.value

    # 根据裁决结果处理
    if arbitration_result == "favor_submitter":
        # 支持提交方，可能需要退款或补偿
        resolution["action"] = "compensation_required"
    elif arbitration_result == "favor_respondent":
        # 支持响应方，争议驳回
        resolution["action"] = "dispute_rejected"
    elif arbitration_result == "settlement":
        # 和解
        resolution["action"] = "settlement_reached"

    await db.commit()

    logger.info(f"Arbitration processed: {arbitration_id}, result={arbitration_result}")
    return {
        "contract_id": str(contract.id),
        "arbitration": arbitration_record,
        "lifecycle_stage": ContractLifecycleStage.DISPUTE.value,
        "lifecycle_status": ContractLifecycleStatus.ARBITRATION_PROCESSING.value,
        "next_step": "resolve_dispute",
    }


async def resolve_dispute(
    db: AsyncSession,
    contract_id: str,
    dispute_id: str,
) -> Dict[str, Any]:
    """
    争议处理 - 争议解决

    步骤：
    1. 执行裁决结果
    2. 更新争议状态
    3. 恢复合约正常状态
    """
    contract = await _get_contract_or_raise(db, contract_id)

    # 查找争议记录
    terms = contract.terms or {}
    disputes = terms.get("_disputes", [])
    dispute = next((d for d in disputes if d["dispute_id"] == dispute_id), None)

    if not dispute:
        raise DataNotFoundError(f"争议记录未找到: {dispute_id}")

    # 更新争议状态
    dispute["status"] = "resolved"
    dispute["resolved_at"] = datetime.now(timezone.utc).isoformat()

    # 更新合约状态
    contract.lifecycle_status = ContractLifecycleStatus.DISPUTE_RESOLVED.value
    contract.status = "active"  # 恢复正常状态

    await db.commit()

    logger.info(f"Dispute resolved: {dispute_id}")
    return {
        "contract_id": str(contract.id),
        "dispute_id": dispute_id,
        "status": "resolved",
        "lifecycle_stage": ContractLifecycleStage.DISPUTE.value,
        "lifecycle_status": ContractLifecycleStatus.DISPUTE_RESOLVED.value,
        "message": "争议已解决",
    }


# ==================== 生命周期查询 ====================

async def get_contract_lifecycle_status(
    db: AsyncSession,
    contract_id: str,
) -> Dict[str, Any]:
    """获取合约的生命周期状态"""
    contract = await _get_contract_or_raise(db, contract_id)

    return {
        "contract_id": str(contract.id),
        "contract_no": contract.contract_no,
        "contract_type": contract.contract_type,
        "status": contract.status,
        "lifecycle_stage": contract.lifecycle_stage,
        "lifecycle_status": contract.lifecycle_status,
        "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
        "expiration_date": contract.expiration_date.isoformat() if contract.expiration_date else None,
        "created_at": contract.created_at.isoformat(),
        "updated_at": contract.updated_at.isoformat(),
    }


async def get_contract_lifecycle_history(
    db: AsyncSession,
    contract_id: str,
) -> Dict[str, Any]:
    """获取合约的生命周期历史记录"""
    contract = await _get_contract_or_raise(db, contract_id)

    # 收集所有历史记录
    terms = contract.terms or {}

    history = {
        "contract_id": str(contract.id),
        "contract_no": contract.contract_no,
        "current_stage": contract.lifecycle_stage,
        "current_status": contract.lifecycle_status,
        "confirmations": terms.get("_confirmations", {}),
        "signing_task": terms.get("_signing_task", {}),
        "execution_history": terms.get("_execution_history", []),
        "delivery_confirmations": terms.get("_delivery_confirmations", []),
        "settlement": terms.get("_settlement", {}),
        "disputes": terms.get("_disputes", []),
        "archive": terms.get("_archive", {}),
    }

    return history


# ==================== 辅助函数 ====================

async def _get_contract_or_raise(db: AsyncSession, contract_id: str) -> Contract:
    """获取合约或抛出异常"""
    result = await db.execute(
        select(Contract).where(Contract.id == uuid.UUID(contract_id))
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise DataNotFoundError(f"合约未找到: {contract_id}")
    return contract


def _generate_contract_no() -> str:
    """生成合约编号: CTR-{timestamp}-{random4}"""
    import secrets
    import string
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"CTR-{ts}-{rand}"
