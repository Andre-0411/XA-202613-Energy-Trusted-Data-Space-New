/**
 * DataTable 增强数据表格组件
 * 基于 tdesign-react Table + Pagination
 * 迁移自 MUI Table → tdesign-react Table
 */
import React from 'react';
import { Table, Pagination } from 'tdesign-react';
import { FileIcon as InboxIcon } from 'tdesign-icons-react';

/** 列定义（保持原有接口不变） */
export interface DataTableColumn<T = Record<string, unknown>> {
  /** 列唯一标识 */
  id: string;
  /** 列标题 */
  label: string;
  /** 最小宽度 */
  minWidth?: number;
  /** 对齐方式 */
  align?: 'left' | 'center' | 'right';
  /** 自定义渲染（接收行数据与行索引） */
  render?: (row: T, index: number) => React.ReactNode;
  /** 是否可排序 */
  sortable?: boolean;
  /** sx（已废弃，保留接口兼容） */
  cellSx?: Record<string, any>;
}

export interface DataTableProps<T = Record<string, unknown>> {
  /** 列定义 */
  columns: DataTableColumn<T>[];
  /** 行数据 */
  data?: T[];
  /** 行数据（别名，与 data 二选一） */
  rows?: T[];
  /** 是否加载中 */
  loading?: boolean;
  /** 当前页码（从 0 开始） */
  page?: number;
  /** 每页条数 */
  pageSize?: number;
  /** 总条数 */
  total?: number;
  /** 页码变更回调（接收从 0 开始的页码） */
  onPageChange?: (newPage: number) => void;
  /** 每页条数变更回调 */
  onPageSizeChange?: (newPageSize: number) => void;
  /** 行点击回调 */
  onRowClick?: (row: T, index: number) => void;
  /** 空状态提示文本 */
  emptyMessage?: string;
  /** 是否使用固定表头 */
  stickyHeader?: boolean;
  /** 容器 className */
  className?: string;
}

/** 每页条数选项 */
const PAGE_SIZE_OPTIONS = [
  { label: '10 条/页', value: 10 },
  { label: '20 条/页', value: 20 },
  { label: '50 条/页', value: 50 },
  { label: '100 条/页', value: 100 },
];

/**
 * DataTable 增强数据表格
 * 封装 tdesign-react Table 常见模式：分页、加载状态、空状态
 */
const DataTable = <T extends Record<string, any>>({
  columns,
  data,
  rows,
  loading = false,
  page = 0,
  pageSize = 10,
  total = 0,
  onPageChange,
  onPageSizeChange,
  onRowClick,
  emptyMessage = '暂无数据',
  stickyHeader = true,
  className,
}: DataTableProps<T>): React.ReactElement => {
  const effectiveData = rows ?? data ?? [];

  /** 将内部列定义转换为 tdesign-react Table 列格式 */
  const tdColumns = columns.map((col) => ({
    colKey: col.id,
    title: col.label,
    width: col.minWidth,
    align: col.align as 'left' | 'center' | 'right' | undefined,
    sorter: col.sortable || undefined,
    render: col.render
      ? ({ row, rowIndex }: { row: T; rowIndex: number }) => {
          return col.render!(row, rowIndex);
        }
      : undefined,
  }));

  /** 自定义空状态 */
  const emptyRender = (
    <div className="flex flex-col items-center gap-2 py-12">
      <InboxIcon style={{ fontSize: 48, color: '#bdbdbd' }} />
      <span className="text-sm text-gray-400">{emptyMessage}</span>
    </div>
  );

  /** 分页变更处理（tdesign Pagination 使用从 1 开始的页码） */
  const handlePageChange = (pageInfo: any) => {
    const current = pageInfo?.current ?? pageInfo ?? 1;
    if (onPageChange) {
      onPageChange(current - 1); // 转换回从 0 开始
    }
    if (onPageSizeChange && pageInfo?.pageSize !== undefined) {
      onPageSizeChange(pageInfo.pageSize);
    }
  };

  return (
    <div
      className={`w-full overflow-hidden rounded-lg border border-gray-200 ${className ?? ''}`}
    >
      <Table
        data={effectiveData}
        columns={tdColumns}
        loading={loading}
        rowKey="id"
        hover
        bordered={false}
        stripe
        empty={emptyRender}
        onRowClick={
          onRowClick
            ? ({ row, index }: { row: T; index: number }) =>
                onRowClick(row, index)
            : undefined
        }
        maxHeight={stickyHeader ? 480 : undefined}
        size="small"
        tableLayout="auto"
      />

      {/* 分页 */}
      {(total > 0 || onPageChange) && (
        <div
          className="flex flex-wrap items-center justify-end px-4 py-2 border-t border-gray-200"
          style={{ gap: 8 }}
        >
          <Pagination
            current={page + 1} // 转换为从 1 开始
            pageSize={pageSize}
            total={total}
            onChange={handlePageChange}
            onPageSizeChange={(size: number) => onPageSizeChange?.(size)}
            showJumper
            showPageSize
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            size="small"
          />
        </div>
      )}
    </div>
  );
};

/** Column type alias — many pages import { Column } from DataTable */
export type Column<T = Record<string, unknown>> = DataTableColumn<T>;

export default DataTable;
