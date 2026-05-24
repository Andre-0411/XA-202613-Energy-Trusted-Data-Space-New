"""获取监控指标的详细错误"""
import paramiko

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)

    # 查看 uvicorn.log 最新错误
    stdin, stdout, stderr = client.exec_command(
        r'powershell -Command "Get-Content D:\Andre\project\energy-trusted-data-space\uvicorn.log -Tail 30"',
        timeout=10
    )
    print("=== uvicorn.log (最新30行) ===")
    print(stdout.read().decode("gbk", errors="replace"))

    client.close()

if __name__ == "__main__":
    main()
