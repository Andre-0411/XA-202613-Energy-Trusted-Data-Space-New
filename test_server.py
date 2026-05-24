"""Test backend modules on server"""
import requests
import json
import time

BASE = "http://localhost:8000"
TOKEN = None

def login():
    global TOKEN
    try:
        r = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "admin", "password": "admin123"}, timeout=10)
        print(f"[LOGIN] Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if "data" in data and "access_token" in data["data"]:
                TOKEN = data["data"]["access_token"]
                print(f"[LOGIN] OK - Token obtained")
            elif "access_token" in data:
                TOKEN = data["access_token"]
                print(f"[LOGIN] OK - Token obtained")
            else:
                print(f"[LOGIN] Response: {json.dumps(data, ensure_ascii=False)[:300]}")
        else:
            print(f"[LOGIN] Response: {r.text[:300]}")
    except Exception as e:
        print(f"[LOGIN] Error: {e}")

def test_endpoint(name, method, path, **kwargs):
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{path}", headers=headers, timeout=10, **kwargs)
        elif method == "POST":
            r = requests.post(f"{BASE}{path}", headers=headers, timeout=10, **kwargs)
        else:
            r = requests.request(method, f"{BASE}{path}", headers=headers, timeout=10, **kwargs)
        status = "OK" if r.status_code < 400 else "FAIL"
        print(f"[{status}] {name} - {method} {path} -> {r.status_code}")
        if r.status_code >= 400:
            print(f"  Error: {r.text[:200]}")
    except Exception as e:
        print(f"[ERR] {name} - {method} {path} -> {e}")

print("=" * 60)
print("Backend Module Test - " + time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 60)

# 1. Auth
login()
print()

# 2. Blockchain
print("--- Blockchain ---")
test_endpoint("区块链查询", "GET", "/api/v1/blockchain/query/blocks")
test_endpoint("区块链交易", "GET", "/api/v1/blockchain/query/transactions")
test_endpoint("区块链存证", "GET", "/api/v1/blockchain/evidence/list")
test_endpoint("跨链桥-链列表", "GET", "/api/v1/blockchain/bridge/chains")
test_endpoint("跨链桥-交易", "GET", "/api/v1/blockchain/bridge/transactions")
test_endpoint("共识状态", "GET", "/api/v1/blockchain/consensus/status")
test_endpoint("智能合约列表", "GET", "/api/v1/blockchain/contracts")
test_endpoint("结算列表", "GET", "/api/v1/blockchain/settlement/list")
print()

# 3. Federated Learning
print("--- Federated Learning ---")
test_endpoint("FL模型列表", "GET", "/api/v1/compute/fl/models")
test_endpoint("FATE任务", "GET", "/api/v1/compute/fl/fate/jobs")
test_endpoint("FATE算法", "GET", "/api/v1/compute/fl/fate/algorithms")
test_endpoint("FATE组件", "GET", "/api/v1/compute/fl/fate/components")
print()

# 4. MPC / TEE / HE / DP
print("--- Privacy Computing ---")
test_endpoint("MPC协议", "GET", "/api/v1/compute/mpc/protocols")
test_endpoint("TEE实例", "GET", "/api/v1/compute/tee/instances")
test_endpoint("TEE运行时", "GET", "/api/v1/compute/tee/runtime-info")
test_endpoint("HE方案", "GET", "/api/v1/compute/he/schemes")
test_endpoint("HE密钥", "GET", "/api/v1/compute/he/keys")
test_endpoint("DP配置", "GET", "/api/v1/compute/dp/configs")
print()

# 5. Data Center
print("--- Data Center ---")
test_endpoint("数据源列表", "GET", "/api/v1/data/sources")
test_endpoint("数据资产", "GET", "/api/v1/data/assets")
test_endpoint("数据目录", "GET", "/api/v1/data/catalog")
test_endpoint("数据质量报告", "GET", "/api/v1/data/quality/reports")
test_endpoint("数据质量统计", "GET", "/api/v1/data/quality/statistics")
test_endpoint("数据市场资产", "GET", "/api/v1/data/market/assets")
test_endpoint("数据市场分类", "GET", "/api/v1/data/market/categories")
test_endpoint("数据市场统计", "GET", "/api/v1/data/market/stats")
print()

# 6. Connectors
print("--- Connectors ---")
test_endpoint("连接器列表", "GET", "/api/v1/connectors")
test_endpoint("连接器状态", "GET", "/api/v1/connectors/status/summary")
test_endpoint("文件集", "GET", "/api/v1/connectors/files/sets")
print()

# 7. Contracts
print("--- Contracts ---")
test_endpoint("合约列表", "GET", "/api/v1/contracts")
test_endpoint("合约统计", "GET", "/api/v1/contracts/statistics")
print()

# 8. Organizations
print("--- Organizations ---")
test_endpoint("组织角色", "GET", "/api/v1/organizations/roles")
test_endpoint("组织认证", "GET", "/api/v1/organizations/certifications")
test_endpoint("邀请码", "GET", "/api/v1/organizations/invite-codes")
print()

# 9. Workflow
print("--- Workflow ---")
test_endpoint("工作流列表", "GET", "/api/v1/workflows")
print()

# 10. Portal
print("--- Portal ---")
test_endpoint("门户仪表盘", "GET", "/api/v1/portal/dashboard")
test_endpoint("门户活动", "GET", "/api/v1/portal/activities")
test_endpoint("门户通知", "GET", "/api/v1/portal/notifications")
print()

# 11. Monitoring
print("--- Monitoring ---")
test_endpoint("监控状态", "GET", "/api/v1/monitor/status")
test_endpoint("监控告警", "GET", "/api/v1/monitor/alerts")
print()

# 12. Product Market
print("--- Product Market ---")
test_endpoint("产品市场搜索", "GET", "/api/v1/product-market/search")
test_endpoint("产品订阅", "GET", "/api/v1/product-market/subscriptions")
print()

# 13. Auth SSO
print("--- Auth SSO ---")
test_endpoint("SSO提供商", "GET", "/api/v1/auth/sso/providers")
test_endpoint("SSO会话", "GET", "/api/v1/auth/sso/sessions")
print()

# 14. Compute
print("--- Compute ---")
test_endpoint("计算任务", "GET", "/api/v1/compute/tasks")
test_endpoint("计算代理历史", "GET", "/api/v1/compute/agents/history")
test_endpoint("集群节点", "GET", "/api/v1/compute/cluster/nodes")
test_endpoint("集群状态", "GET", "/api/v1/compute/cluster/status")
print()

print("=" * 60)
print("Test Complete")
print("=" * 60)
