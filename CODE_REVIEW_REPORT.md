# Energy Trusted Data Space - Pre-Launch Code Review Report

**Reviewer**: gstack-product-reviewer  
**Date**: 2025-01-24  
**Project**: XA-202613 面向能源可信数据空间的多方安全协同与隐私保护技术创新解决方案  
**Tech Stack**: FastAPI + PostgreSQL + React 18 + TDesign + Tailwind CSS  
**Scope**: Backend API/Services/Models/Schemas/Utils + Frontend Pages/API/Stores + Config/Deploy

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 6 |
| 🟠 Important | 9 |
| 🟡 General | 10 |
| 🟢 Suggestion | 7 |

---

## 🔴 CRITICAL Issues

### C1. Two Conflicting Security Utility Modules (`core/security.py` vs `utils/security.py`)

**Location**: `backend/app/core/security.py`, `backend/app/utils/security.py`

**Problem**: There are two security modules with completely different password hashing implementations:
- `core/security.py` uses **SM3** hash with salt format `salt$hash` (used by `auth_service.py`)
- `utils/security.py` uses **bcrypt** via `passlib` (dead code, but confusing)

Additionally, `utils/security.py` imports `from app.config import get_settings` which doesn't exist (the config module exports `settings` directly, not `get_settings()`). This would crash if ever imported.

**Impact**: Any future developer importing from the wrong module will silently use a different hashing algorithm, causing all password verification to fail. The `utils/security.py` module is broken and will raise `ImportError` at runtime.

**Fix**: 
1. Delete `app/utils/security.py` entirely
2. Ensure all code imports from `app.core.security`
3. Add a `# DEPRECATED` comment or remove the file

---

### C2. `authenticate_certificate` Does Full Table Scan

**Location**: `backend/app/services/auth_service.py`, lines 332-350

```python
result = await db.execute(
    select(User).where(User.sm2_public_key.isnot(None))
)
users = result.scalars().all()
for user in users:
    try:
        is_valid = gmssl_adapter.sm2_verify(user.sm2_public_key, challenge, signature)
        ...
```

**Problem**: Certificate authentication loads ALL users with SM2 public keys and tries to verify the signature against each one. This is O(n) in the number of users and will degrade severely as user count grows.

**Impact**: With 1000+ users, login will take seconds. With 10,000+ users, it will time out.

**Fix**: 
1. Add a `certificate_hash` column to the User model
2. Hash the certificate and look up by hash
3. Or require the user to provide their DID/username along with the certificate

---

### C3. Duplicate Alembic Migration Version Numbers

**Location**: `backend/alembic/versions/`

**Problem**: Two migration files share the same version prefix:
- `0006_add_notification_fields.py`
- `0006_add_ops_enhanced.py`

**Impact**: Alembic will only execute one of these migrations, causing the other's schema changes to be silently skipped. This will lead to missing database tables/columns in production.

**Fix**: Rename one of them (e.g., `0006a` and `0006b`, or renumber to `0006` and `0007` and renumber all subsequent migrations).

---

### C4. XSS Middleware Consumes Request Body

**Location**: `backend/app/middleware.py`, XSSFilterMiddleware, line 473

```python
body = await request.body()
```

**Problem**: `request.body()` reads and caches the body. However, for streaming uploads or when downstream middleware/handlers also read the body via `request.body()` or `request.json()`, this may cause issues depending on Starlette's body caching behavior. More critically, for `multipart/form-data` (file uploads), the XSS check is skipped entirely, meaning malicious content could be uploaded via file metadata.

**Impact**: Potential bypass of XSS protection via file upload metadata fields. Also, reading the entire request body into memory for every POST/PUT/PATCH request adds memory pressure.

**Fix**: 
1. For file uploads, validate file content types and sanitize metadata separately
2. Consider size-limiting the body read (e.g., only check first 10KB)

---

### C5. No Authorization on User Management Endpoints

**Location**: `backend/app/api/v1/ops_user.py`

**Problem**: The user management endpoints (create, update, delete, list, batch import) only require authentication (`get_current_user`), not authorization. Any authenticated user can:
- Create new users
- Update any user's information
- Delete users
- View all users
- Batch import users

Only `reset-password` has an admin check (line 124).

**Impact**: Any logged-in user (including regular "user" role) can create admin accounts, delete other users, or modify user data. This is a **privilege escalation vulnerability**.

**Fix**: Add `require_roles("admin", "operator")` dependency to all user management endpoints:
```python
from app.utils.deps import require_roles

@router.post("", ...)
async def create_user(
    ...,
    user: dict = Depends(require_roles("admin", "operator")),
):
```

---

### C6. No Authorization on Data Asset Modification

**Location**: `backend/app/api/v1/data_asset.py`, `update_data_asset` (line 115), `delete_data_asset` (line 129)

**Problem**: The update and delete endpoints don't verify that the current user owns the asset or has write permission. Any authenticated user can modify or soft-delete any data asset.

**Impact**: Data integrity violation — users can tamper with or hide other organizations' data assets.

**Fix**: Add ownership check:
```python
if str(asset.owner_id) != user.get("user_id") and user.get("role") != "admin":
    raise HTTPException(status_code=403, detail="无权修改此资产")
```

---

## 🟠 IMPORTANT Issues

### I1. Frontend-Backend Pagination Type Mismatch

**Location**: `frontend/src/types/api.ts` line 16 vs `backend/app/schemas/common.py` line 31

**Problem**: 
- Frontend `PaginatedResponse` has field `pages`
- Backend `PaginatedResponse` has field `total_pages`

**Impact**: Frontend will always see `undefined` for the total pages count, breaking pagination controls.

**Fix**: Align the field name. Change frontend to `total_pages` or backend to `pages`.

---

### I2. JWT Refresh Token Not Updated in Frontend

**Location**: `frontend/src/api/request.ts`, lines 122-136

**Problem**: When the token refresh succeeds, only `access_token` is saved:
```javascript
localStorage.setItem(TOKEN_KEY, newToken);
```
The new `refresh_token` from the response is not saved.

**Impact**: If the backend rotates refresh tokens (which it does — `refresh_access_token` returns a new refresh token), the old refresh token will eventually expire, forcing the user to re-login.

**Fix**: Also save the new refresh token:
```javascript
const newRefreshToken = res.data?.data?.refresh_token;
if (newRefreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
}
```

---

### I3. `Database.py` Defines Duplicate `Base` Class

**Location**: `backend/app/database.py` line 34 vs `backend/app/models/base.py` line 13

**Problem**: Both files define `class Base(DeclarativeBase)`. Models use `models/base.py` Base. The `database.py` Base is unused but confusing.

**Impact**: Risk of future developers importing the wrong Base, causing models to not be registered with Alembic.

**Fix**: Remove the `Base` class from `database.py`. It serves no purpose.

---

### I4. Hardcoded Default Secret Keys in Config

**Location**: `backend/app/config.py`, lines 25, 99

**Problem**: `APP_SECRET_KEY` and `JWT_SECRET_KEY` default to `change-me-to-a-random-secret-key` and `change-me-jwt-secret-key`. The validator only enforces non-default in `production` env, but the minimum length check is only 16 characters.

**Impact**: If someone deploys with `APP_ENV=development` in production (common mistake), all tokens and sessions will use weak default keys.

**Fix**: 
1. Reduce minimum length to 32 characters
2. Add a startup warning if default keys are detected regardless of environment
3. Consider using `APP_ENV != "development"` check instead of `== "production"`

---

### I5. `SessionResponse` Missing `organization_name`

**Location**: `backend/app/schemas/auth.py` line 90, `backend/app/services/auth_service.py` line 499-507

**Problem**: `SessionResponse` schema has `organization_name` field, but `auth_service.get_session()` never populates it.

**Impact**: The session endpoint always returns `null` for `organization_name`.

**Fix**: Query the Organization model in `get_session()` and populate the field.

---

### I6. CORS Production Origins Missing Port 3000

**Location**: `backend/app/main.py`, lines 117-128

**Problem**: The production CORS allowlist includes ports 80, 5173, 8080, and 8000, but the frontend runs on port 3000 per the project spec.

**Impact**: Frontend requests from port 3000 will be blocked by CORS in production.

**Fix**: Add `http://10.241.2.64:3000` to the CORS origins.

---

### I7. Security Headers Allow `unsafe-inline` and `unsafe-eval`

**Location**: `backend/app/middleware.py`, line 49

```python
"script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
```

**Problem**: CSP allows inline scripts and eval, which significantly weakens XSS protection.

**Impact**: If an attacker can inject inline scripts, CSP won't block them.

**Fix**: Use nonce-based CSP for production, or at minimum remove `'unsafe-eval'`.

---

### I8. WebSocket Token in Query Parameter

**Location**: `backend/app/main.py`, line 222

**Problem**: WebSocket authentication passes JWT token as a URL query parameter (`?token=xxx`).

**Impact**: Tokens may appear in server access logs, browser history, and proxy logs.

**Fix**: Use the WebSocket `Sec-WebSocket-Protocol` header or first message for token exchange.

---

### I9. `unlock_account` Doesn't Verify Target User Exists Before Redis Operations

**Location**: `backend/app/services/auth_service.py`, lines 136-149

**Problem**: The function queries the user first, but if the user doesn't exist, it raises `AuthenticationError("用户不存在")`. However, the Redis cleanup happens after the database check. If the database query fails for a different reason (e.g., connection timeout), the error handling is inconsistent.

**Impact**: Minor — error handling could be cleaner.

**Fix**: Add specific database error handling.

---

## 🟡 GENERAL Issues

### G1. Chinese Function Names in API Endpoints

**Location**: `backend/app/api/v1/blockchain_evidence.py`

**Problem**: Functions like `溯源查询_by_hash`, `提交存证`, `存证详情` use Chinese characters mixed with English.

**Impact**: May cause issues with some tools, profilers, and log analyzers. Inconsistent naming convention.

**Fix**: Use English function names consistently (e.g., `trace_by_hash`, `submit_evidence`, `get_evidence_detail`).

---

### G2. Hardcoded Null UUID Fallback

**Location**: `backend/app/api/v1/compute_task.py`, line 52

```python
organization_id=user.get("organization_id", "00000000-0000-0000-0000-000000000000")
```

**Impact**: If `organization_id` is missing from the JWT, a null UUID is silently used, which may violate foreign key constraints or associate tasks with a non-existent organization.

**Fix**: Validate that `organization_id` exists and raise a clear error if missing.

---

### G3. CSRF Cookie Set But Never Actually Used for API

**Location**: `backend/app/middleware.py`, CSRFMiddleware

**Problem**: The CSRF middleware skips all `/api/v1/` paths (line 253), but still sets a CSRF cookie on every response. The frontend also injects CSRF tokens in request headers.

**Impact**: Wasted overhead. The CSRF cookie and header injection serve no purpose for API requests.

**Fix**: Either remove CSRF handling entirely (since JWT is used) or apply it selectively to state-changing operations.

---

### G4. Inconsistent Error Return Pattern

**Location**: Multiple API files

**Problem**: Some endpoints raise `HTTPException` (e.g., `auth.py` line 131), while others return `ApiResponse(code=2001, ...)` (e.g., `data_asset.py` line 110). The exception handler returns one format, while direct responses use another.

**Impact**: Inconsistent error response format for the frontend to handle.

**Fix**: Standardize on one pattern — preferably using the `AppException` hierarchy everywhere.

---

### G5. `Metadata` Model Inconsistent with TimestampMixin

**Location**: `backend/app/models/data_asset.py`, `Metadata` class (line 100)

**Problem**: `Metadata` model defines `created_at` manually (`default=lambda: datetime.now()`) instead of using `TimestampMixin`. It also lacks `updated_at`.

**Impact**: No update tracking for metadata records. The `created_at` uses local time instead of UTC.

**Fix**: Use `TimestampMixin` and add `updated_at` for consistency.

---

### G6. Database Pool Configuration Not Environment-Configurable

**Location**: `backend/app/database.py`, lines 41-48

**Problem**: `pool_size=20`, `max_overflow=10`, `pool_recycle=3600` are hardcoded.

**Impact**: Cannot tune connection pooling for different environments without code changes.

**Fix**: Add `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` to `.env` configuration.

---

### G7. No Request ID for Distributed Tracing

**Location**: `backend/app/main.py`, `backend/app/middleware.py`

**Problem**: No middleware generates or propagates a request ID (`X-Request-ID`).

**Impact**: Difficult to correlate logs across services for a single request.

**Fix**: Add a simple middleware that generates UUID and attaches to request state + response header.

---

### G8. `_set_csrf_cookie` Comment Contradicts Implementation

**Location**: `backend/app/middleware.py`, line 322-323

**Problem**: Comment says "若 Cookie 已存在，不覆盖" but the code always generates a new token and sets it.

**Impact**: Every response sets a new CSRF token, causing the frontend's cached token to become stale between requests.

**Fix**: Either implement the "don't overwrite" logic or fix the comment.

---

### G9. Frontend `CertificateLoginRequest` Type Mismatch

**Location**: `frontend/src/types/api.ts`, line 40-43

**Problem**: Frontend defines `CertificateLoginRequest` with `password` field, but the backend expects `signature` and `challenge` fields.

**Impact**: Certificate login will fail with a validation error.

**Fix**: Update the frontend type to match backend schema.

---

### G10. `health` Endpoint Doesn't Check Database

**Location**: `backend/app/main.py`, lines 161-177

**Problem**: The health endpoint only returns uptime and version, without checking database, Redis, or MQTT connectivity.

**Impact**: Load balancers may route traffic to a healthy instance that has lost database connectivity.

**Fix**: Add lightweight connectivity checks (e.g., `SELECT 1`) to the health endpoint.

---

## 🟢 SUGGESTIONS

### S1. Add Standard Rate Limit Headers

**Location**: `backend/app/middleware.py`, `RateLimitMiddleware`

Add `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers to help clients handle rate limiting gracefully.

---

### S2. Add React Error Boundaries

**Location**: `frontend/src/`

Add error boundary components at the route level to prevent white-screen crashes from rendering errors.

---

### S3. Standardize Pagination Parameters

Some endpoints use `page`/`page_size`, others use `limit`/`offset`. Standardize on one approach across all APIs.

---

### S4. Add `README.md` for Backend Module

The `backend/app/` directory lacks a clear module-level documentation explaining the architecture and how to add new endpoints.

---

### S5. Use Environment-Based CORS Origin List

Instead of hardcoding IP addresses, use an environment variable for CORS origins:
```python
CORS_ORIGINS= http://10.241.2.64,http://10.241.2.64:3000,...
```

---

### S6. Add OpenTelemetry Integration

For a production system handling energy data, adding OpenTelemetry for traces and metrics would significantly improve observability.

---

### S7. Frontend API Response Interceptor Improvement

The response interceptor (request.ts line 67-74) rejects business errors with `new Error(body.message)`, losing the error code. Consider preserving the full error object for better error handling by callers.

---

## Migration Safety Checklist

| Item | Status | Notes |
|------|--------|-------|
| All models registered in `__init__.py` | ✅ | All 42+ models imported |
| Alembic env.py imports all models | ✅ | Via `import app.models` |
| Migration version chain | ❌ | Duplicate `0006` versions |
| Downgrade support | ❌ | No downgrade functions |
| Migration tested | ⚠️ | Need to verify on clean database |

---

## Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| Authentication | ✅ | JWT + DID + SM2 Certificate + MFA |
| Authorization | ❌ | Missing on most management endpoints |
| CORS | ⚠️ | Missing port 3000 |
| CSP | ⚠️ | Too permissive (`unsafe-inline/eval`) |
| CSRF | ⚠️ | Implemented but skipped for all API paths |
| Rate Limiting | ✅ | Redis-based sliding window |
| SQL Injection Protection | ✅ | Middleware + SQLAlchemy parameterized queries |
| XSS Protection | ✅ | Middleware + CSP headers |
| Password Hashing | ✅ | SM3 with salt (in `core/security.py`) |
| Token Rotation | ⚠️ | Backend rotates but frontend doesn't save new refresh token |
| Secret Key Validation | ⚠️ | Only enforced in production env |

---

## Priority Action Plan

1. **P0 (Block Launch)**: Fix C5 (authorization on user management), C3 (duplicate migration), C1 (remove conflicting security module)
2. **P1 (Fix Before Demo)**: Fix C2 (certificate auth performance), I1 (pagination type mismatch), I2 (refresh token), I6 (CORS port 3000)
3. **P2 (Fix This Week)**: Fix C6 (asset authorization), I4 (secret key validation), I7 (CSP tightening), G4 (error pattern consistency)
4. **P3 (Tech Debt)**: G1-G10, S1-S7

---

*Report generated by gstack-product-reviewer*
