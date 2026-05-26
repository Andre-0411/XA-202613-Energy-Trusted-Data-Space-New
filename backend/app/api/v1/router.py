"""
API v1 路由聚合
挂载所有子路由
"""
from fastapi import APIRouter

from app.api.v1 import (
    abac,
    auth,
    auth_mfa,
    auth_sso,
    portal,
    data_source,
    data_asset,
    data_catalog,
    metadata,
    tags,
    quality,
    data_market,
    data_application,
    data_pipeline,
    integration,
    compute_task,
    compute_dag,
    compute_fl,
    compute_mpc,
    compute_tee,
    compute_he,
    compute_dp,
    compute_sandbox,
    compute_agent,
    compute_cluster,
    compute_enhanced,
    compute_benchmark,
    compute_quota,
    compute_router,
    compute_result,
    task_status,
    agent_manage,
    agent_chat,
    blockchain_nft,
    blockchain_evidence,
    blockchain_contract,
    blockchain_settle,
    blockchain_transactions,
    billing_rule,
    settlement_enhanced,
    cross_chain,
    ops_user,
    ops_org,
    ops_service,
    ops_billing,
    ops_monitor,
    ops_monitoring,
    ops_alerts,
    ops_sla,
    ops_compliance,
    ops_kpi,
    ops_quota,
    ops_gdpr,
    ops_import,
    ops_health,
    ops_audit_external,
    ops_revenue,
    security_policy,
    security_did,
    security_vc,
    security_key,
    security_threat,
    security_gmssl,
    security_zkp,
    security_enhanced,
    security_audit,
    security_hsm,
    security_level,
    security_apt,
    security_bbs,
    notification,
    system_config,
    audit_log,
    mqtt_collect,
    data_enhanced,
    llm,
    health,
    system_info,
    # 新增业务模块
    org_management,
    connector_manage,
    catalog_manage,
    data_subscription,
    product_manage,
    product_publish_v2,
    product_market,
    demand_manage,
    contract_manage,
    connector_file_manage,
    workflow_manage,
    energy_ml,
    agent_skills,
)
from app.api.v1.endpoints import mqtt_stream, websocket

router = APIRouter(prefix="/api/v1")

# 认证
router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(auth_mfa.router, prefix="/auth", tags=["MFA 多因素认证"])
router.include_router(auth_sso.router, prefix="/auth", tags=["SSO 单点登录"])

# 统一门户
router.include_router(portal.router, prefix="/portal", tags=["统一门户"])

# 数据资源
router.include_router(data_source.router, prefix="/data/sources", tags=["数据源"])
router.include_router(data_asset.router, prefix="/data/assets", tags=["数据资产"])
router.include_router(data_catalog.router, prefix="/data/catalog", tags=["数据目录"])
router.include_router(metadata.router, prefix="/data/metadata", tags=["元数据"])
router.include_router(tags.router, prefix="/data/tags", tags=["标签"])
router.include_router(quality.router, prefix="/data/quality", tags=["数据质量"])
router.include_router(data_market.router, prefix="/data/market", tags=["数据服务市场"])
router.include_router(data_pipeline.router, prefix="/data/pipeline", tags=["数据处理流水线"])
router.include_router(data_application.router, prefix="/data/applications", tags=["服务申请审批"])
router.include_router(data_enhanced.router, prefix="/data", tags=["数据增强"])
router.include_router(integration.router, prefix="/integration", tags=["互联互通"])

# 可信计算
router.include_router(compute_task.router, prefix="/compute/tasks", tags=["计算任务"])
router.include_router(compute_dag.router, prefix="/compute/dag", tags=["DAG编排"])
router.include_router(compute_fl.router, prefix="/compute/fl", tags=["联邦学习"])
router.include_router(compute_mpc.router, prefix="/compute/mpc", tags=["安全多方计算"])
router.include_router(compute_tee.router, prefix="/compute/tee", tags=["TEE"])
router.include_router(compute_he.router, prefix="/compute/he", tags=["同态加密"])
router.include_router(compute_dp.router, prefix="/compute/dp", tags=["差分隐私"])
router.include_router(compute_sandbox.router, prefix="/compute/sandbox", tags=["数据沙箱"])
router.include_router(compute_agent.router, prefix="/compute/agents", tags=["AI Agent"])
router.include_router(compute_cluster.router, prefix="/compute/cluster", tags=["计算集群"])
router.include_router(compute_enhanced.router, prefix="/compute/enhanced", tags=["计算增强"])
router.include_router(compute_benchmark.router, prefix="/compute/benchmarks", tags=["性能基准"])
router.include_router(compute_quota.router, prefix="/compute/quota", tags=["计算配额"])
router.include_router(compute_router.router, prefix="/compute/router", tags=["隐私计算路由"])
router.include_router(compute_result.router, prefix="/compute/results", tags=["计算结果管理"])
router.include_router(task_status.router, prefix="/compute/task-status", tags=["任务状态追踪"])
router.include_router(agent_manage.router, prefix="/agents", tags=["Agent 管理"])
router.include_router(agent_chat.router, prefix="/agent", tags=["Agent 对话"])

# 区块链
router.include_router(blockchain_nft.router, prefix="/blockchain/nft", tags=["NFT确权"])
router.include_router(blockchain_evidence.router, prefix="/blockchain/evidence", tags=["存证"])
router.include_router(blockchain_contract.router, prefix="/blockchain/contracts", tags=["智能合约"])
router.include_router(blockchain_settle.router, prefix="/blockchain/settlement", tags=["链上结算"])
router.include_router(settlement_enhanced.router, prefix="/blockchain/settlement-enhanced", tags=["增强结算"])
router.include_router(billing_rule.router, prefix="/blockchain/billing-rules", tags=["计费规则"])
router.include_router(blockchain_transactions.router, prefix="/blockchain", tags=["链上交易"])
router.include_router(cross_chain.router, prefix="/blockchain/bridge", tags=["跨链互操作"])

# 运营管理
router.include_router(ops_user.router, prefix="/ops/users", tags=["用户管理"])
router.include_router(ops_org.router, prefix="/ops/organizations", tags=["组织管理"])
router.include_router(ops_service.router, prefix="/ops/services", tags=["服务管理"])
router.include_router(ops_billing.router, prefix="/ops/billing", tags=["计费管理"])
router.include_router(ops_monitor.router, prefix="/ops/monitoring", tags=["运营监控"])
router.include_router(ops_monitoring.router, prefix="/ops/monitoring-enhanced", tags=["监控增强"])
router.include_router(ops_alerts.router, prefix="/ops/alerts", tags=["告警管理"])
router.include_router(ops_sla.router, prefix="/ops/sla", tags=["SLA 管理"])
router.include_router(ops_compliance.router, prefix="/ops/compliance", tags=["合规管理"])
router.include_router(ops_kpi.router, prefix="/ops/kpi", tags=["KPI仪表盘"])
router.include_router(ops_quota.router, prefix="/ops/quotas", tags=["配额管理"])
router.include_router(ops_gdpr.router, prefix="/ops/gdpr", tags=["GDPR合规"])
router.include_router(ops_import.router, prefix="/ops/import", tags=["批量导入"])
router.include_router(ops_health.router, prefix="/ops/health", tags=["健康检查与自愈"])
router.include_router(ops_audit_external.router, prefix="/ops/audit-external", tags=["第三方审计只读接口"])
router.include_router(ops_revenue.router, prefix="/ops/revenue", tags=["收益分配"])

# 安全管控
router.include_router(abac.router, prefix="/security/abac", tags=["ABAC 策略引擎"])
router.include_router(security_policy.router, prefix="/security/policies", tags=["安全策略"])
router.include_router(security_did.router, prefix="/security/did", tags=["DID身份"])
router.include_router(security_vc.router, prefix="/security/vc", tags=["可验证凭证"])
router.include_router(security_key.router, prefix="/security/keys", tags=["密钥管理"])
router.include_router(security_threat.router, prefix="/security/threats", tags=["威胁检测"])
router.include_router(security_gmssl.router, prefix="/security/gmssl", tags=["国密算法"])
router.include_router(security_zkp.router, prefix="/security/zkp", tags=["零知识证明"])
router.include_router(security_enhanced.router, prefix="/security", tags=["安全增强"])
router.include_router(security_audit.router, prefix="/security/audit", tags=["增强审计"])
router.include_router(security_hsm.router, prefix="/security/hsm", tags=["HSM 硬件安全模块"])
router.include_router(security_level.router, prefix="/security/levels", tags=["安全等级防护"])
router.include_router(security_apt.router, prefix="/security/apt", tags=["APT 高级威胁检测"])
router.include_router(security_bbs.router, prefix="/security/bbs", tags=["BBS+ 签名方案"])

# LLM 大模型集成
router.include_router(llm.router, prefix="/llm", tags=["LLM 大模型"])

# MQTT 数据采集
router.include_router(mqtt_collect.router, prefix="/mqtt", tags=["MQTT采集"])
router.include_router(mqtt_stream.router, prefix="/mqtt/stream", tags=["MQTT数据流"])

# 系统管理
router.include_router(notification.router, prefix="/notifications", tags=["通知公告"])
router.include_router(system_config.router, prefix="/system/config", tags=["系统配置"])
router.include_router(audit_log.router, prefix="/audit-logs", tags=["操作日志"])
router.include_router(health.router, prefix="/health", tags=["健康检查"])
router.include_router(system_info.router, prefix="/system", tags=["系统信息"])

# 能源机器学习
router.include_router(energy_ml.router, prefix="/energy-ml", tags=["能源机器学习"])

# Agent 技能系统
router.include_router(agent_skills.router, prefix="/agent-skills", tags=["Agent技能"])

# 新增业务模块路由
router.include_router(org_management.router, prefix="/organizations", tags=["机构管理"])
router.include_router(connector_manage.router, prefix="/connector-manage", tags=["连接器管理"])
router.include_router(catalog_manage.router, prefix="/catalog-manage", tags=["数据目录管理"])
router.include_router(data_subscription.router, prefix="/data-subscriptions", tags=["数据订阅"])
router.include_router(product_manage.router, prefix="/product-manage", tags=["数据产品管理"])
router.include_router(product_publish_v2.router, prefix="/product-publish", tags=["产品上架"])
router.include_router(product_market.router, prefix="/product-market", tags=["产品市场"])
router.include_router(demand_manage.router, prefix="/demand-manage", tags=["需求管理"])
router.include_router(contract_manage.router, prefix="/contracts", tags=["合约管理"])
router.include_router(connector_file_manage.router, prefix="/connector-files", tags=["连接器文件库"])
router.include_router(workflow_manage.router, prefix="/workflows", tags=["审批工作流"])

# WebSocket 实时通信
router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
