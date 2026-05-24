#!/usr/bin/env python3
"""
能源可信数据空间项目 QA 测试脚本
测试所有核心 API 端点的可用性
"""
import requests
import json
import sys
from typing import Dict, Any, List

BASE_URL = "http://10.241.2.64:8000"
HEADERS = {"Content-Type": "application/json"}

# 测试结果存储
results = []

def log_result(test_name: str, expected: str, actual: str, status: str, module: str = ""):
    """记录测试结果"""
    results.append({
        "module": module,
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "status": status
    })
    print(f"[{status}] {test_name}: {actual[:100]}...")

def test_login() -> str:
    """测试登录并返回 token"""
    print("\n=== 测试认证模块 ===")
    
    # 测试登录
    login_data = {
        "username": "admin",
        "password": "admin123",
        "auth_type": "password"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                token = data["data"]["access_token"]
                log_result("登录", "返回 token", "成功获取 token", "✅", "认证")
                return token
            else:
                log_result("登录", "返回成功", f"错误: {data.get('message')}", "❌", "认证")
        else:
            log_result("登录", "200", f"HTTP {response.status_code}", "❌", "认证")
    except Exception as e:
        log_result("登录", "连接成功", f"异常: {e}", "❌", "认证")
    
    return ""

def test_auth_endpoints(token: str):
    """测试认证相关端点"""
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    # 测试获取会话
    try:
        response = requests.get(f"{BASE_URL}/api/v1/auth/session", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("获取会话", "返回会话信息", "成功", "✅", "认证")
            else:
                log_result("获取会话", "返回成功", f"错误: {data.get('message')}", "❌", "认证")
        else:
            log_result("获取会话", "200", f"HTTP {response.status_code}", "❌", "认证")
    except Exception as e:
        log_result("获取会话", "连接成功", f"异常: {e}", "❌", "认证")
    
    # 测试刷新 token
    try:
        # 这里需要 refresh_token，暂时跳过
        log_result("刷新 Token", "需要 refresh_token", "跳过测试", "⚠️", "认证")
    except Exception as e:
        log_result("刷新 Token", "连接成功", f"异常: {e}", "❌", "认证")

def test_data_endpoints(token: str):
    """测试数据资源模块"""
    print("\n=== 测试数据资源模块 ===")
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    # 数据资产列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/data/assets", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("数据资产列表", "返回资产列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "数据资源")
            else:
                log_result("数据资产列表", "返回成功", f"错误: {data.get('message')}", "❌", "数据资源")
        else:
            log_result("数据资产列表", "200", f"HTTP {response.status_code}", "❌", "数据资源")
    except Exception as e:
        log_result("数据资产列表", "连接成功", f"异常: {e}", "❌", "数据资源")
    
    # 数据源列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/data/sources", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("数据源列表", "返回数据源列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "数据资源")
            else:
                log_result("数据源列表", "返回成功", f"错误: {data.get('message')}", "❌", "数据资源")
        else:
            log_result("数据源列表", "200", f"HTTP {response.status_code}", "❌", "数据资源")
    except Exception as e:
        log_result("数据源列表", "连接成功", f"异常: {e}", "❌", "数据资源")
    
    # 数据目录
    try:
        response = requests.get(f"{BASE_URL}/api/v1/catalog/items", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("数据目录", "返回目录列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "数据资源")
            else:
                log_result("数据目录", "返回成功", f"错误: {data.get('message')}", "❌", "数据资源")
        else:
            log_result("数据目录", "200", f"HTTP {response.status_code}", "❌", "数据资源")
    except Exception as e:
        log_result("数据目录", "连接成功", f"异常: {e}", "❌", "数据资源")

def test_compute_endpoints(token: str):
    """测试计算模块"""
    print("\n=== 测试计算模块 ===")
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    # 计算任务列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/compute/tasks", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("计算任务列表", "返回任务列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "计算")
            else:
                log_result("计算任务列表", "返回成功", f"错误: {data.get('message')}", "❌", "计算")
        else:
            log_result("计算任务列表", "200", f"HTTP {response.status_code}", "❌", "计算")
    except Exception as e:
        log_result("计算任务列表", "连接成功", f"异常: {e}", "❌", "计算")
    
    # 计算代理列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/compute/agents", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("计算代理列表", "返回代理列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "计算")
            else:
                log_result("计算代理列表", "返回成功", f"错误: {data.get('message')}", "❌", "计算")
        else:
            log_result("计算代理列表", "200", f"HTTP {response.status_code}", "❌", "计算")
    except Exception as e:
        log_result("计算代理列表", "连接成功", f"异常: {e}", "❌", "计算")

def test_blockchain_endpoints(token: str):
    """测试区块链模块"""
    print("\n=== 测试区块链模块 ===")
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    # NFT 列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/blockchain/nft", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("NFT列表", "返回NFT列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "区块链")
            else:
                log_result("NFT列表", "返回成功", f"错误: {data.get('message')}", "❌", "区块链")
        else:
            log_result("NFT列表", "200", f"HTTP {response.status_code}", "❌", "区块链")
    except Exception as e:
        log_result("NFT列表", "连接成功", f"异常: {e}", "❌", "区块链")
    
    # 存证列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/blockchain/evidence", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("存证列表", "返回存证列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "区块链")
            else:
                log_result("存证列表", "返回成功", f"错误: {data.get('message')}", "❌", "区块链")
        else:
            log_result("存证列表", "200", f"HTTP {response.status_code}", "❌", "区块链")
    except Exception as e:
        log_result("存证列表", "连接成功", f"异常: {e}", "❌", "区块链")
    
    # 合约列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/blockchain/contracts", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("合约列表", "返回合约列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "区块链")
            else:
                log_result("合约列表", "返回成功", f"错误: {data.get('message')}", "❌", "区块链")
        else:
            log_result("合约列表", "200", f"HTTP {response.status_code}", "❌", "区块链")
    except Exception as e:
        log_result("合约列表", "连接成功", f"异常: {e}", "❌", "区块链")
    
    # 结算列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/blockchain/settle", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("结算列表", "返回结算列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "区块链")
            else:
                log_result("结算列表", "返回成功", f"错误: {data.get('message')}", "❌", "区块链")
        else:
            log_result("结算列表", "200", f"HTTP {response.status_code}", "❌", "区块链")
    except Exception as e:
        log_result("结算列表", "连接成功", f"异常: {e}", "❌", "区块链")

def test_ops_endpoints(token: str):
    """测试运营模块"""
    print("\n=== 测试运营模块 ===")
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    # 用户列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ops/users", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("用户列表", "返回用户列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "运营")
            else:
                log_result("用户列表", "返回成功", f"错误: {data.get('message')}", "❌", "运营")
        else:
            log_result("用户列表", "200", f"HTTP {response.status_code}", "❌", "运营")
    except Exception as e:
        log_result("用户列表", "连接成功", f"异常: {e}", "❌", "运营")
    
    # 组织列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ops/organizations", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("组织列表", "返回组织列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "运营")
            else:
                log_result("组织列表", "返回成功", f"错误: {data.get('message')}", "❌", "运营")
        else:
            log_result("组织列表", "200", f"HTTP {response.status_code}", "❌", "运营")
    except Exception as e:
        log_result("组织列表", "连接成功", f"异常: {e}", "❌", "运营")
    
    # 监控数据
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ops/monitor", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("监控数据", "返回监控数据", "成功", "✅", "运营")
            else:
                log_result("监控数据", "返回成功", f"错误: {data.get('message')}", "❌", "运营")
        else:
            log_result("监控数据", "200", f"HTTP {response.status_code}", "❌", "运营")
    except Exception as e:
        log_result("监控数据", "连接成功", f"异常: {e}", "❌", "运营")
    
    # KPI 数据
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ops/kpi", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("KPI数据", "返回KPI数据", "成功", "✅", "运营")
            else:
                log_result("KPI数据", "返回成功", f"错误: {data.get('message')}", "❌", "运营")
        else:
            log_result("KPI数据", "200", f"HTTP {response.status_code}", "❌", "运营")
    except Exception as e:
        log_result("KPI数据", "连接成功", f"异常: {e}", "❌", "运营")
    
    # 告警列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/ops/alerts", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("告警列表", "返回告警列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "运营")
            else:
                log_result("告警列表", "返回成功", f"错误: {data.get('message')}", "❌", "运营")
        else:
            log_result("告警列表", "200", f"HTTP {response.status_code}", "❌", "运营")
    except Exception as e:
        log_result("告警列表", "连接成功", f"异常: {e}", "❌", "运营")

def test_security_endpoints(token: str):
    """测试安全模块"""
    print("\n=== 测试安全模块 ===")
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    # DID 列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/security/dids", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("DID列表", "返回DID列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "安全")
            else:
                log_result("DID列表", "返回成功", f"错误: {data.get('message')}", "❌", "安全")
        else:
            log_result("DID列表", "200", f"HTTP {response.status_code}", "❌", "安全")
    except Exception as e:
        log_result("DID列表", "连接成功", f"异常: {e}", "❌", "安全")
    
    # 密钥列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/security/keys", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("密钥列表", "返回密钥列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "安全")
            else:
                log_result("密钥列表", "返回成功", f"错误: {data.get('message')}", "❌", "安全")
        else:
            log_result("密钥列表", "200", f"HTTP {response.status_code}", "❌", "安全")
    except Exception as e:
        log_result("密钥列表", "连接成功", f"异常: {e}", "❌", "安全")
    
    # 策略列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/security/policies", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("策略列表", "返回策略列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "安全")
            else:
                log_result("策略列表", "返回成功", f"错误: {data.get('message')}", "❌", "安全")
        else:
            log_result("策略列表", "200", f"HTTP {response.status_code}", "❌", "安全")
    except Exception as e:
        log_result("策略列表", "连接成功", f"异常: {e}", "❌", "安全")
    
    # 威胁列表
    try:
        response = requests.get(f"{BASE_URL}/api/v1/security/threats", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                log_result("威胁列表", "返回威胁列表", f"成功，共 {len(data.get('data', {}).get('items', []))} 项", "✅", "安全")
            else:
                log_result("威胁列表", "返回成功", f"错误: {data.get('message')}", "❌", "安全")
        else:
            log_result("威胁列表", "200", f"HTTP {response.status_code}", "❌", "安全")
    except Exception as e:
        log_result("威胁列表", "连接成功", f"异常: {e}", "❌", "安全")

def test_error_handling(token: str):
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    
    # 测试未授权访问
    try:
        response = requests.get(f"{BASE_URL}/api/v1/data/assets", headers=HEADERS)
        if response.status_code == 401:
            log_result("未授权访问", "401", f"HTTP {response.status_code}", "✅", "错误处理")
        else:
            log_result("未授权访问", "401", f"HTTP {response.status_code}", "❌", "错误处理")
    except Exception as e:
        log_result("未授权访问", "连接成功", f"异常: {e}", "❌", "错误处理")
    
    # 测试无效 token
    invalid_headers = {**HEADERS, "Authorization": "Bearer invalid_token"}
    try:
        response = requests.get(f"{BASE_URL}/api/v1/data/assets", headers=invalid_headers)
        if response.status_code == 401:
            log_result("无效 Token", "401", f"HTTP {response.status_code}", "✅", "错误处理")
        else:
            log_result("无效 Token", "401", f"HTTP {response.status_code}", "❌", "错误处理")
    except Exception as e:
        log_result("无效 Token", "连接成功", f"异常: {e}", "❌", "错误处理")

def generate_report():
    """生成测试报告"""
    print("\n" + "="*80)
    print("能源可信数据空间项目 QA 测试报告")
    print("="*80)
    
    # 按模块分组
    modules = {}
    for result in results:
        module = result["module"]
        if module not in modules:
            modules[module] = []
        modules[module].append(result)
    
    total_tests = len(results)
    passed = sum(1 for r in results if r["status"] == "✅")
    failed = sum(1 for r in results if r["status"] == "❌")
    warnings = sum(1 for r in results if r["status"] == "⚠️")
    
    print(f"\n总计测试: {total_tests}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"警告: {warnings}")
    print(f"通过率: {passed/total_tests*100:.1f}%")
    
    print("\n" + "-"*80)
    print("详细结果:")
    print("-"*80)
    
    for module, tests in modules.items():
        print(f"\n【{module}】")
        for test in tests:
            print(f"  {test['status']} {test['test']}")
            if test['status'] == '❌':
                print(f"      预期: {test['expected']}")
                print(f"      实际: {test['actual']}")
    
    # 保存报告到文件
    with open("D:/XA-202613-Energy-Trusted-Data-Space-New/qa_test_report.txt", "w", encoding="utf-8") as f:
        f.write("能源可信数据空间项目 QA 测试报告\n")
        f.write("="*80 + "\n\n")
        f.write(f"总计测试: {total_tests}\n")
        f.write(f"通过: {passed}\n")
        f.write(f"失败: {failed}\n")
        f.write(f"警告: {warnings}\n")
        f.write(f"通过率: {passed/total_tests*100:.1f}%\n\n")
        
        for module, tests in modules.items():
            f.write(f"【{module}】\n")
            for test in tests:
                f.write(f"  {test['status']} {test['test']}\n")
                if test['status'] == '❌':
                    f.write(f"      预期: {test['expected']}\n")
                    f.write(f"      实际: {test['actual']}\n")
            f.write("\n")

def main():
    """主测试流程"""
    print("开始能源可信数据空间项目 QA 测试...")
    print(f"目标服务器: {BASE_URL}")
    
    # 1. 测试登录
    token = test_login()
    if not token:
        print("登录失败，无法继续测试")
        return
    
    # 2. 测试认证端点
    test_auth_endpoints(token)
    
    # 3. 测试数据资源模块
    test_data_endpoints(token)
    
    # 4. 测试计算模块
    test_compute_endpoints(token)
    
    # 5. 测试区块链模块
    test_blockchain_endpoints(token)
    
    # 6. 测试运营模块
    test_ops_endpoints(token)
    
    # 7. 测试安全模块
    test_security_endpoints(token)
    
    # 8. 测试错误处理
    test_error_handling(token)
    
    # 9. 生成报告
    generate_report()

if __name__ == "__main__":
    main()