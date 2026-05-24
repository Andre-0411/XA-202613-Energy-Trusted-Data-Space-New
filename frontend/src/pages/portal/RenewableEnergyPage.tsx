/**
 * 新能源消纳管理页面
 * 风电/光伏发电量监控 + 弃风弃光率 + 消纳率趋势 + 优化建议
 */
import React, { useState, useMemo } from 'react';
import { Card, Tag, Button, Table } from 'tdesign-react';
import {
  CloudIcon, ChartLineIcon, TrendingUpIcon, RefreshIcon,
  SunnyIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

const PLANTS = [
  { id: 1, name: '华能风电场A', type: '风电', capacity: 200, output: 165, rate: 82.5, status: 'normal' },
  { id: 2, name: '三峡光伏站B', type: '光伏', capacity: 150, output: 120, rate: 80.0, status: 'normal' },
  { id: 3, name: '龙源风电场C', type: '风电', capacity: 300, output: 210, rate: 70.0, status: 'curtailed' },
  { id: 4, name: '中广核光伏站D', type: '光伏', capacity: 100, output: 85, rate: 85.0, status: 'normal' },
  { id: 5, name: '大唐风电场E', type: '风电', capacity: 250, output: 180, rate: 72.0, status: 'curtailed' },
];

const RenewableEnergyPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [
    homeBreadcrumb,
    { label: '业务场景' },
    { label: '新能源消纳管理' },
  ];

  const stats = useMemo(() => [
    { title: '总装机容量', value: 1000, unit: 'MW', icon: <SunnyIcon />, gradient: 'blue', trend: 8.5 },
    { title: '当前出力', value: 760, unit: 'MW', icon: <CloudIcon />, gradient: 'green', trend: 5.2 },
    { title: '消纳率', value: 94.2, unit: '%', icon: <TrendingUpIcon />, gradient: 'purple', trend: 1.8 },
    { title: '弃风弃光率', value: 5.8, unit: '%', icon: <ChartLineIcon />, gradient: 'red', trend: -2.1 },
  ], []);

  const consumptionChart = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['风电出力', '光伏出力', '消纳率'], top: 5 },
    xAxis: { type: 'category' as const, data: ['00:00','04:00','08:00','12:00','16:00','20:00','24:00'] },
    yAxis: [
      { type: 'value' as const, name: 'MW' },
      { type: 'value' as const, name: '%', max: 100 },
    ],
    series: [
      { name: '风电出力', type: 'bar' as const, data: [180, 150, 120, 100, 140, 170, 190], itemStyle: { color: '#1976d2' } },
      { name: '光伏出力', type: 'bar' as const, data: [0, 0, 60, 120, 100, 20, 0], itemStyle: { color: '#ff9800' } },
      { name: '消纳率', type: 'line' as const, yAxisIndex: 1, data: [98, 97, 95, 92, 94, 96, 98], smooth: true, itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const plantColumns = [
    { title: '电站名称', colKey: 'name', width: 160 },
    {
      title: '类型', colKey: 'type', width: 80,
      cell: ({ row }: { row: any }) => (
        <Tag theme={row.type === '风电' ? 'primary' : 'warning'} variant="light">
          {row.type === '风电' ? <CloudIcon size="12px" /> : <SunnyIcon size="12px" />}
          {' '}{row.type}
        </Tag>
      ),
    },
    { title: '装机容量(MW)', colKey: 'capacity', width: 120 },
    { title: '当前出力(MW)', colKey: 'output', width: 120 },
    {
      title: '消纳率', colKey: 'rate', width: 100,
      cell: ({ row }: { row: any }) => (
        <span className={row.rate >= 80 ? 'text-green-600 font-semibold' : 'text-orange-600 font-semibold'}>
          {row.rate}%
        </span>
      ),
    },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: any }) => (
        <Tag theme={row.status === 'normal' ? 'success' : 'warning'} variant="light">
          {row.status === 'normal' ? '正常' : '弃风弃光'}
        </Tag>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader title="新能源消纳管理" subtitle="风电/光伏发电监控与消纳优化" breadcrumbs={breadcrumbs} />

      <PageSection>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6">
          {stats.map((s, i) => <StatCard key={i} {...s} />)}
        </div>
      </PageSection>

      <PageSection>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-6">
          <ChartCard title="新能源出力与消纳率" chipLabel="今日" option={consumptionChart} height={350} />
          <Card className="rounded-xl shadow-sm">
            <h3 className="text-base font-semibold mb-4 m-0">消纳优化建议</h3>
            <div className="flex flex-col gap-3">
              {[
                { time: '12:00', text: '光伏出力高峰，建议增加储能充电', impact: '+2.3%消纳率' },
                { time: '14:30', text: '风电出力下降，建议启动燃气机组补偿', impact: '+1.5%消纳率' },
                { time: '18:00', text: '晚高峰来临，建议储能放电削峰', impact: '+3.1%消纳率' },
                { time: '22:00', text: '负荷低谷，建议限制风电出力', impact: '+0.8%消纳率' },
              ].map((s, i) => (
                <div key={i} className="p-3 bg-green-50 rounded-lg border border-green-100">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-green-800">{s.time}</span>
                    <Tag theme="success" variant="light">{s.impact}</Tag>
                  </div>
                  <p className="text-sm text-gray-700 m-0">{s.text}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </PageSection>

      <PageSection>
        <Card className="rounded-xl shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold m-0">电站运行状态</h3>
            <Button theme="primary" size="small" icon={<RefreshIcon />}>刷新</Button>
          </div>
          <Table data={PLANTS} columns={plantColumns} rowKey="id" />
        </Card>
      </PageSection>
    </PageContainer>
  );
};

export default RenewableEnergyPage;
