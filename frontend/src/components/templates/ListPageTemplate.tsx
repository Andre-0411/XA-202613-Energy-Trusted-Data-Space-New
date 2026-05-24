/**
 * ListPageTemplate 标准列表页模板
 * 组合 PageHeader + StatsRow + FilterBar + DataTable，
 * 提供统一的列表页布局和交互模式。
 */
import React from 'react';
import PageHeader, { BreadcrumbItem, PageAction } from '../PageHeader';
import FilterBar, { FilterField } from '../common/FilterBar';
import StatsRow from '../common/StatsRow';
import StatCard from '../common/StatCard';
import DataTable, { DataTableColumn } from '../common/DataTable';

export interface ListPageTemplateProps {
  /** 页面标题 */
  title: string;
  /** 页面副标题 */
  subtitle?: string;
  /** 面包屑导航 */
  breadcrumbs: BreadcrumbItem[];
  /** 页面操作按钮 */
  actions?: PageAction[];

  /* ---- 筛选栏 ---- */
  /** 筛选字段定义 */
  filterFields?: FilterField[];
  /** 当前筛选值 */
  filterValues?: Record<string, any>;
  /** 筛选值变更回调 */
  onFilterChange?: (name: string, value: any) => void;
  /** 搜索回调 */
  onSearch?: () => void;
  /** 重置回调 */
  onReset?: () => void;

  /* ---- 统计卡片 ---- */
  /** 顶部统计数据 */
  stats?: Array<{
    title: string;
    value: number | string;
    icon?: React.ReactNode;
    color?: string;
    unit?: string;
    gradient?: string;
    trend?: number;
  }>;

  /* ---- 数据表格 ---- */
  /** 表格列定义 */
  columns: DataTableColumn[];
  /** 表格数据 */
  data: any[];
  /** 是否加载中 */
  loading?: boolean;
  /** 当前页码（从 0 开始） */
  page?: number;
  /** 每页条数 */
  pageSize?: number;
  /** 总条数 */
  total?: number;
  /** 页码变更回调 */
  onPageChange?: (page: number) => void;
  /** 行点击回调 */
  onRowClick?: (row: any) => void;

  /** 自定义内容（放在表格下方） */
  children?: React.ReactNode;
}

/**
 * ListPageTemplate 组件
 * 标准列表页布局：页头 → 统计 → 筛选栏 → 数据表格 → 自定义内容
 */
const ListPageTemplate: React.FC<ListPageTemplateProps> = ({
  title,
  subtitle,
  breadcrumbs,
  actions,
  filterFields,
  filterValues,
  onFilterChange,
  onSearch,
  onReset,
  stats,
  columns,
  data,
  loading = false,
  page = 0,
  pageSize = 10,
  total = 0,
  onPageChange,
  onRowClick,
  children,
}) => {
  return (
    <div>
      {/* 页头 */}
      <PageHeader
        title={title}
        subtitle={subtitle}
        breadcrumbs={breadcrumbs}
        actions={actions}
      />

      {/* 统计卡片行 */}
      {stats && stats.length > 0 && (
        <StatsRow columns={Math.min(stats.length, 4)}>
          {stats.map((s, idx) => (
            <StatCard
              key={`stat-${idx}`}
              title={s.title}
              value={typeof s.value === 'number' ? s.value : Number(s.value) || 0}
              unit={s.unit || ''}
              icon={s.icon || <span />}
              gradient={(s.color as any) || 'blue'}
              trend={s.trend}
            />
          ))}
        </StatsRow>
      )}

      {/* 筛选栏 */}
      {filterFields && filterFields.length > 0 && filterValues && onFilterChange && (
        <div className="mb-4">
          <FilterBar
            fields={filterFields}
            values={filterValues}
            onChange={onFilterChange}
            onSearch={onSearch}
            onReset={onReset}
          />
        </div>
      )}

      {/* 数据表格 */}
      <DataTable
        columns={columns}
        data={data}
        loading={loading}
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={onPageChange}
        onRowClick={onRowClick}
      />

      {/* 自定义内容 */}
      {children}
    </div>
  );
};

export default ListPageTemplate;
