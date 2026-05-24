/**
 * MetricsCard 指标卡片组件
 * 显示大数字、趋势箭头、百分比变化
 * 用于 Dashboard、运营监控、KPI 等页面
 * 迁移自 MUI → TDesign + Tailwind CSS
 */
import React from 'react';
import { TrendingUpIcon, TrendingDownIcon, RemoveIcon } from 'tdesign-icons-react';

/** 趋势方向 */
type TrendDirection = 'up' | 'down' | 'stable';

/** 预置色彩 */
type MetricsColor = 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';

/** 颜色→具体色值映射 */
const COLOR_MAP: Record<MetricsColor, { main: string; lighter: string }> = {
  primary: { main: '#1976d2', lighter: '#e3f2fd' },
  secondary: { main: '#9c27b0', lighter: '#f3e5f5' },
  success: { main: '#2e7d32', lighter: '#e8f5e9' },
  error: { main: '#d32f2f', lighter: '#ffebee' },
  warning: { main: '#ed6c02', lighter: '#fff3e0' },
  info: { main: '#0288d1', lighter: '#e1f5fe' },
};

/** 趋势方向 → 颜色映射 */
const trendColorMap: Record<TrendDirection, string> = {
  up: '#2e7d32',
  down: '#d32f2f',
  stable: '#757575',
};

/** 趋势方向 → 图标映射 */
const TREND_ICON_MAP: Record<TrendDirection, React.ReactNode> = {
  up: <TrendingUpIcon size="16px" />,
  down: <TrendingDownIcon size="16px" />,
  stable: <RemoveIcon size="16px" />,
};

export interface MetricsCardProps {
  /** 指标标题 */
  title: string;
  /** 指标值 */
  value: string | number;
  /** 单位 */
  unit?: string;
  /** 趋势方向 */
  trend?: TrendDirection;
  /** 趋势变化值（如 "+12.5%"） */
  trendValue?: string;
  /** 左侧图标 */
  icon?: React.ReactNode;
  /** 主色调 */
  color?: MetricsColor;
  /** 自定义 className */
  className?: string;
  /** 自定义 style */
  style?: React.CSSProperties;
}

/**
 * MetricsCard 指标卡片
 * 展示 KPI 数值与趋势变化
 */
const MetricsCard: React.FC<MetricsCardProps> = ({
  title,
  value,
  unit,
  trend,
  trendValue,
  icon,
  color = 'primary',
  className = '',
  style,
}) => {
  const colors = COLOR_MAP[color] ?? COLOR_MAP.primary;

  return (
    <div
      className={`rounded-lg border border-gray-200 transition-shadow duration-200 hover:shadow-md hover:border-current ${className}`}
      style={{ borderColor: '#e5e7eb', ...style }}
    >
      <div className="p-5">
        <div className="flex items-start justify-between">
          {/* 左侧：标题 + 数值 */}
          <div className="flex-1">
            <p className="text-sm text-gray-500 font-medium mb-2 m-0">
              {title}
            </p>
            <div className="flex items-baseline gap-1">
              <span
                className="text-2xl font-bold leading-none"
                style={{ color: colors.main }}
              >
                {value}
              </span>
              {unit && (
                <span className="text-sm text-gray-500">
                  {unit}
                </span>
              )}
            </div>

            {/* 趋势 */}
            {trend && trendValue && (
              <div className="flex items-center gap-1 mt-2">
                <span style={{ color: trendColorMap[trend], display: 'flex', alignItems: 'center' }}>
                  {TREND_ICON_MAP[trend]}
                </span>
                <span
                  className="text-xs font-semibold"
                  style={{ color: trendColorMap[trend] }}
                >
                  {trendValue}
                </span>
              </div>
            )}
          </div>

          {/* 右侧图标 */}
          {icon && (
            <div
              className="flex items-center justify-center rounded-lg flex-shrink-0"
              style={{
                width: 48,
                height: 48,
                backgroundColor: colors.lighter,
                color: colors.main,
              }}
            >
              {icon}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MetricsCard;
