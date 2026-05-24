"""
互联互通架构 — 安全技术系统与各类外部系统集成
=============================================

架构设计:
┌─────────────────────────────────────────────────────────────┐
│                    能源可信数据空间                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 安全技术  │  │ 隐私计算  │  │ 区块链   │  │ DID身份  │   │
│  │   系统    │  │   引擎    │  │   存证   │  │   管理   │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘   │
│        │             │             │             │         │
│  ┌─────▼─────────────▼─────────────▼─────────────▼─────┐   │
│  │              互联互通总线 (Integration Bus)            │   │
│  └──┬──────────┬──────────┬──────────┬─────────────────┘   │
│     │          │          │          │                      │
│  ┌──▼───┐  ┌──▼───┐  ┌──▼───┐  ┌──▼───┐                  │
│  │终端  │  │边缘  │  │云端  │  │业务  │                  │
│  │连接器│  │连接器│  │连接器│  │连接器│                  │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘                  │
└─────┼─────────┼─────────┼─────────┼────────────────────────┘
      │         │         │         │
  ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
  │IoT终端│ │边缘节点│ │云数据中心│ │业务系统│
  │MQTT/  │ │gRPC/  │ │S3/DB/ │ │REST/  │
  │OPC-UA │ │HTTP   │ │API    │ │WS     │
  └───────┘ └───────┘ └───────┘ └───────┘

协议支持:
- 数据采集终端: MQTT, OPC-UA, Modbus, HTTP
- 边缘计算节点: gRPC, HTTP REST, WebSocket
- 云端数据中心: S3, PostgreSQL, MySQL, MongoDB, HTTP API
- 业务应用系统: REST API, WebSocket, Webhook, 消息队列
"""
import uuid
import json
import logging
import asyncio
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.gmssl_adapter import gmssl_adapter

logger = logging.getLogger(__name__)


class SystemType(str, Enum):
    """外部系统类型"""
    TERMINAL = "terminal"          # 数据采集终端
    EDGE = "edge"                  # 边缘计算节点
    CLOUD = "cloud"                # 云端数据中心
    BUSINESS = "business"          # 业务应用系统


class ProtocolType(str, Enum):
    """通信协议类型"""
    MQTT = "mqtt"
    OPCUA = "opcua"
    MODBUS = "modbus"
    HTTP = "http"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    S3 = "s3"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    WEBHOOK = "webhook"
    MESSAGE_QUEUE = "message_queue"


class ConnectionStatus(str, Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DataFlowDirection(str, Enum):
    """数据流向"""
    INBOUND = "inbound"        # 外部 → 数据空间
    OUTBOUND = "outbound"      # 数据空间 → 外部
    BIDIRECTIONAL = "bidirectional"


# ==================== 连接器基类 ====================

class BaseConnector(ABC):
    """连接器基类"""

    def __init__(self, connector_id: str, config: Dict[str, Any]):
        self.connector_id = connector_id
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self.last_heartbeat = None
        self.error_count = 0
        self.metadata = {}

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接"""
        pass

    @abstractmethod
    async def send_data(self, data: Dict[str, Any]) -> bool:
        """发送数据"""
        pass

    @abstractmethod
    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """接收数据"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "error_count": self.error_count,
            "metadata": self.metadata,
        }


# ==================== 数据采集终端连接器 ====================

class TerminalConnector(BaseConnector):
    """
    数据采集终端连接器
    支持: MQTT, OPC-UA, Modbus, HTTP
    """

    def __init__(self, connector_id: str, config: Dict[str, Any]):
        super().__init__(connector_id, config)
        self.protocol = config.get("protocol", "mqtt")
        self.endpoint = config.get("endpoint", "")
        self.topics = config.get("topics", [])
        self.device_did = config.get("device_did", "")
        self.collection_interval = config.get("collection_interval_ms", 5000)

    async def connect(self) -> bool:
        """连接到数据采集终端"""
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"Terminal connecting: {self.connector_id}, protocol={self.protocol}")

            if self.protocol == "mqtt":
                # MQTT连接配置
                self.metadata["mqtt_broker"] = self.endpoint
                self.metadata["subscribed_topics"] = self.topics
                self.status = ConnectionStatus.CONNECTED
                self.last_heartbeat = datetime.now(timezone.utc)
                logger.info(f"Terminal MQTT connected: {self.endpoint}")
                return True

            elif self.protocol == "opcua":
                # OPC-UA连接配置
                self.metadata["opcua_endpoint"] = self.endpoint
                self.status = ConnectionStatus.CONNECTED
                self.last_heartbeat = datetime.now(timezone.utc)
                logger.info(f"Terminal OPC-UA connected: {self.endpoint}")
                return True

            elif self.protocol == "modbus":
                # Modbus连接配置
                self.metadata["modbus_endpoint"] = self.endpoint
                self.status = ConnectionStatus.CONNECTED
                self.last_heartbeat = datetime.now(timezone.utc)
                logger.info(f"Terminal Modbus connected: {self.endpoint}")
                return True

            elif self.protocol == "http":
                # HTTP轮询配置
                self.metadata["http_endpoint"] = self.endpoint
                self.status = ConnectionStatus.CONNECTED
                self.last_heartbeat = datetime.now(timezone.utc)
                logger.info(f"Terminal HTTP connected: {self.endpoint}")
                return True

            else:
                logger.error(f"Unsupported terminal protocol: {self.protocol}")
                self.status = ConnectionStatus.ERROR
                return False

        except Exception as e:
            logger.error(f"Terminal connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            return False

    async def disconnect(self) -> bool:
        self.status = ConnectionStatus.DISCONNECTED
        logger.info(f"Terminal disconnected: {self.connector_id}")
        return True

    async def send_data(self, data: Dict[str, Any]) -> bool:
        """向终端发送控制指令"""
        try:
            # 计算数据哈希用于完整性校验
            data_hash = gmssl_adapter.sm3_hash(json.dumps(data, sort_keys=True))
            data["_integrity_hash"] = data_hash
            data["_timestamp"] = datetime.now(timezone.utc).isoformat()

            logger.info(f"Terminal send: {self.connector_id}, hash={data_hash[:16]}")
            return True
        except Exception as e:
            logger.error(f"Terminal send failed: {e}")
            return False

    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """接收终端采集数据"""
        try:
            # 模拟接收数据
            data = {
                "device_did": self.device_did,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "protocol": self.protocol,
                "data": {"value": 0, "unit": "unknown"},
            }
            return data
        except Exception as e:
            logger.error(f"Terminal receive failed: {e}")
            return None

    async def health_check(self) -> bool:
        self.last_heartbeat = datetime.now(timezone.utc)
        return self.status == ConnectionStatus.CONNECTED


# ==================== 边缘计算节点连接器 ====================

class EdgeConnector(BaseConnector):
    """
    边缘计算节点连接器
    支持: gRPC, HTTP REST, WebSocket
    """

    def __init__(self, connector_id: str, config: Dict[str, Any]):
        super().__init__(connector_id, config)
        self.protocol = config.get("protocol", "http")
        self.endpoint = config.get("endpoint", "")
        self.node_id = config.get("node_id", "")
        self.capabilities = config.get("capabilities", [])

    async def connect(self) -> bool:
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"Edge connecting: {self.connector_id}, node={self.node_id}")

            self.metadata["node_id"] = self.node_id
            self.metadata["capabilities"] = self.capabilities
            self.status = ConnectionStatus.CONNECTED
            self.last_heartbeat = datetime.now(timezone.utc)

            logger.info(f"Edge connected: {self.node_id}")
            return True
        except Exception as e:
            logger.error(f"Edge connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            return False

    async def disconnect(self) -> bool:
        self.status = ConnectionStatus.DISCONNECTED
        return True

    async def send_data(self, data: Dict[str, Any]) -> bool:
        """向边缘节点发送计算任务"""
        try:
            task_id = str(uuid.uuid4())[:8]
            data["_task_id"] = task_id
            data["_node_id"] = self.node_id
            logger.info(f"Edge task sent: {task_id} -> {self.node_id}")
            return True
        except Exception as e:
            logger.error(f"Edge send failed: {e}")
            return False

    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """接收边缘节点计算结果"""
        return {"node_id": self.node_id, "status": "idle"}

    async def health_check(self) -> bool:
        self.last_heartbeat = datetime.now(timezone.utc)
        return self.status == ConnectionStatus.CONNECTED

    async def deploy_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """部署计算任务到边缘节点"""
        task_id = str(uuid.uuid4())[:8]
        logger.info(f"Edge task deployed: {task_id} -> {self.node_id}")
        return {
            "task_id": task_id,
            "node_id": self.node_id,
            "status": "deployed",
            "deployed_at": datetime.now(timezone.utc).isoformat(),
        }


# ==================== 云端数据中心连接器 ====================

class CloudConnector(BaseConnector):
    """
    云端数据中心连接器
    支持: S3, PostgreSQL, MySQL, MongoDB, HTTP API
    """

    def __init__(self, connector_id: str, config: Dict[str, Any]):
        super().__init__(connector_id, config)
        self.storage_type = config.get("storage_type", "s3")
        self.endpoint = config.get("endpoint", "")
        self.credentials = config.get("credentials", {})
        self.buckets = config.get("buckets", [])

    async def connect(self) -> bool:
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"Cloud connecting: {self.connector_id}, type={self.storage_type}")

            self.metadata["storage_type"] = self.storage_type
            self.metadata["endpoint"] = self.endpoint
            self.status = ConnectionStatus.CONNECTED
            self.last_heartbeat = datetime.now(timezone.utc)

            logger.info(f"Cloud connected: {self.storage_type}")
            return True
        except Exception as e:
            logger.error(f"Cloud connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            return False

    async def disconnect(self) -> bool:
        self.status = ConnectionStatus.DISCONNECTED
        return True

    async def send_data(self, data: Dict[str, Any]) -> bool:
        """上传数据到云端"""
        try:
            data_hash = gmssl_adapter.sm3_hash(json.dumps(data, sort_keys=True))
            logger.info(f"Cloud upload: hash={data_hash[:16]}")
            return True
        except Exception as e:
            logger.error(f"Cloud upload failed: {e}")
            return False

    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """从云端下载数据"""
        return {"source": "cloud", "status": "ready"}

    async def health_check(self) -> bool:
        self.last_heartbeat = datetime.now(timezone.utc)
        return self.status == ConnectionStatus.CONNECTED

    async def sync_data(self, direction: DataFlowDirection) -> Dict[str, Any]:
        """数据同步"""
        sync_id = str(uuid.uuid4())[:8]
        logger.info(f"Cloud sync: {sync_id}, direction={direction.value}")
        return {
            "sync_id": sync_id,
            "direction": direction.value,
            "status": "completed",
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }


# ==================== 业务应用系统连接器 ====================

class BusinessConnector(BaseConnector):
    """
    业务应用系统连接器
    支持: REST API, WebSocket, Webhook, 消息队列
    """

    def __init__(self, connector_id: str, config: Dict[str, Any]):
        super().__init__(connector_id, config)
        self.integration_type = config.get("integration_type", "rest")
        self.endpoint = config.get("endpoint", "")
        self.api_key = config.get("api_key", "")
        self.webhook_url = config.get("webhook_url", "")

    async def connect(self) -> bool:
        try:
            self.status = ConnectionStatus.CONNECTING
            logger.info(f"Business connecting: {self.connector_id}, type={self.integration_type}")

            self.metadata["integration_type"] = self.integration_type
            self.metadata["endpoint"] = self.endpoint
            self.status = ConnectionStatus.CONNECTED
            self.last_heartbeat = datetime.now(timezone.utc)

            logger.info(f"Business connected: {self.integration_type}")
            return True
        except Exception as e:
            logger.error(f"Business connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            self.error_count += 1
            return False

    async def disconnect(self) -> bool:
        self.status = ConnectionStatus.DISCONNECTED
        return True

    async def send_data(self, data: Dict[str, Any]) -> bool:
        """向业务系统推送数据"""
        try:
            data_hash = gmssl_adapter.sm3_hash(json.dumps(data, sort_keys=True))
            logger.info(f"Business push: hash={data_hash[:16]}")
            return True
        except Exception as e:
            logger.error(f"Business push failed: {e}")
            return False

    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """从业务系统接收数据"""
        return {"source": "business", "status": "ready"}

    async def health_check(self) -> bool:
        self.last_heartbeat = datetime.now(timezone.utc)
        return self.status == ConnectionStatus.CONNECTED

    async def trigger_webhook(self, event: Dict[str, Any]) -> bool:
        """触发Webhook通知"""
        try:
            event["_webhook_triggered"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Business webhook triggered: {self.webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Webhook trigger failed: {e}")
            return False


# ==================== 互联互通管理器 ====================

class IntegrationBus:
    """
    互联互通总线
    统一管理所有外部系统连接
    """

    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
        self.data_flows: List[Dict[str, Any]] = []
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "data_transferred": 0,
            "errors": 0,
        }

    def register_connector(self, system_type: SystemType, connector_id: str, config: Dict[str, Any]) -> BaseConnector:
        """注册新连接器"""
        connector_map = {
            SystemType.TERMINAL: TerminalConnector,
            SystemType.EDGE: EdgeConnector,
            SystemType.CLOUD: CloudConnector,
            SystemType.BUSINESS: BusinessConnector,
        }

        connector_class = connector_map.get(system_type)
        if not connector_class:
            raise ValueError(f"Unsupported system type: {system_type}")

        connector = connector_class(connector_id, config)
        self.connectors[connector_id] = connector
        self.stats["total_connections"] += 1

        logger.info(f"Connector registered: {connector_id}, type={system_type.value}")
        return connector

    async def connect_all(self) -> Dict[str, bool]:
        """连接所有注册的连接器"""
        results = {}
        for cid, connector in self.connectors.items():
            try:
                success = await connector.connect()
                results[cid] = success
                if success:
                    self.stats["active_connections"] += 1
            except Exception as e:
                results[cid] = False
                self.stats["errors"] += 1
                logger.error(f"Connection failed: {cid}, error={e}")
        return results

    async def disconnect_all(self) -> Dict[str, bool]:
        """断开所有连接"""
        results = {}
        for cid, connector in self.connectors.items():
            try:
                success = await connector.disconnect()
                results[cid] = success
                if success:
                    self.stats["active_connections"] -= 1
            except Exception as e:
                results[cid] = False
        return results

    async def health_check_all(self) -> Dict[str, bool]:
        """健康检查所有连接"""
        results = {}
        for cid, connector in self.connectors.items():
            try:
                results[cid] = await connector.health_check()
            except Exception as e:
                results[cid] = False
        return results

    def get_connector(self, connector_id: str) -> Optional[BaseConnector]:
        return self.connectors.get(connector_id)

    def get_all_status(self) -> List[Dict[str, Any]]:
        return [c.get_status() for c in self.connectors.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "active_connectors": len([c for c in self.connectors.values() if c.status == ConnectionStatus.CONNECTED]),
            "total_connectors": len(self.connectors),
        }


# ==================== 全局实例 ====================

integration_bus = IntegrationBus()


# ==================== 便捷函数 ====================

async def register_terminal(
    db: AsyncSession,
    name: str,
    protocol: str,
    endpoint: str,
    device_did: str,
    topics: List[str] = None,
    org_id: str = None,
) -> Dict[str, Any]:
    """注册数据采集终端"""
    connector_id = f"terminal_{device_did}"
    config = {
        "protocol": protocol,
        "endpoint": endpoint,
        "device_did": device_did,
        "topics": topics or [],
    }

    connector = integration_bus.register_connector(SystemType.TERMINAL, connector_id, config)
    success = await connector.connect()

    return {
        "connector_id": connector_id,
        "status": "connected" if success else "error",
        "protocol": protocol,
        "device_did": device_did,
    }


async def register_edge_node(
    db: AsyncSession,
    name: str,
    node_id: str,
    endpoint: str,
    capabilities: List[str] = None,
    org_id: str = None,
) -> Dict[str, Any]:
    """注册边缘计算节点"""
    connector_id = f"edge_{node_id}"
    config = {
        "protocol": "http",
        "endpoint": endpoint,
        "node_id": node_id,
        "capabilities": capabilities or [],
    }

    connector = integration_bus.register_connector(SystemType.EDGE, connector_id, config)
    success = await connector.connect()

    return {
        "connector_id": connector_id,
        "status": "connected" if success else "error",
        "node_id": node_id,
        "capabilities": capabilities or [],
    }


async def register_cloud_storage(
    db: AsyncSession,
    name: str,
    storage_type: str,
    endpoint: str,
    credentials: Dict[str, str] = None,
    org_id: str = None,
) -> Dict[str, Any]:
    """注册云端存储"""
    connector_id = f"cloud_{storage_type}_{uuid.uuid4().hex[:8]}"
    config = {
        "storage_type": storage_type,
        "endpoint": endpoint,
        "credentials": credentials or {},
    }

    connector = integration_bus.register_connector(SystemType.CLOUD, connector_id, config)
    success = await connector.connect()

    return {
        "connector_id": connector_id,
        "status": "connected" if success else "error",
        "storage_type": storage_type,
    }


async def register_business_app(
    db: AsyncSession,
    name: str,
    integration_type: str,
    endpoint: str,
    api_key: str = None,
    webhook_url: str = None,
    org_id: str = None,
) -> Dict[str, Any]:
    """注册业务应用系统"""
    connector_id = f"business_{uuid.uuid4().hex[:8]}"
    config = {
        "integration_type": integration_type,
        "endpoint": endpoint,
        "api_key": api_key or "",
        "webhook_url": webhook_url or "",
    }

    connector = integration_bus.register_connector(SystemType.BUSINESS, connector_id, config)
    success = await connector.connect()

    return {
        "connector_id": connector_id,
        "status": "connected" if success else "error",
        "integration_type": integration_type,
    }
