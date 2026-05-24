#!/usr/bin/env python3
"""检查并启动HTTP服务"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USERNAME, PASSWORD, timeout=30)

def run_cmd(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    return out, err

# 1. 检查dist目录
print("1. 检查构建产物目录:")
out, _ = run_cmd('dir "C:\\Users\\zhouxuying\\energy-trusted-data-space\\frontend\\dist"')
print(out[:500] if out else "目录不存在")

# 2. 检查Python
print("\n2. 检查Python:")
out, _ = run_cmd('python --version')
print(out)

# 3. 检查端口8080
print("\n3. 检查端口8080:")
out, _ = run_cmd('netstat -ano | findstr ":8080"')
print(out if out else "端口8080未被占用")

# 4. 创建并运行HTTP服务器
print("\n4. 启动HTTP服务器...")
# 使用PowerShell启动后台进程
cmd = '''
powershell -Command "
Set-Location 'C:\\Users\\zhouxuying\\energy-trusted-data-space\\frontend\\dist';
Start-Process python -ArgumentList '-m', 'http.server', '8080' -WindowStyle Hidden;
Start-Sleep -Seconds 3;
netstat -ano | Select-String ':8080'
"
'''
out, err = run_cmd(cmd)
print(out)
if err:
    print(f"错误: {err}")

# 5. 再次检查端口
print("\n5. 验证服务状态:")
out, _ = run_cmd('netstat -ano | findstr ":8080"')
if '8080' in out:
    print("✅ HTTP服务器已成功启动！")
    print(f"\n访问地址: http://{HOST}:8080")
    print("\n登录页面: http://10.241.2.64:8080")
else:
    print("⚠️ 服务未启动，尝试直接运行...")
    # 直接运行
    cmd2 = 'cd /d "C:\\Users\\zhouxuying\\energy-trusted-data-space\\frontend\\dist" && python -m http.server 8080 &'
    out, err = run_cmd(cmd2)
    print(out)
    time.sleep(3)
    out, _ = run_cmd('netstat -ano | findstr ":8080"')
    print(out)

client.close()
