"""修复 pagination.py 的 UUID 序列化问题"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"
BACKEND = f"{PROJECT}\\backend"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err

def upload_text(ssh, path, content):
    sftp = ssh.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close()

# 1. 上传修复后的 pagination.py
print("[1] 上传修复后的 pagination.py...")
with open(r"D:\Projects\energy-trusted-data-space\backend\app\utils\pagination.py", 'r', encoding='utf-8') as f:
    content = f.read()
upload_text(ssh, f"{BACKEND}\\app\\utils\\pagination.py", content)
print("  ✓ pagination.py 已上传\n")

# 2. 重启后端
print("[2] 重启后端...")
out, _ = run('netstat -ano | findstr ":8000" | findstr "LISTENING"')
for line in (out or '').strip().split('\n'):
    parts = line.strip().split()
    if parts and parts[-1] != '0':
        run(f'taskkill /F /PID {parts[-1]} 2>nul')
        print(f"  杀掉 PID={parts[-1]}")
time.sleep(2)

run('schtasks /End /TN "ETDS-Backend" 2>nul')
run('schtasks /Run /TN "ETDS-Backend"')
time.sleep(12)

out, _ = run('netstat -an | findstr ":8000" | findstr "LISTENING"')
print(f"  {'✓ 后端已启动' if out else '✗ 后端未启动'}\n")

# 3. 测试
print("[3] 测试所有端点...")
test_py = r'''import urllib.request, urllib.error, json

BASE = "http://127.0.0.1:8000"

def test(method, path, body=None, token=None):
    url = BASE + path
    hd = {"Content-Type": "application/json"} if body else {}
    if token: hd["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=15)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except:
            return e.code, {"raw": e.read().decode()[:200]}
    except Exception as e:
        return 0, {"error": str(e)}

# Login
code, data = test("POST", "/api/v1/auth/login", {"username":"admin","password":"admin123","auth_type":"password"})
print(f"Login: HTTP {code}")
if code == 200 and data.get("code") == 0:
    token = data["data"]["access_token"]
    print(f"  OK")
    
    endpoints = [
        ("Session", "GET", "/api/v1/auth/session"),
        ("Users", "GET", "/api/v1/ops/users"),
        ("Notifications", "GET", "/api/v1/notifications"),
        ("Organizations", "GET", "/api/v1/organizations"),
    ]
    
    for name, method, path in endpoints:
        code, data = test(method, path, token=token)
        status = "OK" if code == 200 else "FAIL"
        detail = ""
        if code == 200 and isinstance(data, dict) and data.get("code") == 0:
            if "total" in str(data.get("data", {})):
                detail = f"total={data['data'].get('total', 'N/A')}"
            elif "username" in str(data.get("data", {})):
                detail = f"user={data['data'].get('username', 'N/A')}"
        elif code != 200:
            detail = str(data)[:100]
        print(f"\n{name}: HTTP {code} [{status}] {detail}")
else:
    print(f"  FAIL: {data}")
'''

upload_text(ssh, f"{PROJECT}\\test_final.py", test_py)
stdin, stdout, stderr = ssh.exec_command(f'python "{PROJECT}\\test_final.py"', timeout=60)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(out)
if err:
    print(f"\nSTDERR:\n{err}")

ssh.close()
