/**
 * 虚拟电厂运营页面
 * 分布式资源聚合 + 响应能力评估 + 调度指令 + 收益结算
 */
import React, { useMemo } from 'react';
import { Card, Tag, Button, Table } from 'tdesign-react';
import {
  ComponentSwitchIcon, TrendingUpIcon, MoneyIcon, CloudIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

const RESOURCES = [
  { id: 1, name: '海尔智能工厂', type: '可调负荷', capacity: 50, response: 45, status: 'online' },
  { id: 2, name: '特锐德充电桩群', type: '充电桩', capacity: 30, response: 28, status: 'online' },
  { id: 3, name: '比亚迪储能站', type: '储能', capacity: 100, response: 95, status: 'online' },
  { id: 4, name: '居民空调负荷', type: '可调负荷', capacity: 80, response: 60, status: 'partial' },
  { id: 5, name: '商业楼宇照明', type: '可调负荷', capacity: 20, response: 18, status: 'online' },
];

const VirtualPowerPlantPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [
    homeBreadcrumb,
    { label: '业务场景' },
    { label: '虚拟电厂运营' },
  ];

  const stats = useMemo(() => [
    { title: '聚合容量', value: 280, unit: 'MW', icon: <ComponentSwitchIcon />, gradient: 'blue', trend: 12.5 },
    { title: '响应能力', value: 246, unit: 'MW', icon: <CloudIcon />, gradient: 'green', trend: 8.3 },
    { title: '今日收益', value: 12.8, unit: '万元', icon: <MoneyIcon />, gradient: 'orange', trend: 15.2 },
    { title: '响应成功率', value: 97.5, unit: '%', icon: <TrendingUpIcon />, gradient: 'purple', trend: 2.1 },
  ], []);

  const resourceColumns = [
    { title: '资源名称', colKey: 'name', width: 160 },
    {
      title: '类型', colKey: 'type', width: 100,
      cell: ({ row }: { row: any }) => {
        const colors: Record<string, string> = { '可调负荷': 'primary', '充电桩': 'success', '储能': 'warning' };
        return <Tag theme={(colors[row.type] || 'default') as any} variant="light">{row.type}</Tag>;
      },
    },
    { title: '可调容量(MW)', colKey: 'capacity', width: 120 },
    { title: '响应能力(MW)', colKey: 'response', width: 120 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: any }) => (
        <Tag theme={row.status === 'online' ? 'success' : 'warning'} variant="light">
          {row.status === 'online' ? '在线' : '部分在线'}
        </Tag>
      ),
    },
  ];

  const revenueChart = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['需求响应', '调峰收益', '辅助服务'], top: 5 },
    xAxis: { type: 'category' as const, data: ['1月','2月','3月','4月','5月','6月'] },
    yAxis: { type: 'value' as const, name: '万元' },
    series: [
      { name: '需求响应', type: 'bar' as const, stack: 'total', data: [45, 52, 48, 61, 58, 65], itemStyle: { color: '#1976d2' } },
      { name: '调峰收益', type: 'bar' as const, stack: 'total', data: [30, 35, 32, 40, 38, 42], itemStyle: { color: '#4caf50' } },
      { name: '辅助服务', type: 'bar' as const, stack: 'total', data: [15, 18, 16, 22, 20, 24], itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  return (
    <PageContainer>
      <PageHeader title="虚拟电厂运营" subtitle="分布式能源聚合管理与需求响应" breadcrumbs={breadcrumbs} />

      <PageSection>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6">
          {stats.map((s, i) => <StatCard key={i} {...s} />)}
        </div>
      </PageSection>

      <PageSection>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 mb-6">
          <ChartCard title="收益构成趋势" chipLabel="近6月" option={revenueChart} height={350} />
          <Card className="rounded-xl shadow-sm">
            <h3 className="text-base font-semibold mb-4 m-0">响应事件记录</h3>
            <div className="flex flex-col gap-3">
              {[
                { time: '10:30', event: '削峰响应', amount: '+45MW', duration: '2小时', revenue: '2.1万' },
                { time: '14:00', event: '填谷响应', amount: '+30MW', duration: '3小时', revenue: '1.8万' },
                { time: '18:30', event: '调频服务', amount: '+20MW', duration: '1小时', revenue: '0.9万' },
              ].map((e, i) => (
                <div key={i} className="p-3 bg-orange-50 rounded-lg border border-orange-100">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-orange-800">{e.time} {e.event}</span>
                    <Tag theme="warning" variant="light">{e.revenue}</Tag>
                  </div>
                  <p className="text-sm text-gray-600 m-0">{e.amount} · {e.duration}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </PageSection>

      <PageSection>
        <Card className="rounded-xl shadow-sm">
          <h3 className="text-base font-semibold mb-4 m-0">聚合资源列表</h3>
          <Table data={RESOURCES} columns={resourceColumns} rowKey="id" />
        </Card>
      </PageSection>
    </PageContainer>
  );
};

export default VirtualPowerPlantPage;
