"""Get latest server error log."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=10)

# Clear log and make a fresh request
stdin, stdout, stderr = ssh.exec_command(f'echo. > {PROJECT_DIR}\\uvicorn.log', timeout=10)
stdout.read()
time.sleep(1)

# Make a request from the server itself to trigger the error
PYTHON = r"D:\xujingyi\anaconda3\python.exe"
test_script = '''
import requests
BASE = "http://127.0.0.1:8000"
try:
    login = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "admin123"}, timeout=10)
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE}/api/v1/ops/monitoring/metrics", headers=headers, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:300]}")
except Exception as e:
    print(f"Error: {e}")
'''
stdin, stdout, stderr = ssh.exec_command(f'{PYTHON} -c "{test_script}"', timeout=30)
# Wait for it
time.sleep(5)

# Now check the log
stdin, stdout, stderr = ssh.exec_command(f'type {PROJECT_DIR}\\uvicorn.log 2>nul', timeout=15)
out = stdout.read().decode('gbk', errors='replace').strip()
print("=== Uvicorn error log ===")
print(out[:3000])

ssh.close()
