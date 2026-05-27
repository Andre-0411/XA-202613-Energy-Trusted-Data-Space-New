/**
 * NFT 资产管理页面
 * NFT 资产列表 + 铸造 NFT + 查看详情 + 转让 NFT
 * 已对接真实API，无模拟数据
 */
import React, { useState } from 'react';
import { Button, Input, Tag, Dialog, MessagePlugin, Tabs, Card, Statistic } from 'tdesign-react';
import { AddIcon, RefreshIcon, BrowseIcon, SwapIcon } from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listNfts, mintNft, getNftDetail, transferNft } from '@/api/blockchain';
import type { NftAsset } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';

const NFT_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  ACTIVE: { label: '活跃', theme: 'success' },
  PENDING: { label: '待确认', theme: 'warning' },
  BURNED: { label: '已销毁', theme: 'danger' },
};

const BcAssetsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // 弹窗状态
  const [mintOpen, setMintOpen] = useState<boolean>(false);
  const [mintAssetId, setMintAssetId] = useState<string>('');
  const [mintMetadataUri, setMintMetadataUri] = useState<string>('');
  const [transferOpen, setTransferOpen] = useState<boolean>(false);
  const [transferTarget, setTransferTarget] = useState<NftAsset | null>(null);
  const [transferTo, setTransferTo] = useState<string>('');
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<NftAsset | null>(null);

  // 查询NFT列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['nfts', page, pageSize],
    queryFn: () => listNfts({ page: page + 1, page_size: pageSize }),
  });

  const items: NftAsset[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;

  // 统计数据
  const stats = {
    totalAssets: total,
    activeAssets: items.filter(i => i.status === 'ACTIVE').length,
    pendingAssets: items.filter(i => i.status === 'PENDING').length,
  };

  // 铸造NFT
  const mintMutation = useMutation({
    mutationFn: mintNft,
    onSuccess: () => {
      MessagePlugin.success('NFT铸造成功');
      setMintOpen(false);
      setMintAssetId('');
      setMintMetadataUri('');
      refetch();
    },
    onError: (error: any) => {
      MessagePlugin.error('铸造失败: ' + (error?.message || '未知错误'));
    },
  });

  // 转让NFT
  const transferMutation = useMutation({
    mutationFn: ({ tokenId, to }: { tokenId: string; to: string }) => transferNft(tokenId, to),
    onSuccess: () => {
      MessagePlugin.success('NFT转让成功');
      setTransferOpen(false);
      setTransferTo('');
      refetch();
    },
    onError: (error: any) => {
      MessagePlugin.error('转让失败: ' + (error?.message || '未知错误'));
    },
  });

  // 表格列定义
  const columns: Column[] = [
    { title: 'Token ID', colKey: 'token_id', width: 200 },
    { title: '资产ID', colKey: 'asset_id', width: 150 },
    { title: '所有者', colKey: 'owner', width: 200 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }) => {
        const status = NFT_STATUS_MAP[row.status] || { label: row.status, theme: 'default' as const };
        return <Tag theme={status.theme} variant="light">{status.label}</Tag>;
      },
    },
    { title: '创建时间', colKey: 'created_at', width: 180 },
    {
      title: '操作', colKey: 'actions', width: 200,
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => { setDetailData(row); setDetailOpen(true); }}>
            详情
          </Button>
          <Button size="small" variant="text" icon={<SwapIcon />} onClick={() => { setTransferTarget(row); setTransferOpen(true); }}>
            转让
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader title="NFT资产管理" breadcrumbs={[homeBreadcrumb, { label: '区块链' }, { label: 'NFT资产' }]} />

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <Card>
          <Statistic title="NFT总数" value={stats.totalAssets} />
        </Card>
        <Card>
          <Statistic title="活跃NFT" value={stats.activeAssets} />
        </Card>
        <Card>
          <Statistic title="待确认" value={stats.pendingAssets} />
        </Card>
      </div>

      {/* 操作栏 */}
      <div className="flex justify-between mb-4">
        <div className="flex gap-2">
          <Button icon={<AddIcon />} onClick={() => setMintOpen(true)}>铸造NFT</Button>
          <Button icon={<RefreshIcon />} variant="outline" onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      {/* 数据表格 */}
      <DataTable
        columns={columns}
        rows={items}
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
        loading={isLoading}
      />

      {/* 铸造弹窗 */}
      <Dialog header="铸造NFT" visible={mintOpen} onClose={() => setMintOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setMintOpen(false)}>取消</Button>
            <Button loading={mintMutation.isPending} onClick={() => mintMutation.mutate({ asset_id: mintAssetId, metadata_uri: mintMetadataUri })}>
              确认铸造
            </Button>
          </div>
        }>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">资产ID *</label>
            <Input value={mintAssetId} onChange={setMintAssetId} placeholder="输入资产ID" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">元数据URI</label>
            <Input value={mintMetadataUri} onChange={setMintMetadataUri} placeholder="ipfs://..." />
          </div>
        </div>
      </Dialog>

      {/* 转让弹窗 */}
      <Dialog header="转让NFT" visible={transferOpen} onClose={() => setTransferOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setTransferOpen(false)}>取消</Button>
            <Button loading={transferMutation.isPending}
              onClick={() => transferTarget && transferMutation.mutate({ tokenId: transferTarget.token_id, to: transferTo })}>
              确认转让
            </Button>
          </div>
        }>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">目标地址 *</label>
            <Input value={transferTo} onChange={setTransferTo} placeholder="0x..." />
          </div>
        </div>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog header="NFT详情" visible={detailOpen} onClose={() => setDetailOpen(false)}
        footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}>
        {detailData && (
          <div className="space-y-3">
            <div><strong>Token ID:</strong> {detailData.token_id}</div>
            <div><strong>资产ID:</strong> {detailData.asset_id}</div>
            <div><strong>所有者:</strong> {detailData.owner}</div>
            <div><strong>状态:</strong> {NFT_STATUS_MAP[detailData.status]?.label || detailData.status}</div>
            <div><strong>创建时间:</strong> {detailData.created_at}</div>
          </div>
        )}
      </Dialog>
    </PageContainer>
  );
};

export default BcAssetsPage;
