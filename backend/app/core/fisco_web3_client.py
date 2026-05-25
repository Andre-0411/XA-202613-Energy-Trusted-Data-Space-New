"""
FISCO BCOS Web3 客户端
基于 Web3.py 封装 FISCO BCOS 3.x JSON-RPC 交互
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FiscoConfig(BaseModel):
    """FISCO BCOS 配置"""
    rpc_url: str = "http://127.0.0.1:8545"
    chain_id: int = 1
    group_id: int = 1
    sm_crypto: bool = False  # 是否使用国密


class ContractInfo(BaseModel):
    """合约信息"""
    name: str
    address: str
    abi: list
    bytecode: str = ""
    version: str = "1.0.0"


class FiscoWeb3Client:
    """
    FISCO BCOS Web3 客户端
    封装 Web3.py 对接 FISCO BCOS 3.x JSON-RPC
    """

    def __init__(self, config: Optional[FiscoConfig] = None):
        self.config = config or FiscoConfig()
        self._web3: Optional[Any] = None
        self._contracts: Dict[str, Any] = {}
        self._connected = False

        if WEB3_AVAILABLE:
            self._init_web3()

    def _init_web3(self):
        """初始化 Web3 连接"""
        try:
            # 使用 HTTP Provider 连接 FISCO BCOS
            provider = Web3.HTTPProvider(self.config.rpc_url)
            self._web3 = Web3(provider)

            # 注入 PoA 中间件（FISCO BCOS 使用 PBFT 共识）
            self._web3.middleware_onion.inject(geth_poa_middleware, layer=0)

            # 测试连接
            if self._web3.is_connected():
                self._connected = True
                logger.info(f"Connected to FISCO BCOS at {self.config.rpc_url}")
            else:
                logger.warning(f"Failed to connect to FISCO BCOS at {self.config.rpc_url}")
        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"Error initializing Web3: {e}")
            self._connected = False

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and WEB3_AVAILABLE

    @property
    def web3(self):
        """获取 Web3 实例"""
        return self._web3

    def deploy_contract(self, abi: list, bytecode: str, args: list = None, account: str = None) -> Tuple[str, str]:
        """
        部署合约

        Args:
            abi: 合约 ABI
            bytecode: 合约字节码
            args: 构造函数参数
            account: 部署账户地址

        Returns:
            (contract_address, tx_hash)
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        contract = self._web3.eth.contract(abi=abi, bytecode=bytecode)

        # 构建部署交易
        if args:
            tx = contract.constructor(*args).build_transaction({
                'from': account or self._web3.eth.default_account,
                'nonce': self._web3.eth.get_transaction_count(account or self._web3.eth.default_account),
                'gas': 3000000,
                'gasPrice': 0,  # FISCO BCOS 联盟链无 gas 费用
            })
        else:
            tx = contract.constructor().build_transaction({
                'from': account or self._web3.eth.default_account,
                'nonce': self._web3.eth.get_transaction_count(account or self._web3.eth.default_account),
                'gas': 3000000,
                'gasPrice': 0,
            })

        # 发送交易
        tx_hash = self._web3.eth.send_transaction(tx)
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        contract_address = receipt['contractAddress']
        logger.info(f"Contract deployed at {contract_address}, tx: {tx_hash.hex()}")

        return contract_address, tx_hash.hex()

    def load_contract(self, address: str, abi: list) -> Any:
        """
        加载已部署的合约

        Args:
            address: 合约地址
            abi: 合约 ABI

        Returns:
            Contract 实例
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        contract = self._web3.eth.contract(address=address, abi=abi)
        return contract

    def call_contract(self, address: str, abi: list, method: str, args: list = None) -> Any:
        """
        调用合约方法（只读）

        Args:
            address: 合约地址
            abi: 合约 ABI
            method: 方法名
            args: 方法参数

        Returns:
            返回值
        """
        contract = self.load_contract(address, abi)
        func = getattr(contract.functions, method)

        if args:
            return func(*args).call()
        else:
            return func().call()

    def send_transaction(self, address: str, abi: list, method: str, args: list = None, account: str = None) -> Dict:
        """
        发送交易调用合约方法（写操作）

        Args:
            address: 合约地址
            abi: 合约 ABI
            method: 方法名
            args: 方法参数
            account: 发送账户

        Returns:
            交易回执
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        contract = self.load_contract(address, abi)
        func = getattr(contract.functions, method)

        # 构建交易
        tx_params = {
            'from': account or self._web3.eth.default_account,
            'nonce': self._web3.eth.get_transaction_count(account or self._web3.eth.default_account),
            'gas': 3000000,
            'gasPrice': 0,
        }

        if args:
            tx = func(*args).build_transaction(tx_params)
        else:
            tx = func().build_transaction(tx_params)

        # 发送交易
        tx_hash = self._web3.eth.send_transaction(tx)
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            'tx_hash': tx_hash.hex(),
            'block_number': receipt['blockNumber'],
            'gas_used': receipt['gasUsed'],
            'status': receipt['status'],
            'contract_address': receipt.get('contractAddress'),
        }

    def get_transaction_receipt(self, tx_hash: str) -> Dict:
        """获取交易回执"""
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        receipt = self._web3.eth.get_transaction_receipt(tx_hash)
        return {
            'tx_hash': tx_hash,
            'block_number': receipt['blockNumber'],
            'gas_used': receipt['gasUsed'],
            'status': receipt['status'],
            'contract_address': receipt.get('contractAddress'),
            'logs': [dict(log) for log in receipt.get('logs', [])],
        }

    def get_block(self, block_number: int = None) -> Dict:
        """获取区块信息"""
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        if block_number is None:
            block_number = self._web3.eth.block_number

        block = self._web3.eth.get_block(block_number)
        return {
            'number': block['number'],
            'hash': block['hash'].hex(),
            'parent_hash': block['parentHash'].hex(),
            'timestamp': block['timestamp'],
            'transactions': len(block['transactions']),
            'gas_used': block['gasUsed'],
            'gas_limit': block['gasLimit'],
        }

    def get_block_number(self) -> int:
        """获取最新区块号"""
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        return self._web3.eth.block_number

    def get_peer_count(self) -> int:
        """获取节点数量"""
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        try:
            return self._web3.net.peer_count
        except (ConnectionError, AttributeError):
            return 0

    def get_chain_id(self) -> int:
        """获取链 ID"""
        if not self.is_connected:
            raise ConnectionError("Not connected to FISCO BCOS")

        return self._web3.eth.chain_id

    def encode_abi(self, abi: list, method: str, args: list = None) -> str:
        """
        ABI 编码

        Args:
            abi: 合约 ABI
            method: 方法名
            args: 参数

        Returns:
            编码后的数据
        """
        contract = self._web3.eth.contract(abi=abi)
        func = getattr(contract.functions, method)

        if args:
            data = func(*args).build_transaction({'gas': 0, 'gasPrice': 0})['data']
        else:
            data = func().build_transaction({'gas': 0, 'gasPrice': 0})['data']

        return data

    def decode_abi(self, abi: list, method: str, data: str) -> Any:
        """
        ABI 解码

        Args:
            abi: 合约 ABI
            method: 方法名
            data: 编码数据

        Returns:
            解码后的数据
        """
        contract = self._web3.eth.contract(abi=abi)
        func = getattr(contract.functions, method)

        # 解码返回数据
        output_types = func().abi['outputs']
        decoded = self._web3.codec.decode(output_types, bytes.fromhex(data[2:] if data.startswith('0x') else data))

        return decoded

    def close(self):
        """关闭连接"""
        self._web3 = None
        self._connected = False
        logger.info("Disconnected from FISCO BCOS")


# 全局客户端实例
_fisco_client: Optional[FiscoWeb3Client] = None


def get_fisco_client() -> FiscoWeb3Client:
    """获取 FISCO BCOS 客户端单例"""
    global _fisco_client
    if _fisco_client is None:
        from ..config import settings
        config = FiscoConfig(
            rpc_url=getattr(settings, 'FISCO_WEB3_PROVIDER_URL', 'http://127.0.0.1:8545'),
            chain_id=getattr(settings, 'FISCO_CHAIN_ID', 1),
            group_id=getattr(settings, 'FISCO_GROUP_ID', 1),
        )
        _fisco_client = FiscoWeb3Client(config)
    return _fisco_client
