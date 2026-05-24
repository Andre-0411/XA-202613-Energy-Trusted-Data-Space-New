"""检查 users 端点的 500 错误"""
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

# 触发 users 请求
test_py = r'''import urllib.request, urllib.error, json
BASE = "http://127.0.0.1:8000"
# Login
r = urllib.request.Request(
    BASE + "/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123","auth_type":"password"}).encode(),
    headers={"Content-Type":"application/json"}, method="POST"
)
resp = urllib.request.urlopen(r, timeout=10)
data = json.loads(resp.read().decode())
token = data["data"]["access_token"]

# Users
r2 = urllib.request.Request(
    BASE + "/api/v1/ops/users",
    headers={"Authorization": f"Bearer {token}"}, method="GET"
)
try:
    resp2 = urllib.request.urlopen(r2, timeout=10)
    print(f"Users: {resp2.status}")
except urllib.error.HTTPError as e:
    print(f"Users ERROR: {e.code}")
    print(e.read().decode()[:500])
'''
upload_text(ssh, f"{PROJECT}\\trigger_users.py", test_py)
run(f'python "{PROJECT}\\trigger_users.py"')
time.sleep(1)

# 读取日志
out, _ = run(f'type "{PROJECT}\\uvicorn.log" 2>nul')
if out:
    # 找最近的错误
    lines = out.split('\n')
    error_lines = []
    capture = False
    for line in lines:
        if 'Error' in line or 'Traceback' in line or 'Exception' in line:
            capture = True
        if capture:
            error_lines.append(line)
        if capture and line.strip() == '' and len(error_lines) > 5:
            capture = False
    if error_lines:
        print("最近的错误:")
        print('\n'.join(error_lines[-40:]))
    else:
        print("日志最后 20 行:")
        print('\n'.join(lines[-20:]))

ssh.close()
