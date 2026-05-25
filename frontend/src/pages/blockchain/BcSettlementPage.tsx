/**
 * 结算管理页面
 * 结算列表 + 发起结算 + 查看详情 + 争议处理
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Textarea, Tag, Tooltip, Dialog, MessagePlugin } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, LinkIcon,
  WalletIcon, CheckCircleFilledIcon, TimeIcon, TrendingUpIcon,
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

const BcSettlementPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 分页 =====
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 发起结算弹窗 =====
  const [settleOpen, setSettleOpen] = useState<boolean>(false);
  const [fromOrg, setFromOrg] = useState<string>('');
  const [toOrg, setToOrg] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [assetId, setAssetId] = useState<string>('');

  // ===== 详情弹窗 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<Settlement | null>(null);

  // ===== 争议处理弹窗 =====
  const [disputeOpen, setDisputeOpen] = useState<boolean>(false);
  const [disputeId, setDisputeId] = useState<string>('');
  const [disputeReason, setDisputeReason] = useState<string>('');

  // ===== 本地结算列表 =====
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const items: Settlement[] = settlements;
  const total: number = settlements.length;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalSettlements: total,
    completedSettlements: items.filter((item) => item.status === 'COMPLETED').length,
    pendingSettlements: items.filter((item) => item.status === 'PENDING').length,
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
          { value: 756, name: '已完成', itemStyle: { color: '#4caf50' } },
          { value: 89, name: '待处理', itemStyle: { color: '#ff9800' } },
          { value: 35, name: '争议中', itemStyle: { color: '#f44336' } },
          { value: 10, name: '失败', itemStyle: { color: '#9e9e9e' } },
        ],
      },
    ],
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
      setFromOrg(''); setToOrg(''); setAmount(''); setAssetId('');
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
    { id: 'from_org', label: '发起方', minWidth: 120 },
    { id: 'to_org', label: '接收方', minWidth: 120 },
    { id: 'amount', label: '金额', minWidth: 100, render: (row) => <span className="font-semibold">¥{(row.amount ?? 0).toFixed(2)}</span> },
    { id: 'asset_id', label: '关联资产', minWidth: 120 },
    {
      id: 'tx_hash', label: '交易哈希', minWidth: 160,
      render: (row) => row.tx_hash ? (
        <Tooltip content={row.tx_hash}>
          <span className="font-mono text-xs truncate inline-block max-w-[140px]">{(row.tx_hash ?? '').slice(0, 14)}...</span>
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
                <LinkIcon size={16} />
              </span>
            </Tooltip>
          )}
        </div>
      ),
    },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="结算管理"
        subtitle="管理链上结算记录，支持发起结算与争议处理"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          { icon: <RefreshIcon />, onClick: () => queryClient.invalidateQueries({ queryKey: ['settlements'] }), tooltip: '刷新' },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总结算数" value={stats.totalSettlements} unit="笔" icon={<WalletIcon />} gradient="purple" />
        <StatCard title="已完成" value={stats.completedSettlements} unit="笔" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="待处理" value={stats.pendingSettlements} unit="笔" icon={<TimeIcon />} gradient="cyan" />
        <StatCard title="今日结算" value={Math.round(stats.todayAmount / 10000)} unit="万" icon={<TrendingUpIcon />} gradient="orange" />
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="结算趋势分析" option={settlementTrendOption} className="lg:col-span-2" />
        <ChartCard title="结算状态分布" option={settlementStatusOption} />
      </div>

      {/* 数据表格 */}
      <PageSection padding="none">
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

      {/* 发起结算弹窗 */}
      <Dialog
        visible={settleOpen}
        onClose={() => setSettleOpen(false)}
        header="发起结算"
        footer={
          <div className="flex justify-end gap-2">
            <Button theme="default" onClick={() => setSettleOpen(false)}>取消</Button>
            <Button
              theme="primary"
              disabled={!fromOrg.trim() || !toOrg.trim() || !amount || !assetId.trim()}
              onClick={() => settleMut.mutate({ from_org: fromOrg, to_org: toOrg, amount: parseFloat(amount), asset_id: assetId })}
            >确认发起</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">发起方组织</label>
            <Input value={fromOrg} onChange={(val) => setFromOrg(String(val))} placeholder="请输入发起方组织" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">接收方组织</label>
            <Input value={toOrg} onChange={(val) => setToOrg(String(val))} placeholder="请输入接收方组织" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">金额</label>
            <Input value={amount} onChange={(val) => setAmount(String(val))} type="number" placeholder="请输入金额" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">关联资产 ID</label>
            <Input value={assetId} onChange={(val) => setAssetId(String(val))} placeholder="请输入关联资产 ID" />
          </div>
        </div>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog
        visible={detailOpen}
        onClose={() => setDetailOpen(false)}
        header="结算详情"
        footer={
          <div className="flex justify-end">
            <Button theme="default" onClick={() => setDetailOpen(false)}>关闭</Button>
          </div>
        }
      >
        {detailData ? (
          <div className="flex flex-col gap-4">
            <div className="flex gap-8">
              <div>
                <div className="text-xs text-gray-400">发起方</div>
                <div className="text-sm">{detailData.from_org}</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">接收方</div>
                <div className="text-sm">{detailData.to_org}</div>
              </div>
            </div>
            <div className="flex gap-8">
              <div>
                <div className="text-xs text-gray-400">金额</div>
                <div className="text-lg font-bold">¥{(detailData.amount ?? 0).toFixed(2)}</div>
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
                <div className="text-xs text-gray-400">交易哈希</div>
                <div className="text-sm font-mono">{detailData.tx_hash ?? '—'}</div>
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400">创建时间</div>
              <div className="text-sm">{new Date(detailData.created_at).toLocaleString('zh-CN')}</div>
            </div>
          </div>
        ) : (
          <div className="text-gray-400">暂无数据</div>
        )}
      </Dialog>

      {/* 争议处理弹窗 */}
      <Dialog
        visible={disputeOpen}
        onClose={() => { setDisputeOpen(false); setDisputeReason(''); }}
        header="争议处理"
        footer={
          <div className="flex justify-end gap-2">
            <Button theme="default" onClick={() => { setDisputeOpen(false); setDisputeReason(''); }}>取消</Button>
            <Button
              theme="warning"
              disabled={!disputeReason.trim()}
              onClick={() => disputeMut.mutate({ id: disputeId, reason: disputeReason })}
            >提交争议</Button>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500">请输入争议原因，将提交链上争议处理。</p>
          <div>
            <label className="block text-sm text-gray-600 mb-1">争议原因</label>
            <Textarea
              value={disputeReason}
              onChange={(val) => setDisputeReason(String(val))}
              placeholder="请输入争议原因"
              rows={3}
            />
          </div>
        </div>
      </Dialog>

      <LoadingOverlay open={settleMut.isPending || detailMut.isPending || disputeMut.isPending} />
    </PageContainer>
  );
};

export default BcSettlementPage;
