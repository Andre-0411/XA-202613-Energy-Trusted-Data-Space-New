"""
合约地址注册中心
管理已部署合约的地址和 ABI
"""
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ContractInfo(BaseModel):
    """合约信息"""
    name: str
    address: str
    abi: list
    bytecode: str = ""
    version: str = "1.0.0"
    deployed_at: str = ""
    deploy_tx_hash: str = ""
    status: str = "active"  # active/inactive/upgrading


class ContractRegistry:
    """
    合约地址注册中心
    内存 + 文件双缓存管理已部署合约的地址和 ABI
    """

    def __init__(self, config_path: str = None):
        self._contracts: Dict[str, ContractInfo] = {}
        self._config_path = config_path or str(
            Path(__file__).parent.parent.parent.parent / "contracts" / "deploy_config.json"
        )
        self._load_from_config()

    def _load_from_config(self):
        """从配置文件加载合约信息"""
        try:
            config_path = Path(self._config_path)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                contracts_config = config.get('contracts', {})
                for name, info in contracts_config.items():
                    if info.get('address'):
                        self._contracts[name] = ContractInfo(
                            name=name,
                            address=info['address'],
                            abi=info.get('abi', []),
                            version=info.get('version', '1.0.0'),
                            deployed_at=info.get('deployed_at', ''),
                            deploy_tx_hash=info.get('deploy_tx_hash', ''),
                            status=info.get('status', 'active'),
                        )
                logger.info(f"Loaded {len(self._contracts)} contracts from config")
        except (FileNotFoundError, json.JSONDecodeError, PermissionError, IOError) as e:
            logger.warning(f"Failed to load contract config: {e}")

    def _save_to_config(self):
        """保存合约信息到配置文件"""
        try:
            config_path = Path(self._config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # 读取现有配置
            config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # 更新合约信息
            if 'contracts' not in config:
                config['contracts'] = {}

            for name, info in self._contracts.items():
                config['contracts'][name] = {
                    'address': info.address,
                    'abi': info.abi,
                    'version': info.version,
                    'deployed_at': info.deployed_at,
                    'deploy_tx_hash': info.deploy_tx_hash,
                    'status': info.status,
                }

            # 保存
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self._contracts)} contracts to config")
        except (PermissionError, IOError, TypeError) as e:
            logger.error(f"Failed to save contract config: {e}")

    def register(self, name: str, address: str, abi: list, version: str = "1.0.0",
                 deploy_tx_hash: str = "") -> ContractInfo:
        """
        注册合约

        Args:
            name: 合约名称
            address: 合约地址
            abi: 合约 ABI
            version: 版本号
            deploy_tx_hash: 部署交易哈希

        Returns:
            合约信息
        """
        info = ContractInfo(
            name=name,
            address=address,
            abi=abi,
            version=version,
            deployed_at=datetime.now().isoformat(),
            deploy_tx_hash=deploy_tx_hash,
            status="active",
        )

        self._contracts[name] = info
        self._save_to_config()

        logger.info(f"Registered contract: {name} at {address}")
        return info

    def get_contract(self, name: str) -> Optional[ContractInfo]:
        """
        获取合约信息

        Args:
            name: 合约名称

        Returns:
            合约信息
        """
        return self._contracts.get(name)

    def get_all(self) -> List[ContractInfo]:
        """获取所有已注册合约"""
        return list(self._contracts.values())

    def update_address(self, name: str, new_address: str):
        """
        更新合约地址

        Args:
            name: 合约名称
            new_address: 新地址
        """
        if name in self._contracts:
            self._contracts[name].address = new_address
            self._contracts[name].deployed_at = datetime.now().isoformat()
            self._save_to_config()
            logger.info(f"Updated contract {name} address to {new_address}")

    def get_abi(self, name: str) -> Optional[list]:
        """
        获取合约 ABI

        Args:
            name: 合约名称

        Returns:
            合约 ABI
        """
        contract = self._contracts.get(name)
        return contract.abi if contract else None

    def get_address(self, name: str) -> Optional[str]:
        """
        获取合约地址

        Args:
            name: 合约名称

        Returns:
            合约地址
        """
        contract = self._contracts.get(name)
        return contract.address if contract else None

    def is_deployed(self, name: str) -> bool:
        """检查合约是否已部署"""
        return name in self._contracts and bool(self._contracts[name].address)

    def remove(self, name: str):
        """移除合约注册"""
        if name in self._contracts:
            del self._contracts[name]
            self._save_to_config()
            logger.info(f"Removed contract: {name}")


# 全局注册中心实例
_registry: Optional[ContractRegistry] = None


def get_contract_registry() -> ContractRegistry:
    """获取合约注册中心单例"""
    global _registry
    if _registry is None:
        _registry = ContractRegistry()
    return _registry
