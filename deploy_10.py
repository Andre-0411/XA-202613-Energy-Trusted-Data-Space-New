#!/usr/bin/env python3
"""一键部署到 10.241.2.64 (前端构建 + 后端启动)"""
import paramiko
import time
import sys

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT_DIR = "/home/zhouxuying/energy-trusted-data-space"
GITHUB_REPO = "https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New.git"

def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, 22, USERNAME, PASSWORD, timeout=30)
    return client

def run(client, cmd, timeout=30, label=""):
    if label:
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
    print(f"  $ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    rc = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split("\n")[-25:]:
            print(f"  {line}")
    if err.strip():
        for line in err.strip().split("\n")[-10:]:
            print(f"  [warn] {line}")
    print(f"  [exit: {rc}]")
    return out, err, rc

print(f"Connecting to {HOST} as {USERNAME}...")
client = connect()
print("Connected!")

# 0. 检查环境
run(client, "uname -a && whoami", label="系统信息")
run(client, "python3 --version 2>&1; node -v 2>&1; npm -v 2>&1; git --version 2>&1", label="环境检查")

# 1. 克隆或拉取代码
out, _, rc = run(client, f"test -d {PROJECT_DIR}/.git && echo 'EXISTS' || echo 'NOT_FOUND'", label="检查项目目录")
if "NOT_FOUND" in out:
    print("  -> 克隆仓库...")
    run(client, f"git clone {GITHUB_REPO} {PROJECT_DIR}", timeout=120, label="Git Clone")
else:
    print("  -> 项目已存在，拉取最新...")
    run(client, f"cd {PROJECT_DIR} && git pull origin main", timeout=60, label="Git Pull")

# 2. 安装前端依赖
run(client, f"cd {PROJECT_DIR}/frontend && npm install --legacy-peer-deps 2>&1 | tail -20", timeout=300, label="npm install")

# 3. 构建前端
out, err, rc = run(client, f"cd {PROJECT_DIR}/frontend && NODE_OPTIONS='--max-old-space-size=2048' npm run build 2>&1 | tail -30", timeout=600, label="npm run build")

# 4. 检查构建产物
run(client, f"ls -lh {PROJECT_DIR}/frontend/dist/index.html 2>/dev/null && echo 'BUILD OK' || echo 'BUILD FAILED'", label="检查构建产物")

# 5. 安装后端依赖
run(client, f"cd {PROJECT_DIR}/backend && pip3 install -r requirements.txt 2>&1 | tail -10 || echo 'No requirements.txt or pip3 not found'", timeout=180, label="pip install 后端依赖")

# 6. 停止旧服务
run(client, "pkill -f 'http.server 8080' 2>/dev/null; pkill -f 'uvicorn' 2>/dev/null; sleep 1; echo 'Old services stopped'", label="停止旧服务")

# 7. 启动前端 HTTP 服务 (8080)
run(client, f"cd {PROJECT_DIR}/frontend/dist && nohup python3 -m http.server 8080 > /tmp/http_frontend.log 2>&1 & echo 'Frontend started on :8080'", label="启动前端服务 (8080)")

# 8. 启动后端 API 服务 (8000)
run(client, f"cd {PROJECT_DIR}/backend && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/http_backend.log 2>&1 & echo 'Backend started on :8000'", label="启动后端服务 (8000)")

time.sleep(3)

# 9. 验证服务
run(client, "ss -tlnp | grep -E '8080|8000' || netstat -tlnp 2>/dev/null | grep -E '8080|8000'", label="验证端口监听")

# 10. 开放防火墙
run(client, """
    # Try firewalld first
    if command -v firewall-cmd &>/dev/null; then
        sudo firewall-cmd --permanent --add-port=8080/tcp 2>/dev/null
        sudo firewall-cmd --permanent --add-port=8000/tcp 2>/dev/null
        sudo firewall-cmd --reload 2>/dev/null
        echo "firewalld: ports opened"
    # Try iptables
    elif command -v iptables &>/dev/null; then
        sudo iptables -I INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null
        sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT 2>/dev/null
        echo "iptables: rules added"
    else
        echo "No firewall tool found"
    fi
""", label="开放防火墙端口")

# 11. 测试访问
run(client, "curl -s -o /dev/null -w 'Frontend: %{http_code}' http://localhost:8080/ 2>/dev/null || echo 'Frontend: curl failed'", label="本地访问测试")
run(client, "curl -s -o /dev/null -w 'Backend:  %{http_code}' http://localhost:8000/ 2>/dev/null || echo 'Backend: curl failed'", label="后端访问测试")

client.close()
print(f"\n{'='*60}")
print(f"  Deploy complete!")
print(f"  Frontend: http://{HOST}:8080")
print(f"  Backend:  http://{HOST}:8000")
print(f"{'='*60}")
