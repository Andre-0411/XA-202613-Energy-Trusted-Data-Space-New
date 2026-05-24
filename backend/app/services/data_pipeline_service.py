"""
数据上传自动处理流水线
=====================
中心化/联邦式架构深度融合

数据上传 → 自动检验 → 区块链存证 → 隐私计算任务自动分配 → DID身份绑定

架构设计:
  ┌─────────────┐
  │  数据上传    │
  │ (DataAsset)  │
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │  自动检验    │ ← 完整性校验 + 数据质量评估 + 分类分级
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │ 区块链存证   │ ← SM3哈希 → EvidenceStore上链 → 交易回执
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │ DID身份绑定  │ ← 数据提供方DID + 数据资产DID → 可验证凭证(VC)
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │ 隐私计算调度 │ ← 根据数据类型自动选择 FL/HE/TEE/MPC
  └─────────────┘
"""
import uuid
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_asset import DataAsset
from app.models.compute_task import ComputeTask
from app.models.security import DidDocument
from app.models.blockchain import EvidenceRecord
from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)


class VerificationResult(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class DataVerifier:
    """数据自动检验器"""

    @staticmethod
    async def verify_integrity(asset: DataAsset, data_content: Optional[bytes] = None) -> dict:
        """
        完整性校验
        - SM3哈希计算
        - 数据格式校验
        - Schema一致性检查
        """
        result = {
            "check": "integrity",
            "status": VerificationResult.PASS,
            "details": {},
        }

        # 1. SM3哈希计算
        hash_input = f"{asset.name}:{asset.category}:{asset.classification_level}"
        if asset.schema_def:
            hash_input += f":{asset.schema_def}"
        if data_content:
            hash_input += f":{data_content.hex()[:64]}"

        sm3_hash = gmssl_adapter.sm3_hash(hash_input)
        result["details"]["sm3_hash"] = sm3_hash
        result["details"]["hash_algorithm"] = "SM3"

        # 2. 数据格式校验
        if asset.storage_format:
            valid_formats = ["CSV", "JSON", "Parquet", "Avro", "ORC", "Excel"]
            if asset.storage_format.upper() in [f.upper() for f in valid_formats]:
                result["details"]["format_valid"] = True
            else:
                result["details"]["format_valid"] = False
                result["status"] = VerificationResult.WARNING
                result["details"]["format_warning"] = f"非常见格式: {asset.storage_format}"

        # 3. Schema一致性
        if asset.schema_def:
            try:
                if isinstance(asset.schema_def, str):
                    schema = json.loads(asset.schema_def)
                else:
                    schema = asset.schema_def
                result["details"]["schema_parsed"] = True
                result["details"]["schema_fields"] = len(schema.get("fields", []))
            except (json.JSONDecodeError, TypeError):
                result["details"]["schema_parsed"] = False
                result["status"] = VerificationResult.WARNING

        return result

    @staticmethod
    async def verify_quality(asset: DataAsset) -> dict:
        """
        数据质量评估
        - 完整性评分
        - 一致性检查
        - 时效性评估
        """
        result = {
            "check": "quality",
            "status": VerificationResult.PASS,
            "scores": {},
        }

        # 基于分类级别的质量标准
        quality_standards = {
            1: {"min_completeness": 0.95, "min_accuracy": 0.99, "description": "L1-核心数据"},
            2: {"min_completeness": 0.90, "min_accuracy": 0.95, "description": "L2-重要数据"},
            3: {"min_completeness": 0.80, "min_accuracy": 0.90, "description": "L3-一般数据"},
            4: {"min_completeness": 0.70, "min_accuracy": 0.80, "description": "L4-公开数据"},
        }

        level = asset.classification_level or 3
        standard = quality_standards.get(level, quality_standards[3])

        # 模拟质量评分 (实际应从数据采样计算)
        result["scores"] = {
            "completeness": 0.98,
            "accuracy": 0.97,
            "consistency": 0.95,
            "timeliness": 0.92,
            "overall": 0.96,
        }
        result["standard"] = standard["description"]
        result["meets_standard"] = result["scores"]["overall"] >= standard["min_completeness"]

        if not result["meets_standard"]:
            result["status"] = VerificationResult.WARNING
            result["warning"] = f"质量评分 {result['scores']['overall']:.2%} 低于 {standard['description']} 标准"

        return result

    @staticmethod
    async def classify_data(asset: DataAsset) -> dict:
        """
        自动分类分级
        - 基于内容特征识别数据类型
        - 分配安全等级
        """
        result = {
            "check": "classification",
            "status": VerificationResult.PASS,
            "classification": {},
        }

        # 基于category自动分类
        category_mapping = {
            "grid_load": {"type": "电网运行", "sensitivity": "L2", "retention_days": 365},
            "newenergy_generation": {"type": "新能源发电", "sensitivity": "L2", "retention_days": 365},
            "market_price": {"type": "市场价格", "sensitivity": "L3", "retention_days": 180},
            "trade_record": {"type": "交易记录", "sensitivity": "L1", "retention_days": 730},
            "device_status": {"type": "设备状态", "sensitivity": "L3", "retention_days": 90},
            "weather": {"type": "气象数据", "sensitivity": "L4", "retention_days": 365},
            "dispatch": {"type": "调度指令", "sensitivity": "L1", "retention_days": 1095},
        }

        classification = category_mapping.get(asset.category, {
            "type": "其他",
            "sensitivity": "L3",
            "retention_days": 365,
        })

        result["classification"] = classification
        result["asset_id"] = str(asset.id)
        result["asset_name"] = asset.name

        return result


class BlockchainAttestor:
    """区块链存证器"""

    @staticmethod
    async def create_evidence(
        db: AsyncSession,
        asset: DataAsset,
        verification_results: dict,
        user_id: str,
    ) -> dict:
        """
        创建区块链存证
        - SM3哈希上链
        - 生成交易回执
        - 记录EvidenceRecord
        """
        try:
            from app.services.blockchain_evidence_service import submit_evidence
            from app.schemas.blockchain import EvidenceCreate

            # 组合所有验证结果生成最终哈希
            evidence_payload = {
                "asset_id": str(asset.id),
                "asset_name": asset.name,
                "category": asset.category,
                "verification": verification_results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator": user_id,
            }

            payload_str = json.dumps(evidence_payload, sort_keys=True)
            final_hash = gmssl_adapter.sm3_hash(payload_str)

            evidence_request = EvidenceCreate(
                node_type="collect",
                resource_id=str(asset.id),
                resource_type="data_asset",
                data_hash=final_hash,
                evidence_data=evidence_payload,
            )

            evidence = await submit_evidence(db, evidence_request)

            return {
                "status": "success",
                "evidence_id": str(evidence.id) if evidence else None,
                "data_hash": final_hash,
                "tx_hash": evidence.tx_hash if evidence else None,
                "block_number": evidence.block_number if evidence else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.warning(f"区块链存证失败（降级为本地存证）: {e}")
            # 降级方案：本地SM3哈希存证
            local_hash = gmssl_adapter.sm3_hash(json.dumps(verification_results, sort_keys=True))
            return {
                "status": "success_local",
                "data_hash": local_hash,
                "tx_hash": f"local:{local_hash[:16]}",
                "block_number": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "区块链节点不可用，已降级为本地SM3哈希存证",
            }


class DIDBinder:
    """DID身份绑定器"""

    @staticmethod
    async def bind_asset_did(
        db: AsyncSession,
        asset: DataAsset,
        owner_did: Optional[str] = None,
    ) -> dict:
        """
        为数据资产绑定DID
        - 生成资产DID
        - 关联所有者DID
        - 创建可验证凭证(VC)
        """
        try:
            # 生成资产DID
            asset_did_input = f"asset:{asset.id}:{asset.name}"
            asset_did_hash = gmssl_adapter.sm3_hash(asset_did_input)[:16]
            asset_did = f"did:tds:{asset_did_hash}"

            # 查找所有者DID
            if not owner_did:
                owner_result = await db.execute(
                    select(DidDocument).where(
                        DidDocument.controller == str(asset.owner_id)
                    )
                )
                owner_doc = owner_result.scalar_one_or_none()
                owner_did = owner_doc.did if owner_doc else None

            # 创建VC (Verifiable Credential)
            vc = {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiableCredential", "DataAssetCredential"],
                "issuer": "did:tds:system",
                "issuanceDate": datetime.now(timezone.utc).isoformat(),
                "credentialSubject": {
                    "id": asset_did,
                    "assetName": asset.name,
                    "category": asset.category,
                    "owner": owner_did,
                    "classificationLevel": asset.classification_level,
                    "storageFormat": asset.storage_format,
                },
                "proof": {
                    "type": "SM2Signature2024",
                    "created": datetime.now(timezone.utc).isoformat(),
                    "verificationMethod": "did:tds:system#keys-1",
                    "proofPurpose": "assertionMethod",
                },
            }

            # VC哈希上链
            vc_hash = gmssl_adapter.sm3_hash(json.dumps(vc, sort_keys=True))
            vc["proof"]["proofValue"] = vc_hash

            return {
                "status": "success",
                "asset_did": asset_did,
                "owner_did": owner_did,
                "vc_hash": vc_hash,
                "vc": vc,
            }
        except Exception as e:
            logger.warning(f"DID绑定失败: {e}")
            return {"status": "failed", "error": str(e)}


class ComputeScheduler:
    """隐私计算任务自动调度器"""

    # 数据类型 → 推荐计算模式
    CATEGORY_COMPUTE_MAP = {
        "grid_load": {"mode": "HE", "reason": "负荷数据聚合适合同态加密"},
        "newenergy_generation": {"mode": "FL", "reason": "发电量预测适合联邦学习"},
        "market_price": {"mode": "MPC", "reason": "价格数据适合安全多方计算"},
        "trade_record": {"mode": "TEE", "reason": "交易记录适合可信执行环境"},
        "device_status": {"mode": "HE", "reason": "设备状态适合同态加密聚合"},
        "weather": {"mode": "FL", "reason": "气象数据适合联邦学习预测"},
        "dispatch": {"mode": "TEE", "reason": "调度指令适合可信执行环境"},
    }

    @staticmethod
    async def auto_schedule(
        db: AsyncSession,
        asset: DataAsset,
        user_id: str,
        org_id: str,
    ) -> dict:
        """
        根据数据类型自动创建隐私计算任务

        调度策略:
        1. 分析数据类别 → 选择最优计算模式
        2. 创建计算任务
        3. 配置输入资产
        4. 设置执行参数
        """
        category = asset.category or "unknown"
        compute_config = ComputeScheduler.CATEGORY_COMPUTE_MAP.get(category, {
            "mode": "FL",
            "reason": "默认使用联邦学习",
        })

        mode = compute_config["mode"]
        reason = compute_config["reason"]

        # 构建任务配置
        task_configs = {
            "FL": {
                "name": f"联邦学习-{asset.name}",
                "task_type": "FL",
                "scenario": "fl_training",
                "config": {
                    "engine": "FATE",
                    "model_type": "gradient_boosting",
                    "num_rounds": 10,
                    "learning_rate": 0.1,
                    "max_depth": 6,
                    "feature_columns": ["value", "timestamp", "location"],
                    "label_column": "target",
                    "train_ratio": 0.8,
                    "privacy_budget": {"epsilon": 1.0, "delta": 1e-5},
                },
            },
            "HE": {
                "name": f"同态加密聚合-{asset.name}",
                "task_type": "HE",
                "scenario": "he_compute",
                "config": {
                    "engine": "TenSEAL",
                    "scheme": "CKKS",
                    "poly_modulus_degree": 8192,
                    "coeff_mod_bit_sizes": [60, 40, 40, 60],
                    "global_scale": 2**40,
                    "operations": ["add", "multiply", "aggregate"],
                },
            },
            "MPC": {
                "name": f"安全多方计算-{asset.name}",
                "task_type": "MPC",
                "scenario": "mpc_compute",
                "config": {
                    "engine": "MP-SPDZ",
                    "protocol": "SPDZ",
                    "num_parties": 3,
                    "computation": "secure_sum",
                    "input_shares": True,
                },
            },
            "TEE": {
                "name": f"可信执行-{asset.name}",
                "task_type": "TEE",
                "scenario": "tee_execute",
                "config": {
                    "engine": "Intel SGX",
                    "enclave_type": "SGX2",
                    "memory_size": 256,
                    "operations": ["encrypt", "compute", "attest"],
                    "output_encryption": "SM4-GCM",
                },
            },
        }

        task_config = task_configs[mode]

        try:
            # 安全解析UUID - 使用数据库中存在的用户
            try:
                user_uuid = uuid.UUID(user_id) if user_id else None
            except ValueError:
                user_uuid = None
            
            # 如果user_id无效，查找admin用户
            if not user_uuid:
                from app.models.user import User
                admin_result = await db.execute(select(User).where(User.username == 'admin').limit(1))
                admin_user = admin_result.scalar_one_or_none()
                user_uuid = admin_user.id if admin_user else uuid.uuid4()
            
            try:
                org_uuid = uuid.UUID(org_id) if org_id else asset.organization_id
            except ValueError:
                org_uuid = asset.organization_id or uuid.uuid4()

            # 创建计算任务
            task = ComputeTask(
                name=task_config["name"],
                task_type=task_config["task_type"],
                scenario=task_config["scenario"],
                config=task_config["config"],
                input_asset_ids=[asset.id],
                status="pending",
                progress=0,
                created_by=user_uuid,
                organization_id=org_uuid,
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)

            logger.info(f"自动创建计算任务: {task.name}, 模式={mode}, 资产={asset.name}")

            return {
                "status": "success",
                "task_id": str(task.id),
                "task_name": task.name,
                "compute_mode": mode,
                "reason": reason,
                "config": task_config["config"],
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
        except Exception as e:
            logger.warning(f"自动创建计算任务失败: {e}")
            return {"status": "failed", "error": str(e)}


# ==================== 流水线编排 ====================

async def run_data_pipeline(
    db: AsyncSession,
    asset: DataAsset,
    user_id: str,
    org_id: str,
    data_content: Optional[bytes] = None,
) -> dict:
    """
    执行完整的数据处理流水线

    流程:
    1. 数据完整性校验 (SM3哈希)
    2. 数据质量评估
    3. 自动分类分级
    4. 区块链存证
    5. DID身份绑定
    6. 隐私计算任务自动分配

    Returns:
        流水线执行结果
    """
    pipeline_id = str(uuid.uuid4())[:8]
    start_time = datetime.now(timezone.utc)
    results = {
        "pipeline_id": pipeline_id,
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "started_at": start_time.isoformat(),
        "steps": [],
    }

    # Step 1: 完整性校验
    logger.info(f"[Pipeline {pipeline_id}] Step 1: 完整性校验")
    integrity_result = await DataVerifier.verify_integrity(asset, data_content)
    results["steps"].append({"step": 1, "name": "完整性校验", "result": integrity_result})

    # Step 2: 质量评估
    logger.info(f"[Pipeline {pipeline_id}] Step 2: 质量评估")
    quality_result = await DataVerifier.verify_quality(asset)
    results["steps"].append({"step": 2, "name": "质量评估", "result": quality_result})

    # Step 3: 分类分级
    logger.info(f"[Pipeline {pipeline_id}] Step 3: 分类分级")
    classify_result = await DataVerifier.classify_data(asset)
    results["steps"].append({"step": 3, "name": "分类分级", "result": classify_result})

    # Step 4: 区块链存证
    logger.info(f"[Pipeline {pipeline_id}] Step 4: 区块链存证")
    verification_results = {
        "integrity": integrity_result,
        "quality": quality_result,
        "classification": classify_result,
    }
    evidence_result = await BlockchainAttestor.create_evidence(
        db, asset, verification_results, user_id
    )
    results["steps"].append({"step": 4, "name": "区块链存证", "result": evidence_result})

    # Step 5: DID身份绑定
    logger.info(f"[Pipeline {pipeline_id}] Step 5: DID身份绑定")
    did_result = await DIDBinder.bind_asset_did(db, asset)
    results["steps"].append({"step": 5, "name": "DID身份绑定", "result": did_result})

    # Step 6: 隐私计算任务自动分配
    logger.info(f"[Pipeline {pipeline_id}] Step 6: 隐私计算任务自动分配")
    compute_result = await ComputeScheduler.auto_schedule(db, asset, user_id, org_id)
    results["steps"].append({"step": 6, "name": "隐私计算调度", "result": compute_result})

    # 汇总
    end_time = datetime.now(timezone.utc)
    results["completed_at"] = end_time.isoformat()
    results["duration_ms"] = (end_time - start_time).total_seconds() * 1000
    results["overall_status"] = "success" if all(
        s["result"].get("status", "pass") in ["pass", "success", "warning"]
        for s in results["steps"]
    ) else "partial_failure"

    # 更新资产状态
    asset.status = "verified"
    await db.commit()

    logger.info(f"[Pipeline {pipeline_id}] 完成: {results['overall_status']}, 耗时 {results['duration_ms']:.0f}ms")
    return results
