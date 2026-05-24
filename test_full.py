"""完整测试 - 登录 + 测试监控指标"""
import paramiko
import json

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)

    # 写一个测试脚本到服务器
    test_script = r'''
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

# 1. 登录
login_data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(
    f"{BASE}/api/v1/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    token = result.get("data", {}).get("access_token", "")
    print(f"LOGIN: {result.get('code')} token={token[:20]}...")
except Exception as e:
    print(f"LOGIN FAILED: {e}")
    import traceback; traceback.print_exc()
    exit(1)

# 2. 测试监控指标
req2 = urllib.request.Request(
    f"{BASE}/api/v1/ops/monitoring/metrics",
    headers={"Authorization": f"Bearer {token}"}
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=15)
    data = json.loads(resp2.read())
    print(f"METRICS STATUS: {data.get('code')}")
    if data.get('data'):
        d = data['data']
        print(f"  CPU: {d.get('cpu_percent')}%")
        print(f"  Memory: {d.get('memory_percent')}%")
        print(f"  Disk: {d.get('disk_percent')}%")
        print(f"  Uptime: {d.get('uptime_seconds')}s")
    else:
        print(f"  Response: {json.dumps(data, ensure_ascii=False)[:500]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"METRICS HTTP ERROR: {e.code}")
    print(f"  Body: {body[:500]}")
except Exception as e:
    print(f"METRICS ERROR: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()
'''

    # 写到服务器临时文件
    sftp = client.open_sftp()
    with sftp.open(r"D:\Andre\project\energy-trusted-data-space\test_api.py", "w") as f:
        f.write(test_script)
    sftp.close()

    # 执行
    print("=== 执行测试 ===")
    stdin, stdout, stderr = client.exec_command(
        r'D:\xujingyi\anaconda3\python.exe D:\Andre\project\energy-trusted-data-space\test_api.py',
        timeout=30
    )
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    print(out)
    if err:
        print(f"STDERR: {err[:500]}")

    # 检查 uvicorn 日志的最新错误
    print("\n=== uvicorn.log 最新错误 ===")
    stdin, stdout, stderr = client.exec_command(
        r'powershell -Command "Get-Content D:\Andre\project\energy-trusted-data-space\uvicorn.log -Tail 5"',
        timeout=10
    )
    print(stdout.read().decode("gbk", errors="replace"))

    client.close()

if __name__ == "__main__":
    main()
