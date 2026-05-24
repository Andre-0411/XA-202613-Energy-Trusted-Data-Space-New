/**
 * useWebSocket Hook
 * 提供WebSocket连接状态、消息订阅、频道管理等功能
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { getWebSocket, type ConnectionStatus, type WSMessage } from '@/api/websocket';

type EventHandler = (data: unknown) => void;

interface UseWebSocketOptions {
  /** 是否自动连接 */
  autoConnect?: boolean;
  /** 订阅的频道列表 */
  channels?: string[];
}

interface UseWebSocketReturn {
  /** 连接状态 */
  status: ConnectionStatus;
  /** 是否已连接 */
  connected: boolean;
  /** 连接 */
  connect: () => void;
  /** 断开连接 */
  disconnect: () => void;
  /** 发送消息 */
  send: (type: string, data?: Record<string, unknown>) => void;
  /** 订阅频道 */
  subscribe: (channels: string[]) => void;
  /** 取消订阅 */
  unsubscribe: (channels: string[]) => void;
  /** 监听消息类型 */
  on: (event: string, handler: EventHandler) => () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = true, channels = [] } = options;
  const ws = getWebSocket();
  const [status, setStatus] = useState<ConnectionStatus>(ws.status);
  const cleanupRefs = useRef<Array<() => void>>([]);

  // 监听连接状态
  useEffect(() => {
    const unsubscribe = ws.onStatusChange(setStatus);
    cleanupRefs.current.push(unsubscribe);

    if (autoConnect && !ws.connected) {
      ws.connect();
    }

    return () => {
      cleanupRefs.current.forEach((fn) => fn());
      cleanupRefs.current = [];
    };
  }, [autoConnect, ws]);

  // 订阅频道
  useEffect(() => {
    if (channels.length > 0 && ws.connected) {
      ws.subscribe(channels);
    }

    return () => {
      if (channels.length > 0) {
        ws.unsubscribe(channels);
      }
    };
  }, [channels, ws.connected, ws]);

  const connect = useCallback(() => ws.connect(), [ws]);
  const disconnect = useCallback(() => ws.disconnect(), [ws]);
  const send = useCallback(
    (type: string, data: Record<string, unknown> = {}) => ws.send(type, data),
    [ws],
  );
  const subscribe = useCallback((chs: string[]) => ws.subscribe(chs), [ws]);
  const unsubscribe = useCallback((chs: string[]) => ws.unsubscribe(chs), [ws]);

  const on = useCallback(
    (event: string, handler: EventHandler) => {
      const unsub = ws.on(event, handler);
      cleanupRefs.current.push(unsub);
      return unsub;
    },
    [ws],
  );

  return {
    status,
    connected: status === 'connected',
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    on,
  };
}

export default useWebSocket;
