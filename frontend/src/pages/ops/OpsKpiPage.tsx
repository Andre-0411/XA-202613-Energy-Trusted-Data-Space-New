/**
 * KPI 仪表盘页面
 * 顶部统计卡片 + ECharts 图表 + SLA/性能指标 Tab
 */
import React, { useState, useMemo } from 'react';
import { Tabs, Button } from 'tdesign-react';
import { RefreshIcon } from 'tdesign-icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getKpiDashboard, getSlaMetrics, getPerformanceMetrics } from '@/api/ops';
import type { KpiDashboard } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';

const KPI_CARDS: Array<{ key: keyof KpiDashboard; label: string; unit: string; color: string }> = [
  { key: 'total_assets', label: '数据资产总数', unit: '', color: '#2196f3' },
  { key: 'total_compute_tasks', label: '计算任务总数', unit: '', color: '#9c27b0' },
  { key: 'active_users', label: '活跃用户数', unit: '', color: '#4caf50' },
  { key: 'total_organizations', label: '组织总数', unit: '', color: '#ff9800' },
  { key: 'blockchain_transactions', label: '区块链交易数', unit: '', color: '#00bcd4' },
  { key: 'security_incidents', label: '安全事件数', unit: '', color: '#f44336' },
  { key: 'avg_response_time_ms', label: '平均响应时间', unit: 'ms', color: '#795548' },
  { key: 'uptime_percentage', label: '系统可用率', unit: '%', color: '#4caf50' },
  { key: 'data_quality_avg', label: '数据质量评分', unit: '', color: '#3f51b5' },
  { key: 'compliance_score', label: '合规评分', unit: '', color: '#009688' },
];

const OpsKpiPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState<string>('sla');

  const { data, isLoading } = useQuery({
    queryKey: ['kpiDashboard'],
    queryFn: () => getKpiDashboard(),
  });

  const { data: slaData } = useQuery({
    queryKey: ['slaMetrics'],
    queryFn: () => getSlaMetrics(),
  });

  const { data: perfData } = useQuery({
    queryKey: ['performanceMetrics'],
    queryFn: () => getPerformanceMetrics(),
  });

  const kpi: KpiDashboard | null = data?.data ?? null;

  // 柱状图 — 月度收入(模拟)
  const barOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    xAxis: {
      type: 'category' as const,
      data: ['1月', '2月', '3月', '4月', '5月', '6月'],
    },
    yAxis: { type: 'value' as const, name: '金额 (¥)' },
    series: [{
      type: 'bar' as const,
      data: [12000, 18000, 15000, 22000, 19000, 25000],
      itemStyle: { color: '#2196f3' },
    }],
    grid: { left: 60, right: 20, top: 30, bottom: 40 },
  }), []);

  // 饼图 — 服务收入分布
  const pieOption = useMemo(() => ({
    tooltip: { trigger: 'item' as const },
    series: [{
      type: 'pie' as const,
      radius: ['40%', '70%'],
      data: [
        { value: 35000, name: '数据共享' },
        { value: 25000, name: '计算服务' },
        { value: 18000, name: '存储服务' },
        { value: 12000, name: '安全服务' },
      ],
      label: { formatter: '{b}: ¥{c}' },
    }],
  }), []);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: 'KPI 仪表盘' }],
    [],
  );

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['kpiDashboard'] });
    queryClient.invalidateQueries({ queryKey: ['slaMetrics'] });
    queryClient.invalidateQueries({ queryKey: ['performanceMetrics'] });
  };

  return (
    <PageContainer>
      <PageHeader
        title="KPI 仪表盘"
        subtitle="系统关键绩效指标概览"
        breadcrumbs={breadcrumbs}
        iconActions={[
          { icon: <RefreshIcon />, onClick: handleRefresh, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-4">
        {KPI_CARDS.map((card) => (
          <div key={card.key} className="rounded-xl bg-white border border-gray-200 p-4">
            <p className="text-xs text-gray-400 mb-1">{card.label}</p>
            <p className="text-xl font-bold" style={{ color: card.color }}>
              {kpi ? `${kpi[card.key]}${card.unit}` : '—'}
            </p>
          </div>
        ))}
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
        <ChartCard title="月度收入统计" option={barOption} height={300} />
        <ChartCard title="服务收入分布" option={pieOption} height={300} />
      </div>

      {/* SLA & 性能指标 */}
      <div className="rounded-xl bg-white border border-gray-200">
        <Tabs value={tabValue} onChange={(val) => setTabValue(val as string)}>
          <Tabs.TabPanel value="sla" label="SLA 指标">
            <div className="p-4">
              {slaData?.data ? (
                <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-4 overflow-auto max-h-[400px]">
                  {JSON.stringify(slaData.data, null, 2)}
                </pre>
              ) : (
                <p className="text-gray-400 text-center py-8">暂无 SLA 数据</p>
              )}
            </div>
          </Tabs.TabPanel>
          <Tabs.TabPanel value="perf" label="性能指标">
            <div className="p-4">
              {perfData?.data ? (
                <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-4 overflow-auto max-h-[400px]">
                  {JSON.stringify(perfData.data, null, 2)}
                </pre>
              ) : (
                <p className="text-gray-400 text-center py-8">暂无性能数据</p>
              )}
            </div>
          </Tabs.TabPanel>
        </Tabs>
      </div>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default OpsKpiPage;
