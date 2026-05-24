"""检查 uvicorn 错误日志"""
import paramiko

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err

# 查找 uvicorn 进程 PID
out, _ = run('netstat -ano | findstr ":8000" | findstr "LISTENING"')
print(f"8000 端口进程:\n{out}")

# 检查各种可能的日志文件
import os
log_files = [
    f"{PROJECT}\\backend_server.log",
    f"{PROJECT}\\uvicorn.log",
    f"{PROJECT}\\server.log",
    f"{PROJECT}\\backend\\server.log",
    f"{PROJECT}\\backend\\uvicorn.log",
]

for lf in log_files:
    out, _ = run(f'type "{lf}" 2>nul')
    if out:
        print(f"\n=== {lf} ===")
        print(out[-3000:])

# 尝试用 tasklist 找 uvicorn 的 PID，然后看它的输出
out, _ = run('tasklist | findstr python')
print(f"\nPython 进程:\n{out}")

# 尝试直接运行 uvicorn 看错误输出
print("\n=== 直接运行 uvicorn 测试 ===")
out, err = run(f'cd /d {PROJECT}\\backend && python -c "from app.main import app; print(\'App loaded OK\')"')
print(f"STDOUT: {out}")
print(f"STDERR: {err}")

# 检查数据库连接
print("\n=== 测试数据库连接 ===")
out, err = run(f'cd /d {PROJECT}\\backend && python -c "import asyncio; from app.database import get_db; print(\'DB module OK\')"')
print(f"STDOUT: {out}")
print(f"STDERR: {err}")

ssh.close()
