/**
 * WebSocket 管理器
 * 连接/断开/重连/消息收发/事件监听/心跳检测
 * 支持频道订阅、离线消息队列、连接状态管理
 */

type EventHandler = (data: unknown) => void;

/** WebSocket 消息类型 */
export interface WSMessage {
  type: string;
  channel?: string;
  data: Record<string, unknown>;
  timestamp?: string;
  message_id?: string;
}

/** WebSocket 配置 */
interface WsConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  offlineQueueSize?: number;
}

/** 连接状态 */
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

/** 连接状态变更回调 */
type StatusChangeHandler = (status: ConnectionStatus) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private config: Required<WsConfig>;
  private reconnectAttempts = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private statusHandlers: Set<StatusChangeHandler> = new Set();
  private _status: ConnectionStatus = 'disconnected';
  private _subscribedChannels: Set<string> = new Set();
  private _offlineQueue: Array<{ type: string; payload: Record<string, unknown> }> = [];

  constructor(config: WsConfig) {
    this.config = {
      url: config.url,
      reconnectInterval: config.reconnectInterval ?? 5000,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 10,
      heartbeatInterval: config.heartbeatInterval ?? 30000,
      offlineQueueSize: config.offlineQueueSize ?? 50,
    };
  }

  /** 当前连接状态 */
  get status(): ConnectionStatus {
    return this._status;
  }

  /** 是否已连接 */
  get connected(): boolean {
    return this._status === 'connected';
  }

  /** 已订阅的频道列表 */
  get subscribedChannels(): string[] {
    return Array.from(this._subscribedChannels);
  }

  /** 监听连接状态变更 */
  onStatusChange(handler: StatusChangeHandler): () => void {
    this.statusHandlers.add(handler);
    return () => {
      this.statusHandlers.delete(handler);
    };
  }

  /** 更新连接状态 */
  private setStatus(status: ConnectionStatus): void {
    this._status = status;
    this.statusHandlers.forEach((handler) => {
      try {
        handler(status);
      } catch (err) {
        console.error('[WS] Status handler error:', err);
      }
    });
  }

  /** 建立连接 */
  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.setStatus('connecting');

    const token = localStorage.getItem('eds_token');
    const url = token ? `${this.config.url}?token=${encodeURIComponent(token)}` : this.config.url;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this._status = 'connected';
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.emit('connected', { timestamp: Date.now() });
      this.statusHandlers.forEach((h) => h('connected'));

      // 重新订阅之前的频道
      if (this._subscribedChannels.size > 0) {
        this.sendSubscribe(Array.from(this._subscribedChannels));
      }

      // 发送离线消息队列
      this.flushOfflineQueue();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data as string) as WSMessage;

        // 处理心跳响应
        if (message.type === 'pong' || message.type === 'heartbeat') {
          return;
        }

        this.emit('message', message);
        // 按消息类型分发
        if (message.type) {
          this.emit(message.type, message.data || message);
        }
        // 按频道分发
        if (message.channel) {
          this.emit(`channel:${message.channel}`, message.data || message);
        }
      } catch {
        this.emit('raw', event.data);
      }
    };

    this.ws.onclose = (event: CloseEvent) => {
      this._status = 'disconnected';
      this.stopHeartbeat();
      this.emit('disconnected', { code: event.code, reason: event.reason });
      this.statusHandlers.forEach((h) => h('disconnected'));

      // 非正常关闭时自动重连
      if (event.code !== 1000) {
        this.attemptReconnect();
      }
    };

    this.ws.onerror = () => {
      this.emit('error', { timestamp: Date.now() });
    };
  }

  /** 断开连接 */
  disconnect(): void {
    this.stopHeartbeat();
    this.clearReconnectTimer();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this._status = 'disconnected';
    this.statusHandlers.forEach((h) => h('disconnected'));
  }

  /** 发送消息 */
  send(type: string, data: Record<string, unknown> = {}): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // 离线时加入队列
      if (this._offlineQueue.length < this.config.offlineQueueSize) {
        this._offlineQueue.push({ type, payload: data });
      }
      console.warn('[WS] Cannot send - not connected, queued');
      return;
    }

    const message = JSON.stringify({
      type,
      data,
      timestamp: new Date().toISOString(),
    });

    this.ws.send(message);
  }

  /** 订阅频道 */
  subscribe(channels: string[]): void {
    channels.forEach((ch) => this._subscribedChannels.add(ch));
    this.sendSubscribe(channels);
  }

  /** 取消订阅频道 */
  unsubscribe(channels: string[]): void {
    channels.forEach((ch) => this._subscribedChannels.delete(ch));
    this.send('unsubscribe', { channels });
  }

  /** 发送订阅请求 */
  private sendSubscribe(channels: string[]): void {
    this.send('subscribe', { channels });
  }

  /** 刷新离线消息队列 */
  private flushOfflineQueue(): void {
    while (this._offlineQueue.length > 0) {
      const msg = this._offlineQueue.shift()!;
      this.send(msg.type, msg.payload);
    }
  }

  /** 订阅事件 */
  on(event: string, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    // 返回取消订阅函数
    return () => {
      this.eventHandlers.get(event)?.delete(handler);
    };
  }

  /** 取消订阅 */
  off(event: string, handler: EventHandler): void {
    this.eventHandlers.get(event)?.delete(handler);
  }

  /** 触发事件 */
  private emit(event: string, data: unknown): void {
    this.eventHandlers.get(event)?.forEach((handler) => {
      try {
        handler(data);
      } catch (err) {
        console.error(`[WS] Event handler error for "${event}":`, err);
      }
    });
  }

  /** 启动心跳 */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send('heartbeat', {});
    }, this.config.heartbeatInterval);
  }

  /** 停止心跳 */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /** 尝试重连 */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.emit('reconnect_failed', { attempts: this.reconnectAttempts });
      return;
    }

    this.reconnectAttempts++;
    this.setStatus('reconnecting');
    this.emit('reconnecting', { attempt: this.reconnectAttempts });

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, this.config.reconnectInterval);
  }

  /** 清理重连定时器 */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

// 全局 WebSocket 实例（懒初始化）
let wsInstance: WebSocketManager | null = null;

/** 获取 WebSocket 实例（单例） */
export function getWebSocket(): WebSocketManager {
  if (!wsInstance) {
    const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws/notifications`;
    wsInstance = new WebSocketManager({ url: wsUrl });
  }
  return wsInstance;
}

/** 重置 WebSocket 实例（用于测试或登出） */
export function resetWebSocket(): void {
  if (wsInstance) {
    wsInstance.disconnect();
    wsInstance = null;
  }
}

export { WebSocketManager };
export default WebSocketManager;
