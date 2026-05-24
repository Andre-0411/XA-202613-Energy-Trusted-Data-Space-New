"""Restart uvicorn on server with correct working directory approach."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"
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

    # Step 1: Kill existing uvicorn/python processes on port 8000
    print("\n=== Step 1: Kill existing processes on port 8000 ===")
    out, err = run_cmd(ssh, 'netstat -ano | findstr ":8000 "')
    if out:
        for line in out.split('\n'):
            parts = line.split()
            if len(parts) >= 5 and '8000' in parts[1]:
                pid = parts[-1]
                if pid != '0':
                    print(f"  Killing PID {pid}...")
                    run_cmd(ssh, f'taskkill /F /PID {pid}')
        time.sleep(2)
    
    # Also kill any stale python processes that are uvicorn
    out, _ = run_cmd(ssh, 'wmic process where "CommandLine like \'%uvicorn%\'" get ProcessId /format:value 2>nul')
    for line in out.split('\n'):
        if 'ProcessId=' in line:
            pid = line.split('=')[-1].strip()
            if pid and pid.isdigit():
                print(f"  Killing stale uvicorn PID {pid}...")
                run_cmd(ssh, f'taskkill /F /PID {pid}')
    time.sleep(1)

    # Step 2: Start uvicorn using cmd /c with proper cd
    print("\n=== Step 2: Start uvicorn ===")
    
    # Method: Use wmic with cmd /c to set working directory
    start_cmd = (
        f'wmic process call create '
        f'"cmd /c cd /d {PROJECT_DIR} && {PYTHON} -m uvicorn app.main:app --host 0.0.0.0 --port 8000"'
    )
    print(f"  Running: {start_cmd}")
    out, err = run_cmd(ssh, start_cmd, timeout=30)
    print(f"  Output: {out[:300]}")
    if err:
        print(f"  Stderr: {err[:300]}")

    # Step 3: Wait and verify
    print("\n=== Step 3: Wait for startup and verify ===")
    time.sleep(8)
    
    # Check process exists
    out, _ = run_cmd(ssh, 'wmic process where "CommandLine like \'%uvicorn%\'" get ProcessId,CommandLine /format:list 2>nul')
    print(f"  Uvicorn processes:\n{out[:500]}")
    
    # Check port is listening
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000 "')
    print(f"\n  Port 8000 status:\n{out[:500]}")
    
    # Try to access locally
    print("\n=== Step 4: Test local access ===")
    out, err = run_cmd(ssh, f'{PYTHON} -c "import urllib.request; r = urllib.request.urlopen(\'http://127.0.0.1:8000/docs\', timeout=5); print(r.status)"', timeout=15)
    print(f"  Local test: {out}")
    if err:
        print(f"  Error: {err[:300]}")
    
    ssh.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
