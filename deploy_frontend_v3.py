#!/usr/bin/env python3
"""
部署脚本 v3：全部通过 SSH exec，不用 SFTP
后端 uvicorn + 前端代理服务器
"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"
BACKEND = f"{PROJECT}\\backend"


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)
    return ssh


def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err


def upload_text(ssh, path, content):
    """通过 SFTP 上传文本文件"""
    sftp = ssh.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content.encode('utf-8'))
    sftp.close()


def main():
    print(f"🚀 部署到 {HOST}\n")
    ssh = connect()

    try:
        # ── 1. 清理旧进程 ──
        print("[1/7] 清理旧进程...")
        for port in [8000, 8080]:
            out, _ = run(ssh, f'netstat -ano | findstr ":{port}" | findstr "LISTENING"')
            for line in (out or '').strip().split('\n'):
                parts = line.strip().split()
                if parts and parts[-1] != '0':
                    run(ssh, f'taskkill /F /PID {parts[-1]} 2>nul')
                    print(f"  杀掉端口 {port} PID={parts[-1]}")
        time.sleep(1)
        # 删除旧计划任务
        run(ssh, 'schtasks /Delete /TN "ETDS-Backend" /F 2>nul')
        run(ssh, 'schtasks /Delete /TN "ETDS-Frontend" /F 2>nul')
        print("  ✓ 清理完成\n")

        # ── 2. 上传前端代理脚本 ──
        print("[2/7] 上传前端代理脚本...")
        proxy_py = '''\
import http.server, urllib.request, urllib.error, os, json

PORT = 8080
BACKEND = "http://127.0.0.1:8000"
STATIC = r"D:\\Andre\\project\\energy-trusted-data-space\\frontend\\dist"

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STATIC, **kw)

    def do_GET(self):
        if self.path.startswith(('/api/', '/ws/')):
            return self._proxy('GET')
        fp = os.path.join(STATIC, self.path.lstrip('/'))
        if not os.path.exists(fp) and '.' not in os.path.split(self.path)[-1]:
            self.path = '/index.html'
        super().do_GET()

    def do_POST(self):
        self._proxy('POST') if self.path.startswith('/api/') else self.send_error(404)

    def do_PUT(self):
        self._proxy('PUT') if self.path.startswith('/api/') else self.send_error(404)

    def do_DELETE(self):
        self._proxy('DELETE') if self.path.startswith('/api/') else self.send_error(404)

    def do_PATCH(self):
        self._proxy('PATCH') if self.path.startswith('/api/') else self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        for h in [('Access-Control-Allow-Origin','*'),
                   ('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,PATCH,OPTIONS'),
                   ('Access-Control-Allow-Headers','*')]:
            self.send_header(*h)
        self.end_headers()

    def _proxy(self, method):
        url = BACKEND + self.path
        cl = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(cl) if cl > 0 else None
        hd = {}
        for k in ['Content-Type','Authorization','Accept','Origin','X-Requested-With','Cookie','X-CSRFToken']:
            v = self.headers.get(k)
            if v: hd[k] = v
        hd['Host'] = '127.0.0.1:8000'
        try:
            req = urllib.request.Request(url, data=body, headers=hd, method=method)
            with urllib.request.urlopen(req, timeout=120) as resp:
                rb = resp.read()
                self.send_response(resp.status)
                for k2, v2 in resp.getheaders():
                    if k2.lower() not in ('transfer-encoding','connection'):
                        self.send_header(k2, v2)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(rb)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(json.dumps({"error":str(e)}).encode())

    def log_message(self, fmt, *args):
        if args and '/api/' in str(args[0]):
            super().log_message(fmt, *args)

print(f"Frontend: http://0.0.0.0:{PORT}")
http.server.HTTPServer(('0.0.0.0', PORT), H).serve_forever()
'''
        upload_text(ssh, f"{PROJECT}\\serve_frontend.py", proxy_py)
        print("  ✓ serve_frontend.py\n")

        # ── 3. 种子数据 (用 raw asyncpg 绕过 app 初始化) ──
        print("[3/7] 初始化种子数据...")
        seed_py = r'''import asyncio, hashlib, uuid, sys
sys.path.insert(0, r"D:\Andre\project\energy-trusted-data-space\backend")
import asyncpg

SALT = "energy_tds_salt"
def hpw(p): return hashlib.sha256(f"{SALT}{p}".encode()).hexdigest()

async def main():
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        database="energy_trusted", user="energy", password="Andre0411"
    )
    cnt = await conn.fetchval("SELECT count(*) FROM users")
    if cnt and cnt > 0:
        print(f"Users already exist ({cnt}), skipping")
        await conn.close()
        return

    org_id = "00000000-0000-0000-0000-000000000001"
    dept_id = "10000000-0000-0000-0000-000000000001"

    await conn.execute("""
        INSERT INTO organizations (id, name, code, level, status, did, metadata, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, '{}', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """, uuid.UUID(org_id), "能源可信数据空间平台", "ETDS-PLATFORM", 1, "active", "did:fisco:etds:platform:001")

    await conn.execute("""
        INSERT INTO departments (id, name, organization_id, status, created_at)
        VALUES ($1, $2, $3, 'active', NOW())
        ON CONFLICT (id) DO NOTHING
    """, uuid.UUID(dept_id), "平台运营部", uuid.UUID(org_id))

    users = [
        ("20000000-0000-0000-0000-000000000001", "admin",          "admin123",     "admin@etds.energy",    "admin"),
        ("20000000-0000-0000-0000-000000000002", "security_admin", "security123",  "security@etds.energy", "admin"),
        ("20000000-0000-0000-0000-000000000005", "auditor",        "auditor123",   "auditor@etds.energy",  "auditor"),
    ]
    for uid, uname, pwd, email, role in users:
        try:
            await conn.execute("""
                INSERT INTO users (id, username, password_hash, email, phone, role,
                    organization_id, department_id, status, mfa_enabled, login_fail_count, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', false, 0, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """, uuid.UUID(uid), uname, hpw(pwd), email, "13800000001", role,
               uuid.UUID(org_id), uuid.UUID(dept_id))
            print(f"  + {uname} ({role})")
        except Exception as e:
            print(f"  ! {uname}: {e}")

    await conn.close()
    print("Seed done")

asyncio.run(main())
'''
        upload_text(ssh, f"{PROJECT}\\seed_users.py", seed_py)
        out, err = run(ssh, f'python "{PROJECT}\\seed_users.py"', timeout=30)
        print(f"  {out}")
        if err:
            for line in err.split('\n'):
                if 'error' in line.lower() or 'traceback' in line.lower():
                    print(f"  ⚠ {line}")
        print()

        # ── 4. 创建后端启动 bat ──
        print("[4/7] 创建启动脚本...")
        uvicorn_bat = '\r\n'.join([
            '@echo off',
            f'cd /d {BACKEND}',
            'set POSTGRES_HOST=localhost',
            'set POSTGRES_PORT=5432',
            'set POSTGRES_DB=energy_trusted',
            'set POSTGRES_USER=energy',
            'set POSTGRES_PASSWORD=Andre0411',
            'set PYTHONIOENCODING=utf-8',
            'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000',
        ])
        upload_text(ssh, f"{PROJECT}\\run_uvicorn.bat", uvicorn_bat)
        print("  ✓ run_uvicorn.bat")

        frontend_bat = '\r\n'.join([
            '@echo off',
            f'cd /d {PROJECT}',
            'set PYTHONIOENCODING=utf-8',
            'python serve_frontend.py',
        ])
        upload_text(ssh, f"{PROJECT}\\run_frontend.bat", frontend_bat)
        print("  ✓ run_frontend.bat\n")

        # ── 5. 启动后端 ──
        print("[5/7] 启动后端 uvicorn (schtask)...")
        run(ssh, f'schtasks /Create /TN "ETDS-Backend" /TR "cmd /c {PROJECT}\\run_uvicorn.bat" /SC ONCE /ST 00:00 /F')
        run(ssh, 'schtasks /Run /TN "ETDS-Backend"')
        print("  等待启动...")
        time.sleep(8)

        out, _ = run(ssh, 'netstat -an | findstr ":8000" | findstr "LISTENING"')
        if out:
            print("  ✓ 后端 8000 已启动")
        else:
            print("  ⚠ 8000 未就绪，等待更久...")
            time.sleep(5)
            out, _ = run(ssh, 'netstat -an | findstr ":8000" | findstr "LISTENING"')
            print(f"  {'✓ 后端已启动' if out else '✗ 后端启动失败'}")
            if not out:
                out2, _ = run(ssh, 'schtasks /Query /TN "ETDS-Backend" /FO LIST 2>nul')
                print(f"  任务状态: {out2[:200]}")
        print()

        # ── 6. 启动前端 ──
        print("[6/7] 启动前端服务器 (schtask)...")
        run(ssh, f'schtasks /Create /TN "ETDS-Frontend" /TR "cmd /c {PROJECT}\\run_frontend.bat" /SC ONCE /ST 00:00 /F')
        run(ssh, 'schtasks /Run /TN "ETDS-Frontend"')
        time.sleep(4)

        out, _ = run(ssh, 'netstat -an | findstr ":8080" | findstr "LISTENING"')
        if out:
            print("  ✓ 前端 8080 已启动")
        else:
            print("  ⚠ 8080 未就绪，等待...")
            time.sleep(3)
            out, _ = run(ssh, 'netstat -an | findstr ":8080" | findstr "LISTENING"')
            print(f"  {'✓ 前端已启动' if out else '✗ 前端启动失败'}")
            if not out:
                out2, _ = run(ssh, f'type "{PROJECT}\\frontend_server.log" 2>nul')
                if out2:
                    print(f"  日志: {out2[-300:]}")
        print()

        # ── 7. 验证 ──
        print("[7/7] 验证服务...")
        out, _ = run(ssh, 'netstat -an | findstr "LISTENING" | findstr ":8000 :8080"')
        print(f"  端口: {out if out else '无'}")

        # 用 PowerShell 测试 HTTP (避免 curl 转义问题)
        out, _ = run(ssh, 'powershell -Command "(Invoke-WebRequest -Uri http://localhost:8000/api/v1/health -UseBasicParsing -TimeoutSec 5).StatusCode" 2>nul')
        print(f"  后端 API: HTTP {out}")

        out, _ = run(ssh, 'powershell -Command "(Invoke-WebRequest -Uri http://localhost:8080/ -UseBasicParsing -TimeoutSec 5).StatusCode" 2>nul')
        print(f"  前端页面: HTTP {out}")

        out, _ = run(ssh, 'powershell -Command "(Invoke-WebRequest -Uri http://localhost:8080/api/v1/health -UseBasicParsing -TimeoutSec 5).StatusCode" 2>nul')
        print(f"  前端代理API: HTTP {out}")

        print()
        print("=" * 60)
        print("🎉 部署完成!")
        print("=" * 60)
        print(f"  📱 前端访问: http://{HOST}:8080")
        print(f"  🔧 后端 API: http://{HOST}:8000")
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
