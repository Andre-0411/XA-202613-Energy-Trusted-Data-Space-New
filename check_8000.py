"""Quick check - just wait and see if server came up."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PYTHON = r"D:\xujingyi\anaconda3\python.exe"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

def run_cmd(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('gbk', errors='replace').strip(), stderr.read().decode('gbk', errors='replace').strip()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

# Wait more
print("Waiting 15s more...")
time.sleep(15)

# Full log
out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\uvicorn.log 2>nul')
print("=== Uvicorn log ===")
print(out[:3000])

# Port check
out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000 " 2>nul')
print(f"\n=== Port 8000 ===\n{out[:500] if out else 'NOT FOUND'}")

# Process check
out, _ = run_cmd(ssh, 'tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2>nul')
print(f"\n=== Python processes ===\n{out[:500]}")

# Test
out, err = run_cmd(ssh, f'{PYTHON} -c "import urllib.request; r = urllib.request.urlopen(\'http://127.0.0.1:8000/docs\', timeout=5); print(\'STATUS:\', r.status)"', timeout=15)
print(f"\n=== HTTP Test ===\n{out}")
if err:
    print(f"Error: {err[:300]}")

ssh.close()
