#!/usr/bin/env python3
"""部署脚本 - 从GitHub拉取代码并构建前端 (Windows服务器版)"""
import paramiko
import sys

# 服务器配置
HOST = "10.241.2.64"
PORT = 22
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT_DIR = "C:\\Users\\zhouxuying\\energy-trusted-data-space"

def ssh_connect():
    """建立SSH连接"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, PORT, USERNAME, PASSWORD, timeout=30)
    return client

def run_command(client, command, timeout=300):
    """执行命令并返回输出"""
    print(f"\n>>> 执行: {command}")
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)

    # 读取输出
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')

    if output:
        print(output)
    if error:
        print(f"[stderr] {error}")

    return output, error

def main():
    print(f"连接到Windows服务器 {HOST}...")
    client = ssh_connect()
    print("连接成功！")

    try:
        # 1. 检查项目目录
        print("\n" + "="*50)
        print("步骤1: 检查项目目录")
        output, _ = run_command(client, f'if exist "{PROJECT_DIR}" (echo exists) else (echo not_exists)')

        # 2. 如果目录不存在，克隆仓库
        if "not_exists" in output:
            print("\n" + "="*50)
            print("步骤2: 克隆GitHub仓库")
            run_command(client, f'cd C:\\Users\\zhouxuying && git clone https://github.com/Andre-0411/XA-202613-Energy-Trusted-Data-Space-New.git energy-trusted-data-space', timeout=120)

        # 3. 拉取最新代码
        print("\n" + "="*50)
        print("步骤3: 拉取最新代码")
        run_command(client, f'cd {PROJECT_DIR} && git pull origin main')

        # 4. 检查Node环境
        print("\n" + "="*50)
        print("步骤4: 检查Node环境")
        run_command(client, "node -v && npm -v")

        # 5. 安装依赖并构建前端
        print("\n" + "="*50)
        print("步骤5: 安装依赖")
        run_command(client, f'cd {PROJECT_DIR}\\frontend && npm install', timeout=120)

        print("\n" + "="*50)
        print("步骤6: 构建前端")
        run_command(client, f'cd {PROJECT_DIR}\\frontend && set NODE_OPTIONS=--max-old-space-size=2048 && npm run build', timeout=300)

        # 6. 检查构建结果
        print("\n" + "="*50)
        print("步骤7: 检查构建结果")
        run_command(client, f'dir {PROJECT_DIR}\\frontend\\dist')

        print("\n" + "="*50)
        print("✅ 部署完成！")
        print(f"构建产物位置: {PROJECT_DIR}\\frontend\\dist")

    except Exception as e:
        print(f"\n❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
