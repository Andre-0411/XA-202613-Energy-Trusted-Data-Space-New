# 系统架构设计文档

## 面向能源可信数据空间的"一门户五中心"系统

| 字段 | 值 |
|------|-----|
| **项目名称** | energy_trusted_data_space |
| **文档版本** | v1.0 |
| **架构师** | 高见远（Gao） |
| **竞赛编号** | XA-202613 |
| **核心原则** | 全量真实实现，禁止任何模拟/占位/Mock |

---

## 1. 系统架构概述

### 1.1 整体架构图（C4 Context 级别）

```mermaid
graph TB
    subgraph External Actors
        A1[数据管理员]
        A2[分析师]
        A3[结算员]
        A4[监管审查员]
        A5[运营管理员]
    end

    subgraph System[能源可信数据空间]
        P[统一门户]
        DRC[数据资源中心]
        TCC[可信计算中心]
        BEC[区块链存证中心]
        OMC[运营管理中心]
        SCC[安全管控中心]
    end

    subgraph External Systems
        E1[智能电表 DLMS/COSEM]
        E2[新能源终端 Modbus/IEC61850]
        E3[气象 HTTP API]
        E4[市场价格 WebSocket]
    end

    A1 --> P
    A2 --> P
    A3 --> P
    A4 --> P
    A5 --> P

    P --> DRC
    P --> TCC
    P --> BEC
    P --> OMC
    P --> SCC

    E1 -->|DLMS| DRC
    E2 -->|Modbus| DRC
    E3 -->|HTTP| DRC
    E4 -->|WebSocket| DRC
    DRC -->|数据| TCC
    TCC -->|结果| BEC
    DRC -->|确权| BEC
    SCC -->|策略| DRC
    SCC -->|策略| TCC
    OMC -->|计费| BEC
```

### 1.2 整体架构图（C4 Container 级别）

```mermaid
graph TB
    subgraph Frontend[前端层]
        FE[React 18 + Vite + MUI v6]
        FE_ECharts[ECharts 数据大屏]
        FE_WS[WebSocket Client]
    end

    subgraph APIGateway[API 网关层]
        NGINX[Nginx 反向代理]
    end

    subgraph Backend[后端服务层]
        API[FastAPI REST API]
        WS_SRV[WebSocket Server]
        MQTT_CLT[EMQX MQTT Client]
        BGWORK[Background Workers]
    end

    subgraph PrivacyLayer[隐私计算层]
        FATE[FATE 联邦学习]
        MPSPDZ[MP-SPDZ 安全多方计算]
        SEAL_LIB[SEAL 同态加密]
        GRAMINE[Gramine TEE]
        DP_MOD[差分隐私模块]
        DAG_ENG[DAG 编排引擎]
        AI_AGT[AI Agent LangChain+AutoGen]
    end

    subgraph BlockchainLayer[区块链层]
        FISCO[FISCO BCOS 3.x PBFT 4节点]
        CONTRACTS[6 Solidity 智能合约]
    end

    subgraph DataLayer[数据层]
        PG[(PostgreSQL 16)]
        REDIS[(Redis 7)]
        MONGO[(MongoDB 7)]
        MINIO[MinIO 对象存储]
    end

    subgraph InfraLayer[基础设施层]
        EMQX_SVR[EMQX MQTT Broker]
        PROM[Prometheus]
        GRAF[Grafana]
    end

    FE --> NGINX
    FE_WS --> WS_SRV
    NGINX --> API
    API --> PG
    API --> REDIS
    API --> MONGO
    API --> MINIO
    API --> FISCO
    API --> FATE
    API --> MPSPDZ
    API --> SEAL_LIB
    API --> GRAMINE
    API --> DP_MOD
    API --> DAG_ENG
    API --> AI_AGT
    MQTT_CLT --> EMQX_SVR
    BGWORK --> REDIS
    PROM --> GRAF
    API --> PROM
    CONTRACTS --> FISCO
```

### 1.3 技术栈选型表

| 层次 | 技术 | 版本 | 用途 | 选型理由 |
|------|------|------|------|----------|
| **前端框架** | React | 18.x | UI 构建 | PRD 硬性要求，组件生态丰富 |
| **前端构建** | Vite | 5.x | 开发/构建 | 极速 HMR，ESM 原生支持 |
| **UI 组件库** | Material UI | 6.x | 组件体系 | PRD 要求，企业级组件完善 |
| **CSS 工具** | TailwindCSS | 3.x | 原子化样式 | 与 MUI sx prop 互补，快速布局 |
| **图表** | ECharts | 5.x | 数据可视化 | 大屏适配优，中文文档全 |
| **状态管理** | Zustand | 4.x | 全局状态 | 轻量、TypeScript 友好 |
| **路由** | React Router | 6.x | 前端路由 | PRD 要求 |
| **HTTP 客户端** | Axios + React Query | 5.x + 5.x | API 请求 | Axios 底层 + RQ 缓存/重试 |
| **实时通信** | WebSocket (native) | - | 推送通知 | 无额外依赖 |
| **后端框架** | FastAPI | 0.115+ | REST API | PRD 要求，异步原生，自动 OpenAPI |
| **语言** | Python | 3.12 | 后端 | PRD 要求 |
| **主数据库** | PostgreSQL | 16 | 关系数据 | ACID 事务，JSONB 支持 |
| **缓存** | Redis | 7 | 缓存/会话/MQ | 高性能，Pub/Sub |
| **文档数据库** | MongoDB | 7 | 遥测/审计 | 灵活 Schema，高写入 |
| **对象存储** | MinIO | latest | 文件/模型 | S3 兼容，私有部署 |
| **区块链** | FISCO BCOS | 3.x | 存证/确权 | 国产开源，国密内置 |
| **联邦学习** | FATE | 2.x | FL 训练 | 工业级 FL 框架 |
| **安全多方计算** | MP-SPDZ | 0.5+ | MPC | 学术+工业双验证 |
| **同态加密** | SEAL | 4.x | HE 计算 | 微软开源，CKKS/BFV |
| **TEE** | Gramine | 1.x | SGX 信封 | 轻量 LibOS |
| **国密** | GmSSL | 3.x | SM2/3/4/9/ZUC | 国密标准实现 |
| **AI Agent** | LangChain + AutoGen | latest | Agent 框架 | 多 Agent 协作 |
| **LLM** | DeepSeek-V3 | - | 本地推理 | 中文能力强 |
| **消息队列** | EMQX | 5.x | MQTT Broker | 物联网标准，高并发 |
| **监控** | Prometheus + Grafana | latest | 系统监控 | 云原生标配 |
| **容器** | Docker + Docker Compose | latest | 容器化 | 一键部署 |
| **反向代理** | Nginx | latest | API 网关 | 高性能，TLS 终结 |

---

## 2. 文件结构与路径

### 2.1 完整项目文件树

```
energy-trusted-data-space/
├── .env.example                          # 环境变量模板
├── .gitignore                            # Git 忽略配置
├── docker-compose.yml                    # 容器编排主文件
├── Makefile                              # 快捷命令
│
├── frontend/                             # ===== 前端 React 应用 =====
│   ├── package.json                      # 依赖声明
│   ├── vite.config.ts                    # Vite 构建配置
│   ├── tsconfig.json                     # TypeScript 配置
│   ├── tsconfig.node.json                # Node TS 配置
│   ├── tailwind.config.ts                # Tailwind 配置
│   ├── postcss.config.js                 # PostCSS 配置
│   ├── index.html                        # HTML 入口
│   ├── Dockerfile                        # 前端容器
│   ├── nginx.conf                        # Nginx 配置
│   ├── public/
│   │   └── favicon.ico
│   └── src/
│       ├── main.tsx                       # React 入口
│       ├── App.tsx                        # 根组件 + 路由挂载
│       ├── vite-env.d.ts                  # Vite 类型声明
│       ├── theme/                         # 主题配置
│       │   ├── index.ts                   # MUI 主题定义（能源蓝+可信绿）
│       │   ├── palette.ts                 # 色彩体系
│       │   └── typography.ts             # 字体体系
│       ├── routes/                        # 路由配置
│       │   ├── index.tsx                  # 路由表定义
│       │   ├── ProtectedRoute.tsx         # 权限路由守卫
│       │   └── LazyLoad.tsx               # 懒加载包装
│       ├── layouts/                       # 布局组件
│       │   ├── MainLayout.tsx            # 主布局（Sidebar+TopBar+Content）
│       │   ├── AuthLayout.tsx             # 认证布局（登录/注册）
│       │   └── FullScreenLayout.tsx      # 全屏布局（大屏）
│       ├── stores/                        # Zustand 状态管理
│       │   ├── useAuthStore.ts           # 认证状态
│       │   ├── useDataAssetStore.ts      # 数据资产状态
│       │   ├── useComputeStore.ts        # 计算任务状态
│       │   ├── useBlockchainStore.ts     # 区块链状态
│       │   ├── useOpsStore.ts            # 运营管理状态
│       │   ├── useSecurityStore.ts       # 安全管控状态
│       │   └── useThemeStore.ts          # 主题切换状态
│       ├── hooks/                         # 自定义 Hooks
│       │   ├── useWebSocket.ts           # WebSocket 连接
│       │   ├── usePermission.ts          # 权限检查
│       │   ├── useECharts.ts             # ECharts 封装
│       │   └── usePagination.ts          # 分页封装
│       ├── services/                      # API 服务层
│       │   ├── api.ts                     # Axios 实例 + 拦截器
│       │   ├── auth.service.ts            # 认证 API
│       │   ├── data.service.ts            # 数据资源 API
│       │   ├── compute.service.ts         # 可信计算 API
│       │   ├── blockchain.service.ts      # 区块链 API
│       │   ├── ops.service.ts            # 运营管理 API
│       │   ├── security.service.ts       # 安全管控 API
│       │   └── websocket.service.ts      # WebSocket 管理
│       ├── types/                         # TypeScript 类型
│       │   ├── auth.ts                    # 认证类型
│       │   ├── data.ts                    # 数据资源类型
│       │   ├── compute.ts                # 计算任务类型
│       │   ├── blockchain.ts             # 区块链类型
│       │   ├── ops.ts                     # 运营类型
│       │   ├── security.ts               # 安全类型
│       │   └── common.ts                 # 通用类型（分页/响应）
│       ├── utils/                         # 工具函数
│       │   ├── format.ts                 # 格式化
│       │   ├── crypto.ts                 # 前端加密
│       │   └── constants.ts             # 常量定义
│       ├── components/                    # 通用组件
│       │   ├── PageHeader.tsx            # 页面标题
│       │   ├── StatusTag.tsx             # 状态标签
│       │   ├── ConfirmDialog.tsx         # 确认对话框
│       │   ├── DataTable.tsx             # 数据表格
│       │   ├── SearchBar.tsx             # 搜索栏
│       │   ├── FileUpload.tsx            # 文件上传
│       │   ├── JsonViewer.tsx            # JSON 查看器
│       │   ├── MetricsCard.tsx           # 指标卡片
│       │   ├── DagCanvas.tsx             # DAG 画布组件
│       │   └── DidBadge.tsx              # DID 徽章
│       └── pages/                         # 页面组件（按模块）
│           ├── portal/                    # ---- 统一门户 ----
│           │   ├── LoginPage.tsx          # 登录页（DID/密码/证书+MFA）
│           │   ├── DashboardPage.tsx     # 门户首页/仪表盘
│           │   ├── DataMarketPage.tsx    # 数据服务市场
│           │   ├── ServiceApplyPage.tsx   # 服务申请管理
│           │   └── MonitorScreenPage.tsx # 监管大屏
│           ├── data/                      # ---- 数据资源中心 ----
│           │   ├── SourceListPage.tsx     # 数据源列表
│           │   ├── SourceDetailPage.tsx   # 数据源详情/接入配置
│           │   ├── AssetListPage.tsx      # 数据资产列表
│           │   ├── AssetDetailPage.tsx   # 资产详情/分级分类
│           │   ├── CatalogPage.tsx        # 数据目录浏览
│           │   ├── CatalogPreviewPage.tsx # 脱敏预览
│           │   ├── MetadataPage.tsx      # 元数据管理
│           │   ├── LineagePage.tsx       # 数据血缘可视化
│           │   └── QualityPage.tsx       # 数据质量报告
│           ├── compute/                   # ---- 可信计算中心 ----
│           │   ├── TaskListPage.tsx      # 计算任务列表
│           │   ├── TaskCreatePage.tsx    # 创建计算任务
│           │   ├── TaskDetailPage.tsx    # 任务详情/执行状态
│           │   ├── DagEditorPage.tsx     # DAG 可视化编排
│           │   ├── SandboxPage.tsx       # 数据沙箱
│           │   ├── AgentChatPage.tsx     # AI Agent 交互
│           │   └── BenchmarkPage.tsx     # 性能基准
│           ├── blockchain/                # ---- 区块链存证中心 ----
│           │   ├── AssetRegisterPage.tsx # 资产确权/NFT
│           │   ├── EvidencePage.tsx      # 全流程存证
│           │   ├── ContractPage.tsx      # 智能合约管理
│           │   ├── SettlementPage.tsx    # 自动结算
│           │   └── ChainQueryPage.tsx    # 链上查询/溯源
│           ├── ops/                       # ---- 运营管理中心 ----
│           │   ├── UserManagePage.tsx    # 用户与组织管理
│           │   ├── ServiceCatalogPage.tsx # 服务目录
│           │   ├── BillingPage.tsx       # 计费管理
│           │   ├── OpsMonitorPage.tsx    # 运营监控
│           │   ├── CompliancePage.tsx    # 合规管理
│           │   └── KpiPage.tsx           # KPI 仪表盘
│           └── security/                 # ---- 安全管控中心 ----
│               ├── PolicyPage.tsx        # RBAC+ABAC 策略
│               ├── DidManagePage.tsx     # DID 身份管理
│               ├── VcManagePage.tsx      # 可验证凭证
│               ├── KeyManagePage.tsx     # 密钥管理
│               ├── ThreatPage.tsx        # 威胁检测
│               ├── CryptoPage.tsx        # 国密工具
│               ├── ZkpPage.tsx           # 零知识证明
│               └── SecurityLevelPage.tsx # 安全等级管理
│
├── backend/                              # ===== 后端 FastAPI 应用 =====
│   ├── pyproject.toml                    # 项目元数据
│   ├── requirements.txt                  # Python 依赖
│   ├── Dockerfile                        # 后端容器
│   ├── alembic.ini                       # 数据库迁移配置
│   ├── alembic/
│   │   ├── env.py                        # Alembic 环境
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_init.py              # 初始迁移
│   └── app/
│       ├── __init__.py
│       ├── main.py                       # FastAPI 应用入口
│       ├── config.py                     # 配置管理（Pydantic Settings）
│       ├── database.py                   # 数据库连接 + Session 管理
│       ├── dependencies.py               # 全局依赖注入
│       ├── exceptions.py                 # 全局异常处理
│       ├── middleware.py                  # 中间件（CORS/安全头/限流）
│       ├── models/                        # SQLAlchemy ORM 模型
│       │   ├── __init__.py               # 导出所有模型
│       │   ├── base.py                   # Base 声明 + 通用 Mixin
│       │   ├── user.py                   # User / Organization / Department
│       │   ├── data_asset.py            # DataAsset / DataSource / Metadata
│       │   ├── tag.py                    # Tag / AssetTag
│       │   ├── access_log.py            # AccessLog
│       │   ├── compute_task.py          # ComputeTask / DagDefinition / DagNode
│       │   ├── blockchain.py             # BlockchainTransaction / NftAsset
│       │   ├── service.py               # ServiceCatalog / Subscription / BillingRecord
│       │   ├── audit_log.py             # AuditLog
│       │   ├── security.py              # SecurityPolicy / DidDocument / VcRecord / KeyStore / ThreatEvent
│       │   └── compliance.py            # ComplianceReport / DataQualityReport
│       ├── schemas/                      # Pydantic 请求/响应模型
│       │   ├── __init__.py
│       │   ├── common.py                 # 通用响应/分页
│       │   ├── auth.py                   # 认证相关 Schema
│       │   ├── user.py                   # 用户相关 Schema
│       │   ├── data_asset.py            # 数据资产 Schema
│       │   ├── compute.py               # 计算任务 Schema
│       │   ├── blockchain.py            # 区块链 Schema
│       │   ├── service.py               # 服务 Schema
│       │   ├── security.py             # 安全 Schema
│       │   └── ops.py                    # 运营 Schema
│       ├── api/                           # API 路由层
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py             # v1 路由聚合
│       │       ├── auth.py               # /api/v1/auth
│       │       ├── data_source.py        # /api/v1/data/sources
│       │       ├── data_asset.py         # /api/v1/data/assets
│       │       ├── data_catalog.py       # /api/v1/data/catalog
│       │       ├── metadata.py           # /api/v1/data/metadata
│       │       ├── tags.py               # /api/v1/data/tags
│       │       ├── quality.py            # /api/v1/data/quality
│       │       ├── compute_task.py       # /api/v1/compute/tasks
│       │       ├── compute_dag.py        # /api/v1/compute/dag
│       │       ├── compute_fl.py         # /api/v1/compute/fl
│       │       ├── compute_mpc.py        # /api/v1/compute/mpc
│       │       ├── compute_tee.py        # /api/v1/compute/tee
│       │       ├── compute_he.py         # /api/v1/compute/he
│       │       ├── compute_dp.py         # /api/v1/compute/dp
│       │       ├── compute_sandbox.py    # /api/v1/compute/sandbox
│       │       ├── compute_agent.py      # /api/v1/compute/agents
│       │       ├── blockchain_nft.py     # /api/v1/blockchain/nft
│       │       ├── blockchain_evidence.py # /api/v1/blockchain/evidence
│       │       ├── blockchain_contract.py # /api/v1/blockchain/contracts
│       │       ├── blockchain_settle.py  # /api/v1/blockchain/settle
│       │       ├── ops_user.py           # /api/v1/ops/users
│       │       ├── ops_org.py            # /api/v1/ops/organizations
│       │       ├── ops_service.py        # /api/v1/ops/services
│       │       ├── ops_billing.py         # /api/v1/ops/billing
│       │       ├── ops_monitor.py         # /api/v1/ops/monitoring
│       │       ├── ops_compliance.py      # /api/v1/ops/compliance
│       │       ├── ops_kpi.py            # /api/v1/ops/kpi
│       │       ├── security_policy.py    # /api/v1/security/policies
│       │       ├── security_did.py       # /api/v1/security/did
│       │       ├── security_vc.py        # /api/v1/security/vc
│       │       ├── security_key.py       # /api/v1/security/keys
│       │       ├── security_threat.py    # /api/v1/security/threats
│       │       ├── security_gmssl.py     # /api/v1/security/gmssl
│       │       └── security_zkp.py       # /api/v1/security/zkp
│       ├── services/                      # 业务逻辑层
│       │   ├── __init__.py
│       │   ├── auth_service.py            # 认证/DID/MFA 逻辑
│       │   ├── data_source_service.py     # 数据源管理 + 协议适配
│       │   ├── data_asset_service.py      # 数据资产管理
│       │   ├── classify_service.py        # 分类分级引擎
│       │   ├── catalog_service.py         # 数据目录服务
│       │   ├── metadata_service.py        # 元数据管理
│       │   ├── quality_service.py         # 数据质量检测
│       │   ├── compute_service.py         # 计算任务编排
│       │   ├── dag_engine.py              # DAG 执行引擎
│       │   ├── fl_service.py              # FATE 联邦学习集成
│       │   ├── mpc_service.py             # MP-SPDZ 安全计算集成
│       │   ├── tee_service.py             # Gramine TEE 集成
│       │   ├── he_service.py              # SEAL 同态加密集成
│       │   ├── dp_service.py              # 差分隐私服务
│       │   ├── sandbox_service.py         # 数据沙箱管理
│       │   ├── agent_service.py           # AI Agent 服务
│       │   ├── blockchain_service.py      # 区块链交互服务
│       │   ├── contract_service.py        # 智能合约调用服务
│       │   ├── nft_service.py             # NFT 确权服务
│       │   ├── evidence_service.py        # 存证服务
│       │   ├── settlement_service.py      # 结算服务
│       │   ├── user_service.py            # 用户管理
│       │   ├── org_service.py             # 组织管理
│       │   ├── billing_service.py         # 计费服务
│       │   ├── monitor_service.py         # 运营监控服务
│       │   ├── compliance_service.py      # 合规管理服务
│       │   ├── policy_service.py          # RBAC+ABAC 策略服务
│       │   ├── did_service.py             # DID 身份服务
│       │   ├── vc_service.py              # 可验证凭证服务
│       │   ├── key_service.py             # 密钥管理服务
│       │   ├── threat_service.py          # 威胁检测服务
│       │   ├── gmssl_service.py           # 国密算法服务
│       │   └── zkp_service.py             # 零知识证明服务
│       ├── core/                          # 核心模块
│       │   ├── __init__.py
│       │   ├── security.py                # 安全工具（JWT/密码/CSRF）
│       │   ├── gmssl_adapter.py          # GmSSL v3.x Python 适配器
│       │   ├── fisco_client.py            # FISCO BCOS Python SDK 封装
│       │   ├── mqtt_client.py             # EMQX MQTT 客户端
│       │   ├── ws_manager.py              # WebSocket 连接管理器
│       │   └── task_scheduler.py          # 后台任务调度器
│       └── utils/                          # 工具函数
│           ├── __init__.py
│           ├── deps.py                    # 依赖注入（get_db/get_current_user）
│           ├── pagination.py              # 分页工具
│           └── logger.py                  # 日志配置
│
├── contracts/                            # ===== 区块链智能合约 =====
│   ├── IdentityRegistry.sol              # DID 身份注册合约
│   ├── DataAssetNFT.sol                  # 数据资产 NFT 合约
│   ├── AccessControl.sol                 # 访问控制合约
│   ├── UsageLogger.sol                   # 使用记录合约
│   ├── AutoSettlement.sol                # 自动结算合约
│   ├── ComplianceAudit.sol               # 合规审计合约
│   ├── libs/                             # 合约库
│   │   └── SMVerify.sol                  # 国密验证库
│   └── deploy/
│       ├── deploy.ts                      # 部署脚本
│       └── abi/                           # 编译输出 ABI
│           ├── IdentityRegistry.json
│           ├── DataAssetNFT.json
│           ├── AccessControl.json
│           ├── UsageLogger.json
│           ├── AutoSettlement.json
│           └── ComplianceAudit.json
│
├── privacy/                              # ===== 隐私计算模块 =====
│   ├── fate/                             # FATE 联邦学习
│   │   ├── conf/                         # FATE 配置
│   │   │   ├── coordinator.yaml
│   │   │   └── party.yaml
│   │   ├── pipeline/                     # FATE Pipeline 定义
│   │   │   ├── fl_lr_pipeline.py         # 横向 LR
│   │   │   ├── fl_nn_pipeline.py         # 纵向 NN
│   │   │   └── fl_tree_pipeline.py       # 树模型
│   │   └── Dockerfile.fate
│   ├── mpc/                              # MP-SPDZ
│   │   ├── scripts/                      # MP-SPDZ 脚本
│   │   │   ├── mpc_settlement.py         # 多方结算
│   │   │   └── mpc_statistics.py         # 统计计算
│   │   ├── Dockerfile.mpspdz
│   │   └── conf/
│   │       └── mpspdz.yaml
│   ├── he/                               # SEAL 同态加密
│   │   ├── he_ckks.py                    # CKKS 浮点计算
│   │   ├── he_bfv.py                     # BFV 整数计算
│   │   └── Dockerfile.seal
│   ├── tee/                              # Gramine TEE
│   │   ├── manifest/                     # Gramine 清单
│   │   │   └── compute.manifest
│   │   ├── app/                          # TEE 内应用
│   │   │   └── secure_compute.py
│   │   └── Dockerfile.gramine
│   ├── dp/                               # 差分隐私
│   │   ├── dp_engine.py                 # DP 引擎（本地/全局）
│   │   └── mechanisms.py                # DP 机制（Laplace/Gaussian）
│   ├── dag/                              # DAG 编排引擎
│   │   ├── engine.py                    # DAG 执行引擎
│   │   ├── parser.py                    # DAG 解析器
│   │   ├── scheduler.py                 # DAG 调度器
│   │   └── models.py                    # DAG 数据模型
│   └── agents/                          # AI Agent
│       ├── base_agent.py                # Agent 基类
│       ├── query_agent.py               # QueryAgent
│       ├── trade_agent.py               # TradeAgent
│       ├── security_agent.py            # SecurityAgent
│       ├── dispatch_agent.py            # DispatchAgent
│       └── tools/                       # Agent 工具
│           ├── data_query_tool.py
│           ├── blockchain_query_tool.py
│           └── compute_tool.py
│
├── deploy/                               # ===== 部署配置 =====
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   ├── fisco.Dockerfile
│   │   ├── fate.Dockerfile
│   │   ├── mpspdz.Dockerfile
│   │   ├── seal.Dockerfile
│   │   └── gramine.Dockerfile
│   ├── nginx/
│   │   └── nginx.conf
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── rules/
│   │       └── alerts.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── system-overview.json
│   │   │   ├── business-metrics.json
│   │   │   └── security-monitor.json
│   │   └── datasources/
│   │       └── prometheus.yml
│   ├── emqx/
│   │   └── emqx.conf
│   └── fisco/
│       ├── node0/
│       ├── node1/
│       ├── node2/
│       └── node3/
│
├── scripts/                              # ===== 工具脚本 =====
│   ├── init_db.py                        # 数据库初始化
│   ├── seed_data.py                      # 种子数据
│   ├── deploy_contracts.py               # 合约部署
│   └── health_check.py                  # 健康检查
│
└── docs/
    ├── PRD.md
    ├── ARCHITECTURE.md
    ├── class-diagram.mermaid
    └── sequence-diagram.mermaid
```

### 2.2 文件统计

| 模块 | 文件数 | 说明 |
|------|--------|------|
| 前端 (frontend/) | ~65 | 页面 27 + 组件 10 + 基础设施 28 |
| 后端 (backend/) | ~75 | API 33 + 服务 33 + 模型 12 + 核心 6 |
| 智能合约 (contracts/) | ~12 | 6 合约 + 6 ABI + 部署脚本 |
| 隐私计算 (privacy/) | ~25 | FATE/MPC/HE/TEE/DP/DAG/Agent |
| 部署配置 (deploy/) | ~15 | Docker/Nginx/Prometheus/Grafana/EMQX |
| 脚本 (scripts/) | 4 | 初始化/种子/部署/检查 |
| **总计** | **~196** | |

---

## 3. 数据模型设计

### 3.1 ER 图

```mermaid
erDiagram
    Organization ||--o{ Department : has
    Department ||--o{ User : contains
    User ||--o{ DidDocument : owns
    User ||--o{ AccessLog : generates
    User ||--o{ ComputeTask : submits
    User ||--o{ AuditLog : triggers
    User ||--o{ Subscription : subscribes

    DataSource ||--o{ DataAsset : produces
    DataSource }o--|| Organization : belongs_to
    DataAsset ||--o{ Metadata : has
    DataAsset ||--o{ AssetTag : tagged_with
    DataAsset }o--|| User : owned_by
    DataAsset ||--o| NftAsset : tokenized_as
    DataAsset ||--o{ AccessLog : accessed_via
    DataAsset ||--o{ DataQualityReport : quality_checked
    Tag ||--o{ AssetTag : applies_to

    ComputeTask }o--|| DagDefinition : follows
    ComputeTask }o--|| User : created_by
    ComputeTask ||--o{ TaskSignature : signed_by

    ServiceCatalog ||--o{ Subscription : subscribed_to
    Subscription ||--o{ BillingRecord : billed_as

    SecurityPolicy ||--o{ PolicyAssignment : assigned_to
    KeyStore ||--o{ KeyUsageLog : usage_tracked
    ThreatEvent ||--o{ ThreatAction : responded_to

    BlockchainTransaction ||--o| EvidenceRecord : records
    ComplianceReport }o--|| Organization : covers
```

### 3.2 PostgreSQL 表定义

#### 3.2.1 用户与组织

**organizations** 组织表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL UNIQUE | 组织名称 |
| code | VARCHAR(50) | NOT NULL UNIQUE | 组织编码 |
| parent_id | UUID | FK → organizations.id | 父组织 |
| level | SMALLINT | NOT NULL DEFAULT 1 | 层级（1平台/2组织/3部门/4用户组） |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 状态 |
| did | VARCHAR(128) | | 组织 DID |
| metadata | JSONB | DEFAULT '{}' | 扩展信息 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新时间 |

索引: `idx_org_parent_id`, `idx_org_code`, `idx_org_status`

**departments** 部门表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 部门名称 |
| organization_id | UUID | FK → organizations.id NOT NULL | 所属组织 |
| parent_id | UUID | FK → departments.id | 父部门 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 状态 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

索引: `idx_dept_org_id`, `idx_dept_parent_id`

**users** 用户表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| username | VARCHAR(100) | NOT NULL UNIQUE | 用户名 |
| password_hash | VARCHAR(256) | NOT NULL | SM3 哈希密码 |
| email | VARCHAR(200) | UNIQUE | 邮箱 |
| phone | VARCHAR(20) | | 手机号 |
| did | VARCHAR(128) | UNIQUE | 用户 DID |
| sm2_public_key | TEXT | | SM2 公钥 |
| mfa_secret | VARCHAR(64) | | MFA 密钥（加密存储） |
| mfa_enabled | BOOLEAN | NOT NULL DEFAULT false | MFA 是否启用 |
| role | VARCHAR(30) | NOT NULL DEFAULT 'user' | 角色（admin/data_admin/user/auditor） |
| department_id | UUID | FK → departments.id | 所属部门 |
| organization_id | UUID | FK → organizations.id NOT NULL | 所属组织 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 状态 |
| last_login_at | TIMESTAMPTZ | | 最后登录时间 |
| login_fail_count | SMALLINT | DEFAULT 0 | 连续登录失败次数 |
| locked_until | TIMESTAMPTZ | | 锁定截止时间 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新时间 |

索引: `idx_user_username`, `idx_user_did`, `idx_user_org_id`, `idx_user_dept_id`, `idx_user_status`

#### 3.2.2 数据资源

**data_sources** 数据源表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 数据源名称 |
| protocol_type | VARCHAR(20) | NOT NULL | 协议类型（DLMS/Modbus/HTTP/WebSocket） |
| connection_config | JSONB | NOT NULL | 连接配置（加密存储） |
| device_did | VARCHAR(128) | | 设备 DID |
| mqtt_topic | VARCHAR(256) | | MQTT 订阅主题 |
| collection_interval_ms | INTEGER | DEFAULT 5000 | 采集间隔（毫秒） |
| is_critical | BOOLEAN | DEFAULT false | 是否核心数据 |
| edge_preprocess | JSONB | DEFAULT '{}' | 边缘预处理配置 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 状态 |
| organization_id | UUID | FK → organizations.id NOT NULL | 所属组织 |
| created_by | UUID | FK → users.id | 创建人 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新时间 |

索引: `idx_source_protocol`, `idx_source_org_id`, `idx_source_device_did`, `idx_source_status`

**data_assets** 数据资产表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 资产名称 |
| source_id | UUID | FK → data_sources.id | 来源数据源 |
| category | VARCHAR(30) | NOT NULL | 大类（发电/用电/调度/市场/设备状态/地理信息） |
| classification_level | SMALLINT | NOT NULL DEFAULT 4 | 敏感级别（1核心/2重要/3敏感/4公开） |
| description | TEXT | | 描述 |
| schema_def | JSONB | | 数据 Schema 定义 |
| storage_path | VARCHAR(500) | | 存储路径 |
| storage_format | VARCHAR(20) | DEFAULT 'parquet' | 存储格式 |
| size_bytes | BIGINT | DEFAULT 0 | 数据大小 |
| record_count | BIGINT | DEFAULT 0 | 记录数 |
| nft_token_id | VARCHAR(128) | | 链上 NFT Token ID |
| status | VARCHAR(20) | NOT NULL DEFAULT 'draft' | 状态 |
| owner_id | UUID | FK → users.id NOT NULL | 所有者 |
| organization_id | UUID | FK → organizations.id NOT NULL | 所属组织 |
| published_at | TIMESTAMPTZ | | 发布时间 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新时间 |

索引: `idx_asset_category`, `idx_asset_level`, `idx_asset_status`, `idx_asset_owner_id`, `idx_asset_org_id`, `idx_asset_nft_token`

**metadata** 元数据表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| asset_id | UUID | FK → data_assets.id NOT NULL UNIQUE | 关联资产 |
| standard | VARCHAR(50) | DEFAULT 'GB/T 36073-2018' | 遵循标准 |
| content | JSONB | NOT NULL | 元数据内容（GB/T 36073 格式） |
| lineage_graph | JSONB | | 血缘图（节点+边定义） |
| version | INTEGER | NOT NULL DEFAULT 1 | 版本号 |
| previous_version_id | UUID | FK → metadata.id | 上一版本 |
| created_by | UUID | FK → users.id | 创建人 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

索引: `idx_meta_asset_id`, `idx_meta_version`

**tags** 标签表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(100) | NOT NULL | 标签名 |
| dimension | VARCHAR(20) | NOT NULL | 维度（industry/security/business） |
| parent_id | UUID | FK → tags.id | 父标签 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

索引: `idx_tag_dimension`, `idx_tag_name`, UNIQUE(name, dimension)

**asset_tags** 资产标签关联表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| asset_id | UUID | FK → data_assets.id NOT NULL | 资产 ID |
| tag_id | UUID | FK → tags.id NOT NULL | 标签 ID |

PK: (asset_id, tag_id)

**access_logs** 访问日志表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users.id | 操作用户 |
| asset_id | UUID | FK → data_assets.id | 访问资产 |
| action | VARCHAR(30) | NOT NULL | 操作类型 |
| compute_task_id | UUID | FK → compute_tasks.id | 关联计算任务 |
| result | VARCHAR(20) | NOT NULL | 结果 |
| ip_address | INET | | 请求 IP |
| details | JSONB | DEFAULT '{}' | 详情 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

索引: `idx_access_user_id`, `idx_access_asset_id`, `idx_access_created_at`

#### 3.2.3 可信计算

**dag_definitions** DAG 定义表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | DAG 名称 |
| description | TEXT | | 描述 |
| nodes | JSONB | NOT NULL | 节点定义 |
| edges | JSONB | NOT NULL | 边定义 |
| version | INTEGER | NOT NULL DEFAULT 1 | 版本 |
| status | VARCHAR(20) | DEFAULT 'draft' | 状态 |
| created_by | UUID | FK → users.id | 创建人 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新时间 |

**compute_tasks** 计算任务表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 任务名称 |
| task_type | VARCHAR(20) | NOT NULL | 类型（FL/MPC/TEE/HE/DP） |
| scenario | VARCHAR(30) | | 业务场景路由 |
| dag_id | UUID | FK → dag_definitions.id | 关联 DAG |
| config | JSONB | NOT NULL | 任务配置 |
| input_asset_ids | UUID[] | NOT NULL | 输入资产 ID 列表 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' | 状态 |
| progress | SMALLINT | DEFAULT 0 | 进度 0-100 |
| result_ref | VARCHAR(500) | | 结果存储路径 |
| result_hash | VARCHAR(128) | | 结果 SM3 哈希 |
| error_message | TEXT | | 错误信息 |
| started_at | TIMESTAMPTZ | | 开始时间 |
| completed_at | TIMESTAMPTZ | | 完成时间 |
| created_by | UUID | FK → users.id NOT NULL | 创建人 |
| organization_id | UUID | FK → organizations.id NOT NULL | 所属组织 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 更新时间 |

索引: `idx_task_type`, `idx_task_status`, `idx_task_created_by`, `idx_task_scenario`

**task_signatures** 任务签名表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| task_id | UUID | FK → compute_tasks.id NOT NULL | 任务 ID |
| signer_did | VARCHAR(128) | NOT NULL | 签名方 DID |
| signature | TEXT | NOT NULL | SM2 签名值 |
| signed_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 签名时间 |

索引: UNIQUE(task_id, signer_did)

#### 3.2.4 区块链

**nft_assets** NFT 资产表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| token_id | VARCHAR(128) | NOT NULL UNIQUE | 链上 Token ID |
| asset_id | UUID | FK → data_assets.id NOT NULL | 关联数据资产 |
| owner_did | VARCHAR(128) | NOT NULL | 所有者 DID |
| creator_did | VARCHAR(128) | NOT NULL | 创建者 DID |
| token_uri | VARCHAR(500) | | 元数据 URI |
| evidence_hash | VARCHAR(128) | NOT NULL | 确权证据 SM3 哈希 |
| certificate_url | VARCHAR(500) | | 确权证书 URL |
| tx_hash | VARCHAR(128) | NOT NULL | 铸造交易哈希 |
| block_number | BIGINT | | 区块号 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**evidence_records** 存证记录表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| node_type | VARCHAR(30) | NOT NULL | 存证节点类型 |
| resource_id | UUID | NOT NULL | 关联资源 ID |
| resource_type | VARCHAR(30) | NOT NULL | 资源类型 |
| data_hash | VARCHAR(128) | NOT NULL | 数据 SM3 哈希 |
| schema_version | VARCHAR(20) | DEFAULT 'v1.0' | JSON Schema 版本 |
| evidence_data | JSONB | NOT NULL | 存证数据 |
| tx_hash | VARCHAR(128) | NOT NULL | 链上交易哈希 |
| block_number | BIGINT | | 区块号 |
| timestamp | BIGINT | NOT NULL | 链上时间戳 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

索引: `idx_evidence_node_type`, `idx_evidence_resource`, `idx_evidence_tx_hash`

**blockchain_transactions** 链上交易记录表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| tx_hash | VARCHAR(128) | NOT NULL UNIQUE | 交易哈希 |
| contract_address | VARCHAR(128) | NOT NULL | 合约地址 |
| method | VARCHAR(100) | NOT NULL | 调用方法 |
| params | JSONB | | 调用参数 |
| from_address | VARCHAR(128) | | 发起地址 |
| block_number | BIGINT | | 区块号 |
| gas_used | BIGINT | | Gas 消耗 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' | 状态 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

#### 3.2.5 运营管理

**service_catalog** 服务目录表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 服务名称 |
| category | VARCHAR(50) | NOT NULL | 分类 |
| parent_id | UUID | FK → service_catalog.id | 父级服务 |
| level | SMALLINT | NOT NULL | 层级（1/2/3） |
| description | TEXT | | 描述 |
| pricing_model | VARCHAR(20) | NOT NULL | 计费模式 |
| pricing_config | JSONB | NOT NULL | 计费配置 |
| quota_limit | INTEGER | | 配额限制 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 状态 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**subscriptions** 服务订阅表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users.id NOT NULL | 订阅用户 |
| service_id | UUID | FK → service_catalog.id NOT NULL | 订阅服务 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'pending' | 状态 |
| start_date | DATE | NOT NULL | 开始日期 |
| end_date | DATE | | 结束日期 |
| quota_used | INTEGER | DEFAULT 0 | 已用配额 |
| approval_status | VARCHAR(20) | DEFAULT 'pending' | 审批状态 |
| approved_by | UUID | FK → users.id | 审批人 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**billing_records** 计费记录表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| subscription_id | UUID | FK → subscriptions.id NOT NULL | 关联订阅 |
| amount | DECIMAL(12,2) | NOT NULL | 金额 |
| billing_period | VARCHAR(20) | NOT NULL | 计费周期 |
| usage_detail | JSONB | | 使用详情 |
| payment_status | VARCHAR(20) | DEFAULT 'pending' | 支付状态 |
| tx_hash | VARCHAR(128) | | 链上结算交易哈希 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**compliance_reports** 合规报告表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| organization_id | UUID | FK → organizations.id NOT NULL | 组织 |
| report_type | VARCHAR(20) | NOT NULL | 类型 |
| period | VARCHAR(20) | NOT NULL | 报告周期 |
| findings | JSONB | NOT NULL | 审计发现 |
| gdpr_checklist | JSONB | | GDPR 清单 |
| data_security_checklist | JSONB | | 数安法清单 |
| status | VARCHAR(20) | DEFAULT 'draft' | 状态 |
| generated_at | TIMESTAMPTZ | | 生成时间 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**data_quality_reports** 数据质量报告表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| asset_id | UUID | FK → data_assets.id NOT NULL | 关联资产 |
| completeness | DECIMAL(5,4) | | 完整性 |
| timeliness_ms | INTEGER | | 时效性 |
| accuracy | DECIMAL(5,4) | | 准确性 |
| consistency | DECIMAL(5,4) | | 一致性 |
| overall_score | DECIMAL(5,4) | | 综合评分 |
| details | JSONB | | 详细检查结果 |
| generated_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 生成时间 |

#### 3.2.6 安全管控

**security_policies** 安全策略表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 策略名称 |
| policy_type | VARCHAR(20) | NOT NULL | 类型（RBAC/ABAC） |
| rules | JSONB | NOT NULL | 策略规则 |
| priority | INTEGER | DEFAULT 0 | 优先级 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| created_by | UUID | FK → users.id | 创建人 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**did_documents** DID 文档表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| did | VARCHAR(128) | NOT NULL UNIQUE | DID 标识 |
| method | VARCHAR(30) | NOT NULL DEFAULT 'did:fisco' | DID 方法 |
| document | JSONB | NOT NULL | W3C DID Document |
| controller | VARCHAR(128) | | 控制者 DID |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 状态 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**vc_records** 可验证凭证表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| vc_id | VARCHAR(128) | NOT NULL UNIQUE | 凭证 ID |
| issuer_did | VARCHAR(128) | NOT NULL | 签发方 DID |
| subject_did | VARCHAR(128) | NOT NULL | 持有方 DID |
| vc_type | VARCHAR(100) | NOT NULL | 凭证类型 |
| claims | JSONB | NOT NULL | 声明内容 |
| signature | TEXT | NOT NULL | SM2 签名 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'active' | 状态 |
| issued_at | TIMESTAMPTZ | NOT NULL | 签发时间 |
| expires_at | TIMESTAMPTZ | | 过期时间 |

**key_store** 密钥存储表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| key_id | VARCHAR(64) | NOT NULL UNIQUE | 密钥标识 |
| algorithm | VARCHAR(20) | NOT NULL | 算法 |
| encrypted_key | TEXT | NOT NULL | 加密后密钥材料 |
| hierarchy_level | VARCHAR(10) | NOT NULL | 层级（master/kek/dek） |
| parent_key_id | VARCHAR(64) | | 父密钥 ID |
| purpose | VARCHAR(50) | NOT NULL | 用途 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| rotated_at | TIMESTAMPTZ | | 轮换时间 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

**threat_events** 威胁事件表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| threat_type | VARCHAR(50) | NOT NULL | 威胁类型 |
| severity | VARCHAR(10) | NOT NULL | 严重程度 |
| source | VARCHAR(100) | | 来源 |
| description | TEXT | NOT NULL | 描述 |
| indicators | JSONB | | 威胁指标 |
| affected_resources | UUID[] | | 受影响资源 |
| status | VARCHAR(20) | DEFAULT 'detected' | 状态 |
| assigned_to | UUID | FK → users.id | 处理人 |
| detected_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 检测时间 |
| resolved_at | TIMESTAMPTZ | | 解决时间 |

**audit_logs** 审计日志表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK → users.id | 操作用户 |
| action | VARCHAR(50) | NOT NULL | 操作动作 |
| resource_type | VARCHAR(30) | NOT NULL | 资源类型 |
| resource_id | UUID | NOT NULL | 资源 ID |
| details | JSONB | | 操作详情 |
| ip_address | INET | | 请求 IP |
| user_agent | VARCHAR(500) | | 浏览器标识 |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT NOW() | 创建时间 |

索引: `idx_audit_user_id`, `idx_audit_action`, `idx_audit_resource`, `idx_audit_created_at`
分区策略: 按 `created_at` 月度分区，保留 ≥6个月

### 3.3 Redis 缓存键设计

| 键模式 | 类型 | TTL | 说明 |
|--------|------|-----|------|
| `session:{session_id}` | Hash | 30min | 用户会话 |
| `ratelimit:{ip}:{endpoint}` | String | 60s | 接口限流计数 |
| `cache:assets:{id}` | Hash | 5min | 数据资产缓存 |
| `cache:catalog:page:{n}` | Hash | 5min | 目录分页缓存 |
| `mfa:pending:{user_id}` | String | 5min | MFA 待验证状态 |
| `lockout:{username}` | String | 15min | 登录锁定 |
| `mqtt:status:{device_did}` | Hash | 1min | 设备在线状态 |
| `mqtt:offline:{device_did}` | List | 永久 | 离线消息队列 |
| `metrics:collect:{source_id}` | Hash | 30s | 实时采集指标 |
| `compute:task:{id}:status` | Hash | 1h | 任务执行状态 |
| `blockchain:nonce:{address}` | String | 永久 | 交易 nonce |
| `blockchain:receipt:{tx_hash}` | Hash | 24h | 交易回执缓存 |
| `billing:daily:{org_id}:{date}` | Hash | 7d | 日计费汇总 |
| `security:threat:score:{ip}` | String | 1h | 威胁评分 |
| `ws:connections:{user_id}` | Set | 永久 | WebSocket 连接集 |

### 3.4 MongoDB 集合设计

**raw_telemetry** 原始遥测数据

```json
{
  "_id": "ObjectId",
  "source_id": "UUID",
  "device_did": "did:fisco:xxx",
  "data_type": "voltage|current|power|temperature",
  "timestamp": "ISO8601",
  "values": {},
  "quality_flag": "valid|invalid|suspect",
  "created_at": "ISO8601"
}
```

索引: `{source_id: 1, timestamp: -1}`, `{device_did: 1, timestamp: -1}`, TTL: 90天

**compute_results** 计算结果

```json
{
  "_id": "ObjectId",
  "task_id": "UUID",
  "task_type": "FL|MPC|TEE|HE|DP",
  "result_data": {},
  "model_artifact_path": "minio://...",
  "metrics": {},
  "created_at": "ISO8601"
}
```

**agent_conversations** Agent 对话记录

```json
{
  "_id": "ObjectId",
  "agent_type": "query|trade|security|dispatch",
  "user_id": "UUID",
  "messages": [],
  "tools_used": [],
  "created_at": "ISO8601"
}
```

---

## 4. API 接口设计

### 4.1 通用约定

**响应格式**:
```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": "2026-05-18T12:00:00Z"
}
```

**分页请求**: `?page=1&page_size=20&sort_by=created_at&sort_order=desc`

**分页响应**:
```json
{
  "code": 0,
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

**错误码**:

| 范围 | 含义 |
|------|------|
| 0 | 成功 |
| 1000-1999 | 认证/授权错误 |
| 2000-2999 | 数据资源错误 |
| 3000-3999 | 计算任务错误 |
| 4000-4999 | 区块链错误 |
| 5000-5999 | 运营管理错误 |
| 6000-6999 | 安全管控错误 |
| 9000-9999 | 系统错误 |

### 4.2 REST API 端点列表

#### 认证模块 /api/v1/auth

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/auth/login | 登录（DID/密码/SM2证书） | P0-PORTAL-01 |
| POST | /api/v1/auth/mfa/verify | MFA 验证 | P0-PORTAL-01 |
| POST | /api/v1/auth/logout | 登出 | P0-PORTAL-01 |
| POST | /api/v1/auth/refresh | 刷新 Token | P0-PORTAL-01 |
| GET | /api/v1/auth/session | 获取当前会话 | P0-PORTAL-06 |

#### 数据源 /api/v1/data/sources

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/data/sources | 数据源列表 | P0-DATA-01 |
| POST | /api/v1/data/sources | 注册数据源 | P0-DATA-01 |
| GET | /api/v1/data/sources/{id} | 数据源详情 | P0-DATA-01 |
| PUT | /api/v1/data/sources/{id} | 更新数据源 | P0-DATA-01 |
| DELETE | /api/v1/data/sources/{id} | 删除数据源 | P0-DATA-01 |
| POST | /api/v1/data/sources/{id}/start | 启动采集 | P0-DATA-03 |
| POST | /api/v1/data/sources/{id}/stop | 停止采集 | P0-DATA-03 |
| GET | /api/v1/data/sources/{id}/status | 采集状态 | P0-DATA-03 |
| GET | /api/v1/data/sources/{id}/metrics | 采集指标 | P0-DATA-10 |

#### 数据资产 /api/v1/data/assets

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/data/assets | 资产列表 | P0-DATA-06 |
| POST | /api/v1/data/assets | 创建资产 | P0-DATA-11 |
| GET | /api/v1/data/assets/{id} | 资产详情 | P0-DATA-11 |
| PUT | /api/v1/data/assets/{id} | 更新资产 | P0-DATA-11 |
| DELETE | /api/v1/data/assets/{id} | 删除资产 | P0-DATA-11 |
| POST | /api/v1/data/assets/{id}/classify | 执行分类分级 | P0-DATA-06 |
| POST | /api/v1/data/assets/{id}/publish | 发布至目录 | P0-DATA-09 |
| POST | /api/v1/data/assets/{id}/preprocess | 触发边缘预处理 | P0-DATA-02 |

#### 数据目录 /api/v1/data/catalog

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/data/catalog | 浏览数据目录 | P0-DATA-09 |
| GET | /api/v1/data/catalog/search | 搜索/筛选 | P0-PORTAL-03 |
| GET | /api/v1/data/catalog/{id}/preview | 脱敏预览（10条） | P0-DATA-09 |
| POST | /api/v1/data/catalog/{id}/apply | 申请使用 | P0-PORTAL-04 |
| POST | /api/v1/data/catalog/{id}/feedback | 评价反馈 | P0-DATA-09 |

#### 元数据 /api/v1/data/metadata

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/data/metadata | 元数据列表 | P0-DATA-08 |
| POST | /api/v1/data/metadata | 创建元数据 | P0-DATA-08 |
| GET | /api/v1/data/metadata/{id} | 元数据详情 | P0-DATA-08 |
| PUT | /api/v1/data/metadata/{id} | 更新元数据 | P0-DATA-08 |
| GET | /api/v1/data/metadata/{id}/lineage | 血缘可视化 | P0-DATA-08 |
| GET | /api/v1/data/metadata/{id}/versions | 版本列表 | P0-DATA-08 |

#### 标签 /api/v1/data/tags

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/data/tags | 标签列表 | P0-DATA-07 |
| POST | /api/v1/data/tags | 创建标签 | P0-DATA-07 |
| GET | /api/v1/data/tags/dimensions | 按维度聚合 | P0-DATA-07 |

#### 数据质量 /api/v1/data/quality

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/data/quality/reports | 质量报告列表 | P0-DATA-10 |
| GET | /api/v1/data/quality/reports/{id} | 质量报告详情 | P0-DATA-10 |
| POST | /api/v1/data/quality/check | 触发质量检查 | P0-DATA-10 |

#### 计算任务 /api/v1/compute/tasks

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/compute/tasks | 任务列表 | P0-COMP-07 |
| POST | /api/v1/compute/tasks | 创建任务 | P0-COMP-07 |
| GET | /api/v1/compute/tasks/{id} | 任务详情 | P0-COMP-07 |
| PUT | /api/v1/compute/tasks/{id} | 更新任务 | P0-COMP-07 |
| POST | /api/v1/compute/tasks/{id}/start | 启动任务 | P0-COMP-07 |
| POST | /api/v1/compute/tasks/{id}/stop | 停止任务 | P0-COMP-07 |
| GET | /api/v1/compute/tasks/{id}/result | 获取结果 | P0-COMP-07 |
| POST | /api/v1/compute/tasks/{id}/sign | 多方签名 | P0-COMP-07 |
| GET | /api/v1/compute/tasks/{id}/signatures | 签名状态 | P0-COMP-07 |

#### DAG 编排 /api/v1/compute/dag

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/compute/dag | DAG 列表 | P0-COMP-07 |
| POST | /api/v1/compute/dag | 创建 DAG | P0-COMP-07 |
| GET | /api/v1/compute/dag/{id} | DAG 详情 | P0-COMP-07 |
| PUT | /api/v1/compute/dag/{id} | 更新 DAG | P0-COMP-07 |
| POST | /api/v1/compute/dag/{id}/execute | 执行 DAG | P0-COMP-07 |

#### 联邦学习 /api/v1/compute/fl

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/compute/fl/train | 发起 FL 训练 | P0-COMP-01 |
| GET | /api/v1/compute/fl/models | 模型列表 | P0-COMP-01 |
| GET | /api/v1/compute/fl/models/{id} | 模型详情 | P0-COMP-01 |
| POST | /api/v1/compute/fl/models/{id}/evaluate | 模型评估 | P0-COMP-01 |

#### 安全多方计算 /api/v1/compute/mpc

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/compute/mpc/compute | 发起 MPC 计算 | P0-COMP-02 |
| GET | /api/v1/compute/mpc/protocols | 可用协议 | P0-COMP-02 |

#### TEE /api/v1/compute/tee

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/compute/tee/execute | TEE 内执行 | P0-COMP-03 |
| GET | /api/v1/compute/tee/status/{id} | TEE 实例状态 | P0-COMP-03 |

#### 同态加密 /api/v1/compute/he

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/compute/he/compute | 同态加密计算 | P0-COMP-04 |
| POST | /api/v1/compute/he/encrypt | 数据加密上传 | P0-COMP-04 |

#### 差分隐私 /api/v1/compute/dp

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/compute/dp/apply | 应用差分隐私 | P0-COMP-05 |
| GET | /api/v1/compute/dp/configs | DP 配置列表 | P0-COMP-05 |

#### 数据沙箱 /api/v1/compute/sandbox

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/compute/sandbox | 沙箱列表 | P0-COMP-08 |
| POST | /api/v1/compute/sandbox | 创建沙箱 | P0-COMP-08 |
| GET | /api/v1/compute/sandbox/{id} | 沙箱详情 | P0-COMP-08 |
| DELETE | /api/v1/compute/sandbox/{id} | 删除沙箱 | P0-COMP-08 |
| POST | /api/v1/compute/sandbox/{id}/scan | 算法准入扫描 | P0-COMP-08 |
| POST | /api/v1/compute/sandbox/{id}/export | 出口审核 | P0-COMP-08 |

#### AI Agent /api/v1/compute/agents

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/compute/agents/query | QueryAgent | P0-COMP-11 |
| POST | /api/v1/compute/agents/trade | TradeAgent | P0-COMP-11 |
| POST | /api/v1/compute/agents/security | SecurityAgent | P0-COMP-11 |
| POST | /api/v1/compute/agents/dispatch | DispatchAgent | P0-COMP-11 |
| GET | /api/v1/compute/agents/history | 对话历史 | P0-COMP-11 |

#### 区块链 NFT /api/v1/blockchain/nft

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/blockchain/nft/mint | 铸造 NFT | P0-CHAIN-01 |
| GET | /api/v1/blockchain/nft/{token_id} | NFT 详情 | P0-CHAIN-01 |
| GET | /api/v1/blockchain/nft/owner/{did} | 按 DID 查询 | P0-CHAIN-01 |
| POST | /api/v1/blockchain/nft/{token_id}/transfer | 转移 NFT | P0-CHAIN-01 |

#### 存证 /api/v1/blockchain/evidence

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/blockchain/evidence | 提交存证 | P0-CHAIN-02 |
| GET | /api/v1/blockchain/evidence/{id} | 存证详情 | P0-CHAIN-02 |
| GET | /api/v1/blockchain/evidence/trace/{resource_id} | 溯源查询 | P0-CHAIN-02, P0-CHAIN-06 |
| GET | /api/v1/blockchain/evidence/range | 范围查询 | P0-CHAIN-06 |

#### 智能合约 /api/v1/blockchain/contracts

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/blockchain/contracts | 合约列表 | P0-CHAIN-05 |
| GET | /api/v1/blockchain/contracts/{address} | 合约详情+ABI | P0-CHAIN-05 |
| POST | /api/v1/blockchain/contracts/{address}/call | 调用合约方法 | P0-CHAIN-05 |
| GET | /api/v1/blockchain/transactions | 交易记录 | P0-CHAIN-05 |

#### 结算 /api/v1/blockchain/settle

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/blockchain/settle | 触发结算 | P0-CHAIN-03 |
| GET | /api/v1/blockchain/settle/{id} | 结算详情 | P0-CHAIN-03 |
| GET | /api/v1/blockchain/settle/dispute/{id} | 争议仲裁 | P0-CHAIN-03 |

#### 用户管理 /api/v1/ops/users

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/ops/users | 用户列表 | P0-OPS-01 |
| POST | /api/v1/ops/users | 创建用户 | P0-OPS-01 |
| GET | /api/v1/ops/users/{id} | 用户详情 | P0-OPS-01 |
| PUT | /api/v1/ops/users/{id} | 更新用户 | P0-OPS-01 |
| DELETE | /api/v1/ops/users/{id} | 删除用户 | P0-OPS-01 |
| POST | /api/v1/ops/users/import | 批量 Excel 导入 | P0-OPS-01 |

#### 组织管理 /api/v1/ops/organizations

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/ops/organizations | 组织列表 | P0-OPS-01 |
| POST | /api/v1/ops/organizations | 创建组织 | P0-OPS-01 |
| GET | /api/v1/ops/organizations/{id} | 组织详情 | P0-OPS-01 |
| PUT | /api/v1/ops/organizations/{id} | 更新组织 | P0-OPS-01 |
| GET | /api/v1/ops/organizations/{id}/tree | 组织树 | P0-OPS-01 |

#### 服务管理 /api/v1/ops/services

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/ops/services | 服务目录 | P0-OPS-02 |
| POST | /api/v1/ops/services | 创建服务 | P0-OPS-02 |
| GET | /api/v1/ops/services/{id} | 服务详情 | P0-OPS-02 |
| PUT | /api/v1/ops/services/{id} | 更新服务 | P0-OPS-02 |
| GET | /api/v1/ops/services/{id}/subscriptions | 订阅列表 | P0-OPS-02 |
| POST | /api/v1/ops/services/{id}/subscribe | 订阅服务 | P0-PORTAL-04 |
| PUT | /api/v1/ops/subscriptions/{id}/approve | 审批订阅 | P0-PORTAL-04 |

#### 计费 /api/v1/ops/billing

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/ops/billing/records | 计费记录 | P0-OPS-02 |
| GET | /api/v1/ops/billing/invoice/{period} | 月度账单 | P0-OPS-02 |
| GET | /api/v1/ops/billing/summary | 计费汇总 | P0-OPS-02 |

#### 运营监控 /api/v1/ops/monitoring

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/ops/monitoring/metrics | 业务指标 | P0-OPS-03 |
| GET | /api/v1/ops/monitoring/alerts | 告警列表 | P0-OPS-03 |
| POST | /api/v1/ops/monitoring/alerts/{id}/ack | 确认告警 | P0-OPS-03 |
| GET | /api/v1/ops/monitoring/health | 健康检查 | P0-OPS-03 |

#### 合规 /api/v1/ops/compliance

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/ops/compliance/reports | 合规报告列表 | P0-OPS-04 |
| POST | /api/v1/ops/compliance/reports/generate | 生成报告 | P0-OPS-04 |
| GET | /api/v1/ops/compliance/reports/{id} | 报告详情 | P0-OPS-04 |
| GET | /api/v1/ops/compliance/checklist | 合规检查清单 | P0-OPS-04 |

#### KPI /api/v1/ops/kpi

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/ops/kpi/dashboard | KPI 仪表盘 | P0-OPS-05 |
| GET | /api/v1/ops/kpi/sla | SLA 指标 | P0-OPS-05 |
| GET | /api/v1/ops/kpi/performance | 性能指标 | P0-OPS-05 |

#### 安全策略 /api/v1/security/policies

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/security/policies | 策略列表 | P0-SEC-01 |
| POST | /api/v1/security/policies | 创建策略 | P0-SEC-01 |
| GET | /api/v1/security/policies/{id} | 策略详情 | P0-SEC-01 |
| PUT | /api/v1/security/policies/{id} | 更新策略 | P0-SEC-01 |
| DELETE | /api/v1/security/policies/{id} | 删除策略 | P0-SEC-01 |
| POST | /api/v1/security/policies/evaluate | 评估权限 | P0-SEC-01 |

#### DID /api/v1/security/did

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/security/did/create | 创建 DID | P0-SEC-02 |
| GET | /api/v1/security/did/{did} | 解析 DID Document | P0-SEC-02 |
| PUT | /api/v1/security/did/{did} | 更新 DID Document | P0-SEC-02 |
| POST | /api/v1/security/did/{did}/deactivate | 停用 DID | P0-SEC-02 |

#### 可验证凭证 /api/v1/security/vc

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/security/vc/issue | 签发 VC | P0-SEC-02 |
| POST | /api/v1/security/vc/verify | 验证 VC | P0-SEC-02 |
| POST | /api/v1/security/vc/{id}/revoke | 撤销 VC | P0-SEC-02 |
| GET | /api/v1/security/vc/list | VC 列表 | P0-SEC-02 |

#### 密钥管理 /api/v1/security/keys

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/security/keys | 密钥列表 | P0-SEC-03 |
| POST | /api/v1/security/keys/generate | 生成密钥 | P0-SEC-03 |
| GET | /api/v1/security/keys/{key_id} | 密钥详情 | P0-SEC-03 |
| POST | /api/v1/security/keys/{key_id}/rotate | 轮换密钥 | P0-SEC-03 |
| GET | /api/v1/security/keys/{key_id}/audit | 使用审计 | P0-SEC-03 |
| POST | /api/v1/security/keys/shamir/split | Shamir 分割 | P0-SEC-03 |
| POST | /api/v1/security/keys/shamir/combine | Shamir 恢复 | P0-SEC-03 |

#### 威胁检测 /api/v1/security/threats

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| GET | /api/v1/security/threats | 威胁事件列表 | P0-SEC-04 |
| POST | /api/v1/security/threats/detect | 主动检测 | P0-SEC-04 |
| GET | /api/v1/security/threats/{id} | 威胁详情 | P0-SEC-04 |
| PUT | /api/v1/security/threats/{id}/resolve | 处置威胁 | P0-SEC-04 |
| GET | /api/v1/security/threats/dashboard | 安全态势 | P0-SEC-04 |

#### 国密 /api/v1/security/gmssl

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/security/gmssl/sm2/sign | SM2 签名 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm2/verify | SM2 验签 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm2/encrypt | SM2 加密 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm2/decrypt | SM2 解密 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm3/hash | SM3 哈希 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm4/encrypt | SM4 加密 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm4/decrypt | SM4 解密 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm9/sign | SM9 签名 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/sm9/verify | SM9 验签 | P0-SEC-05 |
| POST | /api/v1/security/gmssl/zuc/encrypt | ZUC 加密 | P0-SEC-05 |

#### 零知识证明 /api/v1/security/zkp

| 方法 | 路径 | 说明 | 对应需求 |
|------|------|------|----------|
| POST | /api/v1/security/zkp/groth16/prove | Groth16 证明 | P0-SEC-06 |
| POST | /api/v1/security/zkp/groth16/verify | Groth16 验证 | P0-SEC-06 |
| POST | /api/v1/security/zkp/bbs/sign | BBS+ 签名 | P0-SEC-06 |
| POST | /api/v1/security/zkp/bbs/verify | BBS+ 验证 | P0-SEC-06 |
| POST | /api/v1/security/zkp/bulletproofs/prove | Bulletproofs 范围证明 | P0-SEC-06 |
| POST | /api/v1/security/zkp/bulletproofs/verify | Bulletproofs 验证 | P0-SEC-06 |

### 4.3 WebSocket 端点

| 路径 | 说明 | 对应需求 |
|------|------|----------|
| /ws/notifications | 全局通知推送 | P0-PORTAL-04 |
| /ws/compute/{task_id} | 计算任务状态实时推送 | P0-COMP-07 |
| /ws/monitor | 监管大屏实时数据 | P0-PORTAL-05 |
| /ws/security/threats | 安全威胁实时告警 | P0-SEC-04 |

### 4.4 MQTT 主题体系

| 主题 | QoS | 说明 | 对应需求 |
|------|-----|------|----------|
| energy/collect/{device_did}/{data_type} | 1 | 数据采集 | P0-DATA-05 |
| energy/register/{device_did} | 1 | 设备注册 | P0-DATA-05 |
| energy/heartbeat/{device_did} | 0 | 心跳上报 | P0-DATA-05 |
| energy/alarm/{device_did}/{alarm_type} | 1 | 告警推送 | P0-DATA-05 |

---

## 5. 区块链架构

### 5.1 FISCO BCOS 网络拓扑

```
┌─────────────────────────────────────────────────┐
│              Docker Host (单服务器)               │
│                                                   │
│  ┌──────────┐  ┌──────────┐                       │
│  │  Node0   │  │  Node1   │    PBFT 共识          │
│  │  :20200  │  │  :20201  │    4 共识节点          │
│  ├──────────┤  ├──────────┤    链ID: energy-1     │
│  │  Node2   │  │  Node3   │    区块间隔: 1s       │
│  │  :20202  │  │  :20203  │    8C16G + 1TB SSD   │
│  └──────────┘  └──────────┘                       │
│                                                   │
│  ┌──────────────────────────────────────────┐    │
│  │  Python SDK (fisco_client.py)            │    │
│  │  Channel 协议连接 → Node0:20200          │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### 5.2 Solidity 合约接口定义

#### IdentityRegistry.sol — DID 身份注册

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract IdentityRegistry {
    struct DidRecord {
        string did;
        address controller;
        string publicKey;     // SM2 公钥
        uint256 registeredAt;
        bool active;
    }

    mapping(string => DidRecord) public didRecords;
    mapping(address => string) public addressToDid;

    event DidRegistered(string did, address controller, uint256 timestamp);
    event DidUpdated(string did, string newPublicKey, uint256 timestamp);
    event DidDeactivated(string did, uint256 timestamp);

    function registerDid(string calldata did, string calldata publicKey) external;
    function updateDid(string calldata did, string calldata newPublicKey) external;
    function deactivateDid(string calldata did) external;
    function resolveDid(string calldata did) external view returns (DidRecord memory);
    function verifyDidSignature(string calldata did, bytes32 hash, bytes calldata signature) external view returns (bool);
}
```

#### DataAssetNFT.sol — 数据资产 NFT

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DataAssetNFT {
    struct AssetMetadata {
        string assetId;
        string category;
        uint8 classificationLevel;
        string evidenceHash;
        string certificateURI;
        uint256 mintedAt;
    }

    mapping(uint256 => AssetMetadata) public tokenMetadata;
    mapping(uint256 => string) public tokenToAssetId;
    mapping(string => uint256) public assetIdToToken;

    event NFTMinted(uint256 tokenId, string assetId, string ownerDid, string evidenceHash);
    event NFTTransferred(uint256 tokenId, string fromDid, string toDid);

    function mint(string calldata assetId, string calldata category,
                   uint8 level, string calldata evidenceHash,
                   string calldata certificateURI) external returns (uint256);
    function transferByDid(uint256 tokenId, string calldata toDid) external;
    function verifyOwnership(uint256 tokenId, string calldata did) external view returns (bool);
    function getTokenMetadata(uint256 tokenId) external view returns (AssetMetadata memory);
    function getTokensByDid(string calldata did) external view returns (uint256[] memory);
}
```

#### AccessControl.sol — 访问控制

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AccessControl {
    struct AccessPolicy {
        uint256 nftTokenId;
        string consumerDid;
        string accessType;
        uint256 expiresAt;
        bool active;
    }

    mapping(bytes32 => AccessPolicy) public policies;
    mapping(uint256 => bytes32[]) public tokenPolicies;

    event AccessGranted(uint256 tokenId, string consumerDid, string accessType, uint256 expiresAt);
    event AccessRevoked(uint256 tokenId, string consumerDid);

    function grantAccess(uint256 tokenId, string calldata consumerDid,
                         string calldata accessType, uint256 expiresAt) external;
    function revokeAccess(uint256 tokenId, string calldata consumerDid) external;
    function checkAccess(uint256 tokenId, string calldata consumerDid,
                        string calldata accessType) external view returns (bool);
    function getTokenPolicies(uint256 tokenId) external view returns (AccessPolicy[] memory);
}
```

#### UsageLogger.sol — 使用记录

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract UsageLogger {
    struct UsageRecord {
        uint256 nftTokenId;
        string consumerDid;
        string usageType;
        string inputHash;
        string outputHash;
        uint256 timestamp;
        bytes32 recordHash;
    }

    mapping(bytes32 => UsageRecord) public records;
    mapping(uint256 => bytes32[]) public tokenUsageRecords;

    event UsageLogged(bytes32 recordHash, uint256 tokenId, string consumerDid, uint256 timestamp);

    function logUsage(uint256 tokenId, string calldata consumerDid,
                      string calldata usageType, string calldata inputHash,
                      string calldata outputHash) external returns (bytes32);
    function getUsageRecord(bytes32 recordHash) external view returns (UsageRecord memory);
    function getTokenUsageRecords(uint256 tokenId) external view returns (UsageRecord[] memory);
    function verifyUsageRecord(bytes32 recordHash) external view returns (bool);
}
```

#### AutoSettlement.sol — 自动结算

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AutoSettlement {
    struct SettlementRule {
        uint256 serviceId;
        uint256 pricePerUnit;
        string pricingModel;
        address recipient;
        bool active;
    }

    struct SettlementRecord {
        uint256 ruleId;
        string payerDid;
        string payeeDid;
        uint256 amount;
        string usageRef;
        uint256 timestamp;
        bool disputed;
    }

    mapping(uint256 => SettlementRule) public rules;
    mapping(uint256 => SettlementRecord) public settlements;
    uint256 public nextSettlementId;

    event RuleCreated(uint256 ruleId, uint256 serviceId, uint256 price);
    event SettlementExecuted(uint256 settlementId, string payerDid, uint256 amount);
    event DisputeRaised(uint256 settlementId, string reason);

    function createRule(uint256 serviceId, uint256 pricePerUnit,
                        string calldata model, address recipient) external returns (uint256);
    function executeSettlement(uint256 ruleId, string calldata payerDid,
                               string calldata payeeDid, uint256 quantity,
                               string calldata usageRef) external returns (uint256);
    function raiseDispute(uint256 settlementId, string calldata reason) external;
    function resolveDispute(uint256 settlementId, uint256 newAmount) external;
    function getSettlement(uint256 settlementId) external view returns (SettlementRecord memory);
}
```

#### ComplianceAudit.sol — 合规审计

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ComplianceAudit {
    struct AuditEntry {
        string resourceType;
        string resourceId;
        string nodeType;     // 8个节点
        string dataHash;     // SM3
        string operatorDid;
        string schemaVersion;
        uint256 timestamp;
        bytes32 entryHash;
    }

    mapping(bytes32 => AuditEntry) public entries;
    mapping(string => bytes32[]) public resourceAuditTrail;

    event AuditEntryCreated(bytes32 entryHash, string resourceType, string resourceId, string nodeType);

    function createAuditEntry(string calldata resourceType, string calldata resourceId,
                              string calldata nodeType, string calldata dataHash,
                              string calldata operatorDid) external returns (bytes32);
    function getAuditEntry(bytes32 entryHash) external view returns (AuditEntry memory);
    function getResourceAuditTrail(string calldata resourceId) external view returns (AuditEntry[] memory);
    function verifyAuditEntry(bytes32 entryHash) external view returns (bool);
    function getEntriesByNodeType(string calldata nodeType, uint256 from, uint256 to)
                                  external view returns (AuditEntry[] memory);
}
```

### 5.3 链上数据格式

**8 节点存证 JSON Schema**:
```json
{
  "$schema": "https://energy-ds.org/evidence/v1.0",
  "nodeType": "collect | preprocess | classify | publish | apply | compute | result | settle",
  "resourceType": "data_asset | compute_task | billing",
  "resourceId": "uuid",
  "dataHash": "sm3-hash-hex",
  "operatorDid": "did:fisco:0x...",
  "timestamp": 1716000000,
  "metadata": {}
}
```

---

## 6. 隐私计算架构

### 6.1 FATE 联邦学习部署方案

```
┌─────────────────────────────────────────────┐
│               FATE Cluster                   │
│  ┌──────────────┐   ┌──────────────────────┐ │
│  │  Coordinator │   │  Party 0 (Host)      │ │
│  │  8C32GB      │   │  4C16GB              │ │
│  │  FATE Flow   │   │  FATE Board          │ │
│  │  MySQL       │   │  MySQL               │ │
│  └──────┬───────┘   └──────────┬───────────┘ │
│         │                      │             │
│  ┌──────┴───────┐   ┌──────────┴───────────┐ │
│  │  Party 1     │   │  Party 2             │ │
│  │  4C16GB      │   │  4C16GB              │ │
│  └──────────────┘   └──────────────────────┘ │
└─────────────────────────────────────────────┘
```

**集成方式**: FastAPI 通过 FATE Flow REST API 提交训练任务，轮询/Webhook 获取结果。

**支持模型**:
- 横向联邦 LR (HomoLR)
- 纵向联邦 NN (HeteroNN)
- 联邦树模型 (SecureBoost)

### 6.2 MP-SPDZ 集成方案

**架构**: MP-SPDZ 作为独立 Docker 容器运行，FastAPI 通过子进程调用编译后的 MP-SPDZ 程序。

**支持协议**: 秘密分享(SPDZ/2k)、混淆电路(Yao's GC)、不经意传输(OT)

**交互流程**:
1. FastAPI 接收 MPC 请求 → 准备输入数据（加密分片）
2. 调用 MP-SPDZ 编译脚本生成可执行文件
3. 启动多方计算进程（3方 Docker 容器）
4. 等待结果 → 解密 → 返回

### 6.3 SEAL 集成方案

**架构**: Python 绑定（seal-python）或子进程调用 C++ 编译的 SEAL 程序。

**支持方案**:
- CKKS: 浮点数同态运算（发电量预测）
- BFV: 整数同态运算（用电量统计）

**关键接口**:
```python
class HEService:
    def encrypt_ckks(self, plaintext: list[float], public_key) -> Ciphertext
    def compute_ckks(self, ciphertext_a, ciphertext_b, operation) -> Ciphertext
    def decrypt_ckks(self, ciphertext, secret_key) -> list[float]
    def encrypt_bfv(self, plaintext: list[int], public_key) -> Ciphertext
    def compute_bfv(self, ciphertext_a, ciphertext_b, operation) -> Ciphertext
    def decrypt_bfv(self, ciphertext, secret_key) -> list[int]
```

### 6.4 Gramine/SGX 集成方案

**架构**:
1. 应用代码打包为 Docker 镜像
2. Gramine 清单文件定义 enclave 配置
3. 通过 `gramine-sgx` 启动 SGX enclave
4. FastAPI 通过 gRPC/REST 与 enclave 内应用通信

### 6.5 DAG 任务编排引擎设计

```
┌─────────────────────────────────────────┐
│              DAG Engine                  │
│                                          │
│  Parser ──→ Validator ──→ Scheduler      │
│                               │          │
│                          Executor        │
│                          ┌────┘          │
│                          │               │
│           ┌──────┬───────┼──────┬──────┐ │
│           FL     MPC     TEE    HE     DP│
└─────────────────────────────────────────┘
```

**DAG 节点定义**:
```python
@dataclass
class DagNode:
    id: str
    node_type: str           # fl/mpc/tee/he/dp/data_input/data_output
    config: dict             # 节点配置
    dependencies: list[str]  # 上游节点 ID
    compute_config: dict     # 计算参数

@dataclass
class DagEdge:
    source: str
    target: str
    data_mapping: dict       # 输出→输入映射
```

**执行引擎**: Parser → Validator(环检测/类型兼容) → Scheduler(拓扑排序/并行) → Executor(分发到后端) → Monitor(状态/超时/重试)

### 6.6 业务场景路由映射

| 场景 | 计算模式 | 路由键 | 对应需求 |
|------|----------|--------|----------|
| 发电预测 | FL | `power_forecast` | P0-COMP-06 |
| 多方结算 | MPC | `multi_settlement` | P0-COMP-06 |
| 调度指令 | TEE | `dispatch_order` | P0-COMP-06 |
| 统计分析 | DP | `statistical_analysis` | P0-COMP-06 |
| 跨区域 | HE | `cross_region` | P0-COMP-06 |
| 信用评估 | VFL | `credit_evaluation` | P0-COMP-06 |

---

## 7. 基础设施架构

### 7.1 Docker Compose 服务编排

**容器列表** (~20 个):

| 服务 | 镜像 | 端口 | 资源 | 依赖 |
|------|------|------|------|------|
| postgres | postgres:16 | 5432 | 4C8G | - |
| redis | redis:7-alpine | 6379 | 2C4G | - |
| mongodb | mongo:7 | 27017 | 2C4G | - |
| minio | minio/minio | 9000/9001 | 2C4G | - |
| emqx | emqx/emqx:5 | 1883/8083/18083 | 2C4G | - |
| backend | 自建 | 8000 | 4C8G | pg,redis,mongo,minio,emqx |
| frontend | 自建 | 80 | 2C2G | backend |
| fisco-node0 | 自建 | 20200 | 2C4G | - |
| fisco-node1 | 自建 | 20201 | 2C4G | - |
| fisco-node2 | 自建 | 20202 | 2C4G | - |
| fisco-node3 | 自建 | 20203 | 2C4G | - |
| fate-coordinator | 自建 | 9380 | 8C32G | - |
| fate-party0 | 自建 | - | 4C16G | fate-coordinator |
| mpspdz-party0 | 自建 | - | 2C4G | - |
| mpspdz-party1 | 自建 | - | 2C4G | - |
| mpspdz-party2 | 自建 | - | 2C4G | - |
| prometheus | prom/prometheus | 9090 | 1C2G | - |
| grafana | grafana/grafana | 3000 | 1C1G | prometheus |

### 7.2 网络拓扑

```
┌──────────────────────────────────────────────────────────────┐
│                    Docker Network: energy-net                 │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ frontend │  │ backend  │  │ postgres │  │  redis   │     │
│  │  :80     │  │  :8000   │  │  :5432   │  │  :6379   │     │
│  └──────────┘  └────┬─────┘  └──────────┘  └──────────┘     │
│                      │                                        │
│  ┌──────────┐  ┌─────┴────┐  ┌──────────┐  ┌──────────┐     │
│  │ mongodb  │  │  minio   │  │   emqx   │  │ prometh  │     │
│  │ :27017   │  │  :9000   │  │  :1883   │  │  :9090   │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │          FISCO BCOS Subnet (fisco-net)                │   │
│  │  node0:20200  node1:20200  node2:20200  node3:20200  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │        Privacy Computing Subnet (privacy-net)          │   │
│  │  fate-coord  fate-party  mpspdz-0  mpspdz-1  mpspdz-2 │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────┐                                                 │
│  │ grafana  │                                                 │
│  │  :3000   │                                                 │
│  └──────────┘                                                 │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 存储卷规划

| 卷名 | 用途 | 预估大小 | 备份策略 |
|------|------|----------|----------|
| pg_data | PostgreSQL 数据 | 50GB | 每日 pg_dump |
| redis_data | Redis 持久化 | 4GB | RDB+AOF |
| mongo_data | MongoDB 遥测/审计 | 100GB | 每日 mongodump |
| minio_data | 文件/模型存储 | 200GB | MinIO 镜像 |
| fisco_node0-3 | 区块链数据 | 4×100GB | 链式同步 |
| fate_data | FATE 模型/数据 | 50GB | 模型快照 |
| prometheus_data | 监控指标 | 30GB | 15天保留 |

---

## 8. 任务分解

### 8.1 任务列表

#### T01: 项目基础设施与配置

| 字段 | 值 |
|------|-----|
| **任务 ID** | T01 |
| **名称** | 项目基础设施与配置 |
| **优先级** | P0 |
| **复杂度** | XL |
| **依赖** | 无 |

**描述**: 搭建项目完整的基础设施，包括所有配置文件、入口文件、依赖声明、数据库初始化、Docker 编排和开发环境。

**涉及文件** (~35 个):
- 前端基础设施: package.json, vite.config.ts, tsconfig.json, tailwind.config.ts, postcss.config.js, index.html, Dockerfile, nginx.conf
- 前端入口: src/main.tsx, src/App.tsx, src/vite-env.d.ts
- 前端主题: src/theme/index.ts, palette.ts, typography.ts
- 前端路由: src/routes/index.tsx, ProtectedRoute.tsx, LazyLoad.tsx
- 前端布局: src/layouts/MainLayout.tsx, AuthLayout.tsx, FullScreenLayout.tsx
- 后端基础设施: pyproject.toml, requirements.txt, Dockerfile, alembic.ini, alembic/env.py, alembic/versions/0001_init.py
- 后端入口: app/__init__.py, main.py, config.py, database.py, dependencies.py, exceptions.py, middleware.py
- 项目根: docker-compose.yml, .env.example, Makefile
- 部署: deploy/nginx/nginx.conf, deploy/docker/backend.Dockerfile, deploy/docker/frontend.Dockerfile

**验收标准**:
- `docker compose up` 所有基础容器正常启动
- 前端访问 `http://localhost` 显示空白主布局
- 后端访问 `http://localhost:8000/docs` 显示 Swagger 文档
- 数据库迁移成功执行
- 前端主题色（能源蓝 #1976D2 / 可信绿 #2E7D32）正确渲染

---

#### T02: 后端核心服务层

| 字段 | 值 |
|------|-----|
| **任务 ID** | T02 |
| **名称** | 后端核心服务层 |
| **优先级** | P0 |
| **复杂度** | XL |
| **依赖** | T01 |

**描述**: 实现所有后端业务逻辑，包括全部 API 路由(33个端点文件)、服务层(33个服务)、数据模型(12个模型文件)、Pydantic Schema(10个)、核心模块(6个)，覆盖 47 项 P0 需求中的后端部分。

**涉及文件** (~75 个):
- 数据模型: models/ 下 12 个文件（user, data_asset, tag, access_log, compute_task, blockchain, service, audit_log, security, compliance 等）
- Schema: schemas/ 下 10 个文件
- API 路由: api/v1/ 下 33 个端点文件
- 服务层: services/ 下 33 个服务文件
- 核心模块: core/ 下 6 个文件（security, gmssl_adapter, fisco_client, mqtt_client, ws_manager, task_scheduler）
- 工具: utils/ 下 4 个文件

**验收标准**:
- 所有 API 端点可通过 Swagger 文档访问
- 认证流程（DID/密码/SM2证书+MFA）完整可用
- 数据源 CRUD + 采集启停 + MQTT 消息收发
- 数据资产分类分级引擎 + 目录发布 + 脱敏预览
- 计算任务 CRUD + DAG 编排 + 场景路由
- 区块链交互（NFT/存证/合约调用/结算）
- 运营管理（用户/组织/服务/计费/监控/合规/KPI）
- 安全管控（策略/DID/VC/密钥/威胁/国密/ZKP）
- WebSocket 实时推送
- 全链路国密 SM2/SM3/SM4
- 全操作审计日志

---

#### T03: 前端核心应用层

| 字段 | 值 |
|------|-----|
| **任务 ID** | T03 |
| **名称** | 前端核心应用层 |
| **优先级** | P0 |
| **复杂度** | XL |
| **依赖** | T01 |

**描述**: 实现所有前端页面组件(27个页面)、状态管理(7个store)、API 服务层(8个service)、通用组件(10个)、ECharts 大屏、DAG 画布，覆盖 47 项 P0 需求中的前端部分。

**涉及文件** (~65 个):
- 状态管理: stores/ 下 7 个文件
- Hooks: hooks/ 下 4 个文件
- API 服务: services/ 下 8 个文件
- 类型定义: types/ 下 7 个文件
- 工具: utils/ 下 3 个文件
- 通用组件: components/ 下 10 个文件
- 页面: pages/ 下 27 个文件（portal/5, data/9, compute/7, blockchain/5, ops/6, security/8 — 注：ops/security 各含额外子页面）

**验收标准**:
- 所有 27 个页面可正常访问渲染
- 登录页支持 DID/密码/SM2 三种方式 + MFA
- 门户首页仪表盘展示关键指标
- 数据服务市场搜索/筛选/脱敏预览
- 监管大屏 ECharts 全屏模式 ≤5s 刷新
- 数据源列表 + 接入配置 + 实时采集状态
- 数据资产分类分级 + 目录发布
- DAG 拖拽编排画布
- AI Agent 对话界面
- 区块链 NFT/存证/合约/结算/查询
- 用户管理 + 组织树 + 批量导入
- 安全策略/DID/密钥/威胁/国密/ZKP 页面
- 深色/浅色主题切换
- 响应式 1920×1080 + 1366×768
- WebSocket 实时通知

---

#### T04: 隐私计算与区块链实现层

| 字段 | 值 |
|------|-----|
| **任务 ID** | T04 |
| **名称** | 隐私计算与区块链实现层 |
| **优先级** | P0 |
| **复杂度** | XL |
| **依赖** | T01, T02 |

**描述**: 实现隐私计算所有后端（FATE/MP-SPDZ/SEAL/Gramine/DP/DAG 引擎/AI Agent）和区块链智能合约（6个 Solidity 合约 + 部署 + FISCO BCOS 配置），并完成与后端服务的集成。

**涉及文件** (~37 个):
- FATE: conf/2 + pipeline/3 + Dockerfile = 6
- MP-SPDZ: scripts/2 + Dockerfile + conf = 4
- SEAL: he_ckks.py + he_bfv.py + Dockerfile = 3
- Gramine: manifest + app + Dockerfile = 3
- DP: dp_engine.py + mechanisms.py = 2
- DAG: engine.py + parser.py + scheduler.py + models.py = 4
- AI Agent: base + 4 agents + 3 tools = 8
- Solidity: 6 contracts + SMVerify + deploy.ts + 6 ABI = 13
- FISCO 部署: Dockerfile + 配置目录 = 3
- 部署脚本: deploy_contracts.py + 各 Dockerfile = 5

**验收标准**:
- FATE 联邦学习训练可启动，5方 <5min
- MP-SPDZ 安全计算可执行，3方 <10s
- SEAL CKKS/BFV 加密计算可用
- Gramine TEE enclave 可启动，<3s
- 差分隐私引擎可应用，ε 可配置
- DAG 编排引擎可解析/调度/执行
- 4个 AI Agent 可交互
- 6个 Solidity 合约编译部署成功
- FISCO BCOS 4节点 PBFT 共识正常
- 区块链查询 <200ms
- 全流程 8 节点存证

---

#### T05: 集成测试与部署验证

| 字段 | 值 |
|------|-----|
| **任务 ID** | T05 |
| **名称** | 集成测试与部署验证 |
| **优先级** | P0 |
| **复杂度** | L |
| **依赖** | T02, T03, T04 |

**描述**: 端到端集成测试、部署脚本、监控配置、性能验证、数据初始化，确保整个系统可一键部署并通过所有 P0 验收标准。

**涉及文件** (~15 个):
- 脚本: init_db.py, seed_data.py, health_check.py, deploy_contracts.py
- 监控: prometheus/prometheus.yml, rules/alerts.yml, grafana/dashboards/3个, grafana/datasources/prometheus.yml
- 配置: emqx/emqx.conf, docker Dockerfile 补充
- 根: .env.example, Makefile, docker-compose.yml 完善

**验收标准**:
- `docker compose up` 一键启动全部 ~20 个容器
- Prometheus + Grafana 监控面板正常
- EMQX MQTT 消息收发正常
- 端到端数据流通测试通过
- 区块链全流程存证测试通过
- 性能指标达标：API P99<500ms, 页面首屏<2s, TPS≥1000
- 数据种子脚本可初始化完整测试数据
- 健康检查脚本通过

### 8.2 任务依赖图

```mermaid
graph TD
    T01[T01: 项目基础设施与配置<br/>XL | 2天] --> T02[T02: 后端核心服务层<br/>XL | 5天]
    T01 --> T03[T03: 前端核心应用层<br/>XL | 5天]
    T02 --> T04[T04: 隐私计算与区块链实现层<br/>XL | 4天]
    T02 --> T05[T05: 集成测试与部署验证<br/>L | 2天]
    T03 --> T05
    T04 --> T05
```

### 8.3 并行/串行执行策略

```
阶段 1 (串行):  T01 — 基础设施搭建 [2天]
               ↓
阶段 2 (并行):  T02 — 后端核心服务 [5天]  |  T03 — 前端核心应用 [5天]
               ↓                               ↓
阶段 3 (串行):  T04 — 隐私计算与区块链 [4天]（依赖后端 API）
               ↓
阶段 4 (串行):  T05 — 集成测试与部署 [2天]
```

**关键路径**: T01 → T02 → T04 → T05（总计 13天）

---

## 9. 共享知识

### 9.1 跨模块约定

| 约定 | 说明 |
|------|------|
| **API 响应格式** | `{code: int, message: str, data: any, timestamp: ISO8601}` |
| **分页参数** | `page` (1-based), `page_size` (默认20, 最大100), `sort_by`, `sort_order` |
| **分页响应** | `{items: [], total: int, page: int, page_size: int, total_pages: int}` |
| **认证头** | `Authorization: Bearer {access_token}` |
| **错误码范围** | 0=成功, 1xxx=认证, 2xxx=数据, 3xxx=计算, 4xxx=区块链, 5xxx=运营, 6xxx=安全, 9xxx=系统 |
| **日期格式** | ISO 8601 UTC（`2026-05-18T12:00:00Z`） |
| **ID 类型** | UUID v4 |
| **密码哈希** | SM3（国密），非 bcrypt |
| **传输加密** | TLS 1.3 + SM 国密通道 |
| **存证哈希** | SM3 |
| **签名算法** | SM2（国密），非 RSA/ECDSA |
| **DID 方法** | `did:fisco:{address}` |
| **日志保留** | 审计日志 ≥ 6个月 |
| **命名规范** | 文件: snake_case, 组件: PascalCase, API路径: kebab-case, 变量: camelCase |
| **数据库表名** | snake_case 复数 |
| **Redis 键** | `module:entity:identifier` 格式 |
| **前端状态** | Zustand store 命名 `use{Module}Store` |
| **组件样式** | TailwindCSS 原子类 + MUI sx prop，禁止内联 style |
| **分类分级** | 6大类 × 4级别 = 24种组合 |
| **MQTT 主题** | `energy/{type}/{device_did}/{subtype}` |
| **NFT 标准** | ERC-721 类似，自定义 DataAssetNFT |
| **8节点存证** | collect → preprocess → classify → publish → apply → compute → result → settle |

### 9.2 环境变量清单

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://energy:pass@localhost:5432/energy_ds` |
| `REDIS_URL` | Redis 连接串 | `redis://:pass@localhost:6379/0` |
| `MONGO_URL` | MongoDB 连接串 | `mongodb://energy:pass@localhost:27017` |
| `MINIO_ENDPOINT` | MinIO 端点 | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO AK | - |
| `MINIO_SECRET_KEY` | MinIO SK | - |
| `EMQX_HOST` | EMQX 地址 | `localhost` |
| `EMQX_PORT` | EMQX 端口 | `1883` |
| `FISCO_CHANNEL` | FISCO 节点地址 | `localhost:20200` |
| `FISCO_CHANNEL_CA` | FISCO CA 证书路径 | - |
| `FISCO_SSL_CERT` | FISCO SSL 证书 | - |
| `FISCO_SSL_KEY` | FISCO SSL 私钥 | - |
| `FATE_FLOW_URL` | FATE Flow API | `http://localhost:9380` |
| `DEEPSEEK_API_KEY` | DeepSeek-V3 API Key | - |
| `DEEPSEEK_BASE_URL` | DeepSeek-V3 API URL | - |
| `SECRET_KEY` | 应用密钥 | - |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `JWT_EXPIRE_MINUTES` | JWT 过期时间 | `30` |
| `SESSION_EXPIRE_MINUTES` | Session 过期 | `30` |
| `LOGIN_FAIL_LOCKOUT` | 登录失败锁定次数 | `5` |
| `LOCKOUT_DURATION_MINUTES` | 锁定时长 | `15` |
| `GMSSL_LIB_PATH` | GmSSL 动态库路径 | `/usr/local/lib/libgmssl.so` |
| `CORS_ORIGINS` | CORS 允许源 | `http://localhost` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `PROMETHEUS_PORT` | Prometheus 端口 | `9090` |
| `GRAFANA_PORT` | Grafana 端口 | `3000` |

---

## 10. 待明确事项

| # | 事项 | 影响范围 | 建议处理方式 |
|---|------|----------|------------|
| 1 | DeepSeek-V3 本地部署 GPU 是否可用 | P0-COMP-11 | 优先 API 调用，降低部署复杂度；若 GPU 可用则本地部署 |
| 2 | Intel SGX 硬件是否可用 | P0-COMP-03 | 若不可用，使用 Gramine 模拟模式 |
| 3 | HSM 硬件是否可用 | P0-SEC-03 | 使用 SoftHSM v2 软件替代 |
| 4 | FISCO BCOS 4节点是否同服务器 | P0-CHAIN-04 | 建议同服务器 Docker 隔离，降低延迟 |
| 5 | 气象/市场价格 API 端点 | P0-DATA-01 | 实现通用 HTTP/WebSocket 适配器，待确认后配置 |
| 6 | ZKP Python 库成熟度 | P0-SEC-06 | 使用 py_SNARK / petlib / python-bulletproofs |
| 7 | FATE 2.x 与 Python 3.12 兼容性 | P0-COMP-01 | FATE 容器内独立 Python 环境 |
| 8 | DLMS/COSEM 协议栈 Python 实现 | P0-DATA-01 | 使用 dlms-cosem Python 库 |
| 9 | MP-SPDZ 实际部署资源需求 | P0-COMP-02 | 初始 3 方各 4GB 内存，按需扩展 |
| 10 | 前端 DAG 拖拽画布实现方案 | P0-COMP-07 | 推荐使用 React Flow 库 |

---

## 附录 A: P0 需求与任务映射

| 需求 ID | 需求名称 | T01 | T02 | T03 | T04 | T05 |
|---------|----------|-----|-----|-----|-----|-----|
| P0-PORTAL-01 | DID身份认证+MFA | ○ | ● | ● | | |
| P0-PORTAL-02 | RBAC+ABAC权限路由 | ○ | ● | ● | | |
| P0-PORTAL-03 | 数据服务市场 | | ● | ● | | |
| P0-PORTAL-04 | 服务申请管理 | | ● | ● | | |
| P0-PORTAL-05 | 监管大屏 | | ● | ● | | |
| P0-PORTAL-06 | 安全防护 | ○ | ● | ● | | |
| P0-PORTAL-07 | 技术基线 | ● | ○ | ○ | | |
| P0-DATA-01 | 多源数据接入 | | ● | ● | | |
| P0-DATA-02 | 边缘预处理 | | ● | ○ | | |
| P0-DATA-03 | 实时采集 | | ● | ○ | | |
| P0-DATA-04 | 断线续传 | | ● | | | |
| P0-DATA-05 | MQTT主题体系 | | ● | | | |
| P0-DATA-06 | 数据分类分级 | | ● | ● | | |
| P0-DATA-07 | 三维标签体系 | | ● | ● | | |
| P0-DATA-08 | 元数据管理 | | ● | ● | | |
| P0-DATA-09 | 数据目录发布 | | ● | ● | | |
| P0-DATA-10 | 数据质量 | | ● | ● | | |
| P0-DATA-11 | 数据模型 | | ● | | | |
| P0-COMP-01 | 联邦学习FL | | | | ● | |
| P0-COMP-02 | 安全多方计算MPC | | | | ● | |
| P0-COMP-03 | TEE可信执行环境 | | | | ● | |
| P0-COMP-04 | 同态加密HE | | | | ● | |
| P0-COMP-05 | 差分隐私DP | | | | ● | |
| P0-COMP-06 | 业务场景路由 | | ● | | ● | |
| P0-COMP-07 | 计算任务管理 | | ● | ● | ● | |
| P0-COMP-08 | 数据沙箱 | | ● | ● | | |
| P0-COMP-09 | 性能基准 | | | | ● | ● |
| P0-COMP-10 | FATE部署 | | | | ● | |
| P0-COMP-11 | AI Agent | | | | ● | |
| P0-CHAIN-01 | 数据资产确权 | | ● | ● | ● | |
| P0-CHAIN-02 | 全流程存证 | | ● | ● | ● | |
| P0-CHAIN-03 | 智能合约结算 | | ● | ● | ● | |
| P0-CHAIN-04 | FISCO BCOS部署 | ○ | | | ● | |
| P0-CHAIN-05 | 6个智能合约 | | | | ● | |
| P0-CHAIN-06 | 查询性能 | | | | ● | ● |
| P0-OPS-01 | 用户与组织管理 | | ● | ● | | |
| P0-OPS-02 | 服务目录与计费 | | ● | ● | | |
| P0-OPS-03 | 运营监控 | | ● | ● | | ● |
| P0-OPS-04 | 合规管理 | | ● | ● | | |
| P0-OPS-05 | KPI | | ● | ● | | ● |
| P0-SEC-01 | RBAC+ABAC混合 | | ● | ● | | |
| P0-SEC-02 | 数字身份 | | ● | ● | ● | |
| P0-SEC-03 | 密钥管理 | | ● | ● | | |
| P0-SEC-04 | 威胁检测 | | ● | ● | | |
| P0-SEC-05 | 国密算法 | | ● | ○ | ● | |
| P0-SEC-06 | 零知识证明 | | ● | ○ | ● | |
| P0-SEC-07 | 安全等级 | | ● | ● | | |

**图例**: ●=主要实现, ○=部分实现/配置

---

## 附录 B: API 端点统计

| 模块 | 端点数 | WebSocket | MQTT |
|------|--------|-----------|------|
| 认证 | 5 | - | - |
| 数据资源 | 27 | - | 4 |
| 可信计算 | 22 | 1 | - |
| 区块链 | 14 | - | - |
| 运营管理 | 22 | - | - |
| 安全管控 | 25 | 1 | - |
| **总计** | **115** | **2** | **4** |

---

## 附录 C: 数据库表统计

| 存储 | 数量 | 说明 |
|------|------|------|
| PostgreSQL 表 | 22 | 主业务数据 |
| Redis 键模式 | 15 | 缓存/会话/实时状态 |
| MongoDB 集合 | 3 | 遥测/计算结果/对话 |
| **总计** | **40** | |
