"""Check server log for the 500 errors."""
import paramiko

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

stdin, stdout, stderr = ssh.exec_command(f'type {PROJECT_DIR}\\uvicorn.log 2>nul', timeout=15)
out = stdout.read().decode('gbk', errors='replace').strip()
print("=== Uvicorn log (last 60 lines) ===")
lines = out.split('\n')
for line in lines[-60:]:
    print(line)

ssh.close()
