"""上传种子脚本并执行，然后验证登录"""
import paramiko
import time

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

def ssh_exec(ssh, cmd, timeout=120):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('gbk', errors='replace')
    err = stderr.read().decode('gbk', errors='replace')
    if out.strip():
        print(out.strip())
    if err.strip():
        print(f"[STDERR] {err.strip()}")
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    print(f"Connected to {HOST}")

    # Upload seed script
    sftp = ssh.open_sftp()

    # Read local file
    with open(r"D:\Projects\energy-trusted-data-space\seed_final_v2.py", 'r', encoding='utf-8') as f:
        seed_content = f.read()

    with sftp.open(f"{PROJECT_DIR}\\seed_final_v2.py", 'w') as f:
        f.write(seed_content)
    sftp.close()
    print("seed_final_v2.py uploaded")

    # Run seed
    out, err = ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python seed_final_v2.py", timeout=60)

    # Restart backend
    print("\n--- Restarting backend ---")
    ssh_exec(ssh, "schtasks /End /TN \"ETDS-Backend\" 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %a 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "schtasks /Run /TN \"ETDS-Backend\"", timeout=15)

    # Wait for backend
    print("\nWaiting for backend...")
    for i in range(20):
        time.sleep(3)
        out, _ = ssh_exec(ssh, "netstat -ano | findstr :8000 | findstr LISTENING", timeout=10)
        if "8000" in out and "LISTENING" in out:
            print("Backend ready on port 8000!")
            break

    # Restart frontend
    print("\n--- Restarting frontend ---")
    ssh_exec(ssh, "schtasks /End /TN \"ETDS-Frontend\" 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :8080 ^| findstr LISTENING') do taskkill /F /PID %a 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "schtasks /Run /TN \"ETDS-Frontend\"", timeout=15)
    time.sleep(3)

    # Test login directly on backend
    print("\n--- Testing login (backend direct) ---")
    test_cmd = (
        "powershell -Command \""
        "$body = '{\\\"username\\\":\\\"admin\\\",\\\"password\\\":\\\"admin123\\\",\\\"auth_type\\\":\\\"password\\\"}'; "
        "try { "
        "$r = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST "
        "-Body $body -ContentType 'application/json' -UseBasicParsing -TimeoutSec 10; "
        "Write-Host ('HTTP ' + $r.StatusCode); "
        "Write-Host $r.Content "
        "} catch { "
        "$resp = $_.Exception.Response; "
        "if ($resp) { "
        "$sr = New-Object System.IO.StreamReader($resp.GetResponseStream()); "
        "Write-Host $sr.ReadToEnd() "
        "} else { "
        "Write-Host $_.Exception.Message "
        "} "
        "}\""
    )
    ssh_exec(ssh, test_cmd, timeout=20)

    # Test login via frontend proxy
    print("\n--- Testing login (via proxy) ---")
    test_proxy = (
        "powershell -Command \""
        "$body = '{\\\"username\\\":\\\"admin\\\",\\\"password\\\":\\\"admin123\\\",\\\"auth_type\\\":\\\"password\\\"}'; "
        "try { "
        "$r = Invoke-WebRequest -Uri 'http://localhost:8080/api/v1/auth/login' -Method POST "
        "-Body $body -ContentType 'application/json' -UseBasicParsing -TimeoutSec 10; "
        "Write-Host ('HTTP ' + $r.StatusCode); "
        "Write-Host $r.Content "
        "} catch { "
        "$resp = $_.Exception.Response; "
        "if ($resp) { "
        "$sr = New-Object System.IO.StreamReader($resp.GetResponseStream()); "
        "Write-Host $sr.ReadToEnd() "
        "} else { "
        "Write-Host $_.Exception.Message "
        "} "
        "}\""
    )
    ssh_exec(ssh, test_proxy, timeout=20)

    # Check ports
    print("\n--- Port check ---")
    ssh_exec(ssh, "netstat -ano | findstr LISTENING | findstr \"8000 8080\"", timeout=10)

    print("\n" + "="*60)
    print(f"  Frontend: http://{HOST}:8080")
    print(f"  Backend:  http://{HOST}:8000")
    print(f"  Login:    admin / admin123")
    print("="*60)

    ssh.close()

if __name__ == "__main__":
    main()
