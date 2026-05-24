# 能源可信数据空间 - API 文档

## 概述

能源可信数据空间系统提供 RESTful API 接口，支持"一门户五中心"的全部功能。

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **内容类型**: `application/json`
- **字符编码**: UTF-8

## 通用响应格式

### 成功响应
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误响应
```json
{
  "code": 1000,
  "message": "错误描述",
  "data": null
}
```

### 分页响应
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

## 错误码

| 错误码 | 描述 |
|--------|------|
| 0 | 成功 |
| 1000 | 通用错误 |
| 1001 | 参数错误 |
| 1002 | 未授权 |
| 1003 | 禁止访问 |
| 1004 | 资源未找到 |
| 2001 | 数据资产未找到 |
| 3001 | 计算任务错误 |
| 4001 | 区块链错误 |
| 5001 | 安全策略错误 |

---

## 1. 认证模块 `/api/v1/auth`

### 1.1 密码登录
```http
POST /api/v1/auth/login
```

**请求体**:
```json
{
  "auth_type": "password",
  "username": "admin",
  "password": "password123"
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "uuid",
      "username": "admin",
      "role": "admin"
    }
  }
}
```

### 1.2 DID 签名登录
```http
POST /api/v1/auth/login/did
```

**请求体**:
```json
{
  "did": "did:ethr:0x...",
  "signature": "0x...",
  "challenge": "random_challenge_string"
}
```

### 1.3 SM2 证书登录
```http
POST /api/v1/auth/login/certificate
```

**请求体**:
```json
{
  "certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
  "signature": "hex_encoded_signature",
  "challenge": "random_challenge_string"
}
```

### 1.4 MFA 验证
```http
POST /api/v1/auth/mfa/verify
```

**请求体**:
```json
{
  "session_id": "mfa_session_uuid",
  "code": "123456"
}
```

### 1.5 刷新 Token
```http
POST /api/v1/auth/refresh
```

**请求体**:
```json
{
  "refresh_token": "eyJ..."
}
```

### 1.6 登出
```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}
```

### 1.7 获取当前会话
```http
GET /api/v1/auth/session
Authorization: Bearer {access_token}
```

### 1.8 修改密码
```http
POST /api/v1/auth/change-password
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "old_password": "old_password",
  "new_password": "new_password"
}
```

---

## 2. 数据资源中心 `/api/v1/data`

### 2.1 数据源管理 `/api/v1/data/sources`

#### 列出数据源
```http
GET /api/v1/data/sources?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 创建数据源
```http
POST /api/v1/data/sources
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "name": "电力数据源",
  "type": "postgresql",
  "connection_string": "postgresql://user:pass@host:5432/db",
  "description": "电力系统运行数据"
}
```

#### 获取数据源详情
```http
GET /api/v1/data/sources/{source_id}
Authorization: Bearer {access_token}
```

#### 更新数据源
```http
PUT /api/v1/data/sources/{source_id}
Authorization: Bearer {access_token}
```

#### 删除数据源
```http
DELETE /api/v1/data/sources/{source_id}
Authorization: Bearer {access_token}
```

#### 测试数据源连接
```http
POST /api/v1/data/sources/{source_id}/test
Authorization: Bearer {access_token}
```

### 2.2 数据资产 `/api/v1/data/assets`

#### 列出数据资产
```http
GET /api/v1/data/assets?page=1&page_size=20&category=发电&status=published
Authorization: Bearer {access_token}
```

#### 创建数据资产
```http
POST /api/v1/data/assets
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "name": "发电量数据",
  "source_id": "uuid",
  "category": "发电",
  "classification_level": 2,
  "description": "各电厂发电量统计数据",
  "schema_def": {
    "fields": [
      {"name": "plant_id", "type": "string"},
      {"name": "output_mwh", "type": "float"},
      {"name": "timestamp", "type": "datetime"}
    ]
  },
  "storage_format": "parquet",
  "owner_id": "uuid",
  "organization_id": "uuid"
}
```

#### 获取数据资产详情
```http
GET /api/v1/data/assets/{asset_id}
Authorization: Bearer {access_token}
```

#### 更新数据资产
```http
PUT /api/v1/data/assets/{asset_id}
Authorization: Bearer {access_token}
```

#### 删除数据资产
```http
DELETE /api/v1/data/assets/{asset_id}
Authorization: Bearer {access_token}
```

#### 执行分类分级
```http
POST /api/v1/data/assets/{asset_id}/classify
Authorization: Bearer {access_token}
```

#### 发布至目录
```http
POST /api/v1/data/assets/{asset_id}/publish
Authorization: Bearer {access_token}
```

### 2.3 数据目录 `/api/v1/data/catalog`

#### 列出目录
```http
GET /api/v1/data/catalog?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 创建目录项
```http
POST /api/v1/data/catalog
Authorization: Bearer {access_token}
```

### 2.4 元数据管理 `/api/v1/data/metadata`

#### 列出元数据
```http
GET /api/v1/data/metadata?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 创建元数据
```http
POST /api/v1/data/metadata
Authorization: Bearer {access_token}
```

### 2.5 标签管理 `/api/v1/data/tags`

#### 列出标签
```http
GET /api/v1/data/tags
Authorization: Bearer {access_token}
```

#### 创建标签
```http
POST /api/v1/data/tags
Authorization: Bearer {access_token}
```

### 2.6 数据质量 `/api/v1/data/quality`

#### 质量检查
```http
POST /api/v1/data/quality/check
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "asset_id": "uuid",
  "rules": ["completeness", "uniqueness", "consistency"]
}
```

#### 获取质量报告
```http
GET /api/v1/data/quality/{asset_id}/report
Authorization: Bearer {access_token}
```

### 2.7 数据服务市场 `/api/v1/data/market`

#### 列出服务
```http
GET /api/v1/data/market?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 发布服务
```http
POST /api/v1/data/market
Authorization: Bearer {access_token}
```

### 2.8 服务申请审批 `/api/v1/data/applications`

#### 列出申请
```http
GET /api/v1/data/applications?page=1&page_size&status=pending
Authorization: Bearer {access_token}
```

#### 提交申请
```http
POST /api/v1/data/applications
Authorization: Bearer {access_token}
```

#### 审批申请
```http
POST /api/v1/data/applications/{application_id}/approve
Authorization: Bearer {access_token}
```

### 2.9 数据增强 `/api/v1/data`

#### 边缘预处理
```http
POST /api/v1/data/preprocess
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "asset_id": "uuid",
  "operations": ["normalize", "compress", "anomaly_detect"],
  "params": {
    "compression_ratio": 0.8,
    "anomaly_threshold": 3.0
  }
}
```

#### 断线续传状态
```http
GET /api/v1/data/offline/status
Authorization: Bearer {access_token}
```

#### 版本管理
```http
GET /api/v1/data/versions/{asset_id}
Authorization: Bearer {access_token}
```

---

## 3. 可信计算中心 `/api/v1/compute`

### 3.1 计算任务 `/api/v1/compute/tasks`

#### 列出任务
```http
GET /api/v1/compute/tasks?page=1&page_size=20&status=running
Authorization: Bearer {access_token}
```

#### 创建任务
```http
POST /api/v1/compute/tasks
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "name": "发电量预测",
  "type": "federated_learning",
  "algorithm": "horizontal_fl",
  "datasets": ["asset_id_1", "asset_id_2"],
  "params": {
    "epochs": 10,
    "learning_rate": 0.01,
    "batch_size": 32
  }
}
```

#### 获取任务详情
```http
GET /api/v1/compute/tasks/{task_id}
Authorization: Bearer {access_token}
```

#### 取消任务
```http
POST /api/v1/compute/tasks/{task_id}/cancel
Authorization: Bearer {access_token}
```

#### 获取任务结果
```http
GET /api/v1/compute/tasks/{task_id}/result
Authorization: Bearer {access_token}
```

### 3.2 DAG 编排 `/api/v1/compute/dag`

#### 列出 DAG
```http
GET /api/v1/compute/dag?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 创建 DAG
```http
POST /api/v1/compute/dag
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "name": "数据处理流水线",
  "nodes": [
    {"id": "node1", "type": "data_load", "params": {"source": "asset_1"}},
    {"id": "node2", "type": "preprocess", "params": {"method": "normalize"}},
    {"id": "node3", "type": "train", "params": {"algorithm": "xgboost"}}
  ],
  "edges": [
    {"from": "node1", "to": "node2"},
    {"from": "node2", "to": "node3"}
  ]
}
```

#### 执行 DAG
```http
POST /api/v1/compute/dag/{dag_id}/execute
Authorization: Bearer {access_token}
```

### 3.3 联邦学习 `/api/v1/compute/fl`

#### 创建联邦学习任务
```http
POST /api/v1/compute/fl
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "name": "横向联邦学习",
  "algorithm": "fedavg",
  "parties": ["party_1", "party_2", "party_3"],
  "model_config": {
    "type": "neural_network",
    "layers": [64, 32, 1]
  },
  "training_config": {
    "epochs": 10,
    "learning_rate": 0.01
  }
}
```

#### 获取训练状态
```http
GET /api/v1/compute/fl/{task_id}/status
Authorization: Bearer {access_token}
```

### 3.4 安全多方计算 `/api/v1/compute/mpc`

#### 创建 MPC 任务
```http
POST /api/v1/compute/mpc
Authorization: Bearer {access_token}
```

### 3.5 TEE 可信执行 `/api/v1/compute/tee`

#### 创建 TEE 任务
```http
POST /api/v1/compute/tee
Authorization: Bearer {access_token}
```

### 3.6 同态加密 `/api/v1/compute/he`

#### 创建 HE 任务
```http
POST /api/v1/compute/he
Authorization: Bearer {access_token}
```

### 3.7 差分隐私 `/api/v1/compute/dp`

#### 创建 DP 任务
```http
POST /api/v1/compute/dp
Authorization: Bearer {access_token}
```

### 3.8 数据沙箱 `/api/v1/compute/sandbox`

#### 创建沙箱环境
```http
POST /api/v1/compute/sandbox
Authorization: Bearer {access_token}
```

### 3.9 AI Agent `/api/v1/compute/agents`

#### 与 Agent 对话
```http
POST /api/v1/compute/agents/chat
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "agent_type": "data_analyst",
  "message": "分析最近一个月的发电量趋势",
  "context": {"asset_id": "uuid"}
}
```

#### 流式对话
```http
POST /api/v1/compute/agents/chat/stream
Authorization: Bearer {access_token}
```

### 3.10 计算集群 `/api/v1/compute/cluster`

#### 列出集群节点
```http
GET /api/v1/compute/cluster/nodes
Authorization: Bearer {access_token}
```

#### 获取集群状态
```http
GET /api/v1/compute/cluster/status
Authorization: Bearer {access_token}
```

### 3.11 计算增强 `/api/v1/compute/enhanced`

#### FATE 集成
```http
POST /api/v1/compute/enhanced/fate/jobs
Authorization: Bearer {access_token}
```

#### FATE 任务状态
```http
GET /api/v1/compute/enhanced/fate/jobs/{job_id}
Authorization: Bearer {access_token}
```

### 3.12 性能基准 `/api/v1/compute/benchmarks`

#### 列出基准测试
```http
GET /api/v1/compute/benchmarks?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 运行基准测试
```http
POST /api/v1/compute/benchmarks/run
Authorization: Bearer {access_token}
```

### 3.13 Agent 管理 `/api/v1/agents`

#### 列出 Agent 配置
```http
GET /api/v1/agents
Authorization: Bearer {access_token}
```

#### 创建 Agent 配置
```http
POST /api/v1/agents
Authorization: Bearer {access_token}
```

#### 更新 Agent 配置
```http
PUT /api/v1/agents/{agent_id}
Authorization: Bearer {access_token}
```

#### 知识库管理
```http
POST /api/v1/agents/{agent_id}/knowledge
Authorization: Bearer {access_token}
```

---

## 4. 区块链存证中心 `/api/v1/blockchain`

### 4.1 NFT 确权 `/api/v1/blockchain/nft`

#### 铸造 NFT
```http
POST /api/v1/blockchain/nft/mint
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "asset_id": "uuid",
  "owner_did": "did:ethr:0x...",
  "metadata": {
    "name": "发电量数据集",
    "description": "2024年各电厂发电量统计",
    "rights": ["read", "compute"]
  }
}
```

#### 获取 NFT 详情
```http
GET /api/v1/blockchain/nft/{token_id}
Authorization: Bearer {access_token}
```

#### 转移 NFT
```http
POST /api/v1/blockchain/nft/{token_id}/transfer
Authorization: Bearer {access_token}
```

### 4.2 存证管理 `/api/v1/blockchain/evidence`

#### 创建存证
```http
POST /api/v1/blockchain/evidence
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "data_hash": "sha256_hash",
  "evidence_type": "data_asset",
  "metadata": {
    "asset_id": "uuid",
    "action": "create",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

#### 验证存证
```http
POST /api/v1/blockchain/evidence/verify
Authorization: Bearer {access_token}
```

#### 查询存证历史
```http
GET /api/v1/blockchain/evidence/history/{data_hash}
Authorization: Bearer {access_token}
```

### 4.3 智能合约 `/api/v1/blockchain/contracts`

#### 列出合约
```http
GET /api/v1/blockchain/contracts
Authorization: Bearer {access_token}
```

#### 部署合约
```http
POST /api/v1/blockchain/contracts/deploy
Authorization: Bearer {access_token}
```

#### 调用合约
```http
POST /api/v1/blockchain/contracts/{contract_id}/invoke
Authorization: Bearer {access_token}
```

### 4.4 链上结算 `/api/v1/blockchain/settlement`

#### 创建结算
```http
POST /api/v1/blockchain/settlement
Authorization: Bearer {access_token}
```

#### 查询结算记录
```http
GET /api/v1/blocktlement?page=1&page_size=20
Authorization: Bearer {access_token}
```

---

## 5. 运营管理中心 `/api/v1/ops`

### 5.1 用户管理 `/api/v1/ops/users`

#### 列出用户
```http
GET /api/v1/ops/users?page=1&page_size=20&role=admin
Authorization: Bearer {access_token}
```

#### 创建用户
```http
POST /api/v1/ops/users
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "username": "user1",
  "email": "user1@example.com",
  "password": "password123",
  "role": "data_analyst",
  "organization_id": "uuid"
}
```

#### 更新用户
```http
PUT /api/v1/ops/users/{user_id}
Authorization: Bearer {access_token}
```

#### 删除用户
```http
DELETE /api/v1/ops/users/{user_id}
Authorization: Bearer {access_token}
```

### 5.2 组织管理 `/api/v1/ops/organizations`

#### 列出组织
```http
GET /api/v1/ops/organizations?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 创建组织
```http
POST /api/v1/ops/organizations
Authorization: Bearer {access_token}
```

### 5.3 服务管理 `/api/v1/ops/services`

#### 列出服务
```http
GET /api/v1/ops/services?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 注册服务
```http
POST /api/v1/ops/services
Authorization: Bearer {access_token}
```

### 5.4 计费管理 `/api/v1/ops/billing`

#### 查询账单
```http
GET /api/v1/ops/billing?page=1&page_size=20&month=2024-01
Authorization: Bearer {access_token}
```

#### 创建计费规则
```http
POST /api/v1/ops/billing/rules
Authorization: Bearer {access_token}
```

### 5.5 运营监控 `/api/v1/ops/monitoring`

#### 获取监控概览
```http
GET /api/v1/ops/monitoring/overview
Authorization: Bearer {access_token}
```

#### 获取实时指标
```http
GET /api/v1/ops/monitoring/metrics?metric=cpu_usage&period=1h
Authorization: Bearer {access_token}
```

### 5.6 监控增强 `/api/v1/ops/monitoring-enhanced`

#### 获取详细监控数据
```http
GET /api/v1/ops/monitoring-enhanced/detailed
Authorization: Bearer {access_token}
```

### 5.7 告警管理 `/api/v1/ops/alerts`

#### 列出告警
```http
GET /api/v1/ops/alerts?page=1&page_size=20&status=active
Authorization: Bearer {access_token}
```

#### 创建告警规则
```http
POST /api/v1/ops/alerts/rules
Authorization: Bearer {access_token}
```

#### 确认告警
```http
POST /api/v1/ops/alerts/{alert_id}/acknowledge
Authorization: Bearer {access_token}
```

### 5.8 SLA 管理 `/api/v1/ops/sla`

#### 列出 SLA
```http
GET /api/v1/ops/sla?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 创建 SLA
```http
POST /api/v1/ops/sla
Authorization: Bearer {access_token}
```

### 5.9 合规管理 `/api/v1/ops/compliance`

#### 合规检查
```http
POST /api/v1/ops/compliance/check
Authorization: Bearer {access_token}
```

#### 获取合规报告
```http
GET /api/v1/ops/compliance/reports/{report_id}
Authorization: Bearer {access_token}
```

### 5.10 KPI 仪表盘 `/api/v1/ops/kpi`

#### 获取 KPI 数据
```http
GET /api/v1/ops/kpi?period=monthly&metric=data_usage
Authorization: Bearer {access_token}
```

---

## 6. 安全管控中心 `/api/v1/security`

### 6.1 安全策略 `/api/v1/security/policies`

#### 列出策略
```http
GET /api/v1/security/policies?page=1&page_size=20
Authorization: Bearer {access_token}
```

#### 创建策略
```http
POST /api/v1/security/policies
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "name": "数据访问策略",
  "type": "access_control",
  "rules": [
    {
      "resource": "data_asset",
      "action": "read",
      "conditions": {
        "role": ["data_analyst", "admin"],
        "time": "09:00-18:00"
      }
    }
  ]
}
```

### 6.2 DID 身份 `/api/v1/security/did`

#### 创建 DID
```http
POST /api/v1/security/did
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "method": "ethr",
  "public_key": "0x...",
  "metadata": {
    "name": "用户DID",
    "organization": "电力公司"
  }
}
```

#### 解析 DID
```http
GET /api/v1/security/did/{did}
Authorization: Bearer {access_token}
```

#### 验证 DID 签名
```http
POST /api/v1/security/did/verify
Authorization: Bearer {access_token}
```

### 6.3 可验证凭证 `/api/v1/security/vc`

#### 签发凭证
```http
POST /api/v1/security/vc/issue
Authorization: Bearer {access_token}
```

#### 验证凭证
```http
POST /api/v1/security/vc/verify
Authorization: Bearer {access_token}
```

#### 撤销凭证
```http
POST /api/v1/security/vc/{credential_id}/revoke
Authorization: Bearer {access_token}
```

### 6.4 密钥管理 `/api/v1/security/keys`

#### 生成密钥对
```http
POST /api/v1/security/keys/generate
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "algorithm": "SM2",
  "key_size": 256,
  "purpose": "signing"
}
```

#### 导出公钥
```http
GET /api/v1/security/keys/{key_id}/public
Authorization: Bearer {access_token}
```

### 6.5 威胁检测 `/api/v1/security/threats`

#### 列出威胁
```http
GET /api/v1/security/threats?page=1&page_size=20&severity=high
Authorization: Bearer {access_token}
```

#### 获取威胁详情
```http
GET /api/v1/security/threats/{threat_id}
Authorization: Bearer {access_token}
```

#### 处置威胁
```http
POST /api/v1/security/threats/{threat_id}/handle
Authorization: Bearer {access_token}
```

### 6.6 国密算法 `/api/v1/security/gmssl`

#### SM2 加密
```http
POST /api/v1/security/gmssl/sm2/encrypt
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "public_key": "hex_encoded_public_key",
  "plaintext": "base64_encoded_data"
}
```

#### SM2 解密
```http
POST /api/v1/security/gmssl/sm2/decrypt
Authorization: Bearer {access_token}
```

#### SM2 签名
```http
POST /api/v1/security/gmssl/sm2/sign
Authorization: Bearer {access_token}
```

#### SM3 哈希
```http
POST /api/v1/security/gmssl/sm3/hash
Authorization: Bearer {access_token}
```

#### SM4 加密
```http
POST /api/v1/security/gmssl/sm4/encrypt
Authorization: Bearer {access_token}
```

### 6.7 零知识证明 `/api/v1/security/zkp`

#### 生成证明
```http
POST /api/v1/security/zkp/prove
Authorization: Bearer {access_token}
```

#### 验证证明
```http
POST /api/v1/security/zkp/verify
Authorization: Bearer {access_token}
```

### 6.8 安全增强 `/api/v1/security`

#### ABAC 策略评估
```http
POST /api/v1/security/abac/evaluate
Authorization: Bearer {access_token}
```

### 6.9 增强审计 `/api/v1/security/audit`

#### 查询审计日志
```http
GET /api/v1/security/audit?page=1&page_size=20&action=login&user_id=uuid
Authorization: Bearer {access_token}
```

### 6.10 HSM 硬件安全模块 `/api/v1/security/hsm`

#### 获取 HSM 状态
```http
GET /api/v1/security/hsm/status
Authorization: Bearer {access_token}
```

#### HSM 签名
```http
POST /api/v1/security/hsm/sign
Authorization: Bearer {access_token}
```

### 6.11 安全等级防护 `/api/v1/security/levels`

#### 获取安全等级
```http
GET /api/v1/security/levels
Authorization: Bearer {access_token}
```

#### 设置安全等级
```http
POST /api/v1/security/levels
Authorization: Bearer {access_token}
```

---

## 7. MQTT 数据采集 `/api/v1/mqtt`

### 7.1 数据采集 `/api/v1/mqtt`

#### 注册设备
```http
POST /api/v1/mqtt/devices
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "device_id": "meter_001",
  "device_type": "smart_meter",
  "location": "发电厂A",
  "topics": ["energy/meter/001/power", "energy/meter/001/voltage"]
}
```

#### 发布数据
```http
POST /api/v1/mqtt/publish
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "topic": "energy/meter/001/power",
  "payload": {
    "value": 1234.56,
    "unit": "kW",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  "qos": 1
}
```

#### 订阅主题
```http
POST /api/v1/mqtt/subscribe
Authorization: Bearer {access_token}
```

### 7.2 MQTT 数据流 `/api/v1/mqtt/stream`

#### 获取实时数据流
```http
GET /api/v1/mqtt/stream/{topic}
Authorization: Bearer {access_token}
```

---

## 8. 系统管理

### 8.1 通知公告 `/api/v1/notifications`

#### 列出通知
```http
GET /api/v1/notifications?page=1&page_size=20&unread=true
Authorization: Bearer {access_token}
```

#### 创建通知
```http
POST /api/v1/notifications
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "title": "系统维护通知",
  "content": "系统将于今晚22:00-次日02:00进行维护",
  "type": "announcement",
  "target_users": ["user_id_1", "user_id_2"]
}
```

#### 标记已读
```http
POST /api/v1/notifications/{notification_id}/read
Authorization: Bearer {access_token}
```

#### 全部标记已读
```http
POST /api/v1/notifications/read-all
Authorization: Bearer {access_token}
```

### 8.2 系统配置 `/api/v1/system/config`

#### 获取配置
```http
GET /api/v1/system/config?key=site_name
Authorization: Bearer {access_token}
```

#### 更新配置
```http
PUT /api/v1/system/config
Authorization: Bearer {access_token}
```

**请求体**:
```json
{
  "key": "site_name",
  "value": "能源可信数据空间",
  "description": "系统名称"
}
```

### 8.3 操作日志 `/api/v1/audit-logs`

#### 查询日志
```http
GET /api/v1/audit-logs?page=1&page_size=20&action=login&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {access_token}
```

#### 导出日志
```http
GET /api/v1/audit-logs/export?format=csv&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {access_token}
```

---

## 9. WebSocket 实时通信

### 连接
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/notifications?token=YOUR_JWT_TOKEN');
```

### 订阅频道
```json
{
  "type": "subscribe",
  "channel": "notifications"
}
```

### 取消订阅
```json
{
  "type": "unsubscribe",
  "channel": "notifications"
}
```

### 心跳
```json
{
  "type": "heartbeat"
}
```

### 接收消息
```json
{
  "type": "notification",
  "channel": "notifications",
  "data": {
    "id": "uuid",
    "title": "新通知",
    "content": "...",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

---

## 10. 统一门户 `/api/v1/portal`

### 获取门户概览
```http
GET /api/v1/portal/overview
Authorization: Bearer {access_token}
```

### 获取统计数据
```http
GET /api/v1/portal/statistics
Authorization: Bearer {access_token}
```

---

## 认证流程

### 1. 密码登录流程
```
用户 → POST /auth/login (username, password)
服务端 → 验证密码 → 返回 access_token + refresh_token
用户 → 使用 access_token 访问 API
Token 过期 → POST /auth/refresh (refresh_token) → 新 access_token
```

### 2. DID 签名登录流程
```
用户 → 获取 challenge
用户 → 使用私钥签名 challenge
用户 → POST /auth/login/did (did, signature, challenge)
服务端 → 解析 DID → 获取公钥 → 验证签名 → 返回 token
```

### 3. SM2 证书登录流程
```
用户 → 获取 challenge
用户 → 使用 SM2 私钥签名 challenge
用户 → POST /auth/login/certificate (certificate, signature, challenge)
服务端 → 验证证书 → 验证签名 → 返回 token
```

### 4. MFA 流程
```
用户 → POST /auth/login (首次)
服务端 → 返回 mfa_session_id
用户 → POST /auth/mfa/verify (session_id, code)
服务端 → 验证 MFA 码 → 返回 token
```

---

## 国密算法使用

### SM2 非对称加密
- **用途**: 数字签名、密钥交换、身份认证
- **密钥长度**: 256 位
- **接口**: `/api/v1/security/gmssl/sm2/*`

### SM3 哈希算法
- **用途**: 数据完整性校验、数字签名
- **输出长度**: 256 位
- **接口**: `/api/v1/security/gmssl/sm3/hash`

### SM4 对称加密
- **用途**: 数据加密、通信加密
- **密钥长度**: 128 位
- **接口**: `/api/v1/security/gmssl/sm4/*`

---

## 错误处理

### 常见错误场景

#### 1. 未授权 (401)
```json
{
  "code": 1002,
  "message": "未授权：缺少认证令牌",
  "data": null
}
```

#### 2. 禁止访问 (403)
```json
{
  "code": 1003,
  "message": "禁止访问：权限不足",
  "data": null
}
```

#### 3. 资源未找到 (404)
```json
{
  "code": 1004,
  "message": "资源未找到",
  "data": null
}
```

#### 4. 参数验证失败 (422)
```json
{
  "code": 1001,
  "message": "参数错误",
  "data": {
    "errors": [
      {
        "field": "username",
        "message": "用户名不能为空"
      }
    ]
  }
}
```

---

## 限流策略

- **默认限制**: 100 请求/分钟/IP
- **认证接口**: 10 请求/分钟/IP
- **文件上传**: 10 请求/小时/用户

超限响应:
```json
{
  "code": 1005,
  "message": "请求过于频繁，请稍后再试",
  "data": null
}
```

---

## 版本历史

| 版本 | 日期 | 描述 |
|------|------|------|
| v1.0.0 | 2024-01-01 | 初始版本 |
| v1.1.0 | 2024-02-01 | 添加国密算法支持 |
| v1.2.0 | 2024-03-01 | 添加 WebSocket 实时通信 |
| v1.3.0 | 2024-04-01 | 添加 FATE 联邦学习集成 |

---

## 联系方式

- **技术支持**: support@energy-tds.example.com
- **文档更新**: docs@energy-tds.example.com
- **GitHub**: https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New
