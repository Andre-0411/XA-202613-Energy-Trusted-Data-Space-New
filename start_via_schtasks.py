"""Start uvicorn via schtasks"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Write batch file
bat = '''@echo off
cd /d D:\\Andre\\project\\energy-trusted-data-space
D:\\xujingyi\\anaconda3\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
'''
sftp = ssh.open_sftp()
with sftp.open(r"D:\Andre\project\energy-trusted-data-space\run_uvicorn.bat", "w") as f:
    f.write(bat)
sftp.close()
print("Batch file written")

# Create task with current time + 1 min
from datetime import datetime, timedelta
future = datetime.now() + timedelta(minutes=1)
time_str = future.strftime("%H:%M")
date_str = future.strftime("%Y/%m/%d")

# Delete existing task if any
ssh.exec_command('schtasks /Delete /TN "RunUvicorn" /F')
time.sleep(1)

# Create scheduled task
cmd = f'schtasks /Create /TN "RunUvicorn" /TR "cmd /c D:\\Andre\\project\\energy-trusted-data-space\\run_uvicorn.bat" /SC ONCE /ST {time_str} /SD {date_str} /F'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(f"Create task: {out.strip()[:200]} | {err.strip()[:200]}")

# Run it immediately
stdin, stdout, stderr = ssh.exec_command('schtasks /Run /TN "RunUvicorn"', timeout=15)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(f"Run task: {out.strip()[:200]} | {err.strip()[:200]}")

print("Waiting 30s...")
time.sleep(30)

# Check
import urllib.request
try:
    req = urllib.request.Request(
        "http://10.241.2.64:8000/api/v1/auth/login",
        data=b'{"username":"admin","password":"admin123"}',
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"Server UP! Status: {resp.status}")
except Exception as e:
    print(f"Not ready: {e}")

ssh.close()
