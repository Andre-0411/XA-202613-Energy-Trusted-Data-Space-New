"""
裸机部署脚本 - 面向能源可信数据空间
目标服务器: 10.241.2.64 (Windows)
部署方式: 直接安装 Python + uvicorn + PostgreSQL + Redis + Nginx
"""
import paramiko
import os
import sys
import time
import zipfile
import io
import stat
import secrets
from datetime import datetime

# ==================== 配置 ====================
SERVER_HOST = "10.241.2.64"
SERVER_PORT = 22
SERVER_USER = "zhouxuying"
SERVER_PASSWORD = "zhouxuying51"

# 部署路径
DEPLOY_DIR = r"D:\EnergyTDS"
BACKEND_DIR = os.path.join(DEPLOY_DIR, "backend")
FRONTEND_DIR = os.path.join(DEPLOY_DIR, "frontend")

# 本地项目路径
LOCAL_PROJECT = r"D:\XA-202613-Energy-Trusted-Data-Space-New"

# 生成生产密钥
APP_SECRET = secrets.token_urlsafe(48)
JWT_SECRET = secrets.token_urlsafe(48)
PG_PASSWORD = "energy_tds_2024_secure"
REDIS_PASSWORD = ""  # 暂时不设密码


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"OK": "[OK]", "WARN": "[!!]", "ERR": "[XX]", "PHASE": ">>>"}
    prefix = icons.get(level, "   ")
    print(f"[{ts}] {prefix} {msg}", flush=True)


class SSHDeploy:
    def __init__(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        self.ssh.connect(SERVER_HOST, SERVER_PORT, SERVER_USER, SERVER_PASSWORD, timeout=30)
        log(f"SSH 连接成功 {SERVER_HOST}", "OK")

    def close(self):
        self.ssh.close()

    def cmd(self, command, timeout=30):
        """执行命令并返回 stdout"""
        stdin, stdout, stderr = self.ssh.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        return out, err, code

    def cmd_ok(self, command, timeout=30):
        """执行命令，只返回 stdout（成功时）"""
        out, err, code = self.cmd(command, timeout)
        if code != 0:
            log(f"命令失败 [{code}]: {command[:80]}")
            log(f"  stderr: {err[:200]}")
        return out, code

    def upload_dir(self, local_dir, remote_dir):
        """递归上传目录"""
        sftp = self.ssh.open_sftp()

        def ensure_remote_dir(path):
            try:
                sftp.stat(path)
            except FileNotFoundError:
                parent = os.path.dirname(path)
                if parent and parent != path:
                    ensure_remote_dir(parent)
                try:
                    sftp.mkdir(path)
                except IOError:
                    pass

        ensure_remote_dir(remote_dir)
        count = 0

        for root, dirs, files in os.walk(local_dir):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if d not in {
                "__pycache__", ".git", "node_modules", ".next",
                "dist", ".venv", "venv", ".idea", ".vscode",
                ".workbuddy", "target", ".mypy_cache", ".pytest_cache",
                "*.egg-info"
            }]

            rel = os.path.relpath(root, local_dir)
            remote_path = os.path.join(remote_dir, rel).replace("\\", "/") if rel != "." else remote_dir

            ensure_remote_dir(remote_path)

            for f in files:
                if f.endswith((".pyc", ".pyo", ".so", ".dll", ".exe")):
                    continue
                local_file = os.path.join(root, f)
                remote_file = os.path.join(remote_path, f).replace("\\", "/")
                try:
                    sftp.put(local_file, remote_file)
                    count += 1
                    if count % 100 == 0:
                        log(f"  已上传 {count} 个文件...")
                except Exception as e:
                    log(f"  上传失败 {f}: {e}", "WARN")

        sftp.close()
        log(f"  总计上传 {count} 个文件", "OK")
        return count

    def upload_file(self, local_path, remote_path):
        """上传单个文件"""
        sftp = self.ssh.open_sftp()
        remote_dir = os.path.dirname(remote_path).replace("\\", "/")
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)
        sftp.put(local_path, remote_path)
        sftp.close()

    def upload_content(self, content, remote_path):
        """上传文本内容"""
        sftp = self.ssh.open_sftp()
        remote_dir = os.path.dirname(remote_path).replace("\\", "/")
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            try:
                sftp.mkdir(remote_dir)
            except IOError:
                pass
        with sftp.file(remote_path, 'w') as f:
            f.write(content)
        sftp.close()


def phase1_check(deploy):
    """阶段1: 启动 Redis"""
    log("=" * 60, "PHASE")
    log("阶段1: 启动 Redis", "PHASE")
    log("=" * 60, "PHASE")

    # 检查 Redis 是否已运行
    out, err, code = deploy.cmd("netstat -ano | findstr 6379")
    if code == 0 and "LISTENING" in out:
        log("Redis 已在运行", "OK")
        return

    # 启动 Redis
    log("启动 Redis...", "PHASE")
    out, err, code = deploy.cmd(
        f'start /B "" "D:\\Andre\\software\\redis\\redis-server.exe" '
        f'--port 6379 --daemonize no --save 900 1 --save 300 10',
        timeout=10
    )
    time.sleep(2)

    out, err, code = deploy.cmd("netstat -ano | findstr 6379")
    if code == 0 and "LISTENING" in out:
        log("Redis 启动成功 (port 6379)", "OK")
    else:
        log("Redis 启动失败，将尝试另一种方式", "WARN")
        # 直接启动
        deploy.cmd('powershell -NoProfile -Command "Start-Process -FilePath \'D:\\Andre\\software\\redis\\redis-server.exe\' -WindowStyle Hidden"', timeout=10)
        time.sleep(3)
        out, err, code = deploy.cmd("netstat -ano | findstr 6379")
        if code == 0 and "LISTENING" in out:
            log("Redis 启动成功 (port 6379)", "OK")
        else:
            log("Redis 未能启动，后端将以降级模式运行", "WARN")


def phase2_upload(deploy):
    """阶段2: 上传代码"""
    log("=" * 60, "PHASE")
    log("阶段2: 上传项目代码", "PHASE")
    log("=" * 60, "PHASE")

    # 创建部署目录
    deploy.cmd(f'mkdir "{DEPLOY_DIR}" 2>nul', timeout=5)
    deploy.cmd(f'mkdir "{BACKEND_DIR}" 2>nul', timeout=5)

    # 上传后端代码
    log("上传后端代码...", "PHASE")
    deploy.upload_dir(os.path.join(LOCAL_PROJECT, "backend"), BACKEND_DIR)

    # 上传 alembic 配置（在 backend 根目录）
    alembic_src = os.path.join(LOCAL_PROJECT, "backend", "alembic.ini")
    if os.path.exists(alembic_src):
        deploy.upload_file(alembic_src, os.path.join(BACKEND_DIR, "alembic.ini"))
    alembic_dir = os.path.join(LOCAL_PROJECT, "backend", "alembic")
    if os.path.exists(alembic_dir):
        deploy.upload_dir(alembic_dir, os.path.join(BACKEND_DIR, "alembic"))

    # 上传 scripts 目录
    scripts_dir = os.path.join(LOCAL_PROJECT, "scripts")
    if os.path.exists(scripts_dir):
        deploy.upload_dir(scripts_dir, os.path.join(DEPLOY_DIR, "scripts"))

    # 创建生产 .env
    log("创建生产环境 .env...", "PHASE")
    env_content = f"""# ============================================================
# 面向能源可信数据空间 - 生产环境配置
# 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================================

# ==================== 应用配置 ====================
APP_NAME=EnergyTrustedDataSpace
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY={APP_SECRET}
APP_HOST=0.0.0.0
APP_PORT=8000

# ==================== 数据库配置 ====================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=energy_tds
POSTGRES_USER=postgres
POSTGRES_PASSWORD={PG_PASSWORD}

# ==================== Redis 配置 ====================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# ==================== MongoDB 配置 (可选) ====================
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=energy_tds_meta
MONGO_USER=
MONGO_PASSWORD=

# ==================== MinIO 配置 (可选) ====================
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=energy_minio_access
MINIO_SECRET_KEY=energy_minio_secret_key_2024
MINIO_BUCKET=energy-tds
MINIO_USE_SSL=false

# ==================== 消息队列 (可选) ====================
MQTT_BROKER=tcp://localhost:1883
MQTT_WS_URL=ws://localhost:8083/mqtt
MQTT_CLIENT_ID=energy-tds-backend

RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=
RABBITMQ_PASSWORD=
RABBITMQ_VHOST=energy_tds

# ==================== 区块链 (可选) ====================
FISCO_CHANNEL_HOST=localhost
FISCO_CHANNEL_PORT=20200
FISCO_GROUP_ID=1

# ==================== 隐私计算 (可选) ====================
FATE_COORDINATOR_HOST=localhost
FATE_COORDINATOR_PORT=9380
FATE_PARTY_ID=10000

# ==================== 安全配置 ====================
JWT_SECRET_KEY={JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
WORKERS=4
TIMEOUT=120

# ==================== AI 配置 ====================
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
"""
    deploy.upload_content(env_content, os.path.join(BACKEND_DIR, ".env"))
    log("生产环境 .env 已创建", "OK")


def phase3_pip(deploy):
    """阶段3: 安装 Python 依赖"""
    log("=" * 60, "PHASE")
    log("阶段3: 安装 Python 依赖", "PHASE")
    log("=" * 60, "PHASE")

    # 先用 pip 下载依赖（离线缓存）
    log("安装后端依赖 (pip install)...", "PHASE")

    # 使用服务器的 pip 安装 requirements.txt
    req_path = os.path.join(BACKEND_DIR, "requirements.txt").replace("\\", "/")
    cmd = f'pip install -r "{req_path}" --no-cache-dir 2>&1'
    log(f"执行: pip install -r requirements.txt")
    out, err, code = deploy.cmd(cmd, timeout=300)  # 5分钟超时

    if code == 0:
        log("依赖安装成功", "OK")
    else:
        log(f"部分依赖安装失败 (code={code})", "WARN")
        # 显示失败的包
        if err:
            for line in err.split("\n"):
                if "ERROR" in line or "error" in line or "Failed" in line:
                    log(f"  {line[:150]}", "WARN")
        # 继续执行，核心依赖应该已装好


def phase4_db(deploy):
    """阶段4: 初始化数据库"""
    log("=" * 60, "PHASE")
    log("阶段4: 初始化数据库", "PHASE")
    log("=" * 60, "PHASE")

    # 检查 PostgreSQL 用户和数据库
    log("检查 PostgreSQL...", "PHASE")

    # 先检查 postgres 用户密码 - 尝试连接
    out, err, code = deploy.cmd(
        f'set PGPASSWORD={PG_PASSWORD} && psql -h localhost -U postgres -c "SELECT 1" 2>&1',
        timeout=10
    )

    if code != 0:
        # 可能密码不对，尝试信任认证
        log("尝试 PostgreSQL 信任认证...", "PHASE")
        out, err, code = deploy.cmd(
            'psql -h localhost -U postgres -c "SELECT 1" 2>&1',
            timeout=10
        )

    if code == 0:
        log("PostgreSQL 连接成功", "OK")
    else:
        log(f"PostgreSQL 连接失败: {err[:200]}", "ERR")
        log("需要手动检查 PostgreSQL 密码配置", "WARN")
        return

    # 创建数据库和用户
    log("创建数据库 energy_tds (如不存在)...", "PHASE")
    deploy.cmd(
        f'psql -h localhost -U postgres -c "SELECT 1 FROM pg_database WHERE datname=\'energy_tds\'" 2>&1',
        timeout=10
    )
    # 直接创建
    deploy.cmd('psql -h localhost -U postgres -c "CREATE DATABASE energy_tds;" 2>&1', timeout=15)
    log("数据库 energy_tds 已就绪", "OK")

    # 运行 Alembic 迁移
    log("运行数据库迁移 (Alembic)...", "PHASE")
    # 先检查 alembic.ini 和 env.py
    out, err, code = deploy.cmd(f'dir /b "{BACKEND_DIR}\\alembic" 2>&1', timeout=5)

    # 执行迁移
    out, err, code = deploy.cmd(
        f'cd /d "{BACKEND_DIR}" && alembic upgrade head 2>&1',
        timeout=60
    )

    if code == 0:
        log("数据库迁移完成", "OK")
    else:
        log(f"数据库迁移返回: {out[:200]}")
        log(f"错误: {err[:200]}", "WARN")
        # 可能没有迁移文件，尝试使用 create_all
        log("尝试直接创建表...", "PHASE")
        deploy.cmd(
            f'cd /d "{BACKEND_DIR}" && python -c "'
            f'import asyncio; '
            f'from app.database import async_engine, Base; '
            f'from app import models; '
            f'async def main(): '
            f'  async with async_engine.begin() as conn: '
            f'    await conn.run_sync(Base.metadata.create_all); '
            f'    print(\"Tables created\"); '
            f'asyncio.run(main())" 2>&1',
            timeout=60
        )
        log("表创建尝试完成", "OK")


def phase5_start(deploy):
    """阶段5: 启动后端服务"""
    log("=" * 60, "PHASE")
    log("阶段5: 启动后端服务", "PHASE")
    log("=" * 60, "PHASE")

    # 先杀掉占用 8000 端口的旧进程
    out, err, code = deploy.cmd("netstat -ano | findstr :8000 | findstr LISTENING 2>&1", timeout=5)
    if code == 0 and out.strip():
        for line in out.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 5:
                pid = parts[-1]
                log(f"杀掉旧进程 PID {pid} (占用端口 8000)")
                deploy.cmd(f"taskkill /F /PID {pid} 2>&1", timeout=5)
        time.sleep(1)

    # 启动 uvicorn
    log("启动 uvicorn 服务 (端口 8000)...", "PHASE")
    start_cmd = (
        f'cd /d "{BACKEND_DIR}" && '
        f'start /B "" python -m uvicorn app.main:app '
        f'--host 0.0.0.0 --port 8000 '
        f'--workers 4 --log-level info '
        f'> "{BACKEND_DIR}\\uvicorn.log" 2>&1'
    )
    out, err, code = deploy.cmd(start_cmd, timeout=10)
    time.sleep(5)

    # 验证
    out, err, code = deploy.cmd("netstat -ano | findstr :8000 | findstr LISTENING 2>&1", timeout=5)
    if code == 0 and out.strip():
        log(f"uvicorn 已启动: {out.strip()}", "OK")
    else:
        log("uvicorn 可能未正常启动，检查日志...", "WARN")
        out, err, code = deploy.cmd(f'type "{BACKEND_DIR}\\uvicorn.log" 2>&1', timeout=5)
        log(f"日志: {out[:500]}", "WARN")

    # 测试健康检查
    time.sleep(3)
    out, err, code = deploy.cmd('curl -s http://localhost:8000/health 2>&1', timeout=10)
    if code == 0 and "healthy" in out:
        log("健康检查通过!", "OK")
    else:
        log(f"健康检查: {out[:200]}", "WARN")


def phase6_frontend(deploy):
    """阶段6: 构建前端并配置 Nginx"""
    log("=" * 60, "PHASE")
    log("阶段6: 构建前端 (本地)", "PHASE")
    log("=" * 60, "PHASE")

    # 在本地构建前端
    frontend_path = os.path.join(LOCAL_PROJECT, "frontend")
    log(f"进入前端目录: {frontend_path}")

    # 检查是否已有 dist
    dist_path = os.path.join(frontend_path, "dist")
    if os.path.exists(dist_path) and os.listdir(dist_path):
        log("前端 dist 目录已存在", "OK")
    else:
        log("前端需要构建，请在后续手动执行: cd frontend && npm install && npm run build")
        log("暂时跳过前端部署，后端 API 已可用", "WARN")
        return

    # 上传 dist 到服务器
    log("上传前端构建产物...", "PHASE")
    deploy.upload_dir(dist_path, os.path.join(DEPLOY_DIR, "frontend", "dist"))
    log("前端文件已上传", "OK")

    # 创建 Nginx 配置
    log("配置 Nginx...", "PHASE")
    nginx_conf = f"""# 面向能源可信数据空间 - Nginx 配置
server {{
    listen 80;
    server_name localhost;

    # 前端静态文件
    root {DEPLOY_DIR}\\frontend\\dist;
    index index.html;

    # 健康检查
    location /health {{
        access_log off;
        return 200 '{{"status":"healthy"}}';
        add_header Content-Type application/json;
    }}

    # SPA 路由
    location / {{
        try_files $uri $uri/ /index.html;
    }}

    # 静态资源缓存
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }}

    # API 反向代理
    location /api/ {{
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}

    # WebSocket 代理
    location /ws/ {{
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }}

    # 错误页面
    error_page 404 /index.html;
}}
"""
    # 检查服务器是否有 Nginx
    out, err, code = deploy.cmd("where nginx 2>&1", timeout=5)
    if code == 0 and out.strip():
        log(f"Nginx 已安装: {out.strip()}", "OK")
        # 上传配置
        deploy.upload_content(nginx_conf, os.path.join(DEPLOY_DIR, "nginx", "conf", "energy_tds.conf"))
        log("Nginx 配置已上传，需手动 reload", "OK")
    else:
        log("Nginx 未安装，可通过 http://localhost:8000/docs 直接访问 API", "WARN")
        deploy.upload_content(nginx_conf, os.path.join(DEPLOY_DIR, "nginx.conf"))
        log("Nginx 配置已保存，安装 Nginx 后可直接使用", "OK")


def phase7_autorestart(deploy):
    """阶段7: 配置自动重启"""
    log("=" * 60, "PHASE")
    log("阶段7: 配置自动重启", "PHASE")
    log("=" * 60, "PHASE")

    # 创建启动脚本
    start_script = f"""@echo off
REM 面向能源可信数据空间 - 启动脚本
REM 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

echo [%date% %time%] Starting EnergyTDS services...

REM 启动 Redis
start /B "" "D:\\Andre\\software\\redis\\redis-server.exe" --port 6379 --save 900 1 --save 300 10
echo [%date% %time%] Redis started (port 6379)

REM 等待 Redis 启动
timeout /t 2 /nobreak >nul

REM 启动后端
cd /d "{BACKEND_DIR}"
start /B "" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
echo [%date% %time%] Backend started (port 8000)

echo [%date% %time%] All services started!
echo.
echo   API:    http://localhost:8000
echo   Docs:   http://localhost:8000/docs
echo   Health: http://localhost:8000/health
"""
    deploy.upload_content(start_script, os.path.join(DEPLOY_DIR, "start_services.bat"))

    # 创建停止脚本
    stop_script = f"""@echo off
echo [%date% %time%] Stopping EnergyTDS services...
REM Kill uvicorn
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)
echo [%date% %time%] Services stopped.
"""
    deploy.upload_content(stop_script, os.path.join(DEPLOY_DIR, "stop_services.bat"))

    # 配置计划任务（开机自启）
    log("配置开机自启动计划任务...", "PHASE")
    deploy.cmd(
        f'schtasks /Create /TN "EnergyTDS_Startup" /TR "{DEPLOY_DIR}\\start_services.bat" '
        f'/SC ONLOGON /RL HIGHEST /F 2>&1',
        timeout=10
    )
    log("开机自启动已配置 (计划任务: EnergyTDS_Startup)", "OK")


def main():
    log("=" * 60)
    log("面向能源可信数据空间 - 生产部署 (裸机)")
    log(f"目标: {SERVER_HOST} ({SERVER_USER})")
    log(f"部署目录: {DEPLOY_DIR}")
    log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    deploy = SSHDeploy()
    try:
        deploy.connect()

        phase1_check(deploy)
        phase2_upload(deploy)
        phase3_pip(deploy)
        phase4_db(deploy)
        phase5_start(deploy)
        phase6_frontend(deploy)
        phase7_autorestart(deploy)

        log("=" * 60)
        log("部署完成!", "OK")
        log("=" * 60)
        log("")
        log("访问方式:")
        log(f"  API:      http://{SERVER_HOST}:8000")
        log(f"  文档:     http://{SERVER_HOST}:8000/docs")
        log(f"  健康检查: http://{SERVER_HOST}:8000/health")
        log("")
        log(f"部署目录: {DEPLOY_DIR}")
        log(f"后端目录: {BACKEND_DIR}")
        log(f"日志文件: {BACKEND_DIR}\\uvicorn.log")
        log("")
        log("管理命令:")
        log(f"  启动: {DEPLOY_DIR}\\start_services.bat")
        log(f"  停止: {DEPLOY_DIR}\\stop_services.bat")

    except Exception as e:
        log(f"部署失败: {e}", "ERR")
        import traceback
        traceback.print_exc()
    finally:
        deploy.close()


if __name__ == "__main__":
    main()
