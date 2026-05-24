"""Test curl from server"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Use curl from server
cmd = 'curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/api/v1/auth/login" -X POST -H "Content-Type: application/json" -d "{\\"username\\":\\"admin\\",\\"password\\":\\"admin123\\"}" --connect-timeout 5'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
output = stdout.read().decode("utf-8", errors="replace")
errs = stderr.read().decode("utf-8", errors="replace")
print(f"curl result: {output.strip()}")
if errs.strip():
    print(f"curl stderr: {errs[:300]}")

ssh.close()
