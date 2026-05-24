/**
 * SearchBar 搜索栏组件
 * 输入框 + 搜索按钮 + 可选筛选器 Chips
 * 迁移自 MUI → TDesign + Tailwind CSS
 */
import React, { useCallback } from 'react';
import { Input, Tag, Button } from 'tdesign-react';
import { SearchIcon, CloseIcon } from 'tdesign-icons-react';

/** 筛选项定义 */
export interface SearchFilter {
  /** 筛选项 key */
  key: string;
  /** 显示标签 */
  label: string;
  /** 是否激活 */
  active: boolean;
}

interface SearchBarProps {
  /** 搜索关键词 */
  value: string;
  /** 关键词变更回调 */
  onChange: (value: string) => void;
  /** 占位符 */
  placeholder?: string;
  /** 点击搜索按钮或按回车时触发 */
  onSearch?: () => void;
  /** 可选筛选器列表 */
  filters?: SearchFilter[];
  /** 筛选器切换回调 */
  onFilterChange?: (key: string, active: boolean) => void;
  /** 自定义 className */
  className?: string;
}

/**
 * SearchBar 搜索栏
 * 支持关键词搜索与筛选器 Chips
 */
const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  placeholder = '搜索...',
  onSearch,
  filters = [],
  onFilterChange,
  className = '',
}) => {
  /** 按下回车触发搜索 */
  const handleKeyDown = useCallback(
    (_value: string, context: { e: React.KeyboardEvent }) => {
      if (context.e.key === 'Enter' && onSearch) {
        onSearch();
      }
    },
    [onSearch],
  );

  /** 切换筛选器 */
  const handleFilterToggle = useCallback(
    (key: string, currentActive: boolean) => {
      onFilterChange?.(key, !currentActive);
    },
    [onFilterChange],
  );

  return (
    <div className={className}>
      {/* 搜索输入框 */}
      <Input
        value={value}
        onChange={onChange}
        onKeydown={handleKeyDown}
        placeholder={placeholder}
        prefixIcon={<SearchIcon size="16px" className="text-gray-400" />}
        suffix={
          value ? (
            <Button
              variant="text"
              theme="default"
              size="small"
              icon={<CloseIcon size="14px" />}
              onClick={() => onChange('')}
              aria-label="清除搜索"
            />
          ) : null
        }
        size="small"
        style={{ borderRadius: 8 }}
      />

      {/* 筛选器 Chips */}
      {filters.length > 0 && (
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {filters.map((filter) => (
            <Tag
              key={filter.key}
              theme={filter.active ? 'primary' : 'default'}
              variant={filter.active ? 'light' : 'outline'}
              size="small"
              onClick={() => handleFilterToggle(filter.key, filter.active)}
              style={{
                fontWeight: filter.active ? 600 : 400,
                cursor: 'pointer',
              }}
            >
              {filter.label}
            </Tag>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
