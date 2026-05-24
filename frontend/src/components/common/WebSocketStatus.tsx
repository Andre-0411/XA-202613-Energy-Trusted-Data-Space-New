/**
 * WebSocket 连接状态指示器
 * 显示当前WebSocket连接状态，支持手动重连
 * 已从 MUI Chip/Tooltip/IconButton 迁移至 TDesign Tag/Tooltip/Button
 */
import React from 'react';
import { Tag, Tooltip, Button, Loading } from 'tdesign-react';
import {
  WifiIcon,
  RefreshIcon,
  PoweroffIcon,
} from 'tdesign-icons-react';
import type { ConnectionStatus } from '@/api/websocket';

interface WebSocketStatusProps {
  status: ConnectionStatus;
  onReconnect?: () => void;
  showLabel?: boolean;
  size?: 'small' | 'medium';
}

const STATUS_CONFIG: Record<ConnectionStatus, { color: string; label: string; icon: React.ReactNode; theme: 'success' | 'warning' | 'danger' }> = {
  connected: {
    color: '#4caf50',
    label: '已连接',
    icon: <WifiIcon />,
    theme: 'success',
  },
  connecting: {
    color: '#ff9800',
    label: '连接中...',
    icon: <Loading size="small" />,
    theme: 'warning',
  },
  disconnected: {
    color: '#f44336',
    label: '已断开',
    icon: <PoweroffIcon />,
    theme: 'danger',
  },
  reconnecting: {
    color: '#ff9800',
    label: '重连中...',
    icon: <RefreshIcon className="animate-spin" />,
    theme: 'warning',
  },
};

const WebSocketStatus: React.FC<WebSocketStatusProps> = ({
  status,
  onReconnect,
  showLabel = true,
  size = 'small',
}) => {
  const config = STATUS_CONFIG[status];

  if (status === 'disconnected' && onReconnect) {
    return (
      <Tooltip content="点击重连">
        <Tag
          icon={<RefreshIcon />}
          theme="danger"
          variant="outline"
          size={size === 'medium' ? 'medium' : 'small'}
          onClick={onReconnect}
          style={{ cursor: 'pointer' }}
        >
          {showLabel ? '已断开 - 点击重连' : undefined}
        </Tag>
      </Tooltip>
    );
  }

  return (
    <Tooltip content={`实时连接: ${config.label}`}>
      <Tag
        icon={config.icon}
        theme={config.theme}
        variant="outline"
        size={size === 'medium' ? 'medium' : 'small'}
        style={{ fontSize: '0.75rem' }}
      >
        {showLabel ? config.label : undefined}
      </Tag>
    </Tooltip>
  );
};

export default WebSocketStatus;
