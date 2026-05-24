"""上传种子脚本v3并测试登录"""
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

    # Upload seed script v3
    sftp = ssh.open_sftp()
    with open(r"D:\Projects\energy-trusted-data-space\seed_final_v3.py", 'r', encoding='utf-8') as f:
        content = f.read()
    with sftp.open(f"{PROJECT_DIR}\\seed_final_v3.py", 'w') as f:
        f.write(content)
    sftp.close()
    print("seed_final_v3.py uploaded")

    # Run seed
    out, err = ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python seed_final_v3.py", timeout=60)

    # Restart backend
    print("\n--- Restart backend ---")
    ssh_exec(ssh, "schtasks /End /TN \"ETDS-Backend\" 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "for /f \"tokens=5\" %a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %a 2>nul", timeout=15)
    time.sleep(1)
    ssh_exec(ssh, "schtasks /Run /TN \"ETDS-Backend\"", timeout=15)

    print("\nWaiting for backend...")
    for i in range(20):
        time.sleep(3)
        out, _ = ssh_exec(ssh, "netstat -ano | findstr :8000 | findstr LISTENING", timeout=10)
        if "8000" in out and "LISTENING" in out:
            print("Backend ready!")
            break
    else:
        # Check backend log
        ssh_exec(ssh, f"type {PROJECT_DIR}\\backend.log 2>nul", timeout=10)

    # Test login
    print("\n--- Test login via proxy ---")
    ssh_exec(ssh,
        'powershell -Command "'
        "$body = '{\"username\":\"admin\",\"password\":\"admin123\",\"auth_type\":\"password\"}'; "
        "try { "
        "$r = Invoke-WebRequest -Uri 'http://localhost:8080/api/v1/auth/login' -Method POST "
        "-Body $body -ContentType 'application/json' -UseBasicParsing -TimeoutSec 15; "
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
        '}"',
        timeout=30
    )

    # Test frontend page
    print("\n--- Test frontend page ---")
    ssh_exec(ssh,
        'powershell -Command "'
        "try { "
        "$r = Invoke-WebRequest -Uri 'http://localhost:8080' -UseBasicParsing -TimeoutSec 10; "
        "Write-Host ('Frontend: HTTP ' + $r.StatusCode + ' Length: ' + $r.Content.Length) "
        "} catch { "
        "Write-Host $_.Exception.Message "
        "} "
        '}"',
        timeout=20
    )

    # Port check
    ssh_exec(ssh, "netstat -ano | findstr LISTENING | findstr \"8000 8080\"", timeout=10)

    print("\n" + "="*60)
    print(f"  Frontend: http://{HOST}:8080")
    print(f"  Backend:  http://{HOST}:8000")
    print(f"  Login:    admin / admin123")
    print("="*60)

    ssh.close()

if __name__ == "__main__":
    main()
