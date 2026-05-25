/**
 * NFT 资产管理页面
 * NFT 资产列表 + 铸造 NFT + 查看详情 + 转让 NFT + 授权管理
 */
import React, { useState, useMemo } from 'react';
import { Button, Input, Tag, Tooltip, Dialog, MessagePlugin, Tabs, Table, Form, Card, Row, Col, Statistic, Divider, Typography, Space, Select, Steps, Badge, Timeline } from 'tdesign-react';
import {
  AddIcon, RefreshIcon, BrowseIcon, LinkIcon,
  CheckCircleFilledIcon, ErrorCircleFilledIcon, TrendingUpIcon,
  FileIcon, TimeIcon, User1Icon, LockOnIcon, LockOffIcon, SwapIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listNfts, mintNft, getNftDetail, transferNft } from '@/api/blockchain';
import type { NftAsset } from '@/types/api';
import PageContainer, { PageSection } from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem, PageAction } from '@/components/PageHeader';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';
import FilterBar from '@/components/common/FilterBar';
import type { FilterField } from '@/components/common/FilterBar';
import ReactECharts from 'echarts-for-react';

/* ========== 模拟数据 - NFT资产 ========== */
const MOCK_NFTS: NftAsset[] = [
  {
    token_id: '0x1a2b3c4d5e6f7890abcdef1234567890abcdef12',
    asset_id: 'asset-001',
    owner: '0x1234567890abcdef1234567890abcdef12345678',
    metadata_uri: 'ipfs://QmYwAPJzv5CZsnAzt8auVZRn1iiR7aHnGFdNeSV2yzCAH',
    status: 'ACTIVE',
    created_at: '2025-05-20T08:00:00Z',
    tx_hash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
    metadata: {
      name: '电网负荷数据NFT',
      description: '2025年5月电网负荷实时数据集',
      image: 'https://example.com/nft1.png',
      attributes: [
        { trait_type: '数据类型', value: '电网负荷' },
        { trait_type: '时间范围', value: '2025年5月' },
        { trait_type: '数据量', value: '1.2GB' },
      ],
    },
  },
  {
    token_id: '0x2b3c4d5e6f7890abcdef1234567890abcdef1234',
    asset_id: 'asset-002',
    owner: '0x234567890abcdef1234567890abcdef123456789',
    metadata_uri: 'ipfs://QmYwAPJzv5CZsnAzt8auVZRn1iiR7aHnGFdNeSV2yzCAH',
    status: 'ACTIVE',
    created_at: '2025-05-21T10:30:00Z',
    tx_hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    metadata: {
      name: '光伏发电数据NFT',
      description: '光伏发电站实时发电数据',
      image: 'https://example.com/nft2.png',
      attributes: [
        { trait_type: '数据类型', value: '光伏发电' },
        { trait_type: '电站容量', value: '100MW' },
        { trait_type: '更新频率', value: '5分钟' },
      ],
    },
  },
  {
    token_id: '0x3c4d5e6f7890abcdef1234567890abcdef123456',
    asset_id: 'asset-003',
    owner: '0x34567890abcdef1234567890abcdef1234567890',
    metadata_uri: 'ipfs://QmYwAPJzv5CZsnAzt8auVZRn1iiR7aHnGFdNeSV2yzCAH',
    status: 'PENDING',
    created_at: '2025-05-22T14:15:00Z',
    tx_hash: '0xdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abc',
    metadata: {
      name: '碳排放数据NFT',
      description: '企业碳排放监测数据',
      image: 'https://example.com/nft3.png',
      attributes: [
        { trait_type: '数据类型', value: '碳排放' },
        { trait_type: '监测周期', value: '月度' },
        { trait_type: '覆盖企业', value: '50家' },
      ],
    },
  },
  {
    token_id: '0x4d5e6f7890abcdef1234567890abcdef12345678',
    asset_id: 'asset-004',
    owner: '0x4567890abcdef1234567890abcdef1234567890a',
    metadata_uri: 'ipfs://QmYwAPJzv5CZsnAzt8auVZRn1iiR7aHnGFdNeSV2yzCAH',
    status: 'ACTIVE',
    created_at: '2025-05-23T09:45:00Z',
    tx_hash: '0x4567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12',
    metadata: {
      name: '储能调度数据NFT',
      description: '储能电站调度运行数据',
      image: 'https://example.com/nft4.png',
      attributes: [
        { trait_type: '数据类型', value: '储能调度' },
        { trait_type: '储能容量', value: '50MWh' },
        { trait_type: '调度频率', value: '15分钟' },
      ],
    },
  },
  {
    token_id: '0x5e6f7890abcdef1234567890abcdef1234567890',
    asset_id: 'asset-005',
    owner: '0x567890abcdef1234567890abcdef1234567890ab',
    metadata_uri: 'ipfs://QmYwAPJzv5CZsnAzt8auVZRn1iiR7aHnGFdNeSV2yzCAH',
    status: 'ACTIVE',
    created_at: '2025-05-24T11:20:00Z',
    tx_hash: '0x567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234',
    metadata: {
      name: '充电桩运营数据NFT',
      description: '充电桩运营状态与交易数据',
      image: 'https://example.com/nft5.png',
      attributes: [
        { trait_type: '数据类型', value: '充电桩运营' },
        { trait_type: '充电桩数量', value: '1000个' },
        { trait_type: '数据粒度', value: '实时' },
      ],
    },
  },
];

/* ========== 模拟数据 - 授权记录 ========== */
interface Authorization {
  id: string;
  token_id: string;
  authorized_address: string;
  authorization_type: string;
  start_time: string;
  end_time: string;
  status: string;
}

const MOCK_AUTHORIZATIONS: Authorization[] = [
  {
    id: 'auth-001',
    token_id: '0x1a2b3c4d5e6f7890abcdef1234567890abcdef12',
    authorized_address: '0xabcdef1234567890abcdef1234567890abcdef12',
    authorization_type: '数据使用权',
    start_time: '2025-05-20T08:00:00Z',
    end_time: '2025-06-20T08:00:00Z',
    status: 'active',
  },
  {
    id: 'auth-002',
    token_id: '0x2b3c4d5e6f7890abcdef1234567890abcdef1234',
    authorized_address: '0xbcdef1234567890abcdef1234567890abcdef123',
    authorization_type: '数据分析权',
    start_time: '2025-05-21T10:30:00Z',
    end_time: '2025-07-21T10:30:00Z',
    status: 'active',
  },
  {
    id: 'auth-003',
    token_id: '0x3c4d5e6f7890abcdef1234567890abcdef123456',
    authorized_address: '0xcdef1234567890abcdef1234567890abcdef1234',
    authorization_type: '数据展示权',
    start_time: '2025-05-22T14:15:00Z',
    end_time: '2025-06-22T14:15:00Z',
    status: 'expired',
  },
];

/* ========== 模拟数据 - 转让记录 ========== */
interface TransferRecord {
  id: string;
  token_id: string;
  from_address: string;
  to_address: string;
  transfer_time: string;
  tx_hash: string;
  status: string;
}

const MOCK_TRANSFERS: TransferRecord[] = [
  {
    id: 'transfer-001',
    token_id: '0x1a2b3c4d5e6f7890abcdef1234567890abcdef12',
    from_address: '0x1234567890abcdef1234567890abcdef12345678',
    to_address: '0xabcdef1234567890abcdef1234567890abcdef12',
    transfer_time: '2025-05-23T16:30:00Z',
    tx_hash: '0xtransfer1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
    status: 'completed',
  },
  {
    id: 'transfer-002',
    token_id: '0x4d5e6f7890abcdef1234567890abcdef12345678',
    from_address: '0x4567890abcdef1234567890abcdef1234567890a',
    to_address: '0xdef1234567890abcdef1234567890abcdef12345',
    transfer_time: '2025-05-24T09:15:00Z',
    tx_hash: '0xtransfer234567890abcdef1234567890abcdef1234567890abcdef1234567890a',
    status: 'completed',
  },
];

const NFT_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  ACTIVE: { label: '活跃', theme: 'success' },
  PENDING: { label: '待确认', theme: 'warning' },
  BURNED: { label: '已销毁', theme: 'danger' },
};

const AUTH_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  active: { label: '有效', theme: 'success' },
  expired: { label: '已过期', theme: 'warning' },
  revoked: { label: '已撤销', theme: 'danger' },
};

const TRANSFER_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  completed: { label: '已完成', theme: 'success' },
  pending: { label: '处理中', theme: 'warning' },
  failed: { label: '失败', theme: 'danger' },
};

const BcAssetsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 主 Tab =====
  const [activeTab, setActiveTab] = useState<string>('assets');

  // ===== 筛选 & 分页 =====
  const [filterOwner, setFilterOwner] = useState<string>('');
  const [filterAssetId, setFilterAssetId] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 弹窗 =====
  const [mintOpen, setMintOpen] = useState<boolean>(false);
  const [mintStep, setMintStep] = useState<number>(0);
  const [mintAssetId, setMintAssetId] = useState<string>('');
  const [mintMetadataUri, setMintMetadataUri] = useState<string>('');
  const [mintName, setMintName] = useState<string>('');
  const [mintDescription, setMintDescription] = useState<string>('');

  const [transferOpen, setTransferOpen] = useState<boolean>(false);
  const [transferTarget, setTransferTarget] = useState<NftAsset | null>(null);
  const [transferTo, setTransferTo] = useState<string>('');

  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<NftAsset | null>(null);

  const [authOpen, setAuthOpen] = useState<boolean>(false);
  const [authTarget, setAuthTarget] = useState<NftAsset | null>(null);
  const [authAddress, setAuthAddress] = useState<string>('');
  const [authType, setAuthType] = useState<string>('数据使用权');

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

  const items: NftAsset[] = data?.data?.items ?? MOCK_NFTS;
  const total: number = data?.data?.total ?? MOCK_NFTS.length;

  // ===== 统计数据 =====
  const stats = useMemo(() => ({
    totalAssets: total,
    activeAssets: items.filter((item) => item.status === 'ACTIVE').length,
    pendingTransfer: items.filter((item) => item.status === 'PENDING').length,
    todayMinted: items.filter((item) => {
      const today = new Date().toDateString();
      return new Date(item.created_at).toDateString() === today;
    }).length,
    totalAuthorizations: MOCK_AUTHORIZATIONS.length,
    activeAuthorizations: MOCK_AUTHORIZATIONS.filter(a => a.status === 'active').length,
    totalTransfers: MOCK_TRANSFERS.length,
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

  const authorizationChartOption = useMemo(() => ({
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{c}条' },
      data: [
        { value: MOCK_AUTHORIZATIONS.filter(a => a.status === 'active').length, name: '有效授权', itemStyle: { color: '#4caf50' } },
        { value: MOCK_AUTHORIZATIONS.filter(a => a.status === 'expired').length, name: '已过期', itemStyle: { color: '#ff9800' } },
        { value: MOCK_AUTHORIZATIONS.filter(a => a.status === 'revoked').length, name: '已撤销', itemStyle: { color: '#f44336' } },
      ],
    }],
  }), []);

  // ===== Mutations =====
  const mintMut = useMutation({
    mutationFn: (d: { asset_id: string; metadata_uri?: string }) => mintNft(d),
    onSuccess: () => {
      MessagePlugin.success('NFT 铸造成功');
      queryClient.invalidateQueries({ queryKey: ['nfts'] });
      setMintOpen(false);
      setMintStep(0);
      setMintAssetId('');
      setMintMetadataUri('');
      setMintName('');
      setMintDescription('');
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

  // ===== 表格列定义 =====
  const columns: Column<NftAsset>[] = useMemo(() => [
    {
      id: 'token_id', label: 'Token ID', minWidth: 140,
      render: (row) => <Tag variant="outline">{(row.token_id ?? '').slice(0, 12) + '...'}</Tag>,
    },
    {
      id: 'name', label: 'NFT名称', minWidth: 160,
      render: (row) => <span className="text-sm font-medium">{row.metadata?.name || '未命名'}</span>,
    },
    {
      id: 'asset_id', label: '关联资产', minWidth: 140,
      render: (row) => <span className="text-xs text-gray-600 max-w-[140px] truncate inline-block">{row.asset_id ?? '—'}</span>,
    },
    {
      id: 'owner', label: '所有者', minWidth: 180,
      render: (row) => <span className="text-xs text-gray-600 font-mono max-w-[160px] truncate inline-block">{row.owner ?? '—'}</span>,
    },
    {
      id: 'status', label: '状态', minWidth: 100,
      render: (row) => {
        const s = NFT_STATUS_MAP[row.status];
        return s ? <Tag theme={s.theme} size="small">{s.label}</Tag> : <Tag size="small">{row.status}</Tag>;
      },
    },
    {
      id: 'created_at', label: '铸造时间', minWidth: 160,
      render: (row) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      id: 'actions', label: '操作', minWidth: 200, align: 'center',
      render: (row) => (
        <div className="flex items-center justify-center gap-1">
          <Tooltip content="查看详情">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => detailMut.mutate(row.token_id)}>
              <BrowseIcon />
            </span>
          </Tooltip>
          <Tooltip content="授权管理">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500" onClick={() => { setAuthTarget(row); setAuthOpen(true); }}>
              <LockOnIcon />
            </span>
          </Tooltip>
          <Tooltip content="转让">
            <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500" onClick={() => { setTransferTarget(row); setTransferOpen(true); }}>
              <LinkIcon />
            </span>
          </Tooltip>
        </div>
      ),
    },
  ], []);

  // ===== 授权记录列定义 =====
  const authColumns: Column<Authorization>[] = useMemo(() => [
    { id: 'token_id', label: 'Token ID', minWidth: 140, render: (row) => <Tag variant="outline">{row.token_id.slice(0, 12) + '...'}</Tag> },
    { id: 'authorized_address', label: '授权地址', minWidth: 180, render: (row) => <span className="text-xs font-mono">{row.authorized_address.slice(0, 16) + '...'}</span> },
    { id: 'authorization_type', label: '授权类型', minWidth: 120, render: (row) => <Tag variant="outline" size="small">{row.authorization_type}</Tag> },
    { id: 'start_time', label: '开始时间', minWidth: 150, render: (row) => new Date(row.start_time).toLocaleString('zh-CN') },
    { id: 'end_time', label: '结束时间', minWidth: 150, render: (row) => new Date(row.end_time).toLocaleString('zh-CN') },
    { id: 'status', label: '状态', minWidth: 100, render: (row) => { const s = AUTH_STATUS_MAP[row.status]; return s ? <Tag theme={s.theme} size="small">{s.label}</Tag> : <Tag size="small">{row.status}</Tag>; } },
  ], []);

  // ===== 转让记录列定义 =====
  const transferColumns: Column<TransferRecord>[] = useMemo(() => [
    { id: 'token_id', label: 'Token ID', minWidth: 140, render: (row) => <Tag variant="outline">{row.token_id.slice(0, 12) + '...'}</Tag> },
    { id: 'from_address', label: '转出地址', minWidth: 180, render: (row) => <span className="text-xs font-mono">{row.from_address.slice(0, 16) + '...'}</span> },
    { id: 'to_address', label: '转入地址', minWidth: 180, render: (row) => <span className="text-xs font-mono">{row.to_address.slice(0, 16) + '...'}</span> },
    { id: 'transfer_time', label: '转让时间', minWidth: 150, render: (row) => new Date(row.transfer_time).toLocaleString('zh-CN') },
    { id: 'status', label: '状态', minWidth: 100, render: (row) => { const s = TRANSFER_STATUS_MAP[row.status]; return s ? <Tag theme={s.theme} size="small">{s.label}</Tag> : <Tag size="small">{row.status}</Tag>; } },
    { id: 'tx_hash', label: '交易哈希', minWidth: 140, render: (row) => <Tooltip content={row.tx_hash}><Tag variant="outline" theme="primary">{row.tx_hash.slice(0, 10) + '...'}</Tag></Tooltip> },
  ], []);

  return (
    <PageContainer>
      <PageHeader
        title="NFT 资产管理"
        subtitle="管理链上 NFT 资产，支持铸造、转让、授权与详情查看"
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
        <StatCard title="总资产数" value={stats.totalAssets} unit="个" icon={<FileIcon />} gradient="purple" />
        <StatCard title="活跃资产" value={stats.activeAssets} unit="个" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="有效授权" value={stats.activeAuthorizations} unit="条" icon={<LockOnIcon />} gradient="blue" />
        <StatCard title="转让记录" value={stats.totalTransfers} unit="条" icon={<SwapIcon />} gradient="orange" />
      </div>

      {/* 主 Tab 区域 */}
      <Tabs value={activeTab} onChange={(val) => setActiveTab(String(val))}>
        <Tabs.TabPanel value="assets" label="NFT资产">
          {/* ECharts 图表 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
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
          <PageSection padding="none">
            <DataTable
              columns={columns}
              rows={items}
              loading={isLoading}
              page={page}
              pageSize={pageSize}
              total={total}
              onPageChange={setPage}
              onPageSizeChange={(size) => { setPageSize(size); setPage(0); }}
            />
          </PageSection>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="authorizations" label="授权管理">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
            <div className="lg:col-span-2">
              <PageSection padding="none">
                <DataTable columns={authColumns} rows={MOCK_AUTHORIZATIONS} page={0} pageSize={20} total={MOCK_AUTHORIZATIONS.length} />
              </PageSection>
            </div>
            <ChartCard title="授权状态分布" option={authorizationChartOption} />
          </div>
        </Tabs.TabPanel>

        <Tabs.TabPanel value="transfers" label="转让记录">
          <PageSection padding="none" className="mt-4">
            <DataTable columns={transferColumns} rows={MOCK_TRANSFERS} page={0} pageSize={20} total={MOCK_TRANSFERS.length} />
          </PageSection>
        </Tabs.TabPanel>
      </Tabs>

      {/* 铸造 NFT 弹窗（多步骤） */}
      <Dialog visible={mintOpen} onClose={() => setMintOpen(false)} header="铸造 NFT" width="640px" footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setMintOpen(false)}>取消</Button>
          {mintStep > 0 && <Button variant="outline" onClick={() => setMintStep(mintStep - 1)}>上一步</Button>}
          {mintStep < 2 ? (
            <Button theme="primary" onClick={() => setMintStep(mintStep + 1)} disabled={mintStep === 0 && !mintAssetId.trim()}>下一步</Button>
          ) : (
            <Button theme="primary" disabled={!mintAssetId.trim()} onClick={() => mintMut.mutate({ asset_id: mintAssetId, metadata_uri: mintMetadataUri || undefined })}>铸造</Button>
          )}
        </div>
      }>
        <div className="mb-4">
          <Steps current={mintStep} style={{ marginBottom: 24 }}>
            <Steps.StepItem title="选择资产" />
            <Steps.StepItem title="填写元数据" />
            <Steps.StepItem title="确认铸造" />
          </Steps>
        </div>

        {mintStep === 0 && (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">关联资产 ID</label>
              <Input value={mintAssetId} onChange={(val) => setMintAssetId(String(val))} placeholder="请输入要铸造为NFT的资产ID" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">NFT 名称</label>
              <Input value={mintName} onChange={(val) => setMintName(String(val))} placeholder="请输入NFT名称" />
            </div>
          </div>
        )}

        {mintStep === 1 && (
          <div className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">NFT 描述</label>
              <Input value={mintDescription} onChange={(val) => setMintDescription(String(val))} placeholder="请输入NFT描述" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Metadata URI（可选）</label>
              <Input value={mintMetadataUri} onChange={(val) => setMintMetadataUri(String(val))} placeholder="ipfs://..." />
            </div>
          </div>
        )}

        {mintStep === 2 && (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-gray-600">请确认以下NFT信息：</p>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm"><strong>资产ID：</strong>{mintAssetId || '未填写'}</p>
              <p className="text-sm mt-2"><strong>NFT名称：</strong>{mintName || '未填写'}</p>
              <p className="text-sm mt-2"><strong>描述：</strong>{mintDescription || '未填写'}</p>
              <p className="text-sm mt-2"><strong>Metadata URI：</strong>{mintMetadataUri || '自动生成'}</p>
            </div>
            <div className="flex items-center gap-2 text-blue-600">
              <TimeIcon />
              <span className="text-sm">铸造后将生成唯一的Token ID</span>
            </div>
          </div>
        )}
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
            {detailData.metadata && (
              <>
                <Divider>元数据</Divider>
                <div>
                  <span className="text-xs text-gray-500">NFT名称</span>
                  <p className="text-sm font-semibold">{detailData.metadata.name}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">描述</span>
                  <p className="text-sm">{detailData.metadata.description}</p>
                </div>
                {detailData.metadata.attributes && (
                  <div>
                    <span className="text-xs text-gray-500">属性</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {detailData.metadata.attributes.map((attr, index) => (
                        <Tag key={index} variant="outline" size="small">
                          {attr.trait_type}: {attr.value}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        ) : (
          <span className="text-gray-400">暂无数据</span>
        )}
      </Dialog>

      {/* 授权管理弹窗 */}
      <Dialog visible={authOpen} onClose={() => setAuthOpen(false)} header="授权管理" width="480px" footer={
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setAuthOpen(false)}>取消</Button>
          <Button theme="primary" disabled={!authAddress.trim()} onClick={() => {
            MessagePlugin.success(`已授权地址 ${authAddress.slice(0, 16)}...`);
            setAuthOpen(false);
            setAuthAddress('');
          }}>授权</Button>
        </div>
      }>
        <div className="flex flex-col gap-4">
          <span className="text-xs text-gray-600">
            为 Token {authTarget?.token_id?.slice(0, 12) ?? ''}... 设置授权。
          </span>
          <div>
            <label className="block text-sm text-gray-600 mb-1">授权地址</label>
            <Input value={authAddress} onChange={(val) => setAuthAddress(String(val))} placeholder="0x..." />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">授权类型</label>
            <Select value={authType} onChange={(val) => setAuthType(String(val))} options={[
              { label: '数据使用权', value: '数据使用权' },
              { label: '数据分析权', value: '数据分析权' },
              { label: '数据展示权', value: '数据展示权' },
              { label: '数据转授权', value: '数据转授权' },
            ]} />
          </div>
        </div>
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </PageContainer>
  );
};

export default BcAssetsPage;