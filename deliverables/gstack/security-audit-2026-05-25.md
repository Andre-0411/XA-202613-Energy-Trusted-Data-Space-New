# 能源可信数据空间 - 安全审计与QA测试综合报告

**审计日期**: 2026-05-25
**审计范围**: 后端核心模块（认证、用户管理、安全工具、中间件、密钥管理）
**审计标准**: OWASP Top 10 (2021)、STRIDE威胁模型

---

## 一、代码审查发现

### 严重度: HIGH（高）

#### H-1: 硬编码默认凭据（config.py）
**文件**: `backend/app/config.py:25,34,39,47,52,61,67,99,116,119`
**描述**: 多个敏感配置项使用硬编码默认值，包括：
- `APP_SECRET_KEY = "change-me-to-a-random-secret-key"` (line 25)
- `POSTGRES_PASSWORD = "changeme_pg_password"` (line 34)
- `REDIS_PASSWORD = "changeme_redis_password"` (line 39)
- `MONGO_PASSWORD = "changeme_mongo_password"` (line 47)
- `MINIO_SECRET_KEY = "changeme_minio_secret"` (line 52)
- `MQTT_PASSWORD = "changeme_mqtt_password"` (line 61)
- `RABBITMQ_PASSWORD = "changeme_rabbit_password"` (line 67)
- `JWT_SECRET_KEY = "change-me-jwt-secret-key"` (line 99)
- `GRAFANA_ADMIN_PASSWORD = "changeme_grafana_admin"` (line 116)
- `DEEPSEEK_API_KEY = "sk-your-api-key-here"` (line 119)

**风险**: 虽然有 `validate_secret_not_default` 验证器限制生产环境使用默认值，但：
1. 验证器仅检查 `APP_SECRET_KEY` 和 `JWT_SECRET_KEY`，其他密码无验证
2. 验证器使用 `os.environ.get("APP_ENV")` 读取环境变量，而非从 `Settings` 实例读取，可能不一致
3. 最小密钥长度仅16字符（line 206），建议至少32字符

**建议**: 
- 为所有敏感配置添加生产环境默认值验证
- 将最小密钥长度提升至32字符
- 添加启动时安全配置检查

#### H-2: 硬编码临时密码（user_service.py）
**文件**: `backend/app/services/user_service.py:49`
**描述**: `DEFAULT_TEMPORARY_PASSWORD = "Energy@2024!"` 被用于：
1. 批量导入用户时的默认密码（line 317）
2. 密码重置时的默认新密码（line 398）

**风险**: 所有批量导入用户和重置密码的用户共享相同临时密码，如果管理员未强制修改，存在未授权访问风险。

**建议**: 
- 每次批量导入/密码重置生成随机临时密码
- 在返回结果中包含临时密码并强制首次登录修改

#### H-3: 裸异常捕获（多处）
**文件**: `backend/app/services/auth_service.py:60,97,111,141,182,201`
**描述**: 多处使用 `except Exception as e` 捕获所有异常：
- `_check_login_lockout`: line 60 - Redis失败时静默返回None（fail-open）
- `_record_login_failure`: line 97 - Redis失败时静默忽略
- `_reset_login_failures`: line 111 - Redis失败时静默忽略
- `unlock_account`: line 141 - Redis解锁失败时静默继续
- `get_login_lockout_status`: line 182 - Redis失败时返回默认值
- `authenticate_certificate`: line 347 - 跳过单个用户验证失败

**风险**: 
1. Redis不可用时，登录锁定机制完全失效，攻击者可无限尝试密码
2. 证书认证中跳过异常可能掩盖安全问题

**建议**: 
- Redis不可用时应拒绝登录或记录告警
- 区分可恢复异常和不可恢复异常

#### H-4: SM4使用ECB模式（crypto.py / gmssl_adapter.py）
**文件**: `backend/app/utils/crypto.py:143,158` 和 `backend/app/core/gmssl_adapter.py:117,135`
**描述**: SM4加密使用ECB（Electronic Codebook）模式：
```python
return self._sm4.crypt_ecb(data.encode('utf-8'))
```

**风险**: ECB模式不提供语义安全性，相同明文块产生相同密文块，可能泄露数据模式。

**建议**: 使用CBC或GCM模式，需要IV（初始化向量）参数。

### 严重度: MEDIUM（中）

#### M-1: Token黑名单fail-open策略（deps.py）
**文件**: `backend/app/utils/deps.py:68-81`
**描述**: 当Redis不可用时，Token黑名单检查被跳过（fail-open）：
```python
except Exception as e:
    logger.debug(f"Redis 不可用，跳过黑名单检查: {e}")
```

**风险**: Redis故障期间，已登出的Token仍然有效。

**建议**: 
- 在生产环境中，Redis不可用时应拒绝认证
- 或使用数据库作为Token黑名单的备选方案

#### M-2: 证书认证遍历所有用户（auth_service.py）
**文件**: `backend/app/services/auth_service.py:332-348`
**描述**: `authenticate_certificate` 函数加载所有拥有SM2公钥的用户并逐一验证签名：
```python
result = await db.execute(
    select(User).where(User.sm2_public_key.isnot(None))
)
users = result.scalars().all()
for user in users:
    try:
        is_valid = gmssl_adapter.sm2_verify(...)
```

**风险**: 
1. 性能问题：用户量大时需遍历所有用户
2. 安全问题：异常被静默忽略（line 347），可能掩盖攻击

**建议**: 
- 使用证书指纹/哈希索引快速定位用户
- 记录验证失败的详细日志

#### M-3: 权限检查不一致（security.py vs deps.py）
**文件**: 
- `backend/app/core/security.py:171-177`
- `backend/app/utils/deps.py:92-105`

**描述**: 两处权限检查逻辑不一致：
- `security.py` 的 `check_permission`: admin角色直接返回True，使用交集检查
- `deps.py` 的 `require_permissions`: admin角色直接返回True，检查缺失权限

**风险**: 可能导致权限绕过或误判。

**建议**: 统一权限检查逻辑到单一位置。

#### M-4: 密钥材料生成不使用真实密码学安全随机数（key_service.py）
**文件**: `backend/app/services/key_service.py:42-54`
**描述**: `_generate_key_material` 函数生成SM2密钥时：
```python
private_key = secrets.token_hex(32)
public_key = secrets.token_hex(64)
encrypted_key = gmssl_adapter.sm3_hash(private_key)
```

**风险**: 
1. SM2密钥对不是通过密码学安全的方式生成的（未使用椭圆曲线参数）
2. 公钥是随机生成的，与私钥无数学关系
3. 使用SM3哈希作为"加密密钥"，无法恢复原始私钥

**建议**: 使用真实的SM2密钥对生成函数（`gmssl_adapter.sm2_generate_keypair()`）。

#### M-5: Shamir秘密分割使用整数运算而非有限域（key_service.py）
**文件**: `backend/app/services/key_service.py:353-391`
**描述**: `_shamir_split` 使用Python整数运算：
```python
secret_int = int.from_bytes(secret.encode("utf-8"), "big")
coefficients = [secret_int] + [secrets.randbelow(2**128) for _ in range(k - 1)]
```

**风险**: 
1. 未使用有限域运算，份额值可能非常大
2. Lagrange插值使用整数除法（`//`），可能丢失精度
3. 不是标准的Shamir秘密分割实现

**建议**: 使用大素数有限域实现标准Shamir方案。

#### M-6: 认证服务中用户名枚举风险
**文件**: `backend/app/services/auth_service.py:215-216,220-221`
**描述**: 不同错误场景返回不同错误消息：
- 用户不存在: "用户名或密码错误"
- 账号禁用: "账号已被禁用，请联系管理员"

**风险**: 攻击者可通过错误消息区分用户名是否存在和账号状态。

**建议**: 统一返回相同错误消息，不区分用户名不存在和密码错误。

#### M-7: 缺少密码复杂度验证
**文件**: `backend/app/services/user_service.py` 和 `backend/app/api/v1/auth.py`
**描述**: 创建用户和修改密码时未验证密码复杂度。

**风险**: 用户可设置弱密码（如 "123456"）。

**建议**: 添加密码复杂度验证（最小长度、大小写字母、数字、特殊字符）。

### 严重度: LOW（低）

#### L-1: 日志中可能泄露敏感信息
**文件**: `backend/app/services/auth_service.py:85,93-94`
**描述**: 
```python
logger.info(f"Login failure for user {user_id}: {count}/{MAX_LOGIN_ATTEMPTS}")
logger.warning(f"User {user_id} locked for {LOCKOUT_DURATION_MINUTES} minutes...")
```

**风险**: 用户ID直接记录在日志中。

**建议**: 日志中使用脱敏的用户标识。

#### L-2: RateLimitMiddleware内存泄漏风险
**文件**: `backend/app/middleware/__init__.py:42,81-90`
**描述**: 内存回退模式下，`_requests` 字典无大小限制：
```python
_requests: dict[str, list[float]] = {}
```

**风险**: 大量不同IP请求可能导致内存耗尽。

**建议**: 添加最大IP数量限制或使用LRU缓存。

#### L-3: 未使用的导入
**文件**: `backend/app/utils/crypto.py:7`
**描述**: `from typing import Optional` 导入但未使用。

**建议**: 清理未使用的导入。

---

## 二、安全审计发现（OWASP Top 10 分类）

### A01:2021 - 访问控制失效

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| AC-1 | admin角色硬编码为超级管理员，绕过所有权限检查 | MEDIUM | 需修复 |
| AC-2 | 密钥管理API缺少角色级权限控制 | MEDIUM | 需修复 |
| AC-3 | 解锁账户接口仅检查role=="admin"，未使用RBAC | LOW | 建议改进 |

### A02:2021 - 加密机制失效

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| CR-1 | SM4使用ECB模式，不提供语义安全 | HIGH | 需修复 |
| CR-2 | 密钥材料生成不使用真实密码学函数 | MEDIUM | 需修复 |
| CR-3 | SM3降级为SHA-256（GmSSL不可用时） | MEDIUM | 需评估 |
| CR-4 | Shamir实现非标准 | MEDIUM | 建议改进 |

### A03:2021 - 注入

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| IN-1 | SQL注入防护中间件实现完善 | GOOD | 通过 |
| IN-2 | 使用SQLAlchemy ORM，参数化查询 | GOOD | 通过 |
| IN-3 | XSS过滤中间件实现完善 | GOOD | 通过 |

### A04:2021 - 不安全设计

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| ID-1 | Redis不可用时登录锁定失效（fail-open） | HIGH | 需修复 |
| ID-2 | Token黑名单fail-open策略 | MEDIUM | 需评估 |
| ID-3 | 证书认证遍历所有用户 | MEDIUM | 需优化 |

### A05:2021 - 安全配置错误

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| SC-1 | 多个硬编码默认凭据 | HIGH | 需修复 |
| SC-2 | 调试模式默认开启（APP_DEBUG=True） | MEDIUM | 需修复 |
| SC-3 | CORS允许所有来源（unhandled_exception_handler） | MEDIUM | 需修复 |

### A06:2021 - 易受攻击和过时的组件

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| VC-1 | 依赖jose进行JWT操作 | LOW | 需评估版本 |
| VC-2 | GmSSL降级方案存在 | LOW | 需评估 |

### A07:2021 - 身份识别和认证失败

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| IA-1 | 用户名枚举风险（不同错误消息） | MEDIUM | 需修复 |
| IA-2 | 缺少密码复杂度验证 | MEDIUM | 需修复 |
| IA-3 | MFA实现完善（TOTP+备份码） | GOOD | 通过 |
| IA-4 | 登录锁定机制实现（5次/30分钟） | GOOD | 通过 |

### A08:2021 - 软件和数据完整性故障

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| SI-1 | JWT使用HS256对称算法 | LOW | 建议使用RS256 |
| SI-2 | CSRF防护中间件实现 | GOOD | 通过 |

### A09:2021 - 安全日志和监控失败

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| LM-1 | 审计日志中间件记录API调用 | GOOD | 通过 |
| LM-2 | SQL注入攻击日志记录完善 | GOOD | 通过 |
| LM-3 | 日志中可能泄露用户ID | LOW | 建议改进 |

### A10:2021 - 服务端请求伪造(SSRF)

| 编号 | 发现 | 严重度 | 状态 |
|------|------|--------|------|
| SR-1 | 未发现直接SSRF风险 | GOOD | 通过 |

---

## 三、STRIDE威胁模型分析

### 仿冒（Spoofing）
- **威胁**: JWT Token伪造、DID身份伪造
- **现有防护**: JWT签名验证、SM2签名验证、MFA
- **风险点**: JWT密钥默认值风险、Redis不可用时Token黑名单失效

### 篡改（Tampering）
- **威胁**: 数据篡改、请求参数篡改
- **现有防护**: SQL注入防护、XSS过滤、CSRF防护
- **风险点**: SM4 ECB模式可能泄露数据模式

### 抵赖（Repudiation）
- **威胁**: 用户否认操作
- **现有防护**: 审计日志、区块链存证
- **风险点**: 日志中用户标识未脱敏

### 信息泄露（Information Disclosure）
- **威胁**: 敏感数据泄露
- **现有防护**: 密码哈希存储、安全响应头
- **风险点**: 硬编码凭据、日志泄露用户ID

### 拒绝服务（Denial of Service）
- **威胁**: 服务不可用
- **现有防护**: 速率限制中间件、登录锁定
- **风险点**: RateLimitMiddleware内存泄漏、Redis不可用时锁定失效

### 权限提升（Elevation of Privilege）
- **威胁**: 越权访问
- **现有防护**: RBAC权限检查、角色验证
- **风险点**: admin角色硬编码绕过、权限检查不一致

---

## 四、QA测试结果

### 4.1 认证流程测试用例

| 测试ID | 测试项 | 预期结果 | 状态 |
|--------|--------|----------|------|
| AUTH-01 | 密码登录（正确凭据） | 返回Token对 | 待执行 |
| AUTH-02 | 密码登录（错误密码） | 返回"用户名或密码错误" | 待执行 |
| AUTH-03 | 密码登录（不存在用户） | 返回"用户名或密码错误" | 待执行 |
| AUTH-04 | 5次失败后锁定 | 返回"账号已锁定" | 待执行 |
| AUTH-05 | DID登录（有效签名） | 返回Token对 | 待执行 |
| AUTH-06 | DID登录（无效签名） | 返回"签名验证失败" | 待执行 |
| AUTH-07 | MFA验证（正确TOTP） | 返回Token对 | 待执行 |
| AUTH-08 | MFA验证（错误TOTP） | 返回"验证码错误" | 待执行 |
| AUTH-09 | Token刷新 | 返回新Token对 | 待执行 |
| AUTH-10 | 登出 | Token加入黑名单 | 待执行 |
| AUTH-11 | 使用已登出Token | 返回"令牌已被撤销" | 待执行 |

### 4.2 用户管理测试用例

| 测试ID | 测试项 | 预期结果 | 状态 |
|--------|--------|----------|------|
| USER-01 | 创建用户（有效数据） | 返回用户信息 | 待执行 |
| USER-02 | 创建用户（重复用户名） | 返回"用户名已存在" | 待执行 |
| USER-03 | 创建用户（无效角色） | 返回"无效角色" | 待执行 |
| USER-04 | 修改用户角色 | 返回更新后信息 | 待执行 |
| USER-05 | 禁用用户 | 状态变为inactive | 待执行 |
| USER-06 | 重置密码 | 返回重置结果 | 待执行 |
| USER-07 | 批量导入用户 | 返回导入统计 | 待执行 |

### 4.3 权限控制测试用例

| 测试ID | 测试项 | 预期结果 | 状态 |
|--------|--------|----------|------|
| PERM-01 | admin访问管理接口 | 允许 | 待执行 |
| PERM-02 | 普通用户访问管理接口 | 返回403 | 待执行 |
| PERM-03 | 用户查询他人锁定状态 | 返回403 | 待执行 |
| PERM-04 | 用户查询自己锁定状态 | 允许 | 待执行 |
| PERM-05 | 非admin解锁账户 | 返回403 | 待执行 |

### 4.4 密钥管理测试用例

| 测试ID | 测试项 | 预期结果 | 状态 |
|--------|--------|----------|------|
| KEY-01 | 生成SM2密钥 | 返回key_id | 待执行 |
| KEY-02 | 生成SM4密钥 | 返回key_id | 待执行 |
| KEY-03 | 轮换密钥 | 旧密钥rotated，新密钥active | 待执行 |
| KEY-04 | Shamir分割 | 返回份额列表 | 待执行 |
| KEY-05 | Shamir恢复 | 恢复原始秘密 | 待执行 |

---

## 五、性能检查

### 5.1 N+1查询问题

| 位置 | 问题 | 建议 |
|------|------|------|
| `auth_service.py:332-348` | 证书认证遍历所有用户 | 使用索引快速定位 |
| `user_service.py:330-335` | 批量导入逐行检查用户名唯一性 | 使用批量查询或数据库唯一约束 |

### 5.2 缺失索引

| 表 | 列 | 建议 |
|------|------|------|
| users | email | 已有唯一约束（隐式索引） |
| users | role | 建议添加索引 |
| key_store | key_id | 已有索引 |
| mfa_configs | user_id | 建议添加索引 |

### 5.3 内存泄漏风险

| 位置 | 问题 | 建议 |
|------|------|------|
| `middleware/__init__.py:42` | RateLimitMiddleware._requests无大小限制 | 添加LRU缓存或最大条目数 |

---

## 六、改进建议（按优先级排序）

### P0 - 立即修复（安全关键）

1. **修复Redis fail-open安全风险**
   - Redis不可用时，登录锁定机制应拒绝登录而非放行
   - Token黑名单应有备选方案（数据库）

2. **消除硬编码默认凭据**
   - 为所有敏感配置添加生产环境验证
   - 启动时强制检查安全配置

3. **修复SM4 ECB模式**
   - 改用CBC或GCM模式
   - 需要IV参数管理

4. **修复用户名枚举漏洞**
   - 统一所有认证失败的错误消息

### P1 - 高优先级

5. **添加密码复杂度验证**
   - 最小8字符
   - 包含大小写字母、数字、特殊字符

6. **修复密钥材料生成**
   - 使用真实的SM2密钥对生成函数
   - 修复Shamir秘密分割实现

7. **优化证书认证性能**
   - 使用证书哈希索引
   - 添加验证失败日志

### P2 - 中优先级

8. **统一权限检查逻辑**
   - 将权限检查集中在deps.py
   - 消除重复实现

9. **改进日志安全**
   - 日志中脱敏用户标识
   - 避免记录敏感信息

10. **修复RateLimitMiddleware内存问题**
    - 添加最大条目数限制
    - 使用LRU缓存

### P3 - 低优先级

11. **清理未使用的导入**
12. **考虑JWT算法升级（HS256→RS256）**
13. **添加API版本控制**

---

## 七、安全架构建议

### 7.1 密钥管理改进
```
当前: 密钥材料 = random + SM3_hash(random)
建议: 使用HSM或KMS管理密钥生命周期
```

### 7.2 认证架构改进
```
当前: Redis fail-open（Redis故障时认证降级）
建议: Redis + 数据库双写，Redis故障时使用数据库验证
```

### 7.3 密码存储改进
```
当前: SM3(salt + password)
建议: Argon2id 或 bcrypt（考虑GPU攻击防护）
```

---

## 八、合规性检查

### 8.1 国密合规
- [x] SM2签名/验签实现
- [x] SM3哈希实现
- [x] SM4加密实现（需修复ECB模式）
- [x] SM9标识密码实现
- [x] ZUC流密码实现

### 8.2 数据安全
- [x] 密码哈希存储
- [x] 敏感配置外部化
- [ ] 数据脱敏（部分缺失）
- [ ] 传输加密（需检查TLS配置）

---

## 九、总结

### 安全评分: 72/100

| 类别 | 得分 | 说明 |
|------|------|------|
| 认证安全 | 80 | MFA实现完善，但fail-open策略需修复 |
| 授权安全 | 70 | RBAC实现基本完整，admin硬编码需改进 |
| 数据安全 | 65 | SM4 ECB模式需修复，密码存储需加强 |
| 输入验证 | 90 | SQL注入和XSS防护完善 |
| 会话管理 | 75 | Token管理基本安全，黑名单策略需改进 |
| 密码学 | 60 | 国密实现基本完整，但密钥生成需改进 |
| 日志监控 | 80 | 审计日志完善，但需改进脱敏 |

### 关键发现统计
- **HIGH**: 4项
- **MEDIUM**: 7项
- **LOW**: 6项
- **GOOD**: 10项（安全实践）

### 建议修复时间线
- **P0（本周）**: 4项安全关键修复
- **P1（2周内）**: 3项高优先级修复
- **P2（1月内）**: 3项中优先级改进
- **P3（季度内）**: 3项低优先级优化

---

**审计人**: security-qa-engineer
**审核状态**: 待team-lead审核
**下次审计建议**: 修复P0项后进行复审
