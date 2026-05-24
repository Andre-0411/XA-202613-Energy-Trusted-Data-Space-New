"""模拟浏览器行为测试 CSRF"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.241.2.64', username='zhouxuying', password='zhouxuying51')

script = r'''
import urllib.request, urllib.error, json, http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Step 1: GET index.html to get csrf cookie
try:
    resp = opener.open("http://127.0.0.1:8080/", timeout=10)
    print("GET / status:", resp.status)
    print("Cookies after GET:", [c.name + "=" + c.value[:20] for c in cj])
except Exception as e:
    print("GET / error:", e)

# Step 2: POST login with cookies (browser sends cookies automatically)
body = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request("http://127.0.0.1:8080/api/v1/auth/login", data=body, method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("Origin", "http://10.241.2.64:8080")
req.add_header("Referer", "http://10.241.2.64:8080/login")
# NO X-CSRFToken header - simulating browser that doesn't set it
try:
    resp = opener.open(req, timeout=10)
    print("POST login status:", resp.status)
    print("POST login body:", resp.read().decode()[:200])
except urllib.error.HTTPError as e:
    print("POST login HTTPError:", e.code)
    body_text = e.read().decode()[:500]
    print("POST login body:", body_text)
except Exception as e:
    print("POST login error:", e)
'''

# Write script to server and execute
sftp = ssh.open_sftp()
with sftp.open('D:/Andre/project/energy-trusted-data-space/test_csrf_tmp.py', 'w') as f:
    f.write(script)

stdin, stdout, stderr = ssh.exec_command(
    r'cd /d D:\Andre\project\energy-trusted-data-space && python test_csrf_tmp.py',
    timeout=30
)
out = stdout.read().decode('gbk', errors='replace')
err = stderr.read().decode('gbk', errors='replace')
print("OUTPUT:", out)
if err:
    print("STDERR:", err[:500])

ssh.close()
