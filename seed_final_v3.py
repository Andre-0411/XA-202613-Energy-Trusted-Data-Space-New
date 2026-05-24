"""种子数据脚本 v3 - 修正字段名"""
import asyncio, asyncpg, hashlib, secrets, uuid

DB_CONFIG = {"host": "localhost", "port": 5432, "user": "energy", "password": "Andre0411", "database": "energy_trusted"}

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${hashed}"

USERS = [
    ("admin", "admin123", "admin", "admin@energy.local"),
    ("security_admin", "security123", "security_admin", "security@energy.local"),
    ("auditor", "auditor123", "auditor", "auditor@energy.local"),
    ("provider1", "provider123", "data_provider", "provider1@energy.local"),
    ("consumer1", "consumer123", "data_consumer", "consumer1@energy.local"),
    ("operator1", "operator123", "operator", "operator1@energy.local"),
]

async def seed():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        existing = await conn.fetchval("SELECT COUNT(*) FROM users WHERE username='admin'")
        if existing > 0:
            print(f"Already have {existing} admin user(s), skipping.")
            return

        # Get or create org
        org_id = await conn.fetchval("SELECT id FROM organizations WHERE code='DEFAULT'")
        if not org_id:
            org_id = await conn.fetchval(
                "INSERT INTO organizations (id, name, code, level, status) VALUES ($1, '默认机构', 'DEFAULT', 1, 'active') RETURNING id",
                uuid.uuid4()
            )
        print(f"Org: {org_id}")

        # Get or create dept
        dept_id = await conn.fetchval("SELECT id FROM departments WHERE organization_id=$1 LIMIT 1", org_id)
        if not dept_id:
            dept_id = await conn.fetchval(
                "INSERT INTO departments (id, name, organization_id, status) VALUES ($1, '默认部门', $2, 'active') RETURNING id",
                uuid.uuid4(), org_id
            )
        print(f"Dept: {dept_id}")

        # Create users - only use columns that exist in the model
        for username, password, role, email in USERS:
            hashed = hash_password(password)
            try:
                await conn.execute(
                    "INSERT INTO users (id, username, password_hash, role, email, status, organization_id, department_id, mfa_enabled, login_fail_count) "
                    "VALUES ($1, $2, $3, $4, $5, 'active', $6, $7, false, 0) "
                    "ON CONFLICT (username) DO NOTHING",
                    uuid.uuid4(), username, hashed, role, email, org_id, dept_id
                )
                print(f"  Created: {username} / {password}")
            except Exception as e:
                print(f"  Failed {username}: {e}")

        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"Total users: {count}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
