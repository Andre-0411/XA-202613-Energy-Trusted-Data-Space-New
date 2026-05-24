"""测试多个可能的端点路径"""
import urllib.request
import urllib.error
import json

HOST = "10.241.2.64"
BASE = f"http://{HOST}:8080"

# 先登录拿 token
def do_post(path, body):
    url = BASE + path
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type':'application/json'}, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return 0, str(e)

def do_get(path, token):
    url = BASE + path
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'}, method='GET')
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except:
            return e.code, e.read().decode()[:200]
    except Exception as e:
        return 0, str(e)

# 登录
code, data = do_post("/api/v1/auth/login", {"username":"admin","password":"admin123","auth_type":"password"})
print(f"登录: HTTP {code}")
if code != 200:
    print(f"  失败: {data}")
    exit(1)

token = data['data']['access_token']
print(f"  Token: {token[:40]}...\n")

# 测试各种端点
endpoints = [
    "/api/v1/health",
    "/api/v1/health/",
    "/api/health",
    "/health",
    "/api/v1/users/me",
    "/api/v1/users/me/",
    "/api/v1/auth/me",
    "/api/v1/auth/me/",
    "/api/v1/auth/current-user",
    "/api/v1/auth/profile",
    "/api/v1/dashboard/overview",
    "/api/v1/portal/dashboard",
    "/api/v1/system/info",
    "/api/v1/monitor/status",
]

print("测试端点:")
for ep in endpoints:
    code, body = do_get(ep, token)
    status = "✅" if code == 200 else "❌"
    detail = ""
    if code == 200 and isinstance(body, dict):
        if body.get('code') == 0:
            detail = f"OK - {str(body.get('data',''))[:60]}"
        else:
            detail = f"业务错误: {body.get('message','')[:60]}"
    elif isinstance(body, dict):
        detail = body.get('detail', body.get('message', str(body)[:60]))
    print(f"  {status} {ep}: HTTP {code} - {detail}")
