# Security Audit Report - Energy Trusted Data Space

## Meta
- Audit mode: Comprehensive
- Date: 2025-01-27
- Scope: 7 modified security-related files + supporting infrastructure
- Phases executed: 1-6, 10-14

---

## Executive Summary

The codebase has a **solid security foundation** with SM3/SM2 national cryptography, JWT authentication, Redis-based rate limiting, SQL injection guard, and XSS filtering middleware. However, **3 high-severity access control issues** were identified that could allow unauthorized access to other users' MFA configurations and backup codes. The proxy server has a critical CORS misconfiguration. These findings are consistent with OWASP A01 (Broken Access Control) and require immediate remediation.

---

## Findings

### [F-001] IDOR: MFA Status Leaks Other Users' MFA Configuration
- **Category**: OWASP A01 - Broken Access Control
- **Severity**: HIGH
- **Confidence**: 9/10
- **Location**: `backend/app/api/v1/auth_mfa.py:89-94`
- **Description**: The endpoint `GET /mfa/status/{user_id}` accepts an arbitrary `user_id` path parameter and returns that user's MFA status (enabled/disabled, method, backup codes remaining, last verified time). While it requires authentication via `get_current_user`, it does NOT verify that the authenticated user owns the queried `user_id`.
- **Exploit Scenario**:
  1. Attacker authenticates as User A
  2. Attacker calls `GET /api/v1/auth/mfa/status/{victim_user_id}`
  3. Attacker receives victim's MFA status, method, and backup code count
  4. This information aids targeted attacks (e.g., knowing MFA is disabled)
- **Reproduction**: Send authenticated request to `/api/v1/auth/mfa/status/<other_user_uuid>` - no ownership check exists.
- **Remediation**: Add authorization check to verify `user_id == current_user["user_id"]` or `current_user["role"] == "admin"`.
- **Priority**: P0 (immediate)

---

### [F-002] IDOR: Backup Code Verification Uses Client-Supplied user_id
- **Category**: OWASP A01 - Broken Access Control
- **Severity**: HIGH
- **Confidence**: 9/10
- **Location**: `backend/app/api/v1/auth_mfa.py:97-105`
- **Description**: The `POST /mfa/backup-codes/verify` endpoint uses `request.user_id` from the request body instead of extracting `user_id` from the JWT token. This allows any authenticated user to attempt backup code verification against any other user's account.
- **Exploit Scenario**:
  1. Attacker authenticates as User A
  2. Attacker sends `POST /api/v1/auth/mfa/backup-codes/verify` with `{"user_id": "<victim_uuid>", "backup_code": "XXXX-XXXX"}`
  3. Attacker brute-forces backup codes against victim's account
- **Reproduction**: Send authenticated request with different user_id in body.
- **Remediation**: Always use `user_id` from JWT token: `user_id = user.get("user_id") or user.get("sub")`. Ignore `request.user_id`.
- **Priority**: P0 (immediate)

---

### [F-003] Proxy Server CORS Allows All Origins
- **Category**: OWASP A05 - Security Misconfiguration
- **Severity**: HIGH
- **Confidence**: 9/10
- **Location**: `deploy/serve_proxy.py:168, 193, 200`
- **Description**: The proxy server sets `Access-Control-Allow-Origin: *` on all responses, including OPTIONS preflight and proxied API responses. Combined with the backend also using `allow_origins=["*"]`, any website can make cross-origin requests to the API.
- **Exploit Scenario**:
  1. Attacker hosts malicious page at `evil.com`
  2. Victim visits `evil.com` while authenticated
  3. `evil.com` makes cross-origin requests to the API proxy
  4. Browser sends cookies/auth headers due to same-origin policy relaxation
- **Remediation**: Restrict CORS to specific trusted origins in both proxy and backend.
- **Priority**: P0 (immediate)

---

### [F-004] QR Code Endpoint Missing Authentication
- **Category**: OWASP A07 - Identification and Authentication Failures
- **Severity**: MEDIUM
- **Confidence**: 8/10
- **Location**: `backend/app/api/v1/auth_mfa.py:117-144`
- **Description**: The `GET /mfa/qr-code` endpoint does not use `get_current_user` dependency. It accepts any `uri` query parameter and generates a QR code for it. While this doesn't directly expose secrets, it allows unauthenticated QR code generation for arbitrary TOTP URIs.
- **Exploit Scenario**: An attacker could use this endpoint to generate QR codes for phishing TOTP setups.
- **Remediation**: Add `user: dict = Depends(get_current_user)` dependency. Validate that the URI belongs to the requesting user.
- **Priority**: P1 (this sprint)

---

### [F-005] Token Blacklist Fail-Open When Redis Unavailable
- **Category**: OWASP A07 - Identification and Authentication Failures
- **Severity**: MEDIUM
- **Confidence**: 8/10
- **Location**: `backend/app/dependencies.py:68-81`
- **Description**: When Redis is unavailable, the token blacklist check is silently skipped (fail-open). This means revoked/invalidated tokens remain valid if Redis goes down. The `auth_service.py` logout function (line 477) also logs "fail-open" behavior.
- **Exploit Scenario**:
  1. User logs out, token is added to blacklist
  2. Redis becomes unavailable
  3. The logged-out token remains valid and can be used for API access
- **Remediation**: Change to fail-closed: reject requests when Redis blacklist cannot be verified. Or implement a database-backed blacklist as fallback.
- **Priority**: P1 (this sprint)

---

### [F-006] MFA Disable Accepts Optional Password Parameter
- **Category**: OWASP A07 - Identification and Authentication Failures
- **Severity**: MEDIUM
- **Confidence**: 8/10
- **Location**: `backend/app/services/mfa_service.py:315-346`, `frontend/src/components/security/MfaSettings.tsx:146-169`
- **Description**: The `disable_mfa` service function accepts `password` and `code` as parameters, but the code only checks `code` if provided (`if code:`). The frontend only sends `code`, not `password`. The backend `disable_mfa` signature accepts `password` but never validates it. This means MFA can be disabled with just a TOTP code, without verifying the user's password.
- **Remediation**: Require both password AND TOTP code for MFA disable. Update frontend to collect password. Update backend to always verify password.
- **Priority**: P1 (this sprint)

---

### [F-007] Publish Asset Endpoint Missing Authorization
- **Category**: OWASP A01 - Broken Access Control
- **Severity**: MEDIUM
- **Confidence**: 8/10
- **Location**: `backend/app/api/v1/data_asset.py:285-295`
- **Description**: The `POST /{asset_id}/publish` endpoint requires authentication but has no ownership or role check. Any authenticated user can publish any asset to the catalog. Compare with `update_data_asset` (line 124) and `delete_data_asset` (line 143) which both check ownership/admin role.
- **Remediation**: Add the same ownership/admin check as update and delete endpoints.
- **Priority**: P1 (this sprint)

---

### [F-008] Audit Log Export Has No Role-Based Access Control
- **Category**: OWASP A01 - Broken Access Control
- **Severity**: MEDIUM
- **Confidence**: 8/10
- **Location**: `backend/app/api/v1/audit_log.py:232-286`
- **Description**: The `GET /audit-logs/export` endpoint only requires authentication but no role check. Any authenticated user can export all audit logs. The `DELETE /audit-logs/{log_id}` endpoint correctly restricts to admin, but export does not.
- **Remediation**: Add role check: `if current_user.get("role") not in ("admin", "auditor"): raise 403`
- **Priority**: P1 (this sprint)

---

### [F-009] Certificate Authentication Iterates All Users
- **Category**: OWASP A04 - Insecure Design
- **Severity**: MEDIUM
- **Confidence**: 7/10
- **Location**: `backend/app/services/auth_service.py:310-350`
- **Description**: `authenticate_certificate` loads ALL users with SM2 public keys and iterates through them attempting signature verification. This is an O(n) operation that could be exploited for timing attacks and has poor performance at scale.
- **Remediation**: Index users by certificate hash. Use `cert_hash` lookup instead of iterating all users.
- **Priority**: P2 (next sprint)

---

### [F-010] Proxy Error Response Leaks Internal Details
- **Category**: OWASP A05 - Security Misconfiguration
- **Severity**: LOW
- **Confidence**: 8/10
- **Location**: `deploy/serve_proxy.py:198-202`
- **Description**: Proxy error responses include raw exception messages (`str(e)`) in JSON format, potentially exposing internal hostnames, ports, and connection details.
- **Remediation**: Return generic error message. Log details server-side only.
- **Priority**: P2 (next sprint)

---

### [F-011] MFA Secret Exposed in Setup Response
- **Category**: OWASP A07 - Identification and Authentication Failures
- **Severity**: LOW
- **Confidence**: 7/10
- **Location**: `backend/app/services/mfa_service.py:176-182`, `backend/app/api/v1/auth_mfa.py:26-43`
- **Description**: The MFA setup endpoint returns the raw TOTP secret in the API response. While this is necessary for QR code generation, the secret should ideally be transmitted only via QR code and not exposed in API responses that may be logged.
- **Remediation**: Consider short-lived tokens for secret access, or ensure API response logging excludes MFA setup responses.
- **Priority**: P3 (backlog)

---

### [F-012] WebSocket Endpoint Token Verification Fails Silently
- **Category**: OWASP A07 - Identification and Authentication Failures
- **Severity**: LOW
- **Confidence**: 7/10
- **Location**: `backend/app/main.py:232-242`
- **Description**: The WebSocket endpoint attempts to verify the token but if verification fails, it silently continues with `user_id = None`. The connection is still established, just without a user association.
- **Remediation**: Reject WebSocket connections with invalid tokens. Require authentication for sensitive notification channels.
- **Priority**: P2 (next sprint)

---

## Security Posture Score
- Critical: 0
- High: 3
- Medium: 5
- Low: 4
- Info: 0
- **Overall: B** (solid foundation with access control gaps)

---

## Positive Security Controls Identified

1. **SM3 password hashing with salt** - `security.py:109-123` uses `secrets.token_hex(16)` for salt and SM3 for hashing
2. **Timing-safe password comparison** - `security.py:140` uses `secrets.compare_digest()`
3. **Redis-based login lockout** - 5 attempts, 30-minute lockout with dual Redis+DB tracking
4. **SQL injection guard middleware** - Comprehensive pattern matching for common injection vectors
5. **XSS filter middleware** - Blocks script injection, event handlers, and dangerous protocols
6. **Security headers** - HSTS, X-Frame-Options, CSP, X-Content-Type-Options
7. **CSRF middleware** - Referer/Origin validation for non-API paths
8. **Rate limiting** - Redis-backed with in-memory fallback (100 req/min)
9. **JWT token blacklisting** - Redis-based revocation support
10. **Backup code hashing** - SHA-256 hashed storage with HMAC comparison
11. **TOTP verification** - Proper time-window validation with `hmac.compare_digest`
12. **Role-based permissions** - `require_permissions` and `require_roles` dependency injectors
13. **Production secret validation** - Config validator rejects default secrets in production

---

## Remediation Roadmap

### P0 - Immediate (before next release)
1. Fix IDOR in MFA status endpoint [F-001]
2. Fix IDOR in backup code verification [F-002]
3. Restrict CORS to trusted origins [F-003]

### P1 - This Sprint
4. Add auth to QR code endpoint [F-004]
5. Implement fail-closed token blacklist [F-005]
6. Require password for MFA disable [F-006]
7. Add authorization to publish endpoint [F-007]
8. Add role check to audit log export [F-008]

### P2 - Next Sprint
9. Fix certificate auth performance [F-009]
10. Sanitize proxy error messages [F-010]
11. Fix WebSocket auth fail-open [F-012]

### P3 - Backlog
12. Minimize MFA secret exposure in API responses [F-011]
