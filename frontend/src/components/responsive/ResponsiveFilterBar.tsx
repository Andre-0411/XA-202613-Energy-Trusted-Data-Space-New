/**
 * ResponsiveFilterBar 响应式筛选栏组件
 * 桌面端水平排列，移动端垂直堆叠
 * 已从 MUI Stack/Button/Collapse 迁移至 TDesign Button + Tailwind
 */
import React, { useState } from 'react';
import { Button } from 'tdesign-react';
import { FilterIcon, ChevronDownIcon, ChevronUpIcon, RefreshIcon } from 'tdesign-icons-react';

interface ResponsiveFilterBarProps {
  /** 筛选项（通常是 Select、TextField 等筛选控件） */
  children: React.ReactNode;
  /** 操作按钮（如搜索、重置） */
  actions?: React.ReactNode;
  /** 移动端是否可折叠（默认 true） */
  collapsible?: boolean;
  /** 移动端初始是否展开（默认 false） */
  defaultExpanded?: boolean;
  /** 是否显示清除筛选按钮 */
  showClear?: boolean;
  /** 清除筛选回调 */
  onClear?: () => void;
  /** 容器 className */
  className?: string;
  /** 容器 style */
  style?: React.CSSProperties;
}

/**
 * ResponsiveFilterBar
 * 桌面端：水平排列，flexWrap 允许换行
 * 移动端：垂直堆叠，支持折叠/展开
 */
const ResponsiveFilterBar: React.FC<ResponsiveFilterBarProps> = ({
  children,
  actions,
  collapsible = true,
  defaultExpanded = false,
  showClear = false,
  onClear,
  className = '',
  style,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 900;

  /** 桌面端：水平布局 */
  if (!isMobile) {
    return (
      <div
        className={`flex items-center flex-wrap gap-4 mb-6 ${className}`}
        style={style}
      >
        {children}
        <div className="ml-auto flex gap-2">
          {showClear && onClear && (
            <Button
              size="small"
              icon={<RefreshIcon />}
              variant="text"
              onClick={onClear}
            >
              重置
            </Button>
          )}
          {actions}
        </div>
      </div>
    );
  }

  /** 移动端：垂直堆叠 + 可折叠 */
  return (
    <div className={`mb-4 ${className}`} style={style}>
      {/* 折叠触发器 */}
      {collapsible && (
        <Button
          block
          variant="text"
          icon={<FilterIcon />}
          suffix={expanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
          onClick={() => setExpanded(!expanded)}
          style={{
            justifyContent: 'space-between',
            marginBottom: expanded ? 8 : 0,
            color: 'var(--td-text-color-secondary, rgba(0,0,0,0.6))',
            fontWeight: 500,
          }}
        >
          <span style={{ fontSize: '0.875rem' }}>
            筛选条件
          </span>
        </Button>
      )}

      {/* 筛选内容 */}
      <div
        style={{
          display: (!collapsible || expanded) ? 'block' : 'none',
        }}
      >
        <div className="flex flex-col gap-4">
          {children}
          <div className="flex gap-2 justify-end">
            {showClear && onClear && (
              <Button
                size="small"
                icon={<RefreshIcon />}
                variant="text"
                onClick={onClear}
              >
                重置
              </Button>
            )}
            {actions}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResponsiveFilterBar;
