"""Simple connectivity test"""
import urllib.request
import urllib.error

BASE = "http://localhost:8000"

# Test 1: Root
print("Test 1: GET /")
try:
    req = urllib.request.Request(BASE + "/")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"  OK: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# Test 2: Health
print("Test 2: GET /health")
try:
    req = urllib.request.Request(BASE + "/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"  OK: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# Test 3: Docs
print("Test 3: GET /docs")
try:
    req = urllib.request.Request(BASE + "/docs")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"  OK: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"  Error: {e}")

# Test 4: OpenAPI
print("Test 4: GET /openapi.json")
try:
    req = urllib.request.Request(BASE + "/openapi.json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        import json
        data = json.loads(resp.read().decode())
        print(f"  OK: {resp.status}, paths count: {len(data.get('paths', {}))}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"  Error: {e}")
