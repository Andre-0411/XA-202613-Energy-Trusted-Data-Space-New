"""Force start uvicorn"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Check if port 8000 is in use
stdin, stdout, stderr = ssh.exec_command('netstat -ano | findstr ":8000.*LISTEN"', timeout=10)
out = stdout.read().decode("utf-8", errors="replace")
print(f"Port 8000 status: {out.strip()[:200]}")

# Kill any existing python on port 8000
if "LISTENING" in out:
    # Extract PID
    for line in out.strip().split("\n"):
        if "LISTENING" in line:
            parts = line.strip().split()
            pid = parts[-1]
            print(f"Killing PID {pid}...")
            ssh.exec_command(f'taskkill /F /PID {pid}')
            time.sleep(2)
            break

# Start uvicorn using pythonw (background, no window)
cmd = r'start /min cmd /c "cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(f"Start command output: {out.strip()[:200]}")
print(f"Start command err: {err.strip()[:200]}")

print("Waiting 25s for server...")
time.sleep(25)

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
