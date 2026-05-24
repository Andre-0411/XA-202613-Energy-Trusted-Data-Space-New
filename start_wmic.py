"""Start uvicorn via wmic"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Use wmic to create process
cmd = r'wmic process call create "D:\xujingyi\anaconda3\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000", "D:\Andre\project\energy-trusted-data-space"'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(f"wmic output: {out.strip()[:300]}")
print(f"wmic err: {err.strip()[:300]}")

print("Waiting 20s...")
time.sleep(20)

# Check
cmds = [
    'tasklist /FI "IMAGENAME eq python.exe" /FO CSV',
    'netstat -ano | findstr ":8000"',
]
for c in cmds:
    stdin, stdout, stderr = ssh.exec_command(c, timeout=10)
    out = stdout.read().decode("utf-8", errors="replace")
    print(f">>> {c}")
    print(out[:300])
    print()

# Test login
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
