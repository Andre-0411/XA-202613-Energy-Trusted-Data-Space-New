"""修复 CSRF 问题: 重命名旧 middleware/ 目录"""
import paramiko, time, json, http.cookiejar, urllib.request, urllib.error

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to 10.241.2.64...")
ssh.connect('10.241.2.64', username='zhouxuying', password='zhouxuying51')
print("Connected!")

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    print(f">>> {cmd}")
    if out: print(out)
    if err: print(f"ERR: {err}")
    return out, err

# 1. 停止后端
run(r'schtasks /end /tn ETDS-Backend')

# 2. 删除 __pycache__
run(r'rmdir /s /q "D:\Andre\project\energy-trusted-data-space\backend\app\middleware\__pycache__"')

# 3. 检查 middleware_old 是否已存在
out, _ = run(r'dir "D:\Andre\project\energy-trusted-data-space\backend\app\middleware_old" 2>nul')
if 'middleware_old' in out:
    print("middleware_old already exists, removing old one first...")
    run(r'rmdir /s /q "D:\Andre\project\energy-trusted-data-space\backend\app\middleware_old"')

# 4. 重命名旧目录
run(r'ren "D:\Andre\project\energy-trusted-data-space\backend\app\middleware" middleware_old')

# 5. 验证
out, _ = run(r'dir "D:\Andre\project\energy-trusted-data-space\backend\app\middleware.py"')
print(f"middleware.py exists: {'middleware.py' in out}")

# 6. 重启后端
run(r'schtasks /run /tn ETDS-Backend')

# 7. 等待后端启动
print("\nWaiting for backend to start...")
for i in range(20):
    time.sleep(2)
    try:
        out, _ = run(f'curl -s -w "\\nHTTP_CODE:%%{{http_code}}" -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{{\\"username\\":\\"admin\\",\\"password\\":\\"admin123\\"}}"')
        if 'HTTP_CODE:200' in out:
            print(f"Backend ready after {(i+1)*2}s!")
            break
    except:
        pass
    print(f"  waiting... ({(i+1)*2}s)")
else:
    print("Backend may not be ready, continuing anyway...")

# 8. 测试模拟浏览器请求
print("\n--- Testing browser-like request through proxy ---")

# 写测试脚本到服务器
test_script = r'''
import http.cookiejar, urllib.request, urllib.error, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# GET to get csrf cookie
resp1 = opener.open("http://127.0.0.1:8080/", timeout=10)
print("GET / status:", resp1.status)
print("Cookies:", [c.name for c in cj])

# POST login with Origin header (simulating browser)
body = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request("http://127.0.0.1:8080/api/v1/auth/login", data=body, method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("Origin", "http://10.241.2.64:8080")
try:
    resp = opener.open(req, timeout=10)
    print("POST login via proxy:", resp.status)
    data = json.loads(resp.read().decode())
    user = data.get("data", {}).get("user", {}).get("username", "N/A")
    print("  user:", user)
except urllib.error.HTTPError as e:
    print("POST login FAILED:", e.code)
    print("  body:", e.read().decode()[:300])
'''

sftp = ssh.open_sftp()
with sftp.open('D:/Andre/project/energy-trusted-data-space/test_browser_csrf.py', 'w') as f:
    f.write(test_script)

stdin, stdout, stderr = ssh.exec_command(
    r'cd /d D:\Andre\project\energy-trusted-data-space && python test_browser_csrf.py',
    timeout=30
)
print(stdout.read().decode('gbk', errors='replace'))
err = stderr.read().decode('gbk', errors='replace')
if err: print(f"STDERR: {err[:300]}")

ssh.close()
print("\nDone!")
