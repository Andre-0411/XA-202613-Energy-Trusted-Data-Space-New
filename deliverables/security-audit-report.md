# 能源可信数据空间系统 - 安全审计报告

**审计日期**: 2026-05-21
**审计范围**: 后端 (backend/)、前端 (frontend/)、配置文件、Docker 部署
**审计标准**: OWASP Top 10 (2021)、中国网络安全等级保护相关要求

---

## 一、高危问题 (P0) - 必须立即修复

### P0-1: 真实 API 密钥硬编码在代码库中

**严重程度**: 高危
**OWASP 分类**: A02:2021 - 加密失败

**问题描述**:
`.env` 文件中包含真实的 DeepSeek API 密钥，且该文件虽在 `.gitignore` 中但已存在于仓库中。`backend/.env` 也包含真实密钥。

**涉及文件**:
- `.env:78` - `DEEPSEEK_API_KEY=sk-7c620905990d48b6a8fb44f598c2b902`
- `backend/.env:2` - 同一密钥

**影响范围**:
- API 密钥泄露可导致未授权访问 DeepSeek AI 服务
- 可能产生经济损失和数据泄露

**修复建议**:
1. **立即轮换** DeepSeek API 密钥
2. 将 `.env` 和 `backend/.env` 从 Git 历史中清除（使用 `git filter-branch` 或 BFG）
3. 使用环境变量或密钥管理服务（如 HashiCorp Vault）管理敏感配置
4. 在 CI/CD 中使用 Secret 管理功能

---

### P0-2: 弱密码哈希算法 - 使用 SM3 替代 bcrypt/argon2

**严重程度**: 高危
**OWASP 分类**: A02:2021 - 加密失败

**问题描述**:
密码哈希使用 SM3 + salt 方式，而非专用密码哈希算法（bcrypt、argon2、scrypt）。SM3 是通用哈希函数，缺乏密钥拉伸（key stretching），容易遭受暴力破解攻击。

**涉及文件**:
- `backend/app/core/security.py:107-121` - `hash_password` 函数
- `backend/app/core/security.py:124-140` - `verify_password` 函数
- `backend/app/utils/crypto.py:162-188` - `password_hash` 和 `verify_password`

**影响范围**:
- 密码数据库泄露后，攻击者可快速暴力破解密码
- 不符合行业安全标准

**修复建议**:
```python
# 推荐使用 argon2 或 bcrypt
# pip install argon2-cffi 或 pip install bcrypt

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,        # 迭代次数
    memory_cost=65536,  # 内存使用 64MB
    parallelism=4,      # 并行度
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return ph.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
```

**注意**: 需要制定密码迁移策略，支持新旧哈希格式共存。

---

### P0-3: JWT 密钥弱且可预测

**严重程度**: 高危
**OWASP 分类**: A02:2021 - 加密失败

**问题描述**:
JWT 密钥使用可预测的模式字符串，且生产环境验证器被禁用。

**涉及文件**:
- `.env:58` - `JWT_SECRET_KEY=energy-jwt-secret-2026-change-in-production`
- `backend/app/config.py:191-195` - `validate_secret_not_default` 验证器被注释

```python
@field_validator("APP_SECRET_KEY", "JWT_SECRET_KEY")
@classmethod
def validate_secret_not_default(cls, v: str) -> str:
    """生产环境禁止使用默认密钥"""
    return v  # 直接返回，未做任何验证！
```

**影响范围**:
- 攻击者可伪造任意 JWT Token
- 可冒充任何用户身份

**修复建议**:
1. 生成强随机密钥：`openssl rand -base64 64`
2. 启用生产环境验证器：

```python
@field_validator("APP_SECRET_KEY", "JWT_SECRET_KEY")
@classmethod
def validate_secret_not_default(cls, v: str) -> str:
    default_secrets = {
        "change-me-to-a-random-secret-key",
        "change-me-jwt-secret-key",
        "energy-trusted-data-space-secret-key-2026",
        "energy-jwt-secret-2026-change-in-production",
    }
    if settings.APP_ENV == "production" and v in default_secrets:
        raise ValueError("生产环境必须修改默认密钥！")
    if len(v) < 32:
        raise ValueError("密钥长度不得少于 32 字符")
    return v
```

---

### P0-4: 数据库 SQL 日志泄露敏感数据

**严重程度**: 高危
**OWASP 分类**: A09:2021 - 安全日志和监控失败

**问题描述**:
数据库引擎启用 `echo=settings.APP_DEBUG`，当 `APP_DEBUG=true` 时会将所有 SQL 语句（包含密码、Token 等敏感数据）输出到日志。

**涉及文件**:
- `backend/app/database.py:43` - `echo=settings.APP_DEBUG`
- `.env:6` - `APP_DEBUG=true`

**影响范围**:
- 日志中可能包含用户密码、Token、个人数据
- 违反数据保护法规

**修复建议**:
```python
# database.py
async_engine = create_async_engine(
    settings.postgres_url,
    echo=False,  # 生产环境必须关闭
    # 或者使用自定义 logger，过滤敏感信息
    echo_pool=settings.APP_DEBUG and settings.APP_ENV != "production",
)
```

---

### P0-5: 前端 Token 存储在 localStorage - XSS 风险

**严重程度**: 高危
**OWASP 分类**: A03:2021 - 注入（XSS）

**问题描述**:
JWT Token 存储在 `localStorage` 中，容易遭受 XSS 攻击。任何 XSS 漏洞都可导致 Token 被窃取。

**涉及文件**:
- `frontend/src/api/request.ts:8-9` - Token 键名定义
- `frontend/src/api/request.ts:24` - 从 localStorage 读取 Token
- `frontend/src/stores/authStore.ts:122` - 从 localStorage 读取

**影响范围**:
- XSS 攻击可窃取用户 Token
- 攻击者可冒充用户身份

**修复建议**:
1. **短期**: 将 Token 迁移到 `httpOnly` + `Secure` + `SameSite=Strict` Cookie
2. **长期**: 实现后端 Cookie-based 认证

```typescript
// 后端设置 Cookie
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # 仅 HTTPS
    samesite="strict",
    max_age=3600,
)
```

---

### P0-6: 文件上传无安全验证

**严重程度**: 高危
**OWASP 分类**: A03:2021 - 注入

**问题描述**:
批量用户导入端点接受 `UploadFile` 但未验证文件类型、大小或内容。

**涉及文件**:
- `backend/app/api/v1/ops_user.py:92-106` - `batch_import_users` 端点

```python
@router.post("/import", response_model=ApiResponse)
async def batch_import_users(
    file: UploadFile = File(..., description="Excel 文件"),
    # 无文件类型检查、无大小限制
):
    file_content = await file.read()  # 读取全部内容到内存
```

**影响范围**:
- 恶意文件上传可能导致远程代码执行
- 大文件上传可能导致 DoS（内存耗尽）

**修复建议**:
```python
from fastapi import UploadFile, File, HTTPException

ALLOWED_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/import")
async def batch_import_users(
    file: UploadFile = File(..., description="Excel 文件"),
    ...
):
    # 验证文件类型
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "仅支持 Excel 文件格式")

    # 验证文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件大小不能超过 10MB")

    # 验证文件扩展名
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "文件扩展名不合法")
```

---

### P0-7: 证书认证遍历所有用户 - 性能和安全风险

**严重程度**: 高危
**OWASP 分类**: A04:2021 - 不安全的设计

**问题描述**:
`authenticate_certificate` 函数加载所有拥有 SM2 公钥的用户，逐个尝试验证签名。这既是性能问题，也是安全风险。

**涉及文件**:
- `backend/app/services/auth_service.py:98-126` - `authenticate_certificate`

```python
# 加载所有用户
result = await db.execute(
    select(User).where(User.sm2_public_key.isnot(None))
)
users = result.scalars().all()  # 可能加载数千用户

for user in users:
    try:
        is_valid = gmssl_adapter.sm2_verify(user.sm2_public_key, challenge, signature)
        if is_valid:
            return await _generate_tokens(user)
    except Exception:
        continue  # 吞掉所有异常
```

**影响范围**:
- 数据库用户量增长后，性能严重下降
- 异常被静默吞掉，可能导致安全绕过

**修复建议**:
1. 从证书中提取公钥哈希或 Subject，用索引查询用户
2. 限制查询结果数量
3. 不要吞掉异常

---

### P0-8: 生产环境启用调试模式

**严重程度**: 高危
**OWASP 分类**: A05:2021 - 安全配置错误

**问题描述**:
`.env` 文件中 `APP_DEBUG=true`，且配置类默认值也为 `True`。

**涉及文件**:
- `.env:6` - `APP_DEBUG=true`
- `backend/app/config.py:24` - 默认值 `True`

**影响范围**:
- 暴露详细错误信息和堆栈跟踪
- SQL 查询日志泄露
- 可能暴露内部 API 文档

**修复建议**:
```python
# config.py - 修改默认值
APP_DEBUG: bool = Field(default=False, description="调试模式")
```

---

### P0-9: 配置验证器未实际执行验证

**严重程度**: 高危
**OWASP 分类**: A05:2021 - 安全配置错误

**问题描述**:
`validate_secret_not_default` 验证器直接返回输入值，未做任何验证。

**涉及文件**:
- `backend/app/config.py:191-195`

```python
@field_validator("APP_SECRET_KEY", "JWT_SECRET_KEY")
@classmethod
def validate_secret_not_default(cls, v: str) -> str:
    """生产环境禁止使用默认密钥"""
    return v  # BUG: 未做任何验证！
```

**影响范围**:
- 生产环境可使用默认弱密钥
- 安全防线形同虚设

**修复建议**:
参见 P0-3 中的验证器实现。

---

### P0-10: CORS 开发模式允许所有来源

**严重程度**: 高危
**OWASP 分类**: A05:2021 - 安全配置错误

**问题描述**:
开发模式下 CORS 允许所有来源 (`*`)，配合 `allow_credentials=True` 存在安全风险。

**涉及文件**:
- `backend/app/main.py:75-85`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [...],
    allow_credentials=True,  # 与 * 一起使用不安全
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**修复建议**:
```python
# 开发环境也应明确指定允许的来源
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

### P0-11: WebSocket Token 通过 URL 参数传递

**严重程度**: 高危
**OWASP 分类**: A02:2021 - 加密失败

**问题描述**:
WebSocket 认证 Token 通过 URL 查询参数传递，可能被服务器日志、代理日志、浏览器历史记录记录。

**涉及文件**:
- `backend/app/main.py:149-182` - WebSocket 端点

```
ws://host/ws/notifications?token=xxx
```

**修复建议**:
1. 使用 WebSocket 子协议传递 Token
2. 或在连接建立后通过首条消息发送 Token

---

## 二、中危问题 (P1) - 应该修复

### P1-1: 限流中间件使用内存存储

**问题描述**:
`RateLimitMiddleware` 使用内存字典存储请求记录，不支持多实例部署，且无内存清理机制。

**涉及文件**:
- `backend/app/middleware/__init__.py:26-53`

**修复建议**:
使用 Redis 实现分布式限流：

```python
async def check_rate_limit(redis, client_ip: str, limit: int = 100, window: int = 60):
    key = f"rate_limit:{client_ip}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window)
    return current <= limit
```

---

### P1-2: MFA 验证缺少速率限制

**问题描述**:
MFA 验证端点无独立的速率限制，攻击者可无限尝试验证码。

**涉及文件**:
- `backend/app/services/auth_service.py:129-151`

**修复建议**:
```python
# 添加 MFA 尝试次数限制
MAX_MFA_ATTEMPTS = 5
MFA_LOCKOUT_SECONDS = 300

async def verify_mfa(db, user_id, code):
    redis = await _get_redis()
    attempts_key = f"mfa:attempts:{user_id}"
    attempts = await redis.get(attempts_key)

    if attempts and int(attempts) >= MAX_MFA_ATTEMPTS:
        raise AuthenticationError("MFA 验证次数过多，请稍后再试")

    # ... 验证逻辑 ...

    if not expected_code or expected_code != code:
        await redis.incr(attempts_key)
        await redis.expire(attempts_key, MFA_LOCKOUT_SECONDS)
        raise AuthenticationError("MFA 验证码错误")

    # 成功后清除计数
    await redis.delete(attempts_key)
```

---

### P1-3: Refresh Token 无轮换机制

**问题描述**:
Refresh Token 使用后未失效，可被重复使用。如果 Token 泄露，攻击者可持续获取新的 Access Token。

**涉及文件**:
- `backend/app/services/auth_service.py:154-178`

**修复建议**:
1. 每次使用 Refresh Token 后，生成新的 Refresh Token 并使旧的失效
2. 在 Redis 中存储 Refresh Token 关联的 JTI，使用后删除

---

### P1-4: SM4 使用 ECB 模式

**问题描述**:
SM4 加密使用 ECB 模式，相同明文产生相同密文，存在模式泄露风险。

**涉及文件**:
- `backend/app/utils/crypto.py:129-159`

**修复建议**:
使用 CBC 或 GCM 模式，并为每次加密生成随机 IV。

---

### P1-5: 数据库端口暴露到主机

**问题描述**:
Docker Compose 中 PostgreSQL (5432)、Redis (6379)、MongoDB (27017)、RabbitMQ (5672/15672) 等端口全部暴露到主机。

**涉及文件**:
- `docker-compose.yml` - 多个服务的 `ports` 配置

**修复建议**:
1. 生产环境移除端口映射，仅通过 Docker 内部网络访问
2. 如需外部访问，限制绑定地址为 `127.0.0.1`

```yaml
ports:
  - "127.0.0.1:5432:5432"  # 仅本地访问
```

---

### P1-6: 无密码复杂度验证

**问题描述**:
修改密码接口不验证密码复杂度。

**涉及文件**:
- `backend/app/services/auth_service.py:181-205`

**修复建议**:
```python
import re

def validate_password_strength(password: str) -> bool:
    """验证密码强度"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True
```

---

### P1-7: 前端错误信息可能泄露技术细节

**问题描述**:
部分错误处理返回了技术性错误信息，可能泄露内部实现细节。

**涉及文件**:
- `frontend/src/api/request.ts:115` - `"服务器内部错误"`
- `backend/app/exceptions.py:296-309` - 未处理异常返回详细信息

**修复建议**:
- 生产环境仅返回通用错误信息
- 详细错误记录到日志

---

### P1-8: MinIO 未启用 SSL

**问题描述**:
MinIO 配置 `MINIO_USE_SSL=false`，数据传输未加密。

**涉及文件**:
- `.env:36` - `MINIO_USE_SSL=false`

**修复建议**:
生产环境启用 SSL。

---

### P1-9: Docker 镜像版本未固定

**问题描述**:
部分 Docker 镜像使用 `latest` 标签，可能导致不可预期的版本变更。

**涉及文件**:
- `docker-compose.yml:82` - `minio/minio:latest`
- `docker-compose.yml:383` - `prom/prometheus:latest`
- `docker-compose.yml:399` - `grafana/grafana:latest`

**修复建议**:
固定镜像版本，如 `minio/minio:RELEASE.2026-05-01T00-00-00Z`。

---

### P1-10: 无请求体大小限制

**问题描述**:
未设置请求体大小限制，可能导致 DoS 攻击。

**修复建议**:
```python
from starlette.middleware.base import BaseHTTPMiddleware

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_SIZE:
            return JSONResponse(
                status_code=413,
                content={"code": 413, "message": "请求体过大"}
            )
        return await call_next(request)
```

---

## 三、低危问题 (P2) - 建议修复

### P2-1: WebSocket 未验证频道名称

**问题描述**:
客户端可订阅任意频道名称，可能订阅到未授权的频道。

**修复建议**:
限制允许的频道列表。

---

### P2-2: 健康检查端点暴露环境信息

**问题描述**:
`/health` 端点返回 `environment` 字段，可能泄露部署环境信息。

**涉及文件**:
- `backend/app/main.py:110-126`

---

### P2-3: Swagger/ReDoc 文档端点生产环境未禁用

**问题描述**:
`/docs`、`/redoc`、`/openapi.json` 在所有环境都可访问。

**涉及文件**:
- `backend/app/main.py:62-70`

**修复建议**:
```python
app = FastAPI(
    docs_url="/docs" if settings.APP_DEBUG else None,
    redoc_url="/redoc" if settings.APP_DEBUG else None,
    openapi_url="/openapi.json" if settings.APP_DEBUG else None,
)
```

---

### P2-4: AuditLogMiddleware 未记录请求体

**问题描述**:
审计日志中间件仅记录请求方法、路径和响应码，未记录关键操作的请求参数。

---

### P2-5: 前端 CSRF 防护缺失

**问题描述**:
后端有 CSRF Token 生成函数，但前端未使用。

---

## 四、安全加固建议

### 4.1 输入验证增强

1. **实现全局请求验证**: 使用 Pydantic 模型验证所有输入
2. **文件上传白名单**: 严格限制文件类型和大小
3. **参数化查询**: 确保所有数据库查询使用参数化（SQLAlchemy 已支持）
4. **输出编码**: 前端对所有用户输入进行 HTML 转义

### 4.2 认证机制增强

1. **实施密码策略**:
   - 最小长度 12 字符
   - 复杂度要求（大小写+数字+特殊字符）
   - 密码历史检查（禁止重复使用最近 5 个密码）

2. **会话管理**:
   - 实现 Refresh Token 轮换
   - 绑定 Token 到 IP/User-Agent
   - 实现并发会话限制

3. **MFA 增强**:
   - 添加 MFA 尝试速率限制
   - 实现备份码机制
   - 支持多种 MFA 方式

### 4.3 日志和监控增强

1. **结构化日志**: 使用 JSON 格式，便于分析
2. **敏感信息脱敏**: 自动过滤密码、Token、密钥
3. **安全事件告警**: 检测到异常登录、暴力破解时发送告警
4. **审计日志完整性**: 使用区块链存证保护审计日志

### 4.4 数据加密增强

1. **传输加密**: 强制 HTTPS，配置 HSTS
2. **静态加密**: 数据库字段级加密敏感数据
3. **密钥管理**: 使用专用密钥管理服务
4. **国密合规**:
   - SM3 仅用于哈希，不用于密码哈希
   - SM4 使用 CBC/GCM 模式
   - SM2 使用标准证书格式

### 4.5 部署安全

1. **最小权限原则**: 容器使用非 root 用户（已实现）
2. **网络隔离**: 内部服务不暴露端口（已部分实现）
3. **镜像安全**: 固定版本，定期扫描漏洞
4. **密钥管理**: 使用 Docker Secrets 或环境变量注入

---

## 五、安全检查清单

| 检查项 | 状态 | 优先级 |
|--------|------|--------|
| JWT 密钥强度 | 需修复 | P0 |
| 密码哈希算法 | 需修复 | P0 |
| SQL 注入防护 | 已实现 | - |
| XSS 防护 | 部分实现 | P1 |
| CSRF 防护 | 未实现 | P1 |
| Rate Limiting | 已实现(内存) | P1 |
| CORS 配置 | 需修复 | P0 |
| 文件上传安全 | 需修复 | P0 |
| 敏感数据加密 | 需增强 | P0 |
| 日志脱敏 | 需增强 | P0 |
| Docker 安全 | 部分实现 | P1 |
| Token 存储安全 | 需修复 | P0 |
| HTTPS 强制 | 未配置 | P1 |
| 错误处理 | 需改进 | P1 |
| 安全头 | 已实现 | - |

---

## 六、修复优先级建议

### 立即修复（1-3 天）
1. 轮换并安全存储 API 密钥
2. 修复配置验证器
3. 关闭调试模式
4. 禁用数据库 SQL 日志

### 短期修复（1-2 周）
1. 升级密码哈希算法
2. 增强 JWT 密钥管理
3. 实现文件上传验证
4. 迁移 Token 存储方式

### 中期优化（1 个月）
1. 实现 Refresh Token 轮换
2. 分布式限流
3. 完善 MFA 机制
4. 部署安全加固

---

**审计结论**: 系统存在多个高危安全问题，建议按优先级逐步修复。重点关注密钥管理、密码哈希、Token 存储三个核心安全领域。

**审计人**: security-auditor
**审核状态**: 待修复
