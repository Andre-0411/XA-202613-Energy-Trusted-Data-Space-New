"""Run full test on server via paramiko"""
import paramiko
import time

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASS)

cmd = r'cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -u full_test.py'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)

# Read output
output = stdout.read().decode("gbk", errors="replace")
errors = stderr.read().decode("gbk", errors="replace")

print(output)
if errors.strip():
    print("STDERR:", errors[:500])

ssh.close()
