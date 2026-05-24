#!/usr/bin/env python3
"""
完整部署脚本 v2：后端 uvicorn + 前端代理服务器
修复：种子数据用直接SQL、服务用schtasks持久化
"""
import paramiko
import time
import json
import os

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"
BACKEND_DIR = f"{PROJECT_DIR}\\backend"

# === 前端代理服务器代码 ===
FRONTEND_PROXY_SCRIPT = r'''#!/usr/bin/env python3
"""前端服务器：静态文件 + API 反向代理"""
import http.server
import urllib.request
import urllib.error
import os
import json

PORT = 8080
BACKEND_URL = "http://127.0.0.1:8000"
STATIC_DIR = r"D:\Andre\project\energy-trusted-data-space\frontend\dist"

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith('/api/') or self.path.startswith('/ws/'):
            self._proxy_request('GET')
        else:
            file_path = os.path.join(STATIC_DIR, self.path.lstrip('/'))
            if not os.path.exists(file_path) and '.' not in os.path.split(self.path)[-1]:
                self.path = '/index.html'
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self._proxy_request('POST')
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith('/api/'):
            self._proxy_request('PUT')
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self._proxy_request('DELETE')
        else:
            self.send_error(404)

    def do_PATCH(self):
        if self.path.startswith('/api/'):
            self._proxy_request('PATCH')
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def _proxy_request(self, method):
        url = BACKEND_URL + self.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        headers = {}
        for key in ['Content-Type', 'Authorization', 'Accept', 'Origin', 'X-Requested-With']:
            val = self.headers.get(key)
            if val:
                headers[key] = val
        headers['Host'] = '127.0.0.1:8000'

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_body = resp.read()
                self.send_response(resp.status)
                for key, val in resp.getheaders():
                    if key.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(key, val)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_body)
        except urllib.error.HTTPError as e:
            response_body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_body)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        if args and '/api/' in str(args[0]):
            print(f"[{self.log_date_time_string()}] {format % args}")

if __name__ == '__main__':
    print(f"Frontend server: http://0.0.0.0:{PORT}")
    print(f"Static dir: {STATIC_DIR}")
    print(f"API proxy: {BACKEND_URL}")
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    server.serve_forever()
'''

# === 种子数据 SQL (直接插入，不依赖 ORM) ===
SEED_SQL = r'''import asyncio
import uuid
import hashlib
import os
import sys

sys.path.insert(0, r"D:\Andre\project\energy-trusted-data-space\backend")
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "energy_trusted"
os.environ["POSTGRES_USER"] = "energy"
os.environ["POSTGRES_PASSWORD"] = "Andre0411"

from sqlalchemy import text
from app.database import async_engine, AsyncSessionLocal

def hash_pwd(pw):
    salt = "energy_tds_salt"
    return hashlib.sha256(f"{salt}{pw}".encode()).hexdigest()

async def seed():
    async with AsyncSessionLocal() as session:
        # Check if users exist
        r = await session.execute(text("SELECT count(*) FROM users"))
        if r.scalar() > 0:
            print("Users already exist, skipping seed")
            return

        org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        dept_id = uuid.UUID("10000000-0000-0000-0000-000000000001")

        # Create org
        await session.execute(text("""
            INSERT INTO organizations (id, name, code, level, status, did, metadata, created_at, updated_at)
            VALUES (:id, :name, :code, :level, :status, :did, '{}', NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"id": org_id, "name": "能源可信数据空间平台", "code": "ETDS-PLATFORM", "level": 1, "status": "active", "did": "did:fisco:etds:platform:001"})

        # Create dept
        await session.execute(text("""
            INSERT INTO departments (id, name, organization_id, status, created_at)
            VALUES (:id, :name, :org_id, 'active', NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"id": dept_id, "name": "平台运营部", "org_id": org_id})

        users = [
            (uuid.UUID("20000000-0000-0000-0000-000000000001"), "admin", "admin123", "admin@etds.energy", "admin"),
            (uuid.UUID("20000000-0000-0000-0000-000000000002"), "security_admin", "security123", "security@etds.energy", "admin"),
            (uuid.UUID("20000000-0000-0000-0000-000000000003"), "data_admin_hn", "data123", "data@hn-power.com", "data_admin"),
            (uuid.UUID("20000000-0000-0000-0000-000000000005"), "auditor", "auditor123", "auditor@etds.energy", "auditor"),
        ]
        for uid, uname, pwd, email, role in users:
            await session.execute(text("""
                INSERT INTO users (id, username, password_hash, email, phone, role,
                    organization_id, department_id, status, mfa_enabled, login_fail_count, created_at, updated_at)
                VALUES (:id, :uname, :pwd, :email, :phone, :role,
                    :org_id, :dept_id, 'active', false, 0, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """), {"id": uid, "uname": uname, "pwd": hash_pwd(pwd), "email": email, "phone": "13800000001", "role": role, "org_id": org_id, "dept_id": dept_id})

        await session.commit()
        print(f"Seeded {len(users)} users")

asyncio.run(seed())
'''


def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)
    return ssh


def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err


def main():
    print(f"🚀 部署到 {HOST}\n")
    ssh = ssh_connect()

    try:
        # 1. 清理旧进程
        print("[1/6] 清理旧进程...")
        for port in [8000, 8080]:
            out, _ = run_cmd(ssh, f'netstat -ano | findstr ":{port}" | findstr "LISTENING"')
            if out:
                for line in out.strip().split('\n'):
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        if pid != '0':
                            run_cmd(ssh, f'taskkill /F /PID {pid} 2>nul')
                            print(f"  杀掉端口 {port} 进程 PID={pid}")
        time.sleep(1)
        print("  ✓ 清理完成\n")

        # 2. 上传文件
        print("[2/6] 上传部署文件...")
        sftp = ssh.open_sftp()
        files = [
            (f"{PROJECT_DIR}\\serve_frontend.py", FRONTEND_PROXY_SCRIPT),
            (f"{PROJECT_DIR}\\seed_users.py", SEED_SQL),
        ]
        for path, content in files:
            with sftp.open(path, 'w') as f:
                f.write(content.encode('utf-8'))
            print(f"  ✓ {os.path.basename(path)}")
        sftp.close()
        print()

        # 3. 种子数据
        print("[3/6] 初始化种子数据...")
        out, err = run_cmd(ssh, f'cd /d {BACKEND_DIR} && python {PROJECT_DIR}\\seed_users.py', timeout=30)
        print(f"  {out}")
        if err and 'error' in err.lower():
            print(f"  ⚠ {err[:300]}")
        print()

        # 4. 启动后端 (用 schtasks 持久化)
        print("[4/6] 启动后端 uvicorn...")
        # 创建 bat 文件
        uvicorn_bat = (
            f'@echo off\r\n'
            f'cd /d {BACKEND_DIR}\r\n'
            f'set POSTGRES_HOST=localhost\r\n'
            f'set POSTGRES_PORT=5432\r\n'
            f'set POSTGRES_DB=energy_trusted\r\n'
            f'set POSTGRES_USER=energy\r\n'
            f'set POSTGRES_PASSWORD=Andre0411\r\n'
            f'set PYTHONIOENCODING=utf-8\r\n'
            f'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000\r\n'
        )
        with sftp.open(f"{PROJECT_DIR}\\run_uvicorn.bat", 'w') as f:
            # Reopen sftp if needed
            pass
        # sftp was closed, use ssh exec instead
        run_cmd(ssh, (
            f'echo @echo off > "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo cd /d {BACKEND_DIR} >> "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo set POSTGRES_HOST=localhost >> "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo set POSTGRES_PORT=5432 >> "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo set POSTGRES_DB=energy_trusted >> "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo set POSTGRES_USER=energy >> "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo set POSTGRES_PASSWORD=Andre0411 >> "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo set PYTHONIOENCODING=utf-8 >> "{PROJECT_DIR}\\run_uvicorn.bat" && '
            f'echo python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "{PROJECT_DIR}\\run_uvicorn.bat"'
        ))

        run_cmd(ssh, 'schtasks /Create /TN "ETDS-Backend" /TR "cmd /c D:\\Andre\\project\\energy-trusted-data-space\\run_uvicorn.bat" /SC ONCE /ST 00:00 /F')
        run_cmd(ssh, 'schtasks /Run /TN "ETDS-Backend"')
        print("  等待后端启动...")
        time.sleep(6)

        out, _ = run_cmd(ssh, 'netstat -an | findstr ":8000" | findstr "LISTENING"')
        if out:
            print("  ✓ 后端已启动 (8000)")
        else:
            print("  ⚠ 后端未就绪，检查日志...")
            out, _ = run_cmd(ssh, f'type "{PROJECT_DIR}\\uvicorn.log" 2>nul')
            if out:
                print(f"  日志: {out[-300:]}")
        print()

        # 5. 启动前端
        print("[5/6] 启动前端服务器...")
        frontend_bat = (
            f'@echo off\r\n'
            f'cd /d {PROJECT_DIR}\r\n'
            f'set PYTHONIOENCODING=utf-8\r\n'
            f'python serve_frontend.py\r\n'
        )
        run_cmd(ssh, (
            f'echo @echo off > "{PROJECT_DIR}\\run_frontend.bat" && '
            f'echo cd /d {PROJECT_DIR} >> "{PROJECT_DIR}\\run_frontend.bat" && '
            f'echo set PYTHONIOENCODING=utf-8 >> "{PROJECT_DIR}\\run_frontend.bat" && '
            f'echo python serve_frontend.py >> "{PROJECT_DIR}\\run_frontend.bat"'
        ))

        run_cmd(ssh, 'schtasks /Create /TN "ETDS-Frontend" /TR "cmd /c D:\\Andre\\project\\energy-trusted-data-space\\run_frontend.bat" /SC ONCE /ST 00:00 /F')
        run_cmd(ssh, 'schtasks /Run /TN "ETDS-Frontend"')
        time.sleep(3)

        out, _ = run_cmd(ssh, 'netstat -an | findstr ":8080" | findstr "LISTENING"')
        if out:
            print("  ✓ 前端已启动 (8080)")
        else:
            print("  ⚠ 前端未就绪")
        print()

        # 6. 验证
        print("[6/6] 验证服务...")
        out, _ = run_cmd(ssh, 'netstat -an | findstr "LISTENING" | findstr ":8000 :8080"')
        print(f"  端口: {out if out else '无'}")

        # 测试 API
        out, _ = run_cmd(ssh, 'curl -s http://localhost:8000/api/v1/health')
        print(f"  后端 API: {out[:100] if out else '无响应'}")

        # 测试前端
        out, _ = run_cmd(ssh, 'curl -s -o nul -w "HTTP%%{http_code}" http://localhost:8080/')
        print(f"  前端: {out}")

        print()
        print("=" * 60)
        print("🎉 部署完成!")
        print("=" * 60)
        print(f"  📱 前端: http://{HOST}:8080")
        print(f"  🔧 后端: http://{HOST}:8000")
        print(f"  👤 管理员: admin / admin123")
        print()

    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
