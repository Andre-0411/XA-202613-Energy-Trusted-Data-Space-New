"""最终端点测试"""
import paramiko

HOST = "10.241.2.64"
USERNAME = "zhouxuying"
PASSWORD = "zhouxuying51"
PROJECT = r"D:\Andre\project\energy-trusted-data-space"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USERNAME, password=PASSWORD, timeout=15)

def upload_text(ssh, path, content):
    sftp = ssh.open_sftp()
    with sftp.open(path, 'w') as f:
        f.write(content)
    sftp.close()

test_py = '''import urllib.request, urllib.error, json

BASE = "http://127.0.0.1:8000"

def test(method, path, body=None, token=None):
    url = BASE + path
    hd = {"Content-Type": "application/json"} if body else {}
    if token: hd["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        return resp.status, resp.read().decode()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)[:200]

print("=" * 50)
print("Endpoint Test")
print("=" * 50)

# Login
code, body = test("POST", "/api/v1/auth/login", {"username":"admin","password":"admin123","auth_type":"password"})
print(f"\\nLogin: HTTP {code}")
if code == 200:
    data = json.loads(body)
    if data.get("code") == 0:
        token = data["data"]["access_token"]
        print(f"  OK - token: {token[:40]}...")
        
        # Session
        print(f"\\nSession:")
        code, body = test("GET", "/api/v1/auth/session", token=token)
        print(f"  HTTP {code}")
        print(f"  Body: {body[:200]}")
        
        # Users
        print(f"\\nOps Users:")
        code, body = test("GET", "/api/v1/ops/users", token=token)
        print(f"  HTTP {code}")
        print(f"  Body: {body[:200]}")
        
        # Notifications
        print(f"\\nNotifications:")
        code, body = test("GET", "/api/v1/notifications", token=token)
        print(f"  HTTP {code}")
        print(f"  Body: {body[:200]}")
    else:
        print(f"  Login business error: {data.get('message')}")
else:
    print(f"  Login failed: {body[:200]}")
'''

upload_text(ssh, f"{PROJECT}\\test_ep.py", test_py)

stdin, stdout, stderr = ssh.exec_command(f'python "{PROJECT}\\test_ep.py"', timeout=30)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(out)
if err:
    print(f"\nSTDERR:\n{err}")

ssh.close()
