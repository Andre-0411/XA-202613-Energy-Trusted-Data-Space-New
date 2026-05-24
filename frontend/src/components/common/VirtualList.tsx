/**
 * VirtualList 虚拟滚动列表组件
 * 基于 IntersectionObserver 实现无限滚动加载，
 * 无需引入额外依赖。
 */
import React, { useRef, useEffect, useCallback } from 'react';
import { Loading } from 'tdesign-react';

export interface VirtualListProps<T = any> {
  /** 数据列表 */
  data: T[];
  /** 渲染单个列表项 */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** 容器高度（px） */
  height?: number;
  /** 单个列表项预估高度（px），用于 IntersectionObserver rootMargin */
  itemHeight?: number;
  /** 触底加载更多回调 */
  onLoadMore?: () => void;
  /** 是否还有更多数据 */
  hasMore?: boolean;
  /** 是否正在加载 */
  loading?: boolean;
  /** 自定义 className */
  className?: string;
}

/**
 * VirtualList 组件
 * 简单的无限滚动列表，使用 IntersectionObserver 检测底部 sentinel 元素
 */
const VirtualList = <T,>({
  data,
  renderItem,
  height = 600,
  itemHeight = 60,
  onLoadMore,
  hasMore = false,
  loading = false,
  className = '',
}: VirtualListProps<T>): React.ReactElement => {
  /** sentinel 引用 —— 底部标记元素 */
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  /** 容器引用 */
  const containerRef = useRef<HTMLDivElement | null>(null);

  /**
   * 当 sentinel 进入视口时触发加载更多。
   * 使用 useCallback 确保 observer 回调稳定性。
   */
  const handleIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry.isIntersecting && hasMore && !loading && onLoadMore) {
        onLoadMore();
      }
    },
    [hasMore, loading, onLoadMore],
  );

  useEffect(() => {
    const sentinel = sentinelRef.current;
    const container = containerRef.current;
    if (!sentinel || !container) return;

    const observer = new IntersectionObserver(handleIntersect, {
      root: container,
      rootMargin: `0px 0px ${itemHeight * 2}px 0px`,
      threshold: 0,
    });

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
    };
  }, [handleIntersect, itemHeight]);

  /** 空状态 */
  if (!loading && data.length === 0) {
    return (
      <div
        className={`flex flex-col items-center justify-center text-gray-400 ${className}`}
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
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
        <span className="text-sm mt-2">暂无数据</span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`overflow-auto rounded-xl bg-white ${className}`}
      style={{
        height,
        border: '1px solid #e5e7eb',
      }}
    >
      {/* 列表内容 */}
      <div className="divide-y divide-gray-100">
        {data.map((item, index) => (
          <div key={index} className="px-4 py-3">
            {renderItem(item, index)}
          </div>
        ))}
      </div>

      {/* 底部 sentinel 元素 */}
      <div ref={sentinelRef} style={{ height: 1 }} />

      {/* 加载状态 */}
      {loading && (
        <div className="flex items-center justify-center py-4">
          <Loading size="small" />
          <span className="text-sm text-gray-400 ml-2">加载中...</span>
        </div>
      )}

      {/* 没有更多数据 */}
      {!hasMore && data.length > 0 && (
        <div className="text-center text-xs text-gray-400 py-3">
          — 已加载全部数据 —
        </div>
      )}
    </div>
  );
};

export default VirtualList;
