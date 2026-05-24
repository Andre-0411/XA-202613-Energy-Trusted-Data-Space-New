/**
 * useECharts — ECharts 实例管理
 * 接受容器 ref 和 options，自动初始化/更新/销毁，自动处理 resize
 */
import { useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption, ECharts as EChartsInstance } from 'echarts';

interface UseEChartsReturn {
  /** ECharts 实例引用 */
  chart: EChartsInstance | null;
  /** 更新图表配置 */
  setOption: (option: EChartsOption, notMerge?: boolean) => void;
  /** 显示加载动画 */
  showLoading: (text?: string) => void;
  /** 隐藏加载动画 */
  hideLoading: () => void;
}

/**
 * ECharts 实例管理 hook
 * @param containerRef - 容器 DOM ref
 * @param options - ECharts 配置（传入后自动 setOption）
 * @returns 图表实例与操作方法
 */
export function useECharts(
  containerRef: React.RefObject<HTMLDivElement | null>,
  options?: EChartsOption,
): UseEChartsReturn {
  const chartRef = useRef<EChartsInstance | null>(null);

  /** 初始化图表 */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 若已有实例则跳过
    if (chartRef.current) return;

    const chart = echarts.init(container);
    chartRef.current = chart;

    // 若有初始 options 立即渲染
    if (options) {
      chart.setOption(options);
    }

    // 监听窗口 resize
    const handleResize = () => {
      chart.resize();
    };
    window.addEventListener('resize', handleResize);

    // 使用 ResizeObserver 监听容器尺寸变化
    const resizeObserver = new ResizeObserver(() => {
      chart.resize();
    });
    resizeObserver.observe(container);

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerRef]);

  /** options 变化时自动更新 */
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !options) return;
    chart.setOption(options, { notMerge: true });
  }, [options]);

  /** 手动 setOption */
  const setOption = useCallback((option: EChartsOption, notMerge = false) => {
    chartRef.current?.setOption(option, { notMerge });
  }, []);

  /** 显示加载动画 */
  const showLoading = useCallback((text = '加载中...') => {
    chartRef.current?.showLoading('default', {
      text,
      color: '#1976d2',
      textColor: '#333',
      maskColor: 'rgba(255, 255, 255, 0.8)',
    });
  }, []);

  /** 隐藏加载动画 */
  const hideLoading = useCallback(() => {
    chartRef.current?.hideLoading();
  }, []);

  return {
    chart: chartRef.current,
    setOption,
    showLoading,
    hideLoading,
  };
}

export default useECharts;
