/**
 * usePagination — 分页逻辑封装
 * 管理 page / pageSize / total 状态，输出 MUI TablePagination 兼容的 props
 */
import { useState, useCallback, useMemo } from 'react';

interface UsePaginationOptions {
  /** 初始页码（从 1 开始） */
  initialPage?: number;
  /** 初始每页条数 */
  initialPageSize?: number;
  /** 初始总条数 */
  initialTotal?: number;
}

interface PaginationProps {
  /** 当前页（MUI 从 0 开始） */
  page: number;
  /** 每页条数 */
  rowsPerPage: number;
  /** 总条数 */
  count: number;
  /** 页码变更回调（MUI 从 0 开始） */
  onPageChange: (_event: React.MouseEvent<HTMLButtonElement> | null, newPage: number) => void;
  /** 每页条数变更回调 */
  onRowsPerPageChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  /** 可选的每页条数选项 */
  rowsPerPageOptions: number[];
}

interface UsePaginationReturn {
  /** 当前页码（从 1 开始） */
  page: number;
  /** 每页条数 */
  pageSize: number;
  /** 总条数 */
  total: number;
  /** 总页数 */
  totalPages: number;
  /** 设置页码（从 1 开始） */
  setPage: (page: number) => void;
  /** 设置每页条数，同时重置到第一页 */
  setPageSize: (size: number) => void;
  /** 设置总条数 */
  setTotal: (total: number) => void;
  /** 可直接传给 MUI TablePagination 的 props */
  paginationProps: PaginationProps;
}

/**
 * 分页逻辑 hook
 * @param options - 初始配置
 * @returns 分页状态与操作方法
 */
export function usePagination(options: UsePaginationOptions = {}): UsePaginationReturn {
  const {
    initialPage = 1,
    initialPageSize = 10,
    initialTotal = 0,
  } = options;

  const [page, setPageState] = useState<number>(initialPage);
  const [pageSize, setPageSizeState] = useState<number>(initialPageSize);
  const [total, setTotalState] = useState<number>(initialTotal);

  /** 总页数（至少 1 页） */
  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / pageSize)),
    [total, pageSize],
  );

  /** 设置页码（1-based），自动 clamp */
  const setPage = useCallback(
    (newPage: number) => {
      setPageState(Math.max(1, Math.min(newPage, totalPages)));
    },
    [totalPages],
  );

  /** 设置每页条数，同时回到第一页 */
  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    setPageState(1);
  }, []);

  /** 设置总条数 */
  const setTotal = useCallback((newTotal: number) => {
    setTotalState(Math.max(0, newTotal));
  }, []);

  /** MUI TablePagination 兼容 props（MUI page 从 0 开始） */
  const paginationProps: PaginationProps = useMemo(
    () => ({
      page: page - 1,
      rowsPerPage: pageSize,
      count: total,
      rowsPerPageOptions: [10, 20, 50, 100],
      onPageChange: (_event, newPage) => {
        setPageState(newPage + 1);
      },
      onRowsPerPageChange: (event) => {
        const newSize = parseInt(event.target.value, 10);
        setPageSizeState(newSize);
        setPageState(1);
      },
    }),
    [page, pageSize, total],
  );

  return {
    page,
    pageSize,
    total,
    totalPages,
    setPage,
    setPageSize,
    setTotal,
    paginationProps,
  };
}

export default usePagination;
