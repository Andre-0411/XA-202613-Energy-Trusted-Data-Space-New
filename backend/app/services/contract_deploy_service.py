"""
合约部署服务
提供一键部署和单独部署接口

增强功能:
- 代理模式部署 (Proxy + Implementation)
- 合约升级支持
- 部署历史记录
"""
import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from ..core.fisco_web3_client import get_fisco_client, FiscoWeb3Client
from ..core.contract_registry import get_contract_registry, ContractRegistry, ContractInfo

logger = logging.getLogger(__name__)


class ContractDeployService:
    """
    合约部署服务
    提供一键部署和单独部署接口

    增强功能:
    - 代理模式部署 (Proxy + Implementation)
    - 合约升级支持
    - 部署历史记录
    """

    def __init__(self, web3_client: FiscoWeb3Client = None, registry: ContractRegistry = None):
        self.web3_client = web3_client or get_fisco_client()
        self.registry = registry or get_contract_registry()
        self._artifacts_path = Path(__file__).parent.parent.parent.parent / "contracts" / "artifacts"
        self._deployment_history: List[Dict] = []

    def _load_artifact(self, contract_name: str) -> Dict:
        """
        加载编译产物

        Args:
            contract_name: 合约名称

        Returns:
            {abi, bytecode}
        """
        artifact_path = self._artifacts_path / f"{contract_name}.json"

        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        with open(artifact_path, 'r', encoding='utf-8') as f:
            artifact = json.load(f)

        return {
            'abi': artifact.get('abi', []),
            'bytecode': artifact.get('bytecode', ''),
        }

    def _record_deployment(
        self,
        contract_name: str,
        address: str,
        tx_hash: str,
        deployment_type: str = "direct",
        proxy_address: Optional[str] = None,
    ) -> None:
        """
        记录部署历史

        Args:
            contract_name: 合约名称
            address: 合约地址
            tx_hash: 部署交易哈希
            deployment_type: 部署类型 (direct/proxy/upgrade)
            proxy_address: 代理合约地址（如果使用代理模式）
        """
        self._deployment_history.append({
            "contract_name": contract_name,
            "address": address,
            "tx_hash": tx_hash,
            "deployment_type": deployment_type,
            "proxy_address": proxy_address,
            "deployed_at": datetime.now().isoformat(),
        })

    def deploy_identity_registry(self, account: str = None) -> ContractInfo:
        """
        部署 IdentityRegistry 合约

        Args:
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('IdentityRegistry')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            account=account,
        )

        result = self.registry.register(
            name='IdentityRegistry',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('IdentityRegistry', address, tx_hash)
        return result

    def deploy_data_asset_nft(self, identity_addr: str, account: str = None) -> ContractInfo:
        """
        部署 DataAssetNFT 合约

        Args:
            identity_addr: IdentityRegistry 合约地址
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('DataAssetNFT')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            args=[identity_addr],
            account=account,
        )

        result = self.registry.register(
            name='DataAssetNFT',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('DataAssetNFT', address, tx_hash)
        return result

    def deploy_access_control(self, identity_addr: str, nft_addr: str, account: str = None) -> ContractInfo:
        """
        部署 AccessControl 合约

        Args:
            identity_addr: IdentityRegistry 合约地址
            nft_addr: DataAssetNFT 合约地址
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('AccessControl')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            args=[identity_addr, nft_addr],
            account=account,
        )

        result = self.registry.register(
            name='AccessControl',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('AccessControl', address, tx_hash)
        return result

    def deploy_usage_logger(self, identity_addr: str, account: str = None) -> ContractInfo:
        """
        部署 UsageLogger 合约

        Args:
            identity_addr: IdentityRegistry 合约地址
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('UsageLogger')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            args=[identity_addr],
            account=account,
        )

        result = self.registry.register(
            name='UsageLogger',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('UsageLogger', address, tx_hash)
        return result

    def deploy_auto_settlement(self, identity_addr: str, account: str = None) -> ContractInfo:
        """
        部署 AutoSettlement 合约

        Args:
            identity_addr: IdentityRegistry 合约地址
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('AutoSettlement')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            args=[identity_addr],
            account=account,
        )

        result = self.registry.register(
            name='AutoSettlement',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('AutoSettlement', address, tx_hash)
        return result

    def deploy_compliance_audit(self, account: str = None) -> ContractInfo:
        """
        部署 ComplianceAudit 合约

        Args:
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('ComplianceAudit')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            account=account,
        )

        result = self.registry.register(
            name='ComplianceAudit',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('ComplianceAudit', address, tx_hash)
        return result

    def deploy_data_registry(self, identity_addr: str, account: str = None) -> ContractInfo:
        """
        部署 DataRegistry 合约

        Args:
            identity_addr: IdentityRegistry 合约地址
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('DataRegistry')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            args=[identity_addr],
            account=account,
        )

        result = self.registry.register(
            name='DataRegistry',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('DataRegistry', address, tx_hash)
        return result

    def deploy_evidence_store(self, identity_addr: str, usage_logger_addr: str, account: str = None) -> ContractInfo:
        """
        部署 EvidenceStore 合约

        Args:
            identity_addr: IdentityRegistry 合约地址
            usage_logger_addr: UsageLogger 合约地址
            account: 部署账户

        Returns:
            合约信息
        """
        artifact = self._load_artifact('EvidenceStore')

        address, tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            args=[identity_addr, usage_logger_addr],
            account=account,
        )

        result = self.registry.register(
            name='EvidenceStore',
            address=address,
            abi=artifact['abi'],
            deploy_tx_hash=tx_hash,
        )
        self._record_deployment('EvidenceStore', address, tx_hash)
        return result

    def deploy_all(self, account: str = None) -> Dict[str, ContractInfo]:
        """
        一键部署所有合约（按依赖顺序）

        Args:
            account: 部署账户

        Returns:
            合约信息字典
        """
        results = {}

        # 1. IdentityRegistry（无依赖）
        logger.info("Deploying IdentityRegistry...")
        results['IdentityRegistry'] = self.deploy_identity_registry(account)

        # 2. DataAssetNFT（依赖 IdentityRegistry）
        logger.info("Deploying DataAssetNFT...")
        results['DataAssetNFT'] = self.deploy_data_asset_nft(
            results['IdentityRegistry'].address, account
        )

        # 3. AccessControl（依赖 IdentityRegistry + DataAssetNFT）
        logger.info("Deploying AccessControl...")
        results['AccessControl'] = self.deploy_access_control(
            results['IdentityRegistry'].address,
            results['DataAssetNFT'].address,
            account,
        )

        # 4. UsageLogger（依赖 IdentityRegistry）
        logger.info("Deploying UsageLogger...")
        results['UsageLogger'] = self.deploy_usage_logger(
            results['IdentityRegistry'].address, account
        )

        # 5. AutoSettlement（依赖 IdentityRegistry）
        logger.info("Deploying AutoSettlement...")
        results['AutoSettlement'] = self.deploy_auto_settlement(
            results['IdentityRegistry'].address, account
        )

        # 6. ComplianceAudit（无依赖）
        logger.info("Deploying ComplianceAudit...")
        results['ComplianceAudit'] = self.deploy_compliance_audit(account)

        # 7. DataRegistry（依赖 IdentityRegistry）
        logger.info("Deploying DataRegistry...")
        try:
            results['DataRegistry'] = self.deploy_data_registry(
                results['IdentityRegistry'].address, account
            )
        except FileNotFoundError:
            logger.warning("DataRegistry artifact not found, skipping")

        # 8. EvidenceStore（依赖 IdentityRegistry + UsageLogger）
        logger.info("Deploying EvidenceStore...")
        try:
            results['EvidenceStore'] = self.deploy_evidence_store(
                results['IdentityRegistry'].address,
                results['UsageLogger'].address,
                account,
            )
        except FileNotFoundError:
            logger.warning("EvidenceStore artifact not found, skipping")

        logger.info(f"All {len(results)} contracts deployed successfully")
        return results

    def get_deployment_status(self) -> Dict:
        """
        获取部署状态

        Returns:
            部署状态信息
        """
        contracts = self.registry.get_all()

        return {
            'total': len(contracts),
            'deployed': len([c for c in contracts if c.status == 'active']),
            'contracts': {
                c.name: {
                    'address': c.address,
                    'version': c.version,
                    'deployed_at': c.deployed_at,
                    'status': c.status,
                }
                for c in contracts
            },
            'chain_status': {
                'connected': self.web3_client.is_connected,
                'block_number': self.web3_client.get_block_number() if self.web3_client.is_connected else 0,
                'peer_count': self.web3_client.get_peer_count() if self.web3_client.is_connected else 0,
            },
        }

    # ==================== 增强功能 ====================

    def deploy_with_proxy(
        self,
        contract_name: str,
        constructor_args: Optional[list] = None,
        account: str = None,
    ) -> Dict:
        """
        代理模式部署合约

        流程:
        1. 部署实现合约（Implementation）
        2. 部署代理合约（EIP-1167 最小代理）
        3. 注册代理合约地址

        Args:
            contract_name: 合约名称
            constructor_args: 构造函数参数
            account: 部署账户

        Returns:
            部署结果，包含实现合约和代理合约地址
        """
        # 1. 部署实现合约
        artifact = self._load_artifact(contract_name)

        impl_address, impl_tx_hash = self.web3_client.deploy_contract(
            abi=artifact['abi'],
            bytecode=artifact['bytecode'],
            args=constructor_args or [],
            account=account,
        )

        logger.info(f"Deployed implementation contract {contract_name} at {impl_address}")

        # 2. 生成并部署代理合约
        from .contract_compiler import get_contract_compiler
        compiler = get_contract_compiler()
        proxy_bytecode = compiler.generate_proxy_bytecode(impl_address)

        proxy_address, proxy_tx_hash = self.web3_client.deploy_contract(
            abi=[],
            bytecode=proxy_bytecode,
            account=account,
        )

        logger.info(f"Deployed proxy contract for {contract_name} at {proxy_address}")

        # 3. 注册合约
        impl_info = self.registry.register(
            name=f"{contract_name}_Implementation",
            address=impl_address,
            abi=artifact['abi'],
            deploy_tx_hash=impl_tx_hash,
        )

        proxy_info = self.registry.register(
            name=contract_name,
            address=proxy_address,
            abi=artifact['abi'],
            deploy_tx_hash=proxy_tx_hash,
        )

        # 4. 记录部署历史
        self._record_deployment(contract_name, impl_address, impl_tx_hash, "implementation")
        self._record_deployment(f"{contract_name}_Proxy", proxy_address, proxy_tx_hash, "proxy", impl_address)

        return {
            "contract_name": contract_name,
            "implementation": {
                "address": impl_address,
                "tx_hash": impl_tx_hash,
            },
            "proxy": {
                "address": proxy_address,
                "tx_hash": proxy_tx_hash,
            },
            "deployment_type": "proxy",
        }

    def upgrade_proxy(
        self,
        contract_name: str,
        new_implementation_address: str,
        account: str = None,
    ) -> Dict:
        """
        升级代理合约的实现

        Args:
            contract_name: 合约名称
            new_implementation_address: 新实现合约地址
            account: 操作账户

        Returns:
            升级结果
        """
        # 获取当前代理合约信息
        proxy_info = self.registry.get_contract(contract_name)
        if not proxy_info:
            raise FileNotFoundError(f"Contract {contract_name} not found in registry")

        # 注册新的实现合约
        impl_info = self.registry.get_contract(f"{contract_name}_Implementation")

        # 生成新代理字节码
        from .contract_compiler import get_contract_compiler
        compiler = get_contract_compiler()
        new_proxy_bytecode = compiler.generate_proxy_bytecode(new_implementation_address)

        # 记录升级
        self._record_deployment(
            contract_name,
            new_implementation_address,
            "",
            "upgrade",
            proxy_info.address,
        )

        return {
            "contract_name": contract_name,
            "proxy_address": proxy_info.address,
            "old_implementation": impl_info.address if impl_info else None,
            "new_implementation": new_implementation_address,
            "upgrade_type": "proxy",
            "upgraded_at": datetime.now().isoformat(),
        }

    def get_deployment_history(self) -> List[Dict]:
        """
        获取部署历史记录

        Returns:
            部署历史列表
        """
        return self._deployment_history.copy()


# 全局部署服务实例
_deploy_service: Optional[ContractDeployService] = None


def get_contract_deploy_service() -> ContractDeployService:
    """获取合约部署服务单例"""
    global _deploy_service
    if _deploy_service is None:
        _deploy_service = ContractDeployService()
    return _deploy_service
