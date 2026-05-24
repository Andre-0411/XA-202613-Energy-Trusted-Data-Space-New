"""
区块链链状态服务
链状态查询 / 合约部署状态
"""
import asyncio
import logging
from typing import Dict, Optional

from ..core.fisco_web3_client import get_fisco_client, FiscoWeb3Client
from ..core.contract_registry import get_contract_registry, ContractRegistry, ContractInfo
from .contract_deploy_service import get_contract_deploy_service, ContractDeployService

logger = logging.getLogger(__name__)


class BlockchainChainService:
    """
    区块链链状态服务
    封装链状态查询与合约部署调度
    """

    def __init__(
        self,
        web3_client: FiscoWeb3Client = None,
        registry: ContractRegistry = None,
        deploy_service: ContractDeployService = None,
    ):
        self.web3_client = web3_client or get_fisco_client()
        self.registry = registry or get_contract_registry()
        self.deploy_service = deploy_service or get_contract_deploy_service()

    async def get_chain_status(self) -> Dict:
        """
        获取链状态

        Returns:
            { connected, block_number, peer_count, chain_id, latest_block_time }
        """
        connected: bool = self.web3_client.is_connected
        block_number: int = 0
        peer_count: int = 0
        chain_id: int = 0
        latest_block_time: int = 0

        if connected:
            try:
                block_number = await asyncio.to_thread(self.web3_client.get_block_number)
            except Exception as e:
                logger.warning(f"Failed to get block number: {e}")

            try:
                peer_count = await asyncio.to_thread(self.web3_client.get_peer_count)
            except Exception as e:
                logger.warning(f"Failed to get peer count: {e}")

            try:
                chain_id = await asyncio.to_thread(self.web3_client.get_chain_id)
            except Exception as e:
                logger.warning(f"Failed to get chain id: {e}")

            try:
                block_info = await asyncio.to_thread(self.web3_client.get_block)
                latest_block_time = block_info.get('timestamp', 0)
            except Exception as e:
                logger.warning(f"Failed to get latest block time: {e}")

        return {
            'connected': connected,
            'block_number': block_number,
            'peer_count': peer_count,
            'chain_id': chain_id,
            'latest_block_time': latest_block_time,
        }

    async def get_deployment_status(self) -> Dict:
        """
        获取合约部署状态

        Returns:
            { total, deployed, contracts: {name: {address, version, status, deployed_at}} }
        """
        try:
            status = await asyncio.to_thread(self.deploy_service.get_deployment_status)
            return status
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return {
                'total': 0,
                'deployed': 0,
                'contracts': {},
                'chain_status': {'connected': False, 'block_number': 0, 'peer_count': 0},
            }

    async def deploy_contract(self, contract_name: str, account: str = None) -> Dict:
        """
        部署单个合约

        Args:
            contract_name: 合约名称（IdentityRegistry, DataAssetNFT, AccessControl,
                           UsageLogger, AutoSettlement, ComplianceAudit）
            account: 部署账户

        Returns:
            { name, address, deploy_tx_hash, version, status }

        Raises:
            ValueError: 合约名称不合法或依赖未部署
        """
        supported = {
            'IdentityRegistry': self._deploy_identity_registry,
            'DataAssetNFT': self._deploy_data_asset_nft,
            'AccessControl': self._deploy_access_control,
            'UsageLogger': self._deploy_usage_logger,
            'AutoSettlement': self._deploy_auto_settlement,
            'ComplianceAudit': self._deploy_compliance_audit,
        }

        if contract_name not in supported:
            raise ValueError(
                f"Unknown contract: {contract_name}. "
                f"Supported: {', '.join(supported.keys())}"
            )

        deploy_fn = supported[contract_name]
        result: ContractInfo = await asyncio.to_thread(deploy_fn, account)

        return {
            'name': result.name,
            'address': result.address,
            'deploy_tx_hash': result.deploy_tx_hash,
            'version': result.version,
            'status': result.status,
        }

    async def deploy_all_contracts(self, account: str = None) -> Dict:
        """
        一键部署所有合约

        Args:
            account: 部署账户

        Returns:
            { results: {name: {name, address, deploy_tx_hash, version, status}} }
        """
        raw: Dict[str, ContractInfo] = await asyncio.to_thread(
            self.deploy_service.deploy_all, account
        )

        results = {}
        for name, info in raw.items():
            results[name] = {
                'name': info.name,
                'address': info.address,
                'deploy_tx_hash': info.deploy_tx_hash,
                'version': info.version,
                'status': info.status,
            }

        return {'results': results}

    # ---- private deploy helpers ----

    def _deploy_identity_registry(self, account: str = None) -> ContractInfo:
        """部署 IdentityRegistry（无依赖）"""
        return self.deploy_service.deploy_identity_registry(account)

    def _deploy_data_asset_nft(self, account: str = None) -> ContractInfo:
        """部署 DataAssetNFT（依赖 IdentityRegistry）"""
        identity_addr = self.registry.get_address('IdentityRegistry')
        if not identity_addr:
            raise ValueError("IdentityRegistry must be deployed first")
        return self.deploy_service.deploy_data_asset_nft(identity_addr, account)

    def _deploy_access_control(self, account: str = None) -> ContractInfo:
        """部署 AccessControl（依赖 IdentityRegistry + DataAssetNFT）"""
        identity_addr = self.registry.get_address('IdentityRegistry')
        if not identity_addr:
            raise ValueError("IdentityRegistry must be deployed first")
        nft_addr = self.registry.get_address('DataAssetNFT')
        if not nft_addr:
            raise ValueError("DataAssetNFT must be deployed first")
        return self.deploy_service.deploy_access_control(identity_addr, nft_addr, account)

    def _deploy_usage_logger(self, account: str = None) -> ContractInfo:
        """部署 UsageLogger（依赖 IdentityRegistry）"""
        identity_addr = self.registry.get_address('IdentityRegistry')
        if not identity_addr:
            raise ValueError("IdentityRegistry must be deployed first")
        return self.deploy_service.deploy_usage_logger(identity_addr, account)

    def _deploy_auto_settlement(self, account: str = None) -> ContractInfo:
        """部署 AutoSettlement（依赖 IdentityRegistry）"""
        identity_addr = self.registry.get_address('IdentityRegistry')
        if not identity_addr:
            raise ValueError("IdentityRegistry must be deployed first")
        return self.deploy_service.deploy_auto_settlement(identity_addr, account)

    def _deploy_compliance_audit(self, account: str = None) -> ContractInfo:
        """部署 ComplianceAudit（无依赖）"""
        return self.deploy_service.deploy_compliance_audit(account)


# ---- 单例 ----
_chain_service: Optional[BlockchainChainService] = None


def get_blockchain_chain_service() -> BlockchainChainService:
    """获取区块链链状态服务单例"""
    global _chain_service
    if _chain_service is None:
        _chain_service = BlockchainChainService()
    return _chain_service
