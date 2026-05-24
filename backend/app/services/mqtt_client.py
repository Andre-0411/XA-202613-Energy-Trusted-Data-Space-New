"""
MQTT 客户端管理器
负责与 EMQX 的连接、订阅和消息发布
支持配置 broker host/port/topic
"""
import logging
import re
from typing import Optional, Callable
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from app.config import settings

logger = logging.getLogger(__name__)


class MQTTManager:
    """MQTT 连接管理器"""

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self._connected = False
        self._callbacks: dict[str, list[Callable]] = {}
        self._broker_host: str = ""
        self._broker_port: int = 1883
        self._default_topics: list[str] = [
            "energy-tds/notifications/#",
            "energy-tds/compute/#",
            "energy-tds/data/#",
        ]

    async def connect(self) -> None:
        """连接 MQTT Broker"""
        try:
            # 解析 broker 地址
            self._parse_broker_url()

            # 创建客户端
            self.client = mqtt.Client(
                client_id=settings.MQTT_CLIENT_ID,
                protocol=mqtt.MQTTv5,
            )

            # 设置认证
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(
                    settings.MQTT_USERNAME,
                    settings.MQTT_PASSWORD,
                )

            # 注册回调
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            # 设置遗嘱消息 (LWT)
            self.client.will_set(
                "energy-tds/status/backend",
                payload="offline",
                qos=1,
                retain=True,
            )

            # 连接 broker
            self.client.connect(
                self._broker_host,
                self._broker_port,
                keepalive=60,
            )
            self.client.loop_start()

            logger.info(f"MQTT connecting to {self._broker_host}:{self._broker_port}")
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            raise

    def _parse_broker_url(self) -> None:
        """解析 MQTT Broker URL"""
        broker_url = settings.MQTT_BROKER

        # 支持多种格式: tcp://host:port, host:port, host
        if "://" in broker_url:
            parsed = urlparse(broker_url)
            self._broker_host = parsed.hostname or "localhost"
            self._broker_port = parsed.port or 1883
        else:
            # 处理 host:port 格式
            parts = broker_url.split(":")
            self._broker_host = parts[0]
            self._broker_port = int(parts[1]) if len(parts) > 1 else 1883

    async def disconnect(self) -> None:
        """断开 MQTT 连接"""
        if self.client:
            # 发送离线状态
            self.client.publish(
                "energy-tds/status/backend",
                payload="offline",
                qos=1,
                retain=True,
            )
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False
            logger.info("MQTT disconnected")

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        """连接回调"""
        if rc == 0:
            self._connected = True
            logger.info("MQTT connected successfully")

            # 发送在线状态
            self.client.publish(
                "energy-tds/status/backend",
                payload="online",
                qos=1,
                retain=True,
            )

            # 订阅默认主题
            for topic in self._default_topics:
                self.client.subscribe(topic)
                logger.info(f"MQTT subscribed to {topic}")
        else:
            logger.error(f"MQTT connection failed with code: {rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None) -> None:
        """断开回调"""
        self._connected = False
        if rc != 0:
            logger.warning(f"MQTT unexpected disconnect: {rc}")
        else:
            logger.info("MQTT disconnected gracefully")

    def _on_message(self, client, userdata, msg) -> None:
        """消息回调"""
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        logger.debug(f"MQTT message received: {topic} - {payload[:100]}")

        # 精确匹配回调
        callbacks = self._callbacks.get(topic, [])

        # 通配符匹配回调
        for pattern, pattern_callbacks in self._callbacks.items():
            if pattern != topic and self._topic_matches(pattern, topic):
                callbacks.extend(pattern_callbacks)

        # 执行回调
        for callback in callbacks:
            try:
                callback(topic, payload)
            except Exception as e:
                logger.error(f"MQTT message callback error: {e}")

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """检查主题是否匹配通配符模式"""
        # 将 MQTT 通配符转换为正则表达式
        regex_pattern = pattern.replace("+", "[^/]+").replace("#", ".*")
        return bool(re.match(f"^{regex_pattern}$", topic))

    def subscribe(self, topic: str, callback: Callable) -> None:
        """订阅主题并注册回调"""
        if topic not in self._callbacks:
            self._callbacks[topic] = []
            if self.client and self._connected:
                self.client.subscribe(topic)
                logger.info(f"MQTT subscribed to {topic}")
        self._callbacks[topic].append(callback)

    def unsubscribe(self, topic: str) -> None:
        """取消订阅主题"""
        if topic in self._callbacks:
            del self._callbacks[topic]
            if self.client and self._connected:
                self.client.unsubscribe(topic)
                logger.info(f"MQTT unsubscribed from {topic}")

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """发布消息"""
        if self.client and self._connected:
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"MQTT published to {topic}")
            else:
                logger.error(f"MQTT publish failed to {topic}: {result.rc}")
        else:
            logger.warning(f"MQTT not connected, cannot publish to {topic}")

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected


# 全局 MQTT 管理器实例
mqtt_manager = MQTTManager()
