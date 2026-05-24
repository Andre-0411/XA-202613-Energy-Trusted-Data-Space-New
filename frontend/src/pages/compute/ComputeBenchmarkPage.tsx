/**
 * 性能基准页面
 * ECharts 图表：各算法性能对比柱状图、任务执行时间趋势折线图、资源使用率面积图
 * 基准数据表格 + 导出报告按钮
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Select, Tag, MessagePlugin } from 'tdesign-react';
import { RefreshIcon, DownloadIcon, TrendingUpIcon } from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  getBenchmarkSummary, getBenchmarkTrends, runBenchmark, exportBenchmarkReport
} from '@/api/compute';
import type { AlgorithmBenchmark, BenchmarkTrendPoint } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';

/** 基准数据条目 */
interface BenchmarkRow {
  algorithm: string;
  avgTime: number;
  minTime: number;
  maxTime: number;
  throughput: number;
  cpuUsage: number;
  memUsage: number;
  taskCount: number;
}

/** 默认基准数据（无测试时展示） */
const DEFAULT_BENCHMARK: BenchmarkRow[] = [
  { algorithm: 'MPC', avgTime: 12.5, minTime: 8.2, maxTime: 25.1, throughput: 320, cpuUsage: 78, memUsage: 45, taskCount: 156 },
  { algorithm: 'FL', avgTime: 45.3, minTime: 30.1, maxTime: 89.5, throughput: 85, cpuUsage: 92, memUsage: 68, taskCount: 89 },
  { algorithm: 'TEE', avgTime: 3.2, minTime: 1.8, maxTime: 8.9, throughput: 1200, cpuUsage: 55, memUsage: 32, taskCount: 234 },
  { algorithm: 'HE', avgTime: 28.7, minTime: 15.4, maxTime: 56.2, throughput: 150, cpuUsage: 88, memUsage: 72, taskCount: 67 },
  { algorithm: 'DP', avgTime: 1.5, minTime: 0.8, maxTime: 4.2, throughput: 2800, cpuUsage: 35, memUsage: 18, taskCount: 312 },
  { algorithm: 'Sandbox', avgTime: 8.9, minTime: 5.1, maxTime: 18.3, throughput: 520, cpuUsage: 65, memUsage: 52, taskCount: 178 },
];

const TIME_RANGE_OPTIONS = [
  { label: '最近 24 小时', value: '24h' },
  { label: '最近 7 天', value: '7d' },
  { label: '最近 30 天', value: '30d' },
  { label: '最近 90 天', value: '90d' },
];

const ComputeBenchmarkPage: React.FC = () => {
  const [timeRange, setTimeRange] = useState<string>('7d');

  // ===== 数据查询 =====
  const { data: summaryData, isLoading: summaryLoading, refetch: refetchSummary } = useQuery({
    queryKey: ['benchmark-summary'],
    queryFn: () => getBenchmarkSummary(),
  });

  const { data: trendsData, isLoading: trendsLoading } = useQuery({
    queryKey: ['benchmark-trends', timeRange],
    queryFn: () => getBenchmarkTrends({ limit: 50 }),
  });

  // ===== 运行基准测试 =====
  const runBenchmarkMutation = useMutation({
    mutationFn: () => runBenchmark({
      algorithms: ['MPC', 'FL', 'TEE', 'HE', 'DP', 'Sandbox'],
      iterations: 10,
      data_size: 1000,
      participants: 2,
    }),
    onSuccess: () => {
      MessagePlugin.success('基准测试完成');
      refetchSummary();
    },
    onError: () => {
      MessagePlugin.error('基准测试失败');
    },
  });

  // 处理基准数据
  const benchmarkData: AlgorithmBenchmark[] = summaryData?.data?.latest_results ?? [];
  const trendData: BenchmarkTrendPoint[] = trendsData?.data ?? [];

  // 转换为表格行数据
  const benchmarkRows: BenchmarkRow[] = benchmarkData.length > 0
    ? benchmarkData.map((r) => ({
        algorithm: r.algorithm,
        avgTime: r.avg_time_ms / 1000,
        minTime: r.min_time_ms / 1000,
        maxTime: r.max_time_ms / 1000,
        throughput: r.throughput,
        cpuUsage: r.cpu_usage_percent,
        memUsage: (r.memory_usage_mb / 1024) * 100,
        taskCount: r.task_count,
      }))
    : DEFAULT_BENCHMARK;

  const isLoading = summaryLoading || trendsLoading;

  // ===== 算法性能对比柱状图 =====
  const barChartOption = useMemo(() => ({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['平均耗时(s)', '吞吐量(ops/s)'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: benchmarkRows.map((r) => r.algorithm),
    },
    yAxis: [
      { type: 'value', name: '耗时(s)', position: 'left' },
      { type: 'value', name: '吞吐量(ops/s)', position: 'right' },
    ],
    series: [
      {
        name: '平均耗时(s)',
        type: 'bar',
        data: benchmarkRows.map((r) => r.avgTime),
        itemStyle: { color: '#2196f3', borderRadius: [4, 4, 0, 0] },
        barWidth: '30%',
      },
      {
        name: '吞吐量(ops/s)',
        type: 'bar',
        yAxisIndex: 1,
        data: benchmarkRows.map((r) => r.throughput),
        itemStyle: { color: '#4caf50', borderRadius: [4, 4, 0, 0] },
        barWidth: '30%',
      },
    ],
  }), [benchmarkRows]);

  // ===== 任务执行时间趋势折线图 =====
  const trendChartOption = useMemo(() => {
    const algorithms = ['MPC', 'FL', 'TEE', 'HE', 'DP'];
    const timestamps = [...new Set(trendData.map((d) => d.timestamp))].slice(-7);
    
    if (timestamps.length === 0) {
      const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
      return {
        tooltip: { trigger: 'axis' },
        legend: { data: algorithms },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: days, boundaryGap: false },
        yAxis: { type: 'value', name: '平均耗时(s)' },
        series: [
          { name: 'MPC', type: 'line', data: [13.2, 12.1, 11.8, 12.5, 13.0, 12.8, 12.5], smooth: true, lineStyle: { width: 2 } },
          { name: 'FL', type: 'line', data: [48.5, 44.2, 46.1, 43.8, 45.3, 47.2, 45.3], smooth: true, lineStyle: { width: 2 } },
          { name: 'TEE', type: 'line', data: [3.5, 3.1, 3.2, 2.9, 3.2, 3.4, 3.2], smooth: true, lineStyle: { width: 2 } },
          { name: 'HE', type: 'line', data: [30.1, 27.8, 29.2, 28.5, 28.7, 30.5, 28.7], smooth: true, lineStyle: { width: 2 } },
          { name: 'DP', type: 'line', data: [1.6, 1.4, 1.5, 1.3, 1.5, 1.7, 1.5], smooth: true, lineStyle: { width: 2 } },
        ],
      };
    }

    const series = algorithms.map((algo) => {
      const algoData = trendData.filter((d) => d.algorithm === algo);
      const data = timestamps.map((ts) => {
        const point = algoData.find((d) => d.timestamp === ts);
        return point ? point.avg_time_ms / 1000 : null;
      });
      return {
        name: algo,
        type: 'line',
        data,
        smooth: true,
        lineStyle: { width: 2 },
        connectNulls: true,
      };
    });

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: algorithms },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: timestamps.map((ts) => new Date(ts).toLocaleDateString()),
        boundaryGap: false,
      },
      yAxis: { type: 'value', name: '平均耗时(s)' },
      series,
    };
  }, [trendData]);

  // ===== 资源使用率面积图 =====
  const areaChartOption = useMemo(() => {
    const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
    const generateData = (base: number, variance: number) =>
      hours.map(() => Math.round(base + (Math.random() - 0.5) * variance));
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['CPU 使用率', '内存使用率', '网络 I/O'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: hours, boundaryGap: false },
      yAxis: { type: 'value', name: '使用率(%)', min: 0, max: 100 },
      series: [
        {
          name: 'CPU 使用率',
          type: 'line',
          stack: 'resource',
          areaStyle: { opacity: 0.4 },
          data: generateData(65, 30),
          smooth: true,
          itemStyle: { color: '#2196f3' },
        },
        {
          name: '内存使用率',
          type: 'line',
          stack: 'resource',
          areaStyle: { opacity: 0.3 },
          data: generateData(50, 20),
          smooth: true,
          itemStyle: { color: '#4caf50' },
        },
        {
          name: '网络 I/O',
          type: 'line',
          stack: 'resource',
          areaStyle: { opacity: 0.2 },
          data: generateData(35, 25),
          smooth: true,
          itemStyle: { color: '#ff9800' },
        },
      ],
    };
  }, []);

  // ===== 导出报告 =====
  const exportMutation = useMutation({
    mutationFn: (benchmarkIds: string[]) => exportBenchmarkReport({
      benchmark_ids: benchmarkIds,
      format_type: 'json',
    }),
    onSuccess: (data) => {
      const reportData = data?.data;
      if (reportData) {
        const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `benchmark-report-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        MessagePlugin.success('报告导出成功');
      }
    },
    onError: () => {
      MessagePlugin.error('报告导出失败');
    },
  });

  const handleExport = useCallback(() => {
    const latestId = summaryData?.data?.latest_benchmark_id;
    if (latestId) {
      exportMutation.mutate([latestId]);
    } else {
      const reportData = {
        generated_at: new Date().toISOString(),
        time_range: timeRange,
        benchmark: benchmarkRows,
      };
      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `benchmark-report-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  }, [summaryData, timeRange, benchmarkRows, exportMutation]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '计算中心' }, { label: '性能基准' }],
    [],
  );

  return (
    <div className="flex flex-col gap-4 h-full overflow-auto">
      <PageHeader
        title="性能基准"
        subtitle="各算法性能对比分析、任务执行趋势与资源使用率监控"
        breadcrumbs={breadcrumbs}
        actions={[
          {
            label: '导出报告',
            icon: <DownloadIcon />,
            onClick: handleExport,
            variant: 'outlined',
          },
        ]}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => {},
            tooltip: '刷新',
          },
        ]}
      />

      {/* 时间范围选择 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <div className="flex items-center gap-4">
          <Select
            value={timeRange}
            onChange={(val) => setTimeRange(val as string)}
            options={TIME_RANGE_OPTIONS}
            style={{ width: 160 }}
          />
          <div className="flex-1" />
          <Button
            theme="primary"
            onClick={() => runBenchmarkMutation.mutate()}
            disabled={runBenchmarkMutation.isPending}
            loading={runBenchmarkMutation.isPending}
          >
            {runBenchmarkMutation.isPending ? '运行中...' : '运行基准测试'}
          </Button>
          <Tag icon={<TrendingUpIcon />} variant="outline">
            基于 {benchmarkRows.reduce((s, r) => s + r.taskCount, 0)} 个任务
          </Tag>
        </div>
      </div>

      {/* 图表区 */}
      <div className="flex flex-col gap-4">
        {/* 算法性能对比 */}
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <h3 className="text-sm font-bold text-gray-700 mb-2">算法性能对比</h3>
          <ReactECharts option={barChartOption} style={{ height: 300 }} />
        </div>

        {/* 执行时间趋势 */}
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <h3 className="text-sm font-bold text-gray-700 mb-2">任务执行时间趋势</h3>
          <ReactECharts option={trendChartOption} style={{ height: 300 }} />
        </div>

        {/* 资源使用率 */}
        <div className="rounded-xl bg-white border border-gray-200 p-4">
          <h3 className="text-sm font-bold text-gray-700 mb-2">资源使用率</h3>
          <ReactECharts option={areaChartOption} style={{ height: 300 }} />
        </div>
      </div>

      {/* 基准数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 p-4">
        <h3 className="text-sm font-bold text-gray-700 mb-3">基准数据明细</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left px-4 py-3 font-bold text-gray-600">算法</th>
                <th className="text-right px-4 py-3 font-bold text-gray-600">平均耗时(s)</th>
                <th className="text-right px-4 py-3 font-bold text-gray-600">最小耗时(s)</th>
                <th className="text-right px-4 py-3 font-bold text-gray-600">最大耗时(s)</th>
                <th className="text-right px-4 py-3 font-bold text-gray-600">吞吐量(ops/s)</th>
                <th className="text-right px-4 py-3 font-bold text-gray-600">CPU 使用率(%)</th>
                <th className="text-right px-4 py-3 font-bold text-gray-600">内存使用率(%)</th>
                <th className="text-right px-4 py-3 font-bold text-gray-600">任务数</th>
              </tr>
            </thead>
            <tbody>
              {benchmarkRows.map((row) => (
                <tr key={row.algorithm} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Tag variant="outline">{row.algorithm}</Tag>
                  </td>
                  <td className="text-right px-4 py-3 font-semibold">{row.avgTime.toFixed(1)}</td>
                  <td className="text-right px-4 py-3">{row.minTime.toFixed(1)}</td>
                  <td className="text-right px-4 py-3">{row.maxTime.toFixed(1)}</td>
                  <td className="text-right px-4 py-3 font-semibold">{row.throughput.toLocaleString()}</td>
                  <td className="text-right px-4 py-3">
                    <span className={`font-semibold ${row.cpuUsage > 80 ? 'text-red-500' : row.cpuUsage > 60 ? 'text-orange-500' : 'text-green-500'}`}>
                      {row.cpuUsage}%
                    </span>
                  </td>
                  <td className="text-right px-4 py-3">
                    <span className={`font-semibold ${row.memUsage > 70 ? 'text-red-500' : row.memUsage > 50 ? 'text-orange-500' : 'text-green-500'}`}>
                      {row.memUsage}%
                    </span>
                  </td>
                  <td className="text-right px-4 py-3">{row.taskCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <LoadingOverlay open={isLoading} />
    </div>
  );
};

export default ComputeBenchmarkPage;
