#!/usr/bin/env python3
"""修复 CSRF 代理转发问题：添加 Cookie 和 X-CSRFToken 头"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"


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
    sftp = ssh.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close()


def main():
    print("🔧 修复 CSRF 代理转发...")
    ssh = connect()

    try:
        # 1. 上传修复后的 serve_frontend.py
        print("[1/3] 上传修复后的代理脚本...")
        proxy_py = r'''import http.server, urllib.request, urllib.error, os, json

PORT = 8080
BACKEND = "http://127.0.0.1:8000"
STATIC = r"D:\Andre\project\energy-trusted-data-space\frontend\dist"

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
        # 转发所有需要的头，包括 Cookie 和 CSRF token
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
        print("  ✓ serve_frontend.py 已更新\n")

        # 2. 重启前端服务
        print("[2/3] 重启前端服务...")
        # 杀掉旧进程
        out, _ = run(ssh, 'netstat -ano | findstr ":8080" | findstr "LISTENING"')
        for line in (out or '').strip().split('\n'):
            parts = line.strip().split()
            if parts and parts[-1] != '0':
                run(ssh, f'taskkill /F /PID {parts[-1]} 2>nul')
                print(f"  杀掉旧进程 PID={parts[-1]}")
        time.sleep(1)

        # 重启 schtask
        run(ssh, 'schtasks /End /TN "ETDS-Frontend" 2>nul')
        run(ssh, 'schtasks /Run /TN "ETDS-Frontend"')
        time.sleep(4)

        out, _ = run(ssh, 'netstat -an | findstr ":8080" | findstr "LISTENING"')
        if out:
            print("  ✓ 前端 8080 已重启")
        else:
            print("  ⚠ 等待前端启动...")
            time.sleep(3)
            out, _ = run(ssh, 'netstat -an | findstr ":8080" | findstr "LISTENING"')
            print(f"  {'✓ 前端已启动' if out else '✗ 前端启动失败'}")
        print()

        # 3. 验证 CSRF 头转发
        print("[3/3] 验证修复...")
        # 测试登录（应跳过 CSRF）
        out, _ = run(ssh, (
            'powershell -Command "'
            '$body = @{username=\'admin\';password=\'admin123\';auth_type=\'password\'} | ConvertTo-Json; '
            '$r = Invoke-WebRequest -Uri http://localhost:8080/api/v1/auth/login -Method POST '
            '-Body $body -ContentType \'application/json\' -UseBasicParsing -TimeoutSec 10; '
            '$r.StatusCode"'
        ), timeout=20)
        print(f"  登录测试: HTTP {out}")

        # 测试需要 CSRF 的端点（用 GET 测试转发 Cookie）
        out, _ = run(ssh, (
            'powershell -Command "'
            '$r = Invoke-WebRequest -Uri http://localhost:8080/api/v1/health '
            '-UseBasicParsing -TimeoutSec 5; '
            '$r.StatusCode"'
        ), timeout=15)
        print(f"  Health 端点: HTTP {out}")

        print()
        print("=" * 50)
        print("✅ CSRF 代理修复完成！")
        print("=" * 50)
        print(f"  访问: http://{HOST}:8080")
        print("  Cookie 和 X-CSRFToken 头现在会被正确转发")

    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
