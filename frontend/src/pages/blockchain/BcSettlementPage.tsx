/**
 * 结算管理页面
 * 结算列表 + 发起结算 + 查看详情 + 争议处理 + 结算统计
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Textarea, Tag, Tooltip, Dialog, MessagePlugin, Tabs, Table, Form, Card, Row, Col, Statistic, Steps, Select, Divider, Typography, Space, Progress } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, LinkIcon,
  WalletIcon, CheckCircleFilledIcon, TimeIcon, TrendingUpIcon,
  FileIcon, ErrorCircleIcon, MoneyIcon, ChartIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { triggerSettlement, getSettlementDetail, disputeSettlement } from '@/api/blockchain';
import type { Settlement } from '@/types/api';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import ReactECharts from 'echarts-for-react';

const settlementStatusLabel = (s: string): string => {
  const m: Record<string, string> = { PENDING: '待处理', COMPLETED: '已完成', FAILED: '失败', DISPUTED: '争议中' };
  return m[s] ?? s;
};

const settlementStatusColor = (s: string): 'warning' | 'success' | 'error' | 'info' | 'default' => {
  const m: Record<string, 'warning' | 'success' | 'error' | 'info'> = {
    PENDING: 'warning', COMPLETED: 'success', FAILED: 'error', DISPUTED: 'info',
  };
  return m[s] ?? 'default';
};

/* ========== 模拟数据 - 结算记录 ========== */
const MOCK_SETTLEMENTS: Settlement[] = [
  {
    id: 'settle-001',
    from_org: '国网数据中心',
    to_org: '新能源研究院',
    amount: 125000,
    asset_id: 'asset-001',
    tx_hash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
    status: 'COMPLETED',
    created_at: '2025-05-20T08:00:00Z',
    completed_at: '2025-05-20T08:05:00Z',
    contract_id: 'contract-001',
    description: '电网负荷数据共享结算',
  },
  {
    id: 'settle-002',
    from_org: '光伏运营商A',
    to_org: '电力交易中心',
    amount: 89000,
    asset_id: 'asset-002',
    tx_hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    status: 'PENDING',
    created_at: '2025-05-21T10:30:00Z',
    completed_at: '',
    contract_id: 'contract-002',
    description: '光伏发电数据交易结算',
  },
  {
    id: 'settle-003',
    from_org: '双碳管理平台',
    to_org: '环保监测中心',
    amount: 56000,
    asset_id: 'asset-003',
    tx_hash: '0x234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1',
    status: 'COMPLETED',
    created_at: '2025-05-22T14:15:00Z',
    completed_at: '2025-05-22T14:30:00Z',
    contract_id: 'contract-003',
    description: '碳排放数据授权结算',
  },
  {
    id: 'settle-004',
    from_org: '储能电站A',
    to_org: '调度中心',
    amount: 78000,
    asset_id: 'asset-004',
    tx_hash: '0x34567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12',
    status: 'DISPUTED',
    created_at: '2025-05-23T09:45:00Z',
    completed_at: '',
    contract_id: 'contract-004',
    description: '储能调度数据结算',
  },
  {
    id: 'settle-005',
    from_org: '充电服务平台',
    to_org: '电动汽车公司',
    amount: 45000,
    asset_id: 'asset-005',
    tx_hash: '0x4567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef123',
    status: 'COMPLETED',
    created_at: '2025-05-24T11:20:00Z',
    completed_at: '2025-05-24T11:25:00Z',
    contract_id: 'contract-005',
    description: '充电桩运营数据结算',
  },
  {
    id: 'settle-006',
    from_org: '交易中心',
    to_org: 'AI预测平台',
    amount: 32000,
    asset_id: 'asset-006',
    tx_hash: '',
    status: 'FAILED',
    created_at: '2025-05-25T08:30:00Z',
    completed_at: '',
    contract_id: 'contract-006',
    description: '电价预测数据协作结算',
  },
];

/* ========== 模拟数据 - 争议记录 ========== */
interface DisputeRecord {
  id: string;
  settlement_id: string;
  dispute_reason: string;
  dispute_time: string;
  status: string;
  resolution: string;
  resolved_at: string;
}

const MOCK_DISPUTES: DisputeRecord[] = [
  {
    id: 'dispute-001',
    settlement_id: 'settle-004',
    dispute_reason: '数据质量不符合约定标准，部分数据缺失',
    dispute_time: '2025-05-23T10:00:00Z',
    status: 'pending',
    resolution: '',
    resolved_at: '',
  },
  {
    id: 'dispute-002',
    settlement_id: 'settle-002',
    dispute_reason: '结算金额计算有误，多算了10%',
    dispute_time: '2025-05-22T15:30:00Z',
    status: 'resolved',
    resolution: '经核实，金额计算正确，维持原结算',
    resolved_at: '2025-05-23T09:00:00Z',
  },
];

const DISPUTE_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  pending: { label: '处理中', theme: 'warning' },
  resolved: { label: '已解决', theme: 'success' },
  rejected: { label: '已驳回', theme: 'danger' },
};

const BcSettlementPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 主 Tab =====
  const [activeTab, setActiveTab] = useState<string>('settlements');

  // ===== 分页 =====
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 发起结算弹窗 =====
  const [settleOpen, setSettleOpen] = useState<boolean>(false);
  const [settleStep, setSettleStep] = useState<number>(0);
  const [fromOrg, setFromOrg] = useState<string>('');
  const [toOrg, setToOrg] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [assetId, setAssetId] = useState<string>('');
  const [contractId, setContractId] = useState<string>('');
  const [description, setDescription] = useState<string>('');

  // ===== 详情弹窗 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<Settlement | null>(null);

  // ===== 争议处理弹窗 =====
  const [disputeOpen, setDisputeOpen] = useState<boolean>(false);
  const [disputeId, setDisputeId] = useState<string>('');
  const [disputeReason, setDisputeReason] = useState<string>('');

  // ===== 本地结算列表 =====
  const [settlements, setSettlements] = useState<Settlement[]>(MOCK_SETTLEMENTS);
  const items: Settlement[] = settlements;
  const total: number = settlements.length;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalSettlements: total,
    completedSettlements: items.filter((item) => item.status === 'COMPLETED').length,
    pendingSettlements: items.filter((item) => item.status === 'PENDING').length,
    disputedSettlements: items.filter((item) => item.status === 'DISPUTED').length,
    failedSettlements: items.filter((item) => item.status === 'FAILED').length,
    totalAmount: items.reduce((sum, item) => sum + item.amount, 0),
    completedAmount: items.filter(i => i.status === 'COMPLETED').reduce((sum, item) => sum + item.amount, 0),
    todayAmount: items
      .filter((item) => {
        const today = new Date().toDateString();
        return new Date(item.created_at).toDateString() === today;
      })
      .reduce((sum, item) => sum + item.amount, 0),
  }), [total, items]);

  // ===== ECharts 配置 =====
  const settlementTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['结算笔数', '结算金额(万)'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '数量' },
    series: [
      { name: '结算笔数', type: 'bar', data: [85, 95, 110, 120, 135, 150, 165], itemStyle: { color: '#2196f3' } },
      { name: '结算金额(万)', type: 'line', smooth: true, data: [120, 150, 180, 210, 250, 290, 350], itemStyle: { color: '#ff9800' } },
    ],
  }), []);

  const settlementStatusOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '结算状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: stats.completedSettlements, name: '已完成', itemStyle: { color: '#4caf50' } },
          { value: stats.pendingSettlements, name: '待处理', itemStyle: { color: '#ff9800' } },
          { value: stats.disputedSettlements, name: '争议中', itemStyle: { color: '#f44336' } },
          { value: stats.failedSettlements, name: '失败', itemStyle: { color: '#9e9e9e' } },
        ],
      },
    ],
  }), [stats]);

  const monthlyAmountOption = useMemo(() => ({
    tooltip: { trigger: 'axis', formatter: '{b}<br/>{a}: ¥{c}' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '金额 (¥)' },
    series: [{
      name: '结算金额',
      type: 'bar',
      data: [1200000, 1500000, 1800000, 2100000, 2500000, 2900000, 3500000],
      itemStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#2196f3' },
            { offset: 1, color: '#64b5f6' },
          ],
        },
      },
      barWidth: '40%',
    }],
  }), []);

  // ===== Mutations =====
  const settleMut = useMutation({
    mutationFn: (d: { from_org: string; to_org: string; amount: number; asset_id: string }) => triggerSettlement(d),
    onSuccess: (res) => {
      if (res.data) {
        setSettlements((prev) => [res.data, ...prev]);
      }
      MessagePlugin.success('结算发起成功');
      setSettleOpen(false);
      setSettleStep(0);
      setFromOrg(''); setToOrg(''); setAmount(''); setAssetId(''); setContractId(''); setDescription('');
    },
    onError: () => {
      MessagePlugin.error('结算发起失败');
    },
  });

  const detailMut = useMutation({
    mutationFn: (id: string) => getSettlementDetail(id),
    onSuccess: (res) => {
      setDetailData(res.data ?? null);
      setDetailOpen(true);
    },
    onError: () => {
      MessagePlugin.error('获取结算详情失败');
    },
  });

  const disputeMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => disputeSettlement(id, reason),
    onSuccess: () => {
      setSettlements((prev) => prev.map((s) => s.id === disputeId ? { ...s, status: 'DISPUTED' } : s));
      MessagePlugin.success('争议提交成功');
      setDisputeOpen(false);
      setDisputeId(''); setDisputeReason('');
    },
    onError: () => {
      MessagePlugin.error('争议提交失败');
    },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: '结算管理' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [{ label: '发起结算', icon: <AddIcon />, onClick: () => setSettleOpen(true), variant: 'contained' }],
    [],
  );

  // ===== 分页计算 =====
  const pagedItems = useMemo(() => items.slice(page * pageSize, (page + 1) * pageSize), [items, page, pageSize]);

  // ===== 表格列定义 =====
  const columns: Column<Settlement>[] = useMemo(() => [
    { id: 'from_org', label: '发起方', minWidth: 120, render: (row) => <span className="text-sm font-medium">{row.from_org}</span> },
    { id: 'to_org', label: '接收方', minWidth: 120, render: (row) => <span className="text-sm font-medium">{row.to_org}</span> },
    { id: 'amount', label: '金额', minWidth: 100, render: (row) => <span className="font-semibold text-blue-600">¥{(row.amount ?? 0).toFixed(2)}</span> },
    { id: 'asset_id', label: '关联资产', minWidth: 120 },
    {
      id: 'tx_hash', label: '交易哈希', minWidth: 160,
      render: (row) => row.tx_hash ? (
        <Tooltip content={row.tx_hash}>
          <Tag variant="outline" theme="primary">{(row.tx_hash ?? '').slice(0, 10)}...</Tag>
        </Tooltip>
      ) : '—',
    },
    {
      id: 'status', label: '状态', minWidth: 100,
      render: (row) => <StatusTag status={settlementStatusLabel(row.status)} color={settlementStatusColor(row.status)} />,
    },
    { id: 'created_at', label: '创建时间', minWidth: 160, render: (row) => new Date(row.created_at).toLocaleString('zh-CN') },
    {
      id: 'actions', label: '操作', minWidth: 120, align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => detailMut.mutate(row.id)}>
              <BrowseIcon size={16} />
            </span>
          </Tooltip>
          {row.status === 'PENDING' && (
            <Tooltip content="争议处理">
              <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-orange-500" onClick={() => { setDisputeId(row.id); setDisputeOpen(true); }}>
                <ErrorCircleIcon size={16} />
              </span>
            </Tooltip>
          )}
        </div>
      ),
    },
  ], []);

  // ===== 争议记录列定义 =====
  const disputeColumns: Column<DisputeRecord>[] = useMemo(() => [
    { id: 'settlement_id', label: '结算ID', minWidth: 140, render: (row) => <Tag variant="outline">{row.settlement_id}</Tag> },
    { id: 'dispute_reason', label: '争议原因', minWidth: 200, render: (row) => <span className="text-sm">{row.dispute_reason}</span> },
    { id: 'dispute_time', label: '争议时间', minWidth: 150, render: (row) => new Date(row.dispute_time).toLocaleString('zh-CN') },
    { id: 'status', label: '状态', minWidth: 100, render: (row) => { const s = DISPUTE_STATUS_MAP[row.status]; return s ? <Tag theme={s.theme} size="small">{s.label}</Tag> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'resolution', label: '处理结果', minWidth: 200, render: (row) => <span className="text-sm">{row.resolution || '—'}</span> },
    { id: 'resolved_at', label: '解决时间', minWidth: 150, render: (row) => row.resolved_at ? new Date(row.resolved_at).toLocaleString('zh-CN') : '—' },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="结算管理"
        subtitle="管理链上结算记录，支持发起结算、争议处理与统计分析"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['settlements'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总结算数" value={stats.totalSettlements} unit="笔" icon={<WalletIcon />} gradient="purple" />
        <StatCard title="已完成" value={stats.completedSettlements} unit="笔" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="待处理" value={stats.pendingSettlements} unit="笔" icon={<TimeIcon />} gradient="orange" />
        <StatCard title="总金额" value={Math.round(stats.totalAmount / 10000)} unit="万" icon={<MoneyIcon />} gradient="cyan" />
      </div>

      {/* 主 Tab 区域 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="settlements" label="结算记录">
          {/* ECharts 图表 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <ChartCard title="结算趋势分析" option={settlementTrendOption} className="lg:col-span-2" />
            <ChartCard title="结算状态分布" option={settlementStatusOption} />
          </div>

          {/* 数据表格 */}
          <PageSection padding="none" className="mt-4">
            <DataTable
              columns={columns}
              rows={pagedItems}
              loading={false}
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={setPage}
              onPageSizeChange={(size) => { setPageSize(size); setPage(0); }}
            />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="disputes" label="争议处理">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <PageSection padding="none">
                <DataTable columns={disputeColumns} rows={MOCK_DISPUTES} page={0} pageSize={20} total={MOCK_DISPUTES.length} />
              </PageSection>
            </div>
            <ChartCard title="月度结算金额" option={monthlyAmountOption} />
          </div>
        </Tabs.TabPanel>
      </Tabs>

      {/* 发起结算弹窗（多步骤） */}
      <Dialog visible={settleOpen} onClose={() => setSettleOpen(false)} header="发起结算" width="640px" footer={
        <div className="flex justify-end gap-2">
          <Button theme="default" onClick={() => setSettleOpen(false)}>取消</Button>
          {settleStep > 0 && <Button variant="outline" onClick={() => setSettleStep(settleStep - 1)}>上一步</Button>}
          {settleStep < 2 ? (
            <Button theme="primary" onClick={() => setSettleStep(settleStep + 1)} disabled={settleStep === 0 && (!fromOrg.trim() || !toOrg.trim())}>下一步</Button>
          ) : (
            <Button theme="primary" disabled={!fromOrg.trim() || !toOrg.trim() || !amount || !assetId.trim()} onClick={() => settleMut.mutate({ from_org: fromOrg, to_org: toOrg, amount: parseFloat(amount), asset_id: assetId })}>确认发起</Button>
          )}
        </div>
      }>
        <div className="mb-4">
          <Steps current={settleStep} style={{ marginBottom: 24 }}>
            <Steps.StepItem title="选择参与方" />
            <Steps.StepItem title="填写结算信息" />
            <Steps.StepItem title="确认发起" />
          </Steps>
        </div>

        {settleStep === 0 && (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">发起方组织</label>
              <Input value={fromOrg} onChange={(val) => setFromOrg(String(val))} placeholder="请输入发起方组织" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">接收方组织</label>
              <Input value={toOrg} onChange={(val) => setToOrg(String(val))} placeholder="请输入接收方组织" />
            </div>
          </div>
        )}

        {settleStep === 1 && (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">结算金额 (¥)</label>
              <Input value={amount} onChange={(val) => setAmount(String(val))} type="number" placeholder="请输入结算金额" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">关联资产 ID</label>
              <Input value={assetId} onChange={(val) => setAssetId(String(val))} placeholder="请输入关联资产 ID" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">关联合约 ID（可选）</label>
              <Input value={contractId} onChange={(val) => setContractId(String(val))} placeholder="请输入关联合约 ID" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">结算描述（可选）</label>
              <Textarea value={description} onChange={(val) => setDescription(String(val))} rows={2} placeholder="请输入结算描述" />
            </div>
          </div>
        )}

        {settleStep === 2 && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-gray-600">请确认以下结算信息：</p>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm"><strong>发起方：</strong>{fromOrg || '未填写'}</p>
              <p className="text-sm mt-2"><strong>接收方：</strong>{toOrg || '未填写'}</p>
              <p className="text-sm mt-2"><strong>金额：</strong>¥{amount ? parseFloat(amount).toFixed(2) : '0.00'}</p>
              <p className="text-sm mt-2"><strong>关联资产：</strong>{assetId || '未填写'}</p>
              {contractId && <p className="text-sm mt-2"><strong>关联合约：</strong>{contractId}</p>}
              {description && <p className="text-sm mt-2"><strong>描述：</strong>{description}</p>}
            </div>
            <div className="flex items-center gap-2 text-blue-600">
              <TimeIcon />
              <span className="text-sm">结算将通过智能合约自动执行</span>
            </div>
          </div>
        )}
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog visible={detailOpen} onClose={() => setDetailOpen(false)} header="结算详情" width="640px" footer={
        <div className="flex justify-end">
          <Button theme="default" onClick={() => setDetailOpen(false)}>关闭</Button>
        </div>
      }>
        {detailData ? (
          <div className="flex flex-col gap-4">
            <div className="flex gap-8">
              <div>
                <div className="text-xs text-gray-400">发起方</div>
                <div className="text-sm font-semibold">{detailData.from_org}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">接收方</div>
                <div className="text-sm font-semibold">{detailData.to_org}</div>
              </div>
            </div>
            <div className="flex gap-8">
              <div>
                <div className="text-xs text-gray-400">金额</div>
                <div className="text-lg font-bold text-blue-600">¥{(detailData.amount ?? 0).toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">状态</div>
                <StatusTag status={settlementStatusLabel(detailData.status)} color={settlementStatusColor(detailData.status)} />
              </div>
            </div>
            <div className="flex gap-8">
              <div>
                <div className="text-xs text-gray-400">关联资产</div>
                <div className="text-sm">{detailData.asset_id}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">关联合约</div>
                <div className="text-sm">{detailData.contract_id || '—'}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400">交易哈希</div>
              <div className="text-sm font-mono break-all">{detailData.tx_hash ?? '—'}</div>
            </div>
            {detailData.description && (
              <div>
                <div className="text-xs text-gray-400">描述</div>
                <div className="text-sm">{detailData.description}</div>
              </div>
            )}
            <div className="flex gap-8">
              <div>
                <div className="text-xs text-gray-400">创建时间</div>
                <div className="text-sm">{new Date(detailData.created_at).toLocaleString('zh-CN')}</div>
              </div>
              {detailData.completed_at && (
                <div>
                  <div className="text-xs text-gray-400">完成时间</div>
                  <div className="text-sm">{new Date(detailData.completed_at).toLocaleString('zh-CN')}</div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-gray-400">暂无数据</div>
        )}
      </Dialog>

      {/* 争议处理弹窗 */}
      <Dialog visible={disputeOpen} onClose={() => { setDisputeOpen(false); setDisputeReason(''); }} header="争议处理" width="480px" footer={
        <div className="flex justify-end gap-2">
          <Button theme="default" onClick={() => { setDisputeOpen(false); setDisputeReason(''); }}>取消</Button>
          <Button theme="warning" disabled={!disputeReason.trim()} onClick={() => disputeMut.mutate({ id: disputeId, reason: disputeReason })}>提交争议</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500">请输入争议原因，将提交链上争议处理。</p>
          <div>
            <label className="block text-sm text-gray-600 mb-1">结算ID</label>
            <Input value={disputeId} disabled />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">争议原因</label>
            <Textarea value={disputeReason} onChange={(val) => setDisputeReason(String(val))} placeholder="请输入争议原因" rows={3} />
          </div>
        </div>
      </Dialog>

      <LoadingOverlay open={settleMut.isPending || detailMut.isPending || disputeMut.isPending} />
    </PageContainer>
  );
};

export default BcSettlementPage;