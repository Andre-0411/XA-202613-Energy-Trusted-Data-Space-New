"""等待后端启动后测试"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"

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

# 等待后端启动
print("等待后端启动...")
for i in range(8):
    time.sleep(5)
    out, _ = run('netstat -an | findstr ":8000" | findstr "LISTENING"')
    if out:
        print(f"  ✓ 后端已启动 (第 {i+1} 次检查)")
        break
    print(f"  等待中... ({i+1}/8)")
else:
    print("  ⚠ 后端启动超时")
    out, _ = run(f'type "{PROJECT}\\uvicorn.log" 2>nul')
    print(f"  日志: {out[-500:]}")

# 测试
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
            d = data.get("data", {})
            if isinstance(d, dict):
                if "total" in d:
                    detail = f"total={d.get('total', 'N/A')}"
                elif "username" in d:
                    detail = f"user={d.get('username', 'N/A')}"
                elif "items" in d:
                    detail = f"items={len(d.get('items', []))}"
        elif code != 200:
            detail = str(data)[:100]
        print(f"\n{name}: HTTP {code} [{status}] {detail}")
else:
    print(f"  FAIL: {data}")
'''

upload_text(ssh, f"{PROJECT}\\test_final2.py", test_py)
stdin, stdout, stderr = ssh.exec_command(f'python "{PROJECT}\\test_final2.py"', timeout=60)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(f"\n{out}")
if err:
    print(f"\nSTDERR:\n{err}")

ssh.close()
