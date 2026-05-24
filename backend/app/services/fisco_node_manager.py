"""
FISCO BCOS 节点管理器
节点健康检查 / 负载均衡 / 故障转移
"""
import asyncio
import logging
import time
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from app.services.fisco_channel_client import (
    FiscoChannelClient,
    FiscoChannelConfig,
    get_fisco_channel_client,
)

logger = logging.getLogger(__name__)


class NodeStatus(str, Enum):
    """节点状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class NodeHealthInfo:
    """节点健康信息"""
    host: str
    port: int
    status: NodeStatus = NodeStatus.UNKNOWN
    block_number: int = 0
    peer_count: int = 0
    latency_ms: float = 0.0
    last_check: float = 0.0
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0

    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.total_checks == 0:
            return 0.0
        return self.total_failures / self.total_checks

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "status": self.status.value,
            "block_number": self.block_number,
            "peer_count": self.peer_count,
            "latency_ms": round(self.latency_ms, 2),
            "last_check": self.last_check,
            "consecutive_failures": self.consecutive_failures,
            "error_rate": round(self.error_rate, 4),
        }


class FiscoNodeManager:
    """
    FISCO BCOS 节点管理器

    功能:
    1. 节点健康检查 — 定期 ping 各节点，记录延迟和区块高度
    2. 节点负载均衡 — 按延迟和健康状态选择最优节点
    3. 节点故障转移 — 自动将请求切换到可用节点
    4. 节点动态管理 — 添加/移除运行时节点
    """

    # 健康检查阈值
    MAX_CONSECUTIVE_FAILURES: int = 3
    LATENCY_WARNING_MS: float = 500.0
    LATENCY_ERROR_MS: float = 2000.0

    def __init__(self, client: Optional[FiscoChannelClient] = None):
        """
        初始化节点管理器

        Args:
            client: FiscoChannelClient 实例，为 None 时获取全局单例
        """
        self._client = client or get_fisco_channel_client()
        self._node_health: dict[str, NodeHealthInfo] = {}
        self._health_check_active: bool = False
        self._health_check_interval: float = 30.0
        self._health_check_task: Optional[asyncio.Task] = None

        # 初始化节点健康信息
        self._init_node_health()

    def _init_node_health(self) -> None:
        """从客户端配置初始化节点健康信息"""
        for node in self._client.config.nodes:
            key = f"{node['host']}:{node['port']}"
            self._node_health[key] = NodeHealthInfo(
                host=node["host"],
                port=node["port"],
            )

    def _node_key(self, host: str, port: int) -> str:
        """生成节点键名"""
        return f"{host}:{port}"

    # ==================== 节点管理 ====================

    def add_node(self, host: str, port: int) -> bool:
        """
        添加节点

        Args:
            host: 节点地址
            port: 节点端口

        Returns:
            是否添加成功
        """
        key = self._node_key(host, port)
        if key in self._node_health:
            logger.warning(f"节点 {key} 已存在")
            return False

        # 添加到客户端配置
        new_node = {"host": host, "port": port, "cert_node": f"node{len(self._client.config.nodes)}"}
        self._client.config.nodes.append(new_node)

        # 添加健康记录
        self._node_health[key] = NodeHealthInfo(host=host, port=port)
        logger.info(f"已添加节点: {key}")
        return True

    def remove_node(self, host: str, port: int) -> bool:
        """
        移除节点

        Args:
            host: 节点地址
            port: 节点端口

        Returns:
            是否移除成功
        """
        key = self._node_key(host, port)

        # 不允许移除到最后一个
        if len(self._client.config.nodes) <= 1:
            logger.error("不能移除最后一个节点")
            return False

        # 从客户端配置中移除
        for i, node in enumerate(self._client.config.nodes):
            if node["host"] == host and node["port"] == port:
                self._client.config.nodes.pop(i)
                # 调整当前节点索引
                if self._client._current_node_index >= len(self._client.config.nodes):
                    self._client._current_node_index = 0
                break
        else:
            logger.warning(f"节点 {key} 未找到")
            return False

        # 移除健康记录
        self._node_health.pop(key, None)
        logger.info(f"已移除节点: {key}")
        return True

    def get_node_list(self) -> list[dict]:
        """
        获取所有节点列表及其健康状态

        Returns:
            节点信息列表
        """
        nodes = []
        for node in self._client.config.nodes:
            key = self._node_key(node["host"], node["port"])
            health = self._node_health.get(key)
            node_info = {
                "host": node["host"],
                "port": node["port"],
                "cert_node": node.get("cert_node", ""),
                "is_current": key == self._node_key(
                    self._client.config.nodes[self._client._current_node_index]["host"],
                    self._client.config.nodes[self._client._current_node_index]["port"],
                ),
            }
            if health:
                node_info.update(health.to_dict())
            else:
                node_info["status"] = NodeStatus.UNKNOWN.value
            nodes.append(node_info)
        return nodes

    # ==================== 健康检查 ====================

    async def check_node_health(self, host: str, port: int) -> NodeHealthInfo:
        """
        检查单个节点健康状态

        Args:
            host: 节点地址
            port: 节点端口

        Returns:
            节点健康信息
        """
        key = self._node_key(host, port)
        health = self._node_health.get(key)
        if not health:
            health = NodeHealthInfo(host=host, port=port)
            self._node_health[key] = health

        import httpx
        start_time = time.monotonic()

        try:
            url = f"http://{host}:{port}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 发送 getClientVersion 探测请求
                payload = {
                    "jsonrpc": "2.0",
                    "method": "getClientVersion",
                    "params": [],
                    "id": 1,
                }
                response = await client.post(url, json=payload)
                response.raise_for_status()

                elapsed_ms = (time.monotonic() - start_time) * 1000
                health.latency_ms = elapsed_ms
                health.total_checks += 1
                health.consecutive_failures = 0
                health.last_check = time.time()

                # 设置状态
                if elapsed_ms < self.LATENCY_WARNING_MS:
                    health.status = NodeStatus.ONLINE
                elif elapsed_ms < self.LATENCY_ERROR_MS:
                    health.status = NodeStatus.DEGRADED
                else:
                    health.status = NodeStatus.DEGRADED

                # 尝试获取区块高度和节点数
                try:
                    block_payload = {
                        "jsonrpc": "2.0",
                        "method": "getBlockNumber",
                        "params": [self._client.config.group_id],
                        "id": 2,
                    }
                    block_resp = await client.post(url, json=block_payload)
                    if block_resp.status_code == 200:
                        block_result = block_resp.json().get("result", "0x0")
                        health.block_number = int(block_result, 16) if isinstance(block_result, str) else int(block_result)
                except Exception:
                    pass

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            health.latency_ms = elapsed_ms
            health.total_checks += 1
            health.total_failures += 1
            health.consecutive_failures += 1
            health.last_check = time.time()

            if health.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                health.status = NodeStatus.OFFLINE
            else:
                health.status = NodeStatus.DEGRADED

            logger.warning(f"节点健康检查失败 {key}: {e}")

        return health

    async def check_all_nodes(self) -> dict[str, NodeHealthInfo]:
        """
        检查所有节点健康状态

        Returns:
            节点键 → 健康信息
        """
        tasks = []
        for node in self._client.config.nodes:
            tasks.append(
                self.check_node_health(node["host"], node["port"])
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_map = {}
        for i, result in enumerate(results):
            node = self._client.config.nodes[i]
            key = self._node_key(node["host"], node["port"])
            if isinstance(result, Exception):
                logger.error(f"节点健康检查异常 {key}: {result}")
            else:
                health_map[key] = result

        return health_map

    async def start_health_check(self, interval: float = 30.0) -> None:
        """
        启动定期健康检查

        Args:
            interval: 检查间隔（秒）
        """
        self._health_check_active = True
        self._health_check_interval = interval

        async def _health_check_loop():
            logger.info(f"节点健康检查已启动，间隔 {interval}s")
            while self._health_check_active:
                try:
                    await self.check_all_nodes()
                    # 检查后自动执行故障转移
                    await self._auto_failover()
                except Exception as e:
                    logger.error(f"健康检查循环异常: {e}")
                await asyncio.sleep(self._health_check_interval)

        self._health_check_task = asyncio.create_task(_health_check_loop())

    async def stop_health_check(self) -> None:
        """停止健康检查"""
        self._health_check_active = False
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("节点健康检查已停止")

    # ==================== 负载均衡 ====================

    def select_best_node(self) -> Optional[dict]:
        """
        选择最优节点

        策略：在在线节点中选择延迟最低的节点。
        如果所有节点都不健康，则选择连续失败次数最少的。

        Returns:
            节点信息字典，如果无可用节点则返回 None
        """
        online_nodes = []
        degraded_nodes = []

        for node in self._client.config.nodes:
            key = self._node_key(node["host"], node["port"])
            health = self._node_health.get(key)
            if not health:
                continue

            if health.status == NodeStatus.ONLINE:
                online_nodes.append((node, health))
            elif health.status == NodeStatus.DEGRADED:
                degraded_nodes.append((node, health))

        # 优先选择在线节点中延迟最低的
        if online_nodes:
            online_nodes.sort(key=lambda x: x[1].latency_ms)
            best = online_nodes[0][0]
            logger.debug(f"选择最优在线节点: {best['host']}:{best['port']}")
            return best

        # 次选降级节点
        if degraded_nodes:
            degraded_nodes.sort(key=lambda x: x[1].consecutive_failures)
            best = degraded_nodes[0][0]
            logger.warning(f"所有节点降级，选择: {best['host']}:{best['port']}")
            return best

        logger.error("无可用节点")
        return None

    # ==================== 故障转移 ====================

    async def _auto_failover(self) -> None:
        """
        自动故障转移

        如果当前节点不健康，自动切换到最优节点
        """
        current_node = self._client.config.nodes[self._client._current_node_index]
        current_key = self._node_key(current_node["host"], current_node["port"])
        current_health = self._node_health.get(current_key)

        if current_health and current_health.status == NodeStatus.OFFLINE:
            logger.warning(f"当前节点 {current_key} 已离线，执行故障转移")
            best = self.select_best_node()
            if best:
                # 找到最优节点在列表中的索引
                for i, node in enumerate(self._client.config.nodes):
                    if node["host"] == best["host"] and node["port"] == best["port"]:
                        self._client._current_node_index = i
                        self._client._connected = True
                        logger.info(f"故障转移到节点: {best['host']}:{best['port']}")
                        break

    def force_failover(self, host: str, port: int) -> bool:
        """
        强制切换到指定节点

        Args:
            host: 目标节点地址
            port: 目标节点端口

        Returns:
            是否切换成功
        """
        for i, node in enumerate(self._client.config.nodes):
            if node["host"] == host and node["port"] == port:
                self._client._current_node_index = i
                self._client._connected = True
                logger.info(f"强制切换到节点: {host}:{port}")
                return True

        logger.error(f"节点 {host}:{port} 未找到")
        return False

    # ==================== 状态查询 ====================

    def get_health_summary(self) -> dict:
        """
        获取所有节点健康状态摘要

        Returns:
            { total, online, offline, degraded, nodes: [...] }
        """
        nodes = []
        online_count = 0
        offline_count = 0
        degraded_count = 0

        for key, health in self._node_health.items():
            nodes.append(health.to_dict())
            if health.status == NodeStatus.ONLINE:
                online_count += 1
            elif health.status == NodeStatus.OFFLINE:
                offline_count += 1
            elif health.status == NodeStatus.DEGRADED:
                degraded_count += 1

        return {
            "total": len(self._node_health),
            "online": online_count,
            "offline": offline_count,
            "degraded": degraded_count,
            "health_check_active": self._health_check_active,
            "current_node": self._client.base_url,
            "nodes": nodes,
        }


# 全局节点管理器实例
_node_manager: Optional[FiscoNodeManager] = None


def get_fisco_node_manager(
    client: Optional[FiscoChannelClient] = None,
) -> FiscoNodeManager:
    """
    获取节点管理器单例

    Args:
        client: FiscoChannelClient 实例

    Returns:
        FiscoNodeManager 实例
    """
    global _node_manager
    if _node_manager is None:
        _node_manager = FiscoNodeManager(client)
    return _node_manager
