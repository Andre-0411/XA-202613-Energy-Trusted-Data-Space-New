"""Restart uvicorn by creating a .bat file on the server and running it via schtasks."""
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

    # Step 1: Kill existing processes
    print("\n=== Step 1: Kill existing processes ===")
    run_cmd(ssh, 'taskkill /F /IM uvicorn.exe 2>nul')
    # Kill any python running uvicorn
    out, _ = run_cmd(ssh, 'wmic process where "CommandLine like \'%uvicorn%\'" get ProcessId /format:value 2>nul')
    for line in out.split('\n'):
        if 'ProcessId=' in line:
            pid = line.split('=')[-1].strip()
            if pid and pid.isdigit():
                print(f"  Killing PID {pid}...")
                run_cmd(ssh, f'taskkill /F /PID {pid}')
    
    # Also check port 8000
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000.*LISTEN" 2>nul')
    if out:
        for line in out.split('\n'):
            parts = line.split()
            if parts:
                pid = parts[-1]
                if pid.isdigit() and pid != '0':
                    print(f"  Killing process on port 8000: PID {pid}")
                    run_cmd(ssh, f'taskkill /F /PID {pid}')
    time.sleep(2)

    # Step 2: Create .bat file on server
    print("\n=== Step 2: Create startup batch file ===")
    bat_content = f"""@echo off
cd /d {PROJECT_DIR}
echo Starting uvicorn at %date% %time% >> {PROJECT_DIR}\\uvicorn_startup.log
{PYTHON} -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> {PROJECT_DIR}\\uvicorn.log 2>&1
"""
    # Write bat file via sftp
    sftp = ssh.open_sftp()
    bat_path = r"D:\Andre\project\energy-trusted-data-space\start_uvicorn.bat"
    with sftp.open(bat_path, 'w') as f:
        f.write(bat_content)
    print(f"  Created: {bat_path}")
    
    # Also create a vbs wrapper to run it hidden
    vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c {bat_path}", 0, False
"""
    vbs_path = r"D:\Andre\project\energy-trusted-data-space\start_uvicorn.vbs"
    with sftp.open(vbs_path, 'w') as f:
        f.write(vbs_content)
    print(f"  Created: {vbs_path}")
    sftp.close()

    # Step 3: Try running via schtasks with immediate start
    print("\n=== Step 3: Start via schtasks ===")
    # Delete old task if exists
    run_cmd(ssh, 'schtasks /Delete /TN "UvicornStart" /F 2>nul')
    
    # Create task that runs immediately
    create_cmd = (
        f'schtasks /Create /TN "UvicornStart" /TR "{bat_path}" '
        f'/SC ONSTART /F /RL HIGHEST /RU {USER} /RP {PASS}'
    )
    out, err = run_cmd(ssh, create_cmd, timeout=15)
    print(f"  Create task: {out[:200]}")
    if err:
        print(f"  Error: {err[:200]}")
    
    # Run task immediately
    out, err = run_cmd(ssh, 'schtasks /Run /TN "UvicornStart"', timeout=15)
    print(f"  Run task: {out[:200]}")
    if err:
        print(f"  Error: {err[:200]}")
    
    # Step 4: Also try direct start via wscript
    print("\n=== Step 4: Also try wscript.vbs approach ===")
    out, err = run_cmd(ssh, f'wscript //B "{vbs_path}"', timeout=10)
    print(f"  wscript: {out[:200]}")
    if err:
        print(f"  Error: {err[:200]}")
    
    # Step 5: Wait and check
    print("\n=== Step 5: Wait and verify ===")
    time.sleep(10)
    
    # Check startup log
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\uvicorn_startup.log 2>nul')
    print(f"  Startup log: {out[:300]}")
    
    # Check uvicorn log
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\uvicorn.log 2>nul')
    print(f"  Uvicorn log (last 10 lines):")
    for line in out.split('\n')[-10:]:
        print(f"    {line}")
    
    # Check process
    out, _ = run_cmd(ssh, 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2>nul')
    print(f"\n  Python processes:\n{out[:500]}")
    
    # Check port
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000 " 2>nul')
    print(f"\n  Port 8000:\n{out[:500]}")
    
    # Test access
    print("\n=== Step 6: Test HTTP access ===")
    out, err = run_cmd(ssh, f'{PYTHON} -c "import urllib.request; r = urllib.request.urlopen(\'http://127.0.0.1:8000/docs\', timeout=5); print(\'STATUS:\', r.status)"', timeout=15)
    print(f"  Result: {out}")
    if err:
        print(f"  Error: {err[:300]}")
    
    ssh.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
