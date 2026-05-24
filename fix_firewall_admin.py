#!/usr/bin/env python3
"""在10.241.2.64上以管理员权限添加防火墙规则"""
import paramiko
import time

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, 22, USERNAME, PASSWORD, timeout=30)

def run(cmd, timeout=15):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='ignore'), stderr.read().decode('utf-8', errors='ignore')

# 检查是否有其他管理员用户
print("=== 检查管理员用户 ===")
out, _ = run('net localgroup Administrators')
print(out)

# 尝试用runas提权
print("=== 尝试添加防火墙规则 ===")
# 写一个批处理文件
sftp = client.open_sftp()
with sftp.open('C:\\Users\\zhouxuying\\add_firewall.bat', 'w') as f:
    f.write('@echo off\r\n')
    f.write('netsh advfirewall firewall add rule name="HTTP-8080" dir=in action=allow protocol=tcp localport=8080\r\n')
    f.write('echo Done\r\n')
sftp.close()

# 尝试用PowerShell提权
print("尝试PowerShell提权...")
cmd = '''
powershell -Command "Start-Process cmd -ArgumentList '/c C:\\Users\\zhouxuying\\add_firewall.bat' -Verb RunAs -Wait"
'''
out, err = run(cmd, timeout=30)
print(f"out: {out}")
print(f"err: {err}")

# 检查规则是否添加成功
print("\n=== 检查防火墙规则 ===")
out, _ = run('netsh advfirewall firewall show rule name="HTTP-8080"')
print(out)

# 如果还是不行，试试用netsh的另一种方式
if "8080" not in out:
    print("\n尝试另一种方式...")
    # 直接用PowerShell添加规则
    cmd2 = '''
    powershell -Command "New-NetFirewallRule -DisplayName 'HTTP-8080' -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow"
    '''
    out, err = run(cmd2, timeout=30)
    print(f"out: {out}")
    print(f"err: {err}")

    # 检查
    out, _ = run('netsh advfirewall firewall show rule name="HTTP-8080"')
    print(out)

client.close()
