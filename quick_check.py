"""Quick check if uvicorn is up."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"
PYTHON = r"D:\xujingyi\anaconda3\python.exe"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

time.sleep(10)

# Full log
stdin, stdout, stderr = ssh.exec_command(f'type {PROJECT_DIR}\\uvicorn.log 2>nul', timeout=15)
out = stdout.read().decode('gbk', errors='replace').strip()
lines = out.split('\n')
print("=== Last 15 lines ===")
for line in lines[-15:]:
    if line.strip():
        print(f"  {line}")

# Port
stdin, stdout, stderr = ssh.exec_command('netstat -ano | findstr ":8000.*LISTEN"', timeout=10)
port_out = stdout.read().decode('gbk', errors='replace').strip()
print(f"\nPort 8000: {port_out[:200] if port_out else 'NOT FOUND'}")

# HTTP test
stdin, stdout, stderr = ssh.exec_command(
    f'{PYTHON} -c "import urllib.request; r = urllib.request.urlopen(\'http://127.0.0.1:8000/docs\', timeout=5); print(\'STATUS:\', r.status)"',
    timeout=15
)
result = stdout.read().decode('gbk', errors='replace').strip()
print(f"HTTP: {result}")

ssh.close()
