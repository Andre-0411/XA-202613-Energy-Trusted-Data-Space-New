"""快速测试登录"""
import paramiko
import json

HOST = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"
PROJECT_DIR = r"D:\Andre\project\energy-trusted-data-space"

def ssh_exec(ssh, cmd, timeout=30):
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

    # Write a small test script on the server
    test_script = '''
import urllib.request
import json

data = json.dumps({"username": "admin", "password": "admin123", "auth_type": "password"}).encode("utf-8")

# Test backend direct
try:
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/login",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=10)
    print(f"Backend: HTTP {resp.status}")
    body = resp.read().decode("utf-8")
    result = json.loads(body)
    if result.get("code") == 0:
        print(f"LOGIN SUCCESS! Token type: {result['data'].get('token_type', 'N/A')}")
        token = result['data'].get('access_token', '')
        if token:
            print(f"Access token (first 50 chars): {token[:50]}...")
    else:
        print(f"Login failed: {result.get('message')}")
except Exception as e:
    print(f"Backend error: {e}")

# Test proxy
try:
    req2 = urllib.request.Request(
        "http://localhost:8080/api/v1/auth/login",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    resp2 = urllib.request.urlopen(req2, timeout=10)
    print(f"Proxy: HTTP {resp2.status}")
    body2 = resp2.read().decode("utf-8")
    result2 = json.loads(body2)
    if result2.get("code") == 0:
        print(f"PROXY LOGIN SUCCESS!")
    else:
        print(f"Proxy login failed: {result2.get('message')}")
except Exception as e:
    print(f"Proxy error: {e}")

# Test frontend page
try:
    req3 = urllib.request.Request("http://localhost:8080/")
    resp3 = urllib.request.urlopen(req3, timeout=10)
    body3 = resp3.read()
    print(f"Frontend: HTTP {resp3.status}, size={len(body3)} bytes")
    if b"<html" in body3.lower() or b"<!doctype" in body3.lower():
        print("Frontend HTML page loaded successfully!")
except Exception as e:
    print(f"Frontend error: {e}")
'''

    sftp = ssh.open_sftp()
    with sftp.open(f"{PROJECT_DIR}\\test_login.py", 'w') as f:
        f.write(test_script)
    sftp.close()
    print("test_login.py uploaded")

    ssh_exec(ssh, f"cd /d {PROJECT_DIR} && python test_login.py", timeout=30)

    ssh.close()

if __name__ == "__main__":
    main()
