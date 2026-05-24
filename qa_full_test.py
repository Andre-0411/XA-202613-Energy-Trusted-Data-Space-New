#!/usr/bin/env python3
"""能源可信数据空间项目全面 API QA 测试"""
import requests
import json
import sys

BASE = "http://10.241.2.64:8000"

def main():
    # Login first
    r = requests.post(f"{BASE}/api/v1/auth/login", json={"username":"admin","password":"admin123","auth_type":"password"})
    if r.status_code != 200:
        print("Login failed!")
        sys.exit(1)
    token = r.json()["data"]["access_token"]
    H = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

    # Comprehensive API test with correct paths from router.py
    tests = [
        # Auth
        ("GET", "/api/v1/auth/session", "认证-获取会话"),
        ("POST", "/api/v1/auth/refresh", "认证-刷新token", {"refresh_token": "invalid"}),

        # Data Resources
        ("GET", "/api/v1/data/sources", "数据资源-数据源列表"),
        ("GET", "/api/v1/data/assets", "数据资源-数据资产列表"),
        ("GET", "/api/v1/data/catalog", "数据资源-数据目录"),
        ("GET", "/api/v1/data/metadata", "数据资源-元数据"),
        ("GET", "/api/v1/data/tags", "数据资源-标签"),
        ("GET", "/api/v1/data/quality", "数据资源-数据质量"),
        ("GET", "/api/v1/data/market", "数据资源-服务市场"),
        ("GET", "/api/v1/data/applications", "数据资源-服务申请"),
        ("GET", "/api/v1/data/pipeline", "数据资源-数据流水线"),

        # Compute
        ("GET", "/api/v1/compute/tasks", "计算-任务列表"),
        ("GET", "/api/v1/compute/agents", "计算-计算代理"),
        ("GET", "/api/v1/compute/cluster", "计算-计算集群"),
        ("GET", "/api/v1/compute/dag", "计算-DAG编排"),
        ("GET", "/api/v1/compute/fl", "计算-联邦学习"),
        ("GET", "/api/v1/compute/mpc", "计算-安全多方计算"),
        ("GET", "/api/v1/compute/tee", "计算-TEE"),
        ("GET", "/api/v1/compute/he", "计算-同态加密"),
        ("GET", "/api/v1/compute/dp", "计算-差分隐私"),
        ("GET", "/api/v1/compute/sandbox", "计算-数据沙箱"),
        ("GET", "/api/v1/compute/results", "计算-计算结果"),
        ("GET", "/api/v1/compute/benchmarks", "计算-性能基准"),
        ("GET", "/api/v1/compute/quota", "计算-计算配额"),
        ("GET", "/api/v1/compute/enhanced", "计算-增强计算"),

        # Blockchain
        ("GET", "/api/v1/blockchain/nft", "区块链-NFT列表"),
        ("GET", "/api/v1/blockchain/evidence", "区块链-存证列表"),
        ("GET", "/api/v1/blockchain/contracts", "区块链-合约列表"),
        ("GET", "/api/v1/blockchain/settlement", "区块链-结算列表"),
        ("GET", "/api/v1/blockchain/settlement-enhanced", "区块链-增强结算"),
        ("GET", "/api/v1/blockchain/billing-rules", "区块链-计费规则"),
        ("GET", "/api/v1/blockchain/bridge", "区块链-跨链互操作"),

        # Ops
        ("GET", "/api/v1/ops/users", "运营-用户列表"),
        ("GET", "/api/v1/ops/organizations", "运营-组织列表"),
        ("GET", "/api/v1/ops/services", "运营-服务管理"),
        ("GET", "/api/v1/ops/billing", "运营-计费管理"),
        ("GET", "/api/v1/ops/monitoring", "运营-运营监控"),
        ("GET", "/api/v1/ops/monitoring-enhanced", "运营-监控增强"),
        ("GET", "/api/v1/ops/alerts", "运营-告警管理"),
        ("GET", "/api/v1/ops/sla", "运营-SLA管理"),
        ("GET", "/api/v1/ops/compliance", "运营-合规管理"),
        ("GET", "/api/v1/ops/kpi", "运营-KPI仪表盘"),
        ("GET", "/api/v1/ops/quotas", "运营-配额管理"),
        ("GET", "/api/v1/ops/gdpr", "运营-GDPR合规"),
        ("GET", "/api/v1/ops/health", "运营-健康检查"),
        ("GET", "/api/v1/ops/revenue", "运营-收益分配"),

        # Security
        ("GET", "/api/v1/security/did", "安全-DID身份"),
        ("GET", "/api/v1/security/vc", "安全-可验证凭证"),
        ("GET", "/api/v1/security/keys", "安全-密钥管理"),
        ("GET", "/api/v1/security/policies", "安全-安全策略"),
        ("GET", "/api/v1/security/threats", "安全-威胁检测"),
        ("GET", "/api/v1/security/gmssl", "安全-国密算法"),
        ("GET", "/api/v1/security/zkp", "安全-零知识证明"),
        ("GET", "/api/v1/security/audit", "安全-增强审计"),
        ("GET", "/api/v1/security/hsm", "安全-HSM模块"),
        ("GET", "/api/v1/security/levels", "安全-安全等级"),
        ("GET", "/api/v1/security/apt", "安全-APT检测"),
        ("GET", "/api/v1/security/bbs", "安全-BBS+签名"),
        ("GET", "/api/v1/security/abac", "安全-ABAC策略"),

        # System
        ("GET", "/api/v1/notifications", "系统-通知公告"),
        ("GET", "/api/v1/system/config", "系统-系统配置"),
        ("GET", "/api/v1/audit-logs", "系统-操作日志"),

        # Business modules
        ("GET", "/api/v1/organizations", "业务-机构管理"),
        ("GET", "/api/v1/connector-manage", "业务-连接器管理"),
        ("GET", "/api/v1/catalog-manage", "业务-数据目录管理"),
        ("GET", "/api/v1/data-subscriptions", "业务-数据订阅"),
        ("GET", "/api/v1/product-manage", "业务-数据产品管理"),
        ("GET", "/api/v1/product-market", "业务-产品市场"),
        ("GET", "/api/v1/demand-manage", "业务-需求管理"),
        ("GET", "/api/v1/contracts", "业务-合约管理"),
        ("GET", "/api/v1/workflows", "业务-审批工作流"),
        ("GET", "/api/v1/agents", "业务-Agent管理"),

        # Portal & LLM
        ("GET", "/api/v1/portal", "门户-统一门户"),
        ("GET", "/api/v1/llm", "LLM-大模型"),
    ]

    results = []
    for test in tests:
        method = test[0]
        path = test[1]
        name = test[2]
        body = test[3] if len(test) > 3 else None
        url = f"{BASE}{path}"

        try:
            if method == "GET":
                r = requests.get(url, headers=H, timeout=10)
            elif method == "POST":
                r = requests.post(url, headers=H, json=body or {}, timeout=10)

            code = r.status_code
            try:
                data = r.json()
                api_code = data.get("code", "N/A")
                msg = str(data.get("message", "N/A"))[:50]
                data_val = data.get("data")
                data_type = type(data_val).__name__
                if data_type == "list":
                    data_len = len(data_val)
                    data_info = f"list[{data_len}]"
                elif data_type == "dict":
                    keys = list(data_val.keys())[:5]
                    data_info = f"dict{keys}"
                elif data_val is None:
                    data_info = "null"
                else:
                    data_info = data_type
            except:
                api_code = "N/A"
                msg = r.text[:50]
                data_info = "parse_error"

            status = "OK" if code == 200 else f"FAIL({code})"
            if code == 200 and api_code != 0:
                status = f"WARN(api={api_code})"

            results.append((name, method, path, code, api_code, msg, data_info, status))

        except requests.exceptions.ConnectionError:
            results.append((name, method, path, "CONN_ERR", "-", "-", "-", "FAIL"))
        except requests.exceptions.Timeout:
            results.append((name, method, path, "TIMEOUT", "-", "-", "-", "FAIL"))
        except Exception as e:
            results.append((name, method, path, "EXC", "-", str(e)[:50], "-", "FAIL"))

    # Print table
    print("=" * 170)
    print("能源可信数据空间项目 API 端点 QA 测试报告")
    print("=" * 170)

    modules = {}
    for r in results:
        module = r[0].split("-")[0]
        if module not in modules:
            modules[module] = []
        modules[module].append(r)

    total = len(results)
    ok_count = sum(1 for r in results if r[7] == "OK")
    fail_count = sum(1 for r in results if r[7].startswith("FAIL"))
    warn_count = sum(1 for r in results if r[7].startswith("WARN"))

    print(f"\n总计: {total} | 通过: {ok_count} | 失败: {fail_count} | 警告: {warn_count} | 通过率: {ok_count/total*100:.1f}%\n")

    for module, items in modules.items():
        module_ok = sum(1 for i in items if i[7] == "OK")
        print(f"--- {module} ({module_ok}/{len(items)} 通过) ---")
        for name, method, path, code, api_code, msg, data_info, status in items:
            icon = "✅" if status == "OK" else ("⚠️" if status.startswith("WARN") else "❌")
            print(f"  {icon} {name}")
            print(f"     路径: {method} {path}  状态码: {code}  API代码: {api_code}")
            if status != "OK":
                print(f"     消息: {msg}  数据: {data_info}")
            elif data_info != "null":
                print(f"     数据: {data_info}")
        print()

    # Write report to file
    with open("D:/XA-202613-Energy-Trusted-Data-Space-New/qa_api_report.txt", "w", encoding="utf-8") as f:
        f.write("能源可信数据空间项目 API 端点 QA 测试报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"总计: {total} | 通过: {ok_count} | 失败: {fail_count} | 警告: {warn_count}\n")
        f.write(f"通过率: {ok_count/total*100:.1f}%\n\n")

        for module, items in modules.items():
            module_ok = sum(1 for i in items if i[7] == "OK")
            f.write(f"--- {module} ({module_ok}/{len(items)} 通过) ---\n")
            for name, method, path, code, api_code, msg, data_info, status in items:
                icon = "✅" if status == "OK" else ("⚠️" if status.startswith("WARN") else "❌")
                f.write(f"  {icon} {name}\n")
                f.write(f"     路径: {method} {path}  状态码: {code}  API代码: {api_code}\n")
                if status != "OK":
                    f.write(f"     消息: {msg}  数据: {data_info}\n")
                elif data_info != "null":
                    f.write(f"     数据: {data_info}\n")
            f.write("\n")

    print(f"\n报告已保存至 qa_api_report.txt")

if __name__ == "__main__":
    main()
