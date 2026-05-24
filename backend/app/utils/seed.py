"""Seed data initialization script.

Run with: python -m app.utils.seed
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SyncSessionLocal, engine, Base
from app.models import *
from app.core.security import hash_password
from datetime import datetime, timedelta


def seed_data():
    """Initialize database with seed data."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SyncSessionLocal()
    try:
        # Check if data already exists
        if db.query(User).first():
            print("Seed data already exists, skipping...")
            return

        # Create organizations
        orgs = [
            Organization(name="平台运营方", type="platform", description="能源可信数据空间平台运营管理"),
            Organization(name="发电企业A", type="provider", did="did:energy:gen-a-001", description="某新能源发电企业"),
            Organization(name="电网公司B", type="consumer", did="did:energy:grid-b-001", description="区域电网公司"),
            Organization(name="能源监管局", type="regulator", did="did:energy:reg-c-001", description="能源行业监管机构"),
        ]
        for org in orgs:
            db.add(org)
        db.flush()

        # Create users
        users_data = [
            ("admin", "admin123", "系统管理员", "admin@energy.space", "platform", "admin", orgs[0].id),
            ("provider1", "provider123", "张发电", "provider1@gena.com", "provider", "provider", orgs[1].id),
            ("consumer1", "consumer123", "李电网", "consumer1@gridb.com", "consumer", "consumer", orgs[2].id),
            ("auditor1", "auditor123", "王监管", "auditor1@regc.gov", "regulator", "regulator", orgs[3].id),
            ("operator1", "operator123", "赵运营", "operator1@energy.space", "platform", "operator", orgs[0].id),
        ]
        users = []
        for username, password, real_name, email, phone, role, org_id in users_data:
            user = User(
                username=username,
                password_hash=hash_password(password),
                real_name=real_name,
                email=email,
                phone=phone,
                org_id=org_id,
                role=role,
            )
            db.add(user)
            users.append(user)
        db.flush()

        # Create sample DID documents
        dids = [
            DIDDocument(did="did:energy:user-001", controller="did:energy:platform", public_key="MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEkR3xG...", public_key_type="SM2", created_by=users[0].id),
            DIDDocument(did="did:energy:user-002", controller="did:energy:gen-a", public_key="MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEkT4yG...", public_key_type="SM2", created_by=users[1].id),
            DIDDocument(did="did:energy:user-003", controller="did:energy:grid-b", public_key="MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEkU5zH...", public_key_type="SM2", created_by=users[2].id),
        ]
        for did in dids:
            db.add(did)

        # Create sample access policies
        policies = [
            AccessPolicy(name="新能源发电数据访问策略", description="允许授权方访问新能源发电数据", resource_type="dataset", conditions={"category": "generation", "min_role": "consumer"}, effect="allow", priority=1, created_by=users[0].id),
            AccessPolicy(name="电网调度数据访问策略", description="允许授权方访问电网调度相关数据", resource_type="dataset", conditions={"category": "dispatch", "min_role": "consumer"}, effect="allow", priority=2, created_by=users[0].id),
            AccessPolicy(name="隐私计算任务提交策略", description="允许数据使用方提交隐私计算任务", resource_type="compute_task", conditions={"min_role": "consumer"}, effect="allow", priority=3, created_by=users[0].id),
        ]
        for policy in policies:
            db.add(policy)

        # Create sample data assets
        assets = [
            DataAsset(name="山东省2025年风电发电量数据", description="山东省各风电场2025年逐日发电量统计数据", asset_type="dataset", category="generation", owner_id=orgs[1].id, did="did:energy:gen-a-001", asset_metadata={"fields": ["date", "wind_farm_id", "power_output_mwh", "capacity_mw"], "format": "csv", "update_freq": "daily"}, size_bytes=10485760, record_count=36500, status="published", created_by=users[1].id),
            DataAsset(name="光伏电站辐照度数据集", description="光伏电站逐时辐照度与发电功率数据", asset_type="dataset", category="generation", owner_id=orgs[1].id, asset_metadata={"fields": ["timestamp", "plant_id", "irradiance", "power_kw"], "format": "parquet"}, size_bytes=52428800, record_count=876000, status="published", created_by=users[1].id),
            DataAsset(name="电网负荷预测模型", description="基于深度学习的电网短期负荷预测模型", asset_type="model", category="dispatch", owner_id=orgs[2].id, asset_metadata={"framework": "pytorch", "input_features": ["hour", "day_of_week", "temperature", "humidity"], "accuracy_mape": 2.3}, status="published", created_by=users[2].id),
            DataAsset(name="电力交易结算API", description="电力市场交易结算数据查询接口", asset_type="api", category="trading", owner_id=orgs[2].id, asset_metadata={"endpoint": "/api/trading/settlement", "methods": ["GET"], "rate_limit": "100/min"}, status="published", created_by=users[2].id),
        ]
        for asset in assets:
            db.add(asset)

        # Create sample alert rules
        alert_rules = [
            AlertRule(name="频繁数据访问告警", description="同一用户5分钟内访问同一资产超过50次", condition={"type": "frequency", "threshold": 50, "window_minutes": 5}, severity="high", action_type="log", created_by=users[0].id),
            AlertRule(name="异常IP登录检测", description="检测非常用IP地址的登录行为", condition={"type": "ip_anomaly"}, severity="medium", action_type="log", created_by=users[0].id),
            AlertRule(name="数据导出审计告警", description="大数据量导出操作自动告警", condition={"type": "export", "min_size_mb": 100}, severity="critical", action_type="log", created_by=users[3].id),
        ]
        for rule in alert_rules:
            db.add(rule)
        db.flush()

        # Create sample compute tasks
        from datetime import timezone
        now = datetime.now(timezone.utc)
        compute_tasks = [
            ComputeTask(task_type="federated_learning", status="completed", params={"algorithm": "FedAvg", "rounds": 10, "participants": 3}, result={"accuracy": 0.923, "loss": 0.082, "rounds_completed": 10}, created_by=users[1].id),
            ComputeTask(task_type="mpc", status="running", params={"protocol": "secret_sharing", "parties": 2, "computation": "sum"}, created_by=users[2].id),
            ComputeTask(task_type="tee", status="pending", params={"enclave_type": "sgx", "code_hash": "a1b2c3d4e5f6..."}, created_by=users[1].id),
            ComputeTask(task_type="federated_learning", status="completed", params={"algorithm": "FedProx", "rounds": 20, "participants": 5}, result={"accuracy": 0.891, "loss": 0.124}, created_by=users[2].id),
            ComputeTask(task_type="homomorphic", status="failed", params={"scheme": "ckks", "poly_modulus_degree": 8192}, error_message="Computation timeout after 300s", created_by=users[1].id),
        ]
        for task in compute_tasks:
            db.add(task)
        db.flush()

        # Create sample evidence records
        evidence_records = [
            EvidenceRecord(asset_id=assets[0].id, did=users[1].did, action="register", tx_hash="0x1a2b3c4d5e6f...", block_number=1001, timestamp=now - timedelta(days=5), is_valid=True),
            EvidenceRecord(asset_id=assets[0].id, did=users[2].did, action="access", tx_hash="0x2b3c4d5e6f1a...", block_number=1002, timestamp=now - timedelta(days=4), is_valid=True),
            EvidenceRecord(asset_id=assets[1].id, did=users[1].did, action="register", tx_hash="0x3c4d5e6f1a2b...", block_number=1003, timestamp=now - timedelta(days=3), is_valid=True),
            EvidenceRecord(asset_id=assets[2].id, did=users[2].did, action="compute", tx_hash="0x4d5e6f1a2b3c...", block_number=1004, timestamp=now - timedelta(days=2), is_valid=True),
            EvidenceRecord(asset_id=assets[0].id, did=users[2].did, action="share", tx_hash="0x5e6f1a2b3c4d...", block_number=1005, timestamp=now - timedelta(days=1), is_valid=True),
        ]
        for record in evidence_records:
            db.add(record)
        db.flush()

        # Create sample audit logs
        audit_logs = [
            AuditLog(user_id=users[0].id, action="login", resource_type="system", resource_id="system", details={"ip": "192.168.1.100", "user_agent": "Mozilla/5.0..."}, timestamp=now - timedelta(days=1, hours=9)),
            AuditLog(user_id=users[1].id, action="register_asset", resource_type="data_asset", resource_id=str(assets[0].id), details={"asset_name": assets[0].name}, timestamp=now - timedelta(days=1, hours=8)),
            AuditLog(user_id=users[2].id, action="access_asset", resource_type="data_asset", resource_id=str(assets[0].id), details={"purpose": "power_prediction"}, timestamp=now - timedelta(days=1, hours=6)),
            AuditLog(user_id=users[1].id, action="submit_compute_task", resource_type="compute_task", resource_id=str(compute_tasks[0].id), details={"task_type": "federated_learning"}, timestamp=now - timedelta(days=1, hours=4)),
            AuditLog(user_id=users[3].id, action="audit_review", resource_type="audit_log", resource_id="all", details={"review_period": "2025-01-01 to 2025-01-31"}, timestamp=now - timedelta(days=1, hours=2)),
        ]
        for log in audit_logs:
            db.add(log)

        # Create sample alerts
        alerts = [
            Alert(rule_id=alert_rules[0].id, user_id=users[2].id, severity="high", message="用户 consumer1 在5分钟内访问资产超过50次", details={"asset_id": str(assets[0].id), "access_count": 67, "time_window": "5min"}, is_handled=False, created_at=now - timedelta(hours=2)),
            Alert(rule_id=alert_rules[2].id, user_id=users[1].id, severity="critical", message="数据导出操作：导出数据量 256MB 超过阈值", details={"asset_id": str(assets[1].id), "export_size_mb": 256}, is_handled=True, handled_by=users[0].id, handled_at=now - timedelta(hours=1), created_at=now - timedelta(hours=3)),
        ]
        for alert in alerts:
            db.add(alert)

        # Create auth tokens
        from datetime import timezone
        tokens = [
            AuthToken(user_id=users[0].id, token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", did=users[0].did, expires_at=now + timedelta(days=1), is_revoked=False),
            AuthToken(user_id=users[1].id, token="eyJhbGciOiJSMjU2IiwidHlwIjoiSldUIj9..." , did=users[1].did, expires_at=now + timedelta(days=7), is_revoked=False),
            AuthToken(user_id=users[2].id, token="eyJhbGciOiJSMjU2IiwidHlwIjoiSldUIj9...", did=users[2].did, expires_at=now + timedelta(days=3), is_revoked=False),
        ]
        for token in tokens:
            db.add(token)

        # Create sample system stats (realistic energy data)
        today = datetime.now().date()
        import random
        random.seed(42)
        for i in range(30):
            stat_date = today - timedelta(days=i)
            db.add(SystemStat(stat_date=stat_date, metric_name="total_users", metric_value=5 + (30 - i) // 10, dimension="all"))
            db.add(SystemStat(stat_date=stat_date, metric_name="total_assets", metric_value=4 + (30 - i) // 7, dimension="all"))
            db.add(SystemStat(stat_date=stat_date, metric_name="api_requests", metric_value=150 + random.randint(-20, 50) + (30 - i) * 5, dimension="all"))
            db.add(SystemStat(stat_date=stat_date, metric_name="compute_tasks", metric_value=max(1, 8 - i // 4 + random.randint(-1, 1)), dimension="all"))
            db.add(SystemStat(stat_date=stat_date, metric_name="evidence_records", metric_value=20 + (30 - i) * 2 + random.randint(-3, 3), dimension="all"))
            db.add(SystemStat(stat_date=stat_date, metric_name="auth_tokens", metric_value=max(1, 12 - i // 3 + random.randint(-1, 1)), dimension="all"))
            # Energy-specific metrics
            db.add(SystemStat(stat_date=stat_date, metric_name="data_exchange_volume_gb", metric_value=round(12.5 + random.uniform(-2, 5), 1), dimension="all"))
            db.add(SystemStat(stat_date=stat_date, metric_name="active_connections", metric_value=random.randint(3, 8), dimension="all"))

        db.commit()
        print("Seed data initialized successfully!")
        print(f"  - {len(orgs)} organizations")
        print(f"  - {len(users_data)} users")
        print(f"  - {len(dids)} DID documents")
        print(f"  - {len(policies)} access policies")
        print(f"  - {len(assets)} data assets")
        print(f"  - {len(alert_rules)} alert rules")
        print(f"  - {len(compute_tasks)} compute tasks")
        print(f"  - {len(evidence_records)} evidence records")
        print(f"  - {len(audit_logs)} audit logs")
        print(f"  - {len(alerts)} alerts")
        print(f"  - {len(tokens)} auth tokens")
        print(f"  - {30 * 8} stat records (30 days x 8 metrics)")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
