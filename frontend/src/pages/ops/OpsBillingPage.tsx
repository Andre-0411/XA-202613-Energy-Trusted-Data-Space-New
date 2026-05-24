/**
 * 计费管理页面
 * 顶部汇总卡片 + 计费列表 + 月度发票 + ECharts图表
 */
import React, { useState, useMemo } from 'react';
import { Button, Dialog, Input, Select, Tooltip, Pagination } from 'tdesign-react';
import { MoneyIcon, TimeIcon, TrendingUpIcon, ErrorCircleIcon, RefreshIcon, BillIcon } from 'tdesign-icons-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getBillingRecords, getBillingSummary, getMonthlyInvoice } from '@/api/ops';
import type { BillingRecord, BillingSummary } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import MetricsCard from '@/components/common/MetricsCard';
import ChartCard from '@/components/common/ChartCard';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import ReactECharts from 'echarts-for-react';

const PAYMENT_STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'PAID', label: '已支付' },
  { value: 'PENDING', label: '待支付' },
  { value: 'OVERDUE', label: '逾期' },
];

const paymentStatusLabel = (s: string): string => {
  const m: Record<string, string> = { PAID: '已支付', PENDING: '待支付', OVERDUE: '逾期' };
  return m[s] ?? s;
};

const formatAmount = (val: number): string => `¥${val.toFixed(2)}`;

const OpsBillingPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 & 分页 =====
  const [filterPaymentStatus, setFilterPaymentStatus] = useState<string>('');
  const [filterPeriod, setFilterPeriod] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== ECharts 配置 =====
  const revenueTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis', formatter: '{b}<br/>{a}: ¥{c}' },
    legend: { data: ['收入', '支出'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '金额 (¥)' },
    series: [
      { name: '收入', type: 'line', smooth: true, data: [156000, 168000, 172000, 185000, 198000, 210000, 225000], areaStyle: { opacity: 0.3 }, itemStyle: { color: '#4caf50' } },
      { name: '支出', type: 'line', smooth: true, data: [45000, 48000, 52000, 55000, 58000, 62000, 65000], areaStyle: { opacity: 0.3 }, itemStyle: { color: '#f44336' } },
    ],
  }), []);

  const paymentStatusOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '支付状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 1146900, name: '已支付', itemStyle: { color: '#4caf50' } },
          { value: 86500, name: '待支付', itemStyle: { color: '#ff9800' } },
          { value: 23400, name: '逾期', itemStyle: { color: '#f44336' } },
        ],
      },
    ],
  }), []);

  // ===== 月度发票弹窗 =====
  const [invoiceOpen, setInvoiceOpen] = useState<boolean>(false);
  const [invoicePeriod, setInvoicePeriod] = useState<string>('');
  const [invoiceOrgId, setInvoiceOrgId] = useState<string>('');

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['billingRecords', page, pageSize, filterPaymentStatus, filterPeriod],
    queryFn: () => getBillingRecords({
      page: page + 1, page_size: pageSize,
      payment_status: filterPaymentStatus || undefined,
      billing_period: filterPeriod || undefined,
    }),
  });

  const { data: summaryData } = useQuery({
    queryKey: ['billingSummary'],
    queryFn: () => getBillingSummary(),
  });

  const { data: invoiceData, isLoading: invoiceLoading } = useQuery({
    queryKey: ['monthlyInvoice', invoicePeriod, invoiceOrgId],
    queryFn: () => getMonthlyInvoice(invoicePeriod, invoiceOrgId || undefined),
    enabled: invoiceOpen && !!invoicePeriod,
  });

  const items: BillingRecord[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;
  const summary: BillingSummary | null = summaryData?.data ?? null;

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '计费管理' }],
    [],
  );

  const summaryCards = useMemo(() => {
    if (!summary) return [];
    return [
      { label: '总收入', value: formatAmount(summary.total_revenue), color: '#4caf50' },
      { label: '待支付', value: formatAmount(summary.pending_payments), color: '#ff9800' },
      { label: '已完成', value: formatAmount(summary.completed_payments), color: '#2196f3' },
      { label: '逾期', value: formatAmount(summary.overdue_payments), color: '#f44336' },
    ];
  }, [summary]);

  return (
    <PageContainer>
      <PageHeader
        title="计费管理"
        subtitle="查看计费记录、汇总与月度发票"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '月度发票', icon: <BillIcon />, onClick: () => setInvoiceOpen(true), variant: 'outlined' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => { queryClient.invalidateQueries({ queryKey: ['billingRecords'] }); queryClient.invalidateQueries({ queryKey: ['billingSummary'] }); }, tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4}>
        {summaryCards.map((card, index) => (
          <MetricsCard key={index} title={card.label} value={0} icon={index === 0 ? <MoneyIcon /> : index === 1 ? <TimeIcon /> : index === 2 ? <TrendingUpIcon /> : <ErrorCircleIcon />} color={index === 0 ? 'success' : index === 1 ? 'warning' : index === 2 ? 'primary' : 'error'} unit="" />
        ))}
      </StatGrid>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2"><ChartCard title="收入趋势分析" option={revenueTrendOption} height={300} /></div>
        <ChartCard title="支付状态分布" option={paymentStatusOption} height={300} />
      </div>

      {/* 搜索过滤 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4">
        <div className="flex items-center gap-4">
          <Select
            value={filterPaymentStatus}
            options={PAYMENT_STATUS_OPTIONS}
            onChange={(val) => { setFilterPaymentStatus(String(val)); setPage(0); }}
            style={{ width: 160 }}
            placeholder="支付状态"
          />
          <Input
            value={filterPeriod}
            onChange={(val) => { setFilterPeriod(String(val)); setPage(0); }}
            placeholder="计费周期 (如 2024-01)"
            style={{ width: 200 }}
          />
        </div>
      </div>

      {/* 数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">订阅 ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">金额</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">计费周期</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">支付状态</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">交易哈希</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">创建时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{row.subscription_id}</td>
                  <td className="px-4 py-3">{formatAmount(row.amount)}</td>
                  <td className="px-4 py-3">{row.billing_period}</td>
                  <td className="px-4 py-3"><StatusTag status={paymentStatusLabel(row.payment_status)} /></td>
                  <td className="px-4 py-3">
                    {row.tx_hash ? (
                      <Tooltip content={row.tx_hash}>
                        <span className="text-xs text-gray-600">
                          {row.tx_hash.slice(0, 16)}...
                        </span>
                      </Tooltip>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                </tr>
              ))}
              {items.length > 0 && (
                <tr className="bg-gray-50 font-bold">
                  <td className="px-4 py-3">本页合计</td>
                  <td className="px-4 py-3">{formatAmount(items.reduce((sum, row) => sum + row.amount, 0))}</td>
                  <td className="px-4 py-3" colSpan={4}></td>
                </tr>
              )}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end p-4 border-t border-gray-100">
          <Pagination
            current={page + 1}
            total={total}
            pageSize={pageSize}
            onCurrentChange={(current) => setPage(current - 1)}
            onPageSizeChange={(size) => { setPageSize(size); setPage(0); }}
            showPageSize
            pageSizeOptions={[10, 20, 50]}
          />
        </div>
      </div>

      {/* 月度发票弹窗 */}
      <Dialog
        visible={invoiceOpen}
        onClose={() => setInvoiceOpen(false)}
        header="月度发票查询"
        footer={
          <Button onClick={() => setInvoiceOpen(false)}>关闭</Button>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <Input
              value={invoicePeriod}
              onChange={(val) => setInvoicePeriod(String(val))}
              placeholder="月份 (如 2024-01)"
              style={{ flex: 1 }}
            />
            <Input
              value={invoiceOrgId}
              onChange={(val) => setInvoiceOrgId(String(val))}
              placeholder="组织 ID（可选）"
              style={{ flex: 1 }}
            />
          </div>
          {invoiceLoading && <span className="text-gray-500">加载中...</span>}
          {invoiceData?.data && (
            <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
              <h4 className="text-sm font-semibold text-gray-800 mb-2">发票详情</h4>
              <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                {JSON.stringify(invoiceData.data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default OpsBillingPage;
