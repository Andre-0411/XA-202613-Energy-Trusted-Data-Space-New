"""诊断服务器服务状态"""
import paramiko

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

def run(client, cmd, timeout=10):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("gbk", errors="replace")
    err = stderr.read().decode("gbk", errors="replace")
    return out.strip(), err.strip()

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)
    print("✅ SSH 连接成功\n")

    # 1. 检查端口监听
    print("=== 端口监听状态 ===")
    out, _ = run(client, 'netstat -an | findstr "LISTENING"')
    for line in out.split('\n'):
        if '8000' in line or '8080' in line:
            print(f"  {line.strip()}")

    # 2. 检查 Python 进程
    print("\n=== Python 进程 ===")
    out, _ = run(client, 'tasklist /FI "IMAGENAME eq python.exe"')
    print(out)

    # 3. 检查 uvicorn 日志最后几行
    print("\n=== uvicorn.log (最后10行) ===")
    out, _ = run(client, r'powershell -Command "Get-Content D:\Andre\project\energy-trusted-data-space\uvicorn.log -Tail 10 2>$null"')
    print(out if out else "(文件不存在或为空)")

    # 4. 检查 serve_frontend.py 日志
    print("\n=== frontend.log (最后10行) ===")
    out, _ = run(client, r'powershell -Command "Get-Content D:\Andre\project\energy-trusted-data-space\frontend.log -Tail 10 2>$null"')
    print(out if out else "(文件不存在或为空)")

    # 5. 检查 schtasks
    print("\n=== 计划任务 ===")
    out, _ = run(client, 'schtasks /Query /FO LIST | findstr /I "uvicorn\|frontend\|energy"')
    print(out if out else "(无相关计划任务)")

    # 6. 检查防火墙
    print("\n=== 防火墙规则 (8000/8080) ===")
    out, _ = run(client, 'netsh advfirewall firewall show rule name=all | findstr /I "8000 8080"')
    print(out if out else "(无相关防火墙规则)")

    client.close()

if __name__ == "__main__":
    main()
