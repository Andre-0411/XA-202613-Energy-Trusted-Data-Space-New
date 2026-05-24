#!/usr/bin/env python3
"""
逐模块功能测试脚本（基于实际路由）
重点测试：区块链、可信数据空间、联邦学习
"""
import requests
import json
import sys
import urllib3
urllib3.disable_warnings()

BASE_URL = "http://10.241.2.64:8000"
FRONTEND_URL = "http://10.241.2.64:8080"
TIMEOUT = 30

TOKEN = None
RESULTS = []


def login():
    """登录获取 token"""
    global TOKEN
    print("=" * 60)
    print("登录测试")
    print("=" * 60)

    try:
        resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        }, timeout=TIMEOUT)
        print(f"  POST /api/v1/auth/login → HTTP {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 0:
                TOKEN = data.get("data", {}).get("access_token")
                print(f"  ✓ 登录成功")
                RESULTS.append(("登录", "PASS", ""))
                return True
            else:
                print(f"  ✗ 登录失败: {data.get('message')}")
                RESULTS.append(("登录", "FAIL", data.get("message", "")[:50]))
        else:
            print(f"  ✗ HTTP {resp.status_code}: {resp.text[:200]}")
            RESULTS.append(("登录", "FAIL", f"HTTP {resp.status_code}"))
    except Exception as e:
        print(f"  ✗ 登录异常: {e}")
        RESULTS.append(("登录", "FAIL", str(e)[:50]))

    return False


def hdrs():
    """请求头"""
    h = {"Content-Type": "application/json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def test_get(name, path):
    """测试 GET 端点"""
    try:
        resp = requests.get(f"{BASE_URL}/api/v1{path}", headers=hdrs(), timeout=TIMEOUT)
        status = resp.status_code
        if 200 <= status < 300:
            try:
                body = resp.json()
                code = body.get("code")
                if code == 0:
                    data = body.get("data")
                    if isinstance(data, list):
                        print(f"  ✓ {name}: {status} code=0 ({len(data)} 条)")
                    elif isinstance(data, dict):
                        keys = list(data.keys())[:5]
                        print(f"  ✓ {name}: {status} code=0 keys={keys}")
                    elif data is None:
                        print(f"  ✓ {name}: {status} code=0 data=null")
                    else:
                        print(f"  ✓ {name}: {status} code=0")
                    RESULTS.append((name, "PASS", ""))
                    return data
                else:
                    msg = body.get("message", "")[:60]
                    print(f"  ⚠ {name}: {status} code={code} msg={msg}")
                    RESULTS.append((name, "WARN", f"code={code} {msg}"))
                    return None
            except Exception:
                print(f"  ✓ {name}: {status} (非JSON)")
                RESULTS.append((name, "PASS", "非JSON"))
                return None
        elif status == 404:
            print(f"  ✗ {name}: 404 未找到")
            RESULTS.append((name, "FAIL", "404"))
            return None
        elif status == 401:
            print(f"  ✗ {name}: 401 未授权")
            RESULTS.append((name, "FAIL", "401 未授权"))
            return None
        elif status == 403:
            print(f"  ✗ {name}: 403 禁止访问")
            RESULTS.append((name, "FAIL", "403 禁止"))
            return None
        elif status == 422:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            msg = str(body.get("detail", resp.text[:100]))[:60]
            print(f"  ⚠ {name}: 422 参数错误 - {msg}")
            RESULTS.append((name, "WARN", f"422 {msg}"))
            return None
        else:
            msg = resp.text[:80]
            print(f"  ✗ {name}: HTTP {status} - {msg}")
            RESULTS.append((name, "FAIL", f"HTTP {status}"))
            return None
    except requests.exceptions.ConnectionError:
        print(f"  ✗ {name}: 连接失败")
        RESULTS.append((name, "FAIL", "连接失败"))
        return None
    except requests.exceptions.Timeout:
        print(f"  ✗ {name}: 超时")
        RESULTS.append((name, "FAIL", "超时"))
        return None
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        RESULTS.append((name, "FAIL", str(e)[:50]))
        return None


def section(title):
    """打印分节标题"""
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


# ============================================================
# 模块测试
# ============================================================

def test_auth():
    section("模块 1: 认证管理")
    test_get("当前用户", "/auth/session")
    test_get("SSO提供商", "/auth/sso/providers")
    test_get("SSO会话", "/auth/sso/sessions")


def test_portal():
    section("模块 2: 统一门户")
    test_get("门户概览", "/portal/overview")
    test_get("门户仪表盘", "/portal/dashboard")
    test_get("门户通知", "/portal/notifications")
    test_get("门户活动", "/portal/activities")


def test_data_center():
    section("模块 3: 数据中心")
    test_get("数据源列表", "/data/sources")
    test_get("数据资产列表", "/data/assets")
    test_get("数据目录", "/data/catalog")
    test_get("元数据", "/data/metadata")
    test_get("标签列表", "/data/tags")
    test_get("数据质量报告", "/data/quality/reports")
    test_get("数据质量统计", "/data/quality/statistics")
    test_get("数据市场资产", "/data/market/assets")
    test_get("数据市场分类", "/data/market/categories")
    test_get("数据市场统计", "/data/market/stats")
    test_get("服务申请", "/data/applications")


def test_compute():
    section("模块 4: 计算中心")
    test_get("计算任务", "/compute/tasks")
    test_get("DAG编排", "/compute/dag")
    test_get("联邦学习模型", "/compute/fl/models")
    test_get("FATE任务列表", "/compute/fl/fate/jobs")
    test_get("MPC协议", "/compute/mpc/protocols")
    test_get("TEE实例", "/compute/tee/instances")
    test_get("同态加密方案", "/compute/he/schemes")
    test_get("同态密钥", "/compute/he/keys")
    test_get("差分隐私配置", "/compute/dp/configs")
    test_get("数据沙箱", "/compute/sandbox")
    test_get("Agent历史", "/compute/agents/history")
    test_get("计算集群节点", "/compute/cluster/nodes")
    test_get("集群状态", "/compute/cluster/status")
    test_get("性能基准", "/compute/benchmarks")


def test_blockchain():
    """区块链 - 重点"""
    section("模块 5: 区块链（重点）")
    test_get("NFT确权", "/blockchain/nft")
    test_get("NFT列表", "/blockchain/nft/list")
    test_get("存证记录", "/blockchain/evidence")
    test_get("存证列表", "/blockchain/evidence/list")
    test_get("智能合约", "/blockchain/contracts")
    test_get("合约列表", "/blockchain/contracts/list")
    test_get("结算列表", "/blockchain/settlement/list")
    test_get("跨链链列表", "/blockchain/bridge/chains")
    test_get("跨链交易", "/blockchain/bridge/transactions")


def test_trusted_sharing():
    """可信共享 - 重点"""
    section("模块 6: 可信共享中心（可信数据空间）")
    test_get("机构角色", "/organizations/roles")
    test_get("机构认证", "/organizations/certifications")
    test_get("连接器管理", "/connector-manage")
    test_get("数据目录管理", "/catalog-manage")
    test_get("数据订阅", "/data-subscriptions")
    test_get("数据产品管理", "/product-manage")
    test_get("产品上架", "/product-publish")
    test_get("产品市场搜索", "/product-market/search")
    test_get("产品订阅列表", "/product-market/subscriptions")
    test_get("需求管理", "/demand-manage")
    test_get("合约管理", "/contracts")
    test_get("连接器文件库", "/connector-files")
    test_get("审批工作流", "/workflows")


def test_federated_learning():
    """联邦学习 - 重点"""
    section("模块 7: 联邦学习（重点）")
    test_get("联邦学习模型", "/compute/fl/models")
    test_get("FATE任务列表", "/compute/fl/fate/jobs")
    test_get("FATE算法列表", "/compute/fl/fate/algorithms")
    test_get("FATE组件列表", "/compute/fl/fate/components")
    test_get("FATE连接状态", "/compute/fl/fate/connection")


def test_security():
    section("模块 8: 安全中心")
    test_get("ABAC策略", "/security/abac")
    test_get("安全策略", "/security/policies")
    test_get("DID身份", "/security/did")
    test_get("可验证凭证", "/security/vc")
    test_get("密钥管理", "/security/keys")
    test_get("威胁检测", "/security/threats")
    test_get("国密算法", "/security/gmssl")
    test_get("零知识证明", "/security/zkp")
    test_get("HSM模块", "/security/hsm")
    test_get("安全等级", "/security/levels")
    test_get("APT检测", "/security/apt")
    test_get("BBS+签名", "/security/bbs")
    test_get("增强审计", "/security/audit")


def test_ops():
    section("模块 9: 运营分析中心")
    test_get("用户管理", "/ops/users")
    test_get("组织管理", "/ops/organizations")
    test_get("服务管理", "/ops/services")
    test_get("计费管理", "/ops/billing")
    test_get("运营监控", "/ops/monitoring")
    test_get("告警管理", "/ops/alerts")
    test_get("SLA管理", "/ops/sla")
    test_get("合规管理", "/ops/compliance")
    test_get("KPI仪表盘", "/ops/kpi")
    test_get("配额管理", "/ops/quotas")
    test_get("GDPR合规", "/ops/gdpr")
    test_get("健康检查", "/ops/health")


def test_monitoring():
    section("模块 10: 监管中心")
    test_get("审计日志", "/audit-logs")
    test_get("系统配置", "/system/config")


def test_notification():
    section("模块 11: 通知中心")
    test_get("通知列表", "/notifications")
    test_get("未读通知", "/notifications/unread")


def test_agents():
    section("模块 12: AI Agent")
    test_get("Agent列表", "/agents")
    test_get("LLM状态", "/llm/models")


def test_frontend_pages():
    """前端页面可访问性"""
    section("前端页面可访问性")
    pages = [
        "/",
        "/login",
        "/dashboard",
        "/data-center/sources",
        "/data-center/assets",
        "/data-center/catalog",
        "/compute/tasks",
        "/compute/fl",
        "/trusted-sharing/connectors",
        "/trusted-sharing/market",
        "/blockchain/overview",
        "/blockchain/evidence",
        "/blockchain/contracts",
        "/security/policies",
        "/security/did",
        "/ops/kpi",
        "/ops/users",
        "/supervision/audit",
        "/notifications",
    ]

    for page in pages:
        try:
            resp = requests.get(f"{FRONTEND_URL}{page}", timeout=15)
            ct = resp.headers.get("Content-Type", "")
            is_html = "text/html" in ct
            if resp.status_code == 200 and is_html:
                print(f"  ✓ {page}: 200 HTML")
                RESULTS.append((f"前端{page}", "PASS", ""))
            elif resp.status_code == 200:
                print(f"  ✓ {page}: 200")
                RESULTS.append((f"前端{page}", "PASS", ""))
            else:
                print(f"  ✗ {page}: HTTP {resp.status_code}")
                RESULTS.append((f"前端{page}", "FAIL", f"HTTP {resp.status_code}"))
        except Exception as e:
            print(f"  ✗ {page}: {e}")
            RESULTS.append((f"前端{page}", "FAIL", str(e)[:30]))


def print_summary():
    """测试总结"""
    section("测试总结")

    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    warned = sum(1 for _, s, _ in RESULTS if s == "WARN")
    failed = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    total = len(RESULTS)

    print(f"  总计: {total} 个测试")
    print(f"  通过: {passed}")
    print(f"  警告: {warned}")
    print(f"  失败: {failed}")
    print()

    if failed > 0:
        print("  失败项:")
        for name, status, detail in RESULTS:
            if status == "FAIL":
                print(f"    ✗ {name}: {detail}")
        print()

    if warned > 0:
        print("  警告项:")
        for name, status, detail in RESULTS:
            if status == "WARN":
                print(f"    ⚠ {name}: {detail}")
        print()

    pass_rate = (passed / total * 100) if total > 0 else 0
    print(f"  通过率: {pass_rate:.1f}%")


def main():
    print("能源可信数据空间 - 逐模块功能测试")
    print(f"后端: {BASE_URL}")
    print(f"前端: {FRONTEND_URL}")
    print(f"超时: {TIMEOUT}s")
    print()

    if not login():
        print("登录失败，继续无 token 测试...")

    test_auth()
    test_portal()
    test_data_center()
    test_compute()
    test_blockchain()
    test_trusted_sharing()
    test_federated_learning()
    test_security()
    test_ops()
    test_monitoring()
    test_notification()
    test_agents()
    test_frontend_pages()

    print_summary()


if __name__ == "__main__":
    main()
