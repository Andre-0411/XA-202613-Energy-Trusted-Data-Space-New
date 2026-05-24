#!/usr/bin/env python3
"""检查服务器网络和防火墙"""
import paramiko

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USERNAME, PASSWORD, timeout=30)

def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

# 1. 检查HTTP服务是否还在运行
print("=== 1. 检查HTTP服务状态 ===")
out, _ = run('netstat -ano | findstr ":8080"')
print(out if out else "端口8080未在监听！\n")

# 2. 检查防火墙规则
print("=== 2. 检查防火墙 ===")
out, _ = run('netsh advfirewall firewall show rule name=all | findstr /i "8080"')
print(out if out else "未找到8080相关防火墙规则\n")

# 3. 检查Windows防火墙状态
print("=== 3. 防火墙状态 ===")
out, _ = run('netsh advfirewall show allprofiles state')
print(out)

# 4. 检查本机能否访问
print("=== 4. 本机访问测试 ===")
out, _ = run('curl -s -o NUL -w "%%{http_code}" http://localhost:8080/')
print(f"HTTP状态码: {out.strip()}\n")

# 5. 添加防火墙规则
print("=== 5. 添加防火墙入站规则 ===")
out, err = run('netsh advfirewall firewall add rule name="HTTP-8080" dir=in action=allow protocol=tcp localport=8080')
print(out)
if err:
    print(f"[err] {err}")

# 6. 确认规则已添加
print("\n=== 6. 确认防火墙规则 ===")
out, _ = run('netsh advfirewall firewall show rule name="HTTP-8080"')
print(out)

client.close()
print("\n完成！请重新尝试访问: http://10.241.2.64:8080")
