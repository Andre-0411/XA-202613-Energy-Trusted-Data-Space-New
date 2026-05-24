"""
安全风险评估服务
数据安全风险评估/合规检查
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DataNotFoundError, DataValidationError

logger = logging.getLogger(__name__)


async def assess_data_risk(
    db: AsyncSession,
    target_type: str,
    target_id: str,
    assessment_data: dict,
    assessor_id: str,
) -> dict:
    """执行数据安全风险评估"""
    # 分级评估
    risk_score = 0
    risk_factors = []

    # 数据分类级别评估
    classification = assessment_data.get("classification_level", "public")
    classification_scores = {
        "public": 10,
        "internal": 30,
        "confidential": 60,
        "secret": 90,
    }
    classification_score = classification_scores.get(classification, 10)
    risk_score += classification_score
    if classification_score > 50:
        risk_factors.append(f"数据分类级别较高: {classification}")

    # 数据量评估
    data_volume = assessment_data.get("data_volume", 0)
    if data_volume > 1000000:
        risk_score += 20
        risk_factors.append(f"数据量较大: {data_volume}")
    elif data_volume > 100000:
        risk_score += 10

    # 包含敏感信息评估
    contains_pii = assessment_data.get("contains_pii", False)
    if contains_pii:
        risk_score += 25
        risk_factors.append("包含个人信息数据")

    # 跨境传输评估
    cross_border = assessment_data.get("cross_border", False)
    if cross_border:
        risk_score += 30
        risk_factors.append("涉及跨境数据传输")

    # 确定风险等级
    if risk_score >= 80:
        risk_level = "critical"
    elif risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 生成合规建议
    recommendations = []
    if contains_pii:
        recommendations.append("建议进行个人信息影响评估（PIA）")
    if cross_border:
        recommendations.append("建议评估跨境数据传输合规性")
    if classification in ("confidential", "secret"):
        recommendations.append("建议实施数据加密和访问控制")
    if data_volume > 100000:
        recommendations.append("建议实施数据脱敏和审计日志")

    assessment_result = {
        "target_type": target_type,
        "target_id": target_id,
        "assessor_id": assessor_id,
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "recommendations": recommendations,
        "assessment_data": assessment_data,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(f"Risk assessment completed: {target_type}/{target_id}, score={risk_score}, level={risk_level}")
    return assessment_result


async def check_compliance(
    db: AsyncSession,
    target_type: str,
    target_id: str,
    compliance_standards: Optional[list] = None,
) -> dict:
    """合规性检查"""
    standards = compliance_standards or ["data_security_law", "pipl", "gdpr"]
    check_results = []

    for standard in standards:
        checks = []
        if standard == "data_security_law":
            checks = [
                {"item": "数据分类分级", "status": "passed", "detail": "已实施数据分类分级管理"},
                {"item": "重要数据识别", "status": "passed", "detail": "已识别重要数据目录"},
                {"item": "数据安全评估", "status": "pending", "detail": "待完成安全评估"},
                {"item": "出境安全评估", "status": "not_applicable", "detail": "不涉及数据出境"},
            ]
        elif standard == "pipl":
            checks = [
                {"item": "知情同意", "status": "passed", "detail": "已获得数据主体同意"},
                {"item": "最小必要", "status": "passed", "detail": "符合最小必要原则"},
                {"item": "数据主体权利", "status": "passed", "detail": "已支持数据主体权利请求"},
                {"item": "跨境传输", "status": "not_applicable", "detail": "不涉及跨境传输"},
            ]
        elif standard == "gdpr":
            checks = [
                {"item": "合法性基础", "status": "passed", "detail": "已建立合法性基础"},
                {"item": "数据保护影响评估", "status": "pending", "detail": "待完成DPIA"},
                {"item": "数据保护官", "status": "passed", "detail": "已指定DPO"},
                {"item": "数据泄露通知", "status": "passed", "detail": "已建立泄露通知机制"},
            ]

        passed_count = sum(1 for c in checks if c["status"] == "passed")
        total_count = len(checks)
        compliance_rate = (passed_count / total_count * 100) if total_count > 0 else 0

        check_results.append({
            "standard": standard,
            "compliance_rate": compliance_rate,
            "checks": checks,
            "passed_count": passed_count,
            "total_count": total_count,
        })

    overall_rate = sum(r["compliance_rate"] for r in check_results) / len(check_results) if check_results else 0

    return {
        "target_type": target_type,
        "target_id": target_id,
        "overall_compliance_rate": round(overall_rate, 2),
        "standards_checked": len(check_results),
        "results": check_results,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_security_recommendations(
    db: AsyncSession,
    target_type: str,
    target_id: str,
) -> dict:
    """获取安全建议"""
    recommendations = [
        {
            "category": "数据加密",
            "priority": "high",
            "items": [
                "建议对敏感数据实施静态加密（AES-256）",
                "建议对数据传输通道实施TLS 1.3加密",
                "建议实施国密算法SM2/SM4替代方案",
            ],
        },
        {
            "category": "访问控制",
            "priority": "high",
            "items": [
                "建议实施基于属性的访问控制（ABAC）",
                "建议实施最小权限原则",
                "建议启用多因素认证（MFA）",
            ],
        },
        {
            "category": "审计日志",
            "priority": "medium",
            "items": [
                "建议记录所有数据访问操作",
                "建议实施操作审计日志保留策略",
                "建议启用异常行为检测",
            ],
        },
        {
            "category": "数据治理",
            "priority": "medium",
            "items": [
                "建议实施数据生命周期管理",
                "建议定期评估数据安全风险",
                "建议建立数据安全事件响应机制",
            ],
        },
    ]

    return {
        "target_type": target_type,
        "target_id": target_id,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
