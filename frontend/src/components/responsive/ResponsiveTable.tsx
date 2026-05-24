/**
 * ResponsiveTable 响应式表格组件
 * 桌面端显示标准表格，移动端显示卡片视图
 * 已从 MUI Table/Card/Skeleton 迁移至 TDesign Table + Tailwind
 */
import React from 'react';
import { Table, Pagination } from 'tdesign-react';
import { FileIcon as InboxIcon } from 'tdesign-icons-react';

/** 列定义 */
export interface ResponsiveTableColumn<T = Record<string, unknown>> {
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
  /** 样式（已废弃，保留接口兼容） */
  cellSx?: Record<string, any>;
  /** 移动端卡片中是否隐藏此列 */
  hideOnMobile?: boolean;
  /** 移动端卡片中是否作为主标题显示 */
  isPrimary?: boolean;
  /** 移动端卡片中是否作为副标题显示 */
  isSecondary?: boolean;
}

interface ResponsiveTableProps<T = Record<string, unknown>> {
  /** 列定义 */
  columns: ResponsiveTableColumn<T>[];
  /** 行数据 */
  data: T[];
  /** 是否加载中 */
  loading?: boolean;
  /** 当前页码（从 0 开始） */
  page?: number;
  /** 每页条数 */
  pageSize?: number;
  /** 总条数 */
  total?: number;
  /** 页码变更回调 */
  onPageChange?: (newPage: number) => void;
  /** 每页条数变更回调 */
  onPageSizeChange?: (newPageSize: number) => void;
  /** 行点击回调 */
  onRowClick?: (row: T, index: number) => void;
  /** 空状态提示文本 */
  emptyMessage?: string;
  /** 是否使用固定表头 */
  stickyHeader?: boolean;
  /** 移动端卡片中额外的操作按钮渲染 */
  renderCardActions?: (row: T, index: number) => React.ReactNode;
  /** 容器 className */
  className?: string;
}

/** Loading 骨架行数 */
const SKELETON_ROWS = 3;

/** 每页条数选项 */
const PAGE_SIZE_OPTIONS = [
  { label: '10 条/页', value: 10 },
  { label: '20 条/页', value: 20 },
  { label: '50 条/页', value: 50 },
  { label: '100 条/页', value: 100 },
];

/**
 * ResponsiveTable 响应式表格
 * 桌面端(md+)显示标准表格，移动端(xs/sm)显示卡片视图
 */
const ResponsiveTable = <T extends Record<string, unknown>>({
  columns,
  data,
  loading = false,
  page = 0,
  pageSize = 10,
  total = 0,
  onPageChange,
  onPageSizeChange,
  onRowClick,
  emptyMessage = '暂无数据',
  stickyHeader = true,
  renderCardActions,
  className = '',
}: ResponsiveTableProps<T>): React.ReactElement => {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 900;

  /** 从行数据中安全取值 */
  const getCellValue = (row: T, columnId: string): unknown => {
    return row[columnId as keyof T];
  };

  /** 骨架占位动画 */
  const SkeletonLine: React.FC<{ width?: string }> = ({ width = '80%' }) => (
    <div
      className="rounded bg-gray-200 animate-pulse"
      style={{ width, height: 16, marginBottom: 4 }}
    />
  );

  /** 渲染加载骨架 */
  const renderSkeleton = (): React.ReactNode => {
    if (isMobile) {
      return Array.from({ length: SKELETON_ROWS }).map((_, i) => (
        <div
          key={`skeleton-card-${i}`}
          className="border border-gray-200 rounded-lg mb-2 p-3"
        >
          <SkeletonLine width="60%" />
          <SkeletonLine width="40%" />
          <SkeletonLine width="80%" />
        </div>
      ));
    }
    return Array.from({ length: SKELETON_ROWS }).map((_, rowIndex) => (
      <tr key={`skeleton-${rowIndex}`}>
        {columns.map((col) => (
          <td
            key={`skeleton-cell-${col.id}`}
            className="px-4 py-3"
            style={{ textAlign: col.align || 'left' }}
          >
            <SkeletonLine />
          </td>
        ))}
      </tr>
    ));
  };

  /** 渲染空状态 */
  const renderEmpty = (): React.ReactNode => {
    return (
      <div className="flex flex-col items-center gap-2 py-12">
        <InboxIcon style={{ fontSize: 48, color: '#bdbdbd' }} />
        <span className="text-sm text-gray-400">{emptyMessage}</span>
      </div>
    );
  };

  /** 移动端卡片视图 */
  const renderMobileCards = (): React.ReactNode => {
    if (loading && data.length === 0) return renderSkeleton();
    if (data.length === 0) return renderEmpty();

    return data.map((row, rowIndex) => {
      const primaryCol = columns.find((c) => c.isPrimary);
      const secondaryCol = columns.find((c) => c.isSecondary);
      const detailCols = columns.filter(
        (c) => !c.isPrimary && !c.isSecondary && !c.hideOnMobile
      );

      return (
        <div
          key={`card-${rowIndex}`}
          className={`border border-gray-200 rounded-lg mb-2 transition-all duration-150 ${
            onRowClick ? 'cursor-pointer hover:shadow-md hover:border-blue-400 active:scale-[0.99]' : ''
          }`}
          onClick={onRowClick ? () => onRowClick(row, rowIndex) : undefined}
          style={{ background: '#fff' }}
        >
          <div className="p-3 pb-2">
            {/* 主标题行 */}
            {primaryCol && (
              <div className="flex justify-between items-start">
                <span className="text-base font-semibold truncate flex-1">
                  {primaryCol.render
                    ? primaryCol.render(row, rowIndex)
                    : (getCellValue(row, primaryCol.id) as React.ReactNode) ?? '-'}
                </span>
                {renderCardActions && (
                  <div className="ml-2 flex-shrink-0">
                    {renderCardActions(row, rowIndex)}
                  </div>
                )}
              </div>
            )}

            {/* 副标题 */}
            {secondaryCol && (
              <span className="text-sm text-gray-500 mt-1 block">
                {secondaryCol.render
                  ? secondaryCol.render(row, rowIndex)
                  : (getCellValue(row, secondaryCol.id) as React.ReactNode) ?? '-'}
              </span>
            )}

            {/* 详细字段 */}
            {detailCols.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {detailCols.map((col) => {
                  const value = col.render
                    ? col.render(row, rowIndex)
                    : (getCellValue(row, col.id) as React.ReactNode) ?? '-';
                  return (
                    <div key={col.id} style={{ minWidth: '45%' }}>
                      <span className="text-xs text-gray-400 block">
                        {col.label}
                      </span>
                      <span className="text-sm font-medium">
                        {value}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      );
    });
  };

  /** 将内部列定义转换为 TDesign Table 列格式 */
  const tdColumns = columns.map((col) => ({
    colKey: col.id,
    title: col.label,
    width: col.minWidth,
    align: col.align as 'left' | 'center' | 'right' | undefined,
    render: col.render
      ? ({ row, rowIndex }: { row: T; rowIndex: number }) => {
          return col.render!(row, rowIndex);
        }
      : undefined,
  }));

  /** 桌面端表格视图 */
  const renderDesktopTable = (): React.ReactNode => {
    return (
      <Table
        data={data}
        columns={tdColumns}
        loading={loading && data.length === 0}
        rowKey="id"
        hover
        bordered={false}
        stripe
        empty={renderEmpty()}
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
    );
  };

  /** 分页变更处理（TDesign Pagination 使用从 1 开始的页码） */
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
      className={`w-full overflow-hidden rounded-lg border border-gray-200 ${className}`}
      style={{ background: '#fff' }}
    >
      {/* 顶部加载进度条 */}
      {loading && (
        <div className="w-full h-0.5 bg-gray-100 overflow-hidden">
          <div
            className="h-full bg-blue-500 animate-pulse"
            style={{ width: '30%', transition: 'width 0.3s' }}
          />
        </div>
      )}

      {/* 内容区域 */}
      <div style={{ padding: isMobile ? 6 : 0 }}>
        {isMobile ? renderMobileCards() : renderDesktopTable()}
      </div>

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

export default ResponsiveTable;
