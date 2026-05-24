"""Check if uvicorn process is running"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.241.2.64", username="zhouxuying", password="zhouxuying51", timeout=30)

cmds = [
    'tasklist /FI "IMAGENAME eq python.exe" /FO CSV',
    'netstat -ano | findstr ":8000"',
]
for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    out = stdout.read().decode("utf-8", errors="replace")
    print(f">>> {cmd}")
    print(out[:500])
    print()

ssh.close()
