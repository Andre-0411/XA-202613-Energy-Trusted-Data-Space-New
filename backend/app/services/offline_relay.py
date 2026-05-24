"""
断线续传模块
============
MQTT 离线缓存 + 自动补传机制

功能：
- 离线数据本地缓存（SQLite/文件）
- 连接状态监控
- 自动补传策略
- 消息去重
- 优先级队列
"""
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class MessagePriority(IntEnum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"          # 待发送
    SENT = "sent"                # 已发送
    ACKNOWLEDGED = "acknowledged"  # 已确认
    FAILED = "failed"            # 发送失败
    EXPIRED = "expired"          # 已过期


@dataclass
class OfflineMessage:
    """离线消息"""
    message_id: str
    topic: str
    payload: bytes
    qos: int = 1
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 5
    last_retry_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


class OfflineRelayStore:
    """离线续传存储（SQLite）"""

    def __init__(self, db_path: str = "offline_relay.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offline_messages (
                    message_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    payload BLOB NOT NULL,
                    qos INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 5,
                    last_retry_at TEXT,
                    expires_at TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_priority
                ON offline_messages(status, priority DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON offline_messages(created_at)
            """)
            conn.commit()
            conn.close()

    def store_message(self, message: OfflineMessage) -> str:
        """存储离线消息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO offline_messages
                    (message_id, topic, payload, qos, priority, status,
                     created_at, retry_count, max_retries, last_retry_at,
                     expires_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.message_id,
                    message.topic,
                    message.payload,
                    message.qos,
                    int(message.priority),
                    message.status.value,
                    message.created_at.isoformat(),
                    message.retry_count,
                    message.max_retries,
                    message.last_retry_at.isoformat() if message.last_retry_at else None,
                    message.expires_at.isoformat() if message.expires_at else None,
                    json.dumps(message.metadata),
                ))
                conn.commit()
                logger.debug(f"Stored offline message: {message.message_id}")
                return message.message_id
            finally:
                conn.close()

    def get_pending_messages(
        self,
        limit: int = 100,
        exclude_expired: bool = True,
    ) -> list[OfflineMessage]:
        """获取待发送消息（按优先级排序）"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                now = datetime.now(timezone.utc).isoformat()
                if exclude_expired:
                    cursor = conn.execute("""
                        SELECT * FROM offline_messages
                        WHERE status = 'pending'
                        AND (expires_at IS NULL OR expires_at > ?)
                        ORDER BY priority DESC, created_at ASC
                        LIMIT ?
                    """, (now, limit))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM offline_messages
                        WHERE status = 'pending'
                        ORDER BY priority DESC, created_at ASC
                        LIMIT ?
                    """, (limit,))

                messages = []
                for row in cursor.fetchall():
                    messages.append(self._row_to_message(row))
                return messages
            finally:
                conn.close()

    def get_failed_messages(
        self,
        max_retries: int = 5,
        limit: int = 100,
    ) -> list[OfflineMessage]:
        """获取需要重试的失败消息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.execute("""
                    SELECT * FROM offline_messages
                    WHERE status = 'failed'
                    AND retry_count < ?
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                """, (max_retries, limit))

                messages = []
                for row in cursor.fetchall():
                    messages.append(self._row_to_message(row))
                return messages
            finally:
                conn.close()

    def update_status(
        self,
        message_id: str,
        status: MessageStatus,
        increment_retry: bool = False,
    ) -> bool:
        """更新消息状态"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                now = datetime.now(timezone.utc).isoformat()
                if increment_retry:
                    conn.execute("""
                        UPDATE offline_messages
                        SET status = ?, retry_count = retry_count + 1, last_retry_at = ?
                        WHERE message_id = ?
                    """, (status.value, now, message_id))
                else:
                    conn.execute("""
                        UPDATE offline_messages
                        SET status = ?, last_retry_at = ?
                        WHERE message_id = ?
                    """, (status.value, now, message_id))
                conn.commit()
                return conn.total_changes > 0
            finally:
                conn.close()

    def delete_message(self, message_id: str) -> bool:
        """删除消息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute("DELETE FROM offline_messages WHERE message_id = ?", (message_id,))
                conn.commit()
                return conn.total_changes > 0
            finally:
                conn.close()

    def cleanup_expired(self) -> int:
        """清理过期消息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                now = datetime.now(timezone.utc).isoformat()
                cursor = conn.execute(
                    "DELETE FROM offline_messages WHERE expires_at IS NOT NULL AND expires_at < ?",
                    (now,)
                )
                conn.commit()
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired offline messages")
                return deleted
            finally:
                conn.close()

    def get_statistics(self) -> dict:
        """获取统计信息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                stats = {}
                for status in ["pending", "sent", "acknowledged", "failed", "expired"]:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM offline_messages WHERE status = ?",
                        (status,)
                    )
                    stats[status] = cursor.fetchone()[0]

                stats["total"] = sum(stats.values())

                # 最旧的待发送消息
                cursor = conn.execute("""
                    SELECT created_at FROM offline_messages
                    WHERE status = 'pending'
                    ORDER BY created_at ASC LIMIT 1
                """)
                row = cursor.fetchone()
                stats["oldest_pending"] = row[0] if row else None

                return stats
            finally:
                conn.close()

    def _row_to_message(self, row: tuple) -> OfflineMessage:
        """数据库行转消息对象"""
        return OfflineMessage(
            message_id=row[0],
            topic=row[1],
            payload=row[2],
            qos=row[3],
            priority=MessagePriority(row[4]),
            status=MessageStatus(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            retry_count=row[7],
            max_retries=row[8],
            last_retry_at=datetime.fromisoformat(row[9]) if row[9] else None,
            expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
            metadata=json.loads(row[11]) if row[11] else {},
        )


class OfflineRelay:
    """断线续传管理器"""

    def __init__(
        self,
        db_path: str = "offline_relay.db",
        max_queue_size: int = 10000,
        message_ttl_hours: int = 24,
    ):
        self.store = OfflineRelayStore(db_path)
        self.max_queue_size = max_queue_size
        self.message_ttl = timedelta(hours=message_ttl_hours)

        self._connected = False
        self._relay_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._send_callback: Optional[Callable] = None
        self._dedup_cache: dict[str, set] = defaultdict(set)  # topic -> seen message hashes

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_connected(self, connected: bool) -> None:
        """设置连接状态"""
        was_connected = self._connected
        self._connected = connected

        if connected and not was_connected:
            logger.info("Connection restored, starting offline relay")
            self._start_relay()
        elif not connected and was_connected:
            logger.warning("Connection lost, switching to offline mode")

    def set_send_callback(self, callback: Callable) -> None:
        """设置发送回调函数"""
        self._send_callback = callback

    # ================================================================
    # 消息入队
    # ================================================================

    def enqueue(
        self,
        topic: str,
        payload: dict,
        qos: int = 1,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[dict] = None,
    ) -> Optional[str]:
        """
        入队消息

        如果在线则直接发送，否则缓存到离线队列。
        """
        # 消息去重
        payload_hash = hash(json.dumps(payload, sort_keys=True, default=str))
        if payload_hash in self._dedup_cache[topic]:
            logger.debug(f"Duplicate message dropped: topic={topic}")
            return None

        self._dedup_cache[topic].add(payload_hash)
        # 限制去重缓存大小
        if len(self._dedup_cache[topic]) > 10000:
            self._dedup_cache[topic] = set(list(self._dedup_cache[topic])[-5000:])

        # 检查队列大小
        stats = self.store.get_statistics()
        if stats.get("total", 0) >= self.max_queue_size:
            logger.warning("Offline queue full, dropping oldest low-priority message")
            self._drop_oldest_low_priority()

        message = OfflineMessage(
            message_id=str(uuid.uuid4()),
            topic=topic,
            payload=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
            qos=qos,
            priority=priority,
            expires_at=datetime.now(timezone.utc) + self.message_ttl,
            metadata=metadata or {},
        )

        # 在线则直接发送
        if self._connected and self._send_callback:
            try:
                success = self._send_callback(topic, message.payload, qos)
                if success:
                    message.status = MessageStatus.SENT
                    self.store.store_message(message)
                    logger.debug(f"Message sent directly: {message.message_id}")
                    return message.message_id
            except Exception as e:
                logger.warning(f"Direct send failed, queuing offline: {e}")

        # 离线则缓存
        message.status = MessageStatus.PENDING
        self.store.store_message(message)
        logger.debug(f"Message queued offline: {message.message_id}")
        return message.message_id

    # ================================================================
    # 补传逻辑
    # ================================================================

    def _start_relay(self) -> None:
        """启动补传线程"""
        if self._relay_thread and self._relay_thread.is_alive():
            return

        self._stop_event.clear()
        self._relay_thread = threading.Thread(
            target=self._relay_loop,
            daemon=True,
            name="offline-relay",
        )
        self._relay_thread.start()

    def stop_relay(self) -> None:
        """停止补传"""
        self._stop_event.set()
        if self._relay_thread:
            self._relay_thread.join(timeout=5)

    def _relay_loop(self) -> None:
        """补传主循环"""
        logger.info("Offline relay loop started")

        while not self._stop_event.is_set():
            try:
                # 1. 清理过期消息
                self.store.cleanup_expired()

                # 2. 获取待发送消息
                pending = self.store.get_pending_messages(limit=50)
                failed = self.store.get_failed_messages(limit=20)

                messages_to_send = pending + failed

                if not messages_to_send:
                    # 没有待发送消息，等待
                    self._stop_event.wait(timeout=5)
                    continue

                # 3. 逐条发送
                for message in messages_to_send:
                    if self._stop_event.is_set():
                        break

                    if not self._connected:
                        logger.warning("Connection lost during relay, stopping")
                        break

                    success = self._send_message(message)

                    if success:
                        self.store.update_status(message.message_id, MessageStatus.SENT)
                    else:
                        self.store.update_status(
                            message.message_id,
                            MessageStatus.FAILED,
                            increment_retry=True,
                        )

                        # 指数退避
                        wait_time = min(2 ** message.retry_count, 60)
                        self._stop_event.wait(timeout=wait_time)

                # 批次间短暂休息
                self._stop_event.wait(timeout=1)

            except Exception as e:
                logger.error(f"Relay loop error: {e}")
                self._stop_event.wait(timeout=5)

        logger.info("Offline relay loop stopped")

    def _send_message(self, message: OfflineMessage) -> bool:
        """发送单条消息"""
        if not self._send_callback:
            return False

        try:
            success = self._send_callback(
                message.topic,
                message.payload,
                message.qos,
            )
            if success:
                logger.debug(f"Relayed message: {message.message_id}")
            return success
        except Exception as e:
            logger.error(f"Send message failed: {e}")
            return False

    def acknowledge(self, message_id: str) -> None:
        """确认消息已收到"""
        self.store.update_status(message_id, MessageStatus.ACKNOWLEDGED)

    def _drop_oldest_low_priority(self) -> None:
        """丢弃最旧的低优先级消息"""
        with self.store._lock:
            conn = sqlite3.connect(self.store.db_path)
            try:
                conn.execute("""
                    DELETE FROM offline_messages
                    WHERE message_id = (
                        SELECT message_id FROM offline_messages
                        WHERE status = 'pending' AND priority <= 1
                        ORDER BY created_at ASC LIMIT 1
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    # ================================================================
    # 统计与管理
    # ================================================================

    def get_statistics(self) -> dict:
        """获取统计信息"""
        stats = self.store.get_statistics()
        stats["is_connected"] = self._connected
        stats["max_queue_size"] = self.max_queue_size
        stats["queue_usage"] = f"{stats.get('total', 0)}/{self.max_queue_size}"
        return stats

    def get_pending_count(self) -> int:
        """获取待发送消息数量"""
        stats = self.store.get_statistics()
        return stats.get("pending", 0) + stats.get("failed", 0)

    def clear_all(self) -> int:
        """清空所有离线消息"""
        with self.store._lock:
            conn = sqlite3.connect(self.store.db_path)
            try:
                cursor = conn.execute("DELETE FROM offline_messages")
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()


# 全局单例
_offline_relay: Optional[OfflineRelay] = None


def get_offline_relay(db_path: str = "offline_relay.db") -> OfflineRelay:
    """获取断线续传管理器单例"""
    global _offline_relay
    if _offline_relay is None:
        _offline_relay = OfflineRelay(db_path=db_path)
    return _offline_relay
