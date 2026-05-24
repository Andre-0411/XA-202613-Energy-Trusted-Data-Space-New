#!/usr/bin/env python3
"""部署到47.84.80.39服务器"""
import paramiko
import time

HOST = "47.84.80.39"
USERNAME = "root"
PASSWORD = "Andre0411"
PROJECT_DIR = "/opt/energy-trusted-data-space"

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USERNAME, PASSWORD, timeout=30)
    return client

def run(client, cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    return out, err

print(f"连接到 {HOST}...")
client = connect()
print("连接成功！")

# 1. 检查项目目录
print("\n=== 1. 检查项目 ===")
out, _ = run(client, f"ls -la {PROJECT_DIR}/ 2>/dev/null || echo 'NOT_FOUND'")
if "NOT_FOUND" in out:
    print("目录不存在，克隆仓库...")
    out, err = run(client, "cd /opt && git clone https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New.git energy-trusted-data-space", timeout=120)
    print(out)
else:
    print("项目目录已存在")

# 2. 拉取最新代码
print("\n=== 2. 拉取最新代码 ===")
out, err = run(client, f"cd {PROJECT_DIR} && git pull origin main")
print(out)

# 3. 检查node环境
print("\n=== 3. 检查Node环境 ===")
out, _ = run(client, "node -v && npm -v")
print(out)

# 4. 构建前端
print("\n=== 4. 构建前端 ===")
out, _ = run(client, "cd {PROJECT_DIR}/frontend && npm install", timeout=120)
out, err = run(client, f"cd {PROJECT_DIR}/frontend && NODE_OPTIONS='--max-old-space-size=2048' npm run build", timeout=300)
print(out[-500:] if len(out) > 500 else out)
if err:
    print(f"[err] {err[-300:]}")

# 5. 检查构建结果
print("\n=== 5. 构建结果 ===")
out, _ = run(client, f"ls -la {PROJECT_DIR}/frontend/dist/ | head -10")
print(out)

# 6. 停止旧HTTP服务（如果有）
print("\n=== 6. 停止旧服务 ===")
out, _ = run(client, "pkill -f 'http.server 8080' 2>/dev/null; echo 'done'")
print("旧服务已停止")

# 7. 启动HTTP服务
print("\n=== 7. 启动HTTP服务 ===")
out, err = run(client, f"cd {PROJECT_DIR}/frontend/dist && nohup python3 -m http.server 8080 > /tmp/http_server.log 2>&1 &")
print(out)

time.sleep(2)

# 8. 验证
print("\n=== 8. 验证服务 ===")
out, _ = run(client, "netstat -tlnp 2>/dev/null | grep 8080 || ss -tlnp | grep 8080")
print(out)

# 9. 检查防火墙
print("\n=== 9. 检查防火墙 ===")
out, _ = run(client, "iptables -L -n 2>/dev/null | head -20")
print(out)

# 10. 开放8080端口（如果有iptables）
print("\n=== 10. 开放8080端口 ===")
out, err = run(client, "iptables -I INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null && echo 'Rule added' || echo 'iptables not available'")
print(out)

client.close()
print(f"\n✅ 部署完成！访问地址: http://{HOST}:8080")
