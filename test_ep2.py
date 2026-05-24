"""最终端点测试 - 完整读取"""
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

test_py = r'''import urllib.request, urllib.error, json

BASE = "http://127.0.0.1:8000"

def test(method, path, body=None, token=None):
    url = BASE + path
    hd = {"Content-Type": "application/json"} if body else {}
    if token: hd["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=15)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except:
            return e.code, {"raw": e.read().decode()[:500]}
    except Exception as e:
        return 0, {"error": str(e)}

print("=" * 50)
print("Endpoint Test")
print("=" * 50)

# Login
code, data = test("POST", "/api/v1/auth/login", {"username":"admin","password":"admin123","auth_type":"password"})
print(f"\nLogin: HTTP {code}")
if code == 200 and data.get("code") == 0:
    token = data["data"]["access_token"]
    print(f"  OK")
    
    # Session
    print(f"\nSession GET /api/v1/auth/session:")
    code, data = test("GET", "/api/v1/auth/session", token=token)
    print(f"  HTTP {code}")
    print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    
    # Users
    print(f"\nUsers GET /api/v1/ops/users:")
    code, data = test("GET", "/api/v1/ops/users", token=token)
    print(f"  HTTP {code}")
    print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    
    # Notifications
    print(f"\nNotifications GET /api/v1/notifications:")
    code, data = test("GET", "/api/v1/notifications", token=token)
    print(f"  HTTP {code}")
    print(f"  {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
else:
    print(f"  FAIL: {data}")
'''

upload_text(ssh, f"{PROJECT}\\test_ep2.py", test_py)

stdin, stdout, stderr = ssh.exec_command(f'python "{PROJECT}\\test_ep2.py"', timeout=60)
out = stdout.read().decode('gbk', errors='replace').strip()
err = stderr.read().decode('gbk', errors='replace').strip()
print(out)
if err:
    print(f"\nSTDERR:\n{err}")

ssh.close()
