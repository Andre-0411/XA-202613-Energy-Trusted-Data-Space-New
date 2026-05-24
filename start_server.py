#!/usr/bin/env python3
"""在服务器上启动HTTP服务"""
import paramiko

HOST = "10.241.2.64"
PORT = 22
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, PORT, USERNAME, PASSWORD, timeout=30)

# 创建启动脚本
startup_script = '''
@echo off
cd /d C:\\Users\\zhouxuying\\energy-trusted-data-space\\frontend\\dist
echo 启动HTTP服务器在端口8080...
python -m http.server 8080
'''

# 上传启动脚本
sftp = client.open_sftp()
with sftp.open('C:\\Users\\zhouxuying\\start_frontend.bat', 'w') as f:
    f.write(startup_script)
sftp.close()

# 检查端口是否被占用
stdin, stdout, stderr = client.exec_command('netstat -ano | findstr :8080')
print("检查端口8080:")
print(stdout.read().decode('utf-8', errors='ignore'))

# 启动服务（后台运行）
print("\n启动HTTP服务器...")
command = 'cd /d C:\\Users\\zhouxuying\\energy-trusted-data-space\\frontend\\dist && start /B python -m http.server 8080'
stdin, stdout, stderr = client.exec_command(command)
print(stdout.read().decode('utf-8', errors='ignore'))
err = stderr.read().decode('utf-8', errors='ignore')
if err:
    print(f"错误: {err}")

# 等待一下然后检查服务是否启动
import time
time.sleep(2)

stdin, stdout, stderr = client.exec_command('netstat -ano | findstr :8080')
output = stdout.read().decode('utf-8', errors='ignore')
if '8080' in output:
    print("\n✅ HTTP服务器已启动！")
    print(f"访问地址: http://{HOST}:8080")
else:
    print("\n⚠️ 服务可能未成功启动，请手动检查")

client.close()
