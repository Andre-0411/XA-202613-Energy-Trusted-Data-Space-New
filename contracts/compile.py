#!/usr/bin/env python3
"""
Solidity 合约编译脚本
使用 solc 编译所有 .sol 文件，输出 ABI + Bytecode JSON
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


# 合约列表
CONTRACTS = [
    "IdentityRegistry",
    "DataAssetNFT",
    "AccessControl",
    "UsageLogger",
    "AutoSettlement",
    "ComplianceAudit",
]

# 接口列表
INTERFACES = [
    "IIdentityRegistry",
    "IDataAssetNFT",
    "IAccessControl",
    "IUsageLogger",
    "IAutoSettlement",
    "IComplianceAudit",
]


def find_solc() -> str:
    """查找 solc 编译器"""
    # 尝试使用 solc-select
    try:
        result = subprocess.run(["solc", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "solc"
    except FileNotFoundError:
        pass

    # 尝试使用 solcjs
    try:
        result = subprocess.run(["solcjs", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "solcjs"
    except FileNotFoundError:
        pass

    print("Error: solc not found. Please install solc or solc-select")
    print("  pip install solc-select")
    print("  solc-select install 0.8.24")
    print("  solc-select use 0.8.24")
    sys.exit(1)


def compile_contract(solc_path: str, contract_path: Path, output_dir: Path) -> Dict:
    """
    编译单个合约

    Args:
        solc_path: solc 路径
        contract_path: 合约文件路径
        output_dir: 输出目录

    Returns:
        {abi, bytecode}
    """
    contract_name = contract_path.stem

    # 使用 solc 编译
    cmd = [
        solc_path,
        "--abi",
        "--bin",
        "--optimize",
        "--optimize-runs", "200",
        "--output-dir", str(output_dir),
        "--overwrite",
        str(contract_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error compiling {contract_name}:")
        print(result.stderr)
        return None

    # 读取编译结果
    abi_path = output_dir / f"{contract_name}.abi"
    bin_path = output_dir / f"{contract_name}.bin"

    if not abi_path.exists() or not bin_path.exists():
        print(f"Error: Compiled files not found for {contract_name}")
        return None

    with open(abi_path, 'r') as f:
        abi = json.load(f)

    with open(bin_path, 'r') as f:
        bytecode = f.read().strip()

    # 清理临时文件
    abi_path.unlink()
    bin_path.unlink()

    return {
        "abi": abi,
        "bytecode": f"0x{bytecode}",
        "contractName": contract_name,
        "compiler": {
            "version": "0.8.24",
            "optimize": True,
            "runs": 200,
        },
    }


def compile_all():
    """编译所有合约"""
    # 查找 solc
    solc_path = find_solc()
    print(f"Using solc: {solc_path}")

    # 设置路径
    contracts_dir = Path(__file__).parent
    artifacts_dir = contracts_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    # 编译接口
    print("\nCompiling interfaces...")
    interfaces_dir = contracts_dir / "interfaces"
    for interface_name in INTERFACES:
        interface_path = interfaces_dir / f"{interface_name}.sol"
        if interface_path.exists():
            print(f"  Compiling {interface_name}...")
            compile_contract(solc_path, interface_path, artifacts_dir)

    # 编译合约
    print("\nCompiling contracts...")
    for contract_name in CONTRACTS:
        contract_path = contracts_dir / f"{contract_name}.sol"
        if contract_path.exists():
            print(f"  Compiling {contract_name}...")
            result = compile_contract(solc_path, contract_path, artifacts_dir)
            if result:
                # 保存到 artifacts
                artifact_path = artifacts_dir / f"{contract_name}.json"
                with open(artifact_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"    -> {artifact_path}")
            else:
                print(f"    -> Failed!")
        else:
            print(f"  Skipping {contract_name} (not found)")

    print(f"\nCompilation complete. Artifacts saved to: {artifacts_dir}")


if __name__ == "__main__":
    compile_all()
