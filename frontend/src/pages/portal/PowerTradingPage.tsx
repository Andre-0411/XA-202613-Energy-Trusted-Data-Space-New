/**
 * 电力市场交易页面
 * 实时电价 + 报价策略 + 交易订单 + 结算统计 + AI交易建议
 */
import React, { useMemo } from 'react';
import { Card, Tag, Button, Table } from 'tdesign-react';
import {
  MoneyIcon, ChartLineIcon, TrendingUpIcon, RobotIcon,
} from 'tdesign-icons-react';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

const ORDERS = [
  { id: 'T-20260525-001', time: '09:30', type: '买入', price: 385, volume: 50, amount: 19250, status: 'filled' },
  { id: 'T-20260525-002', time: '10:15', type: '卖出', price: 420, volume: 30, amount: 12600, status: 'filled' },
  { id: 'T-20260525-003', time: '11:00', type: '买入', price: 395, volume: 80, amount: 31600, status: 'partial' },
  { id: 'T-20260525-004', time: '13:30', type: '卖出', price: 450, volume: 60, amount: 27000, status: 'pending' },
  { id: 'T-20260525-005', time: '14:00', type: '买入', price: 410, volume: 100, amount: 41000, status: 'pending' },
];

const PowerTradingPage: React.FC = () => {
  const breadcrumbs: BreadcrumbItem[] = [
    homeBreadcrumb,
    { label: '业务场景' },
    { label: '电力市场交易' },
  ];

  const stats = useMemo(() => [
    { title: '今日交易量', value: 320, unit: 'MWh', icon: <ChartLineIcon />, gradient: 'blue', trend: 18.5 },
    { title: '平均电价', value: 412, unit: '元/MWh', icon: <MoneyIcon />, gradient: 'green', trend: 5.2 },
    { title: '今日收益', value: 8.6, unit: '万元', icon: <TrendingUpIcon />, gradient: 'orange', trend: 22.3 },
    { title: 'AI策略收益', value: 15.2, unit: '%', icon: <RobotIcon />, gradient: 'purple', trend: 3.8 },
  ], []);

  const priceChart = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['实时电价', '预测电价'], top: 5 },
    xAxis: { type: 'category' as const, data: ['00:00','02:00','04:00','06:00','08:00','10:00','12:00','14:00','16:00','18:00','20:00','22:00'] },
    yAxis: { type: 'value' as const, name: '元/MWh' },
    series: [
      { name: '实时电价', type: 'line' as const, data: [320,310,305,340,385,420,450,440,430,460,430,380], smooth: true, areaStyle: { opacity: 0.3 }, itemStyle: { color: '#1976d2' } },
      { name: '预测电价', type: 'line' as const, data: [315,308,300,335,380,415,445,435,425,455,425,375], smooth: true, lineStyle: { type: 'dashed' as const }, itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const orderColumns = [
    { title: '订单号', colKey: 'id', width: 160 },
    { title: '时间', colKey: 'time', width: 80 },
    {
      title: '方向', colKey: 'type', width: 80,
      cell: ({ row }: { row: any }) => (
        <Tag theme={row.type === '买入' ? 'danger' : 'success'} variant="light">{row.type}</Tag>
      ),
    },
    { title: '价格(元/MWh)', colKey: 'price', width: 120 },
    { title: '数量(MWh)', colKey: 'volume', width: 100 },
    { title: '金额(元)', colKey: 'amount', width: 120 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }: { row: any }) => {
        const map: Record<string, { label: string; theme: string }> = {
          filled: { label: '已成交', theme: 'success' },
          partial: { label: '部分成交', theme: 'warning' },
          pending: { label: '待成交', theme: 'default' },
        };
        const s = map[row.status] || map.pending;
        return <Tag theme={s.theme as any} variant="light">{s.label}</Tag>;
      },
    },
  ];

  return (
    <PageContainer>
      <PageHeader title="电力市场交易" subtitle="电力现货市场交易与智能报价" breadcrumbs={breadcrumbs} />

      <PageSection>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6">
          {stats.map((s, i) => <StatCard key={i} {...s} />)}
        </div>
      </PageSection>

      <PageSection>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 mb-6">
          <div className="lg:col-span-2">
            <ChartCard title="24小时电价曲线" chipLabel="今日" option={priceChart} height={350} />
          </div>
          <Card className="rounded-xl shadow-sm">
            <h3 className="text-base font-semibold mb-4 m-0 flex items-center gap-2">
              <RobotIcon size="18px" /> AI交易建议
            </h3>
            <div className="flex flex-col gap-3">
              {[
                { time: '14:00', action: '建议买入', reason: '预测电价将在16:00上涨至460元', confidence: 91 },
                { time: '16:30', action: '建议卖出', reason: '当前电价高于预测均值，锁定利润', confidence: 88 },
                { time: '20:00', action: '建议观望', reason: '电价波动较大，等待稳定信号', confidence: 75 },
              ].map((s, i) => (
                <div key={i} className="p-3 bg-purple-50 rounded-lg border border-purple-100">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-purple-800">{s.time} {s.action}</span>
                    <Tag theme="primary" variant="light">{s.confidence}%</Tag>
                  </div>
                  <p className="text-sm text-gray-600 m-0">{s.reason}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </PageSection>

      <PageSection>
        <Card className="rounded-xl shadow-sm">
          <h3 className="text-base font-semibold mb-4 m-0">交易订单</h3>
          <Table data={ORDERS} columns={orderColumns} rowKey="id" />
        </Card>
      </PageSection>
    </PageContainer>
  );
};

export default PowerTradingPage;
