"""在服务器上直接测试 session 端点"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)

def upload_text(ssh, path, content):
    sftp = ssh.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close()

# 上传测试脚本
test_py = '''import urllib.request
import urllib.error
import json

BASE = "http://127.0.0.1:8000"

def do_req(method, path, body=None, token=None):
    url = BASE + path
    hd = {"Content-Type": "application/json"} if body else {}
    if token:
        hd["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=15)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)

# 1. 登录
print("=== Login ===")
code, body = do_req("POST", "/api/v1/auth/login", {"username":"admin","password":"admin123","auth_type":"password"})
print(f"HTTP {code}")
data = json.loads(body)
if data.get("code") == 0:
    token = data["data"]["access_token"]
    print(f"Token OK: {token[:40]}...")
else:
    print(f"FAIL: {data}")
    exit(1)

# 2. Session
print("\\n=== Session ===")
code, body = do_req("GET", "/api/v1/auth/session", token=token)
print(f"HTTP {code}")
print(f"Body: {body[:500]}")

# 3. Users
print("\\n=== Users ===")
code, body = do_req("GET", "/api/v1/ops/users", token=token)
print(f"HTTP {code}")
print(f"Body: {body[:500]}")

# 4. Notifications
print("\\n=== Notifications ===")
code, body = do_req("GET", "/api/v1/notifications", token=token)
print(f"HTTP {code}")
print(f"Body: {body[:300]}")
'''

upload_text(ssh, f"{PROJECT}\\test_session.py", test_py)

stdin, stdout, stderr = ssh.exec_command(f'python "{PROJECT}\\test_session.py"', timeout=30)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(out)
if err:
    print(f"\nSTDERR:\n{err}")

ssh.close()
