/**
 * FilterBar 搜索筛选栏组件
 * 基于 TDesign Input + Select + Button 的统一筛选栏
 * 替代 MUI Stack + TextField + Select 的筛选模式
 */
import React from 'react';
import { Input, Select, Button } from 'tdesign-react';
import { SearchIcon, RefreshIcon } from 'tdesign-icons-react';

export interface FilterField {
  /** 字段名 */
  name: string;
  /** 类型 */
  type: 'text' | 'select';
  /** 占位文本 */
  placeholder?: string;
  /** 下拉选项（type=select 时必填） */
  options?: Array<{ label: string; value: string | number }>;
  /** 宽度 */
  width?: number;
}

export interface FilterBarProps {
  /** 筛选字段列表 */
  fields: FilterField[];
  /** 当前值 */
  values: Record<string, any>;
  /** 值变更回调 */
  onChange: (name: string, value: any) => void;
  /** 搜索回调 */
  onSearch?: () => void;
  /** 重置回调 */
  onReset?: () => void;
  /** 右侧额外操作 */
  extra?: React.ReactNode;
  /** 自定义 className */
  className?: string;
}

/**
 * FilterBar 组件
 * 统一的搜索筛选栏，支持文本输入和下拉选择
 */
const FilterBar: React.FC<FilterBarProps> = ({
  fields,
  values,
  onChange,
  onSearch,
  onReset,
  extra,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-wrap items-center gap-3 p-4 rounded-xl bg-white ${className}`}
      style={{ border: '1px solid #e5e7eb' }}
    >
      {fields.map((field) => {
        if (field.type === 'text') {
          return (
            <Input
              key={field.name}
              value={values[field.name] ?? ''}
              onChange={(val) => onChange(field.name, val)}
              placeholder={field.placeholder}
              prefixIcon={<SearchIcon />}
              clearable
              style={{ width: field.width ?? 240 }}
            />
          );
        }

        if (field.type === 'select') {
          return (
            <Select
              key={field.name}
              value={values[field.name] ?? ''}
              onChange={(val) => onChange(field.name, val)}
              options={field.options || []}
              placeholder={field.placeholder}
              clearable
              style={{ width: field.width ?? 160 }}
            />
          );
        }

        return null;
      })}

      {onSearch && (
        <Button theme="primary" onClick={onSearch}>
          搜索
        </Button>
      )}

      {onReset && (
        <Button
          variant="outline"
          theme="default"
          icon={<RefreshIcon />}
          onClick={onReset}
        >
          重置
        </Button>
      )}

      {extra && <div className="ml-auto">{extra}</div>}
    </div>
  );
};

export default FilterBar;
