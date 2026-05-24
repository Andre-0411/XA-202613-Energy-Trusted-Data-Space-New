"""检查 gmssl 并用正确算法重写种子数据"""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

def ssh_exec(ssh, cmd, timeout=60):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace')
    err = stderr.read().decode('gbk', errors='replace')
    if out.strip():
        print(out.strip())
    if err.strip():
        print(f"[STDERR] {err.strip()}")
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    print(f"Connected to {HOST}")

    # Check gmssl
    ssh_exec(ssh, "python -c \"import gmssl; print('gmssl available')\"", timeout=10)

    # Check how the backend hashes passwords - run the actual hash function
    check_script = '''
import sys
sys.path.insert(0, r"D:\\Andre\\project\\energy-trusted-data-space\\backend")
from app.core.security import hash_password, verify_password

# Hash admin123 using the actual backend function
hashed = hash_password("admin123")
print(f"Hashed password: {hashed}")

# Verify it works
ok = verify_password("admin123", hashed)
print(f"Verify: {ok}")

# Check the hash format
parts = hashed.split("$")
print(f"Salt: {parts[0]}")
print(f"Hash: {parts[1]}")
print(f"Hash length: {len(parts[1])}")
'''
    sftp = ssh.open_sftp()
    with sftp.open(f"{PROJECT_DIR}\\check_hash.py", 'w') as f:
        f.write(check_script)
    sftp.close()
    ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python check_hash.py", timeout=30)

    # Now create seed script that uses the backend's own hash function
    seed_script = '''
import sys
import asyncio
import uuid

sys.path.insert(0, r"D:\\\\Andre\\\\project\\\\energy-trusted-data-space\\\\backend")
from app.core.security import hash_password
import asyncpg

DB_CONFIG = {"host": "localhost", "port": 5432, "user": "energy", "password": "Andre0411", "database": "energy_trusted"}

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
        # Check existing
        existing = await conn.fetchval("SELECT COUNT(*) FROM users")
        if existing > 0:
            print(f"Already {existing} users. Deleting and re-seeding...")
            await conn.execute("DELETE FROM users")

        org_id = await conn.fetchval("SELECT id FROM organizations WHERE code='DEFAULT'")
        dept_id = await conn.fetchval("SELECT id FROM departments WHERE organization_id=$1 LIMIT 1", org_id)

        for username, password, role, email in USERS:
            hashed = hash_password(password)
            try:
                await conn.execute(
                    "INSERT INTO users (id, username, password_hash, role, email, status, organization_id, department_id, mfa_enabled, login_fail_count) "
                    "VALUES ($1, $2, $3, $4, $5, 'active', $6, $7, false, 0) "
                    "ON CONFLICT (username) DO NOTHING",
                    uuid.uuid4(), username, hashed, role, email, org_id, dept_id
                )
                print(f"  Created: {username}")
            except Exception as e:
                print(f"  Failed {username}: {e}")

        count = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"Total users: {count}")
    finally:
        await conn.close()

asyncio.run(seed())
'''
    with sftp.open(f"{PROJECT_DIR}\\seed_with_backend_hash.py", 'w') as f:
        f.write(seed_script)
    sftp.close()
    print("seed_with_backend_hash.py uploaded")

    # Run seed with backend's own hash function
    ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python seed_with_backend_hash.py", timeout=60)

    # Restart backend
    print("\n--- Restart backend ---")
    ssh_exec(ssh, "schtasks /End /TN \"ETDS-Backend\" 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %a 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "schtasks /Run /TN \"ETDS-Backend\"", timeout=15)

    print("\nWaiting for backend...")
    for i in range(20):
        time.sleep(3)
        out, _ = ssh_exec(ssh, "netstat -ano | findstr :8000 | findstr LISTENING", timeout=10)
        if "8000" in out and "LISTENING" in out:
            print("Backend ready!")
            break

    # Test login
    print("\n--- Test login ---")
    test_script2 = '''
import urllib.request, json

data = json.dumps({"username": "admin", "password": "admin123", "auth_type": "password"}).encode("utf-8")

# Backend direct
try:
    req = urllib.request.Request("http://localhost:8000/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    body = json.loads(resp.read().decode("utf-8"))
    if body.get("code") == 0:
        print(f"BACKEND LOGIN SUCCESS!")
        token = body["data"].get("access_token", "")
        print(f"Token: {token[:60]}...")
    else:
        print(f"Backend login failed: {body.get('message')}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode("utf-8")
    print(f"Backend HTTP {e.code}: {err_body}")
except Exception as e:
    print(f"Backend error: {e}")

# Proxy
try:
    req2 = urllib.request.Request("http://localhost:8080/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
    resp2 = urllib.request.urlopen(req2, timeout=10)
    body2 = json.loads(resp2.read().decode("utf-8"))
    if body2.get("code") == 0:
        print(f"PROXY LOGIN SUCCESS!")
    else:
        print(f"Proxy login failed: {body2.get('message')}")
except urllib.error.HTTPError as e:
    err_body = e.read().decode("utf-8")
    print(f"Proxy HTTP {e.code}: {err_body}")
except Exception as e:
    print(f"Proxy error: {e}")

# Frontend
try:
    req3 = urllib.request.Request("http://localhost:8080/")
    resp3 = urllib.request.urlopen(req3, timeout=10)
    print(f"Frontend: HTTP {resp3.status}, {len(resp3.read())} bytes")
except Exception as e:
    print(f"Frontend error: {e}")
'''
    with sftp.open(f"{PROJECT_DIR}\\test_login2.py", 'w') as f:
        f.write(test_script2)
    sftp.close()

    ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python test_login2.py", timeout=30)

    ssh.close()

if __name__ == "__main__":
    main()
