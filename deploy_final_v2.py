"""最终部署脚本 v2：种子数据 + 重启服务 + 验证"""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

def ssh_exec(ssh, cmd, timeout=120):
    """执行命令并返回输出"""
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
    print(f"✓ Connected to {HOST}")

    # === Step 1: Seed database ===
    print("\n" + "="*60)
    print("STEP 1: Seeding database with default users")
    print("="*60)

    # Seed script that uses SHA-256 (same as backend's SM3 fallback)
    seed_script = r'''import asyncio, asyncpg, hashlib, secrets, uuid

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

        # Get or create default org
        try:
            org_id = await conn.fetchval(
                "INSERT INTO organizations (name, code, status) VALUES ('默认机构', 'DEFAULT', 'active') "
                "ON CONFLICT (code) DO UPDATE SET name='默认机构' RETURNING id"
            )
            print(f"Organization: {org_id}")
        except Exception as e:
            print(f"Org creation failed: {e}")
            org_id = None

        # Get or create default dept
        dept_id = None
        if org_id:
            try:
                dept_id = await conn.fetchval(
                    "INSERT INTO departments (name, code, org_id, status) VALUES ('默认部门', 'DEFAULT_DEPT', $1, 'active') "
                    "ON CONFLICT (code) DO UPDATE SET name='默认部门' RETURNING id",
                    org_id
                )
                print(f"Department: {dept_id}")
            except Exception as e:
                print(f"Dept creation failed: {e}")

        for username, password, role, email, display_name in DEFAULT_USERS:
            uid = str(uuid.uuid4())
            hashed = hash_password(password)
            try:
                await conn.execute(
                    "INSERT INTO users (id, username, hashed_password, role, email, full_name, status, org_id, dept_id) "
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

asyncio.run(seed())
'''

    # Write seed script via SFTP
    sftp = ssh.open_sftp()
    with sftp.open(f"{PROJECT_DIR}\\seed_final.py", 'w') as f:
        f.write(seed_script)
    sftp.close()
    print("✓ seed_final.py uploaded")

    # Run seed script
    out, err = ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python seed_final.py", timeout=60)

    # === Step 2: Restart backend ===
    print("\n" + "="*60)
    print("STEP 2: Restarting backend")
    print("="*60)

    # Stop backend schtask
    ssh_exec(ssh, "schtasks /End /TN \"ETDS-Backend\" 2>nul", timeout=30)
    time.sleep(2)

    # Kill any process on port 8000
    ssh_exec(ssh, "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %a 2>nul", timeout=30)
    time.sleep(1)

    # Restart backend
    ssh_exec(ssh, "schtasks /Run /TN \"ETDS-Backend\"", timeout=30)

    # Wait for backend to start
    print("\nWaiting for backend to start...")
    for i in range(20):
        time.sleep(3)
        out, _ = ssh_exec(ssh, "netstat -ano | findstr :8000 | findstr LISTENING", timeout=15)
        if "8000" in out and "LISTENING" in out:
            print("✓ Backend is listening on port 8000!")
            break
        print(f"  Waiting... ({(i+1)*3}s)")
    else:
        print("⚠ Backend may not have started. Checking logs...")
        ssh_exec(ssh, f"type {PROJECT_DIR}\\backend.log 2>nul | findstr /i \"error trace\"", timeout=15)

    # === Step 3: Restart frontend ===
    print("\n" + "="*60)
    print("STEP 3: Restarting frontend proxy")
    print("="*60)

    ssh_exec(ssh, "schtasks /End /TN \"ETDS-Frontend\" 2>nul", timeout=30)
    time.sleep(1)

    # Kill any process on port 8080
    ssh_exec(ssh, "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do taskkill /F /PID %a 2>nul", timeout=30)
    time.sleep(1)

    ssh_exec(ssh, "schtasks /Run /TN \"ETDS-Frontend\"", timeout=30)

    print("\nWaiting for frontend to start...")
    for i in range(10):
        time.sleep(2)
        out, _ = ssh_exec(ssh, "netstat -ano | findstr :8080 | findstr LISTENING", timeout=15)
        if "8080" in out and "LISTENING" in out:
            print("✓ Frontend is listening on port 8080!")
            break
        print(f"  Waiting... ({(i+1)*2}s)")

    # === Step 4: Verify ===
    print("\n" + "="*60)
    print("STEP 4: Verification")
    print("="*60)

    # Test frontend page
    ssh_exec(ssh, "powershell -Command \"try { $r = Invoke-WebRequest -Uri 'http://localhost:8080' -UseBasicParsing -TimeoutSec 10; Write-Host ('Frontend: HTTP ' + $r.StatusCode) } catch { Write-Host ('Frontend: ' + $_.Exception.Message) }\"", timeout=20)

    # Test API via backend directly
    ssh_exec(ssh, "powershell -Command \"try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -Body '{\\\"username\\\":\\\"admin\\\",\\\"password\\\":\\\"admin123\\\",\\\"auth_type\\\":\\\"password\\\"}' -ContentType 'application/json' -UseBasicParsing -TimeoutSec 10; Write-Host ('Login: HTTP ' + $r.StatusCode + ' - ' + $r.Content.Substring(0, [Math]::Min(300, $r.Content.Length))) } catch { $resp = $_.Exception.Response; if ($resp) { $reader = New-Object System.IO.StreamReader($resp.GetResponseStream()); Write-Host ('Login: ' + $reader.ReadToEnd().Substring(0, [Math]::Min(300, $reader.ReadToEnd().Length))) } else { Write-Host ('Login: ' + $_.Exception.Message) } }\"", timeout=20)

    # Test login via frontend proxy
    ssh_exec(ssh, "powershell -Command \"try { $r = Invoke-WebRequest -Uri 'http://localhost:8080/api/v1/auth/login' -Method POST -Body '{\\\"username\\\":\\\"admin\\\",\\\"password\\\":\\\"admin123\\\",\\\"auth_type\\\":\\\"password\\\"}' -ContentType 'application/json' -UseBasicParsing -TimeoutSec 10; Write-Host ('Proxy Login: HTTP ' + $r.StatusCode + ' - ' + $r.Content.Substring(0, [Math]::Min(300, $r.Content.Length))) } catch { $resp = $_.Exception.Response; if ($resp) { $reader = New-Object System.IO.StreamReader($resp.GetResponseStream()); Write-Host ('Proxy Login: ' + $reader.ReadToEnd().Substring(0, [Math]::Min(300, $reader.ReadToEnd().Length))) } else { Write-Host ('Proxy Login: ' + $_.Exception.Message) } }\"", timeout=20)

    # Check all listening ports
    ssh_exec(ssh, "netstat -ano | findstr LISTENING | findstr \"8000 8080\"", timeout=15)

    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE")
    print("="*60)
    print(f"  Frontend: http://{HOST}:8080")
    print(f"  Backend:  http://{HOST}:8000")
    print(f"  Login:    admin / admin123")
    print(f"  API:      http://{HOST}:8080/api/v1/auth/login")
    print("="*60)

    ssh.close()

if __name__ == "__main__":
    main()
