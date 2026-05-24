"""检查 uvicorn 启动日志"""
import paramiko

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)

    # 检查进程
    stdin, stdout, stderr = client.exec_command('tasklist /FI "IMAGENAME eq python.exe"', timeout=10)
    print("=== Python 进程 ===")
    print(stdout.read().decode("gbk", errors="replace"))

    # 检查日志
    stdin, stdout, stderr = client.exec_command(
        r'powershell -Command "Get-Content D:\Andre\project\energy-trusted-data-space\uvicorn.log -Tail 20"',
        timeout=10
    )
    print("=== uvicorn.log ===")
    print(stdout.read().decode("gbk", errors="replace"))

    # 检查 bat 文件
    stdin, stdout, stderr = client.exec_command(
        r'type D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat',
        timeout=10
    )
    print("=== start_uvicorn.bat ===")
    print(stdout.read().decode("gbk", errors="replace"))

    client.close()

if __name__ == "__main__":
    main()
