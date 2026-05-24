#!/usr/bin/env python3
"""上传前端 dist 到服务器并重启前端服务"""
import paramiko
import os
import time

HOST = '10.241.2.64'
USERNAME = 'zhouxuying'
PASSWORD = 'zhouxuying51'
PROJECT_DIR = r'D:\Andre\project\energy-trusted-data-space'
LOCAL_DIST = r'D:\Projects\energy-trusted-data-space\frontend\dist'
REMOTE_DIST = PROJECT_DIR + r'\frontend\dist'


def ssh_connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)
    return ssh


def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err


def upload_dist(ssh):
    """上传 dist 目录所有文件"""
    print('=== 上传前端 dist 目录 ===')
    sftp = ssh.open_sftp()

    count = 0
    errors = []
    for root, dirs, files in os.walk(LOCAL_DIST):
        for fname in files:
            local_path = os.path.join(root, fname)
            rel_path = os.path.relpath(local_path, LOCAL_DIST)
            remote_path = os.path.join(REMOTE_DIST, rel_path).replace('/', '\\')

            # Create remote directory
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                # mkdir recursively
                parts = remote_dir.split('\\')
                current = parts[0]
                for p in parts[1:]:
                    current = current + '\\' + p
                    try:
                        sftp.stat(current)
                    except FileNotFoundError:
                        try:
                            sftp.mkdir(current)
                        except Exception:
                            pass

            try:
                sftp.put(local_path, remote_path)
                count += 1
                if count % 50 == 0:
                    print(f'  已上传 {count} 个文件...')
            except Exception as e:
                errors.append(f'{rel_path}: {e}')

    sftp.close()
    print(f'  上传完成: {count} 个文件, {len(errors)} 个错误')
    if errors:
        for e in errors[:5]:
            print(f'  错误: {e}')
    return count


def restart_frontend(ssh):
    """重启前端服务"""
    print()
    print('=== 重启前端服务 ===')

    # Kill existing frontend on port 8080
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8080" | findstr "LISTENING"')
    if out:
        for line in out.strip().split('\n'):
            parts = line.strip().split()
            if parts:
                pid = parts[-1]
                if pid != '0':
                    run_cmd(ssh, f'taskkill /F /PID {pid}')
                    print(f'  已终止前端进程 PID={pid}')

    time.sleep(1)

    # Start frontend
    cmd = (
        f'cd /d {PROJECT_DIR} && '
        f'set PYTHONIOENCODING=utf-8&& '
        f'start /B python serve_frontend.py'
    )
    run_cmd(ssh, cmd)
    time.sleep(3)

    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8080" | findstr "LISTENING"')
    if out:
        print('  ✓ 前端服务器已启动 (8080)')
    else:
        print('  ⚠ 8080 未就绪，再等...')
        time.sleep(3)
        out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8080" | findstr "LISTENING"')
        print('  ✓ 前端已启动' if out else '  ✗ 前端启动失败')


def verify(ssh):
    """验证服务"""
    print()
    print('=== 验证 ===')
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000" | findstr "LISTENING"')
    print(f'后端 8000: {"✓ 在线" if out else "✗ 离线"}')

    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8080" | findstr "LISTENING"')
    print(f'前端 8080: {"✓ 在线" if out else "✗ 离线"}')

    out, _ = run_cmd(ssh, 'curl -s -o nul -w "%{http_code}" http://localhost:8080/ 2>nul')
    print(f'前端首页 HTTP: {out}')


def main():
    print(f'开始部署前端到 {HOST}...')
    ssh = ssh_connect()

    try:
        upload_dist(ssh)
        restart_frontend(ssh)
        verify(ssh)
        print()
        print(f'部署完成! 访问: http://{HOST}:8080')
    except Exception as e:
        print(f'部署失败: {e}')
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()


if __name__ == '__main__':
    main()
