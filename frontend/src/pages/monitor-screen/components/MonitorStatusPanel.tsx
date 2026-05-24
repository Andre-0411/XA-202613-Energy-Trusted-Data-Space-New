/**
 * 监管大屏 - 系统状态面板组件
 */
import React from 'react';

const COLORS = {
  cardBg: '#111827',
  cardBorder: '#1f2937',
  textSecondary: '#9ca3af',
  accent1: '#00e5ff',
};

/** 系统状态指示器 */
interface StatusIndicatorProps {
  label: string;
  value: number;
  color: string;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ label, value, color }) => (
  <div className="mb-4" role="progressbar" aria-label={`${label}: ${value}%`} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
    <div className="mb-1 flex items-center justify-between">
      <span className="text-xs" style={{ color: COLORS.textSecondary }}>{label}</span>
      <span className="text-xs font-semibold" style={{ color }}>{value}%</span>
    </div>
    <div className="h-1 w-full overflow-hidden rounded-full" style={{ background: `${color}26` }}>
      <div
        className="h-full rounded-full"
        style={{
          width: `${value}%`,
          background: `linear-gradient(90deg, ${color}, ${color}99)`,
          boxShadow: `0 0 10px ${color}80`,
        }}
      />
    </div>
  </div>
);

/** 数据流动画组件 */
const DataFlowAnimation: React.FC = () => (
  <div className="relative h-[60px] overflow-hidden" aria-hidden="true">
    <div className="absolute left-0 right-0 top-[25px] h-[2px]" style={{ background: `${COLORS.accent1}33` }} />
    {[...Array(8)].map((_, i) => (
      <div
        key={i}
        className="absolute rounded-full"
        style={{
          top: `${15 + (i % 3) * 15}px`,
          left: 0,
          width: 6,
          height: 6,
          background: i % 2 === 0 ? '#00e5ff' : '#7c4dff',
          boxShadow: `0 0 10px ${i % 2 === 0 ? '#00e5ff' : '#7c4dff'}`,
          animation: `flowParticle ${2 + i * 0.3}s linear infinite`,
          animationDelay: `${i * 0.2}s`,
        }}
      />
    ))}
    {[...Array(3)].map((_, i) => (
      <div
        key={`pulse-${i}`}
        className="absolute rounded-full"
        style={{
          top: 20,
          left: `${20 + i * 30}%`,
          width: 20,
          height: 20,
          border: `2px solid ${COLORS.accent1}4D`,
          animation: 'pulseRing 2s ease-out infinite',
          animationDelay: `${i * 0.5}s`,
        }}
      />
    ))}
  </div>
);

/** 数据轮播指示器 */
interface CarouselIndicatorProps {
  total: number;
  current: number;
  onSwitch: (index: number) => void;
}

export const CarouselIndicator: React.FC<CarouselIndicatorProps> = ({ total, current, onSwitch }) => (
  <div className="mt-2 flex justify-center gap-1">
    {Array.from({ length: total }).map((_, i) => (
      <div
        key={i}
        onClick={() => onSwitch(i)}
        aria-label={`切换到第 ${i + 1} 项`}
        role="button"
        tabIndex={0}
        onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter') onSwitch(i); }}
        className="cursor-pointer rounded-full transition-all hover:opacity-100"
        style={{
          width: current === i ? 24 : 8,
          height: 8,
          background: current === i ? COLORS.accent1 : `${COLORS.accent1}4D`,
        }}
      />
    ))}
  </div>
);

/** 系统状态面板 */
interface MonitorStatusPanelProps {
  systemHealth: Array<{ label: string; value: number; color: string }>;
}

const MonitorStatusPanel: React.FC<MonitorStatusPanelProps> = ({ systemHealth }) => (
  <div className="rounded-xl p-4" style={{ background: COLORS.cardBg, border: `1px solid ${COLORS.cardBorder}` }}>
    <p className="mb-4 text-xs font-semibold" style={{ color: COLORS.accent1 }}>系统健康状态</p>
    {systemHealth.map((item, index) => (
      <StatusIndicator key={index} {...item} />
    ))}
  </div>
);

export { DataFlowAnimation };
export default MonitorStatusPanel;
