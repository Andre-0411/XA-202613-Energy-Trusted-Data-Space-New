"""Directly call the 4 failing endpoints to see actual error messages."""
import requests
import json

BASE = "http://10.241.2.64:8000"

# Login first
login_resp = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "admin123"}, timeout=30)
token = login_resp.json().get("data", {}).get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}
print(f"Login: {login_resp.status_code}, token_len={len(token)}")

# 1. Settlement list (wrong URL)
print("\n=== 1. GET /api/v1/blockchain/settlement ===")
r = requests.get(f"{BASE}/api/v1/blockchain/settlement", headers=headers, timeout=30)
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:300]}")

# 1b. Correct URL
print("\n=== 1b. GET /api/v1/blockchain/settlement/list ===")
r = requests.get(f"{BASE}/api/v1/blockchain/settlement/list", headers=headers, timeout=30)
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:300]}")

# 2. Quality statistics
print("\n=== 2. GET /api/v1/data/quality/statistics ===")
r = requests.get(f"{BASE}/api/v1/data/quality/statistics", headers=headers, timeout=30)
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:500]}")

# 3. Monitor metrics
print("\n=== 3. GET /api/v1/ops/monitoring/metrics ===")
r = requests.get(f"{BASE}/api/v1/ops/monitoring/metrics", headers=headers, timeout=30)
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:500]}")

# 4. Alert statistics
print("\n=== 4. GET /api/v1/ops/alerts/statistics ===")
r = requests.get(f"{BASE}/api/v1/ops/alerts/statistics", headers=headers, timeout=30)
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:300]}")

# 4b. Alert list (to confirm routing works)
print("\n=== 4b. GET /api/v1/ops/alerts ===")
r = requests.get(f"{BASE}/api/v1/ops/alerts", headers=headers, timeout=30)
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:300]}")
