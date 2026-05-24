"""Fix .env to use 127.0.0.1 instead of localhost, then restart uvicorn."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"
BACKEND_DIR = r"D:\Andre\project\energy-trusted-data-space\backend"
PYTHON = r"D:\xujingyi\anaconda3\python.exe"

def run_cmd(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace').strip()
    err = stderr.read().decode('gbk', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=10)
    print(f"[OK] Connected to {HOST}")

    # Step 1: Fix .env - replace localhost with 127.0.0.1
    print("\n=== Step 1: Fix .env ===")
    env_path = f"{PROJECT_DIR}\\.env"
    
    # Read current .env
    out, _ = run_cmd(ssh, f'type {env_path}')
    new_env = out.replace('POSTGRES_HOST=localhost', 'POSTGRES_HOST=127.0.0.1')
    new_env = new_env.replace('REDIS_HOST=localhost', 'REDIS_HOST=127.0.0.1')
    new_env = new_env.replace('MONGO_HOST=localhost', 'MONGO_HOST=127.0.0.1')
    new_env = new_env.replace('MINIO_ENDPOINT=localhost:', 'MINIO_ENDPOINT=127.0.0.1:')
    
    # Write fixed .env (sftp.open doesn't support encoding, write bytes)
    sftp = ssh.open_sftp()
    with sftp.open(env_path, 'w') as f:
        f.write(new_env.encode('utf-8'))
    sftp.close()
    print("  Updated .env: localhost -> 127.0.0.1")
    
    # Also create .env in backend/ if needed
    backend_env = f"{BACKEND_DIR}\\.env"
    out, _ = run_cmd(ssh, f'if exist "{backend_env}" (echo EXISTS) else (echo NOT_FOUND)')
    if out == 'NOT_FOUND':
        sftp = ssh.open_sftp()
        with sftp.open(backend_env, 'w') as f:
            f.write(new_env.encode('utf-8'))
        sftp.close()
        print("  Created backend/.env")
    else:
        print("  backend/.env already exists")

    # Step 2: Kill existing python processes
    print("\n=== Step 2: Kill existing processes ===")
    run_cmd(ssh, 'taskkill /F /IM python.exe 2>nul')
    time.sleep(2)

    # Step 3: Restart uvicorn
    print("\n=== Step 3: Restart uvicorn ===")
    # Clear log
    run_cmd(ssh, f'echo. > {PROJECT_DIR}\\uvicorn.log')
    
    # Delete and recreate task
    run_cmd(ssh, 'schtasks /Delete /TN "UvicornStart" /F 2>nul')
    
    bat_path = f"{PROJECT_DIR}\\start_uvicorn.bat"
    create_cmd = (
        f'schtasks /Create /TN "UvicornStart" /TR "{bat_path}" '
        f'/SC ONCE /ST 00:00 /F /RL HIGHEST'
    )
    out, _ = run_cmd(ssh, create_cmd, timeout=15)
    print(f"  Create task: {out[:100]}")
    
    out, _ = run_cmd(ssh, 'schtasks /Run /TN "UvicornStart"', timeout=15)
    print(f"  Run task: {out[:100]}")
    
    # Wait
    print("\n=== Step 4: Wait and verify ===")
    time.sleep(12)
    
    # Check log
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\uvicorn.log 2>nul')
    print(f"  Uvicorn log:")
    for line in out.split('\n')[-20:]:
        if line.strip():
            print(f"    {line}")
    
    # Check port
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000 " 2>nul')
    print(f"\n  Port 8000: {out[:300] if out else 'NOT FOUND'}")
    
    # Check python process
    out, _ = run_cmd(ssh, 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>nul')
    print(f"\n  Python: {out[:300]}")
    
    # Test HTTP
    print("\n=== Step 5: Test HTTP ===")
    out, err = run_cmd(ssh, f'{PYTHON} -c "import urllib.request; r = urllib.request.urlopen(\'http://127.0.0.1:8000/docs\', timeout=5); print(\'STATUS:\', r.status)"', timeout=15)
    print(f"  Result: {out}")
    if err:
        print(f"  Error: {err[:300]}")
    
    ssh.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
