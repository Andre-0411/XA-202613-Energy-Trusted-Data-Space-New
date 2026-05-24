# 能源可信数据空间 API 文档

## 基础信息
- **基础URL**: `http://10.241.2.64:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **默认管理员**: admin / admin123

## 认证 API

### 登录
```
POST /auth/login
Body: {"username": "admin", "password": "admin123"}
Response: {"code": 0, "data": {"access_token": "...", "refresh_token": "...", "user": {...}}}
```

### 刷新Token
```
POST /auth/refresh
Body: {"refresh_token": "..."}
```

### 登出
```
POST /auth/logout
Headers: Authorization: Bearer <token>
```

## 数据资源 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /data/sources | GET | 数据源列表 |
| /data/assets | GET | 数据资产列表 |
| /data/catalog | GET | 数据目录 |
| /data/metadata | GET | 元数据管理 |
| /data/quality | GET | 数据质量 |
| /data/applications | GET | 服务申请 |
| /data/applications/stats | GET | 申请统计 |
| /data/lineage/{id} | GET | 数据血缘 |

## 计算中心 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /compute/tasks | GET | 计算任务列表 |
| /compute/tasks | POST | 创建计算任务 |
| /compute/agents | GET | 计算代理列表 |
| /compute/dag | GET | DAG编排 |
| /compute/sandbox | GET | 数据沙箱 |
| /compute/benchmarks | GET | 性能基准 |
| /compute/cluster/nodes | GET | 集群节点 |
| /compute/cluster/status | GET | 集群状态 |

### 隐私计算

| 端点 | 方法 | 说明 |
|------|------|------|
| /compute/enhanced/privacy/technologies | GET | 隐私计算技术列表 |
| /compute/enhanced/privacy/scenarios | GET | 隐私计算场景 |
| /compute/enhanced/privacy/status | GET | 隐私计算状态 |
| /compute/enhanced/demo/full | GET | 完整隐私计算演示 |
| /compute/enhanced/demo/fate | GET | FATE联邦学习演示 |
| /compute/enhanced/demo/mpc | GET | MPC安全计算演示 |
| /compute/enhanced/demo/he/benchmark | GET | 同态加密性能基准 |
| /compute/enhanced/demo/tee/benchmark | GET | TEE性能基准 |

## 区块链存证 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /blockchain/nft | GET | NFT资产列表 |
| /blockchain/nft | POST | 铸造NFT |
| /blockchain/evidence | GET | 存证记录列表 |
| /blockchain/contracts | GET | 智能合约列表 |
| /blockchain/settlement/list | GET | 结算记录列表 |
| /blockchain/bridge/chains | GET | 跨链支持 |

## 运营管理中心 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /ops/users | GET | 用户列表 |
| /ops/organizations | GET | 组织列表 |
| /ops/services | GET | 服务管理 |
| /ops/quotas | GET | 配额管理 |
| /ops/monitoring/metrics | GET | 业务指标 |
| /ops/monitoring/health | GET | 系统健康 |
| /ops/monitoring/dashboard | GET | 仪表盘数据 |
| /ops/kpi/dashboard | GET | KPI数据 |
| /ops/alerts | GET | 告警列表 |
| /ops/billing/records | GET | 计费记录 |
| /ops/gdpr/requests | GET | GDPR请求 |

## 安全管控中心 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /security/keys | GET | 密钥管理 |
| /security/policies | GET | 安全策略 |
| /security/threats | GET | 威胁检测 |
| /security/levels | GET | 安全等级 |
| /security/zkp/proofs | GET | ZKP证明 |
| /security/audit/logs | GET | 审计日志 |
| /security/bbs/keys | GET | BBS密钥 |
| /security/abac/policies | GET | ABAC策略 |

## AI Agent API

| 端点 | 方法 | 说明 |
|------|------|------|
| /agent/chat | POST | Agent聊天 |
| /agent/agents | GET | 可用Agent列表 |
| /agent/execute | POST | 执行Agent任务 |
| /agent/history | GET | 对话历史 |

## 业务流 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /organizations/invite-codes/batch | POST | 批量生成邀请码 |
| /organizations/invite-codes/{id}/disable | PUT | 禁用邀请码 |
| /organizations/certifications | GET | 机构认证列表 |
| /catalog-manage | GET | 数据目录管理 |
| /catalog-manage/{id}/supply-channels | GET | 供给通道配置 |
| /catalog-manage/{id}/control-protocol | GET | 控制协议配置 |
| /connector-manage | GET | 连接器管理 |
| /data-subscriptions | GET | 数据订阅 |
| /product-manage | GET | 产品管理 |
| /demand-manage | GET | 需求管理 |
| /workflows | GET | 工作流 |
| /contracts | GET | 合约管理 |

## 系统 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /notifications | GET | 通知列表 |
| /audit-logs | GET | 操作日志 |
| /health | GET | 健康检查 |

## 响应格式

所有API返回统一格式：
```json
{
  "code": 0,
  "message": "success",
  "data": {...},
  "timestamp": "2026-05-25T01:00:00Z"
}
```

错误码：
- 0: 成功
- 1001: 认证失败
- 1002: Token过期
- 2001: 业务错误
- 9999: 系统内部错误
