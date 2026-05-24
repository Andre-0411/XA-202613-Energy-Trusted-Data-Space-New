/**
 * NFT 资产管理页面
 * NFT 资产列表 + 铸造 NFT + 查看详情 + 转让 NFT
 */
import React, { useState, useMemo } from 'react';
import { Button, Input, Tag, Tooltip, Dialog, MessagePlugin } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, LinkIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, TrendingUpIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listNfts, mintNft, getNftDetail, transferNft } from '@/api/blockchain';
import type { NftAsset } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import FilterBar from '@/components/common/FilterBar';
import type { FilterField } from '@/components/common/FilterBar';

const BcAssetsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 筛选 & 分页 =====
  const [filterOwner, setFilterOwner] = useState<string>('');
  const [filterAssetId, setFilterAssetId] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 弹窗 =====
  const [mintOpen, setMintOpen] = useState<boolean>(false);
  const [mintAssetId, setMintAssetId] = useState<string>('');
  const [mintMetadataUri, setMintMetadataUri] = useState<string>('');

  const [transferOpen, setTransferOpen] = useState<boolean>(false);
  const [transferTarget, setTransferTarget] = useState<NftAsset | null>(null);
  const [transferTo, setTransferTo] = useState<string>('');

  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<NftAsset | null>(null);

  // ===== 数据查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['nfts', page, pageSize, filterOwner, filterAssetId],
    queryFn: () =>
      listNfts({
        page: page + 1,
        page_size: pageSize,
        owner: filterOwner || undefined,
        asset_id: filterAssetId || undefined,
      }),
  });

  const items: NftAsset[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // ===== 统计数据 (从 API 响应推导) =====
  const stats = useMemo(() => ({
    totalAssets: total,
    activeAssets: items.filter((item) => item.status === 'ACTIVE').length,
    pendingTransfer: items.filter((item) => item.status === 'PENDING').length,
    todayMinted: items.filter((item) => {
      const today = new Date().toDateString();
      return new Date(item.created_at).toDateString() === today;
    }).length,
  }), [total, items]);

  // ===== ECharts 配置 =====
  const mintTrendOption = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: ['铸造数量', '转让数量'], top: 10 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
    yAxis: { type: 'value', name: '资产数量' },
    series: [
      { name: '铸造数量', type: 'bar', data: [120, 150, 180, 185, 200, 220, 256], itemStyle: { color: '#2196f3' } },
      { name: '转让数量', type: 'bar', data: [45, 60, 75, 80, 90, 100, 115], itemStyle: { color: '#4caf50' } },
    ],
  }), []);

  const assetTypeOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 'middle' },
    series: [
      {
        name: '资产类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: [
          { value: 650, name: '能源数据NFT', itemStyle: { color: '#2196f3' } },
          { value: 380, name: '计算任务NFT', itemStyle: { color: '#4caf50' } },
          { value: 226, name: '服务凭证NFT', itemStyle: { color: '#ff9800' } },
        ],
      },
    ],
  }), []);

  // ===== Mutations =====
  const mintMut = useMutation({
    mutationFn: (d: { asset_id: string; metadata_uri?: string }) => mintNft(d),
    onSuccess: () => {
      MessagePlugin.success('NFT 铸造成功');
      queryClient.invalidateQueries({ queryKey: ['nfts'] });
      setMintOpen(false);
      setMintAssetId('');
      setMintMetadataUri('');
    },
    onError: () => { MessagePlugin.error('铸造失败'); },
  });

  const transferMut = useMutation({
    mutationFn: ({ tokenId, to }: { tokenId: string; to: string }) => transferNft(tokenId, to),
    onSuccess: () => {
      MessagePlugin.success('转让成功');
      queryClient.invalidateQueries({ queryKey: ['nfts'] });
      setTransferOpen(false);
      setTransferTarget(null);
      setTransferTo('');
    },
    onError: () => { MessagePlugin.error('转让失败'); },
  });

  const detailMut = useMutation({
    mutationFn: (tokenId: string) => getNftDetail(tokenId),
    onSuccess: (res) => {
      setDetailData(res.data ?? null);
      setDetailOpen(true);
    },
  });

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: 'NFT 资产' }],
    [],
  );

  const headerActions: PageAction[] = useMemo(
    () => [{ label: '铸造 NFT', icon: <AddIcon />, onClick: () => setMintOpen(true), variant: 'contained' }],
    [],
  );

  // ===== 筛选字段 =====
  const filterFields: FilterField[] = useMemo(() => [
    { name: 'owner', type: 'text', placeholder: '所有者地址', width: 220 },
    { name: 'assetId', type: 'text', placeholder: '关联资产 ID', width: 220 },
  ], []);

  const filterValues = useMemo(() => ({ owner: filterOwner, assetId: filterAssetId }), [filterOwner, filterAssetId]);

  const handleFilterChange = (name: string, value: string) => {
    if (name === 'owner') { setFilterOwner(value); setPage(0); }
    if (name === 'assetId') { setFilterAssetId(value); setPage(0); }
  };

  const handleFilterReset = () => { setFilterOwner(''); setFilterAssetId(''); setPage(0); };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="flex flex-col gap-4 h-full">
      <PageHeader
        title="NFT 资产管理"
        subtitle="管理链上 NFT 资产，支持铸造、转让与详情查看"
        breadcrumbs={breadcrumbs}
        actions={headerActions}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => queryClient.invalidateQueries({ queryKey: ['nfts'] }),
            tooltip: '刷新',
          },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="总资产数" value={stats.totalAssets} unit="个" icon={<CheckCircleFilledIcon />} gradient="purple" />
        <StatCard title="活跃资产" value={stats.activeAssets} unit="个" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="待转让" value={stats.pendingTransfer} unit="个" icon={<ErrorCircleFilledIcon />} gradient="cyan" />
        <StatCard title="今日铸造" value={stats.todayMinted} unit="个" icon={<TrendingUpIcon />} gradient="orange" />
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="资产铸造趋势" option={mintTrendOption} className="lg:col-span-2" />
        <ChartCard title="资产类型分布" option={assetTypeOption} />
      </div>

      {/* 搜索过滤栏 */}
      <FilterBar
        fields={filterFields}
        values={filterValues}
        onChange={handleFilterChange}
        onReset={handleFilterReset}
      />

      {/* 数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50 z-10">
              <tr className="border-b border-gray-200">
                <th className="text-left px-4 py-3 font-bold text-gray-600">Token ID</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">关联资产</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">所有者</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">Metadata URI</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">交易哈希</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">创建时间</th>
                <th className="text-center px-4 py-3 font-bold text-gray-600 w-[140px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Tag variant="outline">{row.token_id.slice(0, 12) + '...'}</Tag>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-600 max-w-[140px] truncate inline-block">{row.asset_id}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-600 font-mono max-w-[160px] truncate inline-block">{row.owner}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-600 max-w-[160px] truncate inline-block">{row.metadata_uri ?? '—'}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Tooltip content={row.tx_hash ?? ''}>
                      <Tag variant="outline" theme="primary">
                        {(row.tx_hash?.slice(0, 10) ?? '—') + (row.tx_hash ? '...' : '')}
                      </Tag>
                    </Tooltip>
                  </td>
                  <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('zh-CN')}</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="查看详情">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => detailMut.mutate(row.token_id)}>
                          <BrowseIcon />
                        </span>
                      </Tooltip>
                      <Tooltip content="转让">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => { setTransferTarget(row); setTransferOpen(true); }}>
                          <LinkIcon />
                        </span>
                      </Tooltip>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {/* 分页 */}
        <div className="flex items-center justify-end px-4 py-3 border-t border-gray-200 gap-4">
          <span className="text-xs text-gray-500">每页行数</span>
          <select
            className="border border-gray-300 rounded px-2 py-1 text-sm"
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(0); }}
          >
            {[10, 20, 50].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <span className="text-xs text-gray-500">{`${page * pageSize + 1}-${Math.min((page + 1) * pageSize, total)} / ${total}`}</span>
          <div className="flex gap-1">
            <button className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>上一页</button>
            <button className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50" disabled={page + 1 >= totalPages} onClick={() => setPage((p) => p + 1)}>下一页</button>
          </div>
        </div>
      </div>

      {/* 铸造 NFT 弹窗 */}
      <Dialog visible={mintOpen} onClose={() => setMintOpen(false)} header="铸造 NFT" width="480px" footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setMintOpen(false)}>取消</Button>
          <Button theme="primary" disabled={!mintAssetId.trim()} onClick={() => mintMut.mutate({ asset_id: mintAssetId, metadata_uri: mintMetadataUri || undefined })}>铸造</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">关联资产 ID</label>
            <Input value={mintAssetId} onChange={(val) => setMintAssetId(String(val))} />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Metadata URI（可选）</label>
            <Input value={mintMetadataUri} onChange={(val) => setMintMetadataUri(String(val))} placeholder="ipfs://..." />
          </div>
        </div>
      </Dialog>

      {/* 转让 NFT 弹窗 */}
      <Dialog visible={transferOpen} onClose={() => { setTransferOpen(false); setTransferTo(''); }} header="转让 NFT" width="480px" footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => { setTransferOpen(false); setTransferTo(''); }}>取消</Button>
          <Button theme="primary" disabled={!transferTo.trim()} onClick={() => transferTarget && transferMut.mutate({ tokenId: transferTarget.token_id, to: transferTo })}>确认转让</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <span className="text-xs text-gray-600">
            将 Token {transferTarget?.token_id?.slice(0, 12) ?? ''}... 转让给新所有者。
          </span>
          <div>
            <label className="block text-sm text-gray-600 mb-1">接收方地址</label>
            <Input value={transferTo} onChange={(val) => setTransferTo(String(val))} placeholder="0x..." />
          </div>
        </div>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog visible={detailOpen} onClose={() => setDetailOpen(false)} header="NFT 详情" width="640px" footer={
        <Button variant="outline" onClick={() => setDetailOpen(false)}>关闭</Button>
      }>
        {detailData ? (
          <div className="flex flex-col gap-4">
            <div className="flex gap-8">
              <div>
                <span className="text-xs text-gray-500">Token ID</span>
                <p className="text-sm font-mono">{detailData.token_id}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">关联资产</span>
                <p className="text-sm">{detailData.asset_id}</p>
              </div>
            </div>
            <div className="flex gap-8">
              <div>
                <span className="text-xs text-gray-500">所有者</span>
                <p className="text-sm font-mono">{detailData.owner}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">Metadata URI</span>
                <p className="text-sm">{detailData.metadata_uri ?? '—'}</p>
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500">交易哈希</span>
              <p className="text-sm font-mono">{detailData.tx_hash}</p>
            </div>
            <div>
              <span className="text-xs text-gray-500">创建时间</span>
              <p className="text-sm">{new Date(detailData.created_at).toLocaleString('zh-CN')}</p>
            </div>
          </div>
        ) : (
          <span className="text-gray-400">暂无数据</span>
        )}
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </div>
  );
};

export default BcAssetsPage;
