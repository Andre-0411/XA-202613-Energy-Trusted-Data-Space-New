/**
 * 监管大屏 - 核心指标卡片组件
 */
import React, { useState, useEffect, useRef } from 'react';
import { TrendingUpIcon, TrendingDownIcon } from 'tdesign-icons-react';

/** 深色主题常量 */
const COLORS = {
  text: '#e5e7eb',
  textSecondary: '#9ca3af',
  accent1: '#00e5ff',
  accent2: '#7c4dff',
  accent3: '#00e676',
  accent4: '#ff6e40',
  accent5: '#ffd740',
  cardBg: '#111827',
  cardBorder: '#1f2937',
};

/** 动画计数器组件 */
interface AnimatedCounterProps {
  value: number;
  duration?: number;
}

const AnimatedCounter: React.FC<AnimatedCounterProps> = ({ value, duration = 2000 }) => {
  const [displayValue, setDisplayValue] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const startTime = Date.now();
    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.floor(value * eased));
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    requestAnimationFrame(animate);
  }, [value, duration]);

  return (
    <span ref={ref} aria-label={`${value.toLocaleString()}`}>
      {displayValue.toLocaleString()}
    </span>
  );
};

/** 同比/环比对比组件 */
interface ComparisonIndicatorProps {
  yoy: number;
  mom: number;
}

export const ComparisonIndicator: React.FC<ComparisonIndicatorProps> = ({ yoy, mom }) => (
  <div className="mt-1 flex gap-2">
    <div className="group relative flex items-center gap-1">
      {yoy >= 0
        ? <TrendingUpIcon className="text-xs" style={{ color: COLORS.accent3 }} />
        : <TrendingDownIcon className="text-xs" style={{ color: COLORS.accent4 }} />
      }
      <span className="text-[0.6rem]" style={{ color: yoy >= 0 ? COLORS.accent3 : COLORS.accent4 }}>
        同比 {yoy >= 0 ? '+' : ''}{yoy}%
      </span>
      <div className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
        同比（较去年同期）
      </div>
    </div>
    <div className="group relative flex items-center gap-1">
      {mom >= 0
        ? <TrendingUpIcon className="text-xs" style={{ color: COLORS.accent1 }} />
        : <TrendingDownIcon className="text-xs" style={{ color: COLORS.accent5 }} />
      }
      <span className="text-[0.6rem]" style={{ color: mom >= 0 ? COLORS.accent1 : COLORS.accent5 }}>
        环比 {mom >= 0 ? '+' : ''}{mom}%
      </span>
      <div className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
        环比（较上月）
      </div>
    </div>
  </div>
);

/** 核心指标卡片 */
export interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  icon: React.ReactNode;
  gradient: string;
  trend?: number;
  yoy?: number;
  mom?: number;
  isHighlighted?: boolean;
}

const MonitorMetricCard: React.FC<MetricCardProps> = ({ title, value, unit, icon, gradient, trend, yoy, mom, isHighlighted }) => (
  <div
    role="article"
    aria-label={`${title}: ${value} ${unit}`}
    className="relative overflow-hidden rounded-xl p-5 transition-all hover:-translate-y-0.5"
    style={{
      background: COLORS.cardBg,
      border: `1px solid ${isHighlighted ? COLORS.accent1 : COLORS.cardBorder}`,
      boxShadow: isHighlighted ? `0 0 30px rgba(0, 229, 255, 0.2)` : undefined,
    }}
  >
    <div className="absolute left-0 right-0 top-0 h-[3px]" style={{ background: gradient }} />

    <div className="mb-4 flex items-center justify-between">
      <span className="text-sm font-medium" style={{ color: COLORS.textSecondary }}>{title}</span>
      <div
        className="flex h-10 w-10 items-center justify-center rounded-full"
        style={{ background: gradient, boxShadow: '0 4px 20px rgba(0, 229, 255, 0.3)' }}
      >
        {icon}
      </div>
    </div>
    <h3 className="text-3xl font-bold" style={{ color: COLORS.text }}>
      <AnimatedCounter value={value} />
      <span className="ml-2 text-base" style={{ color: COLORS.textSecondary }}>{unit}</span>
    </h3>
    {trend !== undefined && (
      <div className="flex items-center gap-1">
        <TrendingUpIcon className="text-sm" style={{ color: trend >= 0 ? COLORS.accent3 : COLORS.accent4 }} />
        <span className="text-xs" style={{ color: trend >= 0 ? COLORS.accent3 : COLORS.accent4 }}>
          {trend >= 0 ? '+' : ''}{trend}%
        </span>
      </div>
    )}
    {yoy !== undefined && mom !== undefined && (
      <ComparisonIndicator yoy={yoy} mom={mom} />
    )}
  </div>
);

export default MonitorMetricCard;
