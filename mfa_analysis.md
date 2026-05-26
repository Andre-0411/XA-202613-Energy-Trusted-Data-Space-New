# 能源可信数据空间 — MFA 功能项目现状分析报告

> 分析时间：2026-05-26  
> 项目路径：`D:\XA-202613-Energy-Trusted-Data-Space-New`

---

## 1. 项目整体技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **后端框架** | FastAPI | ≥ 0.115.0 |
| **Python** | CPython | ≥ 3.12 |
| **ORM** | SQLAlchemy (async) | ≥ 2.0.36 |
| **数据库** | PostgreSQL (asyncpg) | — |
| **缓存** | Redis (hiredis) | ≥ 5.2.0 |
| **JWT** | python-jose | HS256 |
| **密码哈希** | 自研 SM3（国密） | — |
| **TOTP / MFA** | pyotp（依赖中声明，实际为自研实现） | ≥ 2.9.0 |
| **QR 码生成** | qrcode[pil] | ≥ 7.4.2 |
| **前端框架** | React 18 + TypeScript | 18.3.1 |
| **前端构建** | Vite | ≥ 5.4.11 |
| **前端 UI** | TDesign React | ≥ 1.17.0 |
| **前端状态** | Zustand | ≥ 4.5.5 |
| **前端请求** | Axios + TanStack Query | — |
| **区块链** | FISCO BCOS（国密 SM2/SM3） | — |
| **容器化** | Docker + docker-compose | — |

---

## 2. 项目目录结构

```
D:\XA-202613-Energy-Trusted-Data-Space-New\
├── backend\
│   ├── app\
│   │   ├── api\v1\              # 所有 API 路由（auth.py, auth_mfa.py, ...）
│   │   ├── core\                 # 安全工具（security.py: JWT/SM3/CSRF）
│   │   ├── models\               # SQLAlchemy 模型（user.py, mfa_model.py）
│   │   ├── schemas\              # Pydantic Schema（auth.py, mfa.py）
│   │   ├── services\             # 业务逻辑（auth_service.py, mfa_service.py）
│   │   ├── middleware.py         # 安全头/CSRF/限流/审计/XSS/SQL注入防护
│   │   ├── database.py          # 异步 PostgreSQL + Redis 连接
│   │   ├── config.py            # Pydantic Settings 配置类
│   │   └── utils\deps.py       # FastAPI 依赖注入
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend\
│   ├── src\
│   │   ├── api\auth.ts         # 认证 API 封装
│   │   ├── stores\authStore.ts # Zustand 认证状态管理
│   │   ├── pages\auth\         # 登录页面
│   │   └── types\api.ts        # 前端类型定义
│   ├── package.json
│   └── vite.config.ts
├── contracts\                    # 区块链智能合约（Solidity）
├── deploy\                       # Docker/Nginx/Prometheus/Grafana
└── docs\                        # 架构/需求文档
```

---

## 3. 现有认证体系分析

### 3.1 认证方式

系统支持三种登录方式：

| 方式 | 端点 | 说明 |
|------|------|------|
| **用户名+密码** | `POST /api/v1/auth/login` (`auth_type=password`) | SM3 加盐哈希 |
| **DID 签名** | `POST /api/v1/auth/login/did` | SM2 公钥验证 |
| **SM2 证书** | `POST /api/v1/auth/login/certificate` | 证书公钥验证 |

### 3.2 JWT 令牌机制

- **Access Token**：默认 60 分钟过期
- **Refresh Token**：默认 7 天过期
- **Token 黑名单**：登出时写入 Redis（`token:blacklist:{token}`）
- **Payload 字段**：`sub` / `username` / `role` / `permissions` / `organization_id` / `jti` / `type`

### 3.3 登录锁定机制

- 失败计数存储在 **Redis**（`login_fail:{user_id}`，TTL=30分钟）
- 连续失败 **5 次**后锁定 **30 分钟**（`login_lockout:{user_id}`）
- 同时同步写入 `users.login_fail_count` 和 `users.locked_until` 字段

### 3.4 中间件安全链

```
请求 → CORS → 安全响应头 → CSRF → 限流 → 审计日志 → SQL注入防护 → XSS过滤 → 路由处理
```

- **CSRF**：双重提交 Cookie 模式
- **限流**：Redis 滑动窗口，登录接口 10 次/分钟
- **审计日志**：所有 API 请求记录 method/path/status_code/duration/client_ip

---

## 4. MFA 功能现状（核心发现）

### 4.1 已完整实现的功能

| 功能 | 后端 | 前端 |
|------|------|------|
| TOTP 密钥生成（Base32） | ✅ `mfa_service.py:setup_mfa` | — |
| TOTP URI 生成（`otpauth://totp/...`） | ✅ `mfa_service.py` | — |
| QR 码图片生成（PNG） | ✅ `auth_mfa.py:/mfa/qr-code` | — |
| TOTP 验证（含时间窗口） | ✅ `_verify_totp`（±1 窗口） | ✅ `LoginForm.tsx` |
| 备份码生成（10 个，`XXXX-XXXX` 格式） | ✅ `_generate_backup_codes` | — |
| 备份码验证（SHA256 哈希比对） | ✅ `verify_backup_code` | ✅ `LoginForm.tsx` |
| MFA 启用/禁用 | ✅ `/mfa/enable`, `/mfa/disable` | — |
| MFA 状态查询 | ✅ `/mfa/status/{user_id}` | — |
| 登录时 MFA 二次验证 | ✅ `auth_service.py:verify_mfa` | ✅ 自动弹出二次验证界面 |
| `mfa_required` 控制登录流程 | ✅ `_generate_tokens` 查 `mfa_configs` | ✅ `authStore.ts` |

### 4.2 数据库模型

已创建三张表：

**mfa_configs（MfaConfig）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | String (unique) | 用户 ID |
| secret | String | TOTP 密钥 |
| method | String | 默认 "totp" |
| enabled | Boolean | 是否启用 |
| last_verified_at | DateTime | 最后验证时间 |

**mfa_backup_codes（MfaBackupCode）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| mfa_config_id | FK → mfa_configs.id | 关联 MFA 配置 |
| code_hash | String | SHA256 哈希 |
| used | Boolean | 是否已使用 |
| used_at | DateTime | 使用时间 |

**mfa_sessions（MfaSession）**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| mfa_config_id | FK → mfa_configs.id | 关联 MFA 配置 |
| session_id | String (unique) | 会话 ID |
| verified | Boolean | 是否已验证 |
| verified_at | DateTime | 验证时间 |
| expires_at | DateTime | 过期时间 |

> **注意**：`users` 表也有 `mfa_secret` 和 `mfa_enabled` 字段，这是**旧架构遗留字段**。新架构已迁移到独立的 `mfa_configs` 表。

### 4.3 后端 API 端点汇总

| 方法 | 路径 | 说明 | 认证要求 |
|------|------|------|----------|
| POST | `/api/v1/auth/login` | 登录（密码/DID/证书） | 无需 |
| POST | `/api/v1/auth/mfa/verify` | MFA 二次验证（返回 Token） | 无需 |
| POST | `/api/v1/auth/mfa/setup` | 生成 TOTP 密钥/QR URI/备份码 | 需认证 |
| POST | `/api/v1/auth/mfa/enable` | 启用 MFA | 需认证 |
| POST | `/api/v1/auth/mfa/disable` | 禁用 MFA | 需认证 |
| GET | `/api/v1/auth/mfa/status` | 获取当前用户 MFA 状态 | 需认证 |
| GET | `/api/v1/auth/mfa/status/{user_id}` | 获取指定用户 MFA 状态 | 需认证 |
| POST | `/api/v1/auth/mfa/backup-codes/verify` | 备份码验证 | 需认证 |
| POST | `/api/v1/auth/mfa/backup-codes/regenerate` | 重新生成备份码 | 需认证 ⚠️ |
| GET | `/api/v1/auth/mfa/qr-code?uri=...` | 生成 QR 码图片（PNG） | 无需 |

### 4.4 前端登录流程（MFA 部分）

```
用户提交登录 → authStore.login()
  ↓
  if (result.mfaRequired)
    → setShowMfa(true)
    → 渲染 MFA 二次验证界面（TOTP 或备份码）
    → 调用 mfaVerify()
      ↓
      if (验证成功 && 有 access_token)
        → navigate('/dashboard')
```

前端 `authStore.ts` 关键状态：
- `mfaRequired: boolean` — 是否需要 MFA
- `mfaVerified: boolean` — MFA 是否已验证
- `mfaSessionId: string | null` — MFA 会话 ID

---

## 5. 发现的潜在问题

### 5.1 数据库字段冗余

- `users` 表有 `mfa_secret` 和 `mfa_enabled` 字段
- 新架构使用独立 `mfa_configs` 表
- **建议**：确认 Alembic 迁移是否已清理旧字段

### 5.2 备份码重新生成端点权限

`auth_mfa.py` 中 `POST /mfa/backup-codes/regenerate` 从请求参数接受 `user_id`，任何已认证用户可为任意用户重新生成备份码。应改为从 `get_current_user` 获取身份。

### 5.3 TOTP 实现为自研，非 pyotp 库

`requirements.txt` 声明了 `pyotp>=2.9.0`，但 `mfa_service.py` 是手写的完整 TOTP 实现。若自研已通过测试，可移除 `pyotp` 依赖避免误导。

### 5.4 MFA 会话过期时间

`mfa:pending:{user.id}` 的 Redis TTL 和 `MfaSession.expires_at` 均为 **5 分钟**。用户停留超过 5 分钟时 token 会失效，需重新登录。

---

## 6. 与 Google Authenticator 的兼容性

当前 TOTP 配置：

- **算法**：HMAC-SHA1（标准）
- **时间窗口**：30 秒
- **验证码位数**：6 位
- **TOTP URI**：`otpauth://totp/{issuer}:{username}?secret={secret}&issuer=EnergyDataSpace&algorithm=SHA1&digits=6&period=30`

**完全兼容 Google Authenticator / Microsoft Authenticator / Authy**。

---

## 7. 总结

| 维度 | 现状 |
|------|------|
| MFA 后端服务 | ✅ 完整实现（TOTP + 备份码） |
| MFA 前端界面 | ✅ 登录二次验证界面已实现 |
| QR 码生成 | ✅ 后端 API 已实现 |
| 数据库模型 | ✅ 三张表已定义 |
| 登录集成 | ✅ `mfa_required` 已集成 |
| 依赖完整性 | ⚠️ `pyotp` 声明但未使用；`qrcode[pil]` 已在依赖中 |
| 权限校验 | ⚠️ 备份码重新生成端点需修复 |
| 前端管理页面 | ⚠️ MFA 设置/启用/禁用/查看备份码页面缺失 |

**结论**：项目的 MFA 功能**主体已完整实现**。主要剩余工作：
1. 修复 `auth_mfa.py` 中备份码重新生成端点权限校验
2. 确认 Alembic 迁移是否已执行
3. 清理 `users` 表中 `mfa_secret`/`mfa_enabled` 冗余字段
4. 前端补充 MFA 管理页面（设置/启用/禁用/查看备份码）