/**
 * StatsRow 统计卡片行布局组件
 * 基于 Tailwind CSS Grid 的响应式统计卡片行
 * 用于在页面顶部展示多列统计数据
 */
import React from 'react';

export interface StatsRowProps {
  /** 子元素（通常是 StatCard 组件） */
  children: React.ReactNode;
  /** 列数（默认 4 列，移动端自动折行） */
  columns?: number;
  /** 自定义 className */
  className?: string;
}

/** 列数 → 响应式 grid class 映射 */
const COLUMNS_CLASS_MAP: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-2 sm:grid-cols-2 lg:grid-cols-4',
  5: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5',
  6: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-6',
};

/**
 * StatsRow 组件
 * 提供统计卡片的网格行布局，支持 1-6 列自适应
 */
const StatsRow: React.FC<StatsRowProps> = ({
  children,
  columns = 4,
  className = '',
}) => {
  const clampedCols = Math.min(Math.max(columns, 1), 6);
  const colsClass = COLUMNS_CLASS_MAP[clampedCols] ?? COLUMNS_CLASS_MAP[4];

  return (
    <div className={`grid ${colsClass} gap-4 sm:gap-5 mb-6 ${className}`}>
      {children}
    </div>
  );
};

export default StatsRow;
