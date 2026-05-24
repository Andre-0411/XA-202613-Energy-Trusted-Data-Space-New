"""重启前端并验证 CSRF 修复"""
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.241.2.64', username='zhouxuying', password='zhouxuying51')

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err

# 1. 停止前端
print("Stopping frontend...")
run(r'schtasks /end /tn ETDS-Frontend')
time.sleep(2)

# 2. 杀掉残留 python 进程 (serve_frontend.py)
print("Killing old processes...")
run(r'taskkill /f /im python.exe /fi "WINDOWTITLE eq *serve_frontend*" 2>nul')
time.sleep(1)

# 3. 启动前端
print("Starting frontend...")
run(r'schtasks /run /tn ETDS-Frontend')

# 4. 等待 8080 端口就绪
print("Waiting for port 8080...")
for i in range(15):
    time.sleep(2)
    out, _ = run(r'netstat -an | findstr ":8080.*LISTEN"')
    if 'LISTEN' in out:
        print(f"Port 8080 ready after {(i+1)*2}s")
        break
else:
    print("Port 8080 not ready!")

# 5. 测试直接 curl 登录（不带 Origin）
print("\nTest 1: POST login without Origin (curl)...")
stdin, stdout, stderr = ssh.exec_command(
    r'curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8080/api/v1/auth/login '
    r'-H "Content-Type: application/json" '
    r'-d "{\"username\":\"admin\",\"password\":\"admin123\"}"',
    timeout=15
)
out = stdout.read().decode('gbk', errors='replace').strip()
print(f"  Result: HTTP {out}")

# 6. 测试带 Origin（模拟浏览器）
print("\nTest 2: POST login WITH Origin header (browser simulation)...")
stdin, stdout, stderr = ssh.exec_command(
    r'curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8080/api/v1/auth/login '
    r'-H "Content-Type: application/json" '
    r'-H "Origin: http://10.241.2.64:8080" '
    r'-d "{\"username\":\"admin\",\"password\":\"admin123\"}"',
    timeout=15
)
out = stdout.read().decode('gbk', errors='replace').strip()
print(f"  Result: HTTP {out}")

# 7. 确认 middleware_old 存在，middleware/ 不存在
print("\nVerification:")
out, _ = run(r'dir "D:\Andre\project\energy-trusted-data-space\backend\app\middleware_old" 2>nul')
print(f"  middleware_old exists: {'middleware_old' in out}")
out, _ = run(r'dir "D:\Andre\project\energy-trusted-data-space\backend\app\middleware" 2>nul')
has_dir = '<DIR>' in out and 'middleware.py' not in out
print(f"  middleware/ dir exists: {has_dir}")

ssh.close()
print("\nDone!")
