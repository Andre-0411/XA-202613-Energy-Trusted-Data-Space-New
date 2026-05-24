"""检查后端状态并测试"""
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

# 检查端口
out, _ = run('netstat -an | findstr ":8000" | findstr "LISTENING"')
print(f"8000 端口: {out if out else '未监听'}")

out, _ = run('netstat -an | findstr ":8080" | findstr "LISTENING"')
print(f"8080 端口: {out if out else '未监听'}")

# 如果 8000 没启动，等待并重试
if not out or '8000' not in out:
    print("\n等待后端启动...")
    time.sleep(10)
    out, _ = run('netstat -an | findstr ":8000" | findstr "LISTENING"')
    print(f"8000 端口: {out if out else '仍未监听'}")

# 读取完整 uvicorn 日志
print("\n=== uvicorn.log ===")
out, _ = run(f'type "{PROJECT}\\uvicorn.log" 2>nul')
print(out[-5000:] if out else "(空)")

# 测试端点
print("\n=== 端点测试 ===")
test_py = '''import urllib.request, urllib.error, json
BASE = "http://127.0.0.1:8000"

def test(method, path, body=None, token=None):
    url = BASE + path
    hd = {"Content-Type": "application/json"} if body else {}
    if token: hd["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        return resp.status, resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)[:200]

# Login
code, body = test("POST", "/api/v1/auth/login", {"username":"admin","password":"admin123","auth_type":"password"})
print(f"Login: {code} - {body[:100]}")
if code == 200:
    data = json.loads(body) if code == 200 else {}
    if data.get("code") == 0:
        token = data["data"]["access_token"]
        # Session
        code, body = test("GET", "/api/v1/auth/session", token=token)
        print(f"Session: {code} - {body[:200]}")
        # Ops Users
        code, body = test("GET", "/api/v1/ops/users", token=token)
        print(f"Users: {code} - {body[:200]}")
'''

stdin, stdout, stderr = ssh.exec_command(f'python -c "{test_py}"', timeout=30)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(out)
if err: print(f"STDERR: {err[:500]}")

ssh.close()
