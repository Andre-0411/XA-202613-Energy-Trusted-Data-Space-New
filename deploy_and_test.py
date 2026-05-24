"""部署 monitor_service.py 修复并测试"""
import paramiko
import time

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
REMOTE_BACKEND = r"D:\Andre\project\energy-trusted-data-space\backend"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)
    sftp = client.open_sftp()

    # 上传修复后的 monitor_service.py
    local = r"D:\Projects\energy-trusted-data-space\backend\app\services\monitor_service.py"
    remote = f"{REMOTE_BACKEND}\\app\\services\\monitor_service.py"
    print("上传 monitor_service.py ...")
    sftp.put(local, remote)
    print("上传完成")
    sftp.close()

    # 重启 uvicorn
    print("重启 uvicorn ...")
    client.exec_command("taskkill /F /IM python.exe 2>nul", timeout=10)
    time.sleep(2)

    bat_path = r"D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat"
    client.exec_command(f'schtasks /Create /TN "UvicornRestart" /TR "{bat_path}" /SC ONCE /ST 00:00 /F', timeout=10)
    client.exec_command('schtasks /Run /TN "UvicornRestart"', timeout=10)
    time.sleep(1)
    client.exec_command('schtasks /Delete /TN "UvicornRestart" /F', timeout=10)

    print("等待启动 ...")
    time.sleep(12)

    # 验证端口
    stdin, stdout, stderr = client.exec_command('netstat -an | findstr ":8000.*LISTEN"', timeout=10)
    port_out = stdout.read().decode("gbk", errors="replace")
    if "LISTENING" in port_out:
        print("✅ 端口 8000 正在监听")
    else:
        print(f"⚠️ 端口状态: {port_out}")
        client.close()
        return

    # 执行测试
    test_script = r'''
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

# 登录
login_data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(
    f"{BASE}/api/v1/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req, timeout=15)
result = json.loads(resp.read())
token = result["data"]["access_token"]
print(f"LOGIN: OK")

# 测试监控指标
req2 = urllib.request.Request(
    f"{BASE}/api/v1/ops/monitoring/metrics",
    headers={"Authorization": f"Bearer {token}"}
)
try:
    resp2 = urllib.request.urlopen(req2, timeout=15)
    data = json.loads(resp2.read())
    print(f"METRICS: code={data.get('code')}")
    if data.get('data'):
        d = data['data']
        print(f"  CPU: {d.get('cpu_percent')}%")
        print(f"  Memory: {d.get('memory_percent')}%")
        print(f"  Disk: {d.get('disk_percent')}%")
        print(f"  Uptime: {d.get('uptime_seconds')}s")
        print(f"  Avg Response: {d.get('avg_response_time_ms')}ms")
        print(f"  Error Rate: {d.get('error_rate')}%")
        print(f"  Total Assets: {d.get('total_assets')}")
        print(f"  Total Tasks: {d.get('total_tasks')}")
    else:
        print(f"  Full: {json.dumps(data, ensure_ascii=False)[:500]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"METRICS ERROR: {e.code} - {body[:500]}")
'''

    sftp = client.open_sftp()
    with sftp.open(r"D:\Andre\project\energy-trusted-data-space\test_api2.py", "w") as f:
        f.write(test_script)
    sftp.close()

    print("\n=== 测试监控指标 ===")
    stdin, stdout, stderr = client.exec_command(
        r'D:\xujingyi\anaconda3\python.exe D:\Andre\project\energy-trusted-data-space\test_api2.py',
        timeout=30
    )
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    print(out)
    if err:
        print(f"STDERR: {err[:300]}")

    # 检查 uvicorn 日志
    print("\n=== uvicorn 日志最新 ===")
    stdin, stdout, stderr = client.exec_command(
        r'powershell -Command "Get-Content D:\Andre\project\energy-trusted-data-space\uvicorn.log -Tail 5"',
        timeout=10
    )
    print(stdout.read().decode("gbk", errors="replace"))

    client.close()

if __name__ == "__main__":
    main()
