"""Upload fixed service files to server via SFTP"""
import paramiko
import os

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
REMOTE_BASE = r"D:\Andre\project\energy-trusted-data-space"
LOCAL_BASE = r"D:\Projects\energy-trusted-data-space"

files_to_upload = [
    "backend/app/services/workflow_service.py",
    "backend/app/services/product_market_service.py",
    "backend/app/services/quality_service.py",
    "full_test.py",
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASS)
sftp = ssh.open_sftp()

for f in files_to_upload:
    local_path = os.path.join(LOCAL_BASE, f).replace("/", os.sep)
    remote_path = f"{REMOTE_BASE}\\{f.replace('/', os.sep)}"
    print(f"Uploading {f}...")
    try:
        sftp.put(local_path, remote_path)
        print(f"  OK")
    except Exception as e:
        print(f"  FAILED: {e}")

sftp.close()

# Restart uvicorn
print("\nRestarting uvicorn...")
commands = [
    'taskkill /F /IM uvicorn.exe 2>nul',
    'timeout /t 2 /nobreak >nul',
    f'schtasks /Create /TN "UvicornRestart" /TR "cmd /c cd /d {REMOTE_BASE} && {r"D:\\xujingyi\\anaconda3\\python.exe"} -m uvicorn app.main:app --host 0.0.0.0 --port 8000" /SC ONCE /ST 00:00 /F',
    'schtasks /Run /TN "UvicornRestart"',
]
for cmd in commands:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.read()
    print(f"  {cmd[:60]}...")

import time
time.sleep(3)

# Verify
import urllib.request
import urllib.error
try:
    req = urllib.request.Request(
        "http://10.241.2.64:8000/api/v1/auth/login",
        data=b'{"username":"admin","password":"admin123"}',
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"\nServer status: {resp.status}")
except Exception as e:
    print(f"\nServer not ready: {e}")

ssh.close()
print("Done!")
