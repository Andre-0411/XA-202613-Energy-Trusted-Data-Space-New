"""修复 Redis 连接问题并重启后端"""
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

# 1. 上传修复后的 deps.py
print("[1] 上传修复后的 deps.py...")
with open(r"D:\Projects\energy-trusted-data-space\backend\app\utils\deps.py", 'r', encoding='utf-8') as f:
    deps_content = f.read()
upload_text(ssh, f"{BACKEND}\\app\\utils\\deps.py", deps_content)
print("  ✓ deps.py 已上传\n")

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
time.sleep(10)

out, _ = run('netstat -an | findstr ":8000" | findstr "LISTENING"')
print(f"  {'✓ 后端已启动' if out else '✗ 后端未启动'}\n")

# 3. 测试
print("[3] 测试端点...")
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
    
    # Session
    code, data = test("GET", "/api/v1/auth/session", token=token)
    print(f"\nSession: HTTP {code}")
    if code == 200:
        print(f"  user={data.get('data',{}).get('username')} role={data.get('data',{}).get('role')}")
    else:
        print(f"  {data}")
    
    # Users
    code, data = test("GET", "/api/v1/ops/users", token=token)
    print(f"\nUsers: HTTP {code}")
    if code == 200:
        print(f"  total={data.get('data',{}).get('total', 'N/A')}")
    else:
        print(f"  {data}")
else:
    print(f"  FAIL: {data}")
'''

upload_text(ssh, f"{PROJECT}\\test_fix.py", test_py)
stdin, stdout, stderr = ssh.exec_command(f'python "{PROJECT}\\test_fix.py"', timeout=60)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(out)
if err:
    print(f"\nSTDERR:\n{err}")

ssh.close()
