"""Run targeted test to identify crash point"""
import paramiko
import time

SERVER = "10.241.2.64"
USER = "zhouxuying"
PASS = "zhouxuying51"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASS, timeout=30)

# Write a safer test script
test_script = r'''
import urllib.request
import urllib.error
import json
import sys

BASE = "http://10.241.2.64:8000"
TOKEN = None
USER_ID = None
results = {"pass": 0, "fail": 0}

def api(method, path, data=None, timeout=10, need_auth=False):
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
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return 0, str(e)

def test(name, method, path, **kw):
    try:
        status, body = api(method, path, **kw)
        ok = 200 <= status < 300
        tag = "PASS" if ok else ("TIMEOUT" if status == 0 else "FAIL")
        if ok:
            results["pass"] += 1
        else:
            results["fail"] += 1
        print(f"[{tag}] {name} -> {status}", flush=True)
        if not ok and status != 0:
            print(f"  {body[:150]}", flush=True)
    except Exception as e:
        results["fail"] += 1
        print(f"[ERROR] {name} -> {e}", flush=True)

import base64

# Login
status, body = api("POST", "/api/v1/auth/login", {"username": "admin", "password": "admin123"}, timeout=30)
if status == 200:
    d = json.loads(body)
    tok = d.get("data", d).get("access_token")
    if tok:
        TOKEN = tok
        payload = tok.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        user_info = json.loads(base64.urlsafe_b64decode(payload))
        USER_ID = user_info.get("sub")
    print(f"[PASS] Login -> 200 (user_id={USER_ID})", flush=True)
    results["pass"] += 1
else:
    print(f"[FAIL] Login -> {status}", flush=True)
    results["fail"] += 1

tests = [
    # Blockchain
    ("区块链-存证列表", "GET", "/api/v1/blockchain/evidence"),
    ("区块链-智能合约列表", "GET", "/api/v1/blockchain/contracts/"),
    ("区块链-链状态", "GET", "/api/v1/blockchain/contracts/chain/status"),
    ("区块链-FISCO共识", "GET", "/api/v1/blockchain/contracts/fisco/consensus"),
    ("区块链-交易记录", "GET", "/api/v1/blockchain/contracts/transactions"),
    ("跨链-链列表", "GET", "/api/v1/blockchain/bridge/chains"),
    ("跨链-交易记录", "GET", "/api/v1/blockchain/bridge/transactions"),
    # FL
    ("FL模型列表", "GET", "/api/v1/compute/fl/models"),
    ("FATE任务", "GET", "/api/v1/compute/fl/fate/jobs"),
    ("FATE算法", "GET", "/api/v1/compute/fl/fate/algorithms"),
    ("FATE组件", "GET", "/api/v1/compute/fl/fate/components"),
    # Privacy
    ("MPC协议", "GET", "/api/v1/compute/mpc/protocols"),
    ("TEE实例", "GET", "/api/v1/compute/tee/instances"),
    ("HE方案", "GET", "/api/v1/compute/he/schemes"),
    ("HE密钥", "GET", "/api/v1/compute/he/keys"),
    ("DP配置", "GET", "/api/v1/compute/dp/configs"),
    # Data Center
    ("数据源", "GET", "/api/v1/data/sources"),
    ("数据资产", "GET", "/api/v1/data/assets"),
    ("数据目录", "GET", "/api/v1/data/catalog"),
    ("数据质量报告", "GET", "/api/v1/data/quality/reports"),
    ("数据质量统计", "GET", "/api/v1/data/quality/statistics"),
    ("数据市场资产", "GET", "/api/v1/data/market/assets"),
    ("数据市场分类", "GET", "/api/v1/data/market/categories"),
    ("数据市场统计", "GET", "/api/v1/data/market/stats"),
    # Connectors
    ("连接器列表", "GET", "/api/v1/connector-manage"),
    ("文件集", "GET", "/api/v1/connector-files/file-sets"),
    # Contracts
    ("合约列表", "GET", "/api/v1/contracts/"),
    # Organizations
    ("组织角色", "GET", "/api/v1/organizations/roles"),
    ("组织认证", "GET", "/api/v1/organizations/certifications"),
    # Workflow
    ("工作流列表", "GET", "/api/v1/workflows"),
    # Portal
    ("门户仪表盘", "GET", f"/api/v1/portal/dashboard?user_id={USER_ID}"),
    ("门户活动", "GET", "/api/v1/portal/activities"),
    ("门户通知", "GET", f"/api/v1/portal/notifications?user_id={USER_ID}"),
    # Monitor
    ("监控指标", "GET", "/api/v1/ops/monitoring/metrics"),
    ("监控健康", "GET", "/api/v1/ops/monitoring/health"),
    ("告警列表", "GET", "/api/v1/ops/alerts"),
    ("告警统计", "GET", "/api/v1/ops/alerts/statistics"),
    # Product Market
    ("产品市场搜索", "GET", "/api/v1/product-market/search"),
    ("产品订阅", "GET", "/api/v1/product-market/subscriptions"),
    # Compute
    ("计算任务", "GET", "/api/v1/compute/tasks"),
    ("计算代理历史", "GET", "/api/v1/compute/agents/history"),
    ("集群节点", "GET", "/api/v1/compute/cluster/nodes"),
    ("集群状态", "GET", "/api/v1/compute/cluster/status"),
    # SSO
    ("SSO提供商", "GET", "/api/v1/auth/sso/providers"),
]

for name, method, path in tests:
    test(name, method, path, need_auth=True)

print(f"\n{'='*60}", flush=True)
print(f"Results: PASS={results['pass']} FAIL={results['fail']}", flush=True)
print(f"{'='*60}", flush=True)
'''

# Write test script to server
sftp = ssh.open_sftp()
with sftp.open(r"D:\Andre\project\energy-trusted-data-space\test_v2.py", "w") as f:
    f.write(test_script)
sftp.close()

# Run it
cmd = r'cd /d D:\Andre\project\energy-trusted-data-space && D:\xujingyi\anaconda3\python.exe -u test_v2.py > test_output_v2.txt 2>&1'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
exit_code = stdout.channel.recv_exit_status()
time.sleep(3)

# Read output
sftp = ssh.open_sftp()
with sftp.open(r"D:\Andre\project\energy-trusted-data-space\test_output_v2.txt", "r") as f:
    raw = f.read()
    for enc in ["utf-8", "gbk", "cp936", "latin1"]:
        try:
            output = raw.decode(enc)
            break
        except:
            continue
    else:
        output = raw.decode("utf-8", errors="replace")
print(output)

with open("D:/Projects/energy-trusted-data-space/test_results_v2.txt", "w", encoding="utf-8") as f:
    f.write(output)

sftp.close()
ssh.close()
