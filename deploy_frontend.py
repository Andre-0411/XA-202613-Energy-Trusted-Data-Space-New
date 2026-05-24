#!/usr/bin/env python3
"""
完整部署脚本：后端 uvicorn + 前端代理服务器
在服务器 10.241.2.64 上同时启动前后端服务
"""
import paramiko
import time
import sys

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"
BACKEND_DIR = f"{PROJECT_DIR}\\backend"
FRONTEND_DIST = f"{PROJECT_DIR}\\frontend\\dist"

# === 前端代理服务器代码 (同时提供静态文件 + API 反向代理) ===
FRONTEND_PROXY_SCRIPT = r'''#!/usr/bin/env python3
"""前端服务器：静态文件 + API 反向代理"""
import http.server
import urllib.request
import urllib.error
import os
import sys
import threading

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
            # SPA fallback: 如果文件不存在且不是静态资源，返回 index.html
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
        if self.path.startswith('/api/'):
            self._proxy_request('OPTIONS')
        else:
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
            import json
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        # 只记录 API 请求，忽略静态资源
        if args and '/api/' in str(args[0]):
            print(f"[{self.log_date_time_string()}] {format % args}")

if __name__ == '__main__':
    print(f"前端服务器启动: http://0.0.0.0:{PORT}")
    print(f"静态文件目录: {STATIC_DIR}")
    print(f"API 代理目标: {BACKEND_URL}")
    server = http.server.HTTPServer(('0.0.0.0', PORT), ProxyHandler)
    server.serve_forever()
'''

# === 后端启动批处理 ===
UVICORN_BAT = r'''@echo off
cd /d D:\Andre\project\energy-trusted-data-space\backend
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set POSTGRES_DB=energy_trusted
set POSTGRES_USER=energy
set POSTGRES_PASSWORD=Andre0411
set PYTHONIOENCODING=utf-8
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > D:\Andre\project\energy-trusted-data-space\uvicorn.log 2>&1
'''

# === 前端启动批处理 ===
FRONTEND_BAT = r'''@echo off
cd /d D:\Andre\project\energy-trusted-data-space
set PYTHONIOENCODING=utf-8
python serve_frontend.py > D:\Andre\project\energy-trusted-data-space\frontend_server.log 2>&1
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


def step1_check_environment(ssh):
    """检查服务器环境"""
    print("=" * 60)
    print("步骤 1: 检查服务器环境")
    print("=" * 60)

    checks = [
        ("Python", "python --version"),
        ("Node.js", "node --version"),
        ("项目目录", f'if exist "{PROJECT_DIR}" (echo OK) else (echo MISSING)'),
        ("前端dist", f'if exist "{FRONTEND_DIST}" (echo OK) else (echo MISSING)'),
        ("端口8000", 'netstat -an | findstr ":8000"'),
        ("端口8080", 'netstat -an | findstr ":8080"'),
    ]

    for name, cmd in checks:
        out, err = run_cmd(ssh, cmd)
        status = out if out else "(空)"
        print(f"  {name}: {status}")

    print()
    return True


def step2_kill_existing(ssh):
    """杀掉已有的 uvicorn 和前端服务进程"""
    print("=" * 60)
    print("步骤 2: 清理已有进程")
    print("=" * 60)

    # 查找并杀掉占用 8000 和 8080 端口的进程
    for port in [8000, 8080]:
        out, _ = run_cmd(ssh, f'netstat -ano | findstr ":{port}" | findstr "LISTENING"')
        if out:
            for line in out.strip().split('\n'):
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    if pid != '0':
                        print(f"  杀掉端口 {port} 的进程 PID={pid}")
                        run_cmd(ssh, f'taskkill /F /PID {pid} 2>nul')
    time.sleep(1)

    # 检查端口是否清理干净
    for port in [8000, 8080]:
        out, _ = run_cmd(ssh, f'netstat -an | findstr ":{port}" | findstr "LISTENING"')
        if out:
            print(f"  ⚠ 端口 {port} 仍被占用: {out}")
        else:
            print(f"  ✓ 端口 {port} 已释放")

    print()
    return True


def step3_upload_files(ssh):
    """上传前端代理服务器和启动脚本"""
    print("=" * 60)
    print("步骤 3: 上传部署文件")
    print("=" * 60)

    sftp = ssh.open_sftp()

    # 上传前端代理服务器
    frontend_script_path = f"{PROJECT_DIR}\\serve_frontend.py"
    print(f"  上传: serve_frontend.py")
    with sftp.open(frontend_script_path, 'w') as f:
        f.write(FRONTEND_PROXY_SCRIPT.encode('utf-8'))

    # 上传后端启动脚本
    backend_bat_path = f"{PROJECT_DIR}\\start_uvicorn.bat"
    print(f"  上传: start_uvicorn.bat")
    with sftp.open(backend_bat_path, 'w') as f:
        f.write(UVICORN_BAT.encode('utf-8'))

    # 上传前端启动脚本
    frontend_bat_path = f"{PROJECT_DIR}\\start_frontend.bat"
    print(f"  上传: start_frontend.bat")
    with sftp.open(frontend_bat_path, 'w') as f:
        f.write(FRONTEND_BAT.encode('utf-8'))

    sftp.close()
    print("  ✓ 文件上传完成")
    print()
    return True


def step4_seed_database(ssh):
    """执行种子数据初始化"""
    print("=" * 60)
    print("步骤 4: 检查种子数据")
    print("=" * 60)

    # 先检查 users 表是否有数据
    cmd = (
        f'cd /d {BACKEND_DIR} && '
        f'set POSTGRES_HOST=localhost&& set POSTGRES_PORT=5432&& '
        f'set POSTGRES_DB=energy_trusted&& set POSTGRES_USER=energy&& '
        f'set POSTGRES_PASSWORD=Andre0411&& '
        f'python -c "'
        f"import asyncio; "
        f"from sqlalchemy import text; "
        f"from app.database import init_db, AsyncSessionLocal; "
        f"async def check(): "
        f"  await init_db(); "
        f"  async with AsyncSessionLocal() as s: "
        f"    r = await s.execute(text('SELECT count(*) FROM users')); "
        f"    print('USER_COUNT=' + str(r.scalar())); "
        f"asyncio.run(check())"
        f'"'
    )
    out, err = run_cmd(ssh, cmd, timeout=30)
    print(f"  数据库用户查询: {out}")
    if err:
        print(f"  错误: {err[:200]}")

    if 'USER_COUNT=0' in out or 'USER_COUNT=' not in out:
        print("  → 用户表为空或查询失败，执行种子数据...")
        cmd = (
            f'cd /d {BACKEND_DIR} && '
            f'set POSTGRES_HOST=localhost&& set POSTGRES_PORT=5432&& '
            f'set POSTGRES_DB=energy_trusted&& set POSTGRES_USER=energy&& '
            f'set POSTGRES_PASSWORD=Andre0411&& '
            f'python seed_data.py'
        )
        out, err = run_cmd(ssh, cmd, timeout=60)
        print(f"  种子数据结果: {out[:500]}")
        if err:
            print(f"  错误: {err[:300]}")
    else:
        print("  ✓ 用户表已有数据，跳过种子数据")

    print()
    return True


def step5_start_backend(ssh):
    """启动后端 uvicorn"""
    print("=" * 60)
    print("步骤 5: 启动后端 (uvicorn :8000)")
    print("=" * 60)

    # 使用 start 命令后台启动
    cmd = (
        f'cd /d {BACKEND_DIR} && '
        f'set POSTGRES_HOST=localhost&& '
        f'set POSTGRES_PORT=5432&& '
        f'set POSTGRES_DB=energy_trusted&& '
        f'set POSTGRES_USER=energy&& '
        f'set POSTGRES_PASSWORD=Andre0411&& '
        f'set PYTHONIOENCODING=utf-8&& '
        f'start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'
    )
    run_cmd(ssh, cmd)
    print("  启动命令已发送，等待...")
    time.sleep(5)

    # 检查端口
    out, _ = run_cmd(ssh, 'netstat -an | findstr ":8000" | findstr "LISTENING"')
    if out:
        print(f"  ✓ 后端已启动，8000 端口监听中")
    else:
        print(f"  ⚠ 8000 端口未就绪，再等几秒...")
        time.sleep(5)
        out, _ = run_cmd(ssh, 'netstat -an | findstr ":8000" | findstr "LISTENING"')
        if out:
            print(f"  ✓ 后端已启动")
        else:
            print(f"  ✗ 后端启动可能失败")
            # 检查日志
            out, _ = run_cmd(ssh, f'type "{PROJECT_DIR}\\uvicorn.log" 2>nul')
            if out:
                print(f"  日志: {out[-500:]}")

    print()
    return True


def step6_start_frontend(ssh):
    """启动前端代理服务器"""
    print("=" * 60)
    print("步骤 6: 启动前端服务器 (:8080)")
    print("=" * 60)

    cmd = (
        f'cd /d {PROJECT_DIR} && '
        f'set PYTHONIOENCODING=utf-8&& '
        f'start /B python serve_frontend.py'
    )
    run_cmd(ssh, cmd)
    print("  启动命令已发送，等待...")
    time.sleep(3)

    out, _ = run_cmd(ssh, 'netstat -an | findstr ":8080" | findstr "LISTENING"')
    if out:
        print(f"  ✓ 前端服务器已启动，8080 端口监听中")
    else:
        print(f"  ⚠ 8080 端口未就绪，再等...")
        time.sleep(3)
        out, _ = run_cmd(ssh, 'netstat -an | findstr ":8080" | findstr "LISTENING"')
        if out:
            print(f"  ✓ 前端服务器已启动")
        else:
            print(f"  ✗ 前端启动可能失败")

    print()
    return True


def step7_verify(ssh):
    """验证服务"""
    print("=" * 60)
    print("步骤 7: 验证服务")
    print("=" * 60)

    # 检查端口
    out, _ = run_cmd(ssh, 'netstat -an | findstr "LISTENING" | findstr ":8000 :8080"')
    print(f"  端口状态:\n{out}")

    # 测试后端 API
    out, err = run_cmd(ssh, 'curl -s -o nul -w "%%{http_code}" http://localhost:8000/api/v1/health 2>nul')
    print(f"  后端 /api/v1/health: HTTP {out}")

    # 测试前端
    out, err = run_cmd(ssh, 'curl -s -o nul -w "%%{http_code}" http://localhost:8080/ 2>nul')
    print(f"  前端首页: HTTP {out}")

    # 测试前端代理 API
    out, err = run_cmd(ssh, 'curl -s -o nul -w "%%{http_code}" http://localhost:8080/api/v1/health 2>nul')
    print(f"  前端代理 /api/v1/health: HTTP {out}")

    print()
    print("=" * 60)
    print("🎉 部署完成!")
    print("=" * 60)
    print(f"  前端访问: http://{HOST}:8080")
    print(f"  后端 API: http://{HOST}:8000")
    print(f"  管理员登录: admin / admin123")
    print()

    return True


def main():
    print(f"🚀 开始部署到服务器 {HOST}")
    print()

    ssh = ssh_connect()

    try:
        step1_check_environment(ssh)
        step2_kill_existing(ssh)
        step3_upload_files(ssh)
        step4_seed_database(ssh)
        step5_start_backend(ssh)
        step6_start_frontend(ssh)
        step7_verify(ssh)
    except Exception as e:
        print(f"\n❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
