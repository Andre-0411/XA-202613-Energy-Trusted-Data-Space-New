"""Full module test with corrected routes"""
import urllib.request
import urllib.error
import json
import time

BASE = "http://10.241.2.64:8000"
TOKEN = None
USER_ID = None
results = {"pass": 0, "fail": 0, "skip": 0, "details": []}

def api(method, path, data=None, timeout=15, need_auth=False):
    global TOKEN
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if need_auth and TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]
    except Exception as e:
        return 0, str(e)

def test(name, method, path, **kw):
    status, body = api(method, path, **kw)
    ok = 200 <= status < 300
    if ok:
        results["pass"] += 1
        tag = "PASS"
    elif status == 0:
        results["fail"] += 1
        tag = "TIMEOUT"
    else:
        results["fail"] += 1
        tag = "FAIL"
    line = f"[{tag}] {name} -> {status}"
    results["details"].append(line)
    print(line)
    if not ok and status != 0:
        print(f"  {body[:200]}")
    return status, body

print("=" * 60)
print("Full Backend Module Test (Fixed Routes)")
print("=" * 60)

# 1. Login
print("\n--- Auth ---")
status, body = api("POST", "/api/v1/auth/login", {"username": "admin", "password": "admin123"}, timeout=30)
print(f"[LOGIN] Status={status}")
if status == 200:
    try:
        d = json.loads(body)
        tok = d.get("data", d).get("access_token") if isinstance(d.get("data", d), dict) else None
        if tok:
            TOKEN = tok
            print(f"  Token OK ({len(tok)} chars)")
        else:
            print(f"  No token in response: {body[:200]}")
    except:
        print(f"  Parse error: {body[:200]}")
else:
    print(f"  Login failed: {body[:300]}")
results["pass" if status == 200 else "fail"] += 1

# Get user_id from token for portal endpoints
if TOKEN:
    try:
        # Decode JWT payload (middle part)
        import base64
        payload = TOKEN.split(".")[1]
        # Add padding
        payload += "=" * (4 - len(payload) % 4)
        user_info = json.loads(base64.urlsafe_b64decode(payload))
        USER_ID = user_info.get("sub") or user_info.get("user_id")
        print(f"  User ID from token: {USER_ID}")
    except Exception as e:
        print(f"  Could not decode user_id: {e}")

# 2. Blockchain
print("\n--- Blockchain ---")
test("区块链-存证列表", "GET", "/api/v1/blockchain/evidence", need_auth=True)
test("区块链-智能合约列表", "GET", "/api/v1/blockchain/contracts/", need_auth=True)
test("区块链-链状态", "GET", "/api/v1/blockchain/contracts/chain/status", need_auth=True)
test("区块链-FISCO共识", "GET", "/api/v1/blockchain/contracts/fisco/consensus", need_auth=True)
test("区块链-交易记录", "GET", "/api/v1/blockchain/contracts/transactions", need_auth=True)
test("跨链-链列表", "GET", "/api/v1/blockchain/bridge/chains", need_auth=True)
test("跨链-交易记录", "GET", "/api/v1/blockchain/bridge/transactions", need_auth=True)
test("结算列表", "GET", "/api/v1/blockchain/settlement/list", need_auth=True)

# 3. Federated Learning
print("\n--- Federated Learning ---")
test("FL模型列表", "GET", "/api/v1/compute/fl/models", need_auth=True)
test("FATE任务", "GET", "/api/v1/compute/fl/fate/jobs", need_auth=True)
test("FATE算法", "GET", "/api/v1/compute/fl/fate/algorithms", need_auth=True)
test("FATE组件", "GET", "/api/v1/compute/fl/fate/components", need_auth=True)

# 4. Privacy Computing
print("\n--- Privacy Computing ---")
test("MPC协议", "GET", "/api/v1/compute/mpc/protocols", need_auth=True)
test("TEE实例", "GET", "/api/v1/compute/tee/instances", need_auth=True)
test("HE方案", "GET", "/api/v1/compute/he/schemes", need_auth=True)
test("HE密钥", "GET", "/api/v1/compute/he/keys", need_auth=True)
test("DP配置", "GET", "/api/v1/compute/dp/configs", need_auth=True)

# 5. Data Center
print("\n--- Data Center ---")
test("数据源", "GET", "/api/v1/data/sources", need_auth=True)
test("数据资产", "GET", "/api/v1/data/assets", need_auth=True)
test("数据目录", "GET", "/api/v1/data/catalog", need_auth=True)
test("数据质量报告", "GET", "/api/v1/data/quality/reports", need_auth=True)
test("数据质量统计", "GET", "/api/v1/data/quality/statistics", need_auth=True)
test("数据市场资产", "GET", "/api/v1/data/market/assets", need_auth=True)
test("数据市场分类", "GET", "/api/v1/data/market/categories", need_auth=True)
test("数据市场统计", "GET", "/api/v1/data/market/stats", need_auth=True)

# 6. Connectors (fixed paths)
print("\n--- Connectors ---")
test("连接器列表", "GET", "/api/v1/connector-manage", need_auth=True)
test("文件集", "GET", "/api/v1/connector-files/file-sets", need_auth=True)

# 7. Contracts (removed /statistics - no such endpoint)
print("\n--- Contracts ---")
test("合约列表", "GET", "/api/v1/contracts/", need_auth=True)

# 8. Organizations
print("\n--- Organizations ---")
test("组织角色", "GET", "/api/v1/organizations/roles", need_auth=True)
test("组织认证", "GET", "/api/v1/organizations/certifications", need_auth=True)

# 9. Workflow
print("\n--- Workflow ---")
test("工作流列表", "GET", "/api/v1/workflows", need_auth=True)

# 10. Portal (fixed: add user_id param)
print("\n--- Portal ---")
portal_uid = f"?user_id={USER_ID}" if USER_ID else ""
test("门户仪表盘", "GET", f"/api/v1/portal/dashboard{portal_uid}", need_auth=True)
test("门户活动", "GET", "/api/v1/portal/activities", need_auth=True)
test("门户通知", "GET", f"/api/v1/portal/notifications{portal_uid}", need_auth=True)

# 11. Monitor (fixed paths)
print("\n--- Monitor ---")
test("监控指标", "GET", "/api/v1/ops/monitoring/metrics", need_auth=True)
test("监控健康", "GET", "/api/v1/ops/monitoring/health", need_auth=True)
test("告警列表", "GET", "/api/v1/ops/alerts", need_auth=True)
test("告警统计", "GET", "/api/v1/ops/alerts/statistics", need_auth=True)

# 12. Product Market
print("\n--- Product Market ---")
test("产品市场搜索", "GET", "/api/v1/product-market/search", need_auth=True)
test("产品订阅", "GET", "/api/v1/product-market/subscriptions", need_auth=True)

# 13. Compute Agent / Cluster
print("\n--- Compute ---")
test("计算任务", "GET", "/api/v1/compute/tasks", need_auth=True)
test("计算代理历史", "GET", "/api/v1/compute/agents/history", need_auth=True)
test("集群节点", "GET", "/api/v1/compute/cluster/nodes", need_auth=True)
test("集群状态", "GET", "/api/v1/compute/cluster/status", need_auth=True)

# 14. SSO
print("\n--- SSO ---")
test("SSO提供商", "GET", "/api/v1/auth/sso/providers", need_auth=True)

print("\n" + "=" * 60)
print(f"Results: PASS={results['pass']} FAIL={results['fail']}")
print("=" * 60)
