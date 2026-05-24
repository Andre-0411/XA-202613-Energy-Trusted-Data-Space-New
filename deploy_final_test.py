"""上传 SM3 种子脚本并完整测试"""
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

    # Upload seed_sm3.py
    sftp = ssh.open_sftp()
    with open(r"D:\Projects\energy-trusted-data-space\seed_sm3.py", 'r', encoding='utf-8') as f:
        content = f.read()
    with sftp.open(f"{PROJECT_DIR}\\seed_sm3.py", 'w') as f:
        f.write(content)
    sftp.close()
    print("seed_sm3.py uploaded")

    # Run seed
    ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python seed_sm3.py", timeout=60)

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

    # Upload test script
    test_code = '''
import urllib.request, json

data = json.dumps({"username": "admin", "password": "admin123", "auth_type": "password"}).encode("utf-8")

try:
    req = urllib.request.Request("http://localhost:8000/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    body = json.loads(resp.read().decode("utf-8"))
    if body.get("code") == 0:
        print("BACKEND LOGIN SUCCESS!")
        print(f"Token type: {body['data'].get('token_type')}")
        print(f"Token (first 80): {body['data'].get('access_token', '')[:80]}...")
    else:
        print(f"Backend failed: {body.get('message')}")
except urllib.error.HTTPError as e:
    print(f"Backend HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Backend error: {e}")

# Proxy test
try:
    req2 = urllib.request.Request("http://localhost:8080/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
    resp2 = urllib.request.urlopen(req2, timeout=10)
    body2 = json.loads(resp2.read().decode("utf-8"))
    if body2.get("code") == 0:
        print("PROXY LOGIN SUCCESS!")
    else:
        print(f"Proxy failed: {body2.get('message')}")
except urllib.error.HTTPError as e:
    print(f"Proxy HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Proxy error: {e}")

# Frontend page
try:
    req3 = urllib.request.Request("http://localhost:8080/")
    resp3 = urllib.request.urlopen(req3, timeout=10)
    html = resp3.read()
    print(f"Frontend: HTTP {resp3.status}, {len(html)} bytes")
    if b"<!DOCTYPE" in html or b"<!doctype" in html or b"<html" in html:
        print("Frontend serving HTML correctly!")
except Exception as e:
    print(f"Frontend error: {e}")
'''
    sftp = ssh.open_sftp()
    with sftp.open(f"{PROJECT_DIR}\\test_final.py", 'w') as f:
        f.write(test_code)
    sftp.close()

    # Run test
    print("\n--- Final test ---")
    ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python test_final.py", timeout=30)

    # Port check
    ssh_exec(ssh, "netstat -ano | findstr LISTENING | findstr \"8000 8080\"", timeout=10)

    print("\n" + "="*60)
    print("  DEPLOYMENT COMPLETE")
    print(f"  Frontend: http://{HOST}:8080")
    print(f"  Backend:  http://{HOST}:8000")
    print(f"  Login:    admin / admin123")
    print("="*60)

    ssh.close()

if __name__ == "__main__":
    main()
