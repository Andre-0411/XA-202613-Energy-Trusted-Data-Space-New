/**
 * useNotifications Hook
 * 集成WebSocket实时通知与React Query缓存
 * 提供实时未读计数、新通知推送、已读状态同步
 */
import { useEffect, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import useWebSocket from './useWebSocket';
import type { Notification } from '@/api/system';

/** 通知WebSocket消息 */
interface NotificationWSMessage {
  action: 'created' | 'read' | 'read_all' | 'deleted';
  notification?: Notification;
  notification_id?: string;
  notification_ids?: string[];
}

interface UseNotificationsOptions {
  /** 是否启用WebSocket实时推送 */
  enabled?: boolean;
}

interface UseNotificationsReturn {
  /** WebSocket连接状态 */
  wsStatus: 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
  /** 是否已连接 */
  isConnected: boolean;
  /** 手动重连 */
  reconnect: () => void;
}

export function useNotifications(options: UseNotificationsOptions = {}): UseNotificationsReturn {
  const { enabled = true } = options;
  const queryClient = useQueryClient();
  const prevUnreadRef = useRef<number>(0);

  const { status, connected, connect, on } = useWebSocket({
    autoConnect: enabled,
    channels: enabled ? ['notifications'] : [],
  });

  // 监听通知消息
  useEffect(() => {
    if (!enabled) return;

    const unsub = on('notification', (data: unknown) => {
      const msg = data as NotificationWSMessage;

      switch (msg.action) {
        case 'created':
          // 新通知到达，刷新通知列表和未读计数
          queryClient.invalidateQueries({ queryKey: ['notifications'] });
          queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
          // 更新未读计数缓存
          queryClient.setQueryData<{ code: number; data: { unread_count: number } }>(
            ['unreadCount'],
            (old) => {
              if (!old) return old;
              return {
                ...old,
                data: { unread_count: (old.data?.unread_count ?? 0) + 1 },
              };
            },
          );
          break;

        case 'read':
          // 通知已读同步
          if (msg.notification_id) {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
            queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
          }
          break;

        case 'read_all':
          // 全部已读
          queryClient.invalidateQueries({ queryKey: ['notifications'] });
          queryClient.setQueryData<{ code: number; data: { unread_count: number } }>(
            ['unreadCount'],
            (old) => {
              if (!old) return old;
              return { ...old, data: { unread_count: 0 } };
            },
          );
          break;

        case 'deleted':
          // 通知删除
          queryClient.invalidateQueries({ queryKey: ['notifications'] });
          queryClient.invalidateQueries({ queryKey: ['unreadCount'] });
          break;
      }
    });

    return unsub;
  }, [enabled, on, queryClient]);

  const reconnect = useCallback(() => {
    connect();
  }, [connect]);

  return {
    wsStatus: status,
    isConnected: connected,
    reconnect,
  };
}

export default useNotifications;
