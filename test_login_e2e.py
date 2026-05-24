"""端到端登录测试：验证 CSRF 修复后的完整登录流程"""
import urllib.request
import urllib.error
import json
import http.cookiejar

HOST = "10.241.2.64"
BASE = f"http://{HOST}:8080"

# 创建 cookie jar 来自动管理 cookies（包括 csrftoken）
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def test_endpoint(method, path, body=None, headers=None):
    url = BASE + path
    hd = headers or {}
    if body:
        hd['Content-Type'] = 'application/json'
        data = json.dumps(body).encode()
    else:
        data = None
    req = urllib.request.Request(url, data=data, headers=hd, method=method)
    try:
        resp = opener.open(req, timeout=15)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)

print("=" * 60)
print("🧪 端到端登录测试")
print("=" * 60)

# 1. Health 检查
print("\n[1] Health 检查...")
code, body = test_endpoint("GET", "/api/v1/health")
print(f"    HTTP {code}")

# 2. 登录（CSRF 跳过）
print("\n[2] 登录 POST /api/v1/auth/login...")
code, body = test_endpoint("POST", "/api/v1/auth/login", {
    "username": "admin",
    "password": "admin123",
    "auth_type": "password"
})
print(f"    HTTP {code}")
if code == 200:
    try:
        data = json.loads(body)
        if data.get('code') == 0:
            token = data.get('data', {}).get('access_token', '')
            print(f"    ✅ 登录成功！Token: {token[:30]}...")
        else:
            print(f"    ❌ 业务错误: {data.get('message', 'unknown')}")
    except:
        print(f"    响应: {body[:200]}")
else:
    print(f"    ❌ 登录失败: {body[:200]}")

# 3. 查看获取到的 cookies
print("\n[3] Cookies:")
for c in jar:
    print(f"    {c.name} = {c.value[:30] if len(c.value) > 30 else c.value}")

# 4. 带 token 访问需要认证的端点
print("\n[4] 测试认证端点 GET /api/v1/users/me...")
code, body = test_endpoint("GET", "/api/v1/users/me", headers={
    'Authorization': f'Bearer {token}' if 'token' in dir() else ''
})
print(f"    HTTP {code}")
if code == 200:
    try:
        data = json.loads(body)
        if data.get('code') == 0:
            user = data.get('data', {})
            print(f"    ✅ 用户信息: {user.get('username', 'N/A')} ({user.get('role', 'N/A')})")
        else:
            print(f"    ❌ {data.get('message', 'unknown')}")
    except:
        print(f"    响应: {body[:200]}")
else:
    print(f"    ❌ 失败: {body[:200]}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
