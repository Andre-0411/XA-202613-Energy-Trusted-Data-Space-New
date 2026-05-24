"""写测试脚本到服务器并执行"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.241.2.64', username='zhouxuying', password='zhouxuying51')

# 写一个 bat 测试脚本到服务器
bat_script = r'''@echo off
echo === Test 1: POST login without Origin ===
curl -s -o NUL -w "HTTP_CODE:%%{http_code}\n" -X POST http://127.0.0.1:8080/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

echo === Test 2: POST login WITH Origin ===
curl -s -o NUL -w "HTTP_CODE:%%{http_code}\n" -X POST http://127.0.0.1:8080/api/v1/auth/login -H "Content-Type: application/json" -H "Origin: http://10.241.2.64:8080" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

echo === Test 3: POST login via direct backend ===
curl -s -o NUL -w "HTTP_CODE:%%{http_code}\n" -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -H "Origin: http://10.241.2.64:8080" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

echo === Done ===
'''

sftp = ssh.open_sftp()
with sftp.open('D:/Andre/project/energy-trusted-data-space/test_csrf.bat', 'w') as f:
    f.write(bat_script)

# 先确保前端已启动
stdin, stdout, stderr = ssh.exec_command(r'schtasks /query /tn ETDS-Frontend /fo list | findstr "模式"', timeout=10)
status = stdout.read().decode('gbk', errors='replace').strip()
print("Frontend status:", status)

if '正在运行' not in status:
    print("Starting frontend...")
    ssh.exec_command(r'schtasks /run /tn ETDS-Frontend', timeout=10)
    time.sleep(5)

# 执行测试脚本（在服务器上本地运行，不需要 SSH 超时）
print("\nRunning test on server...")
stdin, stdout, stderr = ssh.exec_command(
    r'cd /d D:\Andre\project\energy-trusted-data-space && test_csrf.bat',
    timeout=60
)
print(stdout.read().decode('gbk', errors='replace'))
err = stderr.read().decode('gbk', errors='replace')
if err: print("STDERR:", err[:300])

ssh.close()
