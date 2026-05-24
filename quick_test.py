"""Quick test of backend endpoints"""
import urllib.request
import urllib.error
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "http://localhost:8000"

def api(method, path, data=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)

print("=" * 60)
print("Backend Module Test")
print("=" * 60)

# Login
status, body = api("POST", "/api/v1/auth/login", {"username": "admin", "password": "admin123"})
print(f"[LOGIN] Status={status}")
print(f"  Body: {json.dumps(body, ensure_ascii=False)[:300] if isinstance(body, dict) else str(body)[:300]}")

TOKEN = None
if status == 200 and isinstance(body, dict):
    d = body.get("data", body)
    TOKEN = d.get("access_token") if isinstance(d, dict) else None
    if TOKEN:
        print(f"  Token: {TOKEN[:30]}...")
    else:
        print(f"  Keys: {list(d.keys()) if isinstance(d, dict) else 'N/A'}")

print()
print("Done")
