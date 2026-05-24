"""部署 monitor_service.py 修复并重启服务"""
import paramiko
import time

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
REMOTE_BACKEND = r"D:\Andre\project\energy-trusted-data-space\backend"

def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)
    return client

def run_cmd(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    return out, err

def main():
    client = ssh_connect()
    sftp = client.open_sftp()

    # 上传修复后的 monitor_service.py
    local = r"D:\Projects\energy-trusted-data-space\backend\app\services\monitor_service.py"
    remote = f"{REMOTE_BACKEND}\\app\\services\\monitor_service.py"
    print(f"上传 monitor_service.py ...")
    sftp.put(local, remote)
    print("上传完成")

    sftp.close()

    # 重启 uvicorn: 先杀掉旧进程，再用 schtasks 启动
    print("重启 uvicorn ...")

    # 创建启动 bat
    bat_content = (
        f'cd /d {REMOTE_BACKEND} && '
        f'D:\\xujingyi\\anaconda3\\python.exe -m uvicorn app.main:app '
        f'--host 0.0.0.0 --port 8000 > {REMOTE_BACKEND}\\..\\uvicorn.log 2>&1'
    )

    # 写 bat 文件
    bat_path = r"D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat"
    run_cmd(client, f'echo @echo off > "{bat_path}"')
    run_cmd(client, f'echo cd /d {REMOTE_BACKEND} >> "{bat_path}"')
    run_cmd(client, f'echo D:\\xujingyi\\anaconda3\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 ^> {REMOTE_BACKEND}\\..\\uvicorn.log 2^>^&1 >> "{bat_path}"')

    # 杀掉旧进程
    run_cmd(client, "taskkill /F /IM python.exe 2>nul", timeout=10)
    time.sleep(2)

    # 通过 schtasks 启动
    run_cmd(client, f'schtasks /Create /TN "UvicornRestart" /TR "{bat_path}" /SC ONCE /ST 00:00 /F', timeout=10)
    run_cmd(client, 'schtasks /Run /TN "UvicornRestart"', timeout=10)
    time.sleep(1)
    run_cmd(client, 'schtasks /Delete /TN "UvicornRestart" /F', timeout=10)

    print("等待 uvicorn 启动 ...")
    time.sleep(8)

    # 验证
    out, err = run_cmd(client, f'D:\\xujingyi\\anaconda3\\python.exe -c "import urllib.request; r=urllib.request.urlopen(\'http://127.0.0.1:8000/docs\'); print(r.status)"', timeout=15)
    print(f"健康检查: {out.strip()}")
    if "200" in out:
        print("✅ 服务启动成功!")
    else:
        print(f"⚠️ 响应: {out}")
        print(f"错误: {err}")

    # 测试监控指标端点
    print("\n测试监控指标端点 ...")
    test_cmd = (
        'D:\\xujingyi\\anaconda3\\python.exe -c "'
        "import urllib.request, json; "
        "req = urllib.request.Request('http://127.0.0.1:8000/api/v1/ops/monitoring/metrics'); "
        "r = urllib.request.urlopen(req); "
        "data = json.loads(r.read()); "
        "print(json.dumps(data, indent=2, ensure_ascii=False))"
        '"'
    )
    out, err = run_cmd(client, test_cmd, timeout=20)
    print(f"监控指标响应: {out[:500]}")
    if err:
        print(f"错误: {err[:300]}")

    client.close()

if __name__ == "__main__":
    main()
