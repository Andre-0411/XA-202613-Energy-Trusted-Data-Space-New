"""Deploy fixed files and restart uvicorn."""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
BACKEND_DIR = r"D:\Andre\project\energy-trusted-data-space\backend"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

def run_cmd(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('gbk', errors='replace').strip(), stderr.read().decode('gbk', errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=10)
    print(f"[OK] Connected to {HOST}")

    # Upload fixed files
    sftp = ssh.open_sftp()
    files = [
        (r"D:\Projects\energy-trusted-data-space\backend\app\services\monitor_service.py",
         f"{BACKEND_DIR}\\app\\services\\monitor_service.py"),
        (r"D:\Projects\energy-trusted-data-space\backend\app\api\v1\ops_alerts.py",
         f"{BACKEND_DIR}\\app\\api\\v1\\ops_alerts.py"),
        (r"D:\Projects\energy-trusted-data-space\backend\app\services\quality_service.py",
         f"{BACKEND_DIR}\\app\\services\\quality_service.py"),
    ]
    for local, remote in files:
        sftp.put(local, remote)
        print(f"  Uploaded: {remote.split(chr(92))[-1]}")
    sftp.close()

    # Kill existing uvicorn
    print("\n=== Restarting uvicorn ===")
    run_cmd(ssh, 'taskkill /F /IM python.exe 2>nul')
    time.sleep(2)

    # Clear log
    run_cmd(ssh, f'echo. > {PROJECT_DIR}\\uvicorn.log')

    # Restart via schtasks
    run_cmd(ssh, 'schtasks /Delete /TN "UvicornStart" /F 2>nul')
    bat_path = f"{PROJECT_DIR}\\start_uvicorn.bat"
    run_cmd(ssh, f'schtasks /Create /TN "UvicornStart" /TR "{bat_path}" /SC ONCE /ST 00:00 /F /RL HIGHEST')
    run_cmd(ssh, 'schtasks /Run /TN "UvicornStart"')

    # Wait
    time.sleep(12)

    # Check
    out, _ = run_cmd(ssh, f'type {PROJECT_DIR}\\uvicorn.log 2>nul')
    if "Application startup complete" in out:
        print("\n[OK] Uvicorn started successfully!")
    elif "Uvicorn running on" in out:
        print("\n[OK] Uvicorn is running!")
    else:
        print(f"\n[WARN] Log tail:")
        for line in out.split('\n')[-10:]:
            if line.strip():
                print(f"  {line}")

    # Check port
    out, _ = run_cmd(ssh, 'netstat -ano | findstr ":8000.*LISTEN" 2>nul')
    if out:
        print(f"[OK] Port 8000 LISTENING")
    else:
        print(f"[WARN] Port 8000 not found")

    ssh.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
