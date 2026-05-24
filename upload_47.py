#!/usr/bin/env python3
"""上传前端到47.84.80.39"""
import paramiko
import os
import time

HOST = "47.84.80.39"
USERNAME = "root"
PASSWORD = "Andre0411"
LOCAL_DIST = r"D:\Projects\energy-trusted-data-space\frontend\dist"
REMOTE_DIR = "/opt/energy-trusted-data-space/frontend/dist"

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(3):
        try:
            client.connect(HOST, 22, USERNAME, PASSWORD, timeout=60, banner_timeout=60)
            return client
        except Exception as e:
            print(f"重试 {i+1}/3: {e}")
            time.sleep(5)
    raise Exception("无法连接到服务器")

def upload_dir(sftp, local_dir, remote_dir):
    try:
        sftp.mkdir(remote_dir)
    except:
        pass
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        if os.path.isfile(local_path):
            print(f"  {item}")
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            upload_dir(sftp, local_path, remote_path)

print(f"连接到 {HOST}...")
client = connect()
print("连接成功！")

# 清空旧dist
print("清空旧文件...")
stdin, stdout, stderr = client.exec_command(f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR}")
stdout.read()

# SFTP上传
print(f"上传 {LOCAL_DIST} -> {REMOTE_DIR}")
sftp = client.open_sftp()
upload_dir(sftp, LOCAL_DIST, REMOTE_DIR)
sftp.close()
print("上传完成！")

# 停止旧服务
print("停止旧服务...")
stdin, stdout, stderr = client.exec_command("pkill -f 'http.server' 2>/dev/null; sleep 1")
stdout.read()

# 启动服务
print("启动HTTP服务...")
stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_DIR} && nohup python3 -m http.server 8080 > /tmp/http.log 2>&1 &")
stdout.read()

time.sleep(2)

# 验证
stdin, stdout, stderr = client.exec_command("ss -tlnp | grep 8080")
out = stdout.read().decode('utf-8', errors='ignore')
if '8080' in out:
    print(f"\n✅ 部署完成！")
    print(f"🔗 http://{HOST}:8080")
else:
    print("服务未启动，尝试其他方式...")
    stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_DIR} && python3 -m http.server 8080 &")
    time.sleep(2)
    stdin, stdout, stderr = client.exec_command("ss -tlnp | grep 8080")
    out = stdout.read().decode('utf-8', errors='ignore')
    print(out)
    print(f"\n🔗 http://{HOST}:8080")

# 防火墙
stdin, stdout, stderr = client.exec_command("iptables -I INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null")
stdout.read()
print("已开放8080端口")

client.close()
