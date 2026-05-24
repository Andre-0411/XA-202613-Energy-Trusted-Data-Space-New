"""测试 AI Agent 管理页面相关 API"""
import urllib.request
import json

BASE = "http://10.241.2.64:8000"

# 登录
login_data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(f"{BASE}/api/v1/auth/login", data=login_data,
                             headers={"Content-Type": "application/json"}, method="POST")
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read())["data"]["access_token"]
print("LOGIN: OK")

headers = {"Authorization": f"Bearer {token}"}

# 测试各个 Agent 相关端点
endpoints = [
    ("GET", "/api/v1/agents/stats"),
    ("GET", "/api/v1/agents/config"),
    ("GET", "/api/v1/agents/knowledge-bases"),
    ("GET", "/api/v1/agents/models"),
    ("GET", "/api/v1/agents/conversations"),
    ("GET", "/api/v1/compute/agents"),
    ("GET", "/api/v1/compute/agents/history"),
]

for method, path in endpoints:
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        print(f"[PASS] {method} {path} -> {resp.status} code={data.get('code')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        print(f"[FAIL] {method} {path} -> {e.code} {body}")
    except Exception as e:
        print(f"[ERR]  {method} {path} -> {type(e).__name__}: {e}")
