# 后端 API 结构探索报告

> 生成时间: 2026-05-21 | 项目: 能源可信数据空间 (Energy Trusted Data Space)

---

## 1. 总览

| 维度 | 数量 |
|------|------|
| API 路由文件 | 90 个 (88 router + 2 endpoint) |
| API 端点总数 | **786 个** |
| 路由代码行数 | ~18,018 行 |
| 数据库模型文件 | 42 个 |
| 服务层文件 | 100+ 个 |
| Schema 文件 | 49 个 |
| Alembic 迁移 | 10 个 (0001-0010) |

**基础路径**: `/api/v1` (所有端点均挂载在此前缀下)

**统一响应格式**:
```json
{"code": 0, "message": "success", "data": {...}}
```

---

## 2. 模块分布 (13 大域)

### 2.1 认证域 — `/api/v1/auth` (3 文件, 26 端点)

| 文件 | 端点数 | 关键端点 |
|------|--------|----------|
| `auth.py` | 10 | `POST /login`, `/login/did`, `/login/certificate`, `/mfa/verify`, `/logout`, `/refresh`, `/change-password`, `/unlock`; `GET /session`, `/lockout-status/{user_id}` |
| `auth_mfa.py` | 6 | `POST /mfa/setup`, `/mfa/enable`, `/mfa/disable`, `/mfa/backup-codes/verify`, `/mfa/backup-codes/regenerate`; `GET /mfa/status/{user_id}` |
| `auth_sso.py` | 10 | `GET /sso/providers`, `/sso/providers/{id}`, `/sso/userinfo`, `/sso/sessions`; `POST /sso/providers`, `/sso/authorize`, `/sso/token`, `/sso/saml/assertion`; `DELETE /sso/providers/{id}`, `/sso/sessions/{id}` |

### 2.2 统一门户 — `/api/v1/portal` (1 文件, 10 端点)

| 关键端点 | 方法 |
|----------|------|
| `/dashboard` | GET |
| `/quick-links` | GET/POST/DELETE |
| `/overview` | GET |
| `/notifications` | GET |
| `/notifications/{id}/read` | PUT |
| `/layout` | GET/PUT |
| `/activities` | GET |

### 2.3 数据资源域 — `/api/v1/data/*` (8 文件, ~73 端点)

| 文件 | 前缀 | 端点数 | 关键能力 |
|------|------|--------|----------|
| `data_source.py` | `/data/sources` | 12 | CRUD + 启停控制 + 协议管理 |
| `data_asset.py` | `/data/assets` | 12 | CRUD + 分类/发布/预处理/预览/评分/原创证明 |
| `data_catalog.py` | `/data/catalog` | 6 | 浏览/搜索/预览/申请/反馈 |
| `metadata.py` | `/data/metadata` | 6 | CRUD + 血缘/版本 |
| `tags.py` | `/data/tags` | 11 | CRUD + 批量分配 + 搜索/统计 |
| `quality.py` | `/data/quality` | 5 | 质量报告/检测/统计 |
| `data_market.py` | `/data/market` | 4 | 资产浏览/分类/统计 |
| `data_application.py` | `/data/applications` | 6 | 服务申请/审批 |
| `data_enhanced.py` | `/data` | 31 | 分类/质量/血缘/预览/评估/版本/预处理/离线消息 |

### 2.4 可信计算域 — `/api/v1/compute/*` (12 文件, ~116 端点)

| 文件 | 前缀 | 端点数 | 关键能力 |
|------|------|--------|----------|
| `compute_task.py` | `/compute/tasks` | 10 | 任务 CRUD + 生命周期 |
| `compute_dag.py` | `/compute/dag` | 5 | DAG 编排 + 执行 |
| `compute_fl.py` | `/compute/fl` | 20 | 联邦学习 + FATE 集成 |
| `compute_mpc.py` | `/compute/mpc` | 11 | 安全多方计算 + 会话管理 |
| `compute_tee.py` | `/compute/tee` | 6 | TEE 实例 + 远程证明 |
| `compute_he.py` | `/compute/he` | 9 | 同态加密 + 密文分析 |
| `compute_dp.py` | `/compute/dp` | 2 | 差分隐私应用 |
| `compute_sandbox.py` | `/compute/sandbox` | 6 | 沙箱创建/执行/销毁 |
| `compute_agent.py` | `/compute/agents` | 9 | AI Agent (查询/交易/安全/分发) + 流式 |
| `compute_cluster.py` | `/compute/cluster` | 8 | 集群节点管理 + 任务调度 |
| `compute_enhanced.py` | `/compute/enhanced` | 20 | FATE 任务 + 沙箱 + DAG 验证 |
| `compute_benchmark.py` | `/compute/benchmarks` | 6 | 性能基准 + 趋势 + 报告 |
| `compute_quota.py` | `/compute/quota` | 14 | 组织/用户配额管理 |
| `agent_manage.py` | `/agents` | 14 | Agent 配置 + 知识库管理 |

### 2.5 区块链域 — `/api/v1/blockchain/*` (4 文件, ~38 端点)

| 文件 | 前缀 | 端点数 | 关键能力 |
|------|------|--------|----------|
| `blockchain_nft.py` | `/blockchain/nft` | 8 | NFT 铸造/授权/转移 |
| `blockchain_evidence.py` | `/blockchain/evidence` | 10 | 存证提交/验证/溯源/链查询 |
| `blockchain_contract.py` | `/blockchain/contracts` | 13 | 合约部署/调用/FISCO 状态 |
| `blockchain_settle.py` | `/blockchain/settlement` | 7 | 结算/对账/报告/争议 |
| `cross_chain.py` | `/blockchain/bridge` | 6 | 跨链转账/验证/同步 |

### 2.6 运营管理域 — `/api/v1/ops/*` (14 文件, ~103 端点)

| 文件 | 前缀 | 端点数 | 关键能力 |
|------|------|--------|----------|
| `ops_user.py` | `/ops/users` | 7 | 用户 CRUD + 导入 + 密码重置 |
| `ops_org.py` | `/ops/organizations` | 5 | 组织 CRUD + 树形 |
| `ops_service.py` | `/ops/services` | 7 | 服务 CRUD + 订阅管理 |
| `ops_billing.py` | `/ops/billing` | 8 | 计费记录/账单/统计/月报 |
| `ops_monitor.py` | `/ops/monitoring` | 4 | 指标/告警/健康 |
| `ops_monitoring.py` | `/ops/monitoring-enhanced` | 8 | 系统/应用指标 + Prometheus |
| `ops_alerts.py` | `/ops/alerts` | 17 | 告警 CRUD + 规则 + 静默/抑制规则 |
| `ops_sla.py` | `/ops/sla` | 11 | SLA 配置/指标/报告/仪表盘/告警 |
| `ops_compliance.py` | `/ops/compliance` | 6 | 合规报告/清单/导出 |
| `ops_kpi.py` | `/ops/kpi` | 3 | KPI 仪表盘/SLA/性能 |
| `ops_quota.py` | `/ops/quotas` | 11 | 配额 CRUD + 消耗/释放/告警 |
| `ops_gdpr.py` | `/ops/gdpr` | 9 | GDPR 同意/请求/记录管理 |
| `ops_import.py` | `/ops/import` | 2 | 批量导入 (Excel/JSON) |
| `ops_health.py` | `/ops/health` | 9 | 健康检查/历史/自愈/依赖 |
| `ops_audit_external.py` | `/ops/audit-external` | 13 | 第三方审计只读接口 |

### 2.7 安全管控域 — `/api/v1/security/*` (12 文件, ~105 端点)

| 文件 | 前缀 | 端点数 | 关键能力 |
|------|------|--------|----------|
| `abac.py` | `/security/abac` | 12 | 属性管理 + 策略 CRUD + 评估/模拟 |
| `security_policy.py` | `/security/policies` | 6 | 安全策略 CRUD + 评估 |
| `security_did.py` | `/security/did` | 4 | DID 创建/查询/更新/停用 |
| `security_vc.py` | `/security/vc` | 4 | 可验证凭证 签发/验证/撤销 |
| `security_key.py` | `/security/keys` | 7 | 密钥管理 + Shamir 分割 |
| `security_threat.py` | `/security/threats` | 5 | 威胁检测/仪表盘/解决 |
| `security_gmssl.py` | `/security/gmssl` | 10 | SM2/SM3/SM4/SM9/ZUC 国密算法 |
| `security_zkp.py` | `/security/zkp` | 7 | Groth16/BBS+/Bulletproofs |
| `security_enhanced.py` | `/security` | 19 | SM2/SM3/SM4 + ZKP + VC + 密钥管理 |
| `security_audit.py` | `/security/audit` | 11 | 审计日志/报告/哈希链/合规/态势 |
| `security_hsm.py` | `/security/hsm` | 15 | HSM 密钥/签名/加密/派生/分割 |
| `security_level.py` | `/security/levels` | 6 | 安全等级/分类/自动定级/策略 |
| `security_apt.py` | `/security/apt` | 5 | APT 事件/扫描/规则/IOC |
| `security_bbs.py` | `/security/bbs` | 6 | BBS+ 签名/验证/选择性披露 |

### 2.8 LLM 大模型 — `/api/v1/llm` (1 文件, 4 端点)

`GET /models`, `POST /chat`, `POST /report/generate`, `GET /history`

### 2.9 MQTT 数据采集 — `/api/v1/mqtt` (2 文件, 23 端点)

| 文件 | 前缀 | 端点数 |
|------|------|--------|
| `mqtt_collect.py` | `/mqtt` | 10 (模拟器/设备/统计/告警) |
| `mqtt_stream.py` | `/mqtt/stream` | 13 (实时数据流) |

### 2.10 系统管理 (3 文件, 23 端点)

| 文件 | 前缀 | 端点数 |
|------|------|--------|
| `notification.py` | `/notifications` | 10 (通知 CRUD + 已读/批量) |
| `system_config.py` | `/system/config` | 6 (配置分类/更新/重置/导出) |
| `audit_log.py` | `/audit-logs` | 7 (日志列表/统计/导出) |

### 2.11 可信数据空间核心业务 (6 文件, ~60 端点)

| 文件 | 前缀 | 端点数 | 关键能力 |
|------|------|--------|----------|
| `registration.py` | `/registration` | 10 | 邀请码 + 认证审核 + 入驻申请 |
| `connector.py` | `/connectors` | 15 | 连接器 CRUD + 测试/注册/同步 |
| `catalog_registration.py` | `/catalog-registrations` | 15 | 目录注册 + 管控模板 + 访问规则 |
| `subscription.py` | `/subscriptions` | 10 | 订阅 CRUD + 审核/交付/下载 |
| `product.py` | `/products` | 25 | 项目/产品/验收/上下架/订阅/交付 |
| `demand.py` | `/demands` | 10 | 需求 CRUD + 发布/关闭/认领 |

### 2.12 新增业务模块 (11 文件, ~95 端点)

| 文件 | 前缀 | 端点数 | 对应需求 |
|------|------|--------|----------|
| `org_management.py` | `/organizations` | 8 | R001-R005: 自定义角色 + 用户角色分配 |
| `connector_manage.py` | `/connector-manage` | 8 | R006-R011: 连接器注册/审核/测试 |
| `catalog_manage.py` | `/catalog-manage` | 11 | R012-R015: 目录 CRUD + 供给通道 + 管控协议 |
| `data_subscription.py` | `/data-subscriptions` | 8 | R016-R019: 资源搜索/浏览/订阅/交付 |
| `product_manage.py` | `/product-manage` | 11 | R020-R027: 产品项目 + 数据源 + 计算引擎 |
| `product_publish_v2.py` | `/product-publish` | 7 | R028-R032: 上下架 + 管控协议 + 合规文档 |
| `product_market.py` | `/product-market` | 8 | R033-R036: 搜索/推荐/订阅/合约/交付 |
| `demand_manage.py` | `/demand-manage` | 10 | R037-R041: 需求 + 风险评估 + 认领 + 干预 |
| `contract_manage.py` | `/contracts` | 10 | R042-R045: 合约 CRUD + 签署/定价/修订/终止 |
| `connector_file_manage.py` | `/connector-files` | 10 | R046-R048: 文件上传/下载 + 文件集 + API 代理 |
| `workflow_manage.py` | `/workflows` | 5 | 审批工作流: 列表/待审/详情/批准/驳回 |

### 2.13 WebSocket — `/api/v1/ws` (1 文件, 5 端点)

`websocket.py` — 实时通信端点

---

## 3. 数据库模型 (42 个文件)

### 核心模型分组

| 分组 | 模型文件 | 表数 |
|------|----------|------|
| **用户/认证** | `user.py`, `mfa_model.py`, `sso_model.py` | 5+ |
| **数据资源** | `data_asset.py`, `data_version_model.py`, `tag.py` | 4+ |
| **可信计算** | `compute_task.py`, `fl_model.py`, `mpc_session.py`, `tee_instance.py`, `he_key.py`, `fate_job.py`, `cluster_model.py`, `sandbox_model.py`, `quota.py`, `quota_model.py` | 10+ |
| **区块链** | `blockchain.py` | 3+ |
| **安全** | `security.py`, `vc_model.py`, `zkp_model.py` | 5+ |
| **运营** | `portal_model.py`, `monitor_alert.py`, `compliance.py`, `gdpr.py`, `sla_model.py`, `service.py`, `access_log.py`, `audit_log.py` | 10+ |
| **MQTT** | `mqtt_data_model.py` | 2+ |
| **可信数据空间** | `invite_code.py`, `certification.py`, `connector.py`, `catalog.py`, `subscription.py`, `product.py`, `demand.py`, `contract.py`, `connector_file.py`, `workflow.py` | 15+ |

### 基类模式

```python
class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## 4. 服务层 (100+ 文件)

服务层按功能域组织，主要服务包括:

| 域 | 服务文件 | 总代码量 |
|----|----------|----------|
| 认证 | `auth_service.py`, `mfa_service.py`, `sso_service.py` | ~54KB |
| 数据 | `data_asset_service.py`, `data_source_service.py`, `classify_service.py`, `data_quality.py`, `data_lineage.py`, `data_version_service.py`, `tag_service.py`, `catalog_service.py` 等 | ~130KB |
| 计算 | `compute_service.py`, `compute_sandbox.py`, `fl_service.py`, `mpc_service.py`, `tee_service.py`, `he_service.py`, `dp_service.py`, `dag_engine.py`, `fate_integration.py` 等 | ~300KB |
| 区块链 | `blockchain_evidence_service.py`, `blockchain_nft_service.py`, `blockchain_contract_service.py`, `blockchain_settle_service.py`, `cross_chain_service.py` | ~100KB |
| 安全 | `abac_service.py`, `did_service.py`, `vc_service.py`, `key_service.py`, `threat_service.py`, `gmssl_service.py`, `hsm_service.py`, `bbs_plus_service.py`, `zkp_service.py` 等 | ~230KB |
| 运营 | `user_service.py`, `org_service.py`, `billing_service.py`, `sla_service.py`, `compliance_service.py`, `gdpr_service.py`, `quota_service.py`, `health_service.py` 等 | ~160KB |
| 可信数据空间 | `registration_service.py`, `connector_service.py`, `catalog_registration_service.py`, `subscription_service.py`, `product_service.py`, `demand_service.py`, `contract_service.py`, `workflow_service.py` 等 | ~120KB |

---

## 5. Alembic 迁移历史

| 迁移编号 | 文件名 | 大小 | 说明 |
|----------|--------|------|------|
| 0001 | `0001_init.py` | 27KB | 初始数据库创建 |
| 0002 | `0002_add_mfa_fields.py` | 1.5KB | MFA 字段扩展 |
| 0003 | `0003_add_data_quality.py` | 4KB | 数据质量表 |
| 0004 | `0004_add_blockchain_settlement.py` | 6KB | 区块链结算表 |
| 0005 | `0005_add_security_enhanced.py` | 8KB | 安全增强表 |
| 0006 | `0006_add_notification_fields.py` | 2KB | 通知字段扩展 |
| 0006 | `0006_add_ops_enhanced.py` | 7.4KB | 运营增强表 |
| 0007 | `0007_add_mfa_sso_mqtt_tables.py` | 10KB | MFA/SSO/MQTT 表 |
| 0008 | `0008_add_privacy_compute_ops_security_tables.py` | 36KB | 隐私计算/运营/安全表 |
| 0009 | `0009_add_quota_gdpr_tables.py` | 6KB | 配额/GDPR 表 |
| **0010** | `0010_add_registration_connector_catalog_subscription_product_demand.py` | **34KB** | **可信数据空间核心表 (最新)** |

---

## 6. API 前缀完整映射

```
/api/v1/
├── /auth/                    (认证, MFA, SSO)
├── /portal/                  (统一门户)
├── /data/
│   ├── /sources              (数据源)
│   ├── /assets               (数据资产)
│   ├── /catalog              (数据目录)
│   ├── /metadata             (元数据)
│   ├── /tags                 (标签)
│   ├── /quality              (数据质量)
│   ├── /market               (数据市场)
│   ├── /applications         (服务申请)
│   ├── /classify|quality|lineage|preview|evaluate|versions|preprocess|offline  (数据增强)
├── /compute/
│   ├── /tasks                (计算任务)
│   ├── /dag                  (DAG编排)
│   ├── /fl                   (联邦学习)
│   ├── /mpc                  (安全多方计算)
│   ├── /tee                  (TEE)
│   ├── /he                   (同态加密)
│   ├── /dp                   (差分隐私)
│   ├── /sandbox              (数据沙箱)
│   ├── /agents               (AI Agent)
│   ├── /cluster              (计算集群)
│   ├── /enhanced             (计算增强)
│   ├── /benchmarks           (性能基准)
│   ├── /quota                (计算配额)
├── /agents/                  (Agent管理)
├── /blockchain/
│   ├── /nft                  (NFT确权)
│   ├── /evidence             (存证)
│   ├── /contracts            (智能合约)
│   ├── /settlement           (链上结算)
│   ├── /bridge               (跨链互操作)
├── /ops/
│   ├── /users                (用户管理)
│   ├── /organizations        (组织管理)
│   ├── /services             (服务管理)
│   ├── /billing              (计费管理)
│   ├── /monitoring           (运营监控)
│   ├── /monitoring-enhanced  (监控增强)
│   ├── /alerts               (告警管理)
│   ├── /sla                  (SLA管理)
│   ├── /compliance           (合规管理)
│   ├── /kpi                  (KPI仪表盘)
│   ├── /quotas               (配额管理)
│   ├── /gdpr                 (GDPR合规)
│   ├── /import               (批量导入)
│   ├── /health               (健康检查)
│   ├── /audit-external       (第三方审计)
├── /security/
│   ├── /abac                 (ABAC策略)
│   ├── /policies             (安全策略)
│   ├── /did                  (DID身份)
│   ├── /vc                   (可验证凭证)
│   ├── /keys                 (密钥管理)
│   ├── /threats              (威胁检测)
│   ├── /gmssl                (国密算法)
│   ├── /zkp                  (零知识证明)
│   ├── /sm2|sm3|sm4|zkp|vc|keys  (安全增强)
│   ├── /audit                (增强审计)
│   ├── /hsm                  (HSM硬件安全)
│   ├── /levels               (安全等级)
│   ├── /apt                  (APT检测)
│   ├── /bbs                  (BBS+签名)
├── /llm/                     (LLM大模型)
├── /mqtt/                    (MQTT采集)
│   ├── /stream               (MQTT数据流)
├── /notifications/           (通知公告)
├── /system/config/           (系统配置)
├── /audit-logs/              (操作日志)
├── /registration/            (注册认证)
├── /connectors/              (连接器管理)
├── /catalog-registrations/   (数据目录注册)
├── /subscriptions/           (数据资源订阅)
├── /products/                (数据产品)
├── /demands/                 (需求管理)
├── /organizations/           (机构管理 - 新增)
├── /connector-manage/        (连接器管理 - 新增)
├── /catalog-manage/          (数据目录管理 - 新增)
├── /data-subscriptions/      (数据订阅 - 新增)
├── /product-manage/          (数据产品管理 - 新增)
├── /product-publish/         (产品上架 - 新增)
├── /product-market/          (产品市场 - 新增)
├── /demand-manage/           (需求管理 - 新增)
├── /contracts/               (合约管理 - 新增)
├── /connector-files/         (连接器文件库 - 新增)
├── /workflows/               (审批工作流 - 新增)
├── /ws/                      (WebSocket)
```

---

## 7. 技术模式总结

### 7.1 依赖注入模式
```python
from app.database import get_db
from app.utils.deps import get_current_user

@router.get("/")
async def list_items(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    ...
```

### 7.2 服务层模式
```python
class SomeService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: Schema) -> Model:
        obj = Model(**data.model_dump())
        self.db.add(obj)
        await self.db.commit()
        return obj
```

### 7.3 分页模式
```python
@router.get("/", response_model=ApiResponse[PaginatedResponse[SomeResponse]])
async def list_items(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    ...
```

### 7.4 认证方式
- **JWT Token**: 主要认证方式 (Bearer Token)
- **DID 登录**: 去中心化身份认证
- **证书登录**: X.509 证书认证
- **MFA**: TOTP 多因素认证
- **SSO**: OAuth2/SAML 单点登录

---

## 8. 关键发现

### 8.1 代码规模
- 后端总代码量: **~2MB+** (仅 Python 源码)
- 最大服务文件: `fate_integration.py` (58KB), `abac_service.py` (38KB), `compute_service.py` (40KB)
- 最大模型文件: `sandbox_model.py` (15KB), `product.py` (12KB)

### 8.2 模块成熟度
| 成熟度 | 模块 |
|--------|------|
| **高** (有完整服务层+测试) | 认证、数据资产、计算任务、区块链、安全 |
| **中** (路由+服务已实现) | 运营管理、门户、MQTT、LLM |
| **低** (仅有路由壳+基础 CRUD) | 可信数据空间核心 (R001-R048 新增模块) |

### 8.3 双轨路由问题
部分业务存在新旧两套路由:
- `catalog_registration.py` (旧) vs `catalog_manage.py` (新)
- `subscription.py` (旧) vs `data_subscription.py` (新)
- `product.py` (旧) vs `product_manage.py` + `product_publish_v2.py` (新)
- `demand.py` (旧) vs `demand_manage.py` (新)

**建议**: 统一到新路由，旧路由标记为 deprecated。

---

*报告完毕。总计 786 个 API 端点覆盖 13 大业务域，支撑能源可信数据空间的全量功能。*
