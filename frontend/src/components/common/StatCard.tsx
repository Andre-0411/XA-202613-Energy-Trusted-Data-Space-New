/**
 * StatCard 统计卡片组件
 * 基于 Tailwind CSS + TDesign 风格的渐变统计卡片
 * 替代 MUI Card + CardContent 的 dashboard 统计模式
 */
import React, { useState, useEffect } from 'react';

/** 渐变色预设 */
export type GradientPreset = 'blue' | 'green' | 'purple' | 'orange' | 'cyan' | 'red';

const GRADIENT_MAP: Record<GradientPreset, string> = {
  blue: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
  green: 'linear-gradient(135deg, #2e7d32 0%, #66bb6a 100%)',
  purple: 'linear-gradient(135deg, #7b1fa2 0%, #ba68c8 100%)',
  orange: 'linear-gradient(135deg, #ed6c02 0%, #ffb74d 100%)',
  cyan: 'linear-gradient(135deg, #0097a7 0%, #4dd0e1 100%)',
  red: 'linear-gradient(135deg, #c62828 0%, #ef5350 100%)',
};

export interface StatCardProps {
  /** 标题 */
  title: string;
  /** 数值 */
  value: number;
  /** 单位 */
  unit: string;
  /** 图标 */
  icon: React.ReactNode;
  /** 渐变预设或自定义渐变字符串 */
  gradient?: GradientPreset | string;
  /** 趋势百分比（正数上升，负数下降） */
  trend?: number;
  /** 是否加载中 */
  loading?: boolean;
  /** 自定义 className */
  className?: string;
}

/**
 * StatCard 统计卡片
 * 带渐变背景、数字动画、趋势指示器
 */
const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  unit,
  icon,
  gradient = 'blue',
  trend,
  loading = false,
  className = '',
}) => {
  const [displayValue, setDisplayValue] = useState(0);

  /** 数字滚动动画 */
  useEffect(() => {
    if (loading) return;
    const duration = 1500;
    const steps = 60;
    const increment = value / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [value, loading]);

  const bgGradient = gradient in GRADIENT_MAP
    ? GRADIENT_MAP[gradient as GradientPreset]
    : gradient;

  if (loading) {
    return (
      <div
        className={`rounded-xl p-5 ${className}`}
        style={{ background: '#f5f5f5', minHeight: 120 }}
      >
        <div className="animate-pulse space-y-3">
          <div className="h-3 bg-gray-200 rounded w-1/2" />
          <div className="h-8 bg-gray-200 rounded w-2/3" />
          <div className="h-3 bg-gray-200 rounded w-1/3" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={`relative overflow-hidden rounded-xl p-5 text-white transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${className}`}
      style={{ background: bgGradient, minHeight: 120 }}
    >
      {/* 装饰圆 */}
      <div
        className="absolute rounded-full"
        style={{
          top: -50,
          right: -50,
          width: 150,
          height: 150,
          background: 'rgba(255,255,255,0.1)',
        }}
      />
      <div
        className="absolute rounded-full"
        style={{
          bottom: -30,
          left: -30,
          width: 100,
          height: 100,
          background: 'rgba(255,255,255,0.05)',
        }}
      />

      <div className="relative z-10">
        {/* 标题行 */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium opacity-90">{title}</span>
          <div
            className="flex items-center justify-center rounded-full"
            style={{
              background: 'rgba(255,255,255,0.2)',
              width: 44,
              height: 44,
              backdropFilter: 'blur(10px)',
            }}
          >
            {icon}
          </div>
        </div>

        {/* 数值 */}
        <div className="text-3xl font-bold mb-1">
          {displayValue.toLocaleString()}
          <span className="text-base ml-1 opacity-80">{unit}</span>
        </div>

        {/* 趋势 */}
        {trend !== undefined && (
          <div className="flex items-center gap-1">
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              style={{
                transform: trend < 0 ? 'rotate(180deg)' : 'none',
              }}
            >
              <path
                d="M8 3L13 10H3L8 3Z"
                fill="currentColor"
              />
            </svg>
            <span className="text-xs opacity-90">
              {trend >= 0 ? '+' : ''}{trend}% 较上周
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default StatCard;
