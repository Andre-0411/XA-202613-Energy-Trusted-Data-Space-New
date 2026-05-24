/**
 * 智能合约管理页面
 * 合约列表 + 查看详情(ABI) + 调用合约 + 查看交易记录
 * 增强：链状态监控 + 合约部署管理
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Button, Input, Tag, Tooltip, Dialog, MessagePlugin, Textarea } from 'tdesign-react';
import {
  RefreshIcon, BrowseIcon, CheckCircleFilledIcon, TrendingUpIcon,
  LinkIcon, SearchIcon,
} from 'tdesign-icons-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listContracts, getContractDetail, invokeContract, getContractTransactions,
  getChainStatus, deployContract, deployAllContracts,
} from '@/api/blockchain';
import type { SmartContract } from '@/types/api';
import PageHeader, { homeBreadcrumb } from '@/components/PageHeader';
import type { BreadcrumbItem } from '@/components/PageHeader';
import StatusTag from '@/components/StatusTag';
import LoadingOverlay from '@/components/LoadingOverlay';
import StatCard from '@/components/common/StatCard';
import ChartCard from '@/components/common/ChartCard';

/** 合约状态颜色映射 */
const contractStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
  const map: Record<string, 'success' | 'warning' | 'error'> = {
    active: 'success',
    DEPLOYED: 'success',
    inactive: 'warning',
    PENDING: 'warning',
    upgrading: 'info' as unknown as 'warning',
    FAILED: 'error',
  };
  return (map[status] as 'success' | 'warning' | 'error' | 'default') ?? 'default';
};

/** 合约状态中文映射 */
const contractStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    active: '已部署',
    DEPLOYED: '已部署',
    inactive: '未激活',
    PENDING: '部署中',
    upgrading: '升级中',
    FAILED: '部署失败',
  };
  return map[status] ?? status;
};

const BcContractsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // ===== 分页（客户端分页） =====
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<number>(10);

  // ===== 弹窗状态 =====
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [detailData, setDetailData] = useState<SmartContract | null>(null);

  const [invokeOpen, setInvokeOpen] = useState<boolean>(false);
  const [invokeId, setInvokeId] = useState<string>('');
  const [invokeMethod, setInvokeMethod] = useState<string>('');
  const [invokeArgs, setInvokeArgs] = useState<string>('{}');
  const [invokeResult, setInvokeResult] = useState<Record<string, unknown> | null>(null);

  const [txOpen, setTxOpen] = useState<boolean>(false);
  const [txContractId, setTxContractId] = useState<string>('');
  const [txPage, setTxPage] = useState<number>(0);
  const [txPageSize, setTxPageSize] = useState<number>(5);

  // ===== 合约列表查询 =====
  const { data, isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: listContracts,
  });

  const items: SmartContract[] = (data?.data as unknown as SmartContract[]) ?? [];

  // ===== 链状态查询（每 10 秒轮询） =====
  const { data: chainData } = useQuery({
    queryKey: ['chainStatus'],
    queryFn: getChainStatus,
    refetchInterval: 10000,
  });

  const chainStatus = chainData?.data ?? {
    connected: false, block_number: 0, peer_count: 0, chain_id: 0, latest_block_time: 0,
  };

  // ===== 客户端分页 =====
  const total: number = items.length;
  const pagedItems: SmartContract[] = items.slice(page * pageSize, (page + 1) * pageSize);

  // ===== 统计数据 (从真实数据推导) =====
  const stats = useMemo(() => ({
    totalContracts: items.length,
    deployed: items.filter((item) => item.status === 'active' || item.status === 'DEPLOYED').length,
    blockNumber: chainStatus.block_number,
    peerCount: chainStatus.peer_count,
    chainConnected: chainStatus.connected,
    chainId: chainStatus.chain_id,
  }), [items, chainStatus]);

  // ===== ECharts 配置 — 合约类型分布（从 items 动态计算） =====
  const contractTypeOption = useMemo(() => {
    const categories: Record<string, number> = {};
    items.forEach((item) => {
      const cat = item.name.includes('NFT') ? '数据资产NFT'
        : (item.name.includes('Evidence') || item.name.includes('Usage')) ? '存证合约'
        : item.name.includes('Settlement') ? '结算合约'
        : item.name.includes('Identity') ? '身份合约'
        : item.name.includes('Access') ? '访问控制'
        : item.name.includes('Compliance') ? '合规审计'
        : '其他';
      categories[cat] = (categories[cat] || 0) + 1;
    });

    const colors = ['#2196f3', '#4caf50', '#ff9800', '#9c27b0', '#00bcd4', '#e91e63'];

    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', top: 'middle' },
      series: [{
        name: '合约类型',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: { label: { show: true, fontSize: 18, fontWeight: 'bold' } },
        labelLine: { show: false },
        data: Object.entries(categories).map(([name, value], i) => ({
          value, name, itemStyle: { color: colors[i % colors.length] },
        })),
      }],
    };
  }, [items]);

  // ===== ECharts 配置 — 合约状态分布柱状图 =====
  const deployTrendOption = useMemo(() => {
    const active = items.filter((i) => i.status === 'active' || i.status === 'DEPLOYED').length;
    const inactive = items.filter((i) => i.status === 'inactive').length;
    const upgrading = items.filter((i) => i.status === 'upgrading').length;

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['已部署', '未激活', '升级中'], top: 10 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['已部署', '未激活', '升级中'] },
      yAxis: { type: 'value', name: '数量' },
      series: [
        {
          type: 'bar',
          data: [
            { value: active, itemStyle: { color: '#4caf50' } },
            { value: inactive, itemStyle: { color: '#ff9800' } },
            { value: upgrading, itemStyle: { color: '#2196f3' } },
          ],
          barWidth: '40%',
        },
      ],
    };
  }, [items]);

  // 交易记录查询
  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ['contractTransactions', txContractId, txPage, txPageSize],
    queryFn: () => getContractTransactions(txContractId, { page: txPage + 1, page_size: txPageSize }),
    enabled: txOpen && !!txContractId,
  });

  const txItems: Record<string, unknown>[] = txData?.data?.items ?? [];
  const txTotal: number = txData?.data?.total ?? 0;

  // ===== Mutations =====
  const detailMut = useMutation({
    mutationFn: (id: string) => getContractDetail(id),
    onSuccess: (res) => {
      setDetailData(res.data ?? null);
      setDetailOpen(true);
    },
  });

  const invokeMut = useMutation({
    mutationFn: ({ id, method, args }: { id: string; method: string; args: Record<string, unknown> }) =>
      invokeContract(id, method, args),
    onSuccess: (res) => {
      setInvokeResult(res.data ?? null);
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
    },
  });

  // ===== 部署 Mutations =====
  const deployMut = useMutation({
    mutationFn: (contractName: string) => deployContract(contractName),
    onSuccess: (res) => {
      MessagePlugin.success(`合约 ${res.data?.name ?? ''} 部署成功`);
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      queryClient.invalidateQueries({ queryKey: ['chainStatus'] });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : '未知错误';
      MessagePlugin.error(`部署失败: ${message}`);
    },
  });

  const deployAllMut = useMutation({
    mutationFn: deployAllContracts,
    onSuccess: (res) => {
      const count = Object.keys(res.data?.results ?? {}).length;
      MessagePlugin.success(`成功部署 ${count} 个合约`);
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
      queryClient.invalidateQueries({ queryKey: ['chainStatus'] });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : '未知错误';
      MessagePlugin.error(`一键部署失败: ${message}`);
    },
  });

  // ===== 操作处理 =====
  const openInvoke = useCallback((contract: SmartContract) => {
    setInvokeId(contract.id);
    setInvokeMethod('');
    setInvokeArgs('{}');
    setInvokeResult(null);
    setInvokeOpen(true);
  }, []);

  const openTransactions = useCallback((contractId: string) => {
    setTxContractId(contractId);
    setTxPage(0);
    setTxOpen(true);
  }, []);

  const handleInvoke = useCallback(() => {
    let args: Record<string, unknown> = {};
    try {
      args = JSON.parse(invokeArgs || '{}');
    } catch {
      args = {};
    }
    invokeMut.mutate({ id: invokeId, method: invokeMethod, args });
  }, [invokeId, invokeMethod, invokeArgs, invokeMut]);

  // ===== 面包屑 =====
  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [homeBreadcrumb, { label: '区块链中心' }, { label: '智能合约' }],
    [],
  );

  const totalPages = Math.ceil(total / pageSize);
  const txTotalPages = Math.ceil(txTotal / txPageSize);

  return (
    <div className="flex flex-col gap-4 h-full">
      <PageHeader
        title="智能合约管理"
        subtitle="管理链上智能合约，支持查看详情、调用合约、交易记录与部署管理"
        breadcrumbs={breadcrumbs}
        iconActions={[
          {
            icon: <RefreshIcon />,
            onClick: () => {
              queryClient.invalidateQueries({ queryKey: ['contracts'] });
              queryClient.invalidateQueries({ queryKey: ['chainStatus'] });
            },
            tooltip: '刷新',
          },
          {
            icon: <CheckCircleFilledIcon />,
            onClick: () => deployAllMut.mutate(),
            tooltip: '一键部署全部合约',
            disabled: deployAllMut.isPending,
          },
        ]}
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="总合约数" value={stats.totalContracts} unit="个" icon={<SearchIcon />} gradient="purple" />
        <StatCard title="已部署" value={stats.deployed} unit="个" icon={<CheckCircleFilledIcon />} gradient="green" />
        <StatCard title="区块高度" value={stats.blockNumber} unit="" icon={<TrendingUpIcon />} gradient="red" />
        <StatCard title="节点数" value={stats.peerCount} unit="个" icon={<LinkIcon />} gradient="cyan" />
        <StatCard title={stats.chainConnected ? '已连接' : '未连接'} value={stats.chainId} unit="Chain" icon={<LinkIcon />} gradient={stats.chainConnected ? 'green' : 'red'} />
      </div>

      {/* ECharts 图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="合约状态分布" option={deployTrendOption} className="lg:col-span-2" />
        <ChartCard title="合约类型分布" option={contractTypeOption} />
      </div>

      {/* 数据表格 */}
      <div className="rounded-xl bg-white border border-gray-200 flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-50 z-10">
              <tr className="border-b border-gray-200">
                <th className="text-left px-4 py-3 font-bold text-gray-600">合约名称</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">合约地址</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">版本</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">状态</th>
                <th className="text-left px-4 py-3 font-bold text-gray-600">部署时间</th>
                <th className="text-center px-4 py-3 font-bold text-gray-600 w-[200px]">操作</th>
              </tr>
            </thead>
            <tbody>
              {pagedItems.map((row) => (
                <tr key={row.id || row.name} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="text-sm font-medium">{row.name}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Tooltip content={row.address || 'N/A'}>
                      <Tag variant="outline">
                        {row.address
                          ? (row.address.length > 20
                            ? row.address.slice(0, 10) + '...' + row.address.slice(-8)
                            : row.address)
                          : 'N/A'}
                      </Tag>
                    </Tooltip>
                  </td>
                  <td className="px-4 py-3">v{row.version}</td>
                  <td className="px-4 py-3">
                    <StatusTag status={contractStatusLabel(row.status)} color={contractStatusColor(row.status)} />
                  </td>
                  <td className="px-4 py-3">
                    {row.deployed_at ? new Date(row.deployed_at).toLocaleString('zh-CN') : '未部署'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Tooltip content="查看详情">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center" onClick={() => detailMut.mutate(row.id)}>
                          <BrowseIcon />
                        </span>
                      </Tooltip>
                      <Tooltip content="调用合约">
                        <span className={`cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-blue-500 ${row.status !== 'active' && row.status !== 'DEPLOYED' ? 'opacity-40 pointer-events-none' : ''}`} onClick={() => openInvoke(row)}>
                          <CheckCircleFilledIcon />
                        </span>
                      </Tooltip>
                      <Tooltip content="交易记录">
                        <span className="cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-purple-500" onClick={() => openTransactions(row.id)}>
                          <TrendingUpIcon />
                        </span>
                      </Tooltip>
                      {row.status !== 'active' && row.status !== 'DEPLOYED' && (
                        <Tooltip content="部署此合约">
                          <span className={`cursor-pointer hover:bg-gray-100 rounded p-1 inline-flex items-center text-green-500 ${deployMut.isPending ? 'opacity-40 pointer-events-none' : ''}`} onClick={() => deployMut.mutate(row.name)}>
                            <CheckCircleFilledIcon />
                          </span>
                        </Tooltip>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {pagedItems.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-400">暂无数据</td>
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

      {/* 合约详情弹窗 */}
      <Dialog visible={detailOpen} onClose={() => setDetailOpen(false)} header="合约详情" width="640px" footer={
        <Button variant="outline" onClick={() => setDetailOpen(false)}>关闭</Button>
      }>
        {detailData ? (
          <div className="flex flex-col gap-4">
            <div className="flex gap-8">
              <div>
                <span className="text-xs text-gray-500">合约名称</span>
                <p className="text-sm font-semibold">{detailData.name}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">版本</span>
                <p className="text-sm">v{detailData.version}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">状态</span>
                <StatusTag status={contractStatusLabel(detailData.status)} color={contractStatusColor(detailData.status)} />
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500">合约地址</span>
              <p className="text-sm font-mono">{detailData.address}</p>
            </div>
            {detailData.deploy_tx_hash && (
              <div>
                <span className="text-xs text-gray-500">部署交易哈希</span>
                <p className="text-sm font-mono">{detailData.deploy_tx_hash}</p>
              </div>
            )}
            <div>
              <span className="text-xs text-gray-500">ABI 定义</span>
              <div className="mt-1 p-3 bg-gray-50 rounded-lg">
                <pre className="text-xs font-mono whitespace-pre-wrap max-h-[300px] overflow-auto">
                  {JSON.stringify(detailData.abi, null, 2)}
                </pre>
              </div>
            </div>
            <div>
              <span className="text-xs text-gray-500">部署时间</span>
              <p className="text-sm">
                {detailData.deployed_at ? new Date(detailData.deployed_at).toLocaleString('zh-CN') : '未部署'}
              </p>
            </div>
          </div>
        ) : (
          <span className="text-gray-400">暂无数据</span>
        )}
      </Dialog>

      {/* 调用合约弹窗 */}
      <Dialog visible={invokeOpen} onClose={() => setInvokeOpen(false)} header="调用合约" width="480px" footer={
        <Button variant="outline" onClick={() => setInvokeOpen(false)}>关闭</Button>
      }>
        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">方法名</label>
            <Input value={invokeMethod} onChange={(val) => setInvokeMethod(String(val))} placeholder="例如: transfer" />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">参数 (JSON)</label>
            <Textarea value={invokeArgs} onChange={(val) => setInvokeArgs(String(val))} placeholder='{"to": "0x...", "amount": 100}' rows={4} />
          </div>
          <Button theme="primary" onClick={handleInvoke} disabled={!invokeMethod.trim()}>执行调用</Button>
          {invokeResult && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-semibold mb-2">调用结果</p>
              <pre className="text-xs font-mono whitespace-pre-wrap">
                {JSON.stringify(invokeResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </Dialog>

      {/* 交易记录弹窗 */}
      <Dialog visible={txOpen} onClose={() => setTxOpen(false)} header="交易记录" width="640px" footer={
        <Button variant="outline" onClick={() => setTxOpen(false)}>关闭</Button>
      }>
        {txLoading ? (
          <span className="text-gray-400">加载中...</span>
        ) : txItems.length === 0 ? (
          <span className="text-gray-400">暂无交易记录</span>
        ) : (
          <div className="flex flex-col gap-2">
            {txItems.map((tx, idx) => (
              <div key={idx} className="p-3 border border-gray-200 rounded-lg">
                <pre className="text-xs font-mono whitespace-pre-wrap">
                  {JSON.stringify(tx, null, 2)}
                </pre>
              </div>
            ))}
            <div className="flex items-center justify-center gap-2 mt-2">
              <button className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50" disabled={txPage === 0} onClick={() => setTxPage((p) => p - 1)}>上一页</button>
              <span className="text-xs text-gray-500">第 {txPage + 1} 页</span>
              <button className="px-2 py-1 text-sm border border-gray-300 rounded disabled:opacity-50" disabled={(txPage + 1) * txPageSize >= txTotal} onClick={() => setTxPage((p) => p + 1)}>下一页</button>
            </div>
          </div>
        )}
      </Dialog>

      <LoadingOverlay open={isLoading} />
    </div>
  );
};

export default BcContractsPage;
