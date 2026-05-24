"""
FISCO BCOS Python SDK 封装
合约调用 / 交易发送 / 事件监听
"""
import json
import logging
from typing import Optional, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class FiscoClient:
    """
    FISCO BCOS 客户端
    通过 Channel 协议与节点通信
    """

    def __init__(self):
        self.channel_host = settings.FISCO_CHANNEL_HOST
        self.channel_port = settings.FISCO_CHANNEL_PORT
        self.group_id = settings.FISCO_GROUP_ID
        self.sm_crypto = settings.FISCO_SM_CRYPTO
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（FISCO BCOS 3.x JSON-RPC）"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"http://{self.channel_host}:{self.channel_port}",
                timeout=30.0,
            )
        return self._client

    async def _rpc_call(self, method: str, params: list) -> dict:
        """
        发送 JSON-RPC 请求

        Args:
            method: RPC 方法名
            params: 参数列表

        Returns:
            RPC 响应
        """
        client = await self._get_client()
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [self.group_id] + params,
            "id": 1,
        }
        try:
            response = await client.post("/", json=payload)
            response.raise_for_status()
            result = response.json()
            if "error" in result:
                logger.error(f"FISCO RPC error: {result['error']}")
                raise Exception(f"FISCO RPC error: {result['error']}")
            return result.get("result", {})
        except httpx.HTTPError as e:
            logger.error(f"FISCO HTTP error: {e}")
            raise

    async def get_block_number(self) -> int:
        """获取当前区块号"""
        result = await self._rpc_call("getBlockNumber", [])
        return int(result, 16) if isinstance(result, str) else result

    async def get_peer_count(self) -> int:
        """获取节点数"""
        result = await self._rpc_call("getPeers", [])
        return len(result) if isinstance(result, list) else 0

    async def send_transaction(
        self,
        contract_address: str,
        method: str,
        params: Optional[dict] = None,
        from_address: Optional[str] = None,
    ) -> dict:
        """
        发送交易

        Args:
            contract_address: 合约地址
            method: 调用方法
            params: 调用参数
            from_address: 发起地址

        Returns:
            交易结果
        """
        tx_data = {
            "to": contract_address,
            "from": from_address or "0x0",
            "data": json.dumps({"method": method, "params": params or {}}),
        }
        result = await self._rpc_call("sendTx", [tx_data])
        return result

    async def call_contract(
        self,
        contract_address: str,
        method: str,
        params: Optional[dict] = None,
    ) -> dict:
        """
        只读合约调用

        Args:
            contract_address: 合约地址
            method: 调用方法
            params: 调用参数

        Returns:
            调用结果
        """
        call_data = {
            "to": contract_address,
            "data": json.dumps({"method": method, "params": params or {}}),
        }
        result = await self._rpc_call("call", [call_data])
        return result

    async def get_transaction_receipt(self, tx_hash: str) -> dict:
        """获取交易回执"""
        result = await self._rpc_call("getTransactionReceipt", [tx_hash])
        return result

    async def deploy_contract(
        self,
        bytecode: str,
        abi: str,
        constructor_args: Optional[list] = None,
    ) -> str:
        """
        部署合约

        Args:
            bytecode: 合约字节码
            abi: 合约 ABI
            constructor_args: 构造函数参数

        Returns:
            合约地址
        """
        deploy_data = {
            "bytecode": bytecode,
            "abi": abi,
            "constructorArgs": constructor_args or [],
        }
        result = await self._rpc_call("deploy", [deploy_data])
        return result.get("contractAddress", "")

    async def register_did(self, did: str, public_key: str) -> dict:
        """注册 DID 到链上"""
        return await self.send_transaction(
            contract_address="",  # IdentityRegistry 合约地址
            method="registerDid",
            params={"did": did, "publicKey": public_key},
        )

    async def mint_nft(
        self,
        asset_id: str,
        category: str,
        level: int,
        evidence_hash: str,
        certificate_uri: str,
    ) -> dict:
        """铸造数据资产 NFT"""
        return await self.send_transaction(
            contract_address="",  # DataAssetNFT 合约地址
            method="mint",
            params={
                "assetId": asset_id,
                "category": category,
                "level": level,
                "evidenceHash": evidence_hash,
                "certificateURI": certificate_uri,
            },
        )

    async def submit_evidence(self, evidence_data: dict) -> dict:
        """提交存证"""
        return await self.send_transaction(
            contract_address="",  # UsageLogger 合约地址
            method="logUsage",
            params=evidence_data,
        )

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None


# 全局客户端实例
fisco_client = FiscoClient()
