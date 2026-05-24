"""完整登录流程测试：模拟前端行为"""
import urllib.request
import urllib.error
import json
import http.cookiejar

HOST = "10.241.2.64"
BASE = f"http://{HOST}:8080"

# 自动管理 cookies
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def req(method, path, body=None, token=None):
    url = BASE + path
    hd = {'Content-Type': 'application/json'} if body else {}
    if token:
        hd['Authorization'] = f'Bearer {token}'
    # 模拟前端：对非 GET 请求添加 CSRF token
    if method not in ('GET', 'HEAD', 'OPTIONS'):
        for c in jar:
            if c.name == 'csrftoken':
                hd['X-CSRFToken'] = c.value
                break
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        resp = opener.open(r, timeout=15)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except:
            return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)

print("=" * 60)
print("🧪 完整登录流程测试")
print("=" * 60)

# Step 1: 登录
print("\n[1] POST /api/v1/auth/login")
code, data = req("POST", "/api/v1/auth/login", {
    "username": "admin", "password": "admin123", "auth_type": "password"
})
print(f"    HTTP {code}")
if code == 200 and data.get('code') == 0:
    token = data['data']['access_token']
    refresh = data['data'].get('refresh_token', '')
    print(f"    ✅ 登录成功")
    print(f"    access_token: {token[:50]}...")
    print(f"    refresh_token: {refresh[:30]}..." if refresh else "    (无 refresh_token)")
else:
    print(f"    ❌ 失败: {data}")
    exit(1)

# Step 2: 获取会话信息
print("\n[2] GET /api/v1/auth/session")
code, data = req("GET", "/api/v1/auth/session", token=token)
print(f"    HTTP {code}")
if code == 200 and data.get('code') == 0:
    s = data['data']
    print(f"    ✅ 会话信息: {s}")
else:
    print(f"    ❌ 失败: {data}")

# Step 3: 测试 Portal Dashboard
print("\n[3] GET /api/v1/portal/dashboard")
code, data = req("GET", "/api/v1/portal/dashboard", token=token)
print(f"    HTTP {code}")
if code == 200:
    print(f"    ✅ Dashboard 数据获取成功")
    if isinstance(data, dict) and data.get('data'):
        print(f"    数据 keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data']).__name__}")
else:
    print(f"    ❌ 失败: {str(data)[:200]}")

# Step 4: 测试用户列表 (需要 admin 权限)
print("\n[4] GET /api/v1/ops/users")
code, data = req("GET", "/api/v1/ops/users", token=token)
print(f"    HTTP {code}")
if code == 200:
    print(f"    ✅ 用户列表获取成功")
else:
    print(f"    ❌ 失败: {str(data)[:200]}")

# Step 5: 测试通知列表
print("\n[5] GET /api/v1/notifications")
code, data = req("GET", "/api/v1/notifications", token=token)
print(f"    HTTP {code}")
if code == 200:
    print(f"    ✅ 通知列表获取成功")
else:
    print(f"    ❌ 失败: {str(data)[:200]}")

# Cookies 状态
print("\n[Cookies]")
for c in jar:
    print(f"    {c.name} = {c.value[:40]}...")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
