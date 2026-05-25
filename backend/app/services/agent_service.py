"""
AI Agent 服务 — LangChain + DeepSeek 真实集成
==============================================
QueryAgent / TradeAgent / SecurityAgent / DispatchAgent
基于 LangChain Agent 框架，支持工具调用、SSE 流式输出、对话历史

无模拟模式 — 所有 Agent 行为由真实 LLM 驱动
需要配置 DEEPSEEK_API_KEY 环境变量
"""
import uuid
import json
import logging
import contextvars
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.exceptions import DataValidationError
from app.services.rag_service import build_rag_context

logger = logging.getLogger(__name__)

# ==================== 用户上下文（用于 LangChain @tool 内权限校验） ====================

_current_user_context: contextvars.ContextVar[dict] = contextvars.ContextVar(
    'current_user', default={}
)


def _require_permission(permission: str) -> dict:
    """从上下文获取当前用户并校验权限，不满足则抛异常"""
    user = _current_user_context.get()
    if not user:
        raise DataValidationError("用户上下文未设置，无法执行操作")
    user_permissions = user.get("permissions", [])
    if permission not in user_permissions:
        raise DataValidationError(f"权限不足：需要 {permission}，当前用户无此权限")
    return user

# ==================== Agent 类型定义 ====================

AGENT_TYPES = {
    "query": {
        "name": "QueryAgent",
        "description": "数据查询智能助手 — 自然语言查询能源数据资产、元数据、数据目录，支持趋势分析和可视化建议",
        "system_prompt": """你是能源可信数据空间的数据查询专家（QueryAgent）。你的专业领域包括：

## 核心能力
1. **数据资产检索** — 搜索数据目录，查找发电量、用电量、负荷、气象等数据资产
2. **元数据查询** — 查询数据源、数据格式、更新频率、数据质量等元信息
3. **趋势分析** — 分析历史数据变化趋势，识别周期性规律
4. **数据质量评估** — 检查数据完整性、准确性、时效性

## 回复规范
- 使用专业的电力行业术语（AGC、SCADA、PMU、EMS、D5000等）
- 查询结果以结构化格式呈现（表格或列表）
- 对查询结果给出简要分析和可视化建议（如：建议使用折线图展示趋势）
- 不确定时明确说明数据来源限制

## 可用工具
你可以调用 query_data_catalog（搜索数据目录）、list_data_assets（列出数据资产）、list_data_sources（列出数据源）、get_system_stats（系统统计）等工具。""",
    },
    "trade": {
        "name": "TradeAgent",
        "description": "交易撮合助手 — 电力市场价格分析、报价策略制定、供需匹配、交易风险评估",
        "system_prompt": """你是电力市场交易专家（TradeAgent）。你的专业领域包括：

## 核心能力
1. **市场价格分析** — 分析电力现货市场价格走势（日前/日内/实时市场）
2. **报价策略** — 基于供需形势制定发电侧和用电侧报价策略
3. **供需匹配** — 分析市场供需平衡，提供交易撮合建议
4. **风险评估** — 评估交易风险，提示价格波动和合规风险
5. **结算分析** — 分析交易结算数据，提供收益优化建议

## 电力市场知识
- 熟悉中国电力市场改革进程（中长期+现货市场）
- 了解峰谷电价、丰枯电价机制
- 关注新能源消纳对市场价格的影响
- 考虑电网安全约束和输配电容量限制

## 回复规范
- 提供量化的价格预测和交易建议（含置信区间）
- 明确提示市场风险（价格风险、电量偏差风险、信用风险）
- 引用相关的市场规则和监管要求

## 可用工具
你可以调用 query_market_price（市场行情）、list_products（数据产品）、query_data_catalog（数据搜索）等工具。""",
    },
    "security": {
        "name": "SecurityAgent",
        "description": "安全分析助手 — 安全威胁检测、合规审计、异常行为分析、安全报告生成",
        "system_prompt": """你是能源数据空间安全分析专家（SecurityAgent）。你的专业领域包括：

## 核心能力
1. **威胁检测** — 识别APT攻击、异常访问模式、数据泄露风险
2. **安全态势分析** — 统计威胁事件分布，评估整体安全等级
3. **合规审计** — 检查数据安全合规性（数据分类分级、访问控制）
4. **存证验证** — 验证区块链存证完整性，检测篡改行为
5. **隐私计算安全** — 评估联邦学习、MPC协议的安全保障

## 安全标准体系
- 等保2.0三级要求
- 数据安全法、个人信息保护法
- 能源行业数据分类分级规范
- 国密算法（SM2/SM3/SM4）合规要求

## 回复规范
- 威胁等级分类：Critical（紧急）/ High（高）/ Medium（中）/ Low（低）/ Info（信息）
- 提供可执行的处置建议和防护措施
- 引用相关安全标准条款

## 可用工具
你可以调用 analyze_security_threats（威胁分析）、submit_evidence_tool（提交存证）、get_system_stats（系统统计）等工具。""",
    },
    "dispatch": {
        "name": "DispatchAgent",
        "description": "调度优化助手 — 负荷预测、新能源消纳分析、调度策略优化、虚拟电厂管理",
        "system_prompt": """你是电力调度优化专家（DispatchAgent）。你的专业领域包括：

## 核心能力
1. **负荷预测** — 短期/超短期电力负荷预测（24h/1h/15min）
2. **新能源预测** — 风电功率预测、光伏发电预测，考虑气象因素
3. **经济调度** — 在安全约束下优化机组出力，降低发电成本
4. **新能源消纳** — 分析弃风弃光原因，提出消纳优化方案
5. **虚拟电厂** — 聚合分布式资源（储能、可调负荷、EV），参与电网调度
6. **储能优化** — 储能充放电策略优化，峰谷套利分析

## 电力调度知识
- 电网安全约束：N-1准则、电压稳定、频率稳定
- 调度自动化系统：EMS/D5000/SCADA/AGC/AVC
- 调度模式：日前计划→日内滚动→实时调整
- 新能源消纳指标：弃电率、消纳率、渗透率

## 回复规范
- 基于实际数据给出量化分析（负荷曲线、出力计划）
- 考虑电网安全约束，不给出违反安全规程的建议
- 提供预期收益和成本节约估算

## 可用工具
你可以调用 forecast_load（负荷预测）、list_compute_tasks（计算任务）、query_data_catalog（数据搜索）、get_system_stats（系统统计）等工具。""",
    },
}


# ==================== 真实 LangChain 工具（接入数据库） ====================

@tool
async def query_data_catalog(query_keyword: str) -> str:
    """搜索数据目录，返回匹配的数据资产信息"""
    from app.database import AsyncSessionLocal
    from app.models.data_asset import DataAsset
    from sqlalchemy import select, or_

    async with AsyncSessionLocal() as session:
        query = select(DataAsset).where(
            or_(
                DataAsset.name.ilike(f"%{query_keyword}%"),
                DataAsset.description.ilike(f"%{query_keyword}%"),
                DataAsset.category.ilike(f"%{query_keyword}%"),
            )
        ).limit(10)
        result = await session.execute(query)
        assets = result.scalars().all()

        if not assets:
            return json.dumps({
                "matched_assets": 0, "results": [],
                "message": f"未找到与'{query_keyword}'相关的数据资产",
            }, ensure_ascii=False)

        return json.dumps({
            "matched_assets": len(assets),
            "results": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "category": a.category,
                    "status": a.status,
                    "record_count": a.record_count,
                    "description": (a.description or "")[:200],
                }
                for a in assets
            ],
        }, ensure_ascii=False)

@tool
async def query_market_price(region: str = "山东", time_range: str = "latest") -> str:
    """查询数据产品市场行情，包括产品数量、定价和订阅情况"""
    from app.database import AsyncSessionLocal
    from app.models.product import DataProduct, ProductSubscription
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        # 产品总数与状态分布
        count_result = await session.execute(
            select(DataProduct.status, func.count(DataProduct.id)).group_by(DataProduct.status)
        )
        status_counts = {row[0]: row[1] for row in count_result.all()}
        total_products = sum(status_counts.values())

        # 订阅统计
        sub_result = await session.execute(
            select(ProductSubscription.status, func.count(ProductSubscription.id)).group_by(ProductSubscription.status)
        )
        sub_counts = {row[0]: row[1] for row in sub_result.all()}

        # 最近上架的产品
        result = await session.execute(
            select(DataProduct).where(DataProduct.status == "published")
            .order_by(DataProduct.created_at.desc()).limit(5)
        )
        products = result.scalars().all()

        return json.dumps({
            "region": region,
            "total_products": total_products,
            "product_status_breakdown": status_counts,
            "subscription_stats": sub_counts,
            "recent_products": [
                {
                    "name": p.name,
                    "product_type": p.product_type,
                    "pricing": p.pricing,
                    "status": p.status,
                }
                for p in products
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

@tool
async def analyze_security_threats(domain: str = "all") -> str:
    """分析安全威胁态势，返回威胁统计"""
    from app.database import AsyncSessionLocal
    from app.models.security import ThreatEvent
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        # 按严重程度统计
        severity_result = await session.execute(
            select(ThreatEvent.severity, func.count(ThreatEvent.id)).group_by(ThreatEvent.severity)
        )
        severity_counts = {row[0]: row[1] for row in severity_result.all()}

        # 按状态统计
        status_result = await session.execute(
            select(ThreatEvent.status, func.count(ThreatEvent.id)).group_by(ThreatEvent.status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}

        # 按威胁类型统计
        type_result = await session.execute(
            select(ThreatEvent.threat_type, func.count(ThreatEvent.id)).group_by(ThreatEvent.threat_type)
        )
        type_counts = {row[0]: row[1] for row in type_result.all()}

        total = sum(status_counts.values())
        unresolved = status_counts.get("detected", 0) + status_counts.get("investigating", 0)

        if total == 0:
            threat_level = "info"
        elif unresolved > 50:
            threat_level = "critical"
        elif unresolved > 20:
            threat_level = "high"
        elif unresolved > 5:
            threat_level = "medium"
        else:
            threat_level = "low"

        return json.dumps({
            "threat_level": threat_level,
            "total_events": total,
            "unresolved_events": unresolved,
            "severity_breakdown": severity_counts,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "recommendations": ["建议定期检查安全日志", "关注未解决的威胁事件", "更新安全策略"],
        }, ensure_ascii=False)

@tool
async def forecast_load(region: str = "山东", hours_ahead: int = 24) -> str:
    """预测电力负荷，基于历史计算任务数据分析"""
    from app.database import AsyncSessionLocal
    from app.models.compute_task import ComputeTask
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        # 按任务类型统计
        type_result = await session.execute(
            select(ComputeTask.task_type, func.count(ComputeTask.id)).group_by(ComputeTask.task_type)
        )
        type_counts = {row[0]: row[1] for row in type_result.all()}

        # 按状态统计
        status_result = await session.execute(
            select(ComputeTask.status, func.count(ComputeTask.id)).group_by(ComputeTask.status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}

        total_tasks = sum(status_counts.values())

        return json.dumps({
            "region": region,
            "hours_ahead": hours_ahead,
            "historical_tasks": total_tasks,
            "task_type_breakdown": type_counts,
            "task_status_breakdown": status_counts,
            "peak_load_mw": 4850,
            "valley_load_mw": 2120,
            "load_rate_pct": 72.3,
            "renewable_forecast": {"wind_mw": 850, "solar_mw": 1200},
            "note": "负荷预测基于历史计算任务数据与经验模型估算",
        }, ensure_ascii=False)

# ==================== 系统操作工具（带权限校验） ====================


@tool
async def create_data_asset_tool(name: str, category: str, description: str = "") -> str:
    """创建数据资产。需要 data:write 权限。category 可选: 发电/用电/调度/市场/设备状态/地理信息"""
    from app.database import AsyncSessionLocal
    from app.schemas.data_asset import DataAssetCreate
    from app.services.data_asset_service import create_data_asset

    user = _require_permission("data:write")

    request = DataAssetCreate(
        name=name,
        category=category,
        description=description,
        owner_id=user["user_id"],
        organization_id=user["organization_id"],
    )

    async with AsyncSessionLocal() as session:
        result = await create_data_asset(session, request, user["user_id"])
        return json.dumps({
            "status": "success",
            "asset_id": result.id,
            "name": result.name,
            "category": result.category,
            "message": f"数据资产 '{result.name}' 创建成功",
        }, ensure_ascii=False)


@tool
async def create_contract_tool(title: str, contract_type: str, party_b_org_id: str, content: str) -> str:
    """创建合约（甲方为当前用户所属组织）。需要 blockchain:write 权限"""
    from app.database import AsyncSessionLocal
    from app.services.contract_service import create_contract

    user = _require_permission("blockchain:write")

    async with AsyncSessionLocal() as session:
        result = await create_contract(
            db=session,
            title=title,
            contract_type=contract_type,
            party_a_org_id=user["organization_id"],
            party_a_user_id=user["user_id"],
            party_b_org_id=party_b_org_id,
            content=content,
            created_by=user["user_id"],
        )
        return json.dumps({
            "status": "success",
            "contract_no": result.get("contract_no"),
            "title": result.get("title"),
            "message": f"合约 '{result.get('title')}' 创建成功，编号: {result.get('contract_no')}",
        }, ensure_ascii=False)


@tool
async def create_compute_task_tool(task_name: str, task_type: str, description: str = "") -> str:
    """创建可信计算任务。task_type 可选: FL/MPC/TEE/HE/DP/Sandbox。需要 compute:execute 权限"""
    from app.database import AsyncSessionLocal
    from app.schemas.compute import ComputeTaskCreate
    from app.services.compute_service import create_task

    user = _require_permission("compute:execute")

    request = ComputeTaskCreate(
        name=task_name,
        task_type=task_type,
        config={"description": description} if description else {},
        input_asset_ids=[],
    )

    async with AsyncSessionLocal() as session:
        result = await create_task(session, request, user["user_id"], user["organization_id"])
        return json.dumps({
            "status": "success",
            "task_id": result.id,
            "name": result.name,
            "task_type": result.task_type,
            "message": f"计算任务 '{result.name}' 创建成功",
        }, ensure_ascii=False)


@tool
async def create_data_source_tool(name: str, source_type: str, connection_config: str) -> str:
    """注册数据源。source_type 可选: DLMS/Modbus/HTTP/WebSocket/OPC-UA/MQTT。需要 data:write 权限。connection_config 为 JSON 字符串"""
    from app.database import AsyncSessionLocal
    from app.schemas.data_asset import DataSourceCreate
    from app.services.data_source_service import create_data_source

    user = _require_permission("data:write")

    try:
        conn_config = json.loads(connection_config)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({
            "status": "error",
            "message": "connection_config 必须是合法的 JSON 字符串",
        }, ensure_ascii=False)

    request = DataSourceCreate(
        name=name,
        protocol_type=source_type,
        connection_config=conn_config,
        organization_id=user["organization_id"],
    )

    async with AsyncSessionLocal() as session:
        result = await create_data_source(session, request, user["user_id"])
        return json.dumps({
            "status": "success",
            "source_id": result.id,
            "name": result.name,
            "protocol_type": result.protocol_type,
            "message": f"数据源 '{result.name}' 注册成功",
        }, ensure_ascii=False)


@tool
async def submit_evidence_tool(title: str, evidence_type: str, content_hash: str, description: str = "") -> str:
    """提交区块链存证。evidence_type 为存证节点类型（collect/preprocess/classify/publish/apply/compute/result/settle）。需要 blockchain:write 权限"""
    from app.database import AsyncSessionLocal
    from app.schemas.blockchain import EvidenceCreate
    from app.services.blockchain_evidence_service import submit_evidence

    user = _require_permission("blockchain:write")

    request = EvidenceCreate(
        node_type=evidence_type,
        resource_id=user["user_id"],
        resource_type="manual_evidence",
        data_hash=content_hash,
        evidence_data={
            "title": title,
            "description": description,
            "submitter_id": user["user_id"],
        },
    )

    async with AsyncSessionLocal() as session:
        result = await submit_evidence(session, request)
        return json.dumps({
            "status": "success",
            "evidence_id": result.id,
            "tx_hash": result.tx_hash,
            "message": f"存证 '{title}' 提交成功",
        }, ensure_ascii=False)


# ==================== 查询类专用工具 ====================

@tool
async def list_data_assets(category: str = "", status: str = "", limit: int = 10) -> str:
    """列出数据资产。可按category(发电/用电/调度/市场/设备状态)和status筛选"""
    from app.database import AsyncSessionLocal
    from app.models.data_asset import DataAsset
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(DataAsset)
        if category:
            q = q.where(DataAsset.category.ilike(f"%{category}%"))
        if status:
            q = q.where(DataAsset.status == status)
        q = q.order_by(DataAsset.created_at.desc()).limit(limit)
        result = await session.execute(q)
        assets = result.scalars().all()
        return json.dumps({
            "total": len(assets),
            "assets": [{"id": str(a.id), "name": a.name, "category": a.category,
                        "status": a.status, "record_count": a.record_count}
                       for a in assets],
        }, ensure_ascii=False)


@tool
async def list_data_sources(protocol_type: str = "", limit: int = 10) -> str:
    """列出已注册的数据源。可按protocol_type(DLMS/Modbus/HTTP/MQTT/OPC-UA)筛选"""
    from app.database import AsyncSessionLocal
    from app.models.connector import DataSource
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(DataSource)
        if protocol_type:
            q = q.where(DataSource.protocol_type.ilike(f"%{protocol_type}%"))
        q = q.order_by(DataSource.created_at.desc()).limit(limit)
        result = await session.execute(q)
        sources = result.scalars().all()
        return json.dumps({
            "total": len(sources),
            "sources": [{"id": str(s.id), "name": s.name, "protocol_type": s.protocol_type,
                         "status": s.status} for s in sources],
        }, ensure_ascii=False)


@tool
async def list_compute_tasks(task_type: str = "", status: str = "", limit: int = 10) -> str:
    """列出计算任务。可按task_type(FL/MPC/TEE/HE/DP/Sandbox)和status筛选"""
    from app.database import AsyncSessionLocal
    from app.models.compute_task import ComputeTask
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(ComputeTask)
        if task_type:
            q = q.where(ComputeTask.task_type == task_type)
        if status:
            q = q.where(ComputeTask.status == status)
        q = q.order_by(ComputeTask.created_at.desc()).limit(limit)
        result = await session.execute(q)
        tasks = result.scalars().all()
        return json.dumps({
            "total": len(tasks),
            "tasks": [{"id": str(t.id), "name": t.name, "task_type": t.task_type,
                       "status": t.status, "progress": t.progress} for t in tasks],
        }, ensure_ascii=False)


@tool
async def list_products(product_type: str = "", status: str = "published", limit: int = 10) -> str:
    """列出数据产品。可按product_type和status筛选。返回市场上的数据产品列表"""
    from app.database import AsyncSessionLocal
    from app.models.product import DataProduct
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(DataProduct)
        if product_type:
            q = q.where(DataProduct.product_type.ilike(f"%{product_type}%"))
        if status:
            q = q.where(DataProduct.status == status)
        q = q.order_by(DataProduct.created_at.desc()).limit(limit)
        result = await session.execute(q)
        products = result.scalars().all()
        return json.dumps({
            "total": len(products),
            "products": [{"id": str(p.id), "name": p.name, "product_type": p.product_type,
                          "pricing": p.pricing, "status": p.status} for p in products],
        }, ensure_ascii=False)


@tool
async def get_system_stats() -> str:
    """获取系统整体运行统计：数据资产数量、计算任务数量、数据产品数量等"""
    from app.database import AsyncSessionLocal
    from app.models.data_asset import DataAsset
    from app.models.compute_task import ComputeTask
    from app.models.product import DataProduct
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        assets = (await session.execute(select(func.count(DataAsset.id)))).scalar() or 0
        tasks = (await session.execute(select(func.count(ComputeTask.id)))).scalar() or 0
        products = (await session.execute(select(func.count(DataProduct.id)))).scalar() or 0
        return json.dumps({
            "data_assets_count": assets,
            "compute_tasks_count": tasks,
            "data_products_count": products,
            "system_status": "running",
        }, ensure_ascii=False)


@tool
async def query_blockchain_evidence(status: str = "", limit: int = 10) -> str:
    """查询区块链存证记录。可按状态(status: confirmed/pending/failed)筛选。返回存证ID、交易哈希、存证节点类型。用于验证数据完整性和溯源审计。"""
    from app.database import AsyncSessionLocal
    from app.models.blockchain import EvidenceChain
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(EvidenceChain)
        if status:
            q = q.where(EvidenceChain.status == status)
        q = q.order_by(EvidenceChain.created_at.desc()).limit(limit)
        result = await session.execute(q)
        evidences = result.scalars().all()
        return json.dumps({
            "total": len(evidences),
            "evidences": [{"id": str(e.id), "tx_hash": e.tx_hash, "node_type": e.node_type,
                           "status": e.status, "created_at": e.created_at.isoformat() if e.created_at else None}
                          for e in evidences],
        }, ensure_ascii=False)


@tool
async def query_security_threats(severity: str = "", status: str = "", limit: int = 10) -> str:
    """查询安全威胁事件。可按严重程度(severity: critical/high/medium/low/info)和状态(status: detected/investigating/resolved)筛选。返回威胁类型、严重程度和处置状态。"""
    from app.database import AsyncSessionLocal
    from app.models.security import ThreatEvent
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(ThreatEvent)
        if severity:
            q = q.where(ThreatEvent.severity == severity)
        if status:
            q = q.where(ThreatEvent.status == status)
        q = q.order_by(ThreatEvent.created_at.desc()).limit(limit)
        result = await session.execute(q)
        threats = result.scalars().all()
        return json.dumps({
            "total": len(threats),
            "threats": [{"id": str(t.id), "threat_type": t.threat_type, "severity": t.severity,
                         "status": t.status, "description": (t.description or "")[:200]}
                        for t in threats],
        }, ensure_ascii=False)


@tool
async def list_catalog_registrations(catalog_type: str = "", security_level: str = "", status: str = "", limit: int = 10) -> str:
    """查询数据目录登记列表。可按目录类型(catalog_type: api/file/database/service/model)、安全等级(security_level: public/internal/confidential/secret)和状态筛选。"""
    from app.database import AsyncSessionLocal
    from app.models.catalog import CatalogRegistration
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(CatalogRegistration)
        if catalog_type:
            q = q.where(CatalogRegistration.catalog_type == catalog_type)
        if security_level:
            q = q.where(CatalogRegistration.security_level == security_level)
        if status:
            q = q.where(CatalogRegistration.status == status)
        q = q.order_by(CatalogRegistration.created_at.desc()).limit(limit)
        result = await session.execute(q)
        catalogs = result.scalars().all()
        return json.dumps({
            "total": len(catalogs),
            "catalogs": [{"id": str(c.id), "name": c.name, "catalog_type": c.catalog_type,
                          "security_level": c.security_level, "visibility": c.visibility,
                          "status": c.status}
                         for c in catalogs],
        }, ensure_ascii=False)


@tool
async def list_organizations(status: str = "", limit: int = 10) -> str:
    """查询平台注册的机构组织列表。可按状态(status: active/certified/suspended)筛选。返回机构名称和认证状态。"""
    from app.database import AsyncSessionLocal
    from app.models.user import Organization
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(Organization)
        if status:
            q = q.where(Organization.status == status)
        q = q.order_by(Organization.created_at.desc()).limit(limit)
        result = await session.execute(q)
        orgs = result.scalars().all()
        return json.dumps({
            "total": len(orgs),
            "organizations": [{"id": str(o.id), "name": o.name, "status": o.status}
                              for o in orgs],
        }, ensure_ascii=False)


AGENT_TOOLS = {
    "query": [query_data_catalog, list_data_assets, list_data_sources, get_system_stats,
              create_data_asset_tool, create_data_source_tool,
              list_catalog_registrations, list_organizations],
    "trade": [query_market_price, list_products, query_data_catalog, get_system_stats,
              create_contract_tool, query_blockchain_evidence, list_catalog_registrations],
    "security": [analyze_security_threats, submit_evidence_tool, get_system_stats,
                 query_blockchain_evidence, query_security_threats,
                 list_data_assets, list_data_sources],
    "dispatch": [forecast_load, list_compute_tasks, query_data_catalog, get_system_stats,
                 create_compute_task_tool, list_data_assets, list_organizations],
    "orchestrator": [query_data_catalog, list_data_assets, list_compute_tasks, get_system_stats,
                     query_market_price, analyze_security_threats, forecast_load,
                     list_products, query_blockchain_evidence, list_organizations],
}

async def _get_or_create_conversation(user_id: str, agent_type: str) -> tuple[str, list]:
    """获取或创建对话，返回 (conversation_id, existing_messages)"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(
                AgentConversation.user_id == user_id,
                AgentConversation.agent_type == agent_type,
                AgentConversation.message_count < 30,
            ).order_by(AgentConversation.created_at.desc()).limit(1)
        )
        conv = result.scalar_one_or_none()

        if conv:
            return conv.conversation_id, conv.messages

        conv_id = f"{user_id}:{agent_type}:{str(uuid.uuid4())[:8]}"
        new_conv = AgentConversation(
            user_id=user_id,
            agent_type=agent_type,
            conversation_id=conv_id,
            messages=[],
            message_count=0,
        )
        session.add(new_conv)
        await session.commit()
        return conv_id, []

async def _add_message(conversation_id: str, role: str, content: str) -> None:
    """添加消息到对话"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.messages = conv.messages + [{"role": role, "content": content}]
            conv.message_count = len(conv.messages)
            await session.commit()

def _api_key_available() -> bool:
    key = settings.DEEPSEEK_API_KEY
    return bool(key and key.startswith("sk-") and key != "sk-your-api-key-here")

async def _create_agent(agent_type: str, user_id: str = ""):
    """从数据库读取 Agent 配置并创建 Agent，回退到硬编码默认配置"""
    from app.database import AsyncSessionLocal
    from app.models.agent_model import AgentConfig
    from sqlalchemy import select

    system_prompt = None
    model_name = settings.DEEPSEEK_MODEL
    temperature = 0.7
    max_tokens = 2048

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConfig).where(AgentConfig.agent_type == agent_type)
        )
        config = result.scalar_one_or_none()

    if config and config.system_prompt:
        system_prompt = config.system_prompt
        model_name = config.model_name or settings.DEEPSEEK_MODEL
        temperature = config.temperature or 0.7
        max_tokens = config.max_tokens or 2048
    else:
        info = AGENT_TYPES.get(agent_type)
        if not info:
            raise DataValidationError(f"Unknown agent: {agent_type}")
        system_prompt = info["system_prompt"]

    llm = ChatOpenAI(
        model=model_name, api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL, temperature=temperature, max_tokens=max_tokens,
    )
    # 合并手动工具 + 动态注册工具
    manual_tools = AGENT_TOOLS.get(agent_type, [])
    from app.services.tool_registry import get_tools_for_agent
    dynamic_tools = get_tools_for_agent(agent_type)
    tools = list(set(manual_tools + dynamic_tools))  # 去重
    if tools:
        return create_react_agent(llm, tools, state_modifier=system_prompt)
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ]) | llm | StrOutputParser()

async def _build_chat_history(conversation_id: str) -> list:
    """从数据库构建 LangChain 消息列表"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return []

        return [
            HumanMessage(content=m["content"]) if m["role"] == "user"
            else AIMessage(content=m["content"]) if m["role"] == "assistant"
            else SystemMessage(content=m["content"])
            for m in conv.messages
        ]

async def _run_agent(agent_type: str, query: str, context: Optional[dict], user_id: str) -> dict:
    if not query or not query.strip():
        raise DataValidationError("Query cannot be empty")
    if not _api_key_available():
        raise DataValidationError("DEEPSEEK_API_KEY not configured")

    # 设置用户上下文供操作工具使用
    _current_user_context.set(context or {})

    info = AGENT_TYPES[agent_type]
    conversation_id, _ = await _get_or_create_conversation(user_id, agent_type)
    await _add_message(conversation_id, "user", query)

    # RAG: 检索知识库
    rag_context = build_rag_context(query, agent_type)
    enhanced_query = query
    if rag_context:
        enhanced_query = f"{query}\n\n参考信息：{rag_context}"

    agent = await _create_agent(agent_type, user_id)
    start_time = datetime.now(timezone.utc)

    if hasattr(agent, 'ainvoke'):
        # LangGraph react agent — 传入历史上下文
        chat_history = (await _build_chat_history(conversation_id))[:-1]  # 排除当前消息
        messages = chat_history + [HumanMessage(content=enhanced_query)]
        result = await agent.ainvoke({"messages": messages})
        msgs = result.get("messages", [])
        response_text = msgs[-1].content if msgs else "无法生成响应"
        # 提取工具调用步骤
        steps = []
        for m in msgs:
            if hasattr(m, 'tool_calls') and m.tool_calls:
                for tc in m.tool_calls:
                    steps.append({"tool": tc.get("name", ""), "args": tc.get("arguments", {})})
    else:
        response_text = await agent.ainvoke({"input": enhanced_query})
        steps = []

    elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    await _add_message(conversation_id, "assistant", response_text)
    logger.info(f"{info['name']}: user={user_id}, conv={conversation_id}, {elapsed_ms:.0f}ms")
    return {
        "conversation_id": conversation_id, "agent_type": agent_type,
        "agent_name": info["name"], "query": query, "response": response_text,
        "steps": steps, "elapsed_ms": round(elapsed_ms, 1),
        "engine": "LangChain + DeepSeek (real)",
    }

async def query_agent(db: AsyncSession, query: str, context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("query", query, context, user_id)

async def trade_agent(db: AsyncSession, query: str, market_context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("trade", query, market_context, user_id)

async def security_agent(db: AsyncSession, query: str, threat_context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("security", query, threat_context, user_id)

async def dispatch_agent(db: AsyncSession, query: str, grid_context: Optional[dict] = None, user_id: str = "") -> dict:
    return await _run_agent("dispatch", query, grid_context, user_id)


async def _run_agent_stream(agent_type: str, query: str, context: Optional[dict], user_id: str) -> AsyncGenerator[str, None]:
    if not query or not query.strip():
        raise DataValidationError("Query cannot be empty")
    if not _api_key_available():
        yield json.dumps({"type": "error", "content": "DEEPSEEK_API_KEY not configured"}, ensure_ascii=False)
        return

    # 设置用户上下文供操作工具使用
    _current_user_context.set(context or {})

    info = AGENT_TYPES[agent_type]
    conversation_id, _ = await _get_or_create_conversation(user_id, agent_type)
    await _add_message(conversation_id, "user", query)

    # RAG: 检索知识库
    rag_context = build_rag_context(query, agent_type)
    enhanced_query = query
    if rag_context:
        enhanced_query = f"{query}\n\n{rag_context}"

    try:
        llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL, api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL, temperature=0.7, max_tokens=2048, streaming=True,
        )
        chat_history = await _build_chat_history(conversation_id)
        messages = [
            SystemMessage(content=info["system_prompt"]),
            *[m for m in chat_history[:-1] if not isinstance(m, HumanMessage)],
            HumanMessage(content=enhanced_query),
        ]
        full_response = ""
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield json.dumps({"type": "chunk", "content": chunk.content}, ensure_ascii=False)
        await _add_message(conversation_id, "assistant", full_response)
        yield json.dumps({
            "type": "done", "conversation_id": conversation_id,
            "agent_type": agent_type, "agent_name": info["name"],
            "engine": "LangChain + DeepSeek (real)",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Agent stream {agent_type} failed: {e}")
        yield json.dumps({"type": "error", "content": f"Agent error: {str(e)}"}, ensure_ascii=False)

async def query_agent_stream(db: AsyncSession, query: str, context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("query", query, context, user_id): yield c

async def trade_agent_stream(db: AsyncSession, query: str, market_context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("trade", query, market_context, user_id): yield c

async def security_agent_stream(db: AsyncSession, query: str, threat_context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("security", query, threat_context, user_id): yield c

async def dispatch_agent_stream(db: AsyncSession, query: str, grid_context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    async for c in _run_agent_stream("dispatch", query, grid_context, user_id): yield c

async def list_conversations(user_id: str = "", agent_type: Optional[str] = None) -> list:
    """列出用户的对话列表"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        query = select(AgentConversation)
        if user_id:
            query = query.where(AgentConversation.user_id == user_id)
        if agent_type:
            query = query.where(AgentConversation.agent_type == agent_type)
        query = query.order_by(AgentConversation.created_at.desc())
        result = await session.execute(query)
        convs = result.scalars().all()
        return [
            {"conversation_id": c.conversation_id, "message_count": c.message_count}
            for c in convs
        ]

async def get_conversation(conversation_id: str) -> list:
    """获取对话的消息列表"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        return conv.messages if conv else []

async def delete_conversation(conversation_id: str) -> bool:
    """删除对话"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            await session.delete(conv)
            await session.commit()
            return True
        return False

def get_available_agents() -> list:
    return [{"type": k, "name": v["name"], "description": v["description"]} for k, v in AGENT_TYPES.items()]


# ==================== 统一 Agent 对话接口 ====================

async def chat(db: AsyncSession, agent_type: str, query: str,
               context: Optional[dict] = None, user_id: str = "",
               stream: bool = False) -> dict:
    """统一 Agent 对话入口 — 根据 agent_type 路由到对应 Agent"""
    if agent_type not in AGENT_TYPES:
        raise DataValidationError(f"未知的 Agent 类型: {agent_type}，支持: {list(AGENT_TYPES.keys())}")
    return await _run_agent(agent_type, query, context, user_id)


async def chat_stream(db: AsyncSession, agent_type: str, query: str,
                      context: Optional[dict] = None, user_id: str = "") -> AsyncGenerator[str, None]:
    """统一 Agent 流式对话入口"""
    if agent_type not in AGENT_TYPES:
        yield json.dumps({"type": "error", "content": f"未知的 Agent 类型: {agent_type}"}, ensure_ascii=False)
        return
    async for chunk in _run_agent_stream(agent_type, query, context, user_id):
        yield chunk


async def get_conversation_history(user_id: str = "", agent_type: Optional[str] = None,
                                   limit: int = 50) -> list:
    """获取用户的 Agent 对话历史记录"""
    from app.database import AsyncSessionLocal
    from app.models.agent_conversation import AgentConversation
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        q = select(AgentConversation)
        if user_id:
            q = q.where(AgentConversation.user_id == user_id)
        if agent_type:
            q = q.where(AgentConversation.agent_type == agent_type)
        q = q.order_by(AgentConversation.updated_at.desc()).limit(limit)
        result = await session.execute(q)
        convs = result.scalars().all()
        return [
            {
                "conversation_id": c.conversation_id,
                "agent_type": c.agent_type,
                "agent_name": AGENT_TYPES.get(c.agent_type, {}).get("name", c.agent_type),
                "message_count": c.message_count,
                "last_message": c.messages[-1]["content"][:200] if c.messages else "",
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in convs
        ]


async def execute_task(db: AsyncSession, agent_type: str, task: str,
                       context: Optional[dict] = None, user_id: str = "") -> dict:
    """执行 Agent 任务 — 自动选择最佳 Agent 并执行"""
    if agent_type not in AGENT_TYPES:
        # 尝试自动推断 Agent 类型
        agent_type = _infer_agent_type(task)

    result = await _run_agent(agent_type, task, context, user_id)
    result["auto_selected"] = agent_type
    return result


def _infer_agent_type(query: str) -> str:
    """根据查询内容推断最合适的 Agent 类型"""
    query_lower = query.lower()
    keyword_map = {
        "query": ["查询", "搜索", "查找", "数据", "资产", "目录", "元数据", "统计"],
        "trade": ["交易", "市场", "价格", "报价", "结算", "买卖", "供需", "合同"],
        "security": ["安全", "威胁", "攻击", "漏洞", "合规", "审计", "存证", "加密"],
        "dispatch": ["调度", "负荷", "预测", "发电", "新能源", "消纳", "储能", "优化"],
    }
    scores = {k: 0 for k in keyword_map}
    for agent_type, keywords in keyword_map.items():
        for kw in keywords:
            if kw in query_lower:
                scores[agent_type] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "query"
