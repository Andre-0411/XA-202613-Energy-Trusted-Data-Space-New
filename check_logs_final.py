"""查看 uvicorn 最新日志"""
import paramiko

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err

# 读取完整的 uvicorn 日志
out, _ = run(f'type "{PROJECT}\\uvicorn.log" 2>nul')
if out:
    print("=== uvicorn.log (last 3000 chars) ===")
    print(out[-3000:])
else:
    print("No uvicorn.log found")

# 也看看有没有其他日志
out, _ = run(f'dir "{PROJECT}\\*.log" 2>nul')
print(f"\n日志文件: {out}")

ssh.close()
