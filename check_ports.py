#!/usr/bin/env python3
"""检查10.241.2.64开放的端口"""
import paramiko

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USERNAME, PASSWORD, timeout=30)

# 检查正在监听的端口
stdin, stdout, stderr = client.exec_command('netstat -an | findstr "LISTENING"', timeout=15)
out = stdout.read().decode('utf-8', errors='ignore')
print("=== 监听中的端口 ===")
print(out)

# 检查防火墙已开放的入站规则
stdin, stdout, stderr = client.exec_command('netsh advfirewall firewall show rule name=all dir=in | findstr /i "Rule Name Enabled LocalPort"', timeout=30)
out = stdout.read().decode('utf-8', errors='ignore')
print("\n=== 防火墙入站规则（摘要） ===")
# 过滤显示有端口的规则
for line in out.split('\n'):
    if 'LocalPort' in line and 'Any' not in line:
        print(line.strip())

client.close()
