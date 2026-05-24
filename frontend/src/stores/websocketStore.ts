/**
 * WebSocket 状态管理（Zustand）
 * connected / messages / lastMessage
 * connect / disconnect / send / subscribe
 */
import { create } from 'zustand';
import { getWebSocket } from '@/api/websocket';
import type { WsMessage } from '@/types/api';

interface WebSocketState {
  connected: boolean;
  messages: WsMessage[];
  lastMessage: WsMessage | null;
  reconnecting: boolean;
  reconnectAttempt: number;

  connect: () => void;
  disconnect: () => void;
  send: (type: string, payload: Record<string, unknown>) => void;
  subscribe: (event: string, handler: (data: unknown) => void) => () => void;
  clearMessages: () => void;
}

export const useWebSocketStore = create<WebSocketState>()((set, _get) => {
  let unsubscribers: (() => void)[] = [];

  return {
    connected: false,
    messages: [],
    lastMessage: null,
    reconnecting: false,
    reconnectAttempt: 0,

    connect: () => {
      const ws = getWebSocket();

      // 清理旧的订阅
      unsubscribers.forEach((unsub) => unsub());
      unsubscribers = [];

      // 连接事件
      unsubscribers.push(
        ws.on('connected', () => {
          set({ connected: true, reconnecting: false, reconnectAttempt: 0 });
        }),
      );

      // 断开事件
      unsubscribers.push(
        ws.on('disconnected', () => {
          set({ connected: false });
        }),
      );

      // 重连中事件
      unsubscribers.push(
        ws.on('reconnecting', (data) => {
          set({
            reconnecting: true,
            reconnectAttempt: (data as { attempt: number }).attempt || 0,
          });
        }),
      );

      // 重连失败
      unsubscribers.push(
        ws.on('reconnect_failed', () => {
          set({ reconnecting: false });
        }),
      );

      // 消息事件
      unsubscribers.push(
        ws.on('message', (data) => {
          const message = data as WsMessage;
          set((state) => ({
            messages: [...state.messages.slice(-99), message],
            lastMessage: message,
          }));
        }),
      );

      // 告警通知
      unsubscribers.push(
        ws.on('alert', (data) => {
          // 通过 CustomEvent 通知全局
          window.dispatchEvent(
            new CustomEvent('eds:notification', {
              detail: { type: 'warning', ...(data as Record<string, unknown>) },
            }),
          );
        }),
      );

      // 任务状态变更
      unsubscribers.push(
        ws.on('task_status_changed', (data) => {
          window.dispatchEvent(
            new CustomEvent('eds:task-update', { detail: data }),
          );
        }),
      );

      ws.connect();
    },

    disconnect: () => {
      const ws = getWebSocket();
      unsubscribers.forEach((unsub) => unsub());
      unsubscribers = [];
      ws.disconnect();
      set({ connected: false, reconnecting: false, reconnectAttempt: 0 });
    },

    send: (type: string, payload: Record<string, unknown>) => {
      const ws = getWebSocket();
      ws.send(type, payload);
    },

    subscribe: (event: string, handler: (data: unknown) => void) => {
      const ws = getWebSocket();
      return ws.on(event, handler);
    },

    clearMessages: () => {
      set({ messages: [], lastMessage: null });
    },
  };
});
