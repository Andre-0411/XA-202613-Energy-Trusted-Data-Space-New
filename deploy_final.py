"""部署修复并测试监控指标"""
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

    # 上传修复后的文件
    local = r"D:\Projects\energy-trusted-data-space\backend\app\services\monitor_service.py"
    remote = f"{REMOTE_BACKEND}\\app\\services\\monitor_service.py"
    print("上传 monitor_service.py ...")
    sftp.put(local, remote)
    sftp.close()

    # 重启
    print("重启 uvicorn ...")
    client.exec_command("taskkill /F /IM python.exe 2>nul", timeout=10)
    time.sleep(2)
    bat_path = r"D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat"
    client.exec_command(f'schtasks /Create /TN "UR" /TR "{bat_path}" /SC ONCE /ST 00:00 /F', timeout=10)
    client.exec_command('schtasks /Run /TN "UR"', timeout=10)
    time.sleep(1)
    client.exec_command('schtasks /Delete /TN "UR" /F', timeout=10)

    # 等待启动完成（MongoDB 超时 30s + 余量）
    print("等待服务启动 ...")
    time.sleep(45)

    # 检查端口
    stdin, stdout, stderr = client.exec_command('netstat -an | findstr ":8000.*LISTEN"', timeout=10)
    if "LISTENING" not in stdout.read().decode("gbk", errors="replace"):
        print("⚠️ 端口 8000 未就绪")
        client.close()
        return

    print("✅ 端口 8000 就绪")

    # 测试脚本
    test_script = r'''
import urllib.request, json

BASE = "http://127.0.0.1:8000"
login_data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(f"{BASE}/api/v1/auth/login", data=login_data,
                             headers={"Content-Type": "application/json"}, method="POST")
resp = urllib.request.urlopen(req, timeout=15)
token = json.loads(resp.read())["data"]["access_token"]
print("LOGIN: OK")

req2 = urllib.request.Request(f"{BASE}/api/v1/ops/monitoring/metrics",
                              headers={"Authorization": f"Bearer {token}"})
try:
    resp2 = urllib.request.urlopen(req2, timeout=15)
    data = json.loads(resp2.read())
    print(f"METRICS: code={data.get('code')}")
    d = data.get("data", {})
    if d:
        sys_m = d.get("system_metrics", d)
        biz_m = d.get("business_metrics", d)
        print(f"  CPU: {sys_m.get('cpu_usage_percent', 'N/A')}%")
        print(f"  Memory: {sys_m.get('memory_usage_percent', 'N/A')}%")
        print(f"  Disk: {sys_m.get('disk_usage_percent', 'N/A')}%")
        print(f"  Uptime: {sys_m.get('uptime_seconds', 'N/A')}s")
        print(f"  Tasks: {biz_m.get('compute_task_total', 'N/A')}")
        print(f"  Assets: {biz_m.get('data_asset_count', 'N/A')}")
    else:
        print(f"  Full: {json.dumps(data, ensure_ascii=False)[:500]}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"METRICS ERROR: {e.code} - {body[:500]}")
except Exception as e:
    print(f"METRICS EXCEPTION: {type(e).__name__}: {e}")
'''

    sftp = client.open_sftp()
    with sftp.open(r"D:\Andre\project\energy-trusted-data-space\test_m.py", "w") as f:
        f.write(test_script)
    sftp.close()

    print("\n=== 测试监控指标 ===")
    stdin, stdout, stderr = client.exec_command(
        r'D:\xujingyi\anaconda3\python.exe D:\Andre\project\energy-trusted-data-space\test_m.py',
        timeout=30
    )
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    print(out)
    if err:
        print(f"STDERR: {err[:300]}")

    # 最新日志
    stdin, stdout, stderr = client.exec_command(
        r'powershell -Command "Get-Content D:\Andre\project\energy-trusted-data-space\uvicorn.log -Tail 5"',
        timeout=10
    )
    print("\n=== 最新日志 ===")
    print(stdout.read().decode("gbk", errors="replace"))

    client.close()

if __name__ == "__main__":
    main()
