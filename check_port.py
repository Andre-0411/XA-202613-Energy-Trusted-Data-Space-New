"""等待并检查服务是否就绪"""
import paramiko
import time
import urllib.request

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASS)

    # 检查端口是否在监听
    print("=== 检查端口 8000 ===")
    stdin, stdout, stderr = client.exec_command('netstat -an | findstr :8000', timeout=10)
    print(stdout.read().decode("gbk", errors="replace"))

    # 再看完整 uvicorn.log
    print("=== uvicorn.log (最后 50 行) ===")
    stdin, stdout, stderr = client.exec_command(
        'type D:\\Andre\\project\\energy-trusted-data-space\\uvicorn.log 2>nul',
        timeout=10
    )
    log = stdout.read().decode("gbk", errors="replace")
    lines = log.strip().split('\n')
    for line in lines[-50:]:
        print(line)

    client.close()

if __name__ == "__main__":
    main()
