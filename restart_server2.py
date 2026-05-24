"""Restart uvicorn - force start"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Write a start script that runs in background
bat_content = '''@echo off
cd /d D:\\Andre\\project\\energy-trusted-data-space
D:\\xujingyi\\anaconda3\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > nul 2>&1
'''
sftp = ssh.open_sftp()
with sftp.open(r"D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat", "w") as f:
    f.write(bat_content)
sftp.close()

# Use schtasks to create and run
cmds = [
    r'schtasks /Create /TN "StartUvicorn" /TR "cmd /c start /min D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat" /SC ONCE /ST 00:00 /F',
    'schtasks /Run /TN "StartUvicorn"',
]
for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(f"CMD: {cmd[:60]}...")
    if out.strip():
        print(f"  OUT: {out.strip()[:200]}")
    if err.strip():
        print(f"  ERR: {err.strip()[:200]}")

# Wait longer
print("Waiting 20s for server start...")
time.sleep(20)

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
    print(f"Still not ready: {e}")

ssh.close()
