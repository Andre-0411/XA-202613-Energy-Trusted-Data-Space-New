"""Check startup error"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Run uvicorn and capture output
cmd = r'cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=20)
time.sleep(15)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print("--- STDOUT ---")
print(out[:3000])
print("--- STDERR ---")
print(err[:3000])
ssh.close()
