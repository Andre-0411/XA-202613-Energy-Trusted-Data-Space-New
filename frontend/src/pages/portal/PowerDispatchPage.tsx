/**
 * 电网调度优化页面
 * 负荷预测 + 发电计划 + 调度指令 + AI调度建议
 */
import React, { useState, useMemo } from 'react';
import { Card, Tag, Button, Table, MessagePlugin, Dialog } from 'tdesign-react';
import {
  FlashlightIcon, ChartLineIcon, TimeIcon, RobotIcon,
  TrendingUpIcon, RefreshIcon, PlayIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

// ===== 模拟数据 =====
const LOAD_FORECAST = {
  hours: ['00:00','02:00','04:00','06:00','08:00','10:00','12:00','14:00','16:00','18:00','20:00','22:00'],
  actual: [2100, 1800, 1650, 1900, 2800, 3200, 3500, 3300, 3100, 3400, 3000, 2500],
  forecast: [2050, 1750, 1600, 1850, 2750, 3150, 3450, 3250, 3050, 3350, 2950, 2450],
};

const DISPATCH_ORDERS = [
  { id: 'DO-20260525-001', time: '2026-05-25 08:30', target: '华能风电场A', action: '增加出力', value: '+50MW', status: 'executed', priority: 'high' },
  { id: 'DO-20260525-002', time: '2026-05-25 09:15', target: '三峡光伏站B', action: '限制出力', value: '-30MW', status: 'executed', priority: 'medium' },
  { id: 'DO-20260525-003', time: '2026-05-25 10:00', target: '龙源储能站', action: '充电调度', value: '20MWh', status: 'pending', priority: 'high' },
  { id: 'DO-20260525-004', time: '2026-05-25 11:30', target: '中广核风电场', action: 'AGC调节', value: '自动', status: 'running', priority: 'low' },
];

const AI_SUGGESTIONS = [
  { time: '14:00', suggestion: '预测负荷高峰，建议提前启动备用机组', confidence: 92 },
  { time: '16:30', suggestion: '风电出力下降，建议增加光伏出力补偿', confidence: 87 },
  { time: '18:00', suggestion: '晚高峰来临，建议储能放电削峰', confidence: 95 },
];

const PowerDispatchPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'forecast' | 'orders' | 'ai'>('forecast');

  const breadcrumbs: BreadcrumbItem[] = [
    homeBreadcrumb,
    { label: '业务场景' },
    { label: '电网调度优化' },
  ];

  const stats = useMemo(() => [
    { title: '当前负荷', value: 3200, unit: 'MW', icon: <FlashlightIcon />, gradient: 'blue', trend: 5.2 },
    { title: '预测准确率', value: 96.8, unit: '%', icon: <ChartLineIcon />, gradient: 'green', trend: 1.2 },
    { title: '今日调度指令', value: 47, unit: '条', icon: <TimeIcon />, gradient: 'purple', trend: 12 },
    { title: 'AI建议采纳率', value: 89, unit: '%', icon: <RobotIcon />, gradient: 'orange', trend: 3.5 },
  ], []);

  const forecastChart = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['实际负荷', '预测负荷'], top: 5 },
    xAxis: { type: 'category' as const, data: LOAD_FORECAST.hours },
    yAxis: { type: 'value' as const, name: 'MW' },
    series: [
      { name: '实际负荷', type: 'line' as const, data: LOAD_FORECAST.actual, smooth: true, itemStyle: { color: '#1976d2' } },
      { name: '预测负荷', type: 'line' as const, data: LOAD_FORECAST.forecast, smooth: true, lineStyle: { type: 'dashed' as const }, itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const orderColumns = [
    { title: '指令编号', colKey: 'id', width: 160 },
    { title: '时间', colKey: 'time', width: 160 },
    { title: '目标', colKey: 'target', width: 140 },
    { title: '操作', colKey: 'action', width: 100 },
    { title: '调整量', colKey: 'value', width: 100 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: any }) => {
        const map: Record<string, { label: string; theme: string }> = {
          executed: { label: '已执行', theme: 'success' },
          running: { label: '执行中', theme: 'warning' },
          pending: { label: '待执行', theme: 'default' },
        };
        const s = map[row.status] || map.pending;
        return <Tag theme={s.theme as any} variant="light">{s.label}</Tag>;
      },
    },
    {
      title: '优先级', colKey: 'priority', width: 100,
      cell: ({ row }: { row: any }) => {
        const map: Record<string, { label: string; theme: string }> = {
          high: { label: '高', theme: 'danger' },
          medium: { label: '中', theme: 'warning' },
          low: { label: '低', theme: 'success' },
        };
        const p = map[row.priority] || map.low;
        return <Tag theme={p.theme as any} variant="outline">{p.label}</Tag>;
      },
    },
  ];

  return (
    <PageContainer>
      <PageHeader title="电网调度优化" subtitle="基于AI的智能电网调度系统" breadcrumbs={breadcrumbs} />

      {/* 统计卡片 */}
      <PageSection>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6">
          {stats.map((s, i) => <StatCard key={i} {...s} />)}
        </div>
      </PageSection>

      {/* 标签页切换 */}
      <PageSection>
        <div className="flex gap-2 mb-4">
          {[
            { key: 'forecast', label: '负荷预测', icon: <ChartLineIcon size="14px" /> },
            { key: 'orders', label: '调度指令', icon: <TimeIcon size="14px" /> },
            { key: 'ai', label: 'AI调度建议', icon: <RobotIcon size="14px" /> },
          ].map(tab => (
            <Button
              key={tab.key}
              theme={activeTab === tab.key ? 'primary' : 'default'}
              variant={activeTab === tab.key ? 'base' : 'outline'}
              icon={tab.icon}
              onClick={() => setActiveTab(tab.key as any)}
              size="small"
            >
              {tab.label}
            </Button>
          ))}
        </div>

        {activeTab === 'forecast' && (
          <ChartCard title="24小时负荷预测" chipLabel="今日" option={forecastChart} height={350} />
        )}

        {activeTab === 'orders' && (
          <Card className="rounded-xl shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold m-0">调度指令列表</h3>
              <Button theme="primary" size="small" icon={<RefreshIcon />}>刷新</Button>
            </div>
            <Table data={DISPATCH_ORDERS} columns={orderColumns} rowKey="id" />
          </Card>
        )}

        {activeTab === 'ai' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="rounded-xl shadow-sm">
              <h3 className="text-base font-semibold mb-4 m-0 flex items-center gap-2">
                <RobotIcon size="18px" /> AI调度建议
              </h3>
              <div className="flex flex-col gap-3">
                {AI_SUGGESTIONS.map((s, i) => (
                  <div key={i} className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-blue-800">{s.time}</span>
                      <Tag theme="primary" variant="light">置信度 {s.confidence}%</Tag>
                    </div>
                    <p className="text-sm text-gray-700 m-0">{s.suggestion}</p>
                  </div>
                ))}
              </div>
            </Card>
            <ChartCard title="调度准确率趋势" chipLabel="近7天" option={{
              tooltip: { trigger: 'axis' as const },
              xAxis: { type: 'category' as const, data: ['周一','周二','周三','周四','周五','周六','周日'] },
              yAxis: { type: 'value' as const, max: 100 },
              series: [{ type: 'line' as const, data: [94, 95, 96, 95, 97, 96, 97], smooth: true, areaStyle: { opacity: 0.3 }, itemStyle: { color: '#4caf50' } }],
            }} height={300} />
          </div>
        )}
      </PageSection>
    </PageContainer>
  );
};

export default PowerDispatchPage;
