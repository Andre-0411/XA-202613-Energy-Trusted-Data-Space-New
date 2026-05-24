/**
 * PageContainer 通用页面容器组件
 * 基于 Tailwind CSS 的统一页面布局容器
 * 替代 MUI Box + Paper + Container 的页面包裹模式
 */
import React from 'react';

export interface PageContainerProps {
  /** 子元素 */
  children: React.ReactNode;
  /** 背景色 */
  bgColor?: string;
  /** 最大宽度限制 */
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** 内边距 */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** 自定义 className */
  className?: '';
  /** 自定义 style */
  style?: React.CSSProperties;
}

const MAX_WIDTH_MAP = {
  sm: 'max-w-screen-sm',
  md: 'max-w-screen-md',
  lg: 'max-w-screen-lg',
  xl: 'max-w-screen-xl',
  full: 'max-w-full',
};

const PADDING_MAP = {
  none: '',
  sm: 'px-3 py-2',
  md: 'px-4 sm:px-6 py-4',
  lg: 'px-4 sm:px-8 py-6',
};

/**
 * PageContainer 页面容器
 * 提供统一的页面布局和背景色
 */
const PageContainer: React.FC<PageContainerProps> = ({
  children,
  bgColor = '#f8fafc',
  maxWidth = 'xl',
  padding = 'md',
  className = '',
  style,
}) => {
  return (
    <div
      className={`min-h-full ${className}`}
      style={{ backgroundColor: bgColor, ...style }}
    >
      <div className={`${MAX_WIDTH_MAP[maxWidth]} mx-auto ${PADDING_MAP[padding]}`}>
        {children}
      </div>
    </div>
  );
};

/**
 * PageSection 页面分区
 * 替代 MUI Paper，提供带圆角和阴影的内容区块
 */
export interface PageSectionProps {
  children: React.ReactNode;
  /** 标题 */
  title?: string;
  /** 标题图标 */
  titleIcon?: React.ReactNode;
  /** 右侧操作区 */
  extra?: React.ReactNode;
  /** 内边距 */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** 是否显示边框 */
  bordered?: boolean;
  /** 自定义 className */
  className?: string;
}

const SECTION_PADDING_MAP = {
  none: '',
  sm: 'p-3',
  md: 'p-4 sm:p-6',
  lg: 'p-4 sm:p-8',
};

export const PageSection: React.FC<PageSectionProps> = ({
  children,
  title,
  titleIcon,
  extra,
  padding = 'md',
  bordered = true,
  className = '',
}) => {
  return (
    <div
      className={`rounded-xl bg-white ${SECTION_PADDING_MAP[padding]} ${className}`}
      style={{
        border: bordered ? '1px solid #e5e7eb' : 'none',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}
    >
      {(title || extra) && (
        <div className="flex items-center justify-between mb-4">
          {title && (
            <h6 className="text-lg font-semibold text-gray-900 flex items-center gap-2 m-0">
              {titleIcon && <span className="flex items-center">{titleIcon}</span>}
              {title}
            </h6>
          )}
          {extra && <div className="flex items-center gap-2">{extra}</div>}
        </div>
      )}
      {children}
    </div>
  );
};

/**
 * StatGrid 统计卡片网格
 * 替代 MUI Grid container，专门用于统计卡片布局
 */
export interface StatGridProps {
  children: React.ReactNode;
  /** 列数（响应式） */
  columns?: 2 | 3 | 4;
  /** 间距 */
  gap?: 'sm' | 'md' | 'lg';
  /** 自定义 className */
  className?: string;
}

const GRID_COLS_MAP = {
  2: 'grid-cols-1 sm:grid-cols-2',
  3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-2 sm:grid-cols-2 lg:grid-cols-4',
};

const GAP_MAP = {
  sm: 'gap-3',
  md: 'gap-4 sm:gap-5',
  lg: 'gap-5 sm:gap-6',
};

export const StatGrid: React.FC<StatGridProps> = ({
  children,
  columns = 4,
  gap = 'md',
  className = '',
}) => {
  return (
    <div className={`grid ${GRID_COLS_MAP[columns]} ${GAP_MAP[gap]} ${className}`}>
      {children}
    </div>
  );
};

export default PageContainer;
