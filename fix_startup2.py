"""Fix uvicorn startup - the app module is in backend/ subdirectory."""
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

    # Verify backend/app exists
    print("\n=== Verify backend/app structure ===")
    out, _ = run_cmd(ssh, f'dir {BACKEND_DIR}\\app /B 2>nul')
    print(f"  backend/app/ contents: {out[:300]}")
    
    # Check main.py exists
    out, _ = run_cmd(ssh, f'if exist "{BACKEND_DIR}\\app\\main.py" (echo EXISTS) else (echo NOT_FOUND)')
    print(f"  main.py: {out}")

    # Kill existing processes
    print("\n=== Kill existing processes ===")
    run_cmd(ssh, 'taskkill /F /IM python.exe 2>nul')
    time.sleep(2)

    # Update batch file with CORRECT path (backend/)
    print("\n=== Create correct batch file ===")
    bat_content = f"""@echo off
cd /d {BACKEND_DIR}
echo Starting uvicorn at %date% %time% >> {PROJECT_DIR}\\uvicorn_startup.log
{PYTHON} -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> {PROJECT_DIR}\\uvicorn.log 2>&1
"""
    sftp = ssh.open_sftp()
    bat_path = f"{PROJECT_DIR}\\start_uvicorn.bat"
    with sftp.open(bat_path, 'w') as f:
        f.write(bat_content)
    print(f"  Updated: {bat_path}")
    print(f"  Working dir: {BACKEND_DIR}")
    sftp.close()

    # Clear old log
    run_cmd(ssh, f'echo. > {PROJECT_DIR}\\uvicorn.log')
    
    # Run via schtasks
    print("\n=== Start via schtasks ===")
    run_cmd(ssh, 'schtasks /Delete /TN "UvicornStart" /F 2>nul')
    
    create_cmd = (
        f'schtasks /Create /TN "UvicornStart" /TR "{bat_path}" '
        f'/SC ONCE /ST 00:00 /F /RL HIGHEST'
    )
    out, err = run_cmd(ssh, create_cmd, timeout=15)
    print(f"  Create: {out[:200]}")
    
    out, err = run_cmd(ssh, 'schtasks /Run /TN "UvicornStart"', timeout=15)
    print(f"  Run: {out[:200]}")
    
    # Wait for startup
    print("\n=== Wait for startup ===")
    time.sleep(12)
    
    # Check log
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\uvicorn.log 2>nul')
    print(f"  Uvicorn log (last 15 lines):")
    for line in out.split('\n')[-15:]:
        if line.strip():
            print(f"    {line}")
    
    # Check port
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000.*LISTEN" 2>nul')
    print(f"\n  Port 8000 LISTENING: {out[:300]}")
    
    # Check python processes
    out, _ = run_cmd(ssh, 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>nul')
    print(f"\n  Python processes: {out[:500]}")
    
    # Test HTTP
    print("\n=== Test HTTP access ===")
    out, err = run_cmd(ssh, f'{PYTHON} -c "import urllib.request; r = urllib.request.urlopen(\'http://127.0.0.1:8000/docs\', timeout=5); print(\'STATUS:\', r.status)"', timeout=15)
    print(f"  Result: {out}")
    if err:
        print(f"  Error: {err[:300]}")
    
    ssh.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
