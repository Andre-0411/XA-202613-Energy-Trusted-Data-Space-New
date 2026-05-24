#!/usr/bin/env python3
"""
Solidity 合约部署脚本
按依赖顺序部署所有合约到 FISCO BCOS
"""
import json
import sys
from pathlib import Path
from typing import Dict

# 添加 backend 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.fisco_web3_client import FiscoWeb3Client, FiscoConfig
from app.core.contract_registry import ContractRegistry
from app.services.contract_deploy_service import ContractDeployService


def load_config() -> Dict:
    """加载部署配置"""
    config_path = Path(__file__).parent / "deploy_config.json"

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        print("Please create deploy_config.json with your network settings")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def deploy():
    """部署所有合约"""
    print("=" * 60)
    print("能源可信数据空间 - 智能合约部署工具")
    print("=" * 60)

    # 加载配置
    config = load_config()
    network = config.get('network', {})
    account = config.get('account', {})

    print(f"\nNetwork: {network.get('rpc_url', 'http://127.0.0.1:8545')}")
    print(f"Chain ID: {network.get('chain_id', 1)}")
    print(f"Account: {account.get('address', 'Not configured')}")

    # 初始化客户端
    fisco_config = FiscoConfig(
        rpc_url=network.get('rpc_url', 'http://127.0.0.1:8545'),
        chain_id=network.get('chain_id', 1),
        group_id=network.get('group_id', 1),
    )

    client = FiscoWeb3Client(fisco_config)

    if not client.is_connected:
        print("\nError: Cannot connect to FISCO BCOS node")
        print("Please check your network configuration and ensure the node is running")
        sys.exit(1)

    print(f"\nConnected to FISCO BCOS")
    print(f"Block number: {client.get_block_number()}")
    print(f"Peer count: {client.get_peer_count()}")

    # 初始化注册中心和服务
    registry = ContractRegistry()
    deploy_service = ContractDeployService(client, registry)

    # 检查是否已部署
    existing = registry.get_all()
    if existing:
        print(f"\nFound {len(existing)} existing contracts:")
        for contract in existing:
            print(f"  - {contract.name}: {contract.address}")

        response = input("\nDo you want to redeploy all contracts? (y/N): ")
        if response.lower() != 'y':
            print("Deployment cancelled")
            return

    # 部署所有合约
    print("\nDeploying contracts...")
    print("-" * 40)

    try:
        results = deploy_service.deploy_all(account=account.get('address'))

        print("\n" + "=" * 60)
        print("Deployment Summary")
        print("=" * 60)

        for name, info in results.items():
            print(f"\n{name}:")
            print(f"  Address: {info.address}")
            print(f"  Version: {info.version}")
            print(f"  TX Hash: {info.deploy_tx_hash}")

        print("\n" + "=" * 60)
        print("All contracts deployed successfully!")
        print("=" * 60)

        # 更新配置文件
        config['contracts'] = {
            name: {
                'address': info.address,
                'deployed_at': info.deployed_at,
                'version': info.version,
                'deploy_tx_hash': info.deploy_tx_hash,
            }
            for name, info in results.items()
        }

        config_path = Path(__file__).parent / "deploy_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"\nConfig updated: {config_path}")

    except Exception as e:
        print(f"\nError during deployment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    deploy()
