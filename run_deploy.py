#!/usr/bin/env python3
"""
生产部署脚本 - 能源可信数据空间
目标: 10.241.2.64 (Windows Server)
"""
import paramiko, os, sys, time, secrets, string, base64, json
from datetime import datetime

SERVER_HOST = "10.241.2.64"
SERVER_PORT = 22
SERVER_USER = "zhouxuying"
SERVER_PASSWORD = "zhouxuying51"
PROJECT_DIR = "D:\\energy-tds"
REPO_URL = "https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New.git"

ssh = None
sftp = None

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"OK": "✓", "WARN": "⚠", "ERROR": "✗", "PHASE": "►", "INSTALL": "↓"}.get(level, "·")
    print(f"[{ts}] {prefix} {msg}", flush=True)

def connect():
    global ssh, sftp
    log(f"连接到 {SERVER_USER}@{SERVER_HOST}:{SERVER_PORT} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SERVER_HOST, SERVER_PORT, SERVER_USER, SERVER_PASSWORD, timeout=30)
        sftp = ssh.open_sftp()
        log("SSH 连接成功", "OK")
        return True
    except Exception as e:
        log(f"SSH 连接失败: {e}", "ERROR")
        return False

def runcmd(cmd, timeout=120, encoding="gbk"):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(encoding, errors="replace").strip()
    err = stderr.read().decode(encoding, errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

def runps(cmd, timeout=120):
    full = f'powershell -NoProfile -NonInteractive -Command "{cmd}"'
    stdin, stdout, stderr = ssh.exec_command(full, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    return out, err, code

def phase1_check():
    log("=" * 50)
    log("阶段 1: 环境检查", "PHASE")
    log("=" * 50)

    # OS
    out, _, _ = runps("(Get-WmiObject Win32_OperatingSystem).Caption")
    log(f"OS: {out}")

    # RAM
    out, _, _ = runps("[math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)")
    log(f"内存: {out} GB")

    # Disk
    out, _, _ = runps("(Get-PSDrive D -EA SilentlyContinue | ForEach-Object {[math]::Round($_.Free/1GB,1)})")
    log(f"D盘可用: {out} GB")

    # Docker
    out, _, code = runcmd("docker --version 2>&1")
    docker_ok = code == 0
    if docker_ok:
        log(f"Docker: {out}", "OK")
    else:
        log("Docker 未安装", "WARN")

    # Docker Compose
    out, _, code = runcmd("docker compose version 2>&1")
    if code != 0:
        out, _, code = runcmd("docker-compose --version 2>&1")
    compose_ok = code == 0
    if compose_ok:
        log(f"Compose: {out}", "OK")

    # Git
    out, _, code = runcmd("git --version 2>&1")
    git_ok = code == 0
    if git_ok:
        log(f"Git: {out}", "OK")
    else:
        log("Git 未安装", "WARN")

    # Python
    out, _, code = runcmd("python --version 2>&1")
    log(f"Python: {out}")

    return docker_ok, compose_ok, git_ok

def install_docker():
    log("安装 Docker Desktop...", "INSTALL")
    # Use winget first (faster)
    out, err, code = runcmd(
        "winget install Docker.DockerDesktop --accept-source-agreements --accept-package-agreements 2>&1",
        timeout=900
    )
    if code == 0:
        log("Docker 安装成功 (winget)", "OK")
    else:
        log(f"winget 失败: {err[:200]}", "WARN")
        # Manual download
        log("改用下载安装包...", "INSTALL")
        dl = 'powershell -Command "Invoke-WebRequest -Uri https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe -OutFile C:\\temp\\docker.exe"'
        runcmd("mkdir C:\\temp 2>nul")
        runcmd(dl, timeout=1200)
        out, err, code = runcmd('powershell -Command "Start-Process C:\\temp\\docker.exe -ArgumentList install,--quiet,--accept-license -Wait"', timeout=900)

    # Start Docker Desktop
    runps("Start-Process 'C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe' -ErrorAction SilentlyContinue")
    log("等待 Docker 守护进程就绪 (最多3分钟)...")
    for i in range(36):
        time.sleep(5)
        out, _, code = runcmd("docker version 2>&1")
        if code == 0:
            log(f"Docker 就绪 ({(i+1)*5}s)", "OK")
            return True
    log("Docker 未能在规定时间内就绪", "WARN")
    return False

def install_git():
    log("安装 Git...", "INSTALL")
    out, err, code = runcmd(
        "winget install Git.Git --accept-source-agreements --accept-package-agreements 2>&1",
        timeout=300
    )
    return code == 0

def phase2_code():
    log("=" * 50)
    log("阶段 2: 代码部署", "PHASE")
    log("=" * 50)

    # Check if exists
    out, _, _ = runps(f"Test-Path '{PROJECT_DIR}'")
    if out.strip().lower() == "true":
        log("项目已存在，执行 git pull...")
        out, err, code = runcmd(f'cd /d "{PROJECT_DIR}" && git pull origin main 2>&1', timeout=120)
        if code == 0:
            log("代码已更新", "OK")
        else:
            log(f"git pull 警告: {err[:200]}", "WARN")
    else:
        log(f"克隆 {REPO_URL} ...")
        out, err, code = runcmd(f'git clone "{REPO_URL}" "{PROJECT_DIR}" 2>&1', timeout=180)
        if code != 0:
            log(f"克隆失败: {err[:300]}", "ERROR")
            # Try create dir and init
            runps(f"New-Item -ItemType Directory -Force -Path '{PROJECT_DIR}'")
            return False
        log("克隆成功", "OK")

    # Copy Dockerfiles
    log("复制 Dockerfiles...")
    runcmd(f'copy /Y "{PROJECT_DIR}\\deploy\\docker\\backend.Dockerfile" "{PROJECT_DIR}\\backend\\Dockerfile"')
    runcmd(f'copy /Y "{PROJECT_DIR}\\deploy\\docker\\frontend.Dockerfile" "{PROJECT_DIR}\\frontend\\Dockerfile"')

    return True

def gen_pass(n=32):
    c = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(c) for _ in range(n))

def phase2_env():
    log("生成并上传 .env ...")
    pg_pw = gen_pass(24)
    redis_pw = gen_pass(24)
    mongo_pw = gen_pass(24)
    minio_pw = gen_pass(24)
    mqtt_pw = gen_pass(20)
    rabbit_pw = gen_pass(24)
    app_sec = gen_pass(64)
    jwt_sec = gen_pass(64)
    graf_pw = gen_pass(16)

    env_content = f"""APP_NAME=EnergyTrustedDataSpace
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY={app_sec}
APP_HOST=0.0.0.0
APP_PORT=8000
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=energy_tds
POSTGRES_USER=energy_admin
POSTGRES_PASSWORD={pg_pw}
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD={redis_pw}
REDIS_DB=0
MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_DB=energy_tds_meta
MONGO_USER=energy_mongo
MONGO_PASSWORD={mongo_pw}
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=energy_minio_access
MINIO_SECRET_KEY={minio_pw}
MINIO_BUCKET=energy-tds
MINIO_USE_SSL=false
MQTT_BROKER=tcp://emqx:1883
MQTT_USERNAME=energy_mqtt
MQTT_PASSWORD={mqtt_pw}
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=energy_rabbit
RABBITMQ_PASSWORD={rabbit_pw}
RABBITMQ_VHOST=energy_tds
FISCO_CHANNEL_HOST=fisco-node0
FISCO_CHANNEL_PORT=20200
FISCO_GROUP_ID=1
FISCO_SM_CRYPTO=true
FATE_PARTY_ID=10000
JWT_SECRET_KEY={jwt_sec}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
GRAFANA_ADMIN_PASSWORD={graf_pw}
DEEPSEEK_API_KEY=sk-placeholder
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
LOG_LEVEL=INFO
WORKERS=4
"""

    # Save credentials locally
    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production_credentials.txt")
    with open(cred_path, 'w', encoding='utf-8') as f:
        f.write(f"""# 能源可信数据空间 - 生产凭据
# 服务器: {SERVER_HOST}
# 生成时间: {datetime.now().isoformat()}
# !! 请妥善保管 !!

POSTGRES_PASSWORD={pg_pw}
REDIS_PASSWORD={redis_pw}
MONGO_PASSWORD={mongo_pw}
MINIO_SECRET_KEY={minio_pw}
MQTT_PASSWORD={mqtt_pw}
RABBITMQ_PASSWORD={rabbit_pw}
APP_SECRET_KEY={app_sec}
JWT_SECRET_KEY={jwt_sec}
GRAFANA_ADMIN_PASSWORD={graf_pw}
""")
    log(f"凭据已保存: {cred_path}", "OK")

    # Upload via base64
    b64 = base64.b64encode(env_content.encode('utf-8')).decode('ascii')
    ps_cmd = f"[IO.File]::WriteAllBytes('{PROJECT_DIR}\\.env', [Convert]::FromBase64String('{b64}'))"
    out, err, code = runps(ps_cmd, timeout=30)
    if code == 0:
        log(".env 上传成功", "OK")
    else:
        log(f".env 写入失败: {err[:300]}", "ERROR")
    return True

def phase3_build_start():
    log("=" * 50)
    log("阶段 3: 构建与启动", "PHASE")
    log("=" * 50)
    wd = f'cd /d "{PROJECT_DIR}" && '

    # Pull base images
    log("拉取基础镜像 (可能需要较长时间)...")
    base_imgs = [
        "postgres:16", "redis:7-alpine", "mongo:7",
        "minio/minio:latest", "emqx/emqx:5",
        "rabbitmq:3-management-alpine", "nginx:alpine",
        "prom/prometheus:latest", "grafana/grafana:latest",
        "python:3.12-slim", "node:22-alpine"
    ]
    for img in base_imgs:
        log(f"  pull {img}...")
        out, err, code = runcmd(wd + f"docker pull {img} 2>&1", timeout=600)
        if code == 0:
            log(f"  {img} OK", "OK")
        else:
            log(f"  {img} WARN: {err[:100]}", "WARN")

    # Build
    log("构建后端镜像 (约5-10分钟)...")
    out, err, code = runcmd(wd + "docker compose build --no-cache backend 2>&1", timeout=1800)
    if code == 0:
        log("后端镜像构建成功", "OK")
    else:
        log(f"后端构建警告: {err[:300]}", "WARN")

    log("构建前端镜像...")
    out, err, code = runcmd(wd + "docker compose build --no-cache frontend 2>&1", timeout=1800)
    if code == 0:
        log("前端镜像构建成功", "OK")
    else:
        log(f"前端构建警告: {err[:300]}", "WARN")

    # Wave 1: Infrastructure
    log("第1波: 启动基础设施...")
    out, err, code = runcmd(
        wd + "docker compose up -d postgres redis mongo minio emqx rabbitmq 2>&1", timeout=300
    )
    log(f"基础设施: {out[-200:] if out else ''}")
    log("等待60秒让基础设施稳定...")
    time.sleep(60)

    # Wave 2: Backend
    log("第2波: 启动后端...")
    out, err, code = runcmd(wd + "docker compose up -d backend 2>&1", timeout=300)
    log(f"后端: {out[-200:] if out else ''}")
    log("等待30秒...")
    time.sleep(30)

    # Wave 3: Frontend + Nginx
    log("第3波: 启动前端+Nginx...")
    out, err, code = runcmd(wd + "docker compose up -d frontend nginx 2>&1", timeout=300)
    log(f"前端/Nginx: {out[-200:] if out else ''}")

    # Wave 4: Blockchain + Privacy (optional, heavy)
    log("第4波: 启动区块链节点 (较重)...")
    out, err, code = runcmd(
        wd + "docker compose up -d fisco-node0 fisco-node1 fisco-node2 fisco-node3 2>&1", timeout=600
    )

    # Wave 5: Monitoring
    log("第5波: 启动监控...")
    out, err, code = runcmd(wd + "docker compose up -d prometheus grafana 2>&1", timeout=300)

    # Status
    log("等待60秒后检查状态...")
    time.sleep(60)
    out, _, _ = runcmd(wd + "docker compose ps 2>&1")
    log(f"容器状态:\n{out}")
    return True

def phase4_init_db():
    log("=" * 50)
    log("阶段 4: 初始化数据库", "PHASE")
    log("=" * 50)
    wd = f'cd /d "{PROJECT_DIR}" && '

    log("运行 Alembic 迁移...")
    out, err, code = runcmd(
        wd + "docker compose exec -T backend alembic upgrade head 2>&1", timeout=180
    )
    log(f"迁移: {out[:500] if out else err[:300]}")

    log("写入种子数据...")
    out, err, code = runcmd(
        wd + "docker compose exec -T backend python seed_data.py 2>&1", timeout=180
    )
    log(f"种子: {out[:300] if out else err[:200]}")
    return True

def phase5_verify():
    log("=" * 50)
    log("阶段 5: 验证部署", "PHASE")
    log("=" * 50)
    wd = f'cd /d "{PROJECT_DIR}" && '
    results = {}

    # Backend health
    out, _, code = runcmd(
        wd + "docker compose exec -T backend curl -sf http://localhost:8000/health 2>&1",
        timeout=30
    )
    results["backend_health"] = code == 0
    log(f"Backend /health: {'✓' if code==0 else '✗'} {out[:100]}")

    # Nginx
    out, _, code = runcmd("curl -sf http://localhost:80/ 2>&1", timeout=15)
    results["nginx"] = code == 0
    log(f"Nginx  :80: {'✓' if code==0 else '✗'}")

    # API docs
    out, _, code = runcmd("curl -sf http://localhost:8000/docs 2>&1", timeout=15)
    results["api_docs"] = code == 0
    log(f"API Docs: {'✓' if code==0 else '✗'}")

    # Grafana
    out, _, code = runcmd("curl -sf http://localhost:3000/api/health 2>&1", timeout=15)
    results["grafana"] = code == 0
    log(f"Grafana :3000: {'✓' if code==0 else '✗'}")

    return results

def phase6_harden():
    log("=" * 50)
    log("阶段 6: 生产强化", "PHASE")
    log("=" * 50)

    # Firewall rules
    log("配置 Windows 防火墙...")
    ports = {"HTTP":80, "HTTPS":443, "API":8000, "Grafana":3000,
             "EMQX-MQTT":1883, "EMQX-Admin":18083, "MinIO":9001,
             "RabbitMQ-Admin":15672, "Prometheus":9090}
    for name, port in ports.items():
        rule_name = f"ETDS-{name}"
        runps(f"Remove-NetFirewallRule -DisplayName '{rule_name}' -EA SilentlyContinue 2>$null")
        out, err, code = runps(
            f"New-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound -Protocol TCP -LocalPort {port} -Action Allow -Profile Any"
        )
    log("防火墙规则已配置", "OK")

    # Auto-restart scheduled task
    log("创建自动重启计划任务...")
    task_ps = f"""
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c cd /d "{PROJECT_DIR}" && docker compose up -d >> "%TEMP%\\etds-restart.log" 2>&1'
$trigger1 = New-ScheduledTaskTrigger -AtStartup
$trigger2 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At '00:00'
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Unregister-ScheduledTask -TaskName 'ETDS-AutoStart' -Confirm:$false -EA SilentlyContinue
Register-ScheduledTask -TaskName 'ETDS-AutoStart' -Action $action -Trigger $trigger1 -Principal $principal -Description 'Energy TDS Auto Start'
"""
    out, err, code = runps(task_ps.replace('\n', '; '), timeout=60)
    log(f"计划任务: {'OK' if code==0 else 'WARN - '+err[:100]}")
    return True

def main():
    print()
    print("=" * 60)
    print("  能源可信数据空间 - 生产部署")
    print(f"  目标: {SERVER_HOST}  用户: {SERVER_USER}")
    print(f"  开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    if not connect():
        sys.exit(1)

    try:
        docker_ok, compose_ok, git_ok = phase1_check()

        if not docker_ok:
            log("准备安装 Docker...", "INSTALL")
            install_docker()

        if not git_ok:
            install_git()

        if not phase2_code():
            log("代码克隆失败，中止部署", "ERROR")
            return

        phase2_env()
        phase3_build_start()
        phase4_init_db()
        results = phase5_verify()
        phase6_harden()

        ok_count = sum(1 for v in results.values() if v)
        total = len(results)

        print()
        print("=" * 60)
        print(f"  部署完成! 验证: {ok_count}/{total} 通过")
        print()
        print(f"  🌐 前端门户:   http://{SERVER_HOST}")
        print(f"  📖 API 文档:   http://{SERVER_HOST}:8000/docs")
        print(f"  📊 Grafana:    http://{SERVER_HOST}:3000  (admin / 见凭据文件)")
        print(f"  🗄  MinIO:      http://{SERVER_HOST}:9001")
        print(f"  📡 EMQX:       http://{SERVER_HOST}:18083")
        print(f"  🐰 RabbitMQ:   http://{SERVER_HOST}:15672")
        print(f"  📈 Prometheus: http://{SERVER_HOST}:9090")
        print()
        print(f"  凭据文件: production_credentials.txt (本地)")
        print("=" * 60)

    finally:
        if sftp: sftp.close()
        if ssh: ssh.close()

if __name__ == "__main__":
    main()
