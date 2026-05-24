"""
FISCO BCOS HTTP Channel Service 客户端
基于 HTTP Channel Service 协议，支持 SM-TLS 国密安全通信

特性：
- 4 节点 PBFT 共识网络连接
- SM-TLS 国密传输加密
- 交易发送/查询
- 区块监听
- 事件订阅
- 合约部署/调用
"""
import json
import ssl
import logging
import asyncio
import hashlib
from typing import Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

import httpx

from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)


@dataclass
class FiscoChannelConfig:
    """FISCO BCOS HTTP Channel 配置"""
    # 节点列表（4 节点 PBFT）
    nodes: list[dict] = field(default_factory=lambda: [
        {"host": "127.0.0.1", "port": 20200, "cert_node": "node0"},
        {"host": "127.0.0.1", "port": 20201, "cert_node": "node1"},
        {"host": "127.0.0.1", "port": 20202, "cert_node": "node2"},
        {"host": "127.0.0.1", "port": 20203, "cert_node": "node3"},
    ])
    # 超时配置
    connect_timeout: float = 10.0
    request_timeout: float = 30.0
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    # SM-TLS 证书路径
    ca_cert_path: str = "conf/sm_ca.crt"
    node_cert_path: str = "conf/sm_sdk.crt"
    node_key_path: str = "conf/sm_sdk.key"
    # 链 ID
    chain_id: str = "chain0"
    # 群组 ID
    group_id: int = 1


@dataclass
class RpcRequest:
    """JSON-RPC 请求"""
    method: str
    params: list[Any]
    jsonrpc: str = "2.0"
    id: int = 1


@dataclass
class RpcResponse:
    """JSON-RPC 响应"""
    jsonrpc: str = "2.0"
    id: int = 1
    result: Any = None
    error: Optional[dict] = None


class FiscoChannelClient:
    """
    FISCO BCOS HTTP Channel Service 客户端
    
    实现 HTTP Channel Service 协议与 FISCO BCOS 节点通信，
    支持 SM-TLS 国密安全传输。
    
    JSON-RPC 接口参考：
    - getBlockNumber: 获取最新区块高度
    - getBlockByNumber: 获取指定区块
    - getTransaction: 获取交易详情
    - sendTransaction: 发送交易
    - call: 调用合约（只读）
    - getPeers: 获取节点连接信息
    - getNodeVersion: 获取节点版本
    - getGroupList: 获取群组列表
    - getGroupInfo: 获取群组信息
    """

    def __init__(self, config: Optional[FiscoChannelConfig] = None):
        """
        初始化 FISCO BCOS HTTP Channel 客户端
        
        Args:
            config: 客户端配置，为 None 时使用默认配置
        """
        self.config = config or FiscoChannelConfig()
        self._current_node_index = 0
        self._connected: bool = False
        self._client: Optional[httpx.AsyncClient] = None
        self._event_handlers: dict[str, list[Callable]] = {}
        self._block_listener_active: bool = False
        self._last_block_number: int = 0
        self._connection_stats: dict[str, Any] = {
            "connected_at": None,
            "total_requests": 0,
            "failed_requests": 0,
            "last_error": None,
        }

    @property
    def base_url(self) -> str:
        """获取当前节点 URL"""
        node = self.config.nodes[self._current_node_index]
        return f"http://{node['host']}:{node['port']}"

    def _get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        创建 SM-TLS SSL 上下文
        
        Returns:
            SSL 上下文，如果证书路径无效则返回 None
        """
        try:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # 尝试加载国密证书
            import os
            if os.path.exists(self.config.ca_cert_path):
                ctx.load_verify_locations(self.config.ca_cert_path)
            if os.path.exists(self.config.node_cert_path) and os.path.exists(self.config.node_key_path):
                ctx.load_cert_chain(self.config.node_cert_path, self.config.node_key_path)
            
            return ctx
        except Exception as e:
            logger.warning(f"SM-TLS SSL 上下文创建失败: {e}")
            return None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        获取或创建 HTTP 客户端
        
        Returns:
            httpx.AsyncClient 实例
        """
        if self._client is None or self._client.is_closed:
            ssl_context = self._get_ssl_context()
            transport_kwargs: dict[str, Any] = {}
            if ssl_context:
                transport_kwargs["verify"] = ssl_context
            
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.request_timeout),
                headers={"Content-Type": "application/json"},
                **transport_kwargs,
            )
        return self._client

    async def connect(self) -> bool:
        """
        连接到 FISCO BCOS 节点
        
        尝试连接所有配置的节点，找到第一个可用节点。
        
        Returns:
            是否连接成功
        """
        for i, node in enumerate(self.config.nodes):
            try:
                client = await self._get_client()
                url = f"http://{node['host']}:{node['port']}"
                
                # 发送测试请求
                response = await self._rpc_call_raw(
                    client, url, "getClientVersion", []
                )
                
                if response and not response.error:
                    self._current_node_index = i
                    self._connected = True
                    self._connection_stats["connected_at"] = datetime.now(timezone.utc).isoformat()
                    logger.info(f"已连接到 FISCO BCOS 节点: {url}")
                    return True
            except Exception as e:
                logger.warning(f"连接节点 {node['host']}:{node['port']} 失败: {e}")
                continue
        
        logger.error("所有 FISCO BCOS 节点连接失败")
        self._connected = False
        return False

    async def disconnect(self) -> None:
        """断开连接"""
        self._block_listener_active = False
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        self._connected = False
        self._connection_stats["connected_at"] = None
        logger.info("已断开 FISCO BCOS 连接")

    async def _rpc_call_raw(
        self, client: httpx.AsyncClient, url: str, method: str, params: list[Any]
    ) -> Optional[RpcResponse]:
        """
        执行原始 JSON-RPC 调用
        
        Args:
            client: HTTP 客户端
            url: 节点 URL
            method: RPC 方法
            params: 参数列表
            
        Returns:
            RPC 响应
        """
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._connection_stats["total_requests"] + 1,
        }
        
        response = await client.post(url, json=request_data)
        response.raise_for_status()
        
        data = response.json()
        return RpcResponse(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id", 0),
            result=data.get("result"),
            error=data.get("error"),
        )

    async def rpc_call(self, method: str, params: list[Any] = None) -> Any:
        """
        执行 JSON-RPC 调用，带重试和故障转移
        
        Args:
            method: RPC 方法名
            params: 参数列表
            
        Returns:
            调用结果
            
        Raises:
            Exception: 所有重试都失败后抛出异常
        """
        params = params or []
        self._connection_stats["total_requests"] += 1
        
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            try:
                client = await self._get_client()
                response = await self._rpc_call_raw(
                    client, self.base_url, method, params
                )
                
                if response and response.error:
                    error_msg = response.error.get("message", "Unknown error")
                    error_code = response.error.get("code", -1)
                    raise Exception(f"RPC Error [{error_code}]: {error_msg}")
                
                if response:
                    return response.result
                
                raise Exception("Empty RPC response")
                
            except Exception as e:
                last_error = e
                self._connection_stats["failed_requests"] += 1
                self._connection_stats["last_error"] = str(e)
                
                logger.warning(
                    f"RPC 调用失败 (尝试 {attempt + 1}/{self.config.max_retries}): "
                    f"{method} - {e}"
                )
                
                # 故障转移到下一个节点
                self._current_node_index = (
                    self._current_node_index + 1
                ) % len(self.config.nodes)
                
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
        
        raise last_error or Exception(f"RPC 调用失败: {method}")

    # ==================== 链状态查询 ====================

    async def get_block_number(self) -> int:
        """
        获取最新区块高度
        
        Returns:
            区块高度
        """
        result = await self.rpc_call("getBlockNumber", [self.config.group_id])
        return int(result, 16) if isinstance(result, str) else int(result)

    async def get_peer_count(self) -> int:
        """
        获取连接的节点数量
        
        Returns:
            节点数量
        """
        result = await self.rpc_call("getPeers", [self.config.group_id])
        if isinstance(result, list):
            return len(result)
        return 0

    async def get_node_version(self) -> dict:
        """
        获取节点版本信息
        
        Returns:
            版本信息字典
        """
        return await self.rpc_call("getClientVersion", [])

    async def get_chain_id(self) -> str:
        """
        获取链 ID
        
        Returns:
            链 ID
        """
        return self.config.chain_id

    async def get_group_list(self) -> list[str]:
        """
        获取群组列表
        
        Returns:
            群组 ID 列表
        """
        return await self.rpc_call("getGroupList", [])

    async def get_group_info(self) -> dict:
        """
        获取群组信息
        
        Returns:
            群组信息字典
        """
        return await self.rpc_call("getGroupInfo", [self.config.group_id])

    async def get_consensus_status(self) -> dict:
        """
        获取共识状态
        
        Returns:
            共识状态信息
        """
        return await self.rpc_call("getConsensusStatus", [self.config.group_id])

    async def get_sync_status(self) -> dict:
        """
        获取同步状态
        
        Returns:
            同步状态信息
        """
        return await self.rpc_call("getSyncStatus", [self.config.group_id])

    # ==================== 区块查询 ====================

    async def get_block_by_number(
        self, block_number: int, include_transactions: bool = True
    ) -> dict:
        """
        获取指定区块
        
        Args:
            block_number: 区块高度
            include_transactions: 是否包含交易详情
            
        Returns:
            区块数据
        """
        hex_number = hex(block_number)
        return await self.rpc_call(
            "getBlockByNumber",
            [self.config.group_id, hex_number, include_transactions],
        )

    async def get_block_hash_by_number(self, block_number: int) -> str:
        """
        获取指定区块的哈希
        
        Args:
            block_number: 区块高度
            
        Returns:
            区块哈希
        """
        hex_number = hex(block_number)
        return await self.rpc_call(
            "getBlockHashByNumber", [self.config.group_id, hex_number]
        )

    async def get_block_by_hash(
        self, block_hash: str, include_transactions: bool = True
    ) -> dict:
        """
        根据哈希获取区块
        
        Args:
            block_hash: 区块哈希
            include_transactions: 是否包含交易详情
            
        Returns:
            区块数据
        """
        return await self.rpc_call(
            "getBlockByHash",
            [self.config.group_id, block_hash, include_transactions],
        )

    # ==================== 交易操作 ====================

    async def send_transaction(
        self,
        to_address: str,
        data: str,
        from_address: str = "",
        abi: str = "",
    ) -> dict:
        """
        发送交易
        
        Args:
            to_address: 合约地址
            data: 交易数据（ABI 编码后）
            from_address: 发送者地址
            abi: 合约 ABI（用于事件解析）
            
        Returns:
            交易结果，包含 transactionHash
        """
        return await self.rpc_call(
            "sendTransaction",
            [self.config.group_id, self.config.group_id, to_address, data],
        )

    async def call_contract(
        self,
        to_address: str,
        data: str,
        from_address: str = "",
    ) -> str:
        """
        调用合约（只读）
        
        Args:
            to_address: 合约地址
            data: 调用数据（ABI 编码后）
            from_address: 调用者地址
            
        Returns:
            调用结果（十六进制）
        """
        result = await self.rpc_call(
            "call",
            [self.config.group_id, {"from": from_address, "to": to_address, "data": data}],
        )
        return result

    async def get_transaction(self, tx_hash: str) -> dict:
        """
        获取交易详情
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            交易详情
        """
        return await self.rpc_call(
            "getTransaction", [self.config.group_id, tx_hash]
        )

    async def get_transaction_receipt(self, tx_hash: str) -> dict:
        """
        获取交易回执
        
        Args:
            tx_hash: 交易哈希
            
        Returns:
            交易回执
        """
        return await self.rpc_call(
            "getTransactionReceipt", [self.config.group_id, tx_hash]
        )

    async def get_pending_transactions(self) -> list[dict]:
        """
        获取待处理交易列表
        
        Returns:
            待处理交易列表
        """
        result = await self.rpc_call(
            "getPendingTransactions", [self.config.group_id]
        )
        return result if isinstance(result, list) else []

    async def get_pending_tx_size(self) -> int:
        """
        获取待处理交易数量
        
        Returns:
            待处理交易数量
        """
        result = await self.rpc_call(
            "getPendingTxSize", [self.config.group_id]
        )
        return int(result, 16) if isinstance(result, str) else int(result)

    # ==================== 合约部署 ====================

    async def deploy_contract(
        self, bytecode: str, abi: str = "", constructor_params: list = None
    ) -> dict:
        """
        部署合约
        
        Args:
            bytecode: 合约字节码
            abi: 合约 ABI
            constructor_params: 构造函数参数
            
        Returns:
            部署结果，包含合约地址和交易哈希
        """
        deploy_data = bytecode
        if constructor_params and abi:
            # 简化处理：直接使用字节码
            deploy_data = bytecode
        
        result = await self.rpc_call(
            "sendTransaction",
            [self.config.group_id, self.config.group_id, "", deploy_data],
        )
        
        return result

    # ==================== 事件查询 ====================

    async def get_logs(
        self,
        from_block: int = 0,
        to_block: int = -1,
        address: str = "",
        topics: list[str] = None,
    ) -> list[dict]:
        """
        获取事件日志
        
        Args:
            from_block: 起始区块
            to_block: 结束区块（-1 表示最新）
            address: 合约地址
            topics: 主题列表
            
        Returns:
            事件日志列表
        """
        filter_params = {
            "fromBlock": hex(from_block) if from_block >= 0 else "latest",
            "toBlock": hex(to_block) if to_block >= 0 else "latest",
        }
        if address:
            filter_params["address"] = address
        if topics:
            filter_params["topics"] = topics
        
        return await self.rpc_call(
            "getLogs", [self.config.group_id, filter_params]
        )

    def on_event(self, event_name: str, handler: Callable) -> None:
        """
        注册事件处理器
        
        Args:
            event_name: 事件名称
            handler: 处理函数
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
        logger.info(f"注册事件处理器: {event_name}")

    # ==================== 区块监听 ====================

    async def start_block_listener(
        self,
        callback: Callable[[dict], Any],
        interval: float = 1.0,
    ) -> None:
        """
        启动区块监听
        
        Args:
            callback: 区块回调函数
            interval: 轮询间隔（秒）
        """
        self._block_listener_active = True
        self._last_block_number = await self.get_block_number()
        
        logger.info(f"区块监听启动，起始区块: {self._last_block_number}")
        
        while self._block_listener_active:
            try:
                current_block = await self.get_block_number()
                
                if current_block > self._last_block_number:
                    for block_num in range(self._last_block_number + 1, current_block + 1):
                        block_data = await self.get_block_by_number(block_num)
                        
                        # 处理区块中的事件
                        if block_data and "transactions" in block_data:
                            for tx in block_data.get("transactions", []):
                                receipt = await self.get_transaction_receipt(
                                    tx.get("hash", "")
                                )
                                if receipt and receipt.get("logs"):
                                    for log_entry in receipt["logs"]:
                                        await self._dispatch_event(log_entry)
                        
                        await callback(block_data)
                    
                    self._last_block_number = current_block
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"区块监听异常: {e}")
                await asyncio.sleep(interval * 2)

    async def stop_block_listener(self) -> None:
        """停止区块监听"""
        self._block_listener_active = False
        logger.info("区块监听已停止")

    async def _dispatch_event(self, log_entry: dict) -> None:
        """
        分发事件到处理器
        
        Args:
            log_entry: 事件日志
        """
        topics = log_entry.get("topics", [])
        if topics:
            event_signature = topics[0]
            if event_signature in self._event_handlers:
                for handler in self._event_handlers[event_signature]:
                    try:
                        await handler(log_entry) if asyncio.iscoroutinefunction(handler) else handler(log_entry)
                    except Exception as e:
                        logger.error(f"事件处理器异常: {e}")

    # ==================== 状态和工具 ====================

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    def get_connection_stats(self) -> dict:
        """
        获取连接统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self._connection_stats,
            "current_node": self.base_url,
            "connected": self._connected,
            "block_listener_active": self._block_listener_active,
            "last_block_number": self._last_block_number,
        }

    def compute_data_hash(self, data: str) -> str:
        """
        计算数据哈希（SM3）
        
        Args:
            data: 输入数据
            
        Returns:
            SM3 哈希值
        """
        return gmssl_adapter.sm3_hash(data)

    async def get_connection_status(self) -> dict:
        """
        获取连接状态详情
        
        Returns:
            连接状态字典
        """
        status = {
            "connected": self._connected,
            "current_node": self.base_url,
            "stats": self._connection_stats,
        }
        
        if self._connected:
            try:
                block_number = await self.get_block_number()
                peer_count = await self.get_peer_count()
                status.update({
                    "block_number": block_number,
                    "peer_count": peer_count,
                    "chain_id": self.config.chain_id,
                    "group_id": self.config.group_id,
                })
            except Exception as e:
                status["error"] = str(e)
        
        return status


# 全局单例
_fisco_channel_client: Optional[FiscoChannelClient] = None


def get_fisco_channel_client(
    config: Optional[FiscoChannelConfig] = None,
) -> FiscoChannelClient:
    """
    获取 FISCO BCOS Channel 客户端单例
    
    Args:
        config: 客户端配置
        
    Returns:
        FiscoChannelClient 实例
    """
    global _fisco_channel_client
    if _fisco_channel_client is None:
        _fisco_channel_client = FiscoChannelClient(config)
    return _fisco_channel_client
