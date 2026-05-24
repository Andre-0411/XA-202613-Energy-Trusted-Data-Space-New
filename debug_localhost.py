"""Debug: test with localhost"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

test_script = '''
import urllib.request
import json
print("Starting test...", flush=True)

# Try localhost first
for host in ["127.0.0.1", "localhost", "10.241.2.64"]:
    try:
        req = urllib.request.Request(
            f"http://{host}:8000/api/v1/auth/login",
            data=b'{"username":"admin","password":"admin123"}',
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[OK] {host}:8000 -> {resp.status}", flush=True)
            break
    except Exception as e:
        print(f"[FAIL] {host}:8000 -> {e}", flush=True)
'''
sftp = ssh.open_sftp()
with sftp.open(r"D:\Andre\project\energy-trusted-data-space\debug_host.py", "w") as f:
    f.write(test_script)
sftp.close()

cmd = r'cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -u debug_host.py'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
output = stdout.read().decode("utf-8", errors="replace")
errs = stderr.read().decode("utf-8", errors="replace")
print(output)
if errs.strip():
    print("STDERR:", errs[:300])
ssh.close()
