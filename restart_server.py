"""Restart uvicorn on server"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Kill existing uvicorn
cmds = [
    'taskkill /F /IM python.exe 2>nul',
    'timeout /t 3 /nobreak >nul',
]
for cmd in cmds:
    ssh.exec_command(cmd)
    time.sleep(1)

# Create startup batch
startup = r'''@echo off
cd /d D:\Andre\project\energy-trusted-data-space
D:\xujingyi\anaconda3\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
'''
sftp = ssh.open_sftp()
with sftp.open(r"D:\Andre\project\energy-trusted-data-space\start_backend.bat", "w") as f:
    f.write(startup)
sftp.close()

# Start via schtasks
cmds2 = [
    r'schtasks /Create /TN "UvicornStart" /TR "cmd /c D:\Andre\project\energy-trusted-data-space\start_backend.bat" /SC ONCE /ST 00:00 /F',
    'schtasks /Run /TN "UvicornStart"',
]
for cmd in cmds2:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    stdout.read()
    time.sleep(1)

print("Waiting for server to start...")
time.sleep(15)

# Verify
import urllib.request, json
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
    print(f"Server not ready: {e}")

ssh.close()
