/**
 * 监管大屏 - 告警面板组件
 */
import React from 'react';
import { Tag } from 'tdesign-react';
import {
  ShieldErrorIcon, CheckCircleFilledIcon, ErrorCircleIcon,
} from 'tdesign-icons-react';
import type { AlertInfo } from '@/types/api';

const COLORS = {
  cardBg: '#111827',
  cardBorder: '#1f2937',
  textSecondary: '#9ca3af',
  accent3: '#00e676',
  accent4: '#ff6e40',
};

/** 告警项组件 */
interface AlertItemProps {
  alert: AlertInfo;
  index: number;
}

const AlertItem: React.FC<AlertItemProps> = ({ alert, index }) => {
  const severityConfig = {
    CRITICAL: { color: '#ef4444', icon: <ErrorCircleIcon />, bg: 'rgba(239, 68, 68, 0.1)' },
    HIGH: { color: '#f59e0b', icon: <ErrorCircleIcon />, bg: 'rgba(245, 158, 11, 0.1)' },
    MEDIUM: { color: '#3b82f6', icon: <ErrorCircleIcon />, bg: 'rgba(59, 130, 246, 0.1)' },
    LOW: { color: '#22c55e', icon: <CheckCircleFilledIcon />, bg: 'rgba(34, 197, 94, 0.1)' },
  };

  const config = severityConfig[alert.severity as keyof typeof severityConfig] || severityConfig.LOW;
  const isCriticalOrHigh = alert.severity === 'CRITICAL' || alert.severity === 'HIGH';

  return (
    <div
      role="alert"
      aria-label={`${alert.severity} 级别告警: ${alert.title}`}
      className="mb-2 rounded-md p-3"
      style={{
        background: config.bg,
        border: `1px solid ${config.color}4D`,
        animation: isCriticalOrHigh
          ? `alertFlash 1.5s ease-in-out infinite ${index * 0.2}s, alertPulse 2s ease-in-out infinite ${index * 0.2}s`
          : `fadeIn 0.5s ease-out ${index * 0.1}s both`,
        borderLeft: isCriticalOrHigh ? `4px solid ${config.color}` : undefined,
      }}
    >
      <div className="flex items-center gap-3">
        <div style={{ color: config.color }}>{config.icon}</div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold" style={{ color: config.color }}>{alert.title}</p>
          <p className="truncate text-[0.65rem]" style={{ color: COLORS.textSecondary }}>{alert.message}</p>
        </div>
        <span className="whitespace-nowrap text-[0.6rem]" style={{ color: COLORS.textSecondary }}>
          {new Date(alert.fired_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
};

/** 告警面板组件 */
interface MonitorAlertPanelProps {
  alerts: AlertInfo[];
}

const MonitorAlertPanel: React.FC<MonitorAlertPanelProps> = ({ alerts }) => (
  <section
    aria-label="告警与存证记录"
    className="rounded-xl p-4"
    style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}
  >
    <div className="mb-4 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <ShieldErrorIcon className="text-sm" style={{ color: COLORS.accent4 }} />
        <span className="text-xs font-semibold" style={{ color: COLORS.accent4 }}>最近告警 / 存证记录</span>
        <Tag style={{ background: `${COLORS.accent4}26`, color: COLORS.accent4, fontSize: '0.6rem', height: 18 }}>{alerts.length} 条</Tag>
      </div>
      <span className="text-xs" style={{ color: COLORS.textSecondary }}>自动刷新: 30s</span>
    </div>

    {/* 屏幕阅读器通知播报区 */}
    <div aria-live="polite" aria-atomic="true" className="absolute h-px w-px overflow-hidden" style={{ clip: 'rect(0 0 0 0)' }}>
      {alerts.length > 0 && `${alerts.length} 条告警，最新: ${alerts[0].title}`}
    </div>

    {alerts.length === 0 ? (
      <div className="py-8 text-center">
        <CheckCircleFilledIcon className="mb-2 text-5xl" style={{ color: COLORS.accent3 }} />
        <p className="text-sm" style={{ color: COLORS.textSecondary }}>系统运行正常，暂无告警</p>
      </div>
    ) : (
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-4">
        {alerts.map((alert, index) => (
          <AlertItem key={alert.id} alert={alert} index={index} />
        ))}
      </div>
    )}
  </section>
);

export default MonitorAlertPanel;
