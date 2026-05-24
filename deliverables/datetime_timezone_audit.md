# Datetime 时区问题审查报告

## 问题概述
PostgreSQL asyncpg 严格区分 timezone-aware 和 naive datetime。当 DB 列定义为 `TIMESTAMP WITHOUT TIME ZONE`（无 timezone=True），写入 `datetime.now(timezone.utc)`（timezone-aware）会导致类型不匹配错误或隐式转换问题。

## 模型审查结果

### ✅ 正确使用 timezone=True 的模型
| 模型 | 字段 | 类型 |
|------|------|------|
| base.TimestampMixin | created_at/updated_at | DateTime(timezone=True) |
| user.User | last_login_at/locked_until | DateTime(timezone=True) |
| subscription.* | 所有时间字段 | DateTime(timezone=True) |
| contract.* | approved_at/effective_date | DateTime(timezone=True) |
| workflow.* | approved_at | DateTime(timezone=True) |
| product.* | published_at/reviewed_at | DateTime(timezone=True) |
| invite_code.* | expires_at/reviewed_at | DateTime(timezone=True) |
| gdpr.DSRRequest | due_date/completed_at | DateTime(timezone=True) |
| vc_model.* | issued_at/revoked_at | DateTime(timezone=True) |
| mfa_model.* | last_verified_at/verified_at | DateTime(timezone=True) |
| monitor_alert.* | acknowledged_at/fired_at | DateTime(timezone=True) |

### ❌ 使用 naive datetime 的模型（潜在 Bug）
| 模型 | 字段 | 问题 |
|------|------|------|
| audit_log.AuditLog | created_at | `default=lambda: datetime.now()` 无 timezone |
| access_log.AccessLog | created_at | `default=lambda: datetime.now()` 无 timezone |
| blockchain.NftAsset | created_at | naive |
| blockchain.EvidenceRecord | created_at | naive |
| blockchain.BlockchainTransaction | created_at | naive |
| compute_task.ComputeTask | started_at/completed_at | naive (mapped_column(nullable=True)) |
| data_asset.DataAsset | published_at | naive |
| data_asset.Metadata | created_at | naive |
| security.SecurityPolicy | created_at | naive |
| security.PolicyAssignment | created_at | naive |
| security.DidDocument | created_at | naive |
| security.VcRecord | issued_at/expires_at | naive |
| security.KeyStore | rotated_at/created_at | naive |
| security.KeyUsageLog | created_at | naive |
| security.ThreatEvent | detected_at/resolved_at | naive |
| security.ThreatAction | created_at | naive |

## 服务层 datetime.now(timezone.utc) 使用统计
扫描结果显示 **200+ 处**使用 `datetime.now(timezone.utc)`，包括：
- auth_service.py (6处)
- vc_service.py (多处)
- audit_enhanced.py (多处，已修复)
- threat_service.py (多处，已修复部分)
- alert_service.py (多处)
- mfa_service.py (多处)
- portal_service.py (多处)
- product_*_service.py (多处)
- subscription_service.py (多处)
- workflow_service.py (多处)
- gdpr_service.py (多处)
- sla_service.py (多处)
- sso_service.py (多处)

## 修复策略

### 高优先级（必须修复）
写入 naive 列的服务：
1. **vc_service.py**: `VcRecord.issued_at` (已修复)
2. **threat_service.py**: `ThreatEvent.resolved_at` (已修复)
3. **auth_service.py**: `User.last_login_at`/`locked_until` **(timezone-aware 列，当前正确)**
4. **audit_enhanced.py**: `AuditLog.created_at` (已修复)

### 中优先级
仅用于比较/计算（不写入 DB）的使用：
- 大多数 `.isoformat()` 输出字符串
- 缓存 TTL 计算
- 时间差计算

**判断规则**：
- 如果写入 DB 列 → 必须匹配列类型
- 如果仅用于计算/输出 → timezone-aware 更安全（避免服务器时区影响）

### 低优先级（架构改进）
将 naive 模型迁移到 timezone-aware（需要 Alembic 迁移，影响范围大）

## 已修复清单
- audit_enhanced.py: 6处 datetime.now(timezone.utc) → datetime.utcnow()
- vc_service.py: 2处 (issued_at 写入, expires_at 比较)
- threat_service.py: 1处 (resolved_at 写入)
- security_enhanced.py: 20个端点添加认证保护
- vc_real.py: 移除错误的 expires_at 字段，修复 issued_at 使用

## 待修复清单
### 需进一步确认
- compute_task.ComputeTask.completed_at: 已确认 naive，但 compute_service.py 可能已修复
- security.VcRecord.issued_at: vc_service.py 已修复，但 vc_real.py 需检查
