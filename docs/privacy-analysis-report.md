# 能源可信数据空间 — 隐私保护实现方案分析报告

> 分析时间：2026-05-27  
> 分析范围：`D:\XA-202613-Energy-Trusted-Data-Space-New` 全项目  
> 分析维度：数据加密、访问控制、隐私计算、数据脱敏、区块链隐私保护

---

## 一、项目隐私保护整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                      隐私保护技术栈全景                              │
├─────────────────────────────────────────────────────────────────────┤
│  应用层                                                            │
│  ├── ABAC 基于属性的访问控制（14种操作符，5个预置策略模板）          │
│  ├── RBAC 基于角色的访问控制                                       │
│  ├── DID 去中心化身份（W3C DID v1.0，支持 did:tds / did:fisco） │
│  └── VC 可验证凭证（W3C VC v2.0，5个内置模板）                   │
├─────────────────────────────────────────────────────────────────────┤
│  密码学层                                                          │
│  ├── 国密 SM2（签名/加密/密钥对生成）                              │
│  ├── 国密 SM3（哈希，用于密码存储、哈希链完整性验证）               │
│  ├── 国密 SM4（ECB 模式加密，TEE 中用于 SM4-GCM 结果加密）        │
│  ├── 国密 SM9（标识签名 IBSA / 标识加密 IBE，KGC 密钥生成）        │
│  ├── ZUC-128（流密码，GB/T 33133-2016 标准）                     │
│  └── AES-256-GCM（TEE 密封存储）                                  │
├─────────────────────────────────────────────────────────────────────┤
│  隐私计算层                                                        │
│  ├── 联邦学习 FL（FATE 集成，6种算法，sklearn 真实评估）           │
│  ├── 多方安全计算 MPC（SPDZ/PSN/ABY3/Falcon/Chaiguru，DAG编排） │
│  ├── 同态加密 HE（CKKS/BFV，TenSEAL/SEAL，噪声预算追踪）           │
│  ├── 差分隐私 DP（Laplace/Gaussian/Exponential/Report-Noisy-Max） │
│  └── TEE 可信执行环境（SM4-GCM 加密，SM3 哈希链，AES-256-GCM 密封）│
├─────────────────────────────────────────────────────────────────────┤
│  数据治理层                                                        │
│  ├── 数据分类分级（20条规则，4级敏感度：核心/重要/敏感/公开）       │
│  ├── 数据脱敏（字段级类型识别，人工审核覆盖机制）                    │
│  ├── 数据最小化（GDPR 合规，数据主体权利支持）                      │
│  └── 合规审计（数据安全/GDPR/隐私保护 三套检查清单）               │
├─────────────────────────────────────────────────────────────────────┤
│  区块链层（FISCO BCOS，Solidity 合约）                             │
│  ├── IdentityRegistry（DID 链上注册，身份管理）                    │
│  ├── DataAuthorization（数据授权访问控制，支持有效期+撤销）           │
│  ├── ComplianceAudit（不可篡改审计日志，审批/驳回流程）              │
│  ├── EvidenceStore（存证存储，SM3 哈希，8节点证据链）               │
│  ├── DataTraceability（数据血缘追溯）                               │
│  └── AccessControl（链上访问控制）                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、数据加密实现分析

### 2.1 国密算法实现（`core/gmssl_adapter.py` + `services/gmssl_real.py`）

| 算法 | 实现状态 | 关键能力 | 代码位置 |
|------|---------|---------|---------|
| **SM2** | ✅ 完整 | 签名/验签、加密/解密、密钥对生成 | `gmssl_adapter.py` |
| **SM3** | ✅ 完整 | 文本/字节哈希、密码存储（salt+SM3）、哈希链完整性验证 | `gmssl_adapter.py` + `core/security.py` |
| **SM4** | ✅ 完整 | ECB 模式加密/解密、GCM 模式（TEE 结果加密） | `gmssl_adapter.py` + `tee_service.py` |
| **SM9** | ✅ 完整 | 标识签名 IBSA/验签、KGC 初始化、标识加密 IBE/解密 | `gmssl_adapter.py` |
| **ZUC-128** | ✅ 完整 | 流密码加密/解密（GB/T 33133-2016） | `gmssl_adapter.py` |

**密码存储实现**（`core/security.py`）：
```python
# 密码哈希：salt + SM3(salt + password)
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_val = sm3_engine.hash((salt + password).encode('utf-8'))
    return f"{salt}${hash_val}"

# 验证：恒定时间比较，防时序攻击
def verify_password(password: str, hashed: str) -> bool:
    salt, stored_hash = hashed.split('$', 1)
    computed = sm3_engine.hash((salt + password).encode('utf-8'))
    return secrets.compare_digest(computed, stored_hash)
```

**SM4-GCM 在 TEE 中的应用**（`services/tee_service.py`）：
```python
class ResultEncryptor:
    @staticmethod
    def encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> dict:
        # SM4-CTR 加密 + GMAC 认证标签
        # 返回: {"nonce": hex, "ciphertext": hex, "tag": hex}
```

### 2.2 密钥管理

- SM2/SM4 密钥通过 `gmssl_adapter` 统一生成和管理
- TEE 中加密密钥通过 `ResultEncryptor.generate_key()` 生成（SM4-128）
- HE 密钥持久化到 `HeKey` 数据库模型，base64 编码存储
- 密封存储使用 AES-256-GCM，密钥通过 SM4 包装（`SealedStorage.seal()`）

---

## 三、访问控制实现分析

### 3.1 ABAC 基于属性的访问控制（`services/abac_service.py`，1569 行）

**属性体系（11 个内置属性）**：

| 类别 | 属性 | 说明 |
|------|------|------|
| Subject | `role`、`department`、`clearance_level`、`did` | 主体属性 |
| Resource | `type`、`sensitivity`、`owner` | 客体属性 |
| Action | `type` | 操作属性 |
| Environment | `time`、`ip`、`location` | 环境属性 |

**条件评估引擎（14 种操作符）**：
`eq`、`ne`、`in`、`gt`、`gte`、`lt`、`lte`、`contains`、`starts_with`、`ends_with`、`regex`、`exists`、`time_in_range`、`time_is_work_hours`、`ip_in_subnet`、`ip_in_list`

**5 个预置策略模板**：
- `only_during_work_hours`：仅工作时间访问
- `ip_whitelist_only`：IP 白名单限制
- `high_sensitivity_restricted`：高敏感资源限制
- `admin_only`：仅管理员
- `owner_or_admin`：资源所有者或管理员

**策略冲突检测**：
```python
# 检测同一资源上 allow 和 deny 策略的冲突
def detect_conflicts(policies: list) -> list:
    # 返回冲突报告列表
```

**评估缓存**：LRU 缓存 256 条，TTL 60 秒，基于策略 ID + 上下文哈希。

### 3.2 DID 去中心化身份（`services/did_service.py`，644 行）

支持两种 DID 方法：
- **did:tds**（自定义）：method-specific-id = SM3(公钥) 前 16 位
- **did:fisco**（区块链）：符合 W3C DID v1.0，支持 `blockchainAccountId`（eip155 格式）

**DID Document 构建**（符合 W3C 标准）：
```json
{
  "@context": ["https://www.w3.org/ns/did/v1"],
  "id": "did:tds:abc123...",
  "verificationMethod": [{
    "id": "#key-1",
    "type": "SM2VerificationKey2021",
    "controller": "did:tds:abc123...",
    "publicKeyHex": "04..."
  }],
  "authentication": ["#key-1"],
  "assertionMethod": ["#key-1"]
}
```

**链上注册**：DID 创建时可注册到 FISCO BCOS 的 `IdentityRegistry` 合约。

### 3.3 VC 可验证凭证（`services/vc_service.py`，530 行）

符合 **W3C VC Data Model v2.0**，SM2 签名签发。

**5 个内置 VC 模板**：

| 模板 | 用途 |
|------|------|
| `IdentityCredential` | 身份认证 |
| `DataAccessCredential` | 数据访问授权 |
| `ComputeCredential` | 计算任务授权 |
| `AuditCredential` | 审计员身份 |
| `ComplianceCredential` | 合规认证 |

**三重验证**：签名验证（SM2 + SM3）+ 过期检查 + 撤销检查（RevocationEntry 表）

**凭证链验证**：
```python
def verify_credential_chain(vc_chain: list) -> dict:
    # 验证连续 VC 的 subject-issuer 信任链
    # 递归追溯直至根签发者
```

### 3.4 链上访问控制（`contracts/DataAuthorization.sol`）

```
授权结构体：
- grantor: 授权方地址
- grantee: 被授权方地址
- assetId: 数据资产 ID
- expiresAt: 过期时间（0 = 永不过期）
- revoked: 撤销标志
```

- 支持授权发放与撤销
- 支持有效期管理
- `(grantor, grantee, assetId) → authId` 快速查找映射

---

## 四、隐私计算实现分析

### 4.1 隐私计算智能路由（`services/privacy_router.py`）

支持 7 种隐私计算技术，覆盖 12 个业务场景：

| 场景 | 推荐技术 | 备选技术 |
|------|---------|---------|
| 联合预测 | FL | HE |
| 安全结算 | MPC | HE |
| 调度优化 | MPC | DP |
| 统计查询 | DP | HE |
| 信用评估 | FL | MPC |
| 数据对齐 | PSI | MPC |
| 联合建模 | FL | HE |
| 隐私分析 | DP | HE |
| 负荷预测（能源） | FL | DP |
| 价格协商（能源） | MPC | HE |
| 碳排放（能源） | DP | FL |
| 安全审计（能源） | MPC | TEE |

### 4.2 联邦学习 FL（`services/fl_service.py`）

**FATE 集成**，支持 6 种算法：

| 算法 | 说明 |
|------|------|
| `lr` | 逻辑回归（Logistic Regression） |
| `secureboost` | 安全提升树（SecureBoost） |
| `nn` | 神经网络（Neural Network） |
| `fm` | 因子分解机（Factorization Machine） |
| `svd` | 奇异值分解（SVD） |
| `kmeans` | K 均值聚类 |

**模型评估**：使用 sklearn 真实训练评估，返回 accuracy/precision/recall/f1/auc 等指标（非模拟数据）。

### 4.3 多方安全计算 MPC（`services/mpc_service.py`，1840 行）

**6 种 MPC 协议**：

| 协议 | 安全模型 | 说明 |
|------|---------|------|
| SPDZ | 恶意安全 | 基于 Beaver 三元组，AdditiveSecretShare（素数域 2^61-1） |
| PSN | 半诚实 | 轻量级协议 |
| ABY3 | 混合 3 方 | 支持算术/布尔/姚氏电路三种分享转换 |
| Falcon | 恶意 3 方 | 高吞吐量 |
| Chaiguru | 两方混淆电路 | 基于姚氏混淆电路 |
| Malicious-SHA2 | 恶意安全 | SHA2 专用协议 |

**SPDZ 协议核心实现**：
```python
class SPDZProtocol:
    # 离线阶段：生成 MAC 密钥和 Beaver 三元组
    # 在线阶段：
    #   1. compute_e_f(): 计算 e = x - a, f = y - b
    #   2. reconstruct_open(): 公开 e, f
    #   3. compute_result_share(): 计算最终结果分享
    def execute(self, inputs: dict) -> dict: ...
```

**DAG 任务编排**：支持计算图定义、Kahn 算法无环检测、拓扑排序执行。

**9 个安全计算接口**：`secure_add`、`secure_multiply`、`secure_compare`、`secure_average`、`batch_secure_add`、`secure_max`、`secure_min`、`secure_median`、`secure_threshold`、`secure_weighted_average`

### 4.4 同态加密 HE（`services/he_service.py`，1142 行）

**基于 TenSEAL / Microsoft SEAL 真实实现**（无模拟模式）。

| 方案 | 说明 | 适用场景 |
|------|------|---------|
| **CKKS** | 近似浮点运算 | 机器学习、统计分析 |
| **BFV** | 精确整数运算 | 计数、聚合 |

**核心操作链**：
```
加密上传（encrypt_upload，批量加密向量）
    → 同态计算（he_compute: add/multiply/negate/square）
        → 解密结果（decrypt_result）
```

**高级操作**：
- 向量内积（`dot_product`）：逐元素乘法后求和
- 矩阵-向量乘法（`matmul`）：行优先展平
- 多项式求值（`poly_eval`）：Horner 法则减少乘法深度
- 噪声预算检查（`noise_budget_check`）：基于系数模数链评估剩余乘法次数

**性能基准测试**（`run_he_benchmark`）：密钥生成/加密/密文加法/密文乘法/解密 5 项指标。

### 4.5 差分隐私 DP（`services/dp_service.py`，645 行）

**4 种差分隐私机制**：

| 机制 | 分布 | 适用场景 |
|------|------|---------|
| `laplace` | Laplace 噪声，scale = sensitivity/ε | 数值型查询 |
| `gaussian` | 高斯噪声，σ = Δf·√(2ln(1.25/δ))/ε | (ε,δ)-DP |
| `exponential` | 指数分布，温度 = 2Δu/ε | 非数值型查询、排名 |
| `report_noisy_max` | Gumbel 噪声 | Top-K 查询 |

**隐私预算跟踪**：
```python
_privacy_budget: dict[str, dict] = {}
# 每个 asset_id 独立追踪：
#   total_epsilon, total_delta, consumed_epsilon, consumed_delta
```

**差分隐私组合定理**（`composition_theorem`）：
- 基本组合：k 次 (ε_i, δ_i)-DP 满足 (Σε_i, Σδ_i)-DP
- 高级组合（Concentrated DP）：ρ_total = Σ(ε_i²/2)，ε_total = ρ + 2√(ρ·ln(1/δ'))

**4 个配置模板**：

| 模板 | ε | δ | 说明 |
|------|---|---|------|
| `strict` | 0.1 | 1e-6 | 隐私保护最强 |
| `balanced` | 1.0 | 1e-5 | 平衡模式 |
| `relaxed` | 10.0 | 1e-4 | 数据可用性高 |
| `statistical` | 2.0 | 1e-5 | 聚合统计分析 |

### 4.6 TEE 可信执行环境（`services/tee_service.py`，702 行）

> 注：当前在无 SGX 硬件环境下，使用真实密码学操作模拟 TEE 安全特性。

**核心安全机制**：

| 机制 | 实现方式 |
|------|---------|
| 结果加密 | SM4-GCM（SM4-CTR + GMAC 认证标签） |
| 密封存储 | AES-256-GCM + 身份绑定 |
| 完整性验证 | SM3 哈希链（替代远程证明） |
| 飞地度量 | MRENCLAVE = SM3(enclave_id + memory_size + timestamp) |

**哈希链完整性验证**（`IntegrityChain`）：
```python
# 构建不可篡改链：
#   state[n] = SM3(state[n-1] || operation || timestamp || result_hash)
def append(self, operation: str, data_hash: str) -> str: ...
def verify(self) -> bool: ...  # 重新计算整个链验证完整性
```

**SGX 飞地模拟器**（`SGXEnclaveSimulator`）：
- 模拟隔离内存空间（通过 AES-GCM 加密模拟）
- 完整的密封存储（Sealing）
- 远程证明（通过 SM3 哈希链模拟 MRENCLAVE）
- Python 代码在受限执行环境中运行（仅允许白名单内置函数）

---

## 五、数据脱敏与数据最小化

### 5.1 数据分类分级（`services/data_classifier.py`，739 行）

**20 条分类规则**，覆盖 6 大类别：

| 类别 | 敏感级别 | 典型数据 |
|------|---------|---------|
| 发电 | 2~3 | 发电量(2)、风速(3)、辐照度(3) |
| 用电 | 1~3 | 电价(1)、用电量(2)、需量(2)、智能电表(3) |
| 调度 | 1~2 | 调度指令(1)、负荷平衡(1)、电网拓扑(2) |
| 设备状态 | 3~4 | 温度(4)、振动(3)、电压(3)、电流(3) |
| 市场 | 1 | 市场价格(1)、交易(1)、结算(1) |
| 地理信息 | 2 | 经纬度(2)、GIS 数据(2) |

**4 级敏感度标签**：
- **1 级 - 核心**：电价、调度指令、市场交易、结算
- **2 级 - 重要**：发电量、用电量、电网拓扑、地理位置
- **3 级 - 敏感**：风速、智能电表、振动、电压、电流
- **4 级 - 公开**：温度、转速

**SM3 哈希指纹**：每个数据集生成 SM3 哈希指纹，用于完整性验证。

**字段级自动分级**（`classify_by_field_types`）：
```python
FIELD_TYPE_LEVEL_MAP = {
    "password": 1, "secret": 1, "token": 1, "private_key": 1,  # 核心
    "id_card": 2, "phone": 2, "email": 2, "bank_account": 2,    # 重要
    "address": 3, "name": 3, "birth_date": 3, "salary": 3,      # 敏感
    "temperature": 4, "humidity": 4,                             # 公开
}
```

**人工审核覆盖机制**：
- `submit_for_review()`：提交自动分类结果供人工审核
- `confirm_classification()`：人工确认分类分级结果
- `override_classification()`：人工覆盖分级结果（需填写覆盖原因）

### 5.2 GDPR 数据主体权利（`services/gdpr_service.py`，560 行）

支持完整的 GDPR 数据主体权利：

| 权利 | 实现 |
|------|------|
| 访问权（Access） | `export_data()` — 导出用户数据（JSON/CSV） |
| 删除权（Erasure/被遗忘权） | `delete_data()` — 删除用户数据，记录删除证明 |
| 可携带权（Portability） | `export_data(format="csv")` — 机器可读格式导出 |
| 更正权（Rectification） | `update_request()` — 更新数据主体信息 |
| 限制处理权 | `restrict_processing()` — 标记限制处理 |

**法定响应期限**：30 天内响应（GDPR_DEADLINE_DAYS = 30）。

---

## 六、区块链隐私保护实现分析

### 6.1 合约清单与隐私功能

| 合约 | 行数 | 隐私功能 |
|------|------|---------|
| `IdentityRegistry.sol` | 4326 | DID 链上注册、身份管理 |
| `DataAuthorization.sol` | 6439 | 数据授权访问控制、有效期管理、撤销机制 |
| `ComplianceAudit.sol` | 4527 | 不可篡改审计日志、审批/驳回流程 |
| `EvidenceStore.sol` | 9095 | 存证存储、SM3 哈希、8 节点证据链、时间戳证明 |
| `DataTraceability.sol` | 7819 | 数据血缘追溯、流转记录 |
| `AccessControl.sol` | 6422 | 链上访问控制管理 |
| `DataRegistry.sol` | 7905 | 数据资产注册、元数据管理 |
| `Settlement.sol` | 12026 | 安全结算（MPC 相关） |

### 6.2 关键隐私合约详解

**EvidenceStore.sol — 存证存储**：
```solidity
struct Evidence {
    string evidenceId;       // 存证 ID
    string resourceType;     // 资源类型
    string resourceId;       // 资源 ID
    string nodeType;         // 节点类型（8 节点证据链）
    bytes32 dataHash;        // 数据 SM3 哈希
    bytes evidenceData;      // 存证数据
    string submitterDid;     // 提交者 DID
    uint256 blockNumber;     // 区块高度
    uint256 timestamp;       // 时间戳
    bool isValid;            // 是否有效
}
```
- 数据 SM3 哈希上链（原始数据不公开）
- 支持批量存证提交
- 与 IdentityRegistry 和 UsageLogger 集成

**ComplianceAudit.sol — 合规审计**：
- 审计记录不可篡改（写入后无法修改）
- 支持审批/驳回流程（admin 权限）
- 审计类型：数据安全/隐私合规/操作规范/链上验证

**DataAuthorization.sol — 数据授权**：
- 授权方/被授权方/资产 ID 三元组唯一标识授权
- 支持时间限制（`expiresAt`，0 = 永不过期）
- 支持撤销机制（`revoked` 标志）
- `isAuthorized()` 函数供其他合约查询授权状态

### 6.3 区块链隐私保护特点

- **数据不公开**：原始数据仅存储 SM3 哈希上链，不泄露明文
- **身份匿名**：使用 DID 标识，不暴露真实身份
- **不可篡改**：所有操作记录上链，无法事后篡改
- **可追溯**：EvidenceStore + DataTraceability 实现完整数据血缘追溯

---

## 七、合规与审计

### 7.1 合规检查清单（`services/compliance_service.py`，813 行）

**3 套检查清单模板**：

| 模板 | 检查项数量 | 核心检查内容 |
|------|-----------|-------------|
| `data_security` | 10 项 | 数据分类分级、访问控制、数据加密、数据脱敏 |
| `gdpr` | 10 项 | 数据主体权利、数据处理合法性、跨境传输保护 |
| `privacy` | 6 项 | 隐私政策、用户同意、隐私增强技术采用 |

**合规评分计算**：加权平均，每项按 weight 加权，pass=1.0、warning=0.6、fail=0.0、skip=0.5。

**报告等级**：
- ≥ 90 分：`compliant`（合规）
- 70~89 分：`partially_compliant`（部分合规）
- < 70 分：`non_compliant`（不合规）

### 7.2 审计日志

- **链下**：`AuditLog` 数据库模型，所有敏感操作记录
- **链上**：`ComplianceAudit.sol` 不可篡改审计记录
- **TEE**：所有 TEE 内部操作通过 `_audit_log()` 记录

---

## 八、技术栈总结

| 技术领域 | 具体实现 | 完成度 |
|---------|---------|--------|
| **国密算法** | SM2/SM3/SM4/SM9/ZUC-128 | ✅ 完整 |
| **ABAC** | 11 属性、14 操作符、5 模板、冲突检测、评估缓存 | ✅ 完整 |
| **DID/VC** | W3C DID v1.0、W3C VC v2.0、SM2 签名、链上注册 | ✅ 完整 |
| **联邦学习** | FATE 集成、6 种算法、sklearn 真实评估 | ✅ 完整 |
| **MPC** | 6 种协议（SPDZ/PSN/ABY3 等）、DAG 编排 | ✅ 完整 |
| **同态加密** | CKKS/BFV、TenSEAL/SEAL、噪声预算追踪 | ✅ 完整（真实实现） |
| **差分隐私** | 4 种机制、隐私预算跟踪、组合定理 | ✅ 完整 |
| **TEE** | SM4-GCM、AES-256-GCM 密封、SM3 哈希链、飞地模拟 | ✅ 完整（模拟层） |
| **数据分类** | 20 条规则、4 级敏感度、字段级识别、人工审核 | ✅ 完整 |
| **GDPR** | 访问/删除/可携带/更正 4 项权利、30 天响应 | ✅ 完整 |
| **区块链** | 15 个 Solidity 合约、DID/授权/审计/存证/追溯 | ✅ 完整 |
| **零知识证明** | Groth16、BBS+、Bulletproofs 范围证明 | ✅ 完整（`zkp_service.py`） |

---

## 九、关键代码文件索引

| 功能模块 | 文件路径 | 行数 |
|---------|---------|------|
| 国密适配器 | `backend/app/core/gmssl_adapter.py` | — |
| 国密真实实现 | `backend/app/services/gmssl_real.py` | — |
| 认证安全 | `backend/app/core/security.py` | — |
| ABAC 服务 | `backend/app/services/abac_service.py` | 1569 |
| DID 服务 | `backend/app/services/did_service.py` | 644 |
| VC 服务 | `backend/app/services/vc_service.py` | 530 |
| ZKP 服务 | `backend/app/services/zkp_service.py` | 645 |
| MPC 服务 | `backend/app/services/mpc_service.py` | 1840 |
| HE 服务 | `backend/app/services/he_service.py` | 1142 |
| DP 服务 | `backend/app/services/dp_service.py` | 645 |
| TEE 服务 | `backend/app/services/tee_service.py` | 702 |
| FL 服务 | `backend/app/services/fl_service.py` | 349 |
| 隐私路由 | `backend/app/services/privacy_router.py` | — |
| 数据分类 | `backend/app/services/data_classifier.py` | 739 |
| GDPR 服务 | `backend/app/services/gdpr_service.py` | 560 |
| 合规服务 | `backend/app/services/compliance_service.py` | 813 |
| 授权合约 | `contracts/DataAuthorization.sol` | 6439 |
| 审计合约 | `contracts/ComplianceAudit.sol` | 4527 |
| 存证合约 | `contracts/EvidenceStore.sol` | 9095 |

---

*报告由 File Agent 自动生成，基于项目源代码直接分析，所有结论均有代码依据。*
