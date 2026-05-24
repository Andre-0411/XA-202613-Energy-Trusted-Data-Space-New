"""Check server project structure and try alternative startup methods."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
BASE = r"D:\Andre\project\energy-trusted-data-space"
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

    # Check what's in the project directory
    print("\n=== Project structure ===")
    out, _ = run_cmd(ssh, f'dir {BASE} /B 2>nul')
    print(out)
    
    # Check if app directory exists
    print("\n=== Check app dir ===")
    out, _ = run_cmd(ssh, f'dir {BASE}\\app /B 2>nul')
    print(f"app/ contents: {out[:300]}")
    
    # Check if main.py exists
    out, _ = run_cmd(ssh, f'type {BASE}\\app\\main.py 2>nul | findstr "app"')
    print(f"main.py check: {out[:200]}")
    
    # Test: Can python import app from that directory?
    print("\n=== Test Python import ===")
    test_cmd = f'cd /d {BASE} && {PYTHON} -c "import os; print(os.getcwd()); import app; print(\'import ok\')"'
    out, err = run_cmd(ssh, test_cmd, timeout=15)
    print(f"  cwd: {out}")
    if err:
        print(f"  error: {err[:300]}")
    
    # Test with explicit PYTHONPATH
    print("\n=== Test with PYTHONPATH ===")
    test_cmd2 = f'set PYTHONPATH={BASE} && {PYTHON} -c "import app; print(\'ok\')"'
    out, err = run_cmd(ssh, test_cmd2, timeout=15)
    print(f"  result: {out}")
    if err:
        print(f"  error: {err[:300]}")
    
    # Try the batch file approach with full path in python -c
    print("\n=== Test direct uvicorn with sys.path ===")
    test_cmd3 = (
        f'{PYTHON} -c "import sys; sys.path.insert(0, r\'{BASE}\'); '
        f'import uvicorn; uvicorn.run(\'app.main:app\', host=\'0.0.0.0\', port=8000)"'
    )
    print(f"  Command: {test_cmd3[:200]}")
    
    # Update batch file with PYTHONPATH
    print("\n=== Update batch file with PYTHONPATH ===")
    bat_content = f"""@echo off
set PYTHONPATH={BASE}
cd /d {BASE}
echo Starting uvicorn at %date% %time% >> {BASE}\\uvicorn_startup.log
{PYTHON} -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> {BASE}\\uvicorn.log 2>&1
"""
    sftp = ssh.open_sftp()
    bat_path = r"D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat"
    with sftp.open(bat_path, 'w') as f:
        f.write(bat_content)
    sftp.close()
    print("  Updated batch file with PYTHONPATH")
    
    # Kill old processes and restart
    print("\n=== Restart ===")
    run_cmd(ssh, 'taskkill /F /IM python.exe 2>nul')
    time.sleep(2)
    
    # Clear old log
    run_cmd(ssh, f'echo. > {BASE}\\uvicorn.log')
    
    # Run via schtasks
    run_cmd(ssh, 'schtasks /Delete /TN "UvicornStart" /F 2>nul')
    create_cmd = (
        f'schtasks /Create /TN "UvicornStart" /TR "{bat_path}" '
        f'/SC ONCE /ST 00:00 /F /RL HIGHEST'
    )
    out, err = run_cmd(ssh, create_cmd, timeout=15)
    print(f"  Create: {out[:200]}")
    
    out, err = run_cmd(ssh, 'schtasks /Run /TN "UvicornStart"', timeout=15)
    print(f"  Run: {out[:200]}")
    
    time.sleep(10)
    
    # Check log
    print("\n=== Check logs ===")
    out, _ = run_cmd(ssh, f'type {BASE}\\uvicorn.log 2>nul')
    print(f"  Log (last 15 lines):")
    for line in out.split('\n')[-15:]:
        print(f"    {line}")
    
    # Check port
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000.*LISTEN" 2>nul')
    print(f"\n  Port 8000 LISTENING: {out[:300]}")
    
    # Check python processes
    out, _ = run_cmd(ssh, 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>nul')
    print(f"\n  Python processes: {out[:300]}")
    
    ssh.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
