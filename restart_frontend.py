"""重启前端代理 + 恢复计划任务持久化"""
import paramiko
import time

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
REMOTE_BASE = r"D:\Andre\project\energy-trusted-data-space"
PYTHON = r"D:\xujingyi\anaconda3\python.exe"

def run(client, cmd, timeout=15):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    return out.strip(), err.strip()

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)
    print("✅ SSH 连接成功")

    # 1. 找到 dist 目录
    print("\n=== 定位 dist 目录 ===")
    dist_path = None
    for candidate in [
        f"{REMOTE_BASE}\\energy-trusted-data-space\\dist",
        f"{REMOTE_BASE}\\dist",
    ]:
        out, _ = run(client, f'dir "{candidate}\\index.html" 2>nul')
        if "index.html" in out:
            dist_path = candidate
            print(f"  ✅ dist: {dist_path}")
            break

    if not dist_path:
        print("  ⚠️ 找不到 dist/index.html，搜索中...")
        out, _ = run(client, f'dir /s /b "{REMOTE_BASE}\\index.html" 2>nul')
        print(f"  搜索结果: {out[:500]}")

    # 2. 检查 serve_frontend.py 内容
    print("\n=== 检查 serve_frontend.py ===")
    out, _ = run(client, f'type "{REMOTE_BASE}\\serve_frontend.py"')
    if dist_path and dist_path not in out:
        print("  ⚠️ serve_frontend.py 中的 dist 路径可能不正确")
        print(f"  文件内容前3行: {chr(10).join(out.split(chr(10))[:5])}")
    else:
        print("  serve_frontend.py 内容正常")

    # 3. 用 schtasks 启动前端代理
    print("\n=== 启动前端代理 ===")
    fe_bat = f"{REMOTE_BASE}\\start_frontend.bat"

    # 用 schtasks 启动
    run(client, f'schtasks /Create /TN "FEProxy" /TR "{fe_bat}" /SC ONCE /ST 00:00 /F')
    run(client, 'schtasks /Run /TN "FEProxy"')
    time.sleep(1)
    run(client, 'schtasks /Delete /TN "FEProxy" /F')

    time.sleep(3)

    # 4. 验证端口
    out, _ = run(client, 'netstat -an | findstr ":8080"')
    print(f"  端口 8080: {out}")
    if "LISTENING" in out:
        print("  ✅ 前端代理已启动")
    else:
        print("  ⚠️ 前端代理可能未启动，检查日志...")
        # 检查 python 进程
        out, _ = run(client, 'tasklist /FI "IMAGENAME eq python.exe"')
        print(f"  Python 进程: {out}")

    # 5. 恢复持久化计划任务
    print("\n=== 恢复持久化计划任务 ===")
    run(client, f'schtasks /Create /TN "UvicornAuto" /TR "{REMOTE_BASE}\\start_uvicorn.bat" /SC ONLOGON /F')
    run(client, f'schtasks /Create /TN "FrontendAuto" /TR "{fe_bat}" /SC ONLOGON /F')
    out, _ = run(client, 'schtasks /Query /FO LIST | findstr /I "Auto"')
    print(f"  {out if out else '无'}")

    # 6. 本机测试
    print("\n=== 本机测试 ===")
    out, _ = run(client, f'{PYTHON} -c "import urllib.request; r=urllib.request.urlopen(chr(104)+chr(116)+chr(116)+chr(112)+chr(58)+chr(47)+chr(47)+chr(49)+chr(50)+chr(55)+chr(46)+chr(48)+chr(46)+chr(48)+chr(46)+chr(49)+chr(58)+chr(56)+chr(48)+chr(48)+chr(48), timeout=10); print(chr(66)+chr(97)+chr(99)+chr(107)+chr(101)+chr(110)+chr(100)+chr(58), r.status)"', timeout=15)
    print(f"  {out}")
    out, _ = run(client, f'{PYTHON} -c "import urllib.request; r=urllib.request.urlopen(chr(104)+chr(116)+chr(116)+chr(112)+chr(58)+chr(47)+chr(47)+chr(49)+chr(50)+chr(55)+chr(46)+chr(48)+chr(46)+chr(48)+chr(46)+chr(49)+chr(58)+chr(56)+chr(48)+chr(56)+chr(48), timeout=10); print(chr(70)+chr(114)+chr(111)+chr(110)+chr(116)+chr(101)+chr(110)+chr(100)+chr(58), r.status)"', timeout=15)
    print(f"  {out}")

    client.close()

if __name__ == "__main__":
    main()
