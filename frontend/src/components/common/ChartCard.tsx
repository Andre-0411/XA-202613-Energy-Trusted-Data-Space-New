/**
 * ChartCard ECharts 图表卡片封装组件
 * 基于 Tailwind CSS + echarts-for-react 的图表卡片
 * 提供标题栏、操作按钮、加载和空状态处理
 */
import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Loading } from 'tdesign-react';

export interface ChartCardProps {
  /** 卡片标题 */
  title: string;
  /** 卡片副标题 */
  subtitle?: string;
  /** 图表高度（px） */
  height?: number;
  /** ECharts option */
  option: any;
  /** 是否加载中 */
  loading?: boolean;
  /** 标题右侧操作按钮 */
  actions?: React.ReactNode;
  /** 自定义 className */
  className?: string;
}

/**
 * ChartCard 组件
 * 将 ECharts 图表封装到带标题的卡片中
 */
const ChartCard: React.FC<ChartCardProps> = ({
  title,
  subtitle,
  height = 320,
  option,
  loading = false,
  actions,
  className = '',
}) => {
  /** 空状态：没有 series 或 series 为空 */
  const isEmpty =
    !option ||
    !option.series ||
    (Array.isArray(option.series)
      ? option.series.length === 0
      : false) ||
    (Array.isArray(option.series) &&
      option.series.every(
        (s: any) => !s.data || (Array.isArray(s.data) && s.data.length === 0),
      ));

  return (
    <div
      className={`rounded-xl bg-white p-5 ${className}`}
      style={{ border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}
    >
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-4">
        <div className="min-w-0 flex-1">
          <h6 className="text-base font-semibold text-gray-900 m-0 truncate">
            {title}
          </h6>
          {subtitle && (
            <span className="text-xs text-gray-500 mt-0.5 block truncate">
              {subtitle}
            </span>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-2 ml-3 shrink-0">{actions}</div>
        )}
      </div>

      {/* 图表区域 */}
      <div className="relative" style={{ minHeight: height }}>
        {loading ? (
          <div
            className="flex items-center justify-center"
            style={{ height }}
          >
            <Loading size="medium" />
          </div>
        ) : isEmpty ? (
          <div
            className="flex flex-col items-center justify-center text-gray-400"
            style={{ height }}
          >
            <svg
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
            <span className="text-sm mt-2">暂无图表数据</span>
          </div>
        ) : (
          <ReactECharts
            option={option}
            style={{ height, width: '100%' }}
            opts={{ renderer: 'canvas' }}
            notMerge
          />
        )}
      </div>
    </div>
  );
};

export default ChartCard;
