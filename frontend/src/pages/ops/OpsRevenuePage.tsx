/**
 * 收益分配管理页面
 * 基于可信数据空间标准体系，实现数据资产收益分配管理
 * 包含：收益概览、价值评估、收益结算、争议处理
 */
import React, { useState, useMemo } from 'react';
import { Button, Tag, Tabs, Dialog, Input, Select, Tooltip, MessagePlugin, Textarea } from 'tdesign-react';
import {
  MoneyIcon, TrendingUpIcon, ChartIcon, TimeIcon,
  RefreshIcon, AddIcon, BrowseIcon, EditIcon,
  CheckCircleFilledIcon, ErrorCircleIcon, BillIcon,
} from 'tdesign-icons-react';
import ReactECharts from 'echarts-for-react';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import PageContainer, { PageSection, StatGrid } from '@/components/common/PageContainer';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import StatusTag from '@/components/StatusTag';

/* ========== 类型定义 ========== */
interface RevenueRecord {
  id: string;
  data_asset: string;
  provider: string;
  consumer: string;
  amount: number;
  period: string;
  status: string;
  settled_at: string;
  tx_hash: string;
}

interface AssetValuation {
  id: string;
  asset_name: string;
  category: string;
  valuation: number;
  usage_count: string;
  revenue: number;
  growth_rate: number;
  last_evaluated: string;
}

interface DisputeRecord {
  id: string;
  contract_name: string;
  complainant: string;
  respondent: string;
  reason: string;
  amount: number;
  status: string;
  filed_at: string;
  resolved_at: string;
}

/* ========== 模拟数据 - 收益记录 ========== */
const MOCK_REVENUE: RevenueRecord[] = [
  { id: 'rev-001', data_asset: '电网负荷数据', provider: '国网数据中心', consumer: '新能源研究院', amount: 12500, period: '2025-05', status: 'settled', settled_at: '2025-05-20T10:00:00Z', tx_hash: '0xabc123...def456' },
  { id: 'rev-002', data_asset: '光伏发电出力数据', provider: '光伏运营商A', consumer: '电力交易中心', amount: 8600, period: '2025-05', status: 'settled', settled_at: '2025-05-19T14:30:00Z', tx_hash: '0x789abc...012def' },
  { id: 'rev-003', data_asset: '碳排放监测数据', provider: '双碳管理平台', consumer: '环保监测中心', amount: 15800, period: '2025-05', status: 'pending', settled_at: '', tx_hash: '' },
  { id: 'rev-004', data_asset: '充电桩运营数据', provider: '充电服务平台', consumer: '电动汽车公司', amount: 6200, period: '2025-05', status: 'settled', settled_at: '2025-05-18T09:00:00Z', tx_hash: '0xdef789...abc012' },
  { id: 'rev-005', data_asset: '电价预测模型数据', provider: 'AI预测平台', consumer: '交易中心', amount: 22000, period: '2025-05', status: 'pending', settled_at: '', tx_hash: '' },
  { id: 'rev-006', data_asset: '储能调度数据', provider: '储能电站A', consumer: '调度中心', amount: 9800, period: '2025-05', status: 'disputed', settled_at: '', tx_hash: '' },
  { id: 'rev-007', data_asset: '用户用电量统计', provider: '营销系统', consumer: '第三方分析机构', amount: 18500, period: '2025-04', status: 'settled', settled_at: '2025-04-30T16:00:00Z', tx_hash: '0x123abc...456def' },
  { id: 'rev-008', data_asset: '配电设备状态数据', provider: '设备管理平台', consumer: '运维服务商', amount: 7400, period: '2025-04', status: 'settled', settled_at: '2025-04-29T11:00:00Z', tx_hash: '0x456def...789abc' },
];

/* ========== 模拟数据 - 资产估值 ========== */
const MOCK_VALUATIONS: AssetValuation[] = [
  { id: 'val-001', asset_name: '电网负荷数据', category: '电网运行', valuation: 1250000, usage_count: '156次/月', revenue: 45000, growth_rate: 12.5, last_evaluated: '2025-05-20' },
  { id: 'val-002', asset_name: '光伏发电出力数据', category: '新能源', valuation: 860000, usage_count: '98次/月', revenue: 28000, growth_rate: 18.2, last_evaluated: '2025-05-18' },
  { id: 'val-003', asset_name: '碳排放监测数据', category: '双碳管理', valuation: 1580000, usage_count: '210次/月', revenue: 62000, growth_rate: 25.3, last_evaluated: '2025-05-22' },
  { id: 'val-004', asset_name: '充电桩运营数据', category: '电动汽车', valuation: 620000, usage_count: '75次/月', revenue: 18500, growth_rate: 8.7, last_evaluated: '2025-05-15' },
  { id: 'val-005', asset_name: '电价预测模型数据', category: '电力交易', valuation: 2200000, usage_count: '320次/月', revenue: 88000, growth_rate: 32.1, last_evaluated: '2025-05-23' },
  { id: 'val-006', asset_name: '储能调度数据', category: '储能运营', valuation: 980000, usage_count: '112次/月', revenue: 35000, growth_rate: 15.6, last_evaluated: '2025-05-21' },
];

/* ========== 模拟数据 - 争议记录 ========== */
const MOCK_DISPUTES: DisputeRecord[] = [
  { id: 'disp-001', contract_name: '储能调度数据共享协议', complainant: '储能电站A', respondent: '调度中心', reason: '数据质量不达标，延迟交付超过约定时间', amount: 3200, status: 'pending', filed_at: '2025-05-20T09:00:00Z', resolved_at: '' },
  { id: 'disp-002', contract_name: '光伏发电数据交易合约', complainant: '电力交易中心', respondent: '光伏运营商B', reason: '数据完整性不足，缺失率达15%', amount: 5600, status: 'resolved', filed_at: '2025-05-10T14:00:00Z', resolved_at: '2025-05-15T16:30:00Z' },
  { id: 'disp-003', contract_name: '用户用电量授权协议', complainant: '第三方分析机构', respondent: '营销系统', reason: '授权范围争议，实际使用超出约定范围', amount: 8000, status: 'arbitrating', filed_at: '2025-05-18T10:00:00Z', resolved_at: '' },
];

const REVENUE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  settled: { label: '已结算', theme: 'success' },
  pending: { label: '待结算', theme: 'warning' },
  disputed: { label: '争议中', theme: 'danger' },
};

const DISPUTE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  pending: { label: '待处理', theme: 'warning' },
  resolved: { label: '已解决', theme: 'success' },
  arbitrating: { label: '仲裁中', theme: 'primary' },
};

const formatAmount = (val: number): string => `¥${val.toLocaleString()}`;

const OpsRevenuePage: React.FC = () => {
  // ===== 状态 =====
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [selectedRecord, setSelectedRecord] = useState<RevenueRecord | null>(null);
  const [disputeOpen, setDisputeOpen] = useState<boolean>(false);

  // ===== 统计数据 =====
  const stats = useMemo(() => {
    const totalRevenue = MOCK_REVENUE.reduce((sum, r) => sum + r.amount, 0);
    const settledAmount = MOCK_REVENUE.filter(r => r.status === 'settled').reduce((sum, r) => sum + r.amount, 0);
    const pendingAmount = MOCK_REVENUE.filter(r => r.status === 'pending').reduce((sum, r) => sum + r.amount, 0);
    const disputedAmount = MOCK_REVENUE.filter(r => r.status === 'disputed').reduce((sum, r) => sum + r.amount, 0);
    const totalValuation = MOCK_VALUATIONS.reduce((sum, v) => sum + v.valuation, 0);
    return { totalRevenue, settledAmount, pendingAmount, disputedAmount, totalValuation, disputeCount: MOCK_DISPUTES.length };
  }, []);

  // ===== ECharts - 月度收益趋势 =====
  const revenueTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis', formatter: (params: any) => { let s = `${params[0].axisValue}<br/>`; params.forEach((p: any) => { s += `${p.marker}${p.seriesName}: ¥${p.value.toLocaleString()}<br/>`; }); return s; } },
    legend: { data: ['数据提供方收益', '平台服务费', '数据使用方支出'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月'] },
    yAxis: { type: 'value', name: '金额 (¥)' },
    series: [
      { name: '数据提供方收益', type: 'bar', data: [120000, 135000, 148000, 162000, 178000], itemStyle: { color: '#4caf50' } },
      { name: '平台服务费', type: 'bar', data: [18000, 20000, 22000, 24000, 26500], itemStyle: { color: '#2196f3' } },
      { name: '数据使用方支出', type: 'line', smooth: true, data: [138000, 155000, 170000, 186000, 204500], itemStyle: { color: '#ff9800' }, areaStyle: { opacity: 0.1 } },
    ],
  }), []);

  // ===== ECharts - 收益分布饼图 =====
  const revenueDistOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [{
      name: '收益分布', type: 'pie', radius: ['40%', '70%'], center: ['60%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' },
      emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
      labelLine: { show: false },
      data: [
        { value: MOCK_VALUATIONS[0].revenue, name: '电网运行', itemStyle: { color: '#2196f3' } },
        { value: MOCK_VALUATIONS[1].revenue, name: '新能源', itemStyle: { color: '#4caf50' } },
        { value: MOCK_VALUATIONS[2].revenue, name: '双碳管理', itemStyle: { color: '#ff9800' } },
        { value: MOCK_VALUATIONS[3].revenue, name: '电动汽车', itemStyle: { color: '#9c27b0' } },
        { value: MOCK_VALUATIONS[4].revenue, name: '电力交易', itemStyle: { color: '#00bcd4' } },
        { value: MOCK_VALUATIONS[5].revenue, name: '储能运营', itemStyle: { color: '#e91e63' } },
      ],
    }],
  }), []);

  // ===== ECharts - 资产估值排名 =====
  const valuationRankOption = useMemo(() => {
    const sorted = [...MOCK_VALUATIONS].sort((a, b) => b.valuation - a.valuation);
    return {
      tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].axisValue}<br/>估值: ¥${params[0].value.toLocaleString()}` },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'value', name: '估值 (¥)' },
      yAxis: { type: 'category', data: sorted.map(v => v.asset_name), inverse: true },
      series: [{
        type: 'bar',
        data: sorted.map((v, i) => ({
          value: v.valuation,
          itemStyle: { color: ['#f44336', '#ff9800', '#ffeb3b', '#4caf50', '#2196f3', '#9c27b0'][i] },
        })),
        barWidth: '50%',
        label: { show: true, position: 'right', formatter: (p: any) => `¥${(p.value / 10000).toFixed(1)}万` },
      }],
    };
  }, []);

  // ===== ECharts - 增长率趋势 =====
  const growthRateOption = useMemo(() => ({
    tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].axisValue}<br/>增长率: ${params[0].value}%` },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: MOCK_VALUATIONS.map(v => v.asset_name) },
    yAxis: { type: 'value', name: '增长率 (%)' },
    series: [{
      type: 'bar',
      data: MOCK_VALUATIONS.map(v => ({
        value: v.growth_rate,
        itemStyle: { color: v.growth_rate > 20 ? '#4caf50' : v.growth_rate > 10 ? '#2196f3' : '#ff9800' },
      })),
      barWidth: '50%',
      label: { show: true, position: 'top', formatter: '{c}%' },
    }],
  }), []);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '运营中心' }, { label: '收益分配' }],
    [],
  );

  // ===== 收益记录表格列 =====
  const revenueColumns: Column<RevenueRecord>[] = useMemo(() => [
    { id: 'data_asset', label: '数据资产', minWidth: 160, render: (row) => <span className="text-sm font-medium">{row.data_asset}</span> },
    { id: 'provider', label: '提供方', minWidth: 120 },
    { id: 'consumer', label: '使用方', minWidth: 120 },
    { id: 'amount', label: '金额', minWidth: 100, render: (row) => <span className="text-sm font-semibold text-green-600">{formatAmount(row.amount)}</span> },
    { id: 'period', label: '结算周期', minWidth: 90 },
    { id: 'status', label: '状态', minWidth: 90, render: (row) => { const s = REVENUE_STATUS_MAP[row.status]; return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'settled_at', label: '结算时间', minWidth: 150, render: (row) => row.settled_at ? new Date(row.settled_at).toLocaleString('zh-CN') : '—' },
    {
      id: 'actions', label: '操作', minWidth: 80, align: 'center',
      render: (row) => (
        <Tooltip content="查看详情">
          <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => { setSelectedRecord(row); setDetailOpen(true); }}>
            <BrowseIcon />
          </span>
        </Tooltip>
      ),
    },
  ], []);

  // ===== 资产估值表格列 =====
  const valuationColumns: Column<AssetValuation>[] = useMemo(() => [
    { id: 'asset_name', label: '资产名称', minWidth: 160, render: (row) => <span className="text-sm font-medium">{row.asset_name}</span> },
    { id: 'category', label: '分类', minWidth: 100, render: (row) => <Tag variant="outline" size="small">{row.category}</Tag> },
    { id: 'valuation', label: '估值', minWidth: 120, render: (row) => <span className="text-sm font-semibold text-blue-600">{formatAmount(row.valuation)}</span> },
    { id: 'usage_count', label: '使用频次', minWidth: 100 },
    { id: 'revenue', label: '月收益', minWidth: 100, render: (row) => <span className="text-sm font-semibold text-green-600">{formatAmount(row.revenue)}</span> },
    { id: 'growth_rate', label: '增长率', minWidth: 90, render: (row) => <span className={`text-sm font-semibold ${row.growth_rate > 15 ? 'text-green-600' : row.growth_rate > 0 ? 'text-blue-600' : 'text-red-600'}`}>{row.growth_rate > 0 ? '+' : ''}{row.growth_rate}%</span> },
    { id: 'last_evaluated', label: '评估日期', minWidth: 110 },
  ], []);

  // ===== 争议记录表格列 =====
  const disputeColumns: Column<DisputeRecord>[] = useMemo(() => [
    { id: 'contract_name', label: '合约名称', minWidth: 180, render: (row) => <span className="text-sm font-medium">{row.contract_name}</span> },
    { id: 'complainant', label: '申诉方', minWidth: 100 },
    { id: 'respondent', label: '被申诉方', minWidth: 100 },
    { id: 'reason', label: '争议原因', minWidth: 200, render: (row) => <span className="text-sm text-gray-600">{row.reason}</span> },
    { id: 'amount', label: '争议金额', minWidth: 100, render: (row) => <span className="text-sm font-semibold text-red-600">{formatAmount(row.amount)}</span> },
    { id: 'status', label: '状态', minWidth: 90, render: (row) => { const s = DISPUTE_STATUS_MAP[row.status]; return s ? <StatusTag status={s.label} color={s.theme} /> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'filed_at', label: '申诉时间', minWidth: 140, render: (row) => new Date(row.filed_at).toLocaleString('zh-CN') },
    {
      id: 'actions', label: '操作', minWidth: 80, align: 'center',
      render: (row) => (
        <Tooltip content="处理争议">
          <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-orange-500" onClick={() => setDisputeOpen(true)}>
            <EditIcon />
          </span>
        </Tooltip>
      ),
    },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="收益分配管理"
        subtitle="基于数据资产价值评估，实现收益的公平、透明分配"
        breadcrumbs={breadcrumbs}
        actions={[
          { label: '生成账单', icon: <BillIcon />, onClick: () => MessagePlugin.info('账单生成功能'), variant: 'contained' },
        ]}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => MessagePlugin.success('数据已刷新'), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <StatGrid columns={4} gap="md">
        <StatCard title="总收益" value={stats.totalRevenue} icon={<MoneyIcon />} gradient="green" unit="¥" />
        <StatCard title="已结算" value={stats.settledAmount} icon={<CheckCircleFilledIcon />} gradient="blue" unit="¥" />
        <StatCard title="待结算" value={stats.pendingAmount} icon={<TimeIcon />} gradient="orange" unit="¥" />
        <StatCard title="争议金额" value={stats.disputedAmount} icon={<ErrorCircleIcon />} gradient="red" unit="¥" />
      </StatGrid>

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="overview" label="收益概览">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <ChartCard title="月度收益趋势" option={revenueTrendOption} height={350} />
            </div>
            <ChartCard title="收益分布" option={revenueDistOption} height={350} />
          </div>
          <div className="mt-4">
            <PageSection title="最近结算记录" titleIcon={<MoneyIcon />}>
              <DataTable columns={revenueColumns} rows={MOCK_REVENUE.slice(0, 5)} page={0} pageSize={5} total={5} />
            </PageSection>
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="valuation" label="价值评估">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <ChartCard title="资产估值排名" option={valuationRankOption} height={350} />
            </div>
            <ChartCard title="增长率对比" option={growthRateOption} height={350} />
          </div>
          <PageSection title="资产估值明细" titleIcon={<ChartIcon />} className="mt-4" padding="none">
            <DataTable columns={valuationColumns} rows={MOCK_VALUATIONS} page={0} pageSize={20} total={MOCK_VALUATIONS.length} />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="settlement" label="收益结算">
          <StatGrid columns={3} gap="md" className="mt-4 mb-4">
            <StatCard title="本月结算总额" value={stats.settledAmount} icon={<MoneyIcon />} gradient="green" unit="¥" />
            <StatCard title="结算笔数" value={MOCK_REVENUE.filter(r => r.status === 'settled').length} icon={<BillIcon />} gradient="blue" unit="笔" />
            <StatCard title="资产总估值" value={stats.totalValuation} icon={<TrendingUpIcon />} gradient="purple" unit="¥" />
          </StatGrid>
          <PageSection title="结算记录" titleIcon={<BillIcon />} padding="none">
            <DataTable columns={revenueColumns} rows={MOCK_REVENUE} page={0} pageSize={20} total={MOCK_REVENUE.length} />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="disputes" label="争议处理">
          <StatGrid columns={3} gap="md" className="mt-4 mb-4">
            <StatCard title="待处理争议" value={MOCK_DISPUTES.filter(d => d.status === 'pending').length} icon={<ErrorCircleIcon />} gradient="orange" unit="件" />
            <StatCard title="仲裁中" value={MOCK_DISPUTES.filter(d => d.status === 'arbitrating').length} icon={<TimeIcon />} gradient="blue" unit="件" />
            <StatCard title="已解决" value={MOCK_DISPUTES.filter(d => d.status === 'resolved').length} icon={<CheckCircleFilledIcon />} gradient="green" unit="件" />
          </StatGrid>
          <PageSection title="争议记录" titleIcon={<ErrorCircleIcon />} padding="none">
            <DataTable columns={disputeColumns} rows={MOCK_DISPUTES} page={0} pageSize={20} total={MOCK_DISPUTES.length} />
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 收益详情弹窗 */}
      <Dialog visible={detailOpen} onClose={() => setDetailOpen(false)} header="收益详情" width={560} footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}>
        {selectedRecord && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div><span className="text-xs text-gray-500">数据资产</span><p className="text-sm font-semibold">{selectedRecord.data_asset}</p></div>
              <div><span className="text-xs text-gray-500">金额</span><p className="text-sm font-semibold text-green-600">{formatAmount(selectedRecord.amount)}</p></div>
              <div><span className="text-xs text-gray-500">提供方</span><p className="text-sm">{selectedRecord.provider}</p></div>
              <div><span className="text-xs text-gray-500">使用方</span><p className="text-sm">{selectedRecord.consumer}</p></div>
              <div><span className="text-xs text-gray-500">结算周期</span><p className="text-sm">{selectedRecord.period}</p></div>
              <div><span className="text-xs text-gray-500">状态</span><StatusTag status={REVENUE_STATUS_MAP[selectedRecord.status]?.label || selectedRecord.status} color={REVENUE_STATUS_MAP[selectedRecord.status]?.theme || 'default'} /></div>
            </div>
            {selectedRecord.tx_hash && (
              <div><span className="text-xs text-gray-500">交易哈希</span><p className="text-sm font-mono">{selectedRecord.tx_hash}</p></div>
            )}
          </div>
        )}
      </Dialog>

      {/* 争议处理弹窗 */}
      <Dialog visible={disputeOpen} onClose={() => setDisputeOpen(false)} header="争议处理" width={560} footer={
        <div className="flex justify-end gap-2">
          <Button onClick={() => setDisputeOpen(false)}>取消</Button>
          <Button theme="primary" onClick={() => { MessagePlugin.success('争议处理意见已提交'); setDisputeOpen(false); }}>提交处理</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <div><label className="block text-sm text-gray-600 mb-1">处理意见</label><Textarea placeholder="请输入争议处理意见..." rows={4} /></div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">处理结果</label>
            <Select options={[{ value: 'refund', label: '全额退款' }, { value: 'partial', label: '部分退款' }, { value: 'reject', label: '驳回申诉' }, { value: 'mediate', label: '调解协商' }]} placeholder="选择处理结果" />
          </div>
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default OpsRevenuePage;
