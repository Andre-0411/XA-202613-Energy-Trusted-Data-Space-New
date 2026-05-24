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
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

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

  return (
    <div className="flex flex-col gap-4 h-full">
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
      <div className="rounded-xl bg-white border border-gray-200 flex flex-col flex-1 overflow-hidden">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">发起方</th>
                <th className="px-4 py-3 text-left font-semibold">接收方</th>
                <th className="px-4 py-3 text-left font-semibold">金额</th>
                <th className="px-4 py-3 text-left font-semibold">关联资产</th>
                <th className="px-4 py-3 text-left font-semibold">交易哈希</th>
                <th className="px-4 py-3 text-left font-semibold">状态</th>
                <th className="px-4 py-3 text-left font-semibold">创建时间</th>
                <th className="px-4 py-3 text-center font-semibold w-40">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pagedItems.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{row.from_org}</td>
                  <td className="px-4 py-3">{row.to_org}</td>
                  <td className="px-4 py-3 font-semibold">¥{row.amount.toFixed(2)}</td>
                  <td className="px-4 py-3">{row.asset_id}</td>
                  <td className="px-4 py-3">
                    {row.tx_hash ? (
                      <Tooltip content={row.tx_hash}>
                        <span className="font-mono text-xs truncate inline-block max-w-[140px]">
                          {row.tx_hash.slice(0, 14)}...
                        </span>
                      </Tooltip>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <StatusTag status={settlementStatusLabel(row.status)} color={settlementStatusColor(row.status)} />
                  </td>
                  <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="查看详情">
                        <span
                          className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500"
                          onClick={() => detailMut.mutate(row.id)}
                        >
                          <BrowseIcon size={16} />
                        </span>
                      </Tooltip>
                      {row.status === 'PENDING' && (
                        <Tooltip content="争议处理">
                          <span
                            className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-orange-500"
                            onClick={() => { setDisputeId(row.id); setDisputeOpen(true); }}
                          >
                            <LinkIcon size={16} />
                          </span>
                        </Tooltip>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {pagedItems.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* 分页 */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
          <span className="text-sm text-gray-500">共 {total} 条</span>
          <div className="flex items-center gap-2">
            <select
              className="border border-gray-300 rounded px-2 py-1 text-sm"
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
            >
              {[10, 20, 50].map((n) => <option key={n} value={n}>{n} 条/页</option>)}
            </select>
            <button
              className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >上一页</button>
            <span className="text-sm text-gray-600">{page + 1} / {Math.max(1, Math.ceil(total / pageSize))}</span>
            <button
              className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50"
              disabled={(page + 1) * pageSize >= total}
              onClick={() => setPage((p) => p + 1)}
            >下一页</button>
          </div>
        </div>
      </div>

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
                <div className="text-lg font-bold">¥{detailData.amount.toFixed(2)}</div>
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
    </div>
  );
};

export default BcSettlementPage;
