"""种子数据脚本 - 使用正确的表结构"""
import asyncio
import asyncpg
import hashlib
import secrets
import uuid

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "energy",
    "password": "Andre0411",
    "database": "energy_trusted",
}

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (matches backend's SM3 fallback)"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${hashed}"

DEFAULT_USERS = [
    ("admin", "admin123", "admin", "admin@energy.local", "系统管理员"),
    ("security_admin", "security123", "security_admin", "security@energy.local", "安全管理员"),
    ("auditor", "auditor123", "auditor", "auditor@energy.local", "审计员"),
    ("provider1", "provider123", "data_provider", "provider1@energy.local", "数据提供方"),
    ("consumer1", "consumer123", "data_consumer", "consumer1@energy.local", "数据使用方"),
    ("operator1", "operator123", "operator", "operator1@energy.local", "运营管理员"),
]

async def seed():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Check if admin already exists
        existing = await conn.fetchval("SELECT COUNT(*) FROM users WHERE username='admin'")
        if existing > 0:
            print(f"Users table already has {existing} user(s) with username 'admin', skipping seed.")
            return

        # Create default organization (with required 'level' field)
        try:
            org_id = await conn.fetchval(
                "INSERT INTO organizations (id, name, code, level, status) "
                "VALUES ($1, '默认机构', 'DEFAULT', 1, 'active') "
                "ON CONFLICT (code) DO UPDATE SET name='默认机构' RETURNING id",
                uuid.uuid4()
            )
            print(f"Organization created: {org_id}")
        except Exception as e:
            print(f"Org creation error: {e}")
            # Try to get existing org
            org_id = await conn.fetchval("SELECT id FROM organizations WHERE code='DEFAULT'")
            if org_id:
                print(f"Using existing org: {org_id}")
            else:
                raise Exception("Cannot create or find default organization")

        # Create default department (with organization_id, not org_id; no 'code' field)
        try:
            dept_id = await conn.fetchval(
                "INSERT INTO departments (id, name, organization_id, status) "
                "VALUES ($1, '默认部门', $2, 'active') RETURNING id",
                uuid.uuid4(), org_id
            )
            print(f"Department created: {dept_id}")
        except Exception as e:
            print(f"Dept creation error: {e}")
            dept_id = await conn.fetchval(
                "SELECT id FROM departments WHERE organization_id=$1 LIMIT 1", org_id
            )
            if dept_id:
                print(f"Using existing dept: {dept_id}")
            else:
                dept_id = None

        # Create users (password_hash, organization_id, department_id)
        for username, password, role, email, display_name in DEFAULT_USERS:
            uid = uuid.uuid4()
            hashed = hash_password(password)
            try:
                await conn.execute(
                    "INSERT INTO users (id, username, password_hash, role, email, full_name, status, organization_id, department_id) "
                    "VALUES ($1, $2, $3, $4, $5, $6, 'active', $7, $8) "
                    "ON CONFLICT (username) DO NOTHING",
                    uid, username, hashed, role, email, display_name, org_id, dept_id
                )
                print(f"  Created user: {username} / {password} (role: {role})")
            except Exception as e:
                print(f"  Failed to create {username}: {e}")

        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"\nTotal users in database: {count}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
