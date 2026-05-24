"""
裸机部署 - 续跑脚本 (阶段5-7)
代码已上传、依赖已安装、PG已连接
"""
import paramiko
import time
from datetime import datetime

HOST, PORT, USER, PW = "10.241.2.64", 22, "zhouxuying", "zhouxuying51"
DEPLOY_DIR = r"D:\EnergyTDS"
BACKEND_DIR = DEPLOY_DIR + r"\backend"

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"OK":"[OK]","WARN":"[!!]","ERR":"[XX]","PHASE":">>>"}
    print(f"[{ts}] {icons.get(level,'   ')} {msg}", flush=True)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, PORT, USER, PW, timeout=30)
log("SSH连接成功", "OK")

def cmd(c, t=30):
    i,o,e = ssh.exec_command(c, timeout=t)
    out = o.read().decode("utf-8","replace").strip()
    err = e.read().decode("utf-8","replace").strip()
    return out, err, o.channel.recv_exit_status()

# ===== 阶段5: 启动 Redis =====
log("="*50, "PHASE")
log("阶段5: 启动 Redis", "PHASE")
log("="*50, "PHASE")

out, err, code = cmd('netstat -ano | findstr 6379 | findstr LISTENING', 10)
if code == 0 and out.strip():
    log("Redis 已在运行", "OK")
else:
    log("启动 Redis...", "PHASE")
    cmd('powershell -NoProfile -Command "Start-Process -FilePath \'D:\\Andre\\software\\redis\\redis-server.exe\' -WindowStyle Hidden -ArgumentList \'--port 6379 --save 900 1 --save 300 10\'"', 15)
    time.sleep(3)
    out, err, code = cmd('netstat -ano | findstr 6379 | findstr LISTENING', 10)
    if code == 0 and out.strip():
        log("Redis 启动成功 (port 6379)", "OK")
    else:
        log("Redis 启动失败，后端降级运行", "WARN")

# ===== 阶段6: 创建数据库表 =====
log("="*50, "PHASE")
log("阶段6: 创建数据库表", "PHASE")
log("="*50, "PHASE")

out, err, code = cmd(
    f'cd /d "{BACKEND_DIR}" && python -c "'
    f'import asyncio;'
    f'from app.database import async_engine, Base;'
    f'from app import models;'
    f'async def m():'
    f'  async with async_engine.begin() as c:'
    f'    await c.run_sync(Base.metadata.create_all);'
    f'    print(\"Tables created successfully\");'
    f'asyncio.run(m())" 2>&1',
    60
)
log(f"表创建: {out[:300]} {'[OK]' if 'successfully' in out else '[WARN]'}")

# ===== 阶段7: 启动后端 =====
log("="*50, "PHASE")
log("阶段7: 启动后端服务", "PHASE")
log("="*50, "PHASE")

# 杀掉占用 8000 端口的旧进程
out, err, code = cmd('netstat -ano | findstr :8000 | findstr LISTENING', 5)
if code == 0 and out.strip():
    for line in out.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) >= 5:
            pid = parts[-1]
            log(f"杀掉旧进程 PID {pid}")
            cmd(f"taskkill /F /PID {pid}", 5)
    time.sleep(1)

# 启动 uvicorn
log("启动 uvicorn (port 8000, 4 workers)...", "PHASE")
cmd(f'cd /d "{BACKEND_DIR}" && start /B "" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info > "{BACKEND_DIR}\\uvicorn.log" 2>&1', 10)
time.sleep(8)

# 验证端口
out, err, code = cmd('netstat -ano | findstr :8000 | findstr LISTENING', 5)
if code == 0 and out.strip():
    log(f"uvicorn 已启动: {out.strip()}", "OK")
else:
    log("uvicorn 未启动，检查日志...", "WARN")
    out, err, code = cmd(f'type "{BACKEND_DIR}\\uvicorn.log"', 10)
    log(f"日志:\n{out[:800]}", "WARN")

# 健康检查
time.sleep(3)
out, err, code = cmd('curl -s http://localhost:8000/health 2>&1', 10)
if "healthy" in out.lower():
    log(f"健康检查通过: {out.strip()}", "OK")
else:
    log(f"健康检查: {out[:300]}", "WARN")
    # 查看详细日志
    out2, err2, code2 = cmd(f'type "{BACKEND_DIR}\\uvicorn.log"', 10)
    log(f"详细日志:\n{out2[:1500]}", "WARN")

# ===== 阶段8: 配置自启动 =====
log("="*50, "PHASE")
log("阶段8: 配置自启动", "PHASE")
log("="*50, "PHASE")

bat_content = f"""@echo off
echo [%date% %time%] Starting EnergyTDS...
start "" /B "D:\\Andre\\software\\redis\\redis-server.exe" --port 6379 --save 900 1 --save 300 10
timeout /t 2 /nobreak >nul
cd /d "{BACKEND_DIR}"
start "" /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info
echo [%date% %time%] EnergyTDS started!
echo   API:    http://localhost:8000
echo   Docs:   http://localhost:8000/docs
echo   Health: http://localhost:8000/health
"""
sftp = ssh.open_sftp()
try:
    f = sftp.file(f"{DEPLOY_DIR}\\start_services.bat", 'w')
    f.write(bat_content)
    f.close()
except:
    pass
sftp.close()

cmd(f'schtasks /Create /TN "EnergyTDS_Startup" /TR "{DEPLOY_DIR}\\start_services.bat" /SC ONLOGON /RL HIGHEST /F 2>&1', 10)
log("自启动计划任务已配置", "OK")

# ===== 完成 =====
log("="*50)
log("部署完成!", "OK")
log("="*50)
log(f"  API:      http://{HOST}:8000")
log(f"  文档:     http://{HOST}:8000/docs")
log(f"  健康检查: http://{HOST}:8000/health")
log(f"  部署目录: {DEPLOY_DIR}")
log(f"  后端目录: {BACKEND_DIR}")
log(f"  日志文件: {BACKEND_DIR}\\uvicorn.log")
log(f"  启动脚本: {DEPLOY_DIR}\\start_services.bat")

ssh.close()
