/**
 * 智能合约管理页面
 * 合约列表 + 部署 + 调用 + 交易记录
 * 已对接真实API，无模拟数据
 */
import React, { useState } from 'react';
import { Button, Input, Tag, Dialog, MessagePlugin, Card, Statistic } from 'tdesign-react';
import { AddIcon, RefreshIcon, PlayIcon, BrowseIcon } from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listContracts, getContractDetail, invokeContract, getContractTransactions, deployContract, deployAllContracts } from '@/api/blockchain';
import type { SmartContract } from '@/types/api';
import PageContainer from '@/components/common/PageContainer';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import DataTable from '@/components/common/DataTable';
import type { Column } from '@/components/common/DataTable';

const CONTRACT_STATUS_MAP: Record<string, { label: string; theme: 'success' | 'warning' | 'primary' | 'danger' | 'default' }> = {
  DEPLOYED: { label: '已部署', theme: 'success' },
  PENDING: { label: '待部署', theme: 'warning' },
  FAILED: { label: '部署失败', theme: 'danger' },
};

const BcContractsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // 弹窗状态
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<SmartContract | null>(null);
  const [invokeOpen, setInvokeOpen] = useState<boolean>(false);
  const [invokeTarget, setInvokeTarget] = useState<SmartContract | null>(null);
  const [invokeMethod, setInvokeMethod] = useState<string>('');
  const [invokeArgs, setInvokeArgs] = useState<string>('{}');
  const [invokeResult, setInvokeResult] = useState<any>(null);

  // 查询合约列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['contracts'],
    queryFn: listContracts,
  });

  const items: SmartContract[] = data?.data ?? [];
  const total = items.length;

  // 统计
  const stats = {
    total: total,
    deployed: items.filter(i => i.status === 'DEPLOYED').length,
    pending: items.filter(i => i.status === 'PENDING').length,
  };

  // 部署所有合约
  const deployAllMutation = useMutation({
    mutationFn: deployAllContracts,
    onSuccess: () => {
      MessagePlugin.success('合约部署已触发');
      refetch();
    },
    onError: (error: any) => {
      MessagePlugin.error('部署失败: ' + (error?.message || '未知错误'));
    },
  });

  // 调用合约
  const invokeMutation = useMutation({
    mutationFn: ({ id, method, args }: { id: string; method: string; args: Record<string, unknown> }) =>
      invokeContract(id, method, args),
    onSuccess: (data) => {
      setInvokeResult(data?.data);
      MessagePlugin.success('合约调用成功');
    },
    onError: (error: any) => {
      MessagePlugin.error('调用失败: ' + (error?.message || '未知错误'));
    },
  });

  // 表格列定义
  const columns: Column[] = [
    { title: '合约名称', colKey: 'name', width: 200 },
    { title: '地址', colKey: 'address', width: 200 },
    { title: '版本', colKey: 'version', width: 80 },
    {
      title: '状态', colKey: 'status', width: 100,
      cell: ({ row }) => {
        const status = CONTRACT_STATUS_MAP[row.status] || { label: row.status, theme: 'default' as const };
        return <Tag theme={status.theme} variant="light">{status.label}</Tag>;
      },
    },
    { title: '部署时间', colKey: 'deployed_at', width: 180 },
    {
      title: '操作', colKey: 'actions', width: 200,
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button size="small" variant="text" icon={<BrowseIcon />} onClick={() => { setDetailData(row); setDetailOpen(true); }}>
            详情
          </Button>
          <Button size="small" variant="text" icon={<PlayIcon />}
            onClick={() => { setInvokeTarget(row); setInvokeOpen(true); setInvokeResult(null); }}>
            调用
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageContainer>
      <PageHeader title="智能合约管理" breadcrumbs={[homeBreadcrumb, { label: '区块链' }, { label: '智能合约' }]} />

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <Card><Statistic title="合约总数" value={stats.total} /></Card>
        <Card><Statistic title="已部署" value={stats.deployed} /></Card>
        <Card><Statistic title="待部署" value={stats.pending} /></Card>
      </div>

      {/* 操作栏 */}
      <div className="flex justify-between mb-4">
        <div className="flex gap-2">
          <Button icon={<AddIcon />} loading={deployAllMutation.isPending} onClick={() => deployAllMutation.mutate()}>
            部署所有合约
          </Button>
          <Button icon={<RefreshIcon />} variant="outline" onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      {/* 数据表格 */}
      <DataTable columns={columns} rows={items} page={page} pageSize={pageSize} total={total}
        onPageChange={setPage} loading={isLoading} />

      {/* 详情弹窗 */}
      <Dialog header="合约详情" visible={detailOpen} onClose={() => setDetailOpen(false)}
        footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}>
        {detailData && (
          <div className="space-y-3">
            <div><strong>合约名称:</strong> {detailData.name}</div>
            <div><strong>地址:</strong> {detailData.address}</div>
            <div><strong>版本:</strong> {detailData.version}</div>
            <div><strong>状态:</strong> {CONTRACT_STATUS_MAP[detailData.status]?.label || detailData.status}</div>
            <div><strong>部署时间:</strong> {detailData.deployed_at}</div>
            <div><strong>描述:</strong> {detailData.description || '无'}</div>
          </div>
        )}
      </Dialog>

      {/* 调用弹窗 */}
      <Dialog header="调用合约" visible={invokeOpen} onClose={() => setInvokeOpen(false)}
        footer={
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => setInvokeOpen(false)}>关闭</Button>
            <Button loading={invokeMutation.isPending}
              onClick={() => invokeTarget && invokeMutation.mutate({ id: invokeTarget.id, method: invokeMethod, args: JSON.parse(invokeArgs || '{}') })}>
              执行调用
            </Button>
          </div>
        }>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">方法名 *</label>
            <Input value={invokeMethod} onChange={setInvokeMethod} placeholder="methodName" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">参数 (JSON)</label>
            <Input value={invokeArgs} onChange={setInvokeArgs} placeholder='{"key": "value"}' />
          </div>
          {invokeResult && (
            <div>
              <label className="block text-sm font-medium mb-1">调用结果</label>
              <pre className="bg-gray-100 p-3 rounded text-sm overflow-auto max-h-40">
                {JSON.stringify(invokeResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Dialog>
    </PageContainer>
  );
};

export default BcContractsPage;
