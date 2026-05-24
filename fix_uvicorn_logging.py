"""修复 uvicorn 日志捕获，重启并测试"""
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

# 1. 创建带日志重定向的 uvicorn 启动脚本
print("[1] 更新后端启动脚本（添加日志捕获）...")
uvicorn_bat = '\r\n'.join([
    '@echo off',
    f'cd /d {PROJECT}\\backend',
    'set POSTGRES_HOST=localhost',
    'set POSTGRES_PORT=5432',
    'set POSTGRES_DB=energy_trusted',
    'set POSTGRES_USER=energy',
    'set POSTGRES_PASSWORD=Andre0411',
    'set PYTHONIOENCODING=utf-8',
    f'python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "{PROJECT}\\uvicorn.log" 2>&1',
])
upload_text(ssh, f"{PROJECT}\\run_uvicorn.bat", uvicorn_bat)
print("  ✓ run_uvicorn.bat 已更新\n")

# 2. 杀掉旧 uvicorn
print("[2] 重启后端...")
out, _ = run('netstat -ano | findstr ":8000" | findstr "LISTENING"')
for line in (out or '').strip().split('\n'):
    parts = line.strip().split()
    if parts and parts[-1] != '0':
        run(f'taskkill /F /PID {parts[-1]} 2>nul')
        print(f"  杀掉 PID={parts[-1]}")
time.sleep(2)

# 重启 schtask
run('schtasks /End /TN "ETDS-Backend" 2>nul')
run('schtasks /Run /TN "ETDS-Backend"')
time.sleep(8)

out, _ = run('netstat -an | findstr ":8000" | findstr "LISTENING"')
print(f"  {'✓ 后端已启动' if out else '✗ 后端未启动'}\n")

# 3. 触发一个 session 请求产生错误
print("[3] 触发 session 请求...")
test_py = '''import urllib.request, urllib.error, json
BASE = "http://127.0.0.1:8000"
# Login
r = urllib.request.Request(
    BASE + "/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123","auth_type":"password"}).encode(),
    headers={"Content-Type":"application/json"},
    method="POST"
)
resp = urllib.request.urlopen(r, timeout=10)
data = json.loads(resp.read().decode())
token = data["data"]["access_token"]
print(f"Login OK, token={token[:30]}...")

# Session
r2 = urllib.request.Request(
    BASE + "/api/v1/auth/session",
    headers={"Authorization": f"Bearer {token}"},
    method="GET"
)
try:
    resp2 = urllib.request.urlopen(r2, timeout=10)
    print(f"Session: {resp2.status} - {resp2.read().decode()[:200]}")
except urllib.error.HTTPError as e:
    print(f"Session ERROR: {e.code} - {e.read().decode()[:300]}")
'''
upload_text(ssh, f"{PROJECT}\\trigger_session.py", test_py)
out, err = run(f'python "{PROJECT}\\trigger_session.py"')
print(f"  {out}\n")

# 4. 读取 uvicorn 日志
print("[4] 读取 uvicorn 日志...")
time.sleep(1)
out, _ = run(f'type "{PROJECT}\\uvicorn.log" 2>nul')
if out:
    # 只显示最后的错误相关行
    lines = out.split('\n')
    # 找到包含 Error/Traceback/500 的行
    error_lines = []
    capture = False
    for line in lines:
        if any(kw in line for kw in ['Error', 'Traceback', 'Exception', '500', 'session', 'File "']):
            capture = True
        if capture:
            error_lines.append(line)
            if line.strip() == '' and len(error_lines) > 3:
                capture = False
    if error_lines:
        print("  错误日志:")
        print('\n'.join(error_lines[-50:]))
    else:
        print("  最后 30 行:")
        print('\n'.join(lines[-30:]))
else:
    print("  ⚠ 无日志文件")

ssh.close()
