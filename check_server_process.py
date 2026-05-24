"""Check if uvicorn is running on server"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

# Check uvicorn process
cmds = [
    'tasklist /FI "IMAGENAME eq python.exe" /FO CSV',
    'netstat -ano | findstr :8000',
]
for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    output = stdout.read().decode("gbk", errors="replace")
    print(f">>> {cmd}")
    print(output[:500])
    print()

ssh.close()
