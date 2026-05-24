/**
 * RecentActivity - 底部区域
 * 包含：快捷操作 + 系统状态指示器 + 告警列表
 */
import React from 'react';
import { Button, Tag } from 'tdesign-react';
import {
  SettingIcon,
  ComponentSwitchIcon,
  ErrorCircleIcon,
  CloseCircleFilledIcon,
  CheckCircleFilledIcon,
  ShieldErrorFilledIcon,
} from 'tdesign-icons-react';
import { useNavigate } from 'react-router-dom';
import type { AlertInfo } from '@/types/api';

/* ===== 系统状态指示器 ===== */
interface SystemStatusProps {
  label: string;
  value: number;
  color: string;
  status: 'excellent' | 'good' | 'warning' | 'critical';
}

const SystemStatusIndicator: React.FC<SystemStatusProps> = ({ label, value, color, status }) => {
  const statusColors = {
    excellent: '#4caf50',
    good: '#8bc34a',
    warning: '#ff9800',
    critical: '#f44336',
  };

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-gray-600">{label}</span>
        <div className="flex items-center gap-1">
          <div
            className={`w-2 h-2 rounded-full ${status === 'critical' ? 'animate-pulse' : ''}`}
            style={{ backgroundColor: statusColors[status] }}
          />
          <span className="text-xs text-gray-600">{value}%</span>
        </div>
      </div>
      <div className="w-full h-1.5 rounded-full" style={{ backgroundColor: `${color}26` }}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${value}%`,
            background: `linear-gradient(90deg, ${color}, ${color}b3)`,
          }}
        />
      </div>
    </div>
  );
};

/* ===== 快捷操作卡片 ===== */
interface QuickActionData {
  title: string;
  icon: React.ReactNode;
  color: string;
  path: string;
  description: string;
}

const QuickActionCard: React.FC<QuickActionData> = ({ title, icon, color, path, description }) => {
  const navigate = useNavigate();

  return (
    <div
      className="rounded-xl bg-white border border-gray-200 cursor-pointer transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg group"
      onClick={() => navigate(path)}
    >
      <div className="p-4 sm:p-5">
        <div className="flex items-center gap-3 sm:gap-4">
          <div
            className="w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center transition-all duration-300 group-hover:bg-white group-hover:text-white shrink-0"
            style={{ backgroundColor: `${color}1a`, color }}
          >
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-800 truncate m-0">{title}</p>
            <p className="text-xs text-gray-500 truncate m-0 hidden sm:block">{description}</p>
          </div>
          <span className="text-gray-400 text-lg hidden sm:block">→</span>
        </div>
      </div>
    </div>
  );
};

/* ===== 告警项组件 ===== */
interface AlertItemProps {
  alert: AlertInfo;
}

const AlertItem: React.FC<AlertItemProps> = ({ alert }) => {
  const severityConfig = {
    CRITICAL: { color: '#f44336', icon: <CloseCircleFilledIcon size="18px" />, bg: '#fef2f2' },
    HIGH: { color: '#ff9800', icon: <ErrorCircleIcon size="18px" />, bg: '#fff8e1' },
    MEDIUM: { color: '#2196f3', icon: <ErrorCircleIcon size="18px" />, bg: '#e3f2fd' },
    LOW: { color: '#4caf50', icon: <CheckCircleFilledIcon size="18px" />, bg: '#f1f8e9' },
  };

  const config = severityConfig[alert.severity as keyof typeof severityConfig] || severityConfig.LOW;

  return (
    <div
      className="p-4 mb-2 rounded-lg transition-all duration-200 hover:translate-x-1 hover:shadow-md cursor-pointer"
      style={{ backgroundColor: config.bg, borderLeft: `4px solid ${config.color}` }}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5" style={{ color: config.color }}>{config.icon}</div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800 truncate m-0">{alert.title}</p>
          <p className="text-xs text-gray-500 mt-0.5 m-0">{alert.message}</p>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <Tag>{alert.severity}</Tag>
            <span className="text-xs text-gray-500">
              {new Date(alert.fired_at).toLocaleString('zh-CN')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ===== 主组件 ===== */
interface RecentActivityProps {
  alerts: AlertInfo[];
  loading: boolean;
  isSmall: boolean;
}

const RecentActivity: React.FC<RecentActivityProps> = ({ alerts, loading, isSmall }) => {
  const navigate = useNavigate();

  return (
    <div className="lg:col-span-8">
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 sm:p-6 h-full">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-gray-800 flex items-center gap-2 m-0">
            <ShieldErrorFilledIcon size="18px" />
            最近告警
          </h3>
          <Button
            theme="default"
            size="small"
            onClick={() => navigate('/dashboard/ops/monitor')}
          >
            查看全部
          </Button>
        </div>
        {loading ? (
          <div className="flex flex-col gap-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-20 bg-gray-200 rounded-lg" />
              </div>
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <CheckCircleFilledIcon size={isSmall ? '48px' : '64px'} className="text-green-500 mb-4" />
            <h3 className="text-base font-semibold text-gray-800 m-0">系统运行正常</h3>
            <span className="text-xs text-gray-500 mt-1">暂无告警信息</span>
          </div>
        ) : (
          <div className="flex flex-col">
            {alerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RecentActivity;
