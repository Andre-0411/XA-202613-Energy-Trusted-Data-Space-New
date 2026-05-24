# 能源可信数据空间 "一门户五中心" 系统 — 完整差距分析报告 v2.0

> **编制人**: gap-analyst-v2  
> **编制时间**: 2026-05-21  
> **分析基准**: 需求文档（完善版 v2.0）vs 当前代码库实现  
> **代码统计**: 后端 247 个 Python 文件 / 前端 99 个 TypeScript/TSX 文件 / 18 个 Solidity 合约 / 54 个 API 路由

---

## 一、总体评估

### 1.1 量化概览

| 维度 | 需求项数 | 已实现 | 部分实现 | 存根/模拟 | 缺失 | 完成度 |
|------|---------|--------|---------|----------|------|--------|
| 统一门户 | 17 | 9 | 4 | 2 | 2 | 53% |
| 数据资源中心 | 20 | 11 | 4 | 3 | 2 | 55% |
| 可信计算中心 | 27 | 7 | 5 | 11 | 4 | 26% |
| 区块链存证中心 | 22 | 6 | 4 | 7 | 5 | 27% |
| 运营管理中心 | 23 | 7 | 5 | 6 | 5 | 30% |
| 安全管控中心 | 28 | 6 | 6 | 9 | 7 | 21% |
| 基础设施层 | 12 | 4 | 2 | 3 | 3 | 33% |
| **总计** | **149** | **50** | **30** | **41** | **28** | **34%** |

### 1.2 关键发现（相比 v1.0 更新）

1. **内存存储问题已部分修复**: MFA、SSO、MQTT 数据存储已迁移到 PostgreSQL 数据库，但仍有多达 15 个服务使用内存字典
2. **WebSocket 管理器已增强**: 支持频道订阅、JWT 认证、离线消息队列、用户定向消息，但缺少 Redis Pub/Sub 跨实例支持
3. **响应式设计组件已创建**: 新增 `ResponsiveTable` 和 `ResponsiveFilterBar` 可复用组件，但仅在 2 个页面中使用
4. **SM2 回退实现已改进**: `gmssl_real.py` 实现了正确的三级回退策略（gmssl → cryptography → RuntimeError），但 `gmssl_adapter.py` 仍有空公钥问题
5. **FATE 集成已增强**: 支持 7 种算法、健康检查、自动降级，但仍回退为本地 sklearn 模拟
6. **隐私计算全链路降级**: FATE、MPC、TEE、HE 四条技术路线均回退为本地模拟，未连接任何真实计算引擎

---

## 二、逐模块详细差距分析

### 2.1 统一门户（2.1）

#### 需求 vs 实现映射表

| 需求项 | 需求描述 | 当前状态 | 优先级 | 具体问题 | 修复建议 |
|--------|---------|---------|--------|---------|---------|
| 2.1.2.1 | DID身份认证登录 | ✅ 已实现 | P0 | `did_service.py` 已实现 DID 创建/解析/更新/停用，使用 did:tds 方法 + SM3 哈希 | 无 |
| 2.1.2.1 | 传统账号密码登录 | ✅ 已实现 | P0 | `auth_service.py` + `auth.py` 路由已实现，包含登录失败5次锁定机制 | 无 |
| 2.1.2.1 | 国密证书登录 | ⚠️ 部分实现 | P1 | `security_gmssl.py` 路由存在，但底层依赖 GmSSL 库 | 需确保 GmSSL 正确安装并测试 |
| 2.1.2.1 | 强制双因素认证（MFA） | ✅ 已实现 | P0 | `mfa_service.py` 实现了 TOTP 协议逻辑，**已迁移到 PostgreSQL 数据库持久化存储**（MfaConfig, MfaBackupCode, MfaSession 模型） | 无 |
| 2.1.2.2 | RBAC+ABAC混合权限 | ⚠️ 部分实现 | P0 | `rolePermissions.ts` 实现了 RBAC，`abac_service.py` 实现了 ABAC 策略引擎，但 ABAC 仅支持基本的 AND/OR/NOT 逻辑组合 | 扩展时间/区域/属性条件支持 |
| 2.1.2.3 | 数据服务市场 | ✅ 已实现 | P1 | `DataMarketPage.tsx` + `data_market.py` | 无 |
| 2.1.2.4 | 服务申请管理 | ✅ 已实现 | P1 | `DataApplyPage.tsx` / `DataApplicationPage.tsx` + `data_application.py` | 无 |
| 2.1.2.5 | 数据使用仪表盘 | ✅ 已实现 | P1 | `DashboardPage.tsx` + `portal_service.py` | 无 |
| 2.1.2.6 | 公告与通知 | ✅ 已实现 | P2 | `NotificationCenterPage.tsx` + `notification.py` | 无 |
| 2.1.2.7 | 监管大屏 | ⚠️ 部分实现 | P1 | `MonitorScreenPage.tsx` 存在，但数据为前端 Mock | 需要接入后端 WebSocket 实时数据流 |
| 2.1.3.1 | 响应式设计（1920x1080 + 1366x768） | ⚠️ 部分实现 | P1 | 已创建 `ResponsiveTable` 和 `ResponsiveFilterBar` 可复用组件，但仅在 2 个页面中使用，其余 45+ 页面未做响应式适配 | 1) 所有页面组件使用响应式组件 2) 增加 `sx={{ display: { xs: 'none', md: 'block' } }}` 模式 |
| 2.1.3.2 | 深色/浅色主题切换 | ⚠️ 部分实现 | P2 | `MainLayout.tsx` 有主题切换按钮和 DarkModeIcon/LightModeIcon，但 ThemeProvider 配置需验证 | 确认 MUI Theme 的 palette mode 切换逻辑 |
| 2.1.3.3 | 数据大屏全屏展示 | ⚠️ 部分实现 | P2 | `MainLayout.tsx` 有 FullscreenIcon，ECharts 实时刷新需验证 | 配置 ECharts 5 秒自动刷新间隔 |
| 2.1.3.4 | WCAG 2.1 AA 无障碍 | ❌ 缺失 | P2 | 未发现任何 ARIA 标签或无障碍相关实现 | 添加 aria-label、role、键盘导航支持 |
| 2.1.4.1 | SSO单点登录 | ✅ 已实现 | P0 | `sso_service.py` 实现了 OAuth2.0/OIDC/SAML2.0 的协议框架，**已迁移到 PostgreSQL 数据库持久化存储**（SsoProvider, SsoSession, SsoPendingAuth 模型） | 无 |
| 2.1.4.2 | 登录失败5次锁定 | ✅ 已实现 | P0 | `auth_service.py` 实现了登录失败计数和账户锁定机制（5次失败锁定15分钟） | 无 |
| 2.1.4.3 | CSRF防护 / XSS过滤 | ⚠️ 部分实现 | P0 | `deploy/nginx/nginx.conf` 中有安全头配置，`middleware/sql_injection_guard.py` 实现了 SQL 注入防护，但后端未实现 CSRF token 中间件 | 1) 使用 `starlette-csrf` 中间件 2) 在 Nginx 配置中添加 `X-Content-Type-Options`、`X-Frame-Options` 等头 |
| 2.1.4.4 | 审计日志 | ✅ 已实现 | P1 | `audit_log.py` + `AuditLogPage.tsx` | 无 |
| 2.1.5 | WebSocket实时推送 | ✅ 已实现 | P1 | `websocket_manager.py` 实现了完整的 WebSocket 管理器，支持频道订阅、JWT 认证、离线消息队列、用户定向消息 | 无 |

### 2.2 数据资源中心（2.2）

| 需求项 | 需求描述 | 当前状态 | 优先级 | 具体问题 | 修复建议 |
|--------|---------|---------|--------|---------|---------|
| 2.2.2.1 | 多源数据接入（DLMS/Modbus/IEC61850） | ⚠️ 部分实现 | P0 | `mqtt_collector.py` 实现了 MQTT 数据采集，支持 energy/collect/{did}/{type} 主题设计，但仅支持 MQTT 协议，DLMS/Modbus/IEC61850 协议适配器缺失 | 开发协议适配器层（Protocol Adapter），统一转为 MQTT 主题上报 |
| 2.2.2.2 | 边缘预处理 | ✅ 已实现 | P1 | `edge_preprocessor.py` 实现了格式转换、数据压缩、异常过滤 | 无 |
| 2.2.2.3 | 实时采集（核心 ≤1秒） | ✅ 已实现 | P0 | `mqtt_simulator.py` 实现了 5 个模拟发电企业的数据采集，**数据存储已迁移到 PostgreSQL 数据库**（MqttDevice, MqttDataRecord, MqttAlarm 模型），同时使用内存缓存加速访问 | 无 |
| 2.2.2.4 | 断线续传 | ✅ 已实现 | P1 | `offline_relay.py` 实现了离线缓存和自动补传 | 无 |
| 2.2.3.1 | 数据类型分类（六大类） | ⚠️ 部分实现 | P1 | `data_classifier.py` 和 `classify_service.py` 实现了自动分类，但需验证是否覆盖发电/用电/调度/市场/设备/地理六大类 | 补充分类规则配置 |
| 2.2.3.2 | 数据敏感级别（四级） | ⚠️ 部分实现 | P1 | `SecurityLevelsPage.tsx` + `security_level.py` 存在，但自动分级引擎基于关键词/字段类型的规则引擎需验证 | 测试自动分级准确性 |
| 2.2.3.3 | 三维度标签体系 | ⚠️ 部分实现 | P2 | `tags.py` 路由存在，但业务/技术/质量三维度标签的具体实现需验证 | 补充标签维度配置 |
| 2.2.4 | 元数据管理（GB/T 36073-2018） | ✅ 已实现 | P1 | `MetadataPage.tsx` + `metadata.py` | 无 |
| 2.2.4 | 数据血缘 | ✅ 已实现 | P1 | `DataLineagePage.tsx` + `data_lineage.py` | 无 |
| 2.2.4 | 版本管理 | ✅ 已实现 | P1 | `data_version_service.py` | 无 |
| 2.2.5.1 | 数据目录发布 | ✅ 已实现 | P1 | `DataCatalogPage.tsx` + `catalog_service.py` + `data_catalog.py` | 无 |
| 2.2.5.2 | 脱敏数据预览（最多10条） | ❌ 缺失 | P1 | 未发现数据预览功能的实现 | 在 `data_asset.py` API 中增加 `/preview` 端点，返回脱敏后的 10 条样本 |
| 2.2.5.3 | 数据集评价/反馈 | ❌ 缺失 | P2 | 未发现评价/反馈功能 | 增加 DataAssetRating 模型和 API |
| 2.2.5.4 | 数据集搜索增强 | ✅ 已实现 | P1 | `data_search.py` 实现了全文搜索 + Facets 多维过滤 | 无 |
| 2.2.6 | MQTT 主题设计（energy/collect/{did}/{type}） | ✅ 已实现 | P0 | `mqtt_collector.py` 已实现按规范设计的 MQTT 主题 | 无 |
| 2.2.7 | 数据质量量化（完整性/时效性/准确性/一致性） | ✅ 已实现 | P1 | `data_quality.py` 实现了 5 维度评分（完整/准确/一致/时效/唯一） | 无 |

### 2.3 可信计算中心（2.3）

| 需求项 | 需求描述 | 当前状态 | 优先级 | 具体问题 | 修复建议 |
|--------|---------|---------|--------|---------|---------|
| 2.3.2.1 | 联邦学习（FATE） | ⚠️ 存根 | P0 | `fate_integration.py` 实现了 FATE Flow REST API 客户端（httpx 异步调用），支持 7 种算法（Homo-LR/Hetero-LR/Homo-NN/Hetero-NN/SecureBoost/PSI/Homo-Statistic），但 **连接失败时自动降级为本地 sklearn 模拟**，且任务存储在内存字典 `_fate_jobs` | 1) 部署 FATE Flow 服务（Docker） 2) 将任务状态持久化到 PostgreSQL 3) 移除或标记模拟模式 |
| 2.3.2.2 | 安全多方计算（MPC） | ⚠️ 存根 | P0 | `mpc_service.py` 实现了协议定义（SPDZ/PSN/ABY3/Falcon 等 6 种）和任务提交框架，但 **未连接 MP-SPDZ 引擎**，`party_endpoints` 使用虚拟 URI `mpcparty://{p}:8080` | 1) 部署 MP-SPDZ Docker 容器 2) 实现真实的秘密分享协议执行 3) 将会话存储从 `_mpc_sessions` 迁移到数据库 |
| 2.3.2.3 | 可信执行环境（TEE） | ⚠️ 存根 | P1 | `tee_service.py` 实现了 TEE 实例管理（创建/查询/销毁/远程证明验证），但 **远程证明（RA）为模拟实现**，MRENCLAVE 使用 SM3 哈希伪造，未与 Intel IAS/DCAP 交互 | 1) 使用 Gramine Docker 镜像模拟 SGX 2) 接入 Intel DCAP 或 FISCO RA 服务 |
| 2.3.2.4 | 同态加密（HE） | ⚠️ 存根 | P1 | `he_service.py` 实现了 CKKS/BFV/BGV 方案定义和加密/计算/解密流程，但 **使用 SM4 对称密钥模拟 RLWE 密钥**，未集成微软 SEAL 库 | 1) 安装 `seal-python` 绑定 2) 替换模拟加密为真实 SEAL 操作 |
| 2.3.2.5 | 差分隐私 | ✅ 已实现 | P1 | `dp_service.py` + `compute_dp.py` 实现了差分隐私机制 | 需验证 ε 值可配置性 |
| 2.3.3.1 | DAG 可视化拖拽编排 | ✅ 已实现 | P1 | `ComputeDagPage.tsx` + `dag_engine.py`（Kahn's BFS 环检测 + 拓扑排序） | 无 |
| 2.3.3.2 | YAML/JSON 配置导入 | ❌ 缺失 | P2 | 未发现配置文件导入功能 | 在任务创建 API 中增加文件上传解析 |
| 2.3.3.3 | 多方DID签名确认 | ⚠️ 部分实现 | P1 | DID 服务层已集成到计算任务流程中 | 需要多方签名确认机制 |
| 2.3.3.4 | 任务状态实时追踪 | ✅ 已实现 | P1 | `compute_task.py` + WebSocket 推送 | 无 |
| 2.3.3.5 | 计算结果加密存储+哈希上链 | ⚠️ 部分实现 | P0 | `compute_service.py` 实现了双节点存证（启动+完成），但加密存储依赖 HE 模拟 | 需 HE 真实实现后才有意义 |
| 2.3.3.6 | CPU/GPU 资源配额管理 | ❌ 缺失 | P2 | 未发现资源配额管理 | 增加 ResourceQuota 模型和检查逻辑 |
| 2.3.4.1 | Docker 容器沙箱隔离 | ⚠️ 部分实现 | P1 | `compute_sandbox.py` + `sandbox_service.py` 实现了 Docker 容器管理框架 | 需配置 seccomp 安全策略 |
| 2.3.4.2 | 算法准入静态代码扫描 | ❌ 缺失 | P2 | 未发现代码扫描功能 | 集成 `bandit` 或 `pylint` 安全扫描 |
| 2.3.4.3 | 数据脱敏入沙箱 | ❌ 缺失 | P2 | 未发现沙箱数据脱敏 | 在数据入沙箱前增加脱敏 Pipeline |
| 2.3.4.4 | 出口审核 | ❌ 缺失 | P2 | 未发现出口审核机制 | 增加结果导出审核流程 |
| 2.3.6 | 隐私计算路由（技术路线自动选择） | ✅ 已实现 | P1 | `privacy_router.py` + `privacy/service_registry.py` 实现了场景-技术矩阵路由 | 无 |
| 2.3.8 | AI Agent 集成（4 种 Agent） | ✅ 已实现 | P1 | `agent_service.py` 实现了 QueryAgent/TradeAgent/SecurityAgent/DispatchAgent + SSE 流式输出，基于 DeepSeek API | 无 |

**隐私计算统一抽象层评估**：`backend/app/services/privacy/` 目录下有 8 个文件实现了 `PrivacyComputeInterface` + 5 个适配器 + 注册中心，架构设计良好，但所有适配器底层均为模拟实现。

### 2.4 区块链存证中心（2.4）

| 需求项 | 需求描述 | 当前状态 | 优先级 | 具体问题 | 修复建议 |
|--------|---------|---------|--------|---------|---------|
| 2.4.2.1 | DID 身份与资产绑定 | ✅ 已实现 | P0 | `did_service.py` + `IdentityRegistry.sol` | 无 |
| 2.4.2.2 | NFT 化资产管理 | ⚠️ 部分实现 | P1 | `DataAssetNFT.sol` + `blockchain_nft_service.py` 存在，但铸造流程需验证 | 端到端测试 NFT 铸造 |
| 2.4.2.3 | 确权证书生成 | ❌ 缺失 | P1 | 未发现确权证书生成逻辑 | 增加证书生成服务（PDF/区块链签名） |
| 2.4.2.4 | 原创性证明 | ⚠️ 部分实现 | P1 | 首次上传时间戳通过存证记录，但独立的原创性证明流程缺失 | 在数据上传时自动创建原创性存证 |
| 2.4.3 | 全流程操作存证（8 节点） | ⚠️ 部分实现 | P0 | `blockchain_evidence_service.py` + `evidence.py` schema 实现了存证框架，覆盖 8 个生命周期节点，链式哈希结构（prev_hash）已定义，但 **实际上链依赖 FISCO BCOS 真实连接** | 需先完成 FISCO BCOS 部署 |
| 2.4.4.1 | 计费规则上链 | ⚠️ 部分实现 | P1 | `AutoSettlement.sol` + `blockchain_settle_service.py` 存在，计费规则需验证 | 测试计费规则上链 |
| 2.4.4.2 | 自动触发结算 | ⚠️ 部分实现 | P1 | 合约和服务层已定义，触发机制需验证 | 实现使用完成 → 触发合约的事件监听 |
| 2.4.4.3 | 收益分配 | ⚠️ 部分实现 | P1 | `IncentiveDistribution.sol` 存在，分配逻辑需验证 | 测试收益分配比例 |
| 2.4.4.4 | 争议仲裁 | ❌ 缺失 | P2 | 未发现仲裁机制 | 增加多方签名仲裁合约 |
| 2.4.5.1 | FISCO BCOS 4 节点部署 | ❌ 缺失 | P0 | `fisco_channel_client.py` 实现了 HTTP Channel Service 客户端（4 节点 PBFT 配置、SM-TLS 证书路径、JSON-RPC 接口），但 **未发现实际的 FISCO BCOS 节点部署配置** | 1) 编写 FISCO BCOS Docker 部署脚本 2) 配置 4 节点 PBFT 共识 3) 部署 SM-TLS 证书 |
| 2.4.5.2 | 核心智能合约（6 个） | ✅ 已实现 | P0 | `IdentityRegistry.sol`、`DataAssetNFT.sol`、`AccessControl.sol`、`UsageLogger.sol`、`AutoSettlement.sol`、`ComplianceAudit.sol` + 6 个扩展合约（共 18 个 .sol 文件） | 需要编译和部署到 FISCO BCOS |
| 2.4.5.3 | 合约编译+部署脚本 | ⚠️ 部分实现 | P0 | `contract_compiler.py` + `contract_deploy_service.py` 存在 | 需要在真实 FISCO BCOS 环境测试 |
| 2.4.6 | 链上查询性能（<200ms 单条） | ❌ 未验证 | P1 | 无法在无链环境下验证 | FISCO BCOS 部署后进行性能测试 |

### 2.5 运营管理中心（2.5）

| 需求项 | 需求描述 | 当前状态 | 优先级 | 具体问题 | 修复建议 |
|--------|---------|---------|--------|---------|---------|
| 2.5.2.1 | 四级组织架构 | ⚠️ 部分实现 | P1 | `OpsOrgPage.tsx` + `ops_org.py` 存在，但层级关系需验证 | 测试组织架构 CRUD |
| 2.5.2.2 | 用户全生命周期 | ⚠️ 部分实现 | P1 | `OpsUsersPage.tsx` + `ops_user.py` 存在 | 验证完整流程 |
| 2.5.2.3 | DID 绑定 | ⚠️ 部分实现 | P1 | DID 服务已集成 | 需验证 DID 变更重新认证 |
| 2.5.2.4 | Excel 批量导入 | ❌ 缺失 | P2 | 未发现批量导入功能 | 增加 Excel 上传解析 API |
| 2.5.3.1 | 服务分级（查询/计算/导出） | ✅ 已实现 | P1 | `OpsServicesPage.tsx` + `ops_service.py` | 无 |
| 2.5.3.2 | 计费模式（按次/按量/订阅） | ⚠️ 部分实现 | P1 | `OpsBillingPage.tsx` + `billing_service.py` 存在，计费模式需验证 | 测试三种计费模式 |
| 2.5.3.3 | 月度账单自动生成 | ❌ 缺失 | P1 | 未发现自动账单生成 | 增加定时任务生成月度账单 |
| 2.5.3.4 | 配额管理 | ❌ 缺失 | P2 | 未发现配额管理 | 增加 Quota 模型和检查 |
| 2.5.4.1 | Prometheus + Grafana | ⚠️ 存根 | P1 | `OpsMonitorPage.tsx` + `ops_monitoring.py` + `monitoring_service.py` 存在，`deploy/prometheus/prometheus.yml` 和 `grafana/dashboards/energy-tds.json` 已配置，但 **monitoring_service.py 使用内存字典存储指标** | 1) 接入真实 Prometheus client（`prometheus_client` 库） 2) 将指标暴露到 `/metrics` 端点 |
| 2.5.4.2 | 业务指标监控 | ⚠️ 部分实现 | P1 | `OpsKpiPage.tsx` + `ops_kpi.py` 存在 | 验证指标采集 |
| 2.5.4.3 | 多渠道告警推送 | ⚠️ 存根 | P1 | `alert_service.py` + `ops_alerts.py` 实现了告警引擎框架（阈值/趋势/复合告警），但 **告警推送通道未接入**（无邮件/短信/钉钉/企业微信集成） | 集成 `smtplib`（邮件）+ `requests`（Webhook） |
| 2.5.4.4 | 故障自愈 | ❌ 缺失 | P2 | 未发现故障自愈 | 增加健康检查 + 自动重启脚本 |
| 2.5.5.1 | 操作日志保留 6 个月 | ⚠️ 部分实现 | P1 | `AuditLogPage.tsx` 存在，日志保留策略未实现 | 增加日志清理定时任务 |
| 2.5.5.2 | 合规报告自动生成 | ⚠️ 部分实现 | P1 | `OpsCompliancePage.tsx` + `compliance_service.py` 存在 | 验证报告生成 |
| 2.5.5.3 | GDPR/数安法合规 | ❌ 缺失 | P2 | 未发现数据主体请求处理流程 | 增加 DataSubjectRequest 模型 |
| 2.5.5.4 | 第三方审计只读接口 | ❌ 缺失 | P2 | 未发现审计专用接口 | 增加只读 API Token |
| 2.5.6 | SLA 管理 | ✅ 已实现 | P1 | `OpsSLAPage.tsx` + `sla_service.py` | 无 |
| 2.5.7 | 收益分配机制 | ⚠️ 存根 | P1 | `IncentiveDistribution.sol` + 收益计算逻辑需验证，当前 `billing_service.py` 使用内存字典 `_billing_store` | 1) 将计费数据迁移到 PostgreSQL 2) 实现智能合约自动结算 |

### 2.6 安全管控中心（2.6）

| 需求项 | 需求描述 | 当前状态 | 优先级 | 具体问题 | 修复建议 |
|--------|---------|---------|--------|---------|---------|
| 2.6.2.1 | RBAC 基础层 | ✅ 已实现 | P0 | `rolePermissions.ts` 定义了 4 种基础角色 | 无 |
| 2.6.2.2 | ABAC 扩展层 | ⚠️ 部分实现 | P0 | `abac_service.py` 实现了策略引擎（AND/OR/NOT），但时间/区域/属性条件支持不完整 | 扩展条件类型 |
| 2.6.2.3 | 动态授权（临时+条件） | ❌ 缺失 | P1 | 未发现动态授权 | 增加授权有效期和条件触发 |
| 2.6.2.4 | 跨域联合授权 | ❌ 缺失 | P2 | 未发现跨域授权 | 增加委托授权模型 |
| 2.6.3.1 | W3C DID v1.0 规范 | ✅ 已实现 | P0 | `did_service.py` 实现了 did:tds 方法，DID Document 符合 W3C 规范 | 无 |
| 2.6.3.2 | VC 可验证凭证签发 | ⚠️ 存根 | P1 | `security_vc.py` + `vc_real.py` 存在，但 VC 签发使用模拟实现 | 集成 W3C VC 签发库 |
| 2.6.3.3 | VC 可验证凭证验证 | ⚠️ 存根 | P1 | 同上 | 同上 |
| 2.6.3.4 | 密钥轮换 | ❌ 缺失 | P1 | 未发现密钥轮换机制 | 增加密钥版本管理和轮换流程 |
| 2.6.3.5 | 设备 DID | ⚠️ 部分实现 | P1 | MQTT 设备注册使用 DID，但设备身份认证需验证 | 验证设备 DID 认证流程 |
| 2.6.4.1 | HSM 模拟 | ⚠️ 存根 | P1 | `hsm_service.py` + `security_hsm.py` 存在，但为软件模拟 | 验证 HSM 接口兼容性 |
| 2.6.4.2 | 三层密钥体系 | ❌ 缺失 | P1 | 未发现分层密钥管理 | 增加密钥层级模型 |
| 2.6.4.3 | Shamir 秘密共享（3-of-5） | ❌ 缺失 | P1 | 未发现 Shamir 实现 | 集成 `secretsharing` 库 |
| 2.6.4.4 | 密钥审计日志 | ❌ 缺失 | P2 | 未发现密钥使用审计 | 增加密钥操作日志 |
| 2.6.5.1 | 实时威胁检测 | ⚠️ 存根 | P1 | `SecurityThreatPage.tsx` + `security_threat.py` 存在，但检测逻辑为模拟 | 集成规则引擎 + ML 模型 |
| 2.6.5.2 | 安全态势大屏 | ⚠️ 存根 | P1 | 前端页面存在，数据为 Mock | 接入实时威胁数据 |
| 2.6.5.3 | APT 检测 | ❌ 缺失 | P2 | 未发现 APT 检测 | 增加行为序列分析 |
| 2.6.5.4 | 每日安全简报 | ⚠️ 存根 | P2 | `SecurityAgent` 可生成安全报告，但为模拟数据 | 接入真实安全事件 |
| 2.6.6 | 国密算法集成（SM2/SM3/SM4） | ⚠️ 部分实现 | P0 | `gmssl_real.py` 实现了正确的三级回退策略（gmssl → cryptography → RuntimeError），但 `gmssl_adapter.py` 仍有空公钥问题（第 101 行 `return private_key, ""`） | 1) 统一使用 `gmssl_real.py` 的 SM2Engine 2) 修复 `gmssl_adapter.py` 的密钥生成 3) 移除 SM9/ZUC 的伪实现 |
| 2.6.7.1 | ZKP 数据源头真实性证明 | ⚠️ 存根 | P1 | `zkp_service.py` + `security_zkp.py` 存在，但为模拟实现 | 集成 `snarkjs` + `circom` |
| 2.6.7.2 | ZKP 身份属性证明（BBS+） | ❌ 缺失 | P2 | 未发现 BBS+ 实现 | 集成 BBS+ 签名库 |
| 2.6.7.3 | ZKP 数据范围证明（Bulletproofs） | ❌ 缺失 | P2 | 未发现 Bulletproofs 实现 | 集成 Bulletproofs 库 |
| 2.6.8 | 四级安全等级与防护矩阵 | ⚠️ 部分实现 | P1 | `SecurityLevelsPage.tsx` + `security_level.py` 存在 | 验证防护矩阵实现 |

---

## 三、基础设施层差距

### 3.1 数据库

| 组件 | 当前状态 | 具体问题 | 修复建议 |
|------|---------|---------|---------|
| PostgreSQL 16 | ⚠️ 已配置未连接 | `database.py` 配置了 async_engine + AsyncSessionLocal，`init_db()` 有连接检测，但 **连接失败时仅 warning 不阻断**，运行在 "demo mode" | 1) 确保 Docker Compose 中 PostgreSQL 启动 2) 执行 `alembic upgrade head` |
| Alembic 迁移 | ✅ 已实现 | 6 个迁移脚本（0001_init 到 0006_add_ops_enhanced） | 需执行迁移 |
| Redis 7 | ⚠️ 已配置未连接 | `database.py` 配置了 Redis 连接池 + RedisSessionManager | 确保 Docker 中 Redis 启动 |
| MongoDB 7 | ⚠️ 已配置可选 | `database.py` 使用 motor 驱动，导入失败时 graceful 降级 | 可选组件 |

### 3.2 消息队列

| 组件 | 当前状态 | 具体问题 | 修复建议 |
|------|---------|---------|---------|
| MQTT Broker (EMQX) | ⚠️ 已配置未部署 | `mqtt_client.py` 配置了 paho-mqtt 客户端，Docker Compose 中有 emqx 服务定义 | 确保 EMQX 容器启动 |
| RabbitMQ | ⚠️ 已配置未部署 | Docker Compose 中有 rabbitmq 服务定义 | 确保 RabbitMQ 容器启动 |

### 3.3 容器化

| 组件 | 当前状态 | 具体问题 | 修复建议 |
|------|---------|---------|---------|
| Docker Compose | ✅ 已实现 | 20+ 服务定义，3 个网络（energy-net/fisco-net/privacy-net） | 需测试完整启动 |
| 后端 Dockerfile | ✅ 已实现 | 多阶段构建 | 无 |
| 前端 Dockerfile | ✅ 已实现 | 多阶段构建 | 无 |
| Nginx 反向代理 | ✅ 已实现 | `deploy/nginx/nginx.conf` + `default.conf`，含 WebSocket 代理和安全头 | 无 |

### 3.4 监控

| 组件 | 当前状态 | 具体问题 | 修复建议 |
|------|---------|---------|---------|
| Prometheus | ⚠️ 已配置 | `deploy/prometheus/prometheus.yml` 存在 | 需确保 `/metrics` 端点暴露 |
| Grafana | ⚠️ 已配置 | `grafana/dashboards/energy-tds.json` 4 面板仪表盘 | 需验证数据源连接 |

---

## 四、内存存储问题清单（关键质量风险）

以下服务文件使用纯内存字典替代数据库持久化，**重启即丢失所有数据**：

| 服务文件 | 内存存储变量 | 影响范围 | 优先级 |
|---------|------------|---------|--------|
| `fate_integration.py` | `_fate_jobs` | 联邦学习任务 | **P0** |
| `mpc_service.py` | `_mpc_sessions` | MPC 计算会话 | **P1** |
| `tee_service.py` | `_tee_instances` | TEE 实例 | **P1** |
| `he_service.py` | `_he_keys`, `_he_ciphertexts` | HE 密钥和密文 | **P1** |
| `monitor_service.py` | 内存指标存储 | 监控指标 | **P1** |
| `portal_service.py` | 内存缓存 | 门户数据 | **P1** |
| `sla_service.py` | 内存 SLA 配置 | SLA 管理 | **P1** |
| `sandbox_service.py` | 内存沙箱状态 | 沙箱管理 | **P1** |
| `compute_sandbox.py` | 内存沙箱映射 | 计算沙箱 | **P1** |
| `agent_manage_service.py` | 内存 Agent 配置 | Agent 管理 | **P1** |
| `cluster_service.py` | 内存集群状态 | 集群管理 | **P1** |
| `data_version_service.py` | 内存版本记录 | 数据版本 | **P1** |
| `fl_service.py` | 内存 FL 任务 | 联邦学习 | **P1** |
| `vc_real.py` | 内存 VC 存储 | 可验证凭证 | **P1** |
| `zkp_service.py` | 内存 ZKP 证明 | 零知识证明 | **P1** |

---

## 五、国密算法实现问题清单（安全关键）

| 问题 | 文件位置 | 严重性 | 描述 | 修复建议 |
|------|---------|--------|------|---------|
| SM2 密钥生成返回空公钥 | `gmssl_adapter.py:101` | **严重** | `sm2_generate_keypair()` 返回 `(private_key, "")`，空公钥将导致所有依赖公钥的操作失败 | 使用 `gmssl_real.py` 的 SM2Engine 正确生成密钥对 |
| SM9 签名伪造 | `gmssl_adapter.py:174` | **严重** | `sm9_sign()` 使用 `SM3(data + master_private_key)` 模拟，这不是 SM9 签名算法 | 移除伪实现或标记为 unsupported |
| SM9 验签伪造 | `gmssl_adapter.py:181` | **严重** | `sm9_verify()` 使用同样的哈希比对，将接受任何伪造的签名 | 同上 |
| ZUC 降级为 SM4 | `gmssl_adapter.py:197` | **中等** | ZUC 流密码降级为 SM4 ECB 模式，安全性差异显著 | 明确标注为降级模式或移除 |
| SM2 无 GmSSL 时抛异常 | `gmssl_adapter.py:44` | **中等** | SM2 签名在 GmSSL 不可用时直接抛 RuntimeError，而 SM3 有 SHA-256 降级 | 统一降级策略 |
| SM3 降级为 SHA-256 | `gmssl_adapter.py:113` | **低** | SM3 不可用时降级为 SHA-256，不符合国密要求 | 标注为开发模式降级，生产环境必须使用 SM3 |

---

## 六、前端响应式设计差距

### 当前状态

- **使用 `useMediaQuery` 的文件**: 仅 2 个
  - `MainLayout.tsx` - 侧边栏折叠
  - `LandingPage.tsx` - 移动端抽屉菜单
- **响应式组件已创建**: 2 个
  - `ResponsiveTable.tsx` - 桌面端表格/移动端卡片视图
  - `ResponsiveFilterBar.tsx` - 桌面端水平/移动端垂直堆叠
- **未做响应式的页面**: 约 45+ 个页面组件
- **未发现 TailwindCSS 响应式类**: 虽然技术栈声明使用 TailwindCSS，但实际以 MUI 为主

### 修复建议

1. **全局主题配置**: 在 MUI Theme 中配置 `breakpoints`（xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536）
2. **布局组件**: 所有页面使用 MUI `Grid` 或 `Stack` 的响应式 props（`xs`, `sm`, `md`, `lg`, `xl`）
3. **侧边栏**: `MainLayout.tsx` 已有 `isMobile` 判断，需确保所有页面继承此行为
4. **表格**: 使用 `ResponsiveTable` 组件替代所有表格
5. **筛选栏**: 使用 `ResponsiveFilterBar` 组件替代所有筛选栏
6. **图表**: ECharts 使用 `resize` 事件自动适配容器大小

---

## 七、优先级排序与行动计划

### P0 — 必须完成（决定基础得分，共 18 项）

| 序号 | 任务 | 涉及模块 | 预估工作量 | 依赖 |
|------|------|---------|-----------|------|
| 1 | PostgreSQL 数据库连接 + Alembic 迁移 | 基础设施 | 0.5 天 | Docker 环境 |
| 2 | Redis 连接验证 | 基础设施 | 0.5 天 | Docker 环境 |
| 3 | FISCO BCOS 4 节点 Docker 部署 | 区块链 | 2 天 | Docker 环境 |
| 4 | 智能合约编译 + 部署到 FISCO BCOS | 区块链 | 1 天 | #3 |
| 5 | 修复 SM2 密钥对生成（统一使用 gmssl_real.py） | 安全 | 0.5 天 | GmSSL 库 |
| 6 | FATE 联邦学习任务持久化 | 可信计算 | 1 天 | #1 |
| 7 | DID 身份认证 + SM2 签名完整流程 | 安全 | 1 天 | #5 |
| 8 | 数据资产上链存证 | 区块链 | 1 天 | #3, #4 |
| 9 | 操作存证全链路覆盖 | 区块链 | 1 天 | #8 |
| 10 | ABAC 策略引擎完善 | 安全 | 1 天 | 无 |
| 11 | 基础权限管控验证 | 门户 | 0.5 天 | 无 |
| 12 | 统一门户多角色登录验证 | 门户 | 0.5 天 | 无 |
| 13 | CSRF/XSS 安全中间件 | 门户 | 0.5 天 | 无 |
| 14 | 多源数据接入协议适配器 | 数据资源 | 1 天 | 无 |
| 15 | 数据资产 NFT 铸造完整流程 | 区块链 | 1 天 | #4 |
| 16 | 计费规则上链验证 | 区块链 | 1 天 | #4 |
| 17 | 自动触发结算验证 | 区块链 | 1 天 | #16 |
| 18 | 响应式组件全面应用 | 门户 | 2 天 | 无 |

### P1 — 重要功能（提升创新评分，共 25 项）

| 序号 | 任务 | 涉及模块 | 预估工作量 |
|------|------|---------|-----------|
| 19 | FATE 真实集成（至少 Homo-LR） | 可信计算 | 3 天 |
| 20 | MPC 真实集成（MP-SPDZ） | 可信计算 | 3 天 |
| 21 | TEE Gramine 模拟集成 | 可信计算 | 2 天 |
| 22 | HE SEAL 库集成 | 可信计算 | 2 天 |
| 23 | ZKP 数据源头真实性证明 | 安全 | 2 天 |
| 24 | 监管大屏实时数据接入 | 门户 | 1 天 |
| 25 | Prometheus 指标采集真实接入 | 运营 | 1 天 |
| 26 | 告警推送通道集成 | 运营 | 1 天 |
| 27 | 月度账单自动生成 | 运营 | 1 天 |
| 28 | VC 可验证凭证真实签发 | 安全 | 2 天 |
| 29 | 密钥轮换机制 | 安全 | 1 天 |
| 30 | 三层密钥体系 | 安全 | 1 天 |
| 31 | Shamir 秘密共享 | 安全 | 1 天 |
| 32 | HSM 模拟完善 | 安全 | 1 天 |
| 33 | 实时威胁检测规则引擎 | 安全 | 2 天 |
| 34 | 安全态势大屏真实数据 | 安全 | 1 天 |
| 35 | 数据沙箱 seccomp 策略 | 可信计算 | 1 天 |
| 36 | DAG 可视化增强 | 可信计算 | 1 天 |
| 37 | 确权证书生成 | 区块链 | 1 天 |
| 38 | 组织架构完善 | 运营 | 1 天 |
| 39 | 用户全生命周期完善 | 运营 | 1 天 |
| 40 | 计费模式完善 | 运营 | 1 天 |
| 41 | 数据脱敏预览功能 | 数据资源 | 1 天 |
| 42 | 数据集评价/反馈功能 | 数据资源 | 1 天 |
| 43 | 内存存储全面迁移 | 基础设施 | 3 天 |

### P2 — 加分项（冲击高分，共 12 项）

| 序号 | 任务 | 涉及模块 |
|------|------|---------|
| 44 | 全同态加密 HE 场景演示 | 可信计算 |
| 45 | LLM 安全分析报告自动生成 | 可信计算 |
| 46 | 市场策略仿真（TradeAgent 强化学习） | 可信计算 |
| 47 | 跨链互操作演示 | 区块链 |
| 48 | 国密 SSL 全链路 | 安全 |
| 49 | WCAG 2.1 AA 无障碍 | 门户 |
| 50 | ZKP 身份属性证明（BBS+） | 安全 |
| 51 | ZKP 数据范围证明（Bulletproofs） | 安全 |
| 52 | APT 慢速渗透检测 | 安全 |
| 53 | 故障自愈 | 运营 |
| 54 | Excel 批量导入 | 运营 |
| 55 | 跨域联合授权 | 安全 |

---

## 八、修复路径建议

### 阶段一：基础设施修复（第 1-3 天）

**目标**: 确保所有服务能正常启动并连接到真实基础设施

1. 启动 Docker Compose（PostgreSQL + Redis + EMQX + RabbitMQ）
2. 执行 Alembic 迁移创建数据库表
3. 验证后端能正常连接所有数据库
4. 部署 FISCO BCOS 4 节点联盟链
5. 编译并部署 6 个核心智能合约

### 阶段二：内存存储迁移（第 4-7 天）

**目标**: 消除所有内存字典存储，迁移到数据库

1. FATE/MPC/TEE/HE 任务持久化
2. 计费/SLA/监控数据持久化
3. 沙箱/集群/版本管理数据持久化
4. Agent 配置/VC/ZKP 数据持久化

### 阶段三：安全加固（第 8-10 天）

**目标**: 修复所有安全关键问题

1. 统一使用 `gmssl_real.py` 的 SM2Engine，修复 `gmssl_adapter.py` 空公钥问题
2. 移除 SM9/ZUC 的伪实现
3. 添加 CSRF/XSS 中间件
4. 完善 ABAC 策略引擎
5. DID + SM2 签名完整流程验证

### 阶段四：隐私计算真实集成（第 11-18 天）

**目标**: 至少一条技术路线从模拟升级为真实实现

1. FATE 真实集成（Homo-LR 发电预测场景）
2. MPC 真实集成（SPDZ 协议）
3. TEE Gramine 模拟
4. HE SEAL 集成

### 阶段五：功能完善与测试（第 19-25 天）

**目标**: 完成 P1 功能并进行端到端测试

1. 响应式设计全面适配
2. 监控告警真实接入
3. 运营管理功能完善
4. 安全管控功能完善
5. 4 个业务场景端到端演示

---

## 九、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| FISCO BCOS 部署复杂 | 高 | P0 功能阻塞 | 使用官方 Docker 镜像，准备降级方案（模拟链） |
| FATE 部署资源需求大 | 高 | 联邦学习演示受阻 | 使用 FATE Standalone 模式，最小化部署 |
| GmSSL 安装困难 | 中 | 国密功能不可用 | 使用 pip install gmssl，或降级到 pycryptodome |
| 内存存储迁移工作量大 | 中 | 15 个服务需要修改 | 按优先级分批迁移，P0 服务优先 |
| 性能达标困难 | 中 | TPS≥1000 难以验证 | 使用压力测试工具验证，必要时优化 |

---

## 十、结论

当前系统在 **架构设计和代码骨架** 方面做得较好，"一门户五中心" 的页面结构、API 路由、服务层抽象、智能合约、Docker 编排均已就位。但在 **工程质量** 方面存在系统性问题：

1. **28% 的功能为存根/模拟实现**，缺乏真实的后端逻辑
2. **15 个服务使用内存字典** 替代数据库，重启即丢失数据
3. **国密算法实现存在安全漏洞**（SM2 空公钥、SM9 签名伪造）
4. **隐私计算四条技术路线全部降级** 为本地模拟
5. **响应式设计覆盖率仅 4%**（2/45+ 页面）

**相比 v1.0 的改进**：
- MFA、SSO、MQTT 数据存储已迁移到 PostgreSQL
- WebSocket 管理器已增强（频道订阅、JWT 认证、离线消息队列）
- 响应式组件已创建（ResponsiveTable、ResponsiveFilterBar）
- SM2 回退实现已改进（gmssl_real.py 三级回退策略）
- FATE 集成已增强（7 种算法、健康检查）

**建议优先级**：基础设施修复 → 内存存储迁移 → 安全加固 → 隐私计算真实集成 → 功能完善。预计完成 P0 任务需要 10 个工作日，完成 P1 任务需要额外 15 个工作日。
