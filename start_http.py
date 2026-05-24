#!/usr/bin/env python3
"""通过WMI创建后台进程"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USERNAME, PASSWORD, timeout=30)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    return out, err

# 用 schtasks 创建一个立即执行的计划任务
print("1. 创建计划任务启动HTTP服务...")
out, err = run(
    'schtasks /Create /TN "FrontendHTTP" /TR "cmd /c cd /d C:\\Users\\zhouxuying\\energy-trusted-data-space\\frontend\\dist && python -m http.server 8080" /SC ONCE /ST 00:00 /F'
)
print(f"   {out.strip()}")

# 立即运行
out, err = run('schtasks /Run /TN "FrontendHTTP"')
print(f"   {out.strip()}")

time.sleep(3)

# 检查
print("\n2. 检查端口8080:")
out, _ = run('netstat -ano | findstr ":8080"')
print(out if out else "   未检测到")

# 检查任务状态
print("3. 任务状态:")
out, _ = run('schtasks /Query /TN "FrontendHTTP"')
print(out)

if '8080' in out or '8080' in (out := run('netstat -ano | findstr ":8080"')[0]):
    print(f"\n✅ 前端服务已启动！")
    print(f"🔗 http://{HOST}:8080")
else:
    print(f"\n⚠️ 请手动登录服务器运行 C:\\Users\\zhouxuying\\start_http.bat")

client.close()
